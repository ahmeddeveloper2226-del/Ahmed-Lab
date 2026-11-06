import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/helpers.dart';
import '../../data/models/branch_model.dart';
import '../../data/services/location_service.dart';
import '../../providers/checkout_provider.dart';
import '../../providers/shop_provider.dart';

/// Shown once per branch-aware shop in the cart, during checkout (spec:
/// "the customer selects Store -> Branch"). Renders nothing for a
/// single-location shop — the delivery-options call comes back empty,
/// same silent-no-op pattern as BranchAvailabilitySection on the product
/// screen, so nothing changes for the overwhelming majority of shops.
///
/// Every branch is shown regardless of distance (spec 1.2 — city-wide,
/// no "too far" filtering); each is quoted with its own ETA and delivery
/// fee, sorted fastest-first. The fastest branch is pre-selected so a
/// customer who doesn't care can just continue, but every branch stays
/// tappable.
class BranchPickerSection extends ConsumerStatefulWidget {
  final String shopId;
  final String shopName;
  const BranchPickerSection({super.key, required this.shopId, required this.shopName});

  @override
  ConsumerState<BranchPickerSection> createState() => _BranchPickerSectionState();
}

class _BranchPickerSectionState extends ConsumerState<BranchPickerSection> {
  LocationResult? _location;
  bool _locationLoading = true;

  @override
  void initState() {
    super.initState();
    _loadLocation();
  }

  Future<void> _loadLocation() async {
    final result = await ref.read(locationServiceProvider).getCurrentLocation();
    if (mounted) setState(() { _location = result; _locationLoading = false; });
  }

  void _autoSelectFastest(List<BranchDeliveryOption> options) {
    if (options.isEmpty) return;
    final selections = ref.read(checkoutBranchSelectionsProvider);
    if (selections.containsKey(widget.shopId)) return; // customer (or a previous build) already picked
    // Options are sorted fastest-ETA-first by the backend.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      ref.read(checkoutBranchSelectionsProvider.notifier).update(
            (state) => {...state, widget.shopId: options.first.branchId},
          );
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_locationLoading) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 12),
        child: Center(child: SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))),
      );
    }
    if (_location == null || !_location!.isSuccess) {
      // No location available — checkout still proceeds via the backend's
      // existing automatic branch selection; there's simply no picker to
      // show without knowing where to compute ETA/fee from.
      return const SizedBox.shrink();
    }

    final optionsAsync = ref.watch(branchDeliveryOptionsProvider(
      BranchOptionsQuery(shopId: widget.shopId, lat: _location!.lat!, lng: _location!.lng!),
    ));

    return optionsAsync.when(
      loading: () => const Padding(
        padding: EdgeInsets.symmetric(vertical: 12),
        child: Center(child: SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))),
      ),
      error: (e, _) => const SizedBox.shrink(), // never blocks checkout — falls back to auto-pick
      data: (options) {
        if (options.isEmpty) return const SizedBox.shrink(); // single-location shop
        _autoSelectFastest(options);

        final selectedId = ref.watch(checkoutBranchSelectionsProvider)[widget.shopId] ?? options.first.branchId;

        return Container(
          margin: const EdgeInsets.only(bottom: 12),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: AppColors.divider),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.storefront_rounded, size: 18, color: AppColors.primaryBlue),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'اختر فرع ${widget.shopName}',
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              ...options.map((branch) {
                final isSelected = branch.branchId == selectedId;
                return GestureDetector(
                  onTap: () => ref.read(checkoutBranchSelectionsProvider.notifier).update(
                        (state) => {...state, widget.shopId: branch.branchId},
                      ),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 150),
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: isSelected ? AppColors.primaryBlue.withValues(alpha: 0.06) : AppColors.background,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: isSelected ? AppColors.primaryBlue : AppColors.divider,
                        width: isSelected ? 1.5 : 1,
                      ),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 20,
                          height: 20,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            border: Border.all(color: isSelected ? AppColors.primaryBlue : AppColors.divider, width: 2),
                            color: isSelected ? AppColors.primaryBlue : Colors.transparent,
                          ),
                          child: isSelected ? const Icon(Icons.check, color: Colors.white, size: 12) : null,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(branch.name, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                              if (branch.address != null)
                                Text(
                                  branch.address!,
                                  style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                                ),
                              const SizedBox(height: 4),
                              Row(
                                children: [
                                  const Icon(Icons.access_time_rounded, size: 12, color: AppColors.textMuted),
                                  const SizedBox(width: 3),
                                  Text('${branch.etaMinutes} دقيقة',
                                      style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
                                  const SizedBox(width: 10),
                                  const Icon(Icons.route_rounded, size: 12, color: AppColors.textMuted),
                                  const SizedBox(width: 3),
                                  Text('${branch.roadDistanceKm.toStringAsFixed(1)} كم',
                                      style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
                                ],
                              ),
                            ],
                          ),
                        ),
                        Text(
                          Helpers.formatPrice(branch.deliveryFee),
                          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: AppColors.primaryBlue),
                        ),
                      ],
                    ),
                  ),
                );
              }),
            ],
          ),
        );
      },
    );
  }
}
