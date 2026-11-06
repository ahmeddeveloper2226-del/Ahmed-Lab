import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/models/medication_model.dart';
import '../data/repositories/medication_repository.dart';

final medicationConditionsProvider = FutureProvider.autoDispose<List<MedicationCondition>>((ref) async {
  try {
    return await ref.watch(medicationRepositoryProvider).getConditions();
  } catch (_) {
    return MedicationCondition.defaults();
  }
});

final medicationsProvider = FutureProvider.autoDispose<List<MedicationResponse>>((ref) async {
  return ref.watch(medicationRepositoryProvider).getMedications();
});
