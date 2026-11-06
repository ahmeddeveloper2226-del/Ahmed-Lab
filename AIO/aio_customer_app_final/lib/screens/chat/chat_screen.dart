import 'dart:async';
import 'dart:io';
import 'package:audioplayers/audioplayers.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';
import '../../core/theme/app_theme.dart';
import '../../data/models/chat_message_model.dart';
import '../../data/repositories/chat_repository.dart';
import '../../data/services/call_service.dart';
import '../../providers/chat_provider.dart';

class ChatScreen extends ConsumerStatefulWidget {
  final String orderId;
  final String otherPartyName;
  const ChatScreen({super.key, required this.orderId, required this.otherPartyName});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _textController = TextEditingController();
  final _scrollController = ScrollController();
  final _recorder = AudioRecorder();
  Timer? _typingDebounce;
  bool _isRecording = false;
  DateTime? _recordingStartedAt;
  String? _myUid;

  @override
  void initState() {
    super.initState();
    _myUid = FirebaseAuth.instance.currentUser?.uid;
    _scrollController.addListener(_onScroll);
  }

  void _onScroll() {
    if (_scrollController.position.pixels <= 100) {
      ref.read(chatProvider(widget.orderId).notifier).loadMoreHistory();
    }
  }

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    _typingDebounce?.cancel();
    _recorder.dispose();
    super.dispose();
  }

  void _onTextChanged(String value) {
    ref.read(chatProvider(widget.orderId).notifier).sendTyping(value.isNotEmpty);
    _typingDebounce?.cancel();
    _typingDebounce = Timer(const Duration(seconds: 2), () {
      ref.read(chatProvider(widget.orderId).notifier).sendTyping(false);
    });
  }

  void _send() {
    final text = _textController.text;
    if (text.trim().isEmpty) return;
    ref.read(chatProvider(widget.orderId).notifier).sendMessage(text);
    _textController.clear();
    ref.read(chatProvider(widget.orderId).notifier).sendTyping(false);
  }

  Future<void> _toggleRecording() async {
    if (_isRecording) {
      final path = await _recorder.stop();
      final duration = _recordingStartedAt != null
          ? DateTime.now().difference(_recordingStartedAt!).inMilliseconds / 1000.0
          : 0.0;
      setState(() => _isRecording = false);
      if (path != null && duration > 0.5) {
        ref.read(chatProvider(widget.orderId).notifier).sendVoiceMessage(path, duration);
      }
      return;
    }

    final hasPermission = await _recorder.hasPermission();
    if (!hasPermission) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('يرجى السماح بالوصول إلى الميكروفون لإرسال رسالة صوتية.')),
        );
      }
      return;
    }

    final dir = await getTemporaryDirectory();
    final path = '${dir.path}/voice_${DateTime.now().millisecondsSinceEpoch}.m4a';
    await _recorder.start(const RecordConfig(), path: path);
    setState(() {
      _isRecording = true;
      _recordingStartedAt = DateTime.now();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(chatProvider(widget.orderId));

    // An incoming call offer arriving while this chat is open should pop
    // up the call screen automatically. See call_service.dart's docstring
    // for the honest limitation: this only works while some screen for
    // this order has the realtime connection open (chat or call screen),
    // not as a true background/anytime incoming call.
    ref.listen(callServiceProvider(widget.orderId), (previous, next) {
      if (next.status == CallStatus.incomingRinging && previous?.status != CallStatus.incomingRinging) {
        context.push('/call/${widget.orderId}?name=${Uri.encodeComponent(widget.otherPartyName)}&incoming=true');
      }
    });

    // Auto-scroll to bottom on new messages.
    ref.listen(chatProvider(widget.orderId), (previous, next) {
      if (previous != null && next.messages.length > previous.messages.length) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (_scrollController.hasClients) {
            _scrollController.animateTo(
              _scrollController.position.maxScrollExtent,
              duration: const Duration(milliseconds: 250),
              curve: Curves.easeOut,
            );
          }
        });
      }
    });

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              width: 10, height: 10,
              margin: const EdgeInsets.only(left: 8),
              decoration: BoxDecoration(
                color: state.otherPartyOnline ? AppColors.success : AppColors.textMuted,
                shape: BoxShape.circle,
              ),
            ),
            Flexible(child: Text(widget.otherPartyName, overflow: TextOverflow.ellipsis)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.call_rounded),
            onPressed: () => context.push('/call/${widget.orderId}?name=${Uri.encodeComponent(widget.otherPartyName)}'),
          ),
        ],
      ),
      body: Column(
        children: [
          if (state.error != null)
            Container(
              width: double.infinity,
              color: AppColors.error.withValues(alpha: 0.1),
              padding: const EdgeInsets.all(8),
              child: Text(state.error!, style: const TextStyle(color: AppColors.error), textAlign: TextAlign.center),
            ),
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(16),
              itemCount: state.messages.length + (state.otherPartyTyping ? 1 : 0),
              itemBuilder: (context, index) {
                if (index == state.messages.length) {
                  return const _TypingBubble();
                }
                final message = state.messages[index];
                if (message.isSystem) {
                  return _SystemMessageBubble(message: message);
                }
                final isMine = message.isMine(_myUid ?? '');
                return message.messageType == 'voice'
                    ? _VoiceMessageBubble(message: message, isMine: isMine)
                    : _TextMessageBubble(message: message, isMine: isMine);
              },
            ),
          ),
          _buildInputBar(),
        ],
      ),
    );
  }

  Widget _buildInputBar() {
    return Container(
      padding: EdgeInsets.fromLTRB(12, 8, 12, 8 + MediaQuery.of(context).padding.bottom),
      decoration: BoxDecoration(
        color: Colors.white,
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 10, offset: const Offset(0, -2))],
      ),
      child: Row(
        children: [
          if (_isRecording)
            const Expanded(
              child: Row(
                children: [
                  Icon(Icons.fiber_manual_record_rounded, color: AppColors.error, size: 16),
                  SizedBox(width: 8),
                  Text('جاري التسجيل...', style: TextStyle(color: AppColors.error)),
                ],
              ),
            )
          else
            Expanded(
              child: TextField(
                controller: _textController,
                textAlign: TextAlign.right,
                onChanged: _onTextChanged,
                decoration: InputDecoration(
                  hintText: 'اكتب رسالة...',
                  filled: true,
                  fillColor: AppColors.background,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(24), borderSide: BorderSide.none),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                ),
              ),
            ),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: _toggleRecording,
            child: CircleAvatar(
              backgroundColor: _isRecording ? AppColors.error : AppColors.primaryBlue,
              child: Icon(_isRecording ? Icons.stop_rounded : Icons.mic_rounded, color: Colors.white),
            ),
          ),
          if (!_isRecording) ...[
            const SizedBox(width: 8),
            CircleAvatar(
              backgroundColor: AppColors.primaryBlue,
              child: IconButton(
                icon: const Icon(Icons.send_rounded, color: Colors.white, size: 20),
                onPressed: _send,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _TypingBubble extends StatelessWidget {
  const _TypingBubble();

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18)),
        child: const Text('...يكتب الآن', style: TextStyle(color: AppColors.textMuted)),
      ),
    );
  }
}

class _SystemMessageBubble extends StatelessWidget {
  final ChatMessageModel message;
  const _SystemMessageBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 8),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(color: AppColors.divider, borderRadius: BorderRadius.circular(12)),
        child: Text(
          message.content ?? '',
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
        ),
      ),
    );
  }
}

class _TextMessageBubble extends StatelessWidget {
  final ChatMessageModel message;
  final bool isMine;
  const _TextMessageBubble({required this.message, required this.isMine});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: isMine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.72),
        decoration: BoxDecoration(
          gradient: isMine ? AppGradients.primary : null,
          color: isMine ? null : Colors.white,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              message.content ?? '',
              style: TextStyle(color: isMine ? Colors.white : AppColors.textPrimary),
            ),
            if (isMine) ...[
              const SizedBox(height: 4),
              Icon(
                message.status == 'read' ? Icons.done_all_rounded : Icons.done_rounded,
                size: 14,
                color: message.status == 'read' ? Colors.amberAccent : Colors.white70,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _VoiceMessageBubble extends ConsumerStatefulWidget {
  final ChatMessageModel message;
  final bool isMine;
  const _VoiceMessageBubble({required this.message, required this.isMine});

  @override
  ConsumerState<_VoiceMessageBubble> createState() => _VoiceMessageBubbleState();
}

class _VoiceMessageBubbleState extends ConsumerState<_VoiceMessageBubble> {
  final _player = AudioPlayer();
  bool _isPlaying = false;
  bool _isLoading = false;

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }

  Future<void> _togglePlay() async {
    if (_isPlaying) {
      await _player.pause();
      setState(() => _isPlaying = false);
      return;
    }

    setState(() => _isLoading = true);
    try {
      final repo = ref.read(chatRepositoryProvider);
      final dir = await getTemporaryDirectory();
      final path = '${dir.path}/${widget.message.id}.m4a';
      final file = File(path);
      if (!await file.exists()) {
        await repo.downloadVoiceMessage(widget.message.id, path);
      }
      await _player.play(DeviceFileSource(path));
      setState(() {
        _isPlaying = true;
        _isLoading = false;
      });
      _player.onPlayerComplete.listen((_) {
        if (mounted) setState(() => _isPlaying = false);
      });
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isMine = widget.isMine;
    return Align(
      alignment: isMine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          gradient: isMine ? AppGradients.primary : null,
          color: isMine ? null : Colors.white,
          borderRadius: BorderRadius.circular(18),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            GestureDetector(
              onTap: _isLoading ? null : _togglePlay,
              child: _isLoading
                  ? SizedBox(
                      width: 32, height: 32,
                      child: CircularProgressIndicator(strokeWidth: 2, color: isMine ? Colors.white : AppColors.primaryBlue),
                    )
                  : Icon(
                      _isPlaying ? Icons.pause_circle_filled_rounded : Icons.play_circle_fill_rounded,
                      size: 32,
                      color: isMine ? Colors.white : AppColors.primaryBlue,
                    ),
            ),
            const SizedBox(width: 8),
            Text(
              widget.message.audioDurationSeconds != null
                  ? '${widget.message.audioDurationSeconds!.toStringAsFixed(0)}s'
                  : '',
              style: TextStyle(color: isMine ? Colors.white : AppColors.textSecondary, fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }
}