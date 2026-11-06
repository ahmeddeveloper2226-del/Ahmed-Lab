import 'package:json_annotation/json_annotation.dart';

part 'auth_model.g.dart';

@JsonSerializable()
class SendEmailCodeRequest {
  final String email;

  SendEmailCodeRequest({required this.email});

  factory SendEmailCodeRequest.fromJson(Map<String, dynamic> json) =>
      _$SendEmailCodeRequestFromJson(json);
  Map<String, dynamic> toJson() => _$SendEmailCodeRequestToJson(this);
}

@JsonSerializable()
class SendEmailCodeResponse {
  final String message;
  final int expires_in_seconds;

  SendEmailCodeResponse({required this.message, required this.expires_in_seconds});

  factory SendEmailCodeResponse.fromJson(Map<String, dynamic> json) =>
      _$SendEmailCodeResponseFromJson(json);
  Map<String, dynamic> toJson() => _$SendEmailCodeResponseToJson(this);
}

@JsonSerializable()
class VerifyEmailCodeRequest {
  final String code;

  VerifyEmailCodeRequest({required this.code});

  factory VerifyEmailCodeRequest.fromJson(Map<String, dynamic> json) =>
      _$VerifyEmailCodeRequestFromJson(json);
  Map<String, dynamic> toJson() => _$VerifyEmailCodeRequestToJson(this);
}

@JsonSerializable()
class VerifyEmailCodeResponse {
  final String email;
  final bool email_verified;

  VerifyEmailCodeResponse({required this.email, required this.email_verified});

  factory VerifyEmailCodeResponse.fromJson(Map<String, dynamic> json) =>
      _$VerifyEmailCodeResponseFromJson(json);
  Map<String, dynamic> toJson() => _$VerifyEmailCodeResponseToJson(this);
}

@JsonSerializable()
class HTTPValidationError {
  final List<ValidationError> detail;

  HTTPValidationError({required this.detail});

  factory HTTPValidationError.fromJson(Map<String, dynamic> json) =>
      _$HTTPValidationErrorFromJson(json);
  Map<String, dynamic> toJson() => _$HTTPValidationErrorToJson(this);
}

@JsonSerializable()
class ValidationError {
  final List<dynamic> loc;
  final String msg;
  final String type;

  ValidationError({required this.loc, required this.msg, required this.type});

  factory ValidationError.fromJson(Map<String, dynamic> json) =>
      _$ValidationErrorFromJson(json);
  Map<String, dynamic> toJson() => _$ValidationErrorToJson(this);
}
