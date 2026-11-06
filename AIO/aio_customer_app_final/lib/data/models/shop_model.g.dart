// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'shop_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ShopResponse _$ShopResponseFromJson(Map<String, dynamic> json) => ShopResponse(
  id: json['id'] as String,
  category_id: json['category_id'] as String,
  subcategory_id: json['subcategory_id'] as String?,
  name: json['name'] as String,
  rating: (json['rating'] as num).toDouble(),
  logo_url: json['logo_url'] as String?,
);

Map<String, dynamic> _$ShopResponseToJson(ShopResponse instance) =>
    <String, dynamic>{
      'id': instance.id,
      'category_id': instance.category_id,
      'subcategory_id': instance.subcategory_id,
      'name': instance.name,
      'rating': instance.rating,
      'logo_url': instance.logo_url,
    };

ShopCreateRequest _$ShopCreateRequestFromJson(Map<String, dynamic> json) =>
    ShopCreateRequest(
      id: json['id'] as String,
      category_id: json['category_id'] as String,
      name: json['name'] as String,
    );

Map<String, dynamic> _$ShopCreateRequestToJson(ShopCreateRequest instance) =>
    <String, dynamic>{
      'id': instance.id,
      'category_id': instance.category_id,
      'name': instance.name,
    };