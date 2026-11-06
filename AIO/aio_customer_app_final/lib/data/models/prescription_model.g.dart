// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'prescription_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

PrescriptionItemResponse _$PrescriptionItemResponseFromJson(
  Map<String, dynamic> json,
) => PrescriptionItemResponse(
  id: json['id'] as String,
  product_id: json['product_id'] as String,
  name: json['name'] as String,
  price: (json['price'] as num).toDouble(),
  quantity: (json['quantity'] as num).toInt(),
  included: json['included'] as bool,
);

Map<String, dynamic> _$PrescriptionItemResponseToJson(
  PrescriptionItemResponse instance,
) => <String, dynamic>{
  'id': instance.id,
  'product_id': instance.product_id,
  'name': instance.name,
  'price': instance.price,
  'quantity': instance.quantity,
  'included': instance.included,
};

PrescriptionResponse _$PrescriptionResponseFromJson(
  Map<String, dynamic> json,
) => PrescriptionResponse(
  id: json['id'] as String,
  shop_id: json['shop_id'] as String,
  shop_name: json['shop_name'] as String,
  image_url: json['image_url'] as String,
  status: json['status'] as String,
  submitted_at: json['submitted_at'] == null
      ? null
      : DateTime.parse(json['submitted_at'] as String),
  created_at: DateTime.parse(json['created_at'] as String),
  items: (json['items'] as List<dynamic>)
      .map((e) => PrescriptionItemResponse.fromJson(e as Map<String, dynamic>))
      .toList(),
);

Map<String, dynamic> _$PrescriptionResponseToJson(
  PrescriptionResponse instance,
) => <String, dynamic>{
  'id': instance.id,
  'shop_id': instance.shop_id,
  'shop_name': instance.shop_name,
  'image_url': instance.image_url,
  'status': instance.status,
  'submitted_at': instance.submitted_at?.toIso8601String(),
  'created_at': instance.created_at.toIso8601String(),
  'items': instance.items.map((e) => e.toJson()).toList(),
};

PrescriptionCreateRequest _$PrescriptionCreateRequestFromJson(
  Map<String, dynamic> json,
) => PrescriptionCreateRequest(
  shop_id: json['shop_id'] as String,
  image_url: json['image_url'] as String,
);

Map<String, dynamic> _$PrescriptionCreateRequestToJson(
  PrescriptionCreateRequest instance,
) => <String, dynamic>{
  'shop_id': instance.shop_id,
  'image_url': instance.image_url,
};