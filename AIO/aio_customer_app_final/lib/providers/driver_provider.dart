import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/models/driver_order_model.dart';
import '../data/repositories/driver_repository.dart';

/// Driver's online/offline toggle. Kept as simple client state — the
/// backend is told about it via updateAvailability() whenever this changes
/// (see driver_home_screen.dart), rather than this provider reading from
/// the backend on every rebuild.
final driverOnlineProvider = StateProvider<bool>((ref) => false);

/// The driver's current position, refreshed by driver_home_screen.dart's
/// location stream — shared here so both the map and the nearby-orders
/// list use the exact same coordinate instead of fetching it twice.
class DriverPosition {
  final double lat;
  final double lng;
  const DriverPosition(this.lat, this.lng);
}

final driverPositionProvider = StateProvider<DriverPosition?>((ref) => null);

/// One entry per delivery_group_id — bundles the (possibly several) shop
/// orders that make up ONE offer, since a driver accepts/declines a whole
/// group in one action, not order-by-order.
class DeliveryOffer {
  final String deliveryGroupId;
  final List<DriverOrderModel> orders;

  DeliveryOffer({required this.deliveryGroupId, required this.orders});

  double get total => orders.fold(0, (sum, o) => sum + o.total);
  List<String> get shopNames => orders.map((o) => o.shopName).toList();
  DateTime get createdAt => orders.map((o) => o.createdAt).reduce((a, b) => a.isBefore(b) ? a : b);
}

List<DeliveryOffer> groupOffersByDeliveryGroup(List<DriverOrderModel> orders) {
  final byGroup = <String, List<DriverOrderModel>>{};
  for (final order in orders) {
    // Falls back to the order id itself if delivery_group_id is somehow
    // missing, so a malformed/older order still renders as its own offer
    // instead of silently disappearing.
    final key = order.deliveryGroupId ?? order.id;
    byGroup.putIfAbsent(key, () => []).add(order);
  }
  return byGroup.entries
      .map((e) => DeliveryOffer(deliveryGroupId: e.key, orders: e.value))
      .toList();
}

/// Polls GET /driver/orders/offers every few seconds while this provider is
/// alive (i.e. while the home screen showing offers is on screen) — offers
/// are time-limited (see backend driver_offer_timeout_seconds), so a stale
/// snapshot would show the driver something he can no longer accept.
final driverOffersProvider = StreamProvider.autoDispose<List<DriverOrderModel>>((ref) async* {
  final repo = ref.watch(driverRepositoryProvider);
  while (true) {
    try {
      yield await repo.getOffers();
    } catch (_) {
      // Best-effort — a single failed poll just keeps the previous value
      // on screen until the next tick succeeds.
    }
    await Future.delayed(const Duration(seconds: 4));
  }
});

final driverOrderDetailProvider =
    FutureProvider.autoDispose.family<DriverOrderModel, String>((ref, orderId) async {
  final repo = ref.watch(driverRepositoryProvider);
  return repo.getOrder(orderId);
});

final driverActiveOrdersProvider =
    FutureProvider.autoDispose<List<DriverOrderModel>>((ref) async {
  final repo = ref.watch(driverRepositoryProvider);
  return repo.getActiveOrders();
});