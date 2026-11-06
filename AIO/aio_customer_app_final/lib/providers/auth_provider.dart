import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/repositories/auth_repository.dart';
import '../data/repositories/driver_repository.dart';
import '../data/services/storage_service.dart';

final authStateProvider = StreamProvider<AuthState>((ref) async* {
  final authRepo = ref.watch(authRepositoryProvider);
  final storage = ref.watch(storageServiceProvider);

  await for (final user in authRepo.authStateChanges) {
    final isOnboardingComplete = await storage.isOnboardingComplete();
    final token = await storage.getToken();

    if (user != null && token != null) {
      // Reads the role custom claim Firebase attaches to the ID token —
      // "driver" for accounts created via the admin panel (see
      // driver_auth_router.py), absent/anything else means a normal
      // customer. This can briefly be stale right after a role-specific
      // login until roleOverrideProvider catches up — same pattern as
      // isAuthenticated/isOnboardingComplete below.
      String role = 'customer';
      try {
        final idTokenResult = await user.getIdTokenResult();
        final claimRole = idTokenResult.claims?['role'];
        if (claimRole == 'driver') role = 'driver';
      } catch (_) {
        // Fall back to 'customer' if claims can't be read for any reason.
      }
      yield AuthState.authenticated(isOnboardingComplete: isOnboardingComplete, role: role);
    } else {
      yield AuthState.unauthenticated(isOnboardingComplete: isOnboardingComplete);
    }
  }
});

// Immediate, synchronous override for onboarding completion.
// authStateProvider only re-emits when Firebase's authStateChanges fires,
// so without this the router's redirect logic would still see stale
// (isOnboardingComplete: false) data right after the user finishes onboarding.
final onboardingCompleteOverrideProvider = StateProvider<bool?>((ref) => null);

// Immediate, synchronous override for "is authenticated".
// authStateProvider's stream fires the instant Firebase signs someone in,
// but at that exact moment our own backend session token hasn't been saved
// to storage yet (createSession() is still an in-flight network call), so
// the stream reads token == null and yields unauthenticated. Nothing then
// re-triggers the stream once the token actually gets saved, so without
// this override the router gets stuck thinking the user isn't logged in
// even after sign-in (and session creation) succeeded.
final authenticatedOverrideProvider = StateProvider<bool?>((ref) => null);

// Immediate, synchronous override for "role" (customer vs driver) — same
// staleness problem as authenticatedOverrideProvider: the role claim is
// embedded in the Firebase ID token, and right after a role-specific login
// (customer OR driver) the router needs to know which shell to send the
// user into before the stream has necessarily settled.
final roleOverrideProvider = StateProvider<String?>((ref) => null);

final authNotifierProvider = StateNotifierProvider<AuthNotifier, AsyncValue<void>>((ref) {
  return AuthNotifier(
    authRepo: ref.watch(authRepositoryProvider),
    driverRepo: ref.watch(driverRepositoryProvider),
    storage: ref.watch(storageServiceProvider),
    ref: ref,
  );
});

class AuthState {
  final bool isAuthenticated;
  final bool isOnboardingComplete;
  final String role; // 'customer' or 'driver' — meaningless when unauthenticated.

  const AuthState._(this.isAuthenticated, this.isOnboardingComplete, this.role);

  factory AuthState.authenticated({required bool isOnboardingComplete, String role = 'customer'}) =>
      AuthState._(true, isOnboardingComplete, role);

  factory AuthState.unauthenticated({required bool isOnboardingComplete}) =>
      AuthState._(false, isOnboardingComplete, 'customer');
}

class AuthNotifier extends StateNotifier<AsyncValue<void>> {
  final AuthRepository _authRepo;
  final DriverRepository _driverRepo;
  final StorageService _storage;
  final Ref _ref;

  AuthNotifier({
    required AuthRepository authRepo,
    required DriverRepository driverRepo,
    required StorageService storage,
    required Ref ref,
  })  : _authRepo = authRepo,
        _driverRepo = driverRepo,
        _storage = storage,
        _ref = ref,
        super(const AsyncValue.data(null));

  String? _verificationId;

  Future<void> verifyPhone(String phoneNumber) async {
    state = const AsyncValue.loading();
    try {
      await _authRepo.verifyPhoneNumber(
        phoneNumber: phoneNumber,
        onCodeSent: (id) => _verificationId = id,
        onError: (error) => throw Exception(error),
      );
      state = const AsyncValue.data(null);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> verifyOtp(String otp) async {
    state = const AsyncValue.loading();
    try {
      if (_verificationId == null) throw Exception('No verification ID');
      final credential = await _authRepo.verifyOtp(_verificationId!, otp);
      final token = await credential.user?.getIdToken();
      if (token != null) {
        await _authRepo.createSession(token);
        _ref.read(roleOverrideProvider.notifier).state = 'customer';
        _ref.read(authenticatedOverrideProvider.notifier).state = true;
      }
      state = const AsyncValue.data(null);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> signInWithGoogle() async {
    state = const AsyncValue.loading();
    try {
      final result = await _authRepo.signInWithGoogle();
      if (result == null) {
        // User cancelled the sign-in flow — not an error, just reset state.
        state = const AsyncValue.data(null);
        return;
      }
      _ref.read(roleOverrideProvider.notifier).state = 'customer';
      _ref.read(authenticatedOverrideProvider.notifier).state = true;
      state = const AsyncValue.data(null);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> signInWithApple() async {
    state = const AsyncValue.loading();
    try {
      final result = await _authRepo.signInWithApple();
      if (result == null) {
        state = const AsyncValue.data(null);
        return;
      }
      _ref.read(roleOverrideProvider.notifier).state = 'customer';
      _ref.read(authenticatedOverrideProvider.notifier).state = true;
      state = const AsyncValue.data(null);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  /// Driver login — no OTP. The backend matches the phone number against a
  /// driver account an admin already created and returns a Firebase custom
  /// token; we sign in with it, then run the exact same session-creation
  /// step every other login path uses.
  Future<void> loginAsDriver(String phoneNumber) async {
    state = const AsyncValue.loading();
    try {
      final loginResponse = await _driverRepo.loginWithPhone(phoneNumber);
      final userCredential = await FirebaseAuth.instance.signInWithCustomToken(
        loginResponse.customToken,
      );
      final token = await userCredential.user?.getIdToken();
      if (token != null) {
        await _authRepo.createSession(token);
        _ref.read(roleOverrideProvider.notifier).state = 'driver';
        _ref.read(authenticatedOverrideProvider.notifier).state = true;
      }
      state = const AsyncValue.data(null);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> signOut() async {
    state = const AsyncValue.loading();
    try {
      await _authRepo.signOut();
      _ref.read(authenticatedOverrideProvider.notifier).state = false;
      _ref.read(roleOverrideProvider.notifier).state = null;
      state = const AsyncValue.data(null);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> completeOnboarding() async {
    await _storage.setOnboardingComplete(true);
  }
}