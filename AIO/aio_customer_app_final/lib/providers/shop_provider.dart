import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/models/shop_model.dart';
import '../data/models/branch_model.dart';
import '../data/repositories/shop_repository.dart';

final shopsForCategoryProvider = FutureProvider.family<List<ShopResponse>, String>((ref, categoryId) async {
  return await ref.watch(shopRepositoryProvider).getShopsForCategory(categoryId);
});

final shopDetailProvider = FutureProvider.family<ShopResponse, String>((ref, shopId) async {
  return await ref.watch(shopRepositoryProvider).getShopDetail(shopId);
});

/// Selected category chip on the home screen's "top rated stores" section —
/// null means "الكل" (all categories, no filter).
final topRatedCategoryFilterProvider = StateProvider<String?>((ref) => null);

final topRatedShopsProvider = FutureProvider.autoDispose<List<ShopResponse>>((ref) async {
  final categoryId = ref.watch(topRatedCategoryFilterProvider);
  return await ref.watch(shopRepositoryProvider).getTopRatedShops(categoryId: categoryId);
});

/// Family key for [branchDeliveryOptionsProvider] — a shop_id plus the
/// customer's location, since the ETA/fee quote is meaningless without it.
class BranchOptionsQuery {
  final String shopId;
  final double lat;
  final double lng;
  const BranchOptionsQuery({required this.shopId, required this.lat, required this.lng});

  @override
  bool operator ==(Object other) =>
      other is BranchOptionsQuery && other.shopId == shopId && other.lat == lat && other.lng == lng;

  @override
  int get hashCode => Object.hash(shopId, lat, lng);
}

/// Every eligible branch for a shop, city-wide, each with its own ETA and
/// delivery fee (spec 1.1-1.4) — powers the checkout branch picker. An
/// empty list means the shop has no branches; the checkout screen treats
/// that exactly like today's single-location flow.
final branchDeliveryOptionsProvider =
    FutureProvider.family.autoDispose<List<BranchDeliveryOption>, BranchOptionsQuery>((ref, query) async {
  return await ref.watch(shopRepositoryProvider).getBranchDeliveryOptions(
        query.shopId,
        lat: query.lat,
        lng: query.lng,
      );
});