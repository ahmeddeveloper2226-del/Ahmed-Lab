import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';
import '../../data/models/medication_model.dart';
import '../../data/repositories/medication_repository.dart';
import '../../providers/cart_provider.dart';
import '../../providers/medication_provider.dart';

const _kMed = Color(0xFF0EA5E9);
const _kMedDark = Color(0xFF0369A1);
const _kMedBg = Color(0xFFF0F9FF);
const _kAlert = Color(0xFFEF4444);

class MedicationsScreen extends ConsumerWidget {
  const MedicationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final medsAsync = ref.watch(medicationsProvider);

    return Scaffold(
      backgroundColor: _kMedBg,
      body: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          SliverToBoxAdapter(
            child: Container(
              padding: const EdgeInsets.fromLTRB(20, 60, 20, 26),
              decoration: const BoxDecoration(
                gradient: LinearGradient(colors: [_kMed, _kMedDark], begin: Alignment.topLeft, end: Alignment.bottomRight),
                borderRadius: BorderRadius.vertical(bottom: Radius.circular(32)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      GestureDetector(
                        onTap: () => context.pop(),
                        child: Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(12)),
                          child: const Icon(Icons.arrow_forward_rounded, color: Colors.white, size: 20),
                        ),
                      ),
                      const SizedBox(width: 12),
                      const Text('💊', style: TextStyle(fontSize: 20)),
                      const SizedBox(width: 8),
                      const Text('تذكير إعادة الصرف', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w800)),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text('أضف أدويتك الدائمة وهنفكرك قبل ما تخلص', style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 13)),
                ],
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 100),
            sliver: medsAsync.when(
              loading: () => const SliverToBoxAdapter(
                child: Padding(padding: EdgeInsets.only(top: 60), child: Center(child: CircularProgressIndicator(color: _kMed))),
              ),
              error: (e, _) => SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.only(top: 60),
                  child: Center(
                    child: Column(children: [
                      const Text('تعذر تحميل أدويتك'),
                      TextButton(
                        onPressed: () => ref.invalidate(medicationsProvider),
                        child: const Text('إعادة المحاولة', style: TextStyle(color: _kMed)),
                      ),
                    ]),
                  ),
                ),
              ),
              data: (meds) {
                if (meds.isEmpty) return SliverToBoxAdapter(child: _EmptyState(onAdd: () => context.push('/medications/add')));
                return SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (context, index) => Padding(
                      padding: const EdgeInsets.only(bottom: 14),
                      child: _MedicationCard(medication: meds[index]),
                    ),
                    childCount: meds.length,
                  ),
                );
              },
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: _kMed,
        onPressed: () => context.push('/medications/add'),
        icon: const Icon(Icons.add_rounded),
        label: const Text('إضافة دواء', style: TextStyle(fontWeight: FontWeight.w700)),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  final VoidCallback onAdd;
  const _EmptyState({required this.onAdd});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 50),
      child: Column(
        children: [
          const Text('💊', style: TextStyle(fontSize: 56)),
          const SizedBox(height: 16),
          const Text('لسه معملتش أي تذكير', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          Text('أضف دوائك الدائم وهنفكرك تجدده قبل ما يخلص', style: TextStyle(fontSize: 13, color: AppColors.textSecondary), textAlign: TextAlign.center),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: onAdd,
            style: ElevatedButton.styleFrom(backgroundColor: _kMed, foregroundColor: Colors.white),
            child: const Text('أضف دواء'),
          ),
        ],
      ),
    );
  }
}

class _MedicationCard extends ConsumerStatefulWidget {
  final MedicationResponse medication;
  const _MedicationCard({required this.medication});

  @override
  ConsumerState<_MedicationCard> createState() => _MedicationCardState();
}

class _MedicationCardState extends ConsumerState<_MedicationCard> {
  bool _reordering = false;

  Future<void> _reorder() async {
    setState(() => _reordering = true);
    try {
      final repo = ref.read(medicationRepositoryProvider);
      final result = await repo.reorderMedication(widget.medication.id);
      ref.invalidate(medicationsProvider);
      if (result.addedToCart) ref.read(cartProvider.notifier).loadCart();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(result.message), backgroundColor: _kMedDark));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تعذرت إعادة الطلب الآن')));
      }
    } finally {
      if (mounted) setState(() => _reordering = false);
    }
  }

  Future<void> _confirmAndDelete() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('حذف التذكير؟'),
        content: Text('هيتم إيقاف تذكير "${widget.medication.medicineName}" نهائيًا.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(dialogContext).pop(false), child: const Text('إلغاء')),
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('حذف', style: TextStyle(color: AppColors.error, fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    final repo = ref.read(medicationRepositoryProvider);
    await repo.deleteMedication(widget.medication.id);
    ref.invalidate(medicationsProvider);
  }

  @override
  Widget build(BuildContext context) {
    final med = widget.medication;
    final condition = MedicationCondition.byId(med.condition);
    final urgent = med.daysLeft <= 0;

    // A rough visual sense of "used up" for the progress bar's fill only
    // — the reminder math itself is computed server-side from the real
    // pack size/dosage, this just re-derives the same ratio for display.
    final totalDaysSupply = med.packQuantity / (med.dailyDosage == 0 ? 1 : med.dailyDosage);
    final elapsed = totalDaysSupply - med.daysLeft;
    final progress = totalDaysSupply <= 0 ? 1.0 : (elapsed / totalDaysSupply).clamp(0.0, 1.0);

    return Dismissible(
      key: ValueKey(med.id),
      direction: DismissDirection.endToStart,
      confirmDismiss: (_) async {
        await _confirmAndDelete();
        return false; // deletion (if confirmed) already happened above; never let Dismissible auto-remove the tile itself — medicationsProvider invalidation drives the list update instead.
      },
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        decoration: BoxDecoration(color: AppColors.error, borderRadius: BorderRadius.circular(20)),
        child: const Icon(Icons.delete_rounded, color: Colors.white),
      ),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: urgent ? Border.all(color: _kAlert, width: 1.5) : null,
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 12, offset: const Offset(0, 4))],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(color: _kMedBg, borderRadius: BorderRadius.circular(14)),
                  alignment: Alignment.center,
                  child: Text(condition.emoji, style: const TextStyle(fontSize: 22)),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(med.medicineName, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700)),
                      const SizedBox(height: 2),
                      Text(condition.labelAr, style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                      if (med.pharmacyName != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 2),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Icon(Icons.local_pharmacy_rounded, size: 12, color: _kMedDark),
                              const SizedBox(width: 3),
                              Text(med.pharmacyName!, style: const TextStyle(fontSize: 11, color: _kMedDark, fontWeight: FontWeight.w600)),
                            ],
                          ),
                        ),
                    ],
                  ),
                ),
                if (med.needsRefillSoon)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(color: urgent ? _kAlert : Colors.orange, borderRadius: BorderRadius.circular(12)),
                    child: Text(
                      urgent ? 'خلص' : 'باقي ${med.daysLeft} يوم',
                      style: const TextStyle(fontSize: 10.5, color: Colors.white, fontWeight: FontWeight.w700),
                    ),
                  ),
                const SizedBox(width: 4),
                // Explicit delete button — the card is also swipe-to-delete
                // (see Dismissible above), but that gesture isn't always
                // discoverable, so give it a visible entry point too.
                GestureDetector(
                  onTap: _confirmAndDelete,
                  child: Padding(
                    padding: const EdgeInsets.all(4),
                    child: Icon(Icons.delete_outline_rounded, size: 20, color: AppColors.textMuted),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: progress,
                minHeight: 6,
                backgroundColor: AppColors.divider,
                valueColor: AlwaysStoppedAnimation(urgent ? _kAlert : _kMed),
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: _reordering ? null : _reorder,
                style: OutlinedButton.styleFrom(
                  foregroundColor: _kMedDark,
                  side: const BorderSide(color: _kMed),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                icon: _reordering
                    ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: _kMed))
                    : const Icon(Icons.refresh_rounded, size: 18),
                label: const Text('إعادة الطلب الآن', style: TextStyle(fontWeight: FontWeight.w700)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
