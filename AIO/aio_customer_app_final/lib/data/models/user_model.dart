import 'package:json_annotation/json_annotation.dart';

part 'user_model.g.dart';

@JsonSerializable()
class UserSessionResponse {
  final String id;
  final String? phone_number;
  final String? email;
  final bool email_verified;
  final DateTime created_at;

  UserSessionResponse({
    required this.id,
    this.phone_number,
    this.email,
    required this.email_verified,
    required this.created_at,
  });

  factory UserSessionResponse.fromJson(Map<String, dynamic> json) =>
      _$UserSessionResponseFromJson(json);
  Map<String, dynamic> toJson() => _$UserSessionResponseToJson(this);
}

@JsonSerializable()
class UserProfileResponse {
  final String id;
  final String? full_name;
  final String? phone_number;
  final String? email;
  final bool email_verified;
  final DateTime created_at;

  UserProfileResponse({
    required this.id,
    this.full_name,
    this.phone_number,
    this.email,
    required this.email_verified,
    required this.created_at,
  });

  factory UserProfileResponse.fromJson(Map<String, dynamic> json) =>
      _$UserProfileResponseFromJson(json);
  Map<String, dynamic> toJson() => _$UserProfileResponseToJson(this);
}

@JsonSerializable()
class UserProfileUpdateRequest {
  final String full_name;

  UserProfileUpdateRequest({required this.full_name});

  factory UserProfileUpdateRequest.fromJson(Map<String, dynamic> json) =>
      _$UserProfileUpdateRequestFromJson(json);
  Map<String, dynamic> toJson() => _$UserProfileUpdateRequestToJson(this);
}
