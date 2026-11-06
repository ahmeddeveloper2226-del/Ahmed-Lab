import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/models/order_model.dart';
import '../data/repositories/order_repository.dart';

final ordersProvider = FutureProvider<List<OrderResponse>>((ref) async {
  return await ref.watch(orderRepositoryProvider).getOrders();
});

final orderDetailProvider = FutureProvider.family<OrderResponse, String>((ref, orderId) async {
  return await ref.watch(orderRepositoryProvider).getOrder(orderId);
});
