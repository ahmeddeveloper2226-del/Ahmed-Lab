import '../models/driver_login_response.dart';
import '../models/driver_order_model.dart';
import '../services/api_service.dart';
import '../../core/constants/api_constants.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final driverRepositoryProvider = Provider<DriverRepository>((ref) {
  return DriverRepository(apiService: ref.watch(apiServiceProvider));
});

class DriverRepository {
  final ApiService _api;

  DriverRepository({required ApiService apiService}) : _api = apiService;

  /// No OTP — the backend matches this phone number against a driver
  /// account an admin already created (after an in-person interview), and
  /// returns a Firebase custom token to sign in with.
  Future<DriverLoginResponse> loginWithPhone(String phoneNumber) async {
    final response = await _api.post(
      ApiConstants.driverAuthLogin,
      data: {'phone_number': phoneNumber},
    );
    return DriverLoginResponse.fromJson(response.data);
  }

  Future<DriverOrderModel> getOrder(String orderId) async {
    final response = await _api.get('/driver/orders/$orderId');
    return DriverOrderModel.fromJson(response.data);
  }

  /// Offers already made to THIS driver by the assignment worker — never a
  /// browsable list of nearby orders. Empty means no pending offer right now.
  Future<List<DriverOrderModel>> getOffers() async {
    final response = await _api.get(ApiConstants.driverOrdersOffers);
    return (response.data as List).map((e) => DriverOrderModel.fromJson(e)).toList();
  }

  Future<List<DriverOrderModel>> getActiveOrders() async {
    final response = await _api.get(ApiConstants.driverOrdersActive);
    return (response.data as List).map((e) => DriverOrderModel.fromJson(e)).toList();
  }

  /// Accepts every order in this delivery group at once (one driver, one
  /// trip, possibly several shops). Returns the updated orders.
  Future<List<DriverOrderModel>> acceptGroup(String deliveryGroupId) async {
    final response = await _api.post(ApiConstants.driverGroupAccept(deliveryGroupId));
    return (response.data as List).map((e) => DriverOrderModel.fromJson(e)).toList();
  }

  /// Declines an offered delivery group — the system offers it to the
  /// next-nearest driver instead.
  Future<void> declineGroup(String deliveryGroupId) async {
    await _api.post(ApiConstants.driverGroupDecline(deliveryGroupId));
  }

  /// status should be one of: "out_for_delivery", "delivered", "cancelled"
  /// ("preparing" is set automatically by acceptGroup()).
  Future<void> updateOrderStatus(String orderId, String status) async {
    await _api.patch(ApiConstants.driverOrderStatus(orderId), data: {'status': status});
  }

  /// Advances the granular AIO delivery lifecycle (spec 1.8/2.4-2.6/2.9),
  /// e.g. going_to_branch -> arrived_at_branch -> picked_up -> in_transit.
  /// Distinct from updateOrderStatus above — see DeliveryStage's docstring
  /// in driver_order_model.dart for why. Returns the updated order so the
  /// UI can refresh immediately without a separate fetch.
  Future<DriverOrderModel> updateDeliveryStage(String orderId, DeliveryStage stage) async {
    final response = await _api.patch(
      ApiConstants.driverOrderDeliveryStage(orderId),
      data: {'stage': stage.value},
    );
    return DriverOrderModel.fromJson(response.data);
  }

  /// Reports a delivery exception (spec 2.10) — customer unavailable, wrong
  /// address, customer refused, driver issue, or other. Frees the driver
  /// for new offers; does not itself cancel/refund the order.
  Future<DriverOrderModel> reportDeliveryFailure(
    String orderId, {
    required String reason,
    String? notes,
  }) async {
    final response = await _api.post(
      ApiConstants.driverOrderFailure(orderId),
      data: {'reason': reason, if (notes != null) 'notes': notes},
    );
    return DriverOrderModel.fromJson(response.data);
  }

  Future<void> updateLocation({
    required String orderId,
    required double lat,
    required double lng,
    double? bearing,
    double? speedKmh,
  }) async {
    await _api.post(ApiConstants.driverLocation, data: {
      'order_id': orderId,
      'lat': lat,
      'lng': lng,
      if (bearing != null) 'bearing': bearing,
      if (speedKmh != null) 'speed_kmh': speedKmh,
    });
  }

  Future<void> updateAvailability({required bool isAvailable, double? lat, double? lng}) async {
    await _api.patch(ApiConstants.driverAvailability, data: {
      'is_available': isAvailable,
      if (lat != null) 'lat': lat,
      if (lng != null) 'lng': lng,
    });
  }
}