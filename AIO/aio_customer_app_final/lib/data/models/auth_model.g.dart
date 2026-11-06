// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'auth_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

SendEmailCodeRequest _$SendEmailCodeRequestFromJson(
  Map<String, dynamic> json,
) => SendEmailCodeRequest(email: json['email'] as String);

Map<String, dynamic> _$SendEmailCodeRequestToJson(
  SendEmailCodeRequest instance,
) => <String, dynamic>{'email': instance.email};

SendEmailCodeResponse _$SendEmailCodeResponseFromJson(
  Map<String, dynamic> json,
) => SendEmailCodeResponse(
  message: json['message'] as String,
  expires_in_seconds: (json['expires_in_seconds'] as num).toInt(),
);

Map<String, dynamic> _$SendEmailCodeResponseToJson(
  SendEmailCodeResponse instance,
) => <String, dynamic>{
  'message': instance.message,
  'expires_in_seconds': instance.expires_in_seconds,
};

VerifyEmailCodeRequest _$VerifyEmailCodeRequestFromJson(
  Map<String, dynamic> json,
) => VerifyEmailCodeRequest(code: json['code'] as String);

Map<String, dynamic> _$VerifyEmailCodeRequestToJson(
  VerifyEmailCodeRequest instance,
) => <String, dynamic>{'code': instance.code};

VerifyEmailCodeResponse _$VerifyEmailCodeResponseFromJson(
  Map<String, dynamic> json,
) => VerifyEmailCodeResponse(
  email: json['email'] as String,
  email_verified: json['email_verified'] as bool,
);

Map<String, dynamic> _$VerifyEmailCodeResponseToJson(
  VerifyEmailCodeResponse instance,
) => <String, dynamic>{
  'email': instance.email,
  'email_verified': instance.email_verified,
};

HTTPValidationError _$HTTPValidationErrorFromJson(Map<String, dynamic> json) =>
    HTTPValidationError(
      detail: (json['detail'] as List<dynamic>)
          .map((e) => ValidationError.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

Map<String, dynamic> _$HTTPValidationErrorToJson(
  HTTPValidationError instance,
) => <String, dynamic>{'detail': instance.detail};

ValidationError _$ValidationErrorFromJson(Map<String, dynamic> json) =>
    ValidationError(
      loc: json['loc'] as List<dynamic>,
      msg: json['msg'] as String,
      type: json['type'] as String,
    );

Map<String, dynamic> _$ValidationErrorToJson(ValidationError instance) =>
    <String, dynamic>{
      'loc': instance.loc,
      'msg': instance.msg,
      'type': instance.type,
    };
