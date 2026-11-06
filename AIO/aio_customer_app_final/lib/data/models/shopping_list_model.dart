class ShoppingListItem {
  final String id;
  final String name;
  final double quantity;
  final String? unit;
  final bool isChecked;
  final String? productId;

  ShoppingListItem({
    required this.id,
    required this.name,
    required this.quantity,
    this.unit,
    required this.isChecked,
    this.productId,
  });

  factory ShoppingListItem.fromJson(Map<String, dynamic> json) => ShoppingListItem(
        id: json['id'] as String,
        name: json['name'] as String,
        quantity: (json['quantity'] as num).toDouble(),
        unit: json['unit'] as String?,
        isChecked: json['is_checked'] as bool? ?? false,
        productId: json['product_id'] as String?,
      );
}

class ShoppingListSummary {
  final String id;
  final String name;
  final String occasion;
  final int itemCount;
  final int checkedCount;
  final DateTime updatedAt;

  ShoppingListSummary({
    required this.id,
    required this.name,
    required this.occasion,
    required this.itemCount,
    required this.checkedCount,
    required this.updatedAt,
  });

  factory ShoppingListSummary.fromJson(Map<String, dynamic> json) => ShoppingListSummary(
        id: json['id'] as String,
        name: json['name'] as String,
        occasion: json['occasion'] as String,
        itemCount: (json['item_count'] as num).toInt(),
        checkedCount: (json['checked_count'] as num).toInt(),
        updatedAt: DateTime.parse(json['updated_at'] as String),
      );
}

class ShoppingListDetail {
  final String id;
  final String name;
  final String occasion;
  final String shareCode;
  final List<ShoppingListItem> items;

  ShoppingListDetail({
    required this.id,
    required this.name,
    required this.occasion,
    required this.shareCode,
    required this.items,
  });

  factory ShoppingListDetail.fromJson(Map<String, dynamic> json) => ShoppingListDetail(
        id: json['id'] as String,
        name: json['name'] as String,
        occasion: json['occasion'] as String,
        shareCode: json['share_code'] as String,
        items: (json['items'] as List<dynamic>? ?? [])
            .map((e) => ShoppingListItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}

class AddToCartResult {
  final int addedCount;
  final int skippedCount;
  final List<String> skippedNames;

  AddToCartResult({required this.addedCount, required this.skippedCount, required this.skippedNames});

  factory AddToCartResult.fromJson(Map<String, dynamic> json) => AddToCartResult(
        addedCount: (json['added_count'] as num).toInt(),
        skippedCount: (json['skipped_count'] as num).toInt(),
        skippedNames: (json['skipped_names'] as List<dynamic>? ?? []).map((e) => e as String).toList(),
      );
}

/// Preset "occasion" tags shown as quick-pick chips when creating a list —
/// purely cosmetic (icon + label), matches ShoppingList.occasion server-side.
class ListOccasion {
  final String id;
  final String label;
  final String emoji;
  const ListOccasion(this.id, this.label, this.emoji);

  static const List<ListOccasion> all = [
    ListOccasion('weekly', 'أسبوعية', '🗓️'),
    ListOccasion('monthly', 'شهرية', '📅'),
    ListOccasion('ramadan', 'رمضان', '🌙'),
    ListOccasion('family_gathering', 'تجمع عائلي', '👨‍👩‍👧‍👦'),
    ListOccasion('bbq', 'شواء', '🍢'),
    ListOccasion('diet_plan', 'نظام غذائي', '🥗'),
    ListOccasion('custom', 'مخصصة', '📝'),
  ];

  static ListOccasion byId(String id) => all.firstWhere((o) => o.id == id, orElse: () => all.last);
}

class RecipeIngredientMatch {
  final String ingredientName;
  final String quantityLabel;
  final String? productId;
  final String? productName;
  final String? shopName;
  final double? price;
  final bool matched;

  RecipeIngredientMatch({
    required this.ingredientName,
    required this.quantityLabel,
    this.productId,
    this.productName,
    this.shopName,
    this.price,
    required this.matched,
  });

  factory RecipeIngredientMatch.fromJson(Map<String, dynamic> json) => RecipeIngredientMatch(
        ingredientName: json['ingredient_name'] as String,
        quantityLabel: json['quantity_label'] as String,
        productId: json['product_id'] as String?,
        productName: json['product_name'] as String?,
        shopName: json['shop_name'] as String?,
        price: (json['price'] as num?)?.toDouble(),
        matched: json['matched'] as bool,
      );
}

class RecipeParseResult {
  final String dishName;
  final int servings;
  final List<RecipeIngredientMatch> ingredients;

  RecipeParseResult({required this.dishName, required this.servings, required this.ingredients});

  factory RecipeParseResult.fromJson(Map<String, dynamic> json) => RecipeParseResult(
        dishName: json['dish_name'] as String,
        servings: (json['servings'] as num).toInt(),
        ingredients: (json['ingredients'] as List<dynamic>? ?? [])
            .map((e) => RecipeIngredientMatch.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
