// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'cart_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

CartItemResponse _$CartItemResponseFromJson(Map<String, dynamic> json) =>
    CartItemResponse(
      product_id: json['product_id'] as String,
      shop_id: json['shop_id'] as String,
      shop_name: json['shop_name'] as String,
      name: json['name'] as String,
      price: (json['price'] as num).toDouble(),
      quantity: (json['quantity'] as num).toInt(),
      subtotal: (json['subtotal'] as num).toDouble(),
    );

Map<String, dynamic> _$CartItemResponseToJson(CartItemResponse instance) =>
    <String, dynamic>{
      'product_id': instance.product_id,
      'shop_id': instance.shop_id,
      'shop_name': instance.shop_name,
      'name': instance.name,
      'price': instance.price,
      'quantity': instance.quantity,
      'subtotal': instance.subtotal,
    };

CartResponse _$CartResponseFromJson(Map<String, dynamic> json) => CartResponse(
  items: (json['items'] as List<dynamic>)
      .map((e) => CartItemResponse.fromJson(e as Map<String, dynamic>))
      .toList(),
  total: (json['total'] as num).toDouble(),
);

Map<String, dynamic> _$CartResponseToJson(CartResponse instance) =>
    <String, dynamic>{'items': instance.items, 'total': instance.total};

UpdateCartItemRequest _$UpdateCartItemRequestFromJson(
  Map<String, dynamic> json,
) => UpdateCartItemRequest(quantity: (json['quantity'] as num).toInt());

Map<String, dynamic> _$UpdateCartItemRequestToJson(
  UpdateCartItemRequest instance,
) => <String, dynamic>{'quantity': instance.quantity};
