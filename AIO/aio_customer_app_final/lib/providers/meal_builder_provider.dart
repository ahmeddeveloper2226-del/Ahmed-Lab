import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/models/meal_builder_model.dart';
import '../data/repositories/meal_builder_repository.dart';

final mealTypesProvider = FutureProvider.autoDispose<List<MealType>>((ref) async {
  try {
    return await ref.watch(mealBuilderRepositoryProvider).getMealTypes();
  } catch (_) {
    return MealType.defaults(); // network hiccup shouldn't block the grid from rendering
  }
});

class MealBuilderState {
  final bool isLoading;
  final BuiltMeal? meal;
  final String? error;
  const MealBuilderState({this.isLoading = false, this.meal, this.error});
}

class MealBuilderNotifier extends StateNotifier<MealBuilderState> {
  final MealBuilderRepository _repo;
  final String shopId;

  MealBuilderNotifier(this._repo, this.shopId) : super(const MealBuilderState());

  Future<void> build(String mealType, {int partySize = 1}) async {
    state = const MealBuilderState(isLoading: true);
    try {
      final meal = await _repo.buildMeal(shopId: shopId, mealType: mealType, partySize: partySize);
      if (!meal.hasMenu) {
        state = const MealBuilderState(error: 'لا يوجد طعام في هذا المطعم لبناء وجبة منه.');
      } else if (meal.items.isEmpty) {
        state = const MealBuilderState(error: 'لم نجد أصنافًا مناسبة لهذا النوع في قائمة هذا المطعم حاليًا.');
      } else {
        state = MealBuilderState(meal: meal);
      }
    } catch (e) {
      state = const MealBuilderState(error: 'تعذر بناء الوجبة الآن، حاول مرة أخرى.');
    }
  }

  void reset() => state = const MealBuilderState();
}

final mealBuilderProvider =
    StateNotifierProvider.autoDispose.family<MealBuilderNotifier, MealBuilderState, String>((ref, shopId) {
  return MealBuilderNotifier(ref.watch(mealBuilderRepositoryProvider), shopId);
});

// ─────────────────────────────────────────────────────────────────────────
//  Cross-restaurant (free-text) meal builder state
// ─────────────────────────────────────────────────────────────────────────

class CrossRestaurantMealBuilderState {
  final bool isLoading;
  final CrossRestaurantBuiltMeal? meal;
  final String? error;
  const CrossRestaurantMealBuilderState({this.isLoading = false, this.meal, this.error});
}

class CrossRestaurantMealBuilderNotifier extends StateNotifier<CrossRestaurantMealBuilderState> {
  final MealBuilderRepository _repo;

  CrossRestaurantMealBuilderNotifier(this._repo) : super(const CrossRestaurantMealBuilderState());

  Future<void> build(String query, {int partySize = 1}) async {
    state = const CrossRestaurantMealBuilderState(isLoading: true);
    try {
      final meal = await _repo.buildCrossRestaurantMeal(query: query, partySize: partySize);
      if (!meal.hasResults) {
        state = const CrossRestaurantMealBuilderState(error: 'مفيش مطاعم بتقدم حاجة تناسب طلبك حاليًا.');
      } else if (meal.items.isEmpty) {
        state = const CrossRestaurantMealBuilderState(error: 'لم نجد أصنافًا مناسبة لطلبك، جرّب تصفه بشكل مختلف.');
      } else {
        state = CrossRestaurantMealBuilderState(meal: meal);
      }
    } catch (e) {
      state = const CrossRestaurantMealBuilderState(error: 'تعذر بناء الوجبة الآن، حاول مرة أخرى.');
    }
  }

  void reset() => state = const CrossRestaurantMealBuilderState();
}

final crossRestaurantMealBuilderProvider =
    StateNotifierProvider.autoDispose<CrossRestaurantMealBuilderNotifier, CrossRestaurantMealBuilderState>((ref) {
  return CrossRestaurantMealBuilderNotifier(ref.watch(mealBuilderRepositoryProvider));
});
