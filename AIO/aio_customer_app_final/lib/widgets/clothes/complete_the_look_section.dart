import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/helpers.dart';
import '../../data/repositories/product_repository.dart';
import '../../providers/cart_provider.dart';
import '../../providers/product_provider.dart';

const _kClothesAccent = Color(0xFF7C3AED); // distinct purple accent — "Complete the Look" isn't the primary CTA on the page, so it doesn't compete visually with the blue Add-to-Cart button above it.
const _kClothesAccentBg = Color(0xFFF5F3FF);

/// AIO Exclusive — Clothes only. Shown under a clothing product's normal
/// details; renders nothing at all (not even a header) when the backend
/// has no suggestions, which covers both "this isn't a clothes product"
/// and "clothes product but nothing in stock to complete it with".
class CompleteTheLookSection extends ConsumerStatefulWidget {
  final String productId;
  const CompleteTheLookSection({super.key, required this.productId});

  @override
  ConsumerState<CompleteTheLookSection> createState() => _CompleteTheLookSectionState();
}

class _CompleteTheLookSectionState extends ConsumerState<CompleteTheLookSection> {
  final Set<String> _deselected = {}; // suggestions the customer tapped off before adding the outfit
  bool _addingOutfit = false;

  Future<void> _addOutfitToCart(List<CompleteLookSuggestion> suggestions) async {
    final idsToAdd = suggestions
        .where((s) => !_deselected.contains(s.product.id))
        .map((s) => s.product.id)
        .toList();
    if (idsToAdd.isEmpty) return;

    setState(() => _addingOutfit = true);
    try {
      final repo = ref.read(productRepositoryProvider);
      final result = await repo.addCompleteLookToCart(idsToAdd);
      ref.read(cartProvider.notifier).loadCart();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(
            result.skippedIds.isEmpty
                ? 'تمت إضافة الإطلالة كاملة للسلة'
                : 'تمت إضافة ${result.addedIds.length} قطعة، وبعض القطع لم تعد متوفرة',
          ),
          backgroundColor: _kClothesAccent,
        ));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تعذرت إضافة الإطلالة للسلة')));
      }
    } finally {
      if (mounted) setState(() => _addingOutfit = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final suggestionsAsync = ref.watch(completeTheLookProvider(widget.productId));

    return suggestionsAsync.when(
      loading: () => const SizedBox.shrink(),
      error: (e, _) => const SizedBox.shrink(),
      data: (suggestions) {
        if (suggestions.isEmpty) return const SizedBox.shrink();

        final selectedCount = suggestions.where((s) => !_deselected.contains(s.product.id)).length;
        final selectedTotal = suggestions
            .where((s) => !_deselected.contains(s.product.id))
            .fold<double>(0, (sum, s) => sum + (s.product.sale_price ?? s.product.price));

        return Container(
          margin: const EdgeInsets.fromLTRB(20, 0, 20, 24),
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: _kClothesAccentBg,
            borderRadius: BorderRadius.circular(24),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Text('✨', style: TextStyle(fontSize: 18)),
                  const SizedBox(width: 6),
                  const Text(
                    'أكمل الإطلالة',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: _kClothesAccent),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                'قطع تناسب هذا المنتج — اختار اللي يعجبك وأضفهم كلهم بضغطة واحدة',
                style: TextStyle(fontSize: 12.5, color: AppColors.textSecondary),
              ),
              const SizedBox(height: 14),
              SizedBox(
                height: 168,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: suggestions.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 12),
                  itemBuilder: (context, index) {
                    final s = suggestions[index];
                    final isSelected = !_deselected.contains(s.product.id);
                    return _SuggestionCard(
                      suggestion: s,
                      selected: isSelected,
                      onTap: () => context.push('/product/${s.product.id}'),
                      onToggle: () => setState(() {
                        if (isSelected) {
                          _deselected.add(s.product.id);
                        } else {
                          _deselected.remove(s.product.id);
                        }
                      }),
                    );
                  },
                ),
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: (selectedCount == 0 || _addingOutfit) ? null : () => _addOutfitToCart(suggestions),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _kClothesAccent,
                    foregroundColor: Colors.white,
                    disabledBackgroundColor: _kClothesAccent.withValues(alpha: 0.4),
                    padding: const EdgeInsets.symmetric(vertical: 15),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                  ),
                  child: _addingOutfit
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : Text(
                          selectedCount == 0
                              ? 'اختار قطعة على الأقل'
                              : 'أضف الإطلالة كاملة ($selectedCount) — ${Helpers.formatPrice(selectedTotal)}',
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _SuggestionCard extends StatelessWidget {
  final CompleteLookSuggestion suggestion;
  final bool selected;
  final VoidCallback onTap;
  final VoidCallback onToggle;

  const _SuggestionCard({
    required this.suggestion,
    required this.selected,
    required this.onTap,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    final product = suggestion.product;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 128,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: selected ? _kClothesAccent : Colors.transparent, width: 2),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Stack(
              children: [
                Container(
                  height: 90,
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: _kClothesAccentBg,
                    borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
                  ),
                  child: (product.image_url != null && product.image_url!.isNotEmpty)
                      ? ClipRRect(
                          borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
                          child: Image.network(
                            product.image_url!,
                            fit: BoxFit.cover,
                            width: double.infinity,
                            height: 90,
                            errorBuilder: (context, error, stack) =>
                                const Icon(Icons.checkroom_rounded, color: _kClothesAccent, size: 32),
                          ),
                        )
                      : const Icon(Icons.checkroom_rounded, color: _kClothesAccent, size: 32),
                ),
                Positioned(
                  top: 6,
                  right: 6,
                  child: GestureDetector(
                    onTap: onToggle,
                    child: Container(
                      padding: const EdgeInsets.all(3),
                      decoration: BoxDecoration(
                        color: selected ? _kClothesAccent : Colors.white,
                        shape: BoxShape.circle,
                        boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 4)],
                      ),
                      child: Icon(
                        selected ? Icons.check_rounded : Icons.close_rounded,
                        size: 14,
                        color: selected ? Colors.white : AppColors.textMuted,
                      ),
                    ),
                  ),
                ),
                Positioned(
                  bottom: 6,
                  right: 6,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(color: Colors.black.withValues(alpha: 0.55), borderRadius: BorderRadius.circular(10)),
                    child: Text(suggestion.slotLabel, style: const TextStyle(fontSize: 9.5, color: Colors.white, fontWeight: FontWeight.w700)),
                  ),
                ),
              ],
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 8, 8, 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    product.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    Helpers.formatPrice(product.sale_price ?? product.price),
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: _kClothesAccent),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
