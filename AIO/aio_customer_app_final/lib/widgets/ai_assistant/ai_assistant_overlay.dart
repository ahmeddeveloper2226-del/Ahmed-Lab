import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../data/models/ai_chat_model.dart';
import '../../providers/ai_assistant_provider.dart';

/// Sits on top of MainShell's body via a Stack — see main_shell.dart. The
/// FAB is always visible (bottom-right, above the bottom nav bar); tapping
/// it opens a compact floating panel anchored to the same corner, NOT a
/// full-screen route — closing it just collapses the panel back to the FAB,
/// the conversation state stays alive in aiChatControllerProvider either way.
class AiAssistantOverlay extends ConsumerWidget {
  const AiAssistantOverlay({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isOpen = ref.watch(aiAssistantOpenProvider);
    final bottomInset = MediaQuery.of(context).padding.bottom;

    return Stack(
      children: [
        if (isOpen)
          Positioned(
            right: 16,
            bottom: 96 + bottomInset,
            child: const _AiAssistantPanel(),
          ),
        Positioned(
          right: 16,
          bottom: 96 + bottomInset,
          child: isOpen ? const SizedBox.shrink() : _buildFab(ref),
        ),
      ],
    );
  }

  Widget _buildFab(WidgetRef ref) {
    return GestureDetector(
      onTap: () => ref.read(aiAssistantOpenProvider.notifier).state = true,
      child: Container(
        width: 56,
        height: 56,
        decoration: BoxDecoration(
          gradient: AppGradients.primary,
          shape: BoxShape.circle,
          boxShadow: [BoxShadow(color: AppColors.primaryBlue.withValues(alpha: 0.4), blurRadius: 16, offset: const Offset(0, 6))],
        ),
        child: const Icon(Icons.smart_toy_rounded, color: Colors.white, size: 28),
      ),
    );
  }
}

class _AiAssistantPanel extends ConsumerStatefulWidget {
  const _AiAssistantPanel();

  @override
  ConsumerState<_AiAssistantPanel> createState() => _AiAssistantPanelState();
}

class _AiAssistantPanelState extends ConsumerState<_AiAssistantPanel> {
  final _textController = TextEditingController();
  final _scrollController = ScrollController();

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
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

  void _send() {
    final text = _textController.text;
    if (text.trim().isEmpty) return;
    _textController.clear();
    ref.read(aiChatControllerProvider.notifier).sendMessage(text);
    _scrollToBottom();
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(aiChatControllerProvider);
    final screenWidth = MediaQuery.of(context).size.width;
    final panelWidth = screenWidth - 32 < 360 ? screenWidth - 32 : 360.0;

    ref.listen(aiChatControllerProvider, (_, __) => _scrollToBottom());

    return Material(
      elevation: 12,
      borderRadius: BorderRadius.circular(24),
      clipBehavior: Clip.antiAlias,
      child: Container(
        width: panelWidth,
        height: 480,
        color: Colors.white,
        child: Column(
          children: [
            _buildHeader(),
            _buildModeToggle(chatState.mode),
            Expanded(
              child: chatState.entries.isEmpty
                  ? _buildEmptyState(chatState.mode)
                  : ListView.builder(
                      controller: _scrollController,
                      padding: const EdgeInsets.all(14),
                      itemCount: chatState.entries.length,
                      itemBuilder: (context, index) => _ChatBubble(entry: chatState.entries[index]),
                    ),
            ),
            if (chatState.sending)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 6),
                child: SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2)),
              ),
            _buildInputRow(chatState.sending),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: const BoxDecoration(gradient: AppGradients.primary),
      child: Row(
        children: [
          const Icon(Icons.smart_toy_rounded, color: Colors.white, size: 20),
          const SizedBox(width: 8),
          const Expanded(
            child: Text('المساعد الذكي', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
          ),
          GestureDetector(
            onTap: () => ref.read(aiAssistantOpenProvider.notifier).state = false,
            child: const Icon(Icons.close_rounded, color: Colors.white, size: 22),
          ),
        ],
      ),
    );
  }

  Widget _buildModeToggle(String mode) {
    return Padding(
      padding: const EdgeInsets.all(10),
      child: Row(
        children: [
          Expanded(child: _ModeButton(label: 'سؤال عادي', selected: mode == 'question', onTap: () => ref.read(aiChatControllerProvider.notifier).setMode('question'))),
          const SizedBox(width: 8),
          Expanded(child: _ModeButton(label: 'تحضير طلب', selected: mode == 'order', onTap: () => ref.read(aiChatControllerProvider.notifier).setMode('order'))),
        ],
      ),
    );
  }

  Widget _buildEmptyState(String mode) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Text(
          mode == 'order'
              ? 'قول لي عايز تطلب إيه، من أي تصنيف، وهساعدك تختار وتضيفه للسلة.'
              : 'اسألني أي سؤال عن التطبيق أو المنتجات.',
          textAlign: TextAlign.center,
          style: const TextStyle(color: AppColors.textMuted, fontSize: 13),
        ),
      ),
    );
  }

  Widget _buildInputRow(bool sending) {
    return Padding(
      padding: EdgeInsets.only(
        left: 10, right: 10, top: 6,
        bottom: 10 + MediaQuery.of(context).viewInsets.bottom * 0, // panel stays fixed-height; keyboard pushes the whole overlay via Positioned's own bottom in the parent if needed
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _textController,
              enabled: !sending,
              decoration: InputDecoration(
                hintText: 'اكتب رسالتك...',
                contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(20), borderSide: BorderSide.none),
                filled: true,
                fillColor: AppColors.background,
              ),
              onSubmitted: (_) => _send(),
            ),
          ),
          const SizedBox(width: 8),
          GestureDetector(
            onTap: sending ? null : _send,
            child: Container(
              width: 40,
              height: 40,
              decoration: const BoxDecoration(gradient: AppGradients.primary, shape: BoxShape.circle),
              child: const Icon(Icons.send_rounded, color: Colors.white, size: 18),
            ),
          ),
        ],
      ),
    );
  }
}

class _ModeButton extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;
  const _ModeButton({required this.label, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          color: selected ? AppColors.primaryBlue : AppColors.background,
          borderRadius: BorderRadius.circular(14),
        ),
        alignment: Alignment.center,
        child: Text(
          label,
          style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: selected ? Colors.white : AppColors.textPrimary),
        ),
      ),
    );
  }
}

class _ChatBubble extends ConsumerWidget {
  final AiChatEntry entry;
  const _ChatBubble({required this.entry});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isUser = entry.role == 'user';
    return Column(
      crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: [
        Align(
          alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
          child: Container(
            margin: const EdgeInsets.symmetric(vertical: 4),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            constraints: const BoxConstraints(maxWidth: 260),
            decoration: BoxDecoration(
              color: isUser ? AppColors.primaryBlue : AppColors.background,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Text(
              entry.text,
              style: TextStyle(color: isUser ? Colors.white : AppColors.textPrimary, fontSize: 13),
            ),
          ),
        ),
        if (entry.choices != null && entry.choices!.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Wrap(
              spacing: 6,
              runSpacing: 6,
              children: entry.choices!.map((option) {
                return GestureDetector(
                  onTap: entry.choicesResolved
                      ? null
                      : () => ref.read(aiChatControllerProvider.notifier).resolveChoice(entry, option),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: entry.choicesResolved ? AppColors.divider : Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: AppColors.primaryBlue.withValues(alpha: entry.choicesResolved ? 0.2 : 0.6)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(option.label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                        if (option.detail != null)
                          Text(option.detail!, style: const TextStyle(fontSize: 10, color: AppColors.textMuted)),
                      ],
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
        if (entry.cartAdditions.isNotEmpty)
          Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: AppColors.success.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                const Row(
                  children: [
                    Icon(Icons.check_circle_rounded, color: AppColors.success, size: 14),
                    SizedBox(width: 4),
                    Text('أُضيف للسلة', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppColors.success)),
                  ],
                ),
                const SizedBox(height: 4),
                ...entry.cartAdditions.map((item) => Text(
                      '${item.name} × ${item.quantity} — ${item.shopName}',
                      style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                    )),
              ],
            ),
          ),
      ],
    );
  }
}
