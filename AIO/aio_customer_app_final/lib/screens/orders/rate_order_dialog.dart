import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/error_helpers.dart';
import '../../data/repositories/order_repository.dart';

/// Shown from order_detail_screen.dart when order.canBeReviewed is true.
/// Submits via OrderRepository.submitReview — the backend enforces the
/// order actually belongs to this customer and is delivered, and that it
/// hasn't already been reviewed (see review_service.py), so this dialog
/// only needs to handle the happy path plus a friendly error message.
class RateOrderDialog extends ConsumerStatefulWidget {
  final String orderId;
  const RateOrderDialog({super.key, required this.orderId});

  @override
  ConsumerState<RateOrderDialog> createState() => _RateOrderDialogState();
}

class _RateOrderDialogState extends ConsumerState<RateOrderDialog> {
  int _rating = 0;
  final _commentController = TextEditingController();
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _commentController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_rating == 0) {
      setState(() => _error = 'اختار تقييم من 1 إلى 5 نجوم أولاً');
      return;
    }
    setState(() { _submitting = true; _error = null; });
    try {
      final repo = ref.read(orderRepositoryProvider);
      await repo.submitReview(
        widget.orderId,
        rating: _rating,
        comment: _commentController.text.trim().isEmpty ? null : _commentController.text.trim(),
      );
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      setState(() { _submitting = false; _error = friendlyErrorMessage(e); });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      title: const Text('قيّم طلبك', style: TextStyle(fontWeight: FontWeight.w800)),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(5, (i) {
              final starIndex = i + 1;
              return IconButton(
                onPressed: _submitting ? null : () => setState(() => _rating = starIndex),
                icon: Icon(
                  starIndex <= _rating ? Icons.star_rounded : Icons.star_border_rounded,
                  color: AppColors.warning,
                  size: 32,
                ),
              );
            }),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _commentController,
            enabled: !_submitting,
            maxLines: 3,
            decoration: InputDecoration(
              hintText: 'اكتب رأيك (اختياري)...',
              filled: true,
              fillColor: AppColors.background,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 8),
            Text(_error!, style: const TextStyle(color: AppColors.error, fontSize: 12.5)),
          ],
        ],
      ),
      actions: [
        TextButton(
          onPressed: _submitting ? null : () => Navigator.of(context).pop(false),
          child: const Text('إلغاء'),
        ),
        ElevatedButton(
          onPressed: _submitting ? null : _submit,
          style: ElevatedButton.styleFrom(backgroundColor: AppColors.primaryBlue, foregroundColor: Colors.white),
          child: _submitting
              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
              : const Text('إرسال'),
        ),
      ],
    );
  }
}
