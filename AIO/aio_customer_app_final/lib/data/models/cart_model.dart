import 'package:json_annotation/json_annotation.dart';

part 'cart_model.g.dart';

@JsonSerializable()
class CartItemResponse {
  final String product_id;
  final String shop_id;
  final String shop_name;
  final String name;
  final double price;
  final int quantity;
  final double subtotal;

  CartItemResponse({
    required this.product_id,
    required this.shop_id,
    required this.shop_name,
    required this.name,
    required this.price,
    required this.quantity,
    required this.subtotal,
  });

  factory CartItemResponse.fromJson(Map<String, dynamic> json) =>
      _$CartItemResponseFromJson(json);
  Map<String, dynamic> toJson() => _$CartItemResponseToJson(this);
}

@JsonSerializable()
class CartResponse {
  final List<CartItemResponse> items;
  final double total;

  CartResponse({required this.items, required this.total});

  factory CartResponse.fromJson(Map<String, dynamic> json) =>
      _$CartResponseFromJson(json);
  Map<String, dynamic> toJson() => _$CartResponseToJson(this);
}

@JsonSerializable()
class UpdateCartItemRequest {
  final int quantity;

  UpdateCartItemRequest({required this.quantity});

  factory UpdateCartItemRequest.fromJson(Map<String, dynamic> json) =>
      _$UpdateCartItemRequestFromJson(json);
  Map<String, dynamic> toJson() => _$UpdateCartItemRequestToJson(this);
}
