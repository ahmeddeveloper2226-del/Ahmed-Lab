import 'package:json_annotation/json_annotation.dart';

part 'subcategory_model.g.dart';

@JsonSerializable()
class SubcategoryResponse {
  final String id;
  final String category_id;
  final String name;
  final int sort_order;

  SubcategoryResponse({
    required this.id,
    required this.category_id,
    required this.name,
    required this.sort_order,
  });

  factory SubcategoryResponse.fromJson(Map<String, dynamic> json) =>
      _$SubcategoryResponseFromJson(json);
  Map<String, dynamic> toJson() => _$SubcategoryResponseToJson(this);
}