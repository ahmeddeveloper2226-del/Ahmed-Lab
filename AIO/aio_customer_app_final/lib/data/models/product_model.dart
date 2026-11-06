import 'package:json_annotation/json_annotation.dart';

part 'product_model.g.dart';

@JsonSerializable()
class ProductResponse {
  final String id;
  final String shop_id;
  final String? subcategory_id;
  final String name;
  final double price;
  // Discounted price — null means "not on sale". Populated by the store
  // management panel; drives the AIO Fast Picks rails everywhere.
  final double? sale_price;
  final int stock_quantity;
  final bool in_stock;
  final bool is_on_sale;
  final int? discount_percent;
  // Was missing entirely — same bug as ShopResponse.logo_url: the backend
  // always sent it, this model just never declared the field, so it was
  // discarded during JSON parsing.
  final String? image_url;
  // Free-form per-category details set in the store panel — grocery
  // weight/expiry, clothes size/colour/sleeve, food add-on choices,
  // electronics company/colour, pharmacy dosage/form/etc. Keys match
  // app/constants/product_attributes.py on the backend; see
  // core/constants/product_attributes.dart for the matching UI schema
  // that turns this raw map into pickers on the product screen.
  final Map<String, dynamic>? attributes;

  ProductResponse({
    required this.id,
    required this.shop_id,
    this.subcategory_id,
    required this.name,
    required this.price,
    this.sale_price,
    required this.stock_quantity,
    this.in_stock = false,
    this.is_on_sale = false,
    this.discount_percent,
    this.image_url,
    this.attributes,
  });

  factory ProductResponse.fromJson(Map<String, dynamic> json) =>
      _$ProductResponseFromJson(json);
  Map<String, dynamic> toJson() => _$ProductResponseToJson(this);
}

@JsonSerializable()
class ProductCreateRequest {
  final String id;
  final String name;
  final double price;
  final double? sale_price;
  final int stock_quantity;

  ProductCreateRequest({
    required this.id,
    required this.name,
    required this.price,
    this.sale_price,
    this.stock_quantity = 0,
  });

  factory ProductCreateRequest.fromJson(Map<String, dynamic> json) =>
      _$ProductCreateRequestFromJson(json);
  Map<String, dynamic> toJson() => _$ProductCreateRequestToJson(this);
}

@JsonSerializable()
class ProductSearchResult {
  final String id;
  final String shop_id;
  final String shop_name;
  final String category_id;
  final String name;
  final double price;
  final int stock_quantity;
  final bool in_stock;
  final String? image_url;

  ProductSearchResult({
    required this.id,
    required this.shop_id,
    required this.shop_name,
    required this.category_id,
    required this.name,
    required this.price,
    required this.stock_quantity,
    required this.in_stock,
    this.image_url,
  });

  factory ProductSearchResult.fromJson(Map<String, dynamic> json) =>
      _$ProductSearchResultFromJson(json);
  Map<String, dynamic> toJson() => _$ProductSearchResultToJson(this);
}