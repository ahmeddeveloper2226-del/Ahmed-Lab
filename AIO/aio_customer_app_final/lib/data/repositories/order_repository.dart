import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/order_model.dart';
import '../services/api_service.dart';
import '../../core/constants/api_constants.dart';

final orderRepositoryProvider = Provider<OrderRepository>((ref) {
  return OrderRepository(apiService: ref.watch(apiServiceProvider));
});

class OrderRepository {
  final ApiService _api;

  OrderRepository({required ApiService apiService}) : _api = apiService;

  Future<List<OrderResponse>> getOrders() async {
    final response = await _api.get(ApiConstants.orders);
    final List<dynamic> data = response.data;
    return data.map((e) => OrderResponse.fromJson(e)).toList();
  }

  Future<OrderResponse> getOrder(String orderId) async {
    final response = await _api.get('${ApiConstants.orders}/$orderId');
    return OrderResponse.fromJson(response.data);
  }

  Future<CheckoutResponse> checkout(
    String addressId,
    Map<String, dynamic> billingData, {
    Map<String, String>? branchSelections,
  }) async {
    final response = await _api.post(
      ApiConstants.checkout,
      data: CheckoutRequest(
        address_id: addressId,
        billing_data: billingData,
        branch_selections: branchSelections,
      ).toJson(),
    );
    return CheckoutResponse.fromJson(response.data);
  }

  Future<void> submitReview(String orderId, {required int rating, String? comment}) async {
    await _api.post(
      '${ApiConstants.orders}/$orderId/review',
      data: {'rating': rating, 'comment': comment},
    );
  }
}
