import 'dart:convert';
import 'dart:math';
import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';
import '../models/user_model.dart';
import '../models/auth_model.dart';
import '../services/api_service.dart';
import '../services/storage_service.dart';
import '../../core/constants/api_constants.dart';

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(
    apiService: ref.watch(apiServiceProvider),
    storage: ref.watch(storageServiceProvider),
  );
});

class AuthRepository {
  final ApiService _api;
  final StorageService _storage;
  final FirebaseAuth _firebaseAuth = FirebaseAuth.instance;

  AuthRepository({required ApiService apiService, required StorageService storage})
      : _api = apiService,
        _storage = storage;

  Stream<User?> get authStateChanges => _firebaseAuth.authStateChanges();

  Future<String?> getCurrentToken() async {
    final user = _firebaseAuth.currentUser;
    if (user != null) {
      return await user.getIdToken();
    }
    return null;
  }

  Future<UserSessionResponse> createSession(String firebaseToken) async {
    final response = await _api.dio.post(
      ApiConstants.authSession,
      options: Options(
        headers: {ApiConstants.authorization: '${ApiConstants.bearer} $firebaseToken'},
      ),
    );
    final session = UserSessionResponse.fromJson(response.data);
    await _storage.setToken(firebaseToken);
    await _storage.setUserId(session.id);
    return session;
  }

  Future<SendEmailCodeResponse> sendEmailVerificationCode(String email) async {
    final response = await _api.post(
      ApiConstants.authEmailSendCode,
      data: SendEmailCodeRequest(email: email).toJson(),
    );
    return SendEmailCodeResponse.fromJson(response.data);
  }

  Future<VerifyEmailCodeResponse> verifyEmailCode(String code) async {
    final response = await _api.post(
      ApiConstants.authEmailVerifyCode,
      data: VerifyEmailCodeRequest(code: code).toJson(),
    );
    return VerifyEmailCodeResponse.fromJson(response.data);
  }

  Future<void> signOut() async {
    await _firebaseAuth.signOut();
    // Google Sign-In caches the last-used account independently of Firebase.
    // Without this, tapping "Sign in with Google" again after logging out
    // (or after a failed attempt) silently reuses the same account instead
    // of showing the account picker.
    try {
      await GoogleSignIn().signOut();
    } catch (_) {
      // Not fatal — the account may never have been a Google account.
    }
    await _storage.clearToken();
  }

  // Phone Auth
  Future<void> verifyPhoneNumber({
    required String phoneNumber,
    required Function(String verificationId) onCodeSent,
    required Function(String error) onError,
  }) async {
    await _firebaseAuth.verifyPhoneNumber(
      phoneNumber: phoneNumber,
      verificationCompleted: (PhoneAuthCredential credential) async {
        await _firebaseAuth.signInWithCredential(credential);
      },
      verificationFailed: (FirebaseAuthException e) {
        onError(e.message ?? 'Verification failed');
      },
      codeSent: (String verificationId, int? resendToken) {
        onCodeSent(verificationId);
      },
      codeAutoRetrievalTimeout: (String verificationId) {},
    );
  }

  Future<UserCredential> verifyOtp(String verificationId, String smsCode) async {
    final credential = PhoneAuthProvider.credential(
      verificationId: verificationId,
      smsCode: smsCode,
    );
    return await _firebaseAuth.signInWithCredential(credential);
  }

  // Google Sign In
  Future<UserCredential?> signInWithGoogle() async {
    final googleSignIn = GoogleSignIn();
    // Clear any cached account first so the picker always shows — without
    // this, retrying after a failed sign-in (or signing in again after a
    // previous session) silently reuses whichever account was picked last,
    // with no way to choose a different one.
    try {
      await googleSignIn.signOut();
    } catch (_) {
      // Ignore — nothing cached yet is the normal first-run case.
    }

    final googleUser = await googleSignIn.signIn();
    if (googleUser == null) {
      // User cancelled the flow.
      return null;
    }

    final googleAuth = await googleUser.authentication;
    final credential = GoogleAuthProvider.credential(
      accessToken: googleAuth.accessToken,
      idToken: googleAuth.idToken,
    );

    final userCredential = await _firebaseAuth.signInWithCredential(credential);
    final token = await userCredential.user?.getIdToken();
    if (token != null) {
      try {
        await createSession(token);
      } catch (e) {
        // Firebase/Google sign-in itself succeeded, but our backend
        // rejected the session (e.g. a transient token-verification issue
        // server-side). Without this, the user is left in a confusing
        // half-signed-in state: Firebase thinks they're logged in, but no
        // backend session/User row exists, and every retry of "Sign in
        // with Google" would hit the same already-signed-in Firebase user
        // instead of a clean new attempt. Signing fully back out here
        // means a retry is a genuinely fresh attempt.
        await signOut();
        rethrow;
      }
    }
    return userCredential;
  }

  // Apple Sign In
  Future<UserCredential?> signInWithApple() async {
    final rawNonce = _generateNonce();
    final nonce = sha256.convert(utf8.encode(rawNonce)).toString();

    final appleCredential = await SignInWithApple.getAppleIDCredential(
      scopes: [
        AppleIDAuthorizationScopes.email,
        AppleIDAuthorizationScopes.fullName,
      ],
      nonce: nonce,
    );

    final oauthCredential = OAuthProvider('apple.com').credential(
      idToken: appleCredential.identityToken,
      rawNonce: rawNonce,
      accessToken: appleCredential.authorizationCode,
    );

    final userCredential = await _firebaseAuth.signInWithCredential(oauthCredential);
    final token = await userCredential.user?.getIdToken();
    if (token != null) {
      try {
        await createSession(token);
      } catch (e) {
        // Same reasoning as signInWithGoogle above — don't leave Firebase
        // signed in if our backend rejected the session.
        await signOut();
        rethrow;
      }
    }
    return userCredential;
  }

  String _generateNonce([int length = 32]) {
    const charset =
        '0123456789ABCDEFGHIJKLMNOPQRSTUVXYZabcdefghijklmnopqrstuvwxyz-._';
    final random = Random.secure();
    return List.generate(length, (_) => charset[random.nextInt(charset.length)])
        .join();
  }
}