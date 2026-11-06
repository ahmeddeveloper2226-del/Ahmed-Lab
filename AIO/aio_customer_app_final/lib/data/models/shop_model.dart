import 'package:json_annotation/json_annotation.dart';

part 'shop_model.g.dart';

@JsonSerializable()
class ShopResponse {
  final String id;
  final String category_id;
  final String? subcategory_id;
  final String name;
  final double rating;
  // Was missing entirely — the backend always returned it, but this model
  // silently dropped it during JSON parsing, so no shop logo could ever
  // reach the UI no matter what was saved in the admin panel.
  final String? logo_url;

  ShopResponse({
    required this.id,
    required this.category_id,
    this.subcategory_id,
    required this.name,
    required this.rating,
    this.logo_url,
  });

  factory ShopResponse.fromJson(Map<String, dynamic> json) =>
      _$ShopResponseFromJson(json);
  Map<String, dynamic> toJson() => _$ShopResponseToJson(this);
}

@JsonSerializable()
class ShopCreateRequest {
  final String id;
  final String category_id;
  final String name;

  ShopCreateRequest({
    required this.id,
    required this.category_id,
    required this.name,
  });

  factory ShopCreateRequest.fromJson(Map<String, dynamic> json) =>
      _$ShopCreateRequestFromJson(json);
  Map<String, dynamic> toJson() => _$ShopCreateRequestToJson(this);
}