// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'subcategory_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

SubcategoryResponse _$SubcategoryResponseFromJson(Map<String, dynamic> json) =>
    SubcategoryResponse(
      id: json['id'] as String,
      category_id: json['category_id'] as String,
      name: json['name'] as String,
      sort_order: (json['sort_order'] as num).toInt(),
    );

Map<String, dynamic> _$SubcategoryResponseToJson(
  SubcategoryResponse instance,
) => <String, dynamic>{
  'id': instance.id,
  'category_id': instance.category_id,
  'name': instance.name,
  'sort_order': instance.sort_order,
};