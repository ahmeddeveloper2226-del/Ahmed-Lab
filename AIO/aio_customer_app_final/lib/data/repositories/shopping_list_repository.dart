import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/shopping_list_model.dart';
import '../services/api_service.dart';

final shoppingListRepositoryProvider = Provider<ShoppingListRepository>((ref) {
  return ShoppingListRepository(apiService: ref.watch(apiServiceProvider));
});

class ShoppingListRepository {
  final ApiService _api;
  static const _base = '/shopping-lists/';

  ShoppingListRepository({required ApiService apiService}) : _api = apiService;

  Future<List<ShoppingListSummary>> getLists() async {
    final response = await _api.get(_base);
    return (response.data as List<dynamic>)
        .map((e) => ShoppingListSummary.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<ShoppingListDetail> createList({
    required String name,
    required String occasion,
    List<Map<String, dynamic>> items = const [],
  }) async {
    final response = await _api.post(_base, data: {
      'name': name,
      'occasion': occasion,
      'items': items,
    });
    return ShoppingListDetail.fromJson(response.data);
  }

  Future<ShoppingListDetail> getList(String listId) async {
    final response = await _api.get('$_base$listId');
    return ShoppingListDetail.fromJson(response.data);
  }

  Future<void> deleteList(String listId) async {
    await _api.delete('$_base$listId');
  }

  Future<ShoppingListDetail> addItem(String listId, {required String name, double quantity = 1, String? unit}) async {
    final response = await _api.post('$_base$listId/items', data: {
      'name': name,
      'quantity': quantity,
      if (unit != null) 'unit': unit,
    });
    return ShoppingListDetail.fromJson(response.data);
  }

  Future<ShoppingListDetail> toggleItem(String listId, String itemId, bool isChecked) async {
    final response = await _api.patch('$_base$listId/items/$itemId', data: {'is_checked': isChecked});
    return ShoppingListDetail.fromJson(response.data);
  }

  Future<ShoppingListDetail> deleteItem(String listId, String itemId) async {
    final response = await _api.delete('$_base$listId/items/$itemId');
    return ShoppingListDetail.fromJson(response.data);
  }

  Future<ShoppingListDetail> copySharedList(String shareCode) async {
    final response = await _api.post('${_base}shared/$shareCode/copy');
    return ShoppingListDetail.fromJson(response.data);
  }

  Future<AddToCartResult> addListToCart(String listId) async {
    final response = await _api.post('$_base$listId/add-to-cart');
    return AddToCartResult.fromJson(response.data);
  }

  Future<RecipeParseResult> parseRecipe({required String dishName, required int servings}) async {
    final response = await _api.post('${_base}recipe/parse', data: {
      'dish_name': dishName,
      'servings': servings,
    });
    return RecipeParseResult.fromJson(response.data);
  }

  Future<AddToCartResult> addRecipeToCart(List<String> productIds) async {
    final response = await _api.post('${_base}recipe/add-to-cart', data: {'product_ids': productIds});
    return AddToCartResult.fromJson(response.data);
  }
}
