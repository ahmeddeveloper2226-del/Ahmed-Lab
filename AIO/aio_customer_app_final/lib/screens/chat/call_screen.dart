import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';
import '../../data/services/call_service.dart';

class CallScreen extends ConsumerStatefulWidget {
  final String orderId;
  final String otherPartyName;
  final bool isOutgoing;
  const CallScreen({super.key, required this.orderId, required this.otherPartyName, required this.isOutgoing});

  @override
  ConsumerState<CallScreen> createState() => _CallScreenState();
}

class _CallScreenState extends ConsumerState<CallScreen> {
  bool _speakerOn = false;

  @override
  void initState() {
    super.initState();
    if (widget.isOutgoing) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(callServiceProvider(widget.orderId).notifier).startCall();
      });
    }
  }

  void _toggleSpeaker() {
    setState(() => _speakerOn = !_speakerOn);
    Helper.setSpeakerphoneOn(_speakerOn);
  }

  String _formatDuration(Duration d) {
    final minutes = d.inMinutes.toString().padLeft(2, '0');
    final seconds = (d.inSeconds % 60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  String _statusLabel(CallStatus status) {
    switch (status) {
      case CallStatus.outgoingRinging:
        return 'جاري الاتصال...';
      case CallStatus.incomingRinging:
        return 'مكالمة واردة';
      case CallStatus.connected:
        return 'متصل';
      case CallStatus.ended:
        return 'انتهت المكالمة';
      case CallStatus.rejected:
        return 'تم رفض المكالمة';
      case CallStatus.busy:
        return 'الطرف الآخر مشغول';
      case CallStatus.timeout:
        return 'لم يتم الرد';
      case CallStatus.error:
        return 'حدث خطأ في المكالمة';
      case CallStatus.idle:
        return '';
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(callServiceProvider(widget.orderId));

    ref.listen(callServiceProvider(widget.orderId), (previous, next) {
      final terminal = {CallStatus.ended, CallStatus.rejected, CallStatus.busy, CallStatus.timeout, CallStatus.error};
      if (terminal.contains(next.status) && previous?.status != next.status) {
        Future.delayed(const Duration(seconds: 2), () {
          if (mounted) context.pop();
        });
      }
    });

    return Scaffold(
      backgroundColor: AppColors.darkBackground,
      body: SafeArea(
        child: Column(
          children: [
            const Spacer(flex: 2),
            CircleAvatar(
              radius: 60,
              backgroundColor: Colors.white.withValues(alpha: 0.15),
              child: Text(
                widget.otherPartyName.isNotEmpty ? widget.otherPartyName[0] : '?',
                style: const TextStyle(fontSize: 48, color: Colors.white, fontWeight: FontWeight.w700),
              ),
            ),
            const SizedBox(height: 20),
            Text(widget.otherPartyName, style: const TextStyle(fontSize: 24, color: Colors.white, fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            Text(
              state.status == CallStatus.connected ? _formatDuration(state.connectedDuration) : _statusLabel(state.status),
              style: TextStyle(fontSize: 15, color: Colors.white.withValues(alpha: 0.75)),
            ),
            const Spacer(flex: 3),
            if (state.status == CallStatus.incomingRinging)
              _buildIncomingControls()
            else
              _buildActiveControls(state),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }

  Widget _buildIncomingControls() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 40),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          _CallActionButton(
            icon: Icons.call_end_rounded,
            color: AppColors.error,
            onTap: () => ref.read(callServiceProvider(widget.orderId).notifier).rejectIncomingCall(),
          ),
          _CallActionButton(
            icon: Icons.call_rounded,
            color: AppColors.success,
            onTap: () => ref.read(callServiceProvider(widget.orderId).notifier).acceptIncomingCall(),
          ),
        ],
      ),
    );
  }

  Widget _buildActiveControls(CallState state) {
    final canHangUp = state.status == CallStatus.outgoingRinging || state.status == CallStatus.connected;
    return Column(
      children: [
        if (state.status == CallStatus.connected)
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _CallActionButton(
                icon: state.isMuted ? Icons.mic_off_rounded : Icons.mic_rounded,
                color: Colors.white.withValues(alpha: 0.2),
                small: true,
                onTap: () => ref.read(callServiceProvider(widget.orderId).notifier).toggleMute(),
              ),
              _CallActionButton(
                icon: _speakerOn ? Icons.volume_up_rounded : Icons.hearing_rounded,
                color: Colors.white.withValues(alpha: 0.2),
                small: true,
                onTap: _toggleSpeaker,
              ),
            ],
          ),
        const SizedBox(height: 24),
        if (canHangUp)
          _CallActionButton(
            icon: Icons.call_end_rounded,
            color: AppColors.error,
            onTap: () => ref.read(callServiceProvider(widget.orderId).notifier).hangUp(),
          ),
      ],
    );
  }
}

class _CallActionButton extends StatelessWidget {
  final IconData icon;
  final Color color;
  final VoidCallback onTap;
  final bool small;
  const _CallActionButton({required this.icon, required this.color, required this.onTap, this.small = false});

  @override
  Widget build(BuildContext context) {
    final size = small ? 56.0 : 70.0;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: size, height: size,
        decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        child: Icon(icon, color: Colors.white, size: small ? 24 : 32),
      ),
    );
  }
}