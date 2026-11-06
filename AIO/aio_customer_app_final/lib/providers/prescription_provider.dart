import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/models/prescription_model.dart';
import '../data/repositories/prescription_repository.dart';

final myPrescriptionsProvider = FutureProvider.autoDispose<List<PrescriptionResponse>>((ref) async {
  return await ref.watch(prescriptionRepositoryProvider).getMyPrescriptions();
});

/// Polls while the review screen is open — the customer is waiting on the
/// PHARMACIST to submit a list (pending_review -> awaiting_customer_approval),
/// which happens on their own time, not something this app can push a
/// notification for (the store management panel has no user account/FCM
/// token — see store_management_router.py). Polling is the same pattern
/// already used for driver.dart's offers.
final prescriptionDetailProvider =
    StreamProvider.autoDispose.family<PrescriptionResponse, String>((ref, prescriptionId) async* {
  final repo = ref.watch(prescriptionRepositoryProvider);
  while (true) {
    try {
      yield await repo.getPrescription(prescriptionId);
    } catch (_) {
      // Best-effort — keep the previous value on screen until the next
      // poll succeeds, rather than showing an error for one dropped request.
    }
    await Future.delayed(const Duration(seconds: 5));
  }
});