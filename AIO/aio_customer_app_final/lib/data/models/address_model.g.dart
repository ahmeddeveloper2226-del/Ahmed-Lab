// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'address_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

AddressResponse _$AddressResponseFromJson(Map<String, dynamic> json) =>
    AddressResponse(
      id: json['id'] as String,
      label: json['label'] as String?,
      full_address: json['full_address'] as String,
      lat: (json['lat'] as num?)?.toDouble(),
      lng: (json['lng'] as num?)?.toDouble(),
      is_default: json['is_default'] as bool,
    );

Map<String, dynamic> _$AddressResponseToJson(AddressResponse instance) =>
    <String, dynamic>{
      'id': instance.id,
      'label': instance.label,
      'full_address': instance.full_address,
      'lat': instance.lat,
      'lng': instance.lng,
      'is_default': instance.is_default,
    };

AddressCreateRequest _$AddressCreateRequestFromJson(
  Map<String, dynamic> json,
) => AddressCreateRequest(
  label: json['label'] as String?,
  full_address: json['full_address'] as String,
  lat: (json['lat'] as num?)?.toDouble(),
  lng: (json['lng'] as num?)?.toDouble(),
  is_default: json['is_default'] as bool? ?? false,
);

Map<String, dynamic> _$AddressCreateRequestToJson(
  AddressCreateRequest instance,
) => <String, dynamic>{
  'label': instance.label,
  'full_address': instance.full_address,
  'lat': instance.lat,
  'lng': instance.lng,
  'is_default': instance.is_default,
};

AddressUpdateRequest _$AddressUpdateRequestFromJson(
  Map<String, dynamic> json,
) => AddressUpdateRequest(
  label: json['label'] as String?,
  full_address: json['full_address'] as String?,
  lat: (json['lat'] as num?)?.toDouble(),
  lng: (json['lng'] as num?)?.toDouble(),
);

Map<String, dynamic> _$AddressUpdateRequestToJson(
  AddressUpdateRequest instance,
) => <String, dynamic>{
  'label': instance.label,
  'full_address': instance.full_address,
  'lat': instance.lat,
  'lng': instance.lng,
};
