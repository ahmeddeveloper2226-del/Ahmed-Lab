import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/models/category_model.dart';
import '../data/models/subcategory_model.dart';
import '../data/repositories/category_repository.dart';

final categoriesProvider = FutureProvider<List<CategoryResponse>>((ref) async {
  return await ref.watch(categoryRepositoryProvider).getCategories();
});

final subcategoriesForCategoryProvider =
    FutureProvider.family<List<SubcategoryResponse>, String>((ref, categoryId) async {
  return await ref.watch(categoryRepositoryProvider).getSubcategories(categoryId);
});

/// Which subcategory pill is selected on the shops screen for a given
/// category — null means "الكل" (all). Keyed by categoryId so navigating
/// between categories doesn't leak one category's selection into another.
final selectedSubcategoryProvider = StateProvider.family<String?, String>((ref, categoryId) => null);