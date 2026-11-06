// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'user_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

UserSessionResponse _$UserSessionResponseFromJson(Map<String, dynamic> json) =>
    UserSessionResponse(
      id: json['id'] as String,
      phone_number: json['phone_number'] as String?,
      email: json['email'] as String?,
      email_verified: json['email_verified'] as bool,
      created_at: DateTime.parse(json['created_at'] as String),
    );

Map<String, dynamic> _$UserSessionResponseToJson(
  UserSessionResponse instance,
) => <String, dynamic>{
  'id': instance.id,
  'phone_number': instance.phone_number,
  'email': instance.email,
  'email_verified': instance.email_verified,
  'created_at': instance.created_at.toIso8601String(),
};

UserProfileResponse _$UserProfileResponseFromJson(Map<String, dynamic> json) =>
    UserProfileResponse(
      id: json['id'] as String,
      full_name: json['full_name'] as String?,
      phone_number: json['phone_number'] as String?,
      email: json['email'] as String?,
      email_verified: json['email_verified'] as bool,
      created_at: DateTime.parse(json['created_at'] as String),
    );

Map<String, dynamic> _$UserProfileResponseToJson(
  UserProfileResponse instance,
) => <String, dynamic>{
  'id': instance.id,
  'full_name': instance.full_name,
  'phone_number': instance.phone_number,
  'email': instance.email,
  'email_verified': instance.email_verified,
  'created_at': instance.created_at.toIso8601String(),
};

UserProfileUpdateRequest _$UserProfileUpdateRequestFromJson(
  Map<String, dynamic> json,
) => UserProfileUpdateRequest(full_name: json['full_name'] as String);

Map<String, dynamic> _$UserProfileUpdateRequestToJson(
  UserProfileUpdateRequest instance,
) => <String, dynamic>{'full_name': instance.full_name};
