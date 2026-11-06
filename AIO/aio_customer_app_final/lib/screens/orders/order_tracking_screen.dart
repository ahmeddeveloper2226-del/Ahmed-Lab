import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart' as ll;
import '../../core/theme/app_theme.dart';
import '../../data/models/order_model.dart';
import '../../data/models/delivery_stage.dart';
import '../../data/services/tracking_service.dart';
import '../../data/services/location_service.dart';

class OrderTrackingScreen extends ConsumerStatefulWidget {
  final OrderResponse order;
  const OrderTrackingScreen({super.key, required this.order});

  @override
  ConsumerState<OrderTrackingScreen> createState() => _OrderTrackingScreenState();
}

class _OrderTrackingScreenState extends ConsumerState<OrderTrackingScreen> {
  final MapController _mapController = MapController();
  ll.LatLng? _driverPosition;
  // flutter_map has no myLocationEnabled equivalent — replicated with one
  // fetch via the same LocationService the rest of the app already uses
  // (see driver_order_detail_screen.dart for the same pattern).
  ll.LatLng? _myPosition;
  String _status = '';
  // Granular AIO delivery stage (spec 1.8), when the order has one — see
  // TrackingStage's docstring. Null for orders with no stage tracking
  // (pre-1.8 orders, or shops with no branch), in which case the screen
  // falls back to _statusLabel(_status) exactly as before this existed.
  DeliveryStage? _stage;
  // Live ETA (spec 1.9), refreshed on every driver location AND stage
  // update — whichever arrives most recently wins, since both carry it.
  int? _etaMinutes;
  String? _error;

  @override
  void initState() {
    super.initState();
    _status = widget.order.status;
    _stage = DeliveryStage.fromValue(widget.order.delivery_stage);
    _etaMinutes = widget.order.live_eta_minutes ?? widget.order.eta_minutes;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _connect();
      _fetchOwnPositionOnce();
    });
  }

  Future<void> _fetchOwnPositionOnce() async {
    final result = await ref.read(locationServiceProvider).getCurrentLocation();
    if (mounted && result.isSuccess) {
      setState(() => _myPosition = ll.LatLng(result.lat!, result.lng!));
    }
  }

  void _connect() {
    final service = ref.read(trackingServiceProvider);
    service.connect(widget.order.id).listen(
      (event) {
        if (!mounted) return;
        if (event is TrackingLocation) {
          setState(() {
            _driverPosition = ll.LatLng(event.lat, event.lng);
            if (event.etaMinutes != null) _etaMinutes = event.etaMinutes;
          });
          // Instant reposition rather than an animated pan — flutter_map
          // has no built-in camera animation like GoogleMap's
          // animateCamera without an extra package (flutter_map_animations).
          // Position stays accurate; it just snaps instead of gliding.
          _mapController.move(_driverPosition!, _mapController.camera.zoom);
        } else if (event is TrackingStatus) {
          setState(() => _status = event.status);
        } else if (event is TrackingStage) {
          setState(() {
            _stage = DeliveryStage.fromValue(event.stage);
            if (event.etaMinutes != null) _etaMinutes = event.etaMinutes;
          });
        }
      },
      onError: (e) {
        if (mounted) setState(() => _error = 'تعذر الاتصال بخدمة التتبع');
      },
    );
  }

  @override
  void dispose() {
    ref.read(trackingServiceProvider).disconnect();
    super.dispose();
  }

  String _statusLabel(String status) {
    switch (status) {
      case 'preparing':
        return 'السائق في الطريق إلى المتجر';
      case 'out_for_delivery':
        return 'السائق في الطريق إليك';
      case 'delivered':
        return 'تم التوصيل';
      case 'cancelled':
        return 'تم إلغاء الطلب';
      default:
        return status;
    }
  }

  @override
  Widget build(BuildContext context) {
    // Pickup marker: the exact branch fulfilling this order (spec 1.1/2.4)
    // when one is assigned, otherwise the shop's own location — unchanged
    // fallback for shops with no branches.
    final pickupLat = widget.order.pickupLat;
    final pickupLng = widget.order.pickupLng;
    final initialCenter = _driverPosition ??
        (pickupLat != null && pickupLng != null ? ll.LatLng(pickupLat, pickupLng) : const ll.LatLng(30.0444, 31.2357));

    final markers = <Marker>[];
    if (pickupLat != null && pickupLng != null) {
      markers.add(Marker(
        point: ll.LatLng(pickupLat, pickupLng),
        width: 40,
        height: 40,
        child: const _LabeledPin(icon: Icons.storefront_rounded, color: Colors.orange),
      ));
    }
    if (widget.order.delivery_lat != null && widget.order.delivery_lng != null) {
      markers.add(Marker(
        point: ll.LatLng(widget.order.delivery_lat!, widget.order.delivery_lng!),
        width: 40,
        height: 40,
        child: const _LabeledPin(icon: Icons.home_rounded, color: Colors.green),
      ));
    }
    if (_driverPosition != null) {
      markers.add(Marker(
        point: _driverPosition!,
        width: 40,
        height: 40,
        child: const _LabeledPin(icon: Icons.two_wheeler_rounded, color: AppColors.primaryBlue),
      ));
    }
    if (_myPosition != null) {
      markers.add(Marker(
        point: _myPosition!,
        width: 22,
        height: 22,
        child: Container(
          decoration: BoxDecoration(
            color: AppColors.primaryBlue,
            shape: BoxShape.circle,
            border: Border.all(color: Colors.white, width: 3),
            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.3), blurRadius: 4)],
          ),
        ),
      ));
    }

    return Scaffold(
      appBar: AppBar(title: const Text('تتبع الطلب')),
      body: Column(
        children: [
          Expanded(
            child: FlutterMap(
              mapController: _mapController,
              options: MapOptions(initialCenter: initialCenter, initialZoom: 13),
              children: [
                // Dev-friendly default tile source — see driver_home_screen.dart's
                // note on switching to a proper tile provider before production
                // traffic (OSM's own servers ask that of self-hosted apps).
                TileLayer(
                  urlTemplate: 'https://api.maptiler.com/maps/base-v4/{z}/{x}/{y}.png?key=WWipVbJeua9IIY8gsxvx',
                  userAgentPackageName: 'com.wasla.aio_customer_app',
                ),
                MarkerLayer(markers: markers),
              ],
            ),
          ),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(20),
            decoration: const BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (_error != null)
                  Text(_error!, style: const TextStyle(color: AppColors.error))
                else
                  Row(
                    children: [
                      Container(
                        width: 12, height: 12,
                        decoration: const BoxDecoration(color: AppColors.success, shape: BoxShape.circle),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          _stage?.arabicLabel ?? _statusLabel(_status),
                          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
                        ),
                      ),
                      if (_etaMinutes != null)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                          decoration: BoxDecoration(
                            color: AppColors.primaryBlue.withValues(alpha: 0.08),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.access_time_rounded, size: 14, color: AppColors.primaryBlue),
                              const SizedBox(width: 4),
                              Text('$_etaMinutes دقيقة',
                                  style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: AppColors.primaryBlue)),
                            ],
                          ),
                        ),
                    ],
                  ),
                if (widget.order.driver_name != null) ...[
                  const SizedBox(height: 12),
                  Text('السائق: ${widget.order.driver_name}', style: const TextStyle(color: AppColors.textSecondary)),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// flutter_map has no InfoWindow — this is the simple visual replacement
/// for GoogleMap's colored-hue markers (BitmapDescriptor.hueOrange/Green/Blue).
class _LabeledPin extends StatelessWidget {
  final IconData icon;
  final Color color;
  const _LabeledPin({required this.icon, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white, width: 2),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.25), blurRadius: 4)],
      ),
      child: Icon(icon, color: Colors.white, size: 20),
    );
  }
}