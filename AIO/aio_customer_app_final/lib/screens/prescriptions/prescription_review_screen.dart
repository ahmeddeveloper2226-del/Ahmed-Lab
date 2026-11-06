import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/error_helpers.dart';
import '../../data/models/prescription_model.dart';
import '../../providers/cart_provider.dart';
import '../../providers/prescription_provider.dart';
import '../../data/repositories/prescription_repository.dart';

class PrescriptionReviewScreen extends ConsumerStatefulWidget {
  final String prescriptionId;
  const PrescriptionReviewScreen({super.key, required this.prescriptionId});

  @override
  ConsumerState<PrescriptionReviewScreen> createState() => _PrescriptionReviewScreenState();
}

class _PrescriptionReviewScreenState extends ConsumerState<PrescriptionReviewScreen> {
  bool _busy = false;

  Future<void> _removeItem(String itemId) async {
    setState(() => _busy = true);
    try {
      await ref.read(prescriptionRepositoryProvider).removeItem(widget.prescriptionId, itemId);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تعذر إزالة الدواء. حاول مرة أخرى.')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _approve(PrescriptionResponse prescription) async {
    setState(() => _busy = true);
    try {
      await ref.read(prescriptionRepositoryProvider).approve(prescription.id);

      // Every item is now guaranteed catalog-linked (the panel only lets
      // the pharmacist pick from their own products — see
      // PrescriptionItem's docstring), so every included item can go
      // straight through the normal cart flow with no exceptions to handle.
      final includedItems = prescription.items.where((i) => i.included).toList();
      for (final item in includedItems) {
        await ref.read(cartProvider.notifier).updateItem(item.product_id, item.quantity);
      }

      if (!mounted) return;
      context.go('/cart');
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تعذر قبول الروشتة. حاول مرة أخرى.')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _cancel(String prescriptionId) async {
    setState(() => _busy = true);
    try {
      await ref.read(prescriptionRepositoryProvider).cancel(prescriptionId);
      if (mounted) context.pop();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تعذر إلغاء الروشتة.')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final prescriptionAsync = ref.watch(prescriptionDetailProvider(widget.prescriptionId));

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('الروشتة'), backgroundColor: Colors.white, elevation: 0),
      body: prescriptionAsync.when(
        data: (prescription) => _buildBody(prescription),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text('تعذر تحميل الروشتة: ${friendlyErrorMessage(err)}')),
      ),
    );
  }

  Widget _buildBody(PrescriptionResponse prescription) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(18),
          child: Image.network(
            prescription.image_url,
            height: 220,
            width: double.infinity,
            fit: BoxFit.cover,
            errorBuilder: (_, __, ___) => Container(
              height: 220,
              color: Colors.white,
              child: const Icon(Icons.receipt_long_rounded, size: 48, color: AppColors.textMuted),
            ),
          ),
        ),
        const SizedBox(height: 20),
        _buildStatusSection(prescription),
      ],
    );
  }

  Widget _buildStatusSection(PrescriptionResponse prescription) {
    switch (prescription.status) {
      case 'pending_review':
        return Column(
          children: [
            const SizedBox(height: 20),
            const CircularProgressIndicator(),
            const SizedBox(height: 16),
            const Text(
              'الصيدلية بتراجع الروشتة الآن، هتوصلك قائمة الأدوية قريبًا',
              textAlign: TextAlign.center,
              style: TextStyle(color: AppColors.textMuted),
            ),
            const SizedBox(height: 20),
            TextButton(
              onPressed: _busy ? null : () => _cancel(prescription.id),
              child: const Text('إلغاء الروشتة', style: TextStyle(color: AppColors.error)),
            ),
          ],
        );

      case 'awaiting_customer_approval':
        final includedItems = prescription.items.where((i) => i.included).toList();
        final total = includedItems.fold<double>(0, (sum, i) => sum + (i.price * i.quantity));

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('الأدوية المقترحة من الصيدلية', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            const Text(
              'يمكنك إزالة أي دواء لا تريده قبل الموافقة',
              style: TextStyle(fontSize: 12, color: AppColors.textMuted),
            ),
            const SizedBox(height: 12),
            if (includedItems.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 20),
                child: Center(child: Text('تم إزالة كل الأدوية', style: TextStyle(color: AppColors.textMuted))),
              )
            else
              ...includedItems.map((item) => _MedicineTile(
                    item: item,
                    busy: _busy,
                    onRemove: () => _removeItem(item.id),
                  )),
            const SizedBox(height: 16),
            if (includedItems.isNotEmpty)
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('الإجمالي', style: TextStyle(fontWeight: FontWeight.w700)),
                  Text('${total.toStringAsFixed(2)} ج.م', style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.primaryBlue)),
                ],
              ),
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton(
                onPressed: (_busy || includedItems.isEmpty) ? null : () => _approve(prescription),
                child: _busy
                    ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Text('قبول وإضافة للسلة'),
              ),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: _busy ? null : () => _cancel(prescription.id),
              child: const Text('إلغاء الروشتة', style: TextStyle(color: AppColors.error)),
            ),
          ],
        );

      case 'approved':
        return const Padding(
          padding: EdgeInsets.symmetric(vertical: 40),
          child: Center(
            child: Column(
              children: [
                Icon(Icons.check_circle_rounded, color: AppColors.success, size: 48),
                SizedBox(height: 12),
                Text('تمت الموافقة على هذه الروشتة بالفعل'),
              ],
            ),
          ),
        );

      case 'rejected':
        return const Padding(
          padding: EdgeInsets.symmetric(vertical: 40),
          child: Center(
            child: Column(
              children: [
                Icon(Icons.cancel_rounded, color: AppColors.error, size: 48),
                SizedBox(height: 12),
                Text('اعتذرت الصيدلية عن تنفيذ هذه الروشتة', textAlign: TextAlign.center),
              ],
            ),
          ),
        );

      case 'cancelled':
      default:
        return const Padding(
          padding: EdgeInsets.symmetric(vertical: 40),
          child: Center(child: Text('تم إلغاء هذه الروشتة')),
        );
    }
  }
}

class _MedicineTile extends StatelessWidget {
  final PrescriptionItemResponse item;
  final bool busy;
  final VoidCallback onRemove;

  const _MedicineTile({required this.item, required this.busy, required this.onRemove});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item.name, style: const TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 4),
                Text(
                  'الكمية: ${item.quantity} — ${item.price.toStringAsFixed(2)} ج.م',
                  style: const TextStyle(fontSize: 12, color: AppColors.textMuted),
                ),
              ],
            ),
          ),
          IconButton(
            onPressed: busy ? null : onRemove,
            icon: const Icon(Icons.delete_outline_rounded, color: AppColors.error),
          ),
        ],
      ),
    );
  }
}