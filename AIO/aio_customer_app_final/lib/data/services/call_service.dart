import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import '../../core/constants/api_constants.dart';
import 'api_service.dart';
import 'realtime_service.dart';

enum CallStatus { idle, incomingRinging, outgoingRinging, connected, ended, rejected, busy, timeout, error }

class CallState {
  final CallStatus status;
  final Duration connectedDuration;
  final bool isMuted;
  const CallState({this.status = CallStatus.idle, this.connectedDuration = Duration.zero, this.isMuted = false});

  CallState copyWith({CallStatus? status, Duration? connectedDuration, bool? isMuted}) => CallState(
        status: status ?? this.status,
        connectedDuration: connectedDuration ?? this.connectedDuration,
        isMuted: isMuted ?? this.isMuted,
      );
}

final callServiceProvider =
    StateNotifierProvider.autoDispose.family<CallService, CallState, String>((ref, orderId) {
  return CallService(orderId: orderId, realtime: ref.watch(realtimeServiceProvider), api: ref.watch(apiServiceProvider));
});

/// WebRTC audio call over the shared realtime WebSocket connection
/// (realtime_service.dart) — signaling only travels through the backend;
/// actual audio is peer-to-peer once connected.
///
/// Honest limitation: this only detects an INCOMING call while the app has
/// this connection open (i.e. the chat/call screen for this order is
/// active). A true "ring anytime" experience needs a push-notification-
/// triggered native call UI (CallKit/ConnectionService), which is a
/// separate, much larger integration this doesn't attempt.
class CallService extends StateNotifier<CallState> {
  final String orderId;
  final RealtimeService _realtime;
  final ApiService _api;

  RTCPeerConnection? _pc;
  MediaStream? _localStream;
  StreamSubscription? _signalingSub;
  Timer? _durationTimer;
  Timer? _ringTimeout;
  DateTime? _connectedAt;

  CallService({required this.orderId, required RealtimeService realtime, required ApiService api})
      : _realtime = realtime,
        _api = api,
        super(const CallState()) {
    _listenForSignaling();
  }

  void _listenForSignaling() {
    _signalingSub = _realtime.connect(orderId).listen((data) {
      switch (data['type']) {
        case 'offer':
          _handleIncomingOffer(data);
          break;
        case 'answer':
          _handleAnswer(data);
          break;
        case 'ice_candidate':
          _handleRemoteIceCandidate(data);
          break;
        case 'hangup':
          _endCall(CallStatus.ended);
          break;
        case 'reject':
          _endCall(CallStatus.rejected);
          break;
        case 'busy':
          _endCall(CallStatus.busy);
          break;
        case 'call_timeout':
          _endCall(CallStatus.timeout);
          break;
      }
    });
  }

  Future<List<Map<String, dynamic>>> _fetchIceServers() async {
    try {
      final response = await _api.get(ApiConstants.iceServers);
      final servers = (response.data['ice_servers'] as List).cast<Map<String, dynamic>>();
      return servers;
    } catch (_) {
      // Fall back to public STUN only if the backend call fails —
      // better than not being able to call at all.
      return [
        {'urls': 'stun:stun.l.google.com:19302'}
      ];
    }
  }

  Future<RTCPeerConnection> _createPeerConnection() async {
    final iceServers = await _fetchIceServers();
    final pc = await createPeerConnection({'iceServers': iceServers});

    pc.onIceCandidate = (candidate) {
      _realtime.send({
        'type': 'ice_candidate',
        'candidate': {
          'candidate': candidate.candidate,
          'sdpMid': candidate.sdpMid,
          'sdpMLineIndex': candidate.sdpMLineIndex,
        },
      });
    };

    pc.onConnectionState = (connectionState) {
      if (connectionState == RTCPeerConnectionState.RTCPeerConnectionStateConnected) {
        _onConnected();
      } else if (connectionState == RTCPeerConnectionState.RTCPeerConnectionStateFailed ||
          connectionState == RTCPeerConnectionState.RTCPeerConnectionStateClosed) {
        if (state.status == CallStatus.connected) {
          _endCall(CallStatus.ended);
        }
      }
    };

    _localStream = await navigator.mediaDevices.getUserMedia({'audio': true, 'video': false});
    for (final track in _localStream!.getTracks()) {
      await pc.addTrack(track, _localStream!);
    }

    return pc;
  }

  /// Outgoing call — called when the user taps the call button.
  Future<void> startCall() async {
    state = state.copyWith(status: CallStatus.outgoingRinging);
    _pc = await _createPeerConnection();
    final offer = await _pc!.createOffer({'offerToReceiveAudio': 1});
    await _pc!.setLocalDescription(offer);
    _realtime.send({'type': 'offer', 'sdp': offer.sdp});

    // No answer within 30s — treat as unanswered (mirrors "call timeout"
    // in the requirements). The other side's client should ideally send
    // its own call_timeout too, but this local timer means the CALLER
    // isn't stuck ringing forever even if that message is lost.
    _ringTimeout = Timer(const Duration(seconds: 30), () {
      if (state.status == CallStatus.outgoingRinging) {
        _realtime.send({'type': 'call_timeout'});
        _endCall(CallStatus.timeout);
      }
    });
  }

  Future<void> _handleIncomingOffer(Map<String, dynamic> data) async {
    if (state.status != CallStatus.idle) {
      // Already on a call — tell the caller we're busy, matching the
      // backend's own busy-state check (see realtime_ws_router.py).
      _realtime.send({'type': 'busy'});
      return;
    }
    state = state.copyWith(status: CallStatus.incomingRinging);
    _pendingOfferSdp = data['sdp'] as String?;
  }

  String? _pendingOfferSdp;

  Future<void> acceptIncomingCall() async {
    if (_pendingOfferSdp == null) return;
    _pc = await _createPeerConnection();
    await _pc!.setRemoteDescription(RTCSessionDescription(_pendingOfferSdp!, 'offer'));
    final answer = await _pc!.createAnswer();
    await _pc!.setLocalDescription(answer);
    _realtime.send({'type': 'answer', 'sdp': answer.sdp});
  }

  void rejectIncomingCall() {
    _realtime.send({'type': 'reject'});
    _endCall(CallStatus.rejected);
  }

  Future<void> _handleAnswer(Map<String, dynamic> data) async {
    if (_pc == null) return;
    _ringTimeout?.cancel();
    await _pc!.setRemoteDescription(RTCSessionDescription(data['sdp'] as String, 'answer'));
  }

  Future<void> _handleRemoteIceCandidate(Map<String, dynamic> data) async {
    if (_pc == null) return;
    final c = data['candidate'] as Map<String, dynamic>?;
    if (c == null) return;
    await _pc!.addCandidate(RTCIceCandidate(c['candidate'], c['sdpMid'], c['sdpMLineIndex']));
  }

  void _onConnected() {
    _ringTimeout?.cancel();
    _connectedAt = DateTime.now();
    state = state.copyWith(status: CallStatus.connected, connectedDuration: Duration.zero);
    _durationTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (_connectedAt != null) {
        state = state.copyWith(connectedDuration: DateTime.now().difference(_connectedAt!));
      }
    });
  }

  void toggleMute() {
    if (_localStream == null) return;
    final newMuted = !state.isMuted;
    for (final track in _localStream!.getAudioTracks()) {
      track.enabled = !newMuted;
    }
    state = state.copyWith(isMuted: newMuted);
  }

  void hangUp() {
    _realtime.send({'type': 'hangup'});
    _endCall(CallStatus.ended);
  }

  void _endCall(CallStatus finalStatus) {
    _ringTimeout?.cancel();
    _durationTimer?.cancel();
    _localStream?.getTracks().forEach((t) => t.stop());
    _pc?.close();
    _pc = null;
    _localStream = null;
    state = state.copyWith(status: finalStatus);
  }

  @override
  void dispose() {
    _signalingSub?.cancel();
    _ringTimeout?.cancel();
    _durationTimer?.cancel();
    _localStream?.getTracks().forEach((t) => t.stop());
    _pc?.close();
    super.dispose();
  }
}