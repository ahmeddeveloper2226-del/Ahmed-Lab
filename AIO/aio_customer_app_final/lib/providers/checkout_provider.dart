import 'package:flutter_riverpod/flutter_riverpod.dart';

/// shop_id -> branch_id, populated as the customer picks a branch for each
/// branch-aware shop in their cart during checkout (see
/// widgets/checkout/branch_picker_section.dart). A shop the customer never
/// gets a picker for (single-location, or the picker hasn't loaded yet)
/// simply has no entry here — checkout_router.py/order_service.py treat a
/// missing entry as "use the existing automatic nearest-branch pick",
/// so this being incomplete never blocks checkout.
final checkoutBranchSelectionsProvider = StateProvider.autoDispose<Map<String, String>>((ref) => {});
