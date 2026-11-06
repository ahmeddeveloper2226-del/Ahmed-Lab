import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../core/utils/error_helpers.dart';
import '../data/models/chat_message_model.dart';
import '../data/repositories/chat_repository.dart';
import '../data/services/realtime_service.dart';

class ChatState {
  final List<ChatMessageModel> messages; // oldest first
  final bool isLoadingHistory;
  final bool hasMoreHistory;
  final bool otherPartyTyping;
  final bool otherPartyOnline;
  final String? error;

  const ChatState({
    this.messages = const [],
    this.isLoadingHistory = false,
    this.hasMoreHistory = true,
    this.otherPartyTyping = false,
    this.otherPartyOnline = false,
    this.error,
  });

  ChatState copyWith({
    List<ChatMessageModel>? messages,
    bool? isLoadingHistory,
    bool? hasMoreHistory,
    bool? otherPartyTyping,
    bool? otherPartyOnline,
    String? error,
  }) =>
      ChatState(
        messages: messages ?? this.messages,
        isLoadingHistory: isLoadingHistory ?? this.isLoadingHistory,
        hasMoreHistory: hasMoreHistory ?? this.hasMoreHistory,
        otherPartyTyping: otherPartyTyping ?? this.otherPartyTyping,
        otherPartyOnline: otherPartyOnline ?? this.otherPartyOnline,
        error: error,
      );
}

final chatProvider =
    StateNotifierProvider.autoDispose.family<ChatNotifier, ChatState, String>((ref, orderId) {
  return ChatNotifier(
    orderId: orderId,
    chatRepo: ref.watch(chatRepositoryProvider),
    realtime: ref.watch(realtimeServiceProvider),
  );
});

class ChatNotifier extends StateNotifier<ChatState> {
  final String orderId;
  final ChatRepository _chatRepo;
  final RealtimeService _realtime;
  String? _myUid;

  ChatNotifier({required this.orderId, required ChatRepository chatRepo, required RealtimeService realtime})
      : _chatRepo = chatRepo,
        _realtime = realtime,
        super(const ChatState()) {
    _init();
  }

  Future<void> _init() async {
    _myUid = FirebaseAuth.instance.currentUser?.uid;
    await loadMoreHistory();
    _realtime.connect(orderId).listen(_handleRealtimeEvent, onError: (e) {
      state = state.copyWith(error: friendlyErrorMessage(e));
    });
  }

  void _handleRealtimeEvent(Map<String, dynamic> data) {
    switch (data['type']) {
      case 'message':
        final incoming = ChatMessageModel.fromJson(data);
        // Avoid duplicating a message we already appended optimistically
        // (shouldn't normally happen since we don't optimistically append
        // text sends, but harmless to guard against here too).
        if (state.messages.any((m) => m.id == incoming.id)) return;
        state = state.copyWith(messages: [...state.messages, incoming]);
        // Immediately tell the sender we've received it, if it's not our own.
        if (incoming.senderId != null && incoming.senderId != _myUid) {
          markRead([incoming.id]);
        }
        break;
      case 'typing':
        if (data['from'] != _myUid) {
          state = state.copyWith(otherPartyTyping: data['is_typing'] == true);
        }
        break;
      case 'presence':
        if (data['from'] != _myUid) {
          state = state.copyWith(otherPartyOnline: data['online'] == true);
        }
        break;
      case 'read_receipt':
        final ids = (data['message_ids'] as List).cast<String>();
        state = state.copyWith(
          messages: [
            for (final m in state.messages)
              if (ids.contains(m.id)) m.copyWith(status: 'read') else m,
          ],
        );
        break;
      case 'voice_message':
        // Nudge that a new voice message exists — simplest correct handling
        // is to just reload the latest page of history rather than trying
        // to splice in a partially-known message.
        _refreshLatest();
        break;
    }
  }

  Future<void> _refreshLatest() async {
    try {
      final page = await _chatRepo.getHistory(orderId);
      final existingIds = state.messages.map((m) => m.id).toSet();
      final newOnes = page.messages.where((m) => !existingIds.contains(m.id));
      state = state.copyWith(messages: [...state.messages, ...newOnes]);
    } catch (_) {
      // Best-effort — the message will still show up next time history loads.
    }
  }

  Future<void> loadMoreHistory() async {
    if (state.isLoadingHistory || !state.hasMoreHistory) return;
    state = state.copyWith(isLoadingHistory: true);
    try {
      final cursor = state.messages.isNotEmpty ? state.messages.first.id : null;
      final page = await _chatRepo.getHistory(orderId, before: cursor);
      state = state.copyWith(
        messages: [...page.messages, ...state.messages],
        isLoadingHistory: false,
        hasMoreHistory: page.nextCursor != null,
      );
    } catch (e) {
      state = state.copyWith(isLoadingHistory: false, error: friendlyErrorMessage(e));
    }
  }

  void sendMessage(String content) {
    if (content.trim().isEmpty) return;
    _realtime.send({'type': 'message', 'content': content.trim()});
    // Not appended optimistically here — the server relay includes an
    // authoritative id/created_at/status, and since this same connection
    // also receives its own... actually the backend explicitly does NOT
    // echo a sender's own message back to them (see realtime_ws_router.py's
    // forward loop), so we DO need to show it immediately ourselves.
    state = state.copyWith(messages: [
      ...state.messages,
      ChatMessageModel(
        id: 'pending-${DateTime.now().microsecondsSinceEpoch}',
        orderId: orderId,
        senderId: _myUid,
        receiverId: '',
        messageType: 'text',
        status: 'sent',
        content: content.trim(),
        audioUrl: null,
        audioDurationSeconds: null,
        createdAt: DateTime.now(),
      ),
    ]);
  }

  void sendTyping(bool isTyping) {
    _realtime.send({'type': 'typing', 'is_typing': isTyping});
  }

  void markRead(List<String> messageIds) {
    if (messageIds.isEmpty) return;
    _realtime.send({'type': 'read', 'message_ids': messageIds});
  }

  Future<void> sendVoiceMessage(String filePath, double durationSeconds) async {
    try {
      final message = await _chatRepo.uploadVoiceMessage(orderId, filePath, durationSeconds);
      state = state.copyWith(messages: [...state.messages, message]);
      _realtime.send({'type': 'voice_message', 'message_id': message.id});
    } catch (e) {
      state = state.copyWith(error: 'تعذر إرسال الرسالة الصوتية');
    }
  }

  @override
  void dispose() {
    _realtime.disconnect();
    super.dispose();
  }
}