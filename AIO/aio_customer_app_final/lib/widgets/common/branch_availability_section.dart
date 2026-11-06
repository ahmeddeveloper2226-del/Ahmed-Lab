import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../data/models/branch_model.dart';
import '../../providers/product_provider.dart';

/// Shown on the product detail screen. Renders nothing for a
/// single-location shop (the `branches` list comes back empty — see
/// products_router.py's GET /products/{id}/branches), so this is a
/// silent no-op for the overwhelming majority of products.
///
/// For a shop that DOES have branches: highlights the nearest branch
/// that actually has this product in stock (already sorted first by the
/// backend), and lets the customer expand to preview every branch and
/// its stock status — not just the one the app picked for them.
class BranchAvailabilitySection extends ConsumerStatefulWidget {
  final String productId;
  const BranchAvailabilitySection({super.key, required this.productId});

  @override
  ConsumerState<BranchAvailabilitySection> createState() => _BranchAvailabilitySectionState();
}

class _BranchAvailabilitySectionState extends ConsumerState<BranchAvailabilitySection> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final branchesAsync = ref.watch(productBranchesProvider(widget.productId));

    return branchesAsync.when(
      loading: () => const SizedBox.shrink(),
      error: (e, _) => const SizedBox.shrink(), // silent — this is a nice-to-have, never blocks viewing the product
      data: (branches) {
        if (branches.isEmpty) return const SizedBox.shrink(); // single-location shop — nothing to show

        final nearestWithStock = branches.firstWhere((b) => b.inStock, orElse: () => branches.first);

        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppColors.divider),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      nearestWithStock.inStock ? Icons.storefront_rounded : Icons.storefront_outlined,
                      size: 20,
                      color: nearestWithStock.inStock ? AppColors.success : AppColors.textMuted,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            nearestWithStock.inStock ? 'متاح في: ${nearestWithStock.name}' : 'غير متوفر في أقرب فرع الآن',
                            style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5),
                          ),
                          if (nearestWithStock.distanceKm != null)
                            Text(
                              'يبعد ${nearestWithStock.distanceKm!.toStringAsFixed(1)} كم عنك',
                              style: const TextStyle(fontSize: 11.5, color: AppColors.textSecondary),
                            ),
                        ],
                      ),
                    ),
                    TextButton(
                      onPressed: () => setState(() => _expanded = !_expanded),
                      child: Text(_expanded ? 'إخفاء الفروع' : 'كل الفروع (${branches.length})'),
                    ),
                  ],
                ),
                if (_expanded) ...[
                  const Divider(height: 20),
                  ...branches.map((b) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        child: Row(
                          children: [
                            Icon(
                              b.inStock ? Icons.check_circle_rounded : Icons.cancel_rounded,
                              size: 16,
                              color: b.inStock ? AppColors.success : AppColors.error,
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(b.name, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                                  if (b.address != null)
                                    Text(b.address!, style: const TextStyle(fontSize: 11, color: AppColors.textSecondary)),
                                ],
                              ),
                            ),
                            if (b.distanceKm != null)
                              Text('${b.distanceKm!.toStringAsFixed(1)} كم', style: const TextStyle(fontSize: 11.5, color: AppColors.textSecondary)),
                          ],
                        ),
                      )),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}
