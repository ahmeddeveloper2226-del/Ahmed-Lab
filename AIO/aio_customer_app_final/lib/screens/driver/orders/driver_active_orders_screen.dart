import 'package:flutter/material.dart';
import '../../../core/utils/error_helpers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/animations/custom_animations.dart';
import '../../../data/models/driver_order_model.dart';
import '../../../providers/driver_provider.dart';

class DriverActiveOrdersScreen extends ConsumerWidget {
  const DriverActiveOrdersScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ordersAsync = ref.watch(driverActiveOrdersProvider);

    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async => ref.invalidate(driverActiveOrdersProvider),
          child: CustomScrollView(
            slivers: [
              const SliverPadding(
                padding: EdgeInsets.all(20),
                sliver: SliverToBoxAdapter(
                  child: FadeSlideIn(
                    child: Text(
                      'طلباتي النشطة',
                      style: TextStyle(fontSize: 24, fontWeight: FontWeight.w800),
                    ),
                  ),
                ),
              ),
              ordersAsync.when(
                data: (orders) {
                  if (orders.isEmpty) {
                    return SliverToBoxAdapter(
                      child: Padding(
                        padding: const EdgeInsets.all(40),
                        child: Column(
                          children: [
                            Icon(Icons.local_shipping_outlined, size: 56, color: AppColors.textMuted.withValues(alpha: 0.4)),
                            const SizedBox(height: 16),
                            const Text('لا توجد طلبات نشطة حاليًا', style: TextStyle(color: AppColors.textMuted)),
                          ],
                        ),
                      ),
                    );
                  }
                  return SliverPadding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    sliver: SliverList(
                      delegate: SliverChildBuilderDelegate(
                        (context, index) => Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: _ActiveOrderCard(order: orders[index]),
                        ),
                        childCount: orders.length,
                      ),
                    ),
                  );
                },
                loading: () => const SliverToBoxAdapter(
                  child: Padding(
                    padding: EdgeInsets.all(40),
                    child: Center(child: CircularProgressIndicator(color: AppColors.primaryBlue)),
                  ),
                ),
                error: (e, st) => SliverToBoxAdapter(
                  child: Padding(
                    padding: const EdgeInsets.all(40),
                    child: Text('تعذر تحميل الطلبات: ${friendlyErrorMessage(e)}', style: const TextStyle(color: AppColors.error)),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ActiveOrderCard extends StatelessWidget {
  final DriverOrderModel order;
  const _ActiveOrderCard({required this.order});

  @override
  Widget build(BuildContext context) {
    final isHeadingToShop = order.isHeadingToShop;
    final stage = order.deliveryStage;
    final label = stage?.arabicLabel ?? (isHeadingToShop ? 'في الطريق إلى المتجر' : 'في الطريق إلى العميل');
    // Post-pickup stages (pickedUp/inTransit/arrivedAtCustomer) are visually
    // "success" (green, heading to customer); everything before pickup is
    // "warning" (amber, still at/heading to the branch) — matches the
    // original two-color scheme, just driven by the finer-grained stage
    // when one exists.
    final isPastPickup = stage != null
        ? (stage == DeliveryStage.pickedUp || stage == DeliveryStage.inTransit || stage == DeliveryStage.arrivedAtCustomer)
        : !isHeadingToShop;
    return GestureDetector(
      onTap: () => context.push('/driver/order/${order.id}'),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 12, offset: const Offset(0, 4)),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 48, height: 48,
              decoration: BoxDecoration(
                color: (isPastPickup ? AppColors.success : AppColors.warning).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(
                isPastPickup ? Icons.two_wheeler_rounded : Icons.storefront_rounded,
                color: isPastPickup ? AppColors.success : AppColors.warning,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(order.shopName, style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text(
                    label,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: isPastPickup ? AppColors.success : AppColors.warning,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: AppColors.textMuted),
          ],
        ),
      ),
    );
  }
}