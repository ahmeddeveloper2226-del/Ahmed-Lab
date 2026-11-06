import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/category_model.dart';
import '../models/subcategory_model.dart';
import '../services/api_service.dart';
import '../../core/constants/api_constants.dart';

final categoryRepositoryProvider = Provider<CategoryRepository>((ref) {
  return CategoryRepository(apiService: ref.watch(apiServiceProvider));
});

class CategoryRepository {
  final ApiService _api;

  CategoryRepository({required ApiService apiService}) : _api = apiService;

  Future<List<CategoryResponse>> getCategories() async {
    final response = await _api.get(ApiConstants.categories);
    final List<dynamic> data = response.data;
    return data.map((e) => CategoryResponse.fromJson(e)).toList();
  }

  /// Ordered by sort_order (the order given when these were seeded), not
  /// alphabetically — for the pill-chip row on the shops screen.
  Future<List<SubcategoryResponse>> getSubcategories(String categoryId) async {
    final response = await _api.get('${ApiConstants.categories}$categoryId/subcategories');
    final List<dynamic> data = response.data;
    return data.map((e) => SubcategoryResponse.fromJson(e)).toList();
  }
}