import 'product_model.dart';

class MealType {
  final String id;
  final String labelAr;
  final String emoji;

  MealType({required this.id, required this.labelAr, required this.emoji});

  factory MealType.fromJson(Map<String, dynamic> json) => MealType(
        id: json['id'] as String,
        labelAr: json['label_ar'] as String,
        emoji: json['emoji'] as String,
      );

  /// Local fallback so the meal-type grid can render instantly without
  /// waiting on a network round trip — matches MEAL_TYPES in
  /// meal_builder_schemas.py exactly; /meal-types is still fetched to stay
  /// the source of truth if it's ever changed server-side only.
  static List<MealType> defaults() => [
        MealType(id: 'healthy', labelAr: 'وجبة صحية', emoji: '🥗'),
        MealType(id: 'family', labelAr: 'وجبة عائلية', emoji: '👨‍👩‍👧‍👦'),
        MealType(id: 'gym', labelAr: 'وجبة الجيم', emoji: '💪'),
        MealType(id: 'kids', labelAr: 'وجبة أطفال', emoji: '🧒'),
        MealType(id: 'high_protein', labelAr: 'وجبة عالية البروتين', emoji: '🍗'),
        MealType(id: 'spicy', labelAr: 'وجبة حارة', emoji: '🌶️'),
      ];
}

class MealBuilderItem {
  final ProductResponse product;
  final int quantity;
  final String reason;

  MealBuilderItem({required this.product, required this.quantity, required this.reason});

  factory MealBuilderItem.fromJson(Map<String, dynamic> json) => MealBuilderItem(
        product: ProductResponse.fromJson(json['product'] as Map<String, dynamic>),
        quantity: (json['quantity'] as num).toInt(),
        reason: json['reason'] as String? ?? '',
      );
}

class BuiltMeal {
  final String mealType;
  final String mealTitle;
  final List<MealBuilderItem> items;
  final double totalPrice;
  final bool hasMenu;

  BuiltMeal({
    required this.mealType,
    required this.mealTitle,
    required this.items,
    required this.totalPrice,
    this.hasMenu = true,
  });

  factory BuiltMeal.fromJson(Map<String, dynamic> json) => BuiltMeal(
        mealType: json['meal_type'] as String,
        mealTitle: json['meal_title'] as String,
        items: (json['items'] as List<dynamic>? ?? [])
            .map((e) => MealBuilderItem.fromJson(e as Map<String, dynamic>))
            .toList(),
        totalPrice: (json['total_price'] as num).toDouble(),
        hasMenu: json['has_menu'] as bool? ?? true,
      );
}

class AddMealToCartResult {
  final int addedCount;
  final int skippedCount;

  AddMealToCartResult({required this.addedCount, required this.skippedCount});

  factory AddMealToCartResult.fromJson(Map<String, dynamic> json) => AddMealToCartResult(
        addedCount: (json['added_count'] as num).toInt(),
        skippedCount: (json['skipped_count'] as num).toInt(),
      );
}

// ─────────────────────────────────────────────────────────────────────────
//  Cross-restaurant meal builder — the free-text version that can mix
//  items from several different restaurants (see meal_builder_router.py:
//  /meal-builder/cross-restaurant).
// ─────────────────────────────────────────────────────────────────────────

class CrossRestaurantMealBuilderItem {
  final ProductResponse product;
  final int quantity;
  final String reason;
  final String shopId;
  final String shopName;

  CrossRestaurantMealBuilderItem({
    required this.product,
    required this.quantity,
    required this.reason,
    required this.shopId,
    required this.shopName,
  });

  factory CrossRestaurantMealBuilderItem.fromJson(Map<String, dynamic> json) => CrossRestaurantMealBuilderItem(
        product: ProductResponse.fromJson(json['product'] as Map<String, dynamic>),
        quantity: (json['quantity'] as num).toInt(),
        reason: json['reason'] as String? ?? '',
        shopId: json['shop_id'] as String,
        shopName: json['shop_name'] as String,
      );
}

class CrossRestaurantBuiltMeal {
  final String mealTitle;
  final List<CrossRestaurantMealBuilderItem> items;
  final double totalPrice;
  final List<String> restaurantsUsed;
  final bool hasResults;

  CrossRestaurantBuiltMeal({
    required this.mealTitle,
    required this.items,
    required this.totalPrice,
    required this.restaurantsUsed,
    this.hasResults = true,
  });

  factory CrossRestaurantBuiltMeal.fromJson(Map<String, dynamic> json) => CrossRestaurantBuiltMeal(
        mealTitle: json['meal_title'] as String,
        items: (json['items'] as List<dynamic>? ?? [])
            .map((e) => CrossRestaurantMealBuilderItem.fromJson(e as Map<String, dynamic>))
            .toList(),
        totalPrice: (json['total_price'] as num).toDouble(),
        restaurantsUsed: (json['restaurants_used'] as List<dynamic>? ?? []).map((e) => e as String).toList(),
        hasResults: json['has_results'] as bool? ?? true,
      );
}
