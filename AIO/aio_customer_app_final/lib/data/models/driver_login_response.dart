class DriverLoginResponse {
  final String customToken;
  final String driverId;
  final String? fullName;
  final String? phoneNumber;

  DriverLoginResponse({
    required this.customToken,
    required this.driverId,
    required this.fullName,
    required this.phoneNumber,
  });

  factory DriverLoginResponse.fromJson(Map<String, dynamic> json) => DriverLoginResponse(
        customToken: json['custom_token'],
        driverId: json['driver_id'],
        fullName: json['full_name'],
        phoneNumber: json['phone_number'],
      );
}