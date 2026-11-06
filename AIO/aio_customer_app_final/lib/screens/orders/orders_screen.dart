import 'package:flutter/material.dart';
import '../../core/utils/error_helpers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_staggered_animations/flutter_staggered_animations.dart';
import 'package:go_router/go_router.dart';
import '../../core/animations/custom_animations.dart';
import '../../core/constants/app_constants.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/helpers.dart';
import '../../providers/order_provider.dart';
import '../../widgets/common/loading_shimmer.dart';

class OrdersScreen extends ConsumerWidget {
  const OrdersScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ordersAsync = ref.watch(ordersProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      body: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          SliverToBoxAdapter(
            child: Container(
              padding: const EdgeInsets.fromLTRB(24, 60, 24, 24),
              decoration: const BoxDecoration(
                gradient: AppGradients.primary,
                borderRadius: BorderRadius.vertical(
                  bottom: Radius.circular(32),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'طلباتي',
                    style: TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.w900,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'تتبع طلباتك الحالية واطلع على سجل المشتريات',
                    style: TextStyle(
                      fontSize: 14,
                      color: Colors.white.withValues(alpha: 0.8),
                    ),
                  ),
                ],
              ),
            ),
          ),

          SliverPadding(
            padding: const EdgeInsets.all(20),
            sliver: ordersAsync.when(
              data: (orders) {
                if (orders.isEmpty) {
                  return SliverToBoxAdapter(
                    child: FadeSlideIn(
                      child: Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const SizedBox(height: 60),
                            Container(
                              width: 140,
                              height: 140,
                              decoration: BoxDecoration(
                                gradient: LinearGradient(
                                  colors: [
                                    AppColors.primaryBlue.withValues(alpha: 0.1),
                                    AppColors.accentCyan.withValues(alpha: 0.05),
                                  ],
                                ),
                                shape: BoxShape.circle,
                              ),
                              child: Icon(
                                Icons.receipt_long_outlined,
                                size: 56,
                                color: AppColors.primaryBlue.withValues(alpha: 0.4),
                              ),
                            ),
                            const SizedBox(height: 24),
                            const Text(
                              'لا توجد طلبات بعد',
                              style: TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 8),
                            const Text(
                              'اطلب الآن واستمتع بتجربة تسوق رائعة',
                              style: TextStyle(
                                fontSize: 14,
                                color: AppColors.textMuted,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                }

                // Separate active and past orders
                final activeOrders = orders.where((o) =>
                  o.status == 'preparing' || o.status == 'out_for_delivery').toList();
                final pastOrders = orders.where((o) =>
                  o.status == 'delivered' || o.status == 'cancelled').toList();

                return SliverList(
                  delegate: SliverChildListDelegate([
                    // Active orders section
                    if (activeOrders.isNotEmpty) ...[
                      const Padding(
                        padding: EdgeInsets.only(bottom: 12, right: 4),
                        child: Row(
                          children: [
                            PulseAnimation(
                              child: Icon(
                                Icons.circle,
                                color: AppColors.success,
                                size: 10,
                              ),
                            ),
                            SizedBox(width: 8),
                            Text(
                              'طلبات نشطة',
                              style: TextStyle(
                                fontSize: 18,
                                fontWeight: FontWeight.w800,
                                color: AppColors.textPrimary,
                              ),
                            ),
                          ],
                        ),
                      ),
                      ...activeOrders.asMap().entries.map((entry) {
                        final index = entry.key;
                        final order = entry.value;
                        return AnimationConfiguration.staggeredList(
                          position: index,
                          duration: const Duration(milliseconds: 400),
                          child: SlideAnimation(
                            verticalOffset: 30,
                            child: FadeInAnimation(
                              child: _OrderCard(order: order, isActive: true),
                            ),
                          ),
                        );
                      }),
                      const SizedBox(height: 24),
                    ],

                    // Past orders section
                    if (pastOrders.isNotEmpty) ...[
                      const Padding(
                        padding: EdgeInsets.only(bottom: 12, right: 4),
                        child: Text(
                          'سجل الطلبات',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w800,
                            color: AppColors.textPrimary,
                          ),
                        ),
                      ),
                      ...pastOrders.asMap().entries.map((entry) {
                        final index = entry.key + activeOrders.length;
                        final order = entry.value;
                        return AnimationConfiguration.staggeredList(
                          position: index,
                          duration: const Duration(milliseconds: 400),
                          child: SlideAnimation(
                            verticalOffset: 30,
                            child: FadeInAnimation(
                              child: _OrderCard(order: order, isActive: false),
                            ),
                          ),
                        );
                      }),
                    ],
                  ]),
                );
              },
              loading: () => SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) => const Padding(
                    padding: EdgeInsets.only(bottom: 12),
                    child: ShopShimmerCard(),
                  ),
                  childCount: 4,
                ),
              ),
              error: (err, _) => SliverToBoxAdapter(
                child: Center(child: Text(friendlyErrorMessage(err))),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _OrderCard extends StatelessWidget {
  final dynamic order;
  final bool isActive;

  const _OrderCard({required this.order, required this.isActive});

  @override
  Widget build(BuildContext context) {
    final statusColor = AppConstants.orderStatusColors[order.status] ?? AppColors.textMuted;
    final statusLabel = AppConstants.orderStatusLabels[order.status] ?? order.status;

    return GestureDetector(
      onTap: () => context.push('/order/${order.id}'),
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(24),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.04),
              blurRadius: 20,
              offset: const Offset(0, 4),
            ),
          ],
          border: isActive
              ? Border.all(color: statusColor.withValues(alpha: 0.3), width: 1.5)
              : null,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: statusColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    statusLabel,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                      color: statusColor,
                    ),
                  ),
                ),
                Text(
                  '#${order.checkout_group_id.substring(0, 8)}',
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.textMuted,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: AppColors.background,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: const Icon(
                    Icons.store_rounded,
                    color: AppColors.primaryBlue,
                    size: 20,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'طلب من متجر',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '${order.items.length} منتجات',
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
                Text(
                  Helpers.formatPrice(order.total),
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w900,
                    color: AppColors.primaryBlue,
                  ),
                ),
              ],
            ),
            if (isActive) ...[
              const SizedBox(height: 16),
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: LinearProgressIndicator(
                  value: order.status == 'out_for_delivery' ? 0.7 : 0.4,
                  backgroundColor: AppColors.divider,
                  valueColor: AlwaysStoppedAnimation<Color>(statusColor),
                  minHeight: 6,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
