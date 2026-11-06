import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/medication_model.dart';
import '../services/api_service.dart';

final medicationRepositoryProvider = Provider<MedicationRepository>((ref) {
  return MedicationRepository(apiService: ref.watch(apiServiceProvider));
});

class MedicationRepository {
  final ApiService _api;
  static const _base = '/medications/';

  MedicationRepository({required ApiService apiService}) : _api = apiService;

  Future<List<MedicationCondition>> getConditions() async {
    final response = await _api.get('${_base}conditions');
    return (response.data as List<dynamic>)
        .map((e) => MedicationCondition.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<List<MedicationResponse>> getMedications() async {
    final response = await _api.get(_base);
    return (response.data as List<dynamic>).map((e) => MedicationResponse.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<MedicationResponse> addMedication({
    required String productId,
    required String medicineName,
    required String condition,
    required int packQuantity,
    required double dailyDosage,
    int reminderDaysBefore = 3,
  }) async {
    final response = await _api.post(_base, data: {
      'product_id': productId,
      'medicine_name': medicineName,
      'condition': condition,
      'pack_quantity': packQuantity,
      'daily_dosage': dailyDosage,
      'reminder_days_before': reminderDaysBefore,
    });
    return MedicationResponse.fromJson(response.data);
  }

  Future<MedicationResponse> updateMedication(String id, {bool? isActive}) async {
    final response = await _api.patch('$_base$id', data: {
      if (isActive != null) 'is_active': isActive,
    });
    return MedicationResponse.fromJson(response.data);
  }

  Future<void> deleteMedication(String id) async {
    await _api.delete('$_base$id');
  }

  Future<ReorderMedicationResult> reorderMedication(String id) async {
    final response = await _api.post('$_base$id/reorder');
    return ReorderMedicationResult.fromJson(response.data);
  }
}
