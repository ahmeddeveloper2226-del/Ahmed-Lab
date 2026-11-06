import 'dart:async';
import 'dart:convert';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../../core/constants/api_constants.dart';

final realtimeServiceProvider = Provider<RealtimeService>((ref) => RealtimeService());

/// One WebSocket connection per order, shared by chat (messages, typing,
/// presence, receipts) and call signaling (offer/answer/ICE/etc.) — mirrors
/// the backend's realtime_ws_router.py, which multiplexes both over a
/// single connection per participant per order.
///
/// Both ChatProvider and CallService listen to the same broadcast stream
/// this exposes, each filtering for the message "type"s they care about.
class RealtimeService {
  WebSocketChannel? _channel;
  StreamController<Map<String, dynamic>>? _controller;
  String? _currentOrderId;

  bool get isConnected => _channel != null;

  Stream<Map<String, dynamic>> connect(String orderId) {
    if (_currentOrderId == orderId && _controller != null) {
      return _controller!.stream;
    }
    disconnect();
    _currentOrderId = orderId;
    _controller = StreamController<Map<String, dynamic>>.broadcast();
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
      _channel = WebSocketChannel.connect(Uri.parse(ApiConstants.realtimeWsUrl(orderId, token)));
      _channel!.stream.listen(
        (raw) {
          try {
            final data = jsonDecode(raw as String) as Map<String, dynamic>;
            // Reply to server pings so the connection is kept alive —
            // matches the backend's _PING_INTERVAL_SECONDS keepalive.
            if (data['type'] == 'ping') {
              send({'type': 'pong'});
              return;
            }
            _controller?.add(data);
          } catch (_) {
            // Ignore malformed frames.
          }
        },
        onError: (error) => _controller?.addError(error),
        onDone: () => _controller?.close(),
      );
    } catch (e) {
      _controller?.addError(e);
    }
  }

  void send(Map<String, dynamic> payload) {
    _channel?.sink.add(jsonEncode(payload));
  }

  void disconnect() {
    _channel?.sink.close();
    _channel = null;
    _controller?.close();
    _controller = null;
    _currentOrderId = null;
  }
}