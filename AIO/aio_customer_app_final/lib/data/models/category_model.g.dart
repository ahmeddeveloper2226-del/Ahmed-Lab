// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'category_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

CategoryResponse _$CategoryResponseFromJson(Map<String, dynamic> json) =>
    CategoryResponse(
      id: json['id'] as String,
      name: json['name'] as String,
      imageUrl: json['imageUrl'] as String?,
    );

Map<String, dynamic> _$CategoryResponseToJson(CategoryResponse instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'imageUrl': instance.imageUrl,
    };

CategoryCreateRequest _$CategoryCreateRequestFromJson(
  Map<String, dynamic> json,
) =>
    CategoryCreateRequest(
      id: json['id'] as String,
      name: json['name'] as String,
    );

Map<String, dynamic> _$CategoryCreateRequestToJson(
  CategoryCreateRequest instance,
) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
    };