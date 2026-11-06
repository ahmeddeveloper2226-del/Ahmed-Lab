import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/models/shopping_list_model.dart';
import '../data/repositories/shopping_list_repository.dart';

/// The lists index ('My Lists') — a simple auto-dispose future provider,
/// refreshed via ref.invalidate after any mutation (create/delete list).
final shoppingListsProvider = FutureProvider.autoDispose<List<ShoppingListSummary>>((ref) async {
  final repo = ref.watch(shoppingListRepositoryProvider);
  return repo.getLists();
});

/// One list's full detail (items included), keyed by list id.
final shoppingListDetailProvider =
    FutureProvider.autoDispose.family<ShoppingListDetail, String>((ref, listId) async {
  final repo = ref.watch(shoppingListRepositoryProvider);
  return repo.getList(listId);
});

/// Holds the in-progress AI recipe result so the screen survives a
/// servings-slider change without re-hitting the network — recomputing
/// only happens when the user explicitly re-searches.
class RecipeSearchState {
  final bool isLoading;
  final RecipeParseResult? result;
  final String? error;

  const RecipeSearchState({this.isLoading = false, this.result, this.error});

  RecipeSearchState copyWith({bool? isLoading, RecipeParseResult? result, String? error}) => RecipeSearchState(
        isLoading: isLoading ?? this.isLoading,
        result: result ?? this.result,
        error: error,
      );
}

class RecipeSearchNotifier extends StateNotifier<RecipeSearchState> {
  final ShoppingListRepository _repo;
  RecipeSearchNotifier(this._repo) : super(const RecipeSearchState());

  Future<void> search(String dishName, int servings) async {
    if (dishName.trim().isEmpty) return;
    state = state.copyWith(isLoading: true, error: null);
    try {
      final result = await _repo.parseRecipe(dishName: dishName.trim(), servings: servings);
      state = RecipeSearchState(isLoading: false, result: result);
    } catch (e) {
      state = RecipeSearchState(isLoading: false, error: 'تعذر جلب مكونات هذا الطبق، حاول مرة أخرى.');
    }
  }

  void reset() => state = const RecipeSearchState();
}

final recipeSearchProvider = StateNotifierProvider.autoDispose<RecipeSearchNotifier, RecipeSearchState>((ref) {
  return RecipeSearchNotifier(ref.watch(shoppingListRepositoryProvider));
});
