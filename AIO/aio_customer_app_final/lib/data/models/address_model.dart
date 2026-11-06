import 'package:json_annotation/json_annotation.dart';

part 'address_model.g.dart';

@JsonSerializable()
class AddressResponse {
  final String id;
  final String? label;
  final String full_address;
  final double? lat;
  final double? lng;
  final bool is_default;

  AddressResponse({
    required this.id,
    this.label,
    required this.full_address,
    this.lat,
    this.lng,
    required this.is_default,
  });

  factory AddressResponse.fromJson(Map<String, dynamic> json) =>
      _$AddressResponseFromJson(json);
  Map<String, dynamic> toJson() => _$AddressResponseToJson(this);
}

@JsonSerializable()
class AddressCreateRequest {
  final String? label;
  final String full_address;
  final double? lat;
  final double? lng;
  final bool is_default;

  AddressCreateRequest({
    this.label,
    required this.full_address,
    this.lat,
    this.lng,
    this.is_default = false,
  });

  factory AddressCreateRequest.fromJson(Map<String, dynamic> json) =>
      _$AddressCreateRequestFromJson(json);
  Map<String, dynamic> toJson() => _$AddressCreateRequestToJson(this);
}

@JsonSerializable()
class AddressUpdateRequest {
  final String? label;
  final String? full_address;
  final double? lat;
  final double? lng;

  AddressUpdateRequest({
    this.label,
    this.full_address,
    this.lat,
    this.lng,
  });

  factory AddressUpdateRequest.fromJson(Map<String, dynamic> json) =>
      _$AddressUpdateRequestFromJson(json);
  Map<String, dynamic> toJson() => _$AddressUpdateRequestToJson(this);
}
