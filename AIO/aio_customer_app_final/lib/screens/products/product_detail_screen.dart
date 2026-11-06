import 'package:flutter/material.dart';
import '../../core/utils/error_helpers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/animations/custom_animations.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/helpers.dart';
import '../../core/constants/product_attributes.dart';
import '../../providers/product_provider.dart';
import '../../providers/cart_provider.dart';
import '../../widgets/clothes/complete_the_look_section.dart';
import '../../widgets/common/branch_availability_section.dart';
import 'package:aio_customer_app/core/extensions/context_extensions.dart';

class ProductDetailScreen extends ConsumerStatefulWidget {
  final String productId;

  const ProductDetailScreen({super.key, required this.productId});

  @override
  ConsumerState<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends ConsumerState<ProductDetailScreen>
    with SingleTickerProviderStateMixin {
  int _quantity = 1;
  late AnimationController _addController;

  // Customer's picks for "choices"/"multi_choices" attributes (e.g. size,
  // colour, extras) — String for a single choice, List<String> for
  // multi_choices. Keyed by attribute key. Reset whenever a different
  // product loads. NOTE: these selections currently only drive the
  // in-app picker UX/validation below — persisting the chosen
  // variant onto the actual cart/order line is a separate backend change
  // (cart_schemas/cart_service don't carry per-item attributes yet).
  final Map<String, dynamic> _selectedChoices = {};
  String? _selectedChoicesForProductId;

  void _ensureChoicesInitialized(String productId) {
    if (_selectedChoicesForProductId != productId) {
      _selectedChoices.clear();
      _selectedChoicesForProductId = productId;
    }
  }

  List<String> _customerChoiceKeysMissingSelection(Map<String, dynamic>? attributes) {
    if (attributes == null) return [];
    final missing = <String>[];
    for (final entry in attributes.entries) {
      final meta = kProductAttributeMeta[entry.key];
      if (meta == null || !isCustomerPickType(meta.type)) continue;
      final options = (entry.value as List?) ?? const [];
      if (options.isEmpty) continue;
      final picked = _selectedChoices[entry.key];
      final hasSelection = meta.type == ProductAttributeType.multiChoices
          ? (picked is List && picked.isNotEmpty)
          : (picked is String && picked.isNotEmpty);
      if (!hasSelection) missing.add(meta.labelAr);
    }
    return missing;
  }

  @override
  void initState() {
    super.initState();
    _addController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 500),
    );
  }

  @override
  void dispose() {
    _addController.dispose();
    super.dispose();
  }

  void _animateAdd() {
    _addController.forward().then((_) => _addController.reverse());
  }

  @override
  Widget build(BuildContext context) {
    final productAsync = ref.watch(productDetailProvider(widget.productId));

    return Scaffold(
      backgroundColor: AppColors.background,
      body: productAsync.when(
        data: (product) {
          _ensureChoicesInitialized(product.id);
          return CustomScrollView(
          physics: const BouncingScrollPhysics(),
          slivers: [
            // Parallax image header
            SliverAppBar(
              expandedHeight: 350,
              pinned: true,
              backgroundColor: Colors.white,
              flexibleSpace: FlexibleSpaceBar(
                background: Hero(
                  tag: 'product_${product.id}',
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          AppColors.primaryBlue.withValues(alpha: 0.15),
                          AppColors.accentCyan.withValues(alpha: 0.1),
                          AppColors.background,
                        ],
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                      ),
                    ),
                    child: Center(
                      child: ScaleBounce(
                        child: Container(
                          width: 180,
                          height: 180,
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.5),
                            borderRadius: BorderRadius.circular(40),
                            boxShadow: [
                              BoxShadow(
                                color: AppColors.primaryBlue.withValues(alpha: 0.1),
                                blurRadius: 40,
                                offset: const Offset(0, 20),
                              ),
                            ],
                          ),
                          child: (product.image_url != null && product.image_url!.isNotEmpty)
                              ? ClipRRect(
                                  borderRadius: BorderRadius.circular(40),
                                  child: Image.network(
                                    product.image_url!,
                                    width: 180,
                                    height: 180,
                                    fit: BoxFit.cover,
                                    // Falls back to the placeholder icon instead of a
                                    // broken-image glyph if the URL 404s or fails to load.
                                    errorBuilder: (context, error, stackTrace) => Icon(
                                      Icons.shopping_bag_rounded,
                                      size: 80,
                                      color: AppColors.primaryBlue.withValues(alpha: 0.6),
                                    ),
                                    loadingBuilder: (context, child, progress) {
                                      if (progress == null) return child;
                                      return const Center(
                                        child: CircularProgressIndicator(strokeWidth: 2),
                                      );
                                    },
                                  ),
                                )
                              : Icon(
                                  Icons.shopping_bag_rounded,
                                  size: 80,
                                  color: AppColors.primaryBlue.withValues(alpha: 0.6),
                                ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              leading: Padding(
                padding: const EdgeInsets.all(8),
                child: GestureDetector(
                  onTap: () => context.pop(),
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.8),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: const Icon(Icons.arrow_back_ios_new, size: 18),
                  ),
                ),
              ),
            ),

            // Content
            SliverToBoxAdapter(
              child: Container(
                padding: const EdgeInsets.all(24),
                decoration: const BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.vertical(
                    top: Radius.circular(32),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    FadeSlideIn(
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              product.name,
                              style: const TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.w900,
                                color: AppColors.textPrimary,
                              ),
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 12,
                              vertical: 6,
                            ),
                            decoration: BoxDecoration(
                              color: product.in_stock
                                  ? const Color(0xFFD1FAE5)
                                  : const Color(0xFFFEE2E2),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(
                              product.in_stock ? 'متوفر' : 'غير متوفر',
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                                color: product.in_stock
                                    ? const Color(0xFF065F46)
                                    : const Color(0xFF991B1B),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                    FadeSlideIn(
                      delay: const Duration(milliseconds: 100),
                      child: Text(
                        Helpers.formatPrice(product.price),
                        style: const TextStyle(
                          fontSize: 32,
                          fontWeight: FontWeight.w900,
                          color: AppColors.primaryBlue,
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    FadeSlideIn(
                      delay: const Duration(milliseconds: 150),
                      child: Text(
                        'المخزون: ${product.stock_quantity} قطعة',
                        style: const TextStyle(
                          fontSize: 14,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ),
                    const SizedBox(height: 32),

                    // Per-category product details (weight/expiry, size,
                    // colour, add-ons, company, dosage, etc — see
                    // core/constants/product_attributes.dart).
                    if (product.attributes != null && product.attributes!.isNotEmpty)
                      _ProductAttributesSection(
                        attributes: product.attributes!,
                        selected: _selectedChoices,
                        onChanged: () => setState(() {}),
                      ),

                    // Quantity stepper
                    if (product.in_stock) ...[
                      const FadeSlideIn(
                        delay: Duration(milliseconds: 200),
                        child: Text(
                          'الكمية',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                            color: AppColors.textPrimary,
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      FadeSlideIn(
                        delay: const Duration(milliseconds: 250),
                        child: Container(
                          padding: const EdgeInsets.all(4),
                          decoration: BoxDecoration(
                            color: AppColors.background,
                            borderRadius: BorderRadius.circular(16),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              _QuantityButton(
                                icon: Icons.remove,
                                onTap: () {
                                  if (_quantity > 1) {
                                    setState(() => _quantity--);
                                  }
                                },
                              ),
                              AnimatedSwitcher(
                                duration: const Duration(milliseconds: 200),
                                transitionBuilder: (child, animation) {
                                  return ScaleTransition(
                                    scale: animation,
                                    child: child,
                                  );
                                },
                                child: Container(
                                  key: ValueKey<int>(_quantity),
                                  width: 60,
                                  alignment: Alignment.center,
                                  child: Text(
                                    '$_quantity',
                                    style: const TextStyle(
                                      fontSize: 20,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                ),
                              ),
                              _QuantityButton(
                                icon: Icons.add,
                                onTap: () {
                                  if (_quantity < product.stock_quantity) {
                                    setState(() => _quantity++);
                                  }
                                },
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],

                    const SizedBox(height: 40),

                    // Add to cart button
                    if (product.in_stock)
                      FadeSlideIn(
                        delay: const Duration(milliseconds: 300),
                        child: GestureDetector(
                          onTap: () async {
                            final missing = _customerChoiceKeysMissingSelection(product.attributes);
                            if (missing.isNotEmpty) {
                              context.showSnackBar('من فضلك اختر: ${missing.join('، ')}');
                              return;
                            }
                            _animateAdd();
                            await ref.read(cartProvider.notifier).updateItem(
                              product.id,
                              _quantity,
                            );
                            if (context.mounted) {
                              context.showSnackBar('تمت الإضافة للسلة بنجاح');
                            }
                          },
                          child: AnimatedBuilder(
                            animation: _addController,
                            builder: (context, child) {
                              return Transform.scale(
                                scale: 1.0 + (_addController.value * 0.05),
                                child: Container(
                                  width: double.infinity,
                                  padding: const EdgeInsets.symmetric(vertical: 18),
                                  decoration: BoxDecoration(
                                    gradient: AppGradients.primary,
                                    borderRadius: BorderRadius.circular(20),
                                    boxShadow: [
                                      BoxShadow(
                                        color: AppColors.primaryBlue.withValues(alpha: 0.3),
                                        blurRadius: 20,
                                        offset: const Offset(0, 8),
                                      ),
                                    ],
                                  ),
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      const Icon(Icons.shopping_cart_outlined,
                                          color: Colors.white),
                                      const SizedBox(width: 12),
                                      Text(
                                        'أضف للسلة - ${Helpers.formatPrice(product.price * _quantity)}',
                                        style: const TextStyle(
                                          fontSize: 16,
                                          fontWeight: FontWeight.w700,
                                          color: Colors.white,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),

            // Branch availability — nearest branch with this product in
            // stock, plus a "preview all branches" list. The widget
            // itself renders nothing for a single-location shop (no
            // branches), so this is a no-op for the overwhelming
            // majority of products.
            SliverToBoxAdapter(
              child: BranchAvailabilitySection(productId: product.id),
            ),

            // AIO Exclusive — Complete the Look (clothes only; the widget
            // itself renders nothing if there's nothing to suggest).
            SliverToBoxAdapter(
              child: CompleteTheLookSection(productId: product.id),
            ),
          ],
        );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text(friendlyErrorMessage(err))),
      ),
    );
  }
}

class _ProductAttributesSection extends StatelessWidget {
  final Map<String, dynamic> attributes;
  final Map<String, dynamic> selected;
  final VoidCallback onChanged;

  const _ProductAttributesSection({
    required this.attributes,
    required this.selected,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final rows = <Widget>[];

    for (final entry in attributes.entries) {
      final meta = kProductAttributeMeta[entry.key];
      if (meta == null) continue;

      if (!isCustomerPickType(meta.type)) {
        // Informational field the store already set (weight, expiry,
        // company, dosage...) — shown read-only.
        String displayValue;
        if (meta.type == ProductAttributeType.boolean) {
          if (entry.value != true) continue;
          displayValue = 'نعم';
        } else {
          displayValue = '${entry.value}';
          if (displayValue.isEmpty) continue;
        }
        rows.add(Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Row(
            children: [
              Text(
                '${meta.labelAr}: ',
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.textMuted),
              ),
              Text(displayValue, style: const TextStyle(fontSize: 13, color: AppColors.textPrimary)),
            ],
          ),
        ));
        continue;
      }

      // Customer-pick field (size/colour/extras/...) — the store's
      // available options for THIS product, rendered as choice chips.
      final options = (entry.value as List?)?.cast<dynamic>() ?? const [];
      if (options.isEmpty) continue;
      final isMulti = meta.type == ProductAttributeType.multiChoices;

      rows.add(Padding(
        padding: const EdgeInsets.only(bottom: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              meta.labelAr,
              style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: options.map((optionRaw) {
                final option = '$optionRaw';
                final isSelected = isMulti
                    ? ((selected[entry.key] as List?)?.contains(option) ?? false)
                    : (selected[entry.key] == option);
                return ChoiceChip(
                  label: Text(option),
                  selected: isSelected,
                  selectedColor: AppColors.primaryBlue.withValues(alpha: 0.15),
                  labelStyle: TextStyle(
                    color: isSelected ? AppColors.primaryBlue : AppColors.textPrimary,
                    fontWeight: FontWeight.w600,
                  ),
                  onSelected: (_) {
                    if (isMulti) {
                      final current = List<String>.from((selected[entry.key] as List?) ?? const []);
                      if (current.contains(option)) {
                        current.remove(option);
                      } else {
                        current.add(option);
                      }
                      selected[entry.key] = current;
                    } else {
                      selected[entry.key] = isSelected ? null : option;
                    }
                    onChanged();
                  },
                );
              }).toList(),
            ),
          ],
        ),
      ));
    }

    if (rows.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: rows),
    );
  }
}

class _QuantityButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;

  const _QuantityButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.05),
              blurRadius: 8,
            ),
          ],
        ),
        child: Icon(icon, size: 20, color: AppColors.primaryBlue),
      ),
    );
  }
}