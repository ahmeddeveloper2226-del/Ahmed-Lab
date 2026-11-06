import 'package:flutter/material.dart';
import '../../core/utils/error_helpers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/animations/custom_animations.dart';
import '../../core/constants/app_constants.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/helpers.dart';
import '../../providers/order_provider.dart';
import 'rate_order_dialog.dart';

class OrderDetailScreen extends ConsumerWidget {
  final String orderId;

  const OrderDetailScreen({super.key, required this.orderId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final orderAsync = ref.watch(orderDetailProvider(orderId));

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('تفاصيل الطلب'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new),
          onPressed: () => context.pop(),
        ),
      ),
      body: orderAsync.when(
        data: (order) {
          final statusColor = AppConstants.orderStatusColors[order.status] ?? AppColors.textMuted;
          final statusLabel = AppConstants.orderStatusLabels[order.status] ?? order.status;

          return ListView(
            physics: const BouncingScrollPhysics(),
            padding: const EdgeInsets.all(20),
            children: [
              // Status card
              FadeSlideIn(
                child: Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [statusColor.withValues(alpha: 0.15), Colors.white],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(24),
                    boxShadow: [
                      BoxShadow(
                        color: statusColor.withValues(alpha: 0.1),
                        blurRadius: 20,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: Column(
                    children: [
                      Container(
                        width: 64,
                        height: 64,
                        decoration: BoxDecoration(
                          color: statusColor.withValues(alpha: 0.2),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          _getStatusIcon(order.status),
                          color: statusColor,
                          size: 32,
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        statusLabel,
                        style: TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.w900,
                          color: statusColor,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'رقم الطلب: #${order.checkout_group_id.substring(0, 8)}',
                        style: const TextStyle(
                          fontSize: 14,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 20),

              if (order.canBeReviewed)
                FadeSlideIn(
                  delay: const Duration(milliseconds: 60),
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(18),
                      boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 12)],
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.star_rounded, color: AppColors.warning, size: 26),
                        const SizedBox(width: 10),
                        const Expanded(
                          child: Text('كيف كانت تجربتك مع هذا الطلب؟', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
                        ),
                        ElevatedButton(
                          onPressed: () async {
                            final submitted = await showDialog<bool>(
                              context: context,
                              builder: (_) => RateOrderDialog(orderId: order.id),
                            );
                            if (submitted == true) {
                              ref.invalidate(orderDetailProvider(orderId));
                            }
                          },
                          style: ElevatedButton.styleFrom(backgroundColor: AppColors.primaryBlue, foregroundColor: Colors.white),
                          child: const Text('قيّم الطلب'),
                        ),
                      ],
                    ),
                  ),
                ),
              if (order.canBeReviewed) const SizedBox(height: 20),

              if (order.hasDriver) ...[
                FadeSlideIn(
                  delay: const Duration(milliseconds: 50),
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      boxShadow: [
                        BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 12, offset: const Offset(0, 4)),
                      ],
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 48, height: 48,
                          decoration: BoxDecoration(gradient: AppGradients.primary, borderRadius: BorderRadius.circular(14)),
                          child: const Icon(Icons.two_wheeler_rounded, color: Colors.white),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('السائق', style: TextStyle(fontSize: 12, color: AppColors.textMuted)),
                              Text(order.driver_name ?? '', style: const TextStyle(fontWeight: FontWeight.w700)),
                            ],
                          ),
                        ),
                        if (order.isActive)
                          IconButton(
                            icon: const Icon(Icons.map_outlined, color: AppColors.primaryBlue),
                            onPressed: () => context.push('/track-order', extra: order),
                          ),
                        IconButton(
                          icon: const Icon(Icons.chat_bubble_outline_rounded, color: AppColors.primaryBlue),
                          onPressed: () => context.push('/chat/${order.id}?name=${Uri.encodeComponent(order.driver_name ?? '')}'),
                        ),
                        IconButton(
                          icon: const Icon(Icons.call_outlined, color: AppColors.primaryBlue),
                          onPressed: () => context.push('/call/${order.id}?name=${Uri.encodeComponent(order.driver_name ?? '')}'),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 20),
              ],

              // Items
              FadeSlideIn(
                delay: const Duration(milliseconds: 100),
                child: Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(24),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'المنتجات',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 16),
                      ...order.items.map((item) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: Row(
                          children: [
                            Container(
                              width: 48,
                              height: 48,
                              decoration: BoxDecoration(
                                color: AppColors.background,
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: const Icon(
                                Icons.shopping_bag_outlined,
                                color: AppColors.primaryBlue,
                                size: 20,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'منتج #${item.product_id.substring(0, 6)}',
                                    style: const TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                  Text(
                                    'الكمية: ${item.quantity}',
                                    style: const TextStyle(
                                      fontSize: 12,
                                      color: AppColors.textMuted,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            Text(
                              Helpers.formatPrice(item.subtotal),
                              style: const TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w700,
                                color: AppColors.primaryBlue,
                              ),
                            ),
                          ],
                        ),
                      )),
                      const Divider(height: 24),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text(
                            'المجموع',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          Text(
                            Helpers.formatPrice(order.total),
                            style: const TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.w900,
                              color: AppColors.primaryBlue,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text(friendlyErrorMessage(err))),
      ),
    );
  }

  IconData _getStatusIcon(String status) {
    switch (status) {
      case 'pending': return Icons.hourglass_empty;
      case 'preparing': return Icons.restaurant;
      case 'out_for_delivery': return Icons.delivery_dining;
      case 'delivered': return Icons.check_circle;
      case 'cancelled': return Icons.cancel;
      default: return Icons.receipt;
    }
  }
}