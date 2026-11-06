import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/models/cart_model.dart';
import '../data/repositories/cart_repository.dart';

final cartProvider = StateNotifierProvider<CartNotifier, AsyncValue<CartResponse>>((ref) {
  return CartNotifier(repo: ref.watch(cartRepositoryProvider));
});

class CartNotifier extends StateNotifier<AsyncValue<CartResponse>> {
  final CartRepository _repo;

  CartNotifier({required CartRepository repo})
      : _repo = repo,
        super(const AsyncValue.loading()) {
    loadCart();
  }

  Future<void> loadCart() async {
    try {
      final cart = await _repo.getCart();
      state = AsyncValue.data(cart);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> updateItem(String productId, int quantity) async {
    try {
      final cart = await _repo.updateCartItem(productId, quantity);
      state = AsyncValue.data(cart);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> removeItem(String productId) async {
    try {
      final cart = await _repo.removeCartItem(productId);
      state = AsyncValue.data(cart);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> clearCart() async {
    try {
      await _repo.clearCart();
      state = AsyncValue.data(CartResponse(items: [], total: 0));
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }
}

final cartItemCountProvider = Provider<int>((ref) {
  final cartState = ref.watch(cartProvider);
  return cartState.when(
    data: (cart) => cart.items.fold(0, (sum, item) => sum + item.quantity),
    loading: () => 0,
    error: (_, __) => 0,
  );
});
