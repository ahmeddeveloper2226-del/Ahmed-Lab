import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/models/product_model.dart';
import '../data/models/branch_model.dart';
import '../data/repositories/product_repository.dart';
import '../data/services/location_service.dart';

final productsForShopProvider = FutureProvider.family<List<ProductResponse>, String>((ref, shopId) async {
  return await ref.watch(productRepositoryProvider).getProductsForShop(shopId);
});

final productDetailProvider = FutureProvider.family<ProductResponse, String>((ref, productId) async {
  return await ref.watch(productRepositoryProvider).getProductDetail(productId);
});

/// Every branch of this product's shop with per-branch stock + distance,
/// nearest-with-stock first — powers both the "closest branch has it"
/// highlight and the full branch preview list on the product detail
/// screen. Best-effort location: if the user hasn't granted location
/// permission, this still returns every branch's stock status, just
/// without distance/nearest-branch sorting.
final productBranchesProvider = FutureProvider.family.autoDispose<List<ProductBranch>, String>((ref, productId) async {
  final locationService = ref.watch(locationServiceProvider);
  final locationResult = await locationService.getCurrentLocation();
  return await ref.watch(productRepositoryProvider).getProductBranches(
        productId,
        lat: locationResult.isSuccess ? locationResult.lat : null,
        lng: locationResult.isSuccess ? locationResult.lng : null,
      );
});

/// AIO Fast Picks — global, across every category — for the home screen's
/// two-row sliding rail.
final fastPicksProvider = FutureProvider.autoDispose<List<ProductResponse>>((ref) async {
  return await ref.watch(productRepositoryProvider).getFastPicks();
});

/// AIO Fast Picks scoped to a single category — the single-row rail shown
/// above the shop list on that category's screen.
final categoryFastPicksProvider =
    FutureProvider.family.autoDispose<List<ProductResponse>, String>((ref, categoryId) async {
  return await ref.watch(productRepositoryProvider).getCategoryFastPicks(categoryId);
});

final searchProductsProvider = FutureProvider.family<List<ProductSearchResult>, ({String query, String categoryId})>((ref, params) async {
  return await ref.watch(productRepositoryProvider).searchProducts(
    query: params.query,
    categoryId: params.categoryId,
  );
});

/// AIO Exclusive — Complete the Look (clothes only). Keyed by the product
/// currently being viewed; empty list for non-clothes products.
final completeTheLookProvider =
    FutureProvider.family.autoDispose<List<CompleteLookSuggestion>, String>((ref, productId) async {
  return await ref.watch(productRepositoryProvider).getCompleteTheLook(productId);
});

/// AIO Exclusive — Compare Before Buying. Keyed by a comma-joined product
/// id string (not List<String>) so Riverpod's family equality check is a
/// simple string compare rather than list identity, which would otherwise
/// refetch on every rebuild even with the same selection.
final compareProductsProvider = FutureProvider.family.autoDispose<List<ProductResponse>, String>((ref, idsKey) async {
  final ids = idsKey.split(',').where((e) => e.isNotEmpty).toList();
  return await ref.watch(productRepositoryProvider).compareProducts(ids);
});