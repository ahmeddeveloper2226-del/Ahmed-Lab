import 'package:json_annotation/json_annotation.dart';

part 'prescription_model.g.dart';

@JsonSerializable()
class PrescriptionItemResponse {
  final String id;
  // Always present now — the pharmacist can only pick from their own
  // product catalog (see the panel's product picker), never a freeform
  // name/price. That guarantees every item can go straight into the cart
  // via /cart/items/{product_id} on approval.
  final String product_id;
  final String name;
  final double price;
  final int quantity;
  final bool included;

  PrescriptionItemResponse({
    required this.id,
    required this.product_id,
    required this.name,
    required this.price,
    required this.quantity,
    required this.included,
  });

  factory PrescriptionItemResponse.fromJson(Map<String, dynamic> json) =>
      _$PrescriptionItemResponseFromJson(json);
  Map<String, dynamic> toJson() => _$PrescriptionItemResponseToJson(this);
}

@JsonSerializable()
class PrescriptionResponse {
  final String id;
  final String shop_id;
  final String shop_name;
  final String image_url;
  final String status;
  final DateTime? submitted_at;
  final DateTime created_at;
  final List<PrescriptionItemResponse> items;

  PrescriptionResponse({
    required this.id,
    required this.shop_id,
    required this.shop_name,
    required this.image_url,
    required this.status,
    this.submitted_at,
    required this.created_at,
    required this.items,
  });

  factory PrescriptionResponse.fromJson(Map<String, dynamic> json) =>
      _$PrescriptionResponseFromJson(json);
  Map<String, dynamic> toJson() => _$PrescriptionResponseToJson(this);
}

@JsonSerializable()
class PrescriptionCreateRequest {
  final String shop_id;
  final String image_url;

  PrescriptionCreateRequest({required this.shop_id, required this.image_url});

  factory PrescriptionCreateRequest.fromJson(Map<String, dynamic> json) =>
      _$PrescriptionCreateRequestFromJson(json);
  Map<String, dynamic> toJson() => _$PrescriptionCreateRequestToJson(this);
}