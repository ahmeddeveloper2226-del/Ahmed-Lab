import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/user_model.dart';
import '../models/address_model.dart';
import '../services/api_service.dart';
import '../../core/constants/api_constants.dart';

final profileRepositoryProvider = Provider<ProfileRepository>((ref) {
  return ProfileRepository(apiService: ref.watch(apiServiceProvider));
});

class ProfileRepository {
  final ApiService _api;

  ProfileRepository({required ApiService apiService}) : _api = apiService;

  Future<UserProfileResponse> getProfile() async {
    final response = await _api.get(ApiConstants.me);
    return UserProfileResponse.fromJson(response.data);
  }

  Future<UserProfileResponse> updateProfile(String fullName) async {
    final response = await _api.patch(
      ApiConstants.me,
      data: UserProfileUpdateRequest(full_name: fullName).toJson(),
    );
    return UserProfileResponse.fromJson(response.data);
  }

  Future<List<AddressResponse>> getAddresses() async {
    final response = await _api.get(ApiConstants.meAddresses);
    final List<dynamic> data = response.data;
    return data.map((e) => AddressResponse.fromJson(e)).toList();
  }

  Future<AddressResponse> createAddress(AddressCreateRequest request) async {
    final response = await _api.post(ApiConstants.meAddresses, data: request.toJson());
    return AddressResponse.fromJson(response.data);
  }

  Future<AddressResponse> updateAddress(String addressId, AddressUpdateRequest request) async {
    final response = await _api.patch(
      '${ApiConstants.meAddresses}/$addressId',
      data: request.toJson(),
    );
    return AddressResponse.fromJson(response.data);
  }

  Future<void> deleteAddress(String addressId) async {
    await _api.delete('${ApiConstants.meAddresses}/$addressId');
  }

  Future<AddressResponse> setDefaultAddress(String addressId) async {
    final response = await _api.post(
      '${ApiConstants.meAddresses}/$addressId/set-default',
    );
    return AddressResponse.fromJson(response.data);
  }
}
