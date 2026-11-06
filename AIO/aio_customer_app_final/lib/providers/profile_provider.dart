import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/models/user_model.dart';
import '../data/models/address_model.dart';
import '../data/repositories/profile_repository.dart';

final profileProvider = FutureProvider<UserProfileResponse>((ref) async {
  return await ref.watch(profileRepositoryProvider).getProfile();
});

final addressesProvider = FutureProvider<List<AddressResponse>>((ref) async {
  return await ref.watch(profileRepositoryProvider).getAddresses();
});

final profileNotifierProvider = StateNotifierProvider<ProfileNotifier, AsyncValue<void>>((ref) {
  return ProfileNotifier(repo: ref.watch(profileRepositoryProvider));
});

class ProfileNotifier extends StateNotifier<AsyncValue<void>> {
  final ProfileRepository _repo;

  ProfileNotifier({required ProfileRepository repo})
      : _repo = repo,
        super(const AsyncValue.data(null));

  Future<void> updateName(String fullName) async {
    state = const AsyncValue.loading();
    try {
      await _repo.updateProfile(fullName);
      state = const AsyncValue.data(null);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }
}
