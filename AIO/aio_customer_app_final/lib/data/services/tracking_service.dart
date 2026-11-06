import 'dart:async';
import 'dart:convert';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../../core/constants/api_constants.dart';

final trackingServiceProvider = Provider<TrackingService>((ref) => TrackingService());

sealed class TrackingEvent {}

class TrackingLocation extends TrackingEvent {
  final double lat;
  final double lng;
  final double? bearing;
  final double? speedKmh;
  // Live ETA (spec 1.9), recalculated by the backend on every driver GPS
  // ping and pushed in the SAME message — see driver_router.py's
  // update_location. Null until the backend has enough info to compute it
  // (e.g. very first ping) or if it's a pre-1.8 order with no delivery_stage.
  final int? etaMinutes;
  TrackingLocation({required this.lat, required this.lng, this.bearing, this.speedKmh, this.etaMinutes});
}

class TrackingStatus extends TrackingEvent {
  final String status;
  TrackingStatus(this.status);
}

/// Granular AIO delivery lifecycle update (spec 1.8) — e.g.
/// "arrived_at_branch", "picked_up", "in_transit". A SEPARATE event type
/// from [TrackingStatus] above (which carries the coarser pending/
/// preparing/out_for_delivery/delivered/cancelled), matching the backend's
/// "stage" vs "status" WebSocket message split — see tracking_ws_router.py.
class TrackingStage extends TrackingEvent {
  final String stage;
  final int? etaMinutes;
  TrackingStage(this.stage, {this.etaMinutes});
}

/// Connects to the existing backend tracking WebSocket
/// (/tracking/{order_id}?token=...) and exposes decoded events. One
/// instance per order — create via connect(), always call disconnect()
/// when the tracking screen is closed so the connection (and the
/// customer-scoped subscription it holds server-side) is cleanly released.
class TrackingService {
  WebSocketChannel? _channel;
  StreamController<TrackingEvent>? _controller;

  Stream<TrackingEvent> connect(String orderId) {
    _controller = StreamController<TrackingEvent>.broadcast();
    _connectInternal(orderId);
    return _controller!.stream;
  }

  Future<void> _connectInternal(String orderId) async {
    final token = await FirebaseAuth.instance.currentUser?.getIdToken();
    if (token == null) {
      _controller?.addError('Not authenticated');
      return;
    }

    try {
      _channel = WebSocketChannel.connect(Uri.parse(ApiConstants.trackingWsUrl(orderId, token)));
      _channel!.stream.listen(
        (raw) {
          try {
            final data = jsonDecode(raw as String) as Map<String, dynamic>;
            switch (data['type']) {
              case 'location':
                _controller?.add(TrackingLocation(
                  lat: (data['lat'] as num).toDouble(),
                  lng: (data['lng'] as num).toDouble(),
                  bearing: (data['bearing'] as num?)?.toDouble(),
                  speedKmh: (data['speed_kmh'] as num?)?.toDouble(),
                  etaMinutes: (data['eta_minutes'] as num?)?.toInt(),
                ));
                break;
              case 'status':
                _controller?.add(TrackingStatus(data['status'] as String));
                break;
              case 'stage':
                _controller?.add(TrackingStage(
                  data['stage'] as String,
                  etaMinutes: (data['eta_minutes'] as num?)?.toInt(),
                ));
                break;
              // 'ping' — server keepalive, nothing to surface to the UI.
            }
          } catch (_) {
            // Ignore malformed frames rather than crashing the stream.
          }
        },
        onError: (error) => _controller?.addError(error),
        onDone: () => _controller?.close(),
      );
    } catch (e) {
      _controller?.addError(e);
    }
  }

  void disconnect() {
    _channel?.sink.close();
    _channel = null;
    _controller?.close();
    _controller = null;
  }
}