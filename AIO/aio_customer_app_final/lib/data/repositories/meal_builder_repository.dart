import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/meal_builder_model.dart';
import '../services/api_service.dart';

final mealBuilderRepositoryProvider = Provider<MealBuilderRepository>((ref) {
  return MealBuilderRepository(apiService: ref.watch(apiServiceProvider));
});

class MealBuilderRepository {
  final ApiService _api;
  MealBuilderRepository({required ApiService apiService}) : _api = apiService;

  Future<List<MealType>> getMealTypes() async {
    final response = await _api.get('/meal-types');
    return (response.data as List<dynamic>).map((e) => MealType.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<BuiltMeal> buildMeal({required String shopId, required String mealType, int partySize = 1}) async {
    final response = await _api.post('/shops/$shopId/meal-builder', data: {
      'meal_type': mealType,
      'party_size': partySize,
    });
    return BuiltMeal.fromJson(response.data);
  }

  Future<AddMealToCartResult> addMealToCart({
    required String shopId,
    required List<MealBuilderItem> items,
  }) async {
    final response = await _api.post('/shops/$shopId/meal-builder/add-to-cart', data: {
      'items': items.map((i) => {'product_id': i.product.id, 'quantity': i.quantity}).toList(),
    });
    return AddMealToCartResult.fromJson(response.data);
  }

  // ── Cross-restaurant (free-text, can mix multiple restaurants) ──────────

  Future<CrossRestaurantBuiltMeal> buildCrossRestaurantMeal({required String query, int partySize = 1}) async {
    final response = await _api.post('/meal-builder/cross-restaurant', data: {
      'query': query,
      'party_size': partySize,
    });
    return CrossRestaurantBuiltMeal.fromJson(response.data);
  }

  Future<AddMealToCartResult> addCrossRestaurantMealToCart({
    required List<CrossRestaurantMealBuilderItem> items,
  }) async {
    final response = await _api.post('/meal-builder/cross-restaurant/add-to-cart', data: {
      'items': items.map((i) => {'product_id': i.product.id, 'quantity': i.quantity}).toList(),
    });
    return AddMealToCartResult.fromJson(response.data);
  }
}
