import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/models/ai_chat_model.dart';
import '../data/repositories/ai_assistant_repository.dart';
import 'cart_provider.dart';

/// Whether the compact chat panel is open — the FAB toggles this, the
/// panel's own close button sets it back to false. Kept separate from
/// AiChatState so opening/closing doesn't need to touch message history.
final aiAssistantOpenProvider = StateProvider<bool>((ref) => false);

class AiChatState {
  final String mode; // 'question' | 'order'
  final List<AiChatEntry> entries;
  final bool sending;

  const AiChatState({this.mode = 'question', this.entries = const [], this.sending = false});

  AiChatState copyWith({String? mode, List<AiChatEntry>? entries, bool? sending}) => AiChatState(
        mode: mode ?? this.mode,
        entries: entries ?? this.entries,
        sending: sending ?? this.sending,
      );
}

final aiChatControllerProvider = StateNotifierProvider<AiChatController, AiChatState>((ref) {
  return AiChatController(ref);
});

class AiChatController extends StateNotifier<AiChatState> {
  final Ref _ref;
  AiChatController(this._ref) : super(const AiChatState());

  void setMode(String mode) {
    if (mode == state.mode) return;
    // Switching mode starts a fresh conversation rather than mixing
    // "answer my question" context into an in-progress order, or vice
    // versa — the two system prompts on the backend assume a clean start.
    state = AiChatState(mode: mode);
  }

  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty || state.sending) return;

    final userEntry = AiChatEntry(role: 'user', text: text.trim());
    state = state.copyWith(entries: [...state.entries, userEntry], sending: true);

    await _callAssistant();
  }

  /// Called when the user taps one of an assistant message's choice chips —
  /// sends the chosen option's label back as the next user turn, same as if
  /// they'd typed "أريد <label>" themselves. The backend's system prompt
  /// instructs the model to resolve a clear choice like this straight to
  /// add_to_cart rather than asking again.
  Future<void> resolveChoice(AiChatEntry sourceEntry, AiChoiceOption option) async {
    if (state.sending) return;
    sourceEntry.choicesResolved = true; // stops the chips from being tappable again
    state = state.copyWith(entries: [...state.entries]); // trigger rebuild for the chip state

    final userEntry = AiChatEntry(role: 'user', text: option.label);
    state = state.copyWith(entries: [...state.entries, userEntry], sending: true);

    await _callAssistant();
  }

  Future<void> _callAssistant() async {
    try {
      final history = state.entries.map((e) => {'role': e.role, 'content': e.text}).toList();
      final response = await _ref.read(aiAssistantRepositoryProvider).chat(mode: state.mode, history: history);

      final assistantEntry = AiChatEntry(
        role: 'assistant',
        text: response.reply,
        choices: response.choices,
        cartAdditions: response.cartAdditions,
      );
      state = state.copyWith(entries: [...state.entries, assistantEntry], sending: false);

      if (response.cartAdditions.isNotEmpty) {
        // The AI added these directly on the backend (see
        // ai_assistant_service.py's add_to_cart tool) — refresh so the
        // cart badge and cart screen reflect it immediately.
        _ref.invalidate(cartProvider);
      }
    } catch (e) {
      final errorEntry = AiChatEntry(role: 'assistant', text: 'حدث خطأ، حاول مرة أخرى.');
      state = state.copyWith(entries: [...state.entries, errorEntry], sending: false);
    }
  }

  void reset() {
    state = const AiChatState();
  }
}