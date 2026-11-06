import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/prescription_model.dart';
import '../services/api_service.dart';
import '../../core/constants/api_constants.dart';

final prescriptionRepositoryProvider = Provider<PrescriptionRepository>((ref) {
  return PrescriptionRepository(apiService: ref.watch(apiServiceProvider));
});

class PrescriptionRepository {
  final ApiService _api;

  PrescriptionRepository({required ApiService apiService}) : _api = apiService;

  Future<PrescriptionResponse> createPrescription({required String shopId, required String imageUrl}) async {
    final response = await _api.post(
      ApiConstants.prescriptions,
      data: PrescriptionCreateRequest(shop_id: shopId, image_url: imageUrl).toJson(),
    );
    return PrescriptionResponse.fromJson(response.data);
  }

  Future<List<PrescriptionResponse>> getMyPrescriptions() async {
    final response = await _api.get(ApiConstants.prescriptions);
    final List<dynamic> data = response.data;
    return data.map((e) => PrescriptionResponse.fromJson(e)).toList();
  }

  Future<PrescriptionResponse> getPrescription(String id) async {
    final response = await _api.get(ApiConstants.prescriptionDetail(id));
    return PrescriptionResponse.fromJson(response.data);
  }

  /// The customer's "remove this medicine, it's too expensive" action.
  Future<PrescriptionResponse> removeItem(String prescriptionId, String itemId) async {
    final response = await _api.delete(ApiConstants.prescriptionRemoveItem(prescriptionId, itemId));
    return PrescriptionResponse.fromJson(response.data);
  }

  Future<PrescriptionResponse> approve(String id) async {
    final response = await _api.post(ApiConstants.prescriptionApprove(id));
    return PrescriptionResponse.fromJson(response.data);
  }

  Future<PrescriptionResponse> cancel(String id) async {
    final response = await _api.post(ApiConstants.prescriptionCancel(id));
    return PrescriptionResponse.fromJson(response.data);
  }
}