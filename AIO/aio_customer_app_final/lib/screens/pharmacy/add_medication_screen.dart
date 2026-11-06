import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';
import '../../data/models/medication_model.dart';
import '../../data/models/product_model.dart';
import '../../data/repositories/medication_repository.dart';
import '../../providers/medication_provider.dart';
import '../../providers/product_provider.dart';

const _kMed = Color(0xFF0EA5E9);
const _kMedDark = Color(0xFF0369A1);
const _kMedBg = Color(0xFFF0F9FF);

class AddMedicationScreen extends ConsumerStatefulWidget {
  const AddMedicationScreen({super.key});

  @override
  ConsumerState<AddMedicationScreen> createState() => _AddMedicationScreenState();
}

class _AddMedicationScreenState extends ConsumerState<AddMedicationScreen> {
  final _searchController = TextEditingController();
  final _customConditionController = TextEditingController();
  String _condition = 'other';
  bool _writingCustomCondition = false;
  int _packQuantity = 30;
  double _dailyDosage = 1;
  int _reminderDaysBefore = 3;
  ProductSearchResult? _linkedProduct;
  bool _saving = false;

  @override
  void dispose() {
    _searchController.dispose();
    _customConditionController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final linked = _linkedProduct;
    if (linked == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('اختار الدواء من قائمة صيدلية عشان نقدر نجدده لك تلقائيًا')),
      );
      return;
    }
    // If the user is writing their own condition name, that free text IS
    // the condition sent to the server — not the placeholder id 'other'.
    final customText = _customConditionController.text.trim();
    if (_writingCustomCondition && customText.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('اكتب اسم الحالة المرضية')),
      );
      return;
    }
    final conditionToSend = _writingCustomCondition ? customText : _condition;

    setState(() => _saving = true);
    try {
      final repo = ref.read(medicationRepositoryProvider);
      await repo.addMedication(
        productId: linked.id,
        medicineName: linked.name,
        condition: conditionToSend,
        packQuantity: _packQuantity,
        dailyDosage: _dailyDosage,
        reminderDaysBefore: _reminderDaysBefore,
      );
      ref.invalidate(medicationsProvider);
      if (mounted) context.pop();
    } catch (e) {
      if (mounted) {
        setState(() => _saving = false);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تعذرت إضافة الدواء')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final conditionsAsync = ref.watch(medicationConditionsProvider);

    return Scaffold(
      backgroundColor: _kMedBg,
      appBar: AppBar(
        backgroundColor: _kMedBg,
        elevation: 0,
        title: const Text('إضافة دواء', style: TextStyle(fontWeight: FontWeight.w800, color: AppColors.textPrimary)),
        iconTheme: const IconThemeData(color: AppColors.textPrimary),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 40),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('الدواء', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
            const SizedBox(height: 4),
            Text(
              'لازم تختار الدواء من صيدلية حقيقية عشان نقدر نضيفه لسلتك تلقائيًا وقت التذكير',
              style: TextStyle(fontSize: 11.5, color: AppColors.textSecondary),
            ),
            const SizedBox(height: 10),
            if (_linkedProduct != null)
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: _kMed)),
                child: Row(
                  children: [
                    const Icon(Icons.medication_rounded, color: _kMed),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(_linkedProduct!.name, style: const TextStyle(fontWeight: FontWeight.w700)),
                          Text(_linkedProduct!.shop_name, style: TextStyle(fontSize: 11.5, color: AppColors.textSecondary)),
                        ],
                      ),
                    ),
                    GestureDetector(
                      onTap: () => setState(() => _linkedProduct = null),
                      child: const Icon(Icons.close_rounded, size: 18, color: AppColors.textMuted),
                    ),
                  ],
                ),
              )
            else ...[
              TextField(
                controller: _searchController,
                onChanged: (_) => setState(() {}),
                decoration: InputDecoration(
                  hintText: 'ابحث عن اسم الدواء في الصيدليات...',
                  prefixIcon: const Icon(Icons.search_rounded, color: _kMed),
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
                ),
              ),
              if (_searchController.text.trim().length >= 2)
                Consumer(
                  builder: (context, ref, _) {
                    final resultsAsync = ref.watch(searchProductsProvider(
                      (query: _searchController.text.trim(), categoryId: 'pharmacies'),
                    ));
                    return resultsAsync.when(
                      loading: () => const Padding(
                        padding: EdgeInsets.only(top: 10),
                        child: Center(child: CircularProgressIndicator(color: _kMed)),
                      ),
                      error: (e, _) => const SizedBox.shrink(),
                      data: (results) {
                        if (results.isEmpty) {
                          return const Padding(
                            padding: EdgeInsets.only(top: 10),
                            child: Text('لا توجد نتائج', style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                          );
                        }
                        return Column(
                          children: results.take(5).map((p) {
                            return ListTile(
                              contentPadding: EdgeInsets.zero,
                              leading: const Icon(Icons.medication_outlined, color: _kMed),
                              title: Text(p.name, style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600)),
                              subtitle: Text(p.shop_name, style: const TextStyle(fontSize: 11.5)),
                              onTap: () => setState(() {
                                _linkedProduct = p;
                                _searchController.clear();
                              }),
                            );
                          }).toList(),
                        );
                      },
                    );
                  },
                ),
            ],
            const SizedBox(height: 20),
            const Text('الحالة المرضية', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
            const SizedBox(height: 10),
            conditionsAsync.when(
              loading: () => const SizedBox.shrink(),
              error: (e, _) => const SizedBox.shrink(),
              data: (conditions) => Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  ...conditions.map((c) {
                    final selected = !_writingCustomCondition && c.id == _condition;
                    return GestureDetector(
                      onTap: () => setState(() {
                        _condition = c.id;
                        _writingCustomCondition = false;
                      }),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                        decoration: BoxDecoration(color: selected ? _kMed : Colors.white, borderRadius: BorderRadius.circular(18)),
                        child: Text(
                          '${c.emoji} ${c.labelAr}',
                          style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: selected ? Colors.white : _kMedDark),
                        ),
                      ),
                    );
                  }),
                  // Lets the user type their own condition instead of being
                  // limited to the predefined list above.
                  GestureDetector(
                    onTap: () => setState(() => _writingCustomCondition = true),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                      decoration: BoxDecoration(
                        color: _writingCustomCondition ? _kMed : Colors.white,
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: Text(
                        '✍️ اكتب حالتك',
                        style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: _writingCustomCondition ? Colors.white : _kMedDark),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            if (_writingCustomCondition) ...[
              const SizedBox(height: 10),
              TextField(
                controller: _customConditionController,
                decoration: InputDecoration(
                  hintText: 'اكتب اسم الحالة المرضية...',
                  filled: true,
                  fillColor: Colors.white,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
                ),
              ),
            ],
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18)),
              child: Column(
                children: [
                  _StepperRow(
                    label: 'عدد الأقراص في العلبة',
                    value: '$_packQuantity',
                    onMinus: _packQuantity > 1 ? () => setState(() => _packQuantity--) : null,
                    onPlus: () => setState(() => _packQuantity++),
                  ),
                  const Divider(height: 24),
                  _StepperRow(
                    label: 'الجرعة اليومية (قرص/يوم)',
                    value: _dailyDosage.toStringAsFixed(_dailyDosage == _dailyDosage.roundToDouble() ? 0 : 1),
                    onMinus: _dailyDosage > 0.5 ? () => setState(() => _dailyDosage -= 0.5) : null,
                    onPlus: () => setState(() => _dailyDosage += 0.5),
                  ),
                  const Divider(height: 24),
                  _StepperRow(
                    label: 'التذكير قبل الخلاص بـ (يوم)',
                    value: '$_reminderDaysBefore',
                    onMinus: _reminderDaysBefore > 0 ? () => setState(() => _reminderDaysBefore--) : null,
                    onPlus: () => setState(() => _reminderDaysBefore++),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: (_saving || _linkedProduct == null) ? null : _save,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _kMed,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
                child: _saving
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Text('حفظ التذكير', style: TextStyle(fontWeight: FontWeight.w700)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StepperRow extends StatelessWidget {
  final String label;
  final String value;
  final VoidCallback? onMinus;
  final VoidCallback onPlus;

  const _StepperRow({required this.label, required this.value, required this.onMinus, required this.onPlus});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(child: Text(label, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13))),
        IconButton(onPressed: onMinus, icon: const Icon(Icons.remove_circle_outline_rounded, color: _kMed)),
        SizedBox(width: 32, child: Text(value, textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w800))),
        IconButton(onPressed: onPlus, icon: const Icon(Icons.add_circle_outline_rounded, color: _kMed)),
      ],
    );
  }
}
