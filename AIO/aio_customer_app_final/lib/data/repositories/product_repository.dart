import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/product_model.dart';
import '../models/branch_model.dart';
import '../services/api_service.dart';
import '../../core/constants/api_constants.dart';

final productRepositoryProvider = Provider<ProductRepository>((ref) {
  return ProductRepository(apiService: ref.watch(apiServiceProvider));
});

class ProductRepository {
  final ApiService _api;

  ProductRepository({required ApiService apiService}) : _api = apiService;

  Future<List<ProductResponse>> getProductsForShop(String shopId, {String? subcategoryId}) async {
    final response = await _api.get(
      '${ApiConstants.shops}/$shopId/products',
      queryParameters: subcategoryId != null ? {'subcategory_id': subcategoryId} : null,
    );
    final List<dynamic> data = response.data;
    return data.map((e) => ProductResponse.fromJson(e)).toList();
  }

  Future<ProductResponse> getProductDetail(String productId) async {
    final response = await _api.get('${ApiConstants.products}/$productId');
    return ProductResponse.fromJson(response.data);
  }

  /// Every branch of this product's shop, with per-branch stock of THIS
  /// product and (when lat/lng is given) distance — sorted nearest-with-
  /// stock first by the backend. Empty list means the shop has no
  /// branches (single-location, the overwhelming majority of shops).
  Future<List<ProductBranch>> getProductBranches(String productId, {double? lat, double? lng}) async {
    final response = await _api.get(
      '${ApiConstants.products}/$productId/branches',
      queryParameters: {
        if (lat != null) 'lat': lat,
        if (lng != null) 'lng': lng,
      },
    );
    final List<dynamic> data = response.data;
    return data.map((e) => ProductBranch.fromJson(e)).toList();
  }

  /// AIO Fast Picks — discounted products across every shop/category, for
  /// the two-row sliding rail on the home screen.
  Future<List<ProductResponse>> getFastPicks({int limit = 30}) async {
    final response = await _api.get(
      ApiConstants.productsFastPicks,
      queryParameters: {'limit': limit},
    );
    final List<dynamic> data = response.data;
    return data.map((e) => ProductResponse.fromJson(e)).toList();
  }

  /// AIO Fast Picks scoped to one category — single-row rail above the
  /// shop list on the category screen.
  Future<List<ProductResponse>> getCategoryFastPicks(String categoryId, {int limit = 30}) async {
    final response = await _api.get(
      ApiConstants.categoryFastPicks(categoryId),
      queryParameters: {'limit': limit},
    );
    final List<dynamic> data = response.data;
    return data.map((e) => ProductResponse.fromJson(e)).toList();
  }

  Future<List<ProductSearchResult>> searchProducts({
    required String query,
    required String categoryId,
  }) async {
    final response = await _api.get(
      ApiConstants.search,
      queryParameters: {'q': query, 'category_id': categoryId},
    );
    final List<dynamic> data = response.data;
    return data.map((e) => ProductSearchResult.fromJson(e)).toList();
  }

  /// AIO Exclusive — Complete the Look (clothes only). Backend returns an
  /// empty suggestions list for non-clothes products, so the caller can
  /// always call this unconditionally and just hide the section on empty.
  Future<List<CompleteLookSuggestion>> getCompleteTheLook(String productId) async {
    final response = await _api.get('${ApiConstants.products}/$productId/complete-look');
    final List<dynamic> data = response.data['suggestions'] as List<dynamic>? ?? [];
    return data.map((e) => CompleteLookSuggestion.fromJson(e as Map<String, dynamic>)).toList();
  }

  /// Adds one unit of each given product id in a single call — powers the
  /// "add the complete outfit to your cart with one tap" button.
  Future<CompleteLookAddResult> addCompleteLookToCart(List<String> productIds) async {
    final response = await _api.post(
      '${ApiConstants.products}/complete-look/add-to-cart',
      data: {'product_ids': productIds},
    );
    return CompleteLookAddResult.fromJson(response.data);
  }

  /// AIO Exclusive — Compare Before Buying (2 to 4 products at once).
  Future<List<ProductResponse>> compareProducts(List<String> productIds) async {
    final response = await _api.get(
      '${ApiConstants.products}/compare',
      queryParameters: {'ids': productIds.join(',')},
    );
    final List<dynamic> data = response.data;
    return data.map((e) => ProductResponse.fromJson(e as Map<String, dynamic>)).toList();
  }
}

class CompleteLookSuggestion {
  final String slot;
  final String slotLabel;
  final ProductResponse product;

  CompleteLookSuggestion({required this.slot, required this.slotLabel, required this.product});

  factory CompleteLookSuggestion.fromJson(Map<String, dynamic> json) => CompleteLookSuggestion(
        slot: json['slot'] as String,
        slotLabel: json['slot_label'] as String,
        product: ProductResponse.fromJson(json['product'] as Map<String, dynamic>),
      );
}

class CompleteLookAddResult {
  final List<String> addedIds;
  final List<String> skippedIds;

  CompleteLookAddResult({required this.addedIds, required this.skippedIds});

  factory CompleteLookAddResult.fromJson(Map<String, dynamic> json) => CompleteLookAddResult(
        addedIds: (json['added_ids'] as List<dynamic>? ?? []).map((e) => e as String).toList(),
        skippedIds: (json['skipped_ids'] as List<dynamic>? ?? []).map((e) => e as String).toList(),
      );
}