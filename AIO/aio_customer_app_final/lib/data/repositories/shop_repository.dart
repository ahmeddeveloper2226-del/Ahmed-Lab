import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/shop_model.dart';
import '../models/branch_model.dart';
import '../services/api_service.dart';
import '../../core/constants/api_constants.dart';

final shopRepositoryProvider = Provider<ShopRepository>((ref) {
  return ShopRepository(apiService: ref.watch(apiServiceProvider));
});

class ShopRepository {
  final ApiService _api;

  ShopRepository({required ApiService apiService}) : _api = apiService;

  Future<List<ShopResponse>> getShopsForCategory(String categoryId, {String? subcategoryId}) async {
    final response = await _api.get(
      '/categories/$categoryId/shops',
      queryParameters: subcategoryId != null ? {'subcategory_id': subcategoryId} : null,
    );
    final List<dynamic> data = response.data;
    return data.map((e) => ShopResponse.fromJson(e)).toList();
  }

  Future<ShopResponse> getShopDetail(String shopId) async {
    final response = await _api.get('${ApiConstants.shops}/$shopId');
    return ShopResponse.fromJson(response.data);
  }

  /// categoryId null means "across the whole marketplace" — used for the
  /// home screen's "top rated stores" section and its category filter chips.
  Future<List<ShopResponse>> getTopRatedShops({String? categoryId, int limit = 20}) async {
    final response = await _api.get(
      '${ApiConstants.shops}/top-rated',
      queryParameters: {
        if (categoryId != null) 'category_id': categoryId,
        'limit': limit,
      },
    );
    final List<dynamic> data = response.data;
    return data.map((e) => ShopResponse.fromJson(e)).toList();
  }

  /// Every eligible branch of this shop, city-wide, each quoted with its
  /// own ETA and delivery fee — backs the checkout branch picker (spec:
  /// "the customer selects Store -> Branch"). Empty list means the shop
  /// has no branches (single-location) — the checkout screen falls back
  /// to its existing flow, unaffected.
  Future<List<BranchDeliveryOption>> getBranchDeliveryOptions(
    String shopId, {
    required double lat,
    required double lng,
  }) async {
    final response = await _api.get(
      '${ApiConstants.shops}/$shopId/branches/delivery-options',
      queryParameters: {'lat': lat, 'lng': lng},
    );
    final List<dynamic> data = response.data;
    return data.map((e) => BranchDeliveryOption.fromJson(e)).toList();
  }
}