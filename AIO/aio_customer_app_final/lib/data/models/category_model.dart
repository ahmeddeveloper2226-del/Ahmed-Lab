import 'package:json_annotation/json_annotation.dart';

part 'category_model.g.dart';

@JsonSerializable()
class CategoryResponse {
  final String id;
  final String name;
  final String? imageUrl;

  CategoryResponse({
    required this.id,
    required this.name,
    this.imageUrl,
  });

  factory CategoryResponse.fromJson(Map<String, dynamic> json) =>
      _$CategoryResponseFromJson(json);

  Map<String, dynamic> toJson() => _$CategoryResponseToJson(this);
}

@JsonSerializable()
class CategoryCreateRequest {
  final String id;
  final String name;

  CategoryCreateRequest({
    required this.id,
    required this.name,
  });

  factory CategoryCreateRequest.fromJson(Map<String, dynamic> json) =>
      _$CategoryCreateRequestFromJson(json);

  Map<String, dynamic> toJson() => _$CategoryCreateRequestToJson(this);
}