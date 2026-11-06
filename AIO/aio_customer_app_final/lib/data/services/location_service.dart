import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';

final locationServiceProvider = Provider<LocationService>((ref) => LocationService());

enum LocationFailureReason { serviceDisabled, permissionDenied, permissionDeniedForever }

class LocationResult {
  final double? lat;
  final double? lng;
  final LocationFailureReason? failure;

  const LocationResult._({this.lat, this.lng, this.failure});

  factory LocationResult.success(double lat, double lng) => LocationResult._(lat: lat, lng: lng);
  factory LocationResult.failure(LocationFailureReason reason) => LocationResult._(failure: reason);

  bool get isSuccess => failure == null;
}

/// Shared across both the customer flow (used for "use my current location"
/// when adding an address) and the driver flow (used for the nearest-orders
/// map and periodic location updates) — one place that handles the
/// permission dance consistently instead of duplicating it per screen.
class LocationService {
  Future<LocationResult> getCurrentLocation() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      return LocationResult.failure(LocationFailureReason.serviceDisabled);
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied) {
      return LocationResult.failure(LocationFailureReason.permissionDenied);
    }
    if (permission == LocationPermission.deniedForever) {
      return LocationResult.failure(LocationFailureReason.permissionDeniedForever);
    }

    final position = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
    );
    return LocationResult.success(position.latitude, position.longitude);
  }

  /// Continuous position updates — used by the driver app while an order is
  /// active, to periodically push location to the backend for live tracking.
  Stream<Position> positionStream({int distanceFilterMeters = 20}) {
    return Geolocator.getPositionStream(
      locationSettings: LocationSettings(
        accuracy: LocationAccuracy.high,
        distanceFilter: distanceFilterMeters,
      ),
    );
  }

  String failureMessage(LocationFailureReason reason) {
    switch (reason) {
      case LocationFailureReason.serviceDisabled:
        return 'خدمة الموقع غير مفعلة على جهازك. يرجى تفعيلها من الإعدادات.';
      case LocationFailureReason.permissionDenied:
        return 'تحتاج إلى السماح بالوصول للموقع لاستخدام هذه الميزة.';
      case LocationFailureReason.permissionDeniedForever:
        return 'تم رفض إذن الموقع بشكل دائم. يرجى تفعيله يدويًا من إعدادات التطبيق.';
    }
  }
}