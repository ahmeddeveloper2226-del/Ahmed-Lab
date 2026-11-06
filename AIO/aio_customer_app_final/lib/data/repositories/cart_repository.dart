import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/cart_model.dart';
import '../services/api_service.dart';
import '../../core/constants/api_constants.dart';

final cartRepositoryProvider = Provider<CartRepository>((ref) {
  return CartRepository(apiService: ref.watch(apiServiceProvider));
});

class CartRepository {
  final ApiService _api;

  CartRepository({required ApiService apiService}) : _api = apiService;

  Future<CartResponse> getCart() async {
    final response = await _api.get(ApiConstants.cart);
    return CartResponse.fromJson(response.data);
  }

  Future<CartResponse> updateCartItem(String productId, int quantity) async {
    final response = await _api.put(
      '${ApiConstants.cart}items/$productId',
      data: UpdateCartItemRequest(quantity: quantity).toJson(),
    );
    return CartResponse.fromJson(response.data);
  }

  Future<CartResponse> removeCartItem(String productId) async {
    final response = await _api.delete('${ApiConstants.cart}items/$productId');
    return CartResponse.fromJson(response.data);
  }

  Future<void> clearCart() async {
    await _api.delete(ApiConstants.cart);
  }
}
