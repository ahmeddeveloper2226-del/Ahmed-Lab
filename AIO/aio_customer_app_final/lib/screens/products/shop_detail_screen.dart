import 'package:flutter/material.dart';
import '../../core/utils/error_helpers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_staggered_animations/flutter_staggered_animations.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/helpers.dart';
import '../../data/models/product_model.dart';
import '../../data/services/cloudinary_upload_service.dart';
import '../../data/repositories/prescription_repository.dart';
import '../../providers/category_provider.dart';
import '../../providers/product_provider.dart';
import '../../providers/cart_provider.dart';
import '../../providers/shop_provider.dart';
import '../../widgets/common/fast_picks_section.dart';
import '../../widgets/common/loading_shimmer.dart';
import '../food/meal_builder_screen.dart';
import 'package:aio_customer_app/core/extensions/context_extensions.dart';

class ShopDetailScreen extends ConsumerWidget {
  final String shopId;

  const ShopDetailScreen({super.key, required this.shopId});

  // Header gradient per category — same scheme as the category's shop
  // list screen (shops_screen.dart's _headerGradient): Grocery = Green,
  // Clothes = Grey, Restaurants = Orange, Electronics = Blue,
  // Pharmacies = Light Blue. Falls back to the app's default blue for any
  // other/unrecognized category, or while the shop is still loading.
  LinearGradient _headerGradient(String? categoryId) {
    switch (categoryId) {
      case 'clothes':
        return const LinearGradient(
          colors: [Color(0xFF6B7280), Color(0xFF1C1C1E)], // Light Grey → Grey
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      case 'grocery':
        return const LinearGradient(
          colors: [Color(0xFF4ADE80), Color(0xFF16A34A)], // Fresh Green → Deep Green
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      case 'electronics':
        return const LinearGradient(
          colors: [Color(0xFF3B82F6), Color(0xFF1E3A8A)], // Blue → Dark Blue
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      case 'food':
        return const LinearGradient(
          colors: [Color(0xFFFDBA74), Color(0xFFF97316)], // Soft Peach → Vibrant Orange
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      case 'pharmacies':
        return const LinearGradient(
          colors: [Color(0xFF7DD3FC), Color(0xFF0284C7)], // Light Medical Blue → Professional Blue
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
        );
      default:
        return AppGradients.primary;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final productsAsync = ref.watch(productsForShopProvider(shopId));
    // Needed only to resolve which category this shop belongs to, so the
    // subcategory pill row lists the RIGHT subcategories (an electronics
    // shop shouldn't offer "بيتزا" as a filter) — this screen doesn't
    // otherwise use the shop's other fields.
    final shopAsync = ref.watch(shopDetailProvider(shopId));
    final selectedSubcategoryId = ref.watch(selectedSubcategoryProvider(shopId));
    final headerGradient = shopAsync.maybeWhen(
      data: (shop) => _headerGradient(shop.category_id),
      orElse: () => AppGradients.primary,
    );

    List<ProductResponse> visibleProducts(List<ProductResponse> products) {
      if (selectedSubcategoryId == null) return products;
      return products.where((p) => p.subcategory_id == selectedSubcategoryId).toList();
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      body: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          // Hero App Bar
          SliverAppBar(
            expandedHeight: 200,
            pinned: true,
            backgroundColor: AppColors.primaryBlue,
            flexibleSpace: FlexibleSpaceBar(
              background: Container(
                decoration: BoxDecoration(
                  gradient: headerGradient,
                ),
                child: SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(20, 60, 20, 20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 6,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.2),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.star_rounded, color: Colors.amber, size: 16),
                              SizedBox(width: 4),
                              Text(
                                '4.8',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w700,
                                  fontSize: 14,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          'منتجات المتجر',
                          style: TextStyle(
                            fontSize: 28,
                            fontWeight: FontWeight.w900,
                            color: Colors.white,
                          ),
                        ),
                      ],
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
                    color: Colors.white.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: const Icon(Icons.arrow_back_ios_new, color: Colors.white, size: 18),
                ),
              ),
            ),
            actions: [
              Padding(
                padding: const EdgeInsets.all(8),
                child: GestureDetector(
                  onTap: () => context.push('/cart'),
                  child: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: const Icon(Icons.shopping_cart_outlined, color: Colors.white, size: 20),
                  ),
                ),
              ),
            ],
          ),

          // Subcategory pill row — same pattern as the category shops
          // screen's chip selector, scoped to this shop's own category's
          // subcategories (resolved via shopAsync above).
          SliverToBoxAdapter(
            child: shopAsync.when(
              data: (shop) {
                final subcategoriesAsync = ref.watch(subcategoriesForCategoryProvider(shop.category_id));
                return subcategoriesAsync.when(
                  data: (subcategories) {
                    if (subcategories.isEmpty) return const SizedBox.shrink();
                    return Padding(
                      padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                      child: SizedBox(
                        height: 44,
                        child: ListView(
                          scrollDirection: Axis.horizontal,
                          children: [
                            _SubcategoryChip(
                              label: 'الكل',
                              selected: selectedSubcategoryId == null,
                              onTap: () => ref.read(selectedSubcategoryProvider(shopId).notifier).state = null,
                            ),
                            for (final sub in subcategories) ...[
                              const SizedBox(width: 8),
                              _SubcategoryChip(
                                label: sub.name,
                                selected: selectedSubcategoryId == sub.id,
                                onTap: () => ref.read(selectedSubcategoryProvider(shopId).notifier).state = sub.id,
                              ),
                            ],
                          ],
                        ),
                      ),
                    );
                  },
                  loading: () => const SizedBox.shrink(),
                  error: (_, __) => const SizedBox.shrink(),
                );
              },
              // Shop details still loading/failed — the products grid below
              // still renders independently (it doesn't depend on shopAsync),
              // this row just doesn't show until the category is known.
              loading: () => const SizedBox.shrink(),
              error: (_, __) => const SizedBox.shrink(),
            ),
          ),

          // ── AIO Fast Picks — this shop's own sale items only, 1 row sliding right ──
          SliverToBoxAdapter(
            child: productsAsync.when(
              data: (allProducts) {
                final saleProducts = allProducts.where((p) => p.is_on_sale).toList();
                return FastPicksSection(
                  products: saleProducts,
                  rows: 1,
                  padding: const EdgeInsets.fromLTRB(20, 16, 0, 4),
                );
              },
              loading: () => const SizedBox.shrink(),
              error: (_, __) => const SizedBox.shrink(),
            ),
          ),

          // Products Grid
          SliverPadding(
            padding: const EdgeInsets.all(20),
            sliver: productsAsync.when(
              data: (allProducts) {
                final products = visibleProducts(allProducts);
                return SliverGrid(
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  mainAxisSpacing: 16,
                  crossAxisSpacing: 16,
                  childAspectRatio: 0.75,
                ),
                delegate: SliverChildBuilderDelegate(
                  (context, index) {
                    final product = products[index];
                    return AnimationConfiguration.staggeredGrid(
                      position: index,
                      columnCount: 2,
                      duration: const Duration(milliseconds: 400),
                      child: ScaleAnimation(
                        child: FadeInAnimation(
                          child: _ProductCard(
                            product: product,
                            onAddToCart: () async {
                              await ref.read(cartProvider.notifier).updateItem(
                                product.id,
                                1,
                              );
                              if (context.mounted) {
                                context.showSnackBar('تمت الإضافة للسلة');
                              }
                            },
                          ),
                        ),
                      ),
                    );
                  },
                  childCount: products.length,
                ),
                );
              },
              loading: () => SliverGrid(
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  mainAxisSpacing: 16,
                  crossAxisSpacing: 16,
                  childAspectRatio: 0.75,
                ),
                delegate: SliverChildBuilderDelegate(
                  (context, index) => const ProductShimmerCard(),
                  childCount: 6,
                ),
              ),
              error: (err, _) => SliverToBoxAdapter(
                child: Center(child: Text(friendlyErrorMessage(err))),
              ),
            ),
          ),
        ],
      ),
      floatingActionButton: shopAsync.maybeWhen(
        data: (shop) {
          if (shop.category_id == 'pharmacies') {
            return FloatingActionButton(
              onPressed: () => _capturePrescription(context, ref, shopId),
              backgroundColor: AppColors.primaryBlue,
              child: const Icon(Icons.camera_alt_rounded, color: Colors.white),
            );
          }
          if (shop.category_id == 'food') {
            return FloatingActionButton.extended(
              onPressed: () => context.push('/shop/$shopId/meal-builder'),
              backgroundColor: const Color(0xFFF97316),
              icon: const Icon(Icons.auto_awesome_rounded, color: Colors.white),
              label: const Text('بناء الوجبة', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
            );
          }
          return null;
        },
        orElse: () => null,
      ),
    );
  }

  Future<void> _capturePrescription(BuildContext context, WidgetRef ref, String shopId) async {
    final picker = ImagePicker();
    final XFile? photo;
    try {
      photo = await picker.pickImage(source: ImageSource.camera, imageQuality: 85);
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('تعذر فتح الكاميرا. تحقق من إذن الوصول للكاميرا.')),
        );
      }
      return;
    }
    if (photo == null) return; // user cancelled

    if (!context.mounted) return;
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(child: CircularProgressIndicator()),
    );

    try {
      final imageUrl = await ref.read(cloudinaryUploadServiceProvider).uploadImage(photo.path);
      final prescription = await ref
          .read(prescriptionRepositoryProvider)
          .createPrescription(shopId: shopId, imageUrl: imageUrl);

      if (!context.mounted) return;
      Navigator.of(context).pop(); // close loading dialog
      context.push('/prescription/${prescription.id}');
    } catch (e) {
      if (!context.mounted) return;
      Navigator.of(context).pop();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('تعذر إرسال الروشتة. حاول مرة أخرى.')),
      );
    }
  }
}

class _ProductCard extends StatefulWidget {
  final dynamic product;
  final VoidCallback onAddToCart;

  const _ProductCard({required this.product, required this.onAddToCart});

  @override
  State<_ProductCard> createState() => _ProductCardState();
}

class _ProductCardState extends State<_ProductCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _addController;

  @override
  void initState() {
    super.initState();
    _addController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
  }

  @override
  void dispose() {
    _addController.dispose();
    super.dispose();
  }

  void _animateAdd() {
    _addController.forward().then((_) => _addController.reverse());
    widget.onAddToCart();
  }

  @override
  Widget build(BuildContext context) {
    final product = widget.product;
    final isOutOfStock = !product.in_stock;

    return GestureDetector(
      onTap: () => context.push('/product/${product.id}'),
      child: Container(
        decoration: BoxDecoration(
          color: isOutOfStock ? AppColors.background : Colors.white,
          borderRadius: BorderRadius.circular(24),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.04),
              blurRadius: 15,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Product image
            Expanded(
              child: Container(
                margin: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      AppColors.primaryBlue.withValues(alpha: 0.1),
                      AppColors.accentCyan.withValues(alpha: 0.05),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(18),
                ),
                child: (product.image_url != null && (product.image_url as String).isNotEmpty)
                    ? ClipRRect(
                        borderRadius: BorderRadius.circular(18),
                        child: Image.network(
                          product.image_url as String,
                          width: double.infinity,
                          fit: BoxFit.cover,
                          // Falls back to the placeholder icon instead of a
                          // broken-image glyph if the URL 404s or fails to load.
                          errorBuilder: (context, error, stackTrace) => Center(
                            child: Icon(
                              Icons.shopping_bag_outlined,
                              size: 40,
                              color: isOutOfStock
                                  ? AppColors.textMuted
                                  : AppColors.primaryBlue.withValues(alpha: 0.5),
                            ),
                          ),
                          loadingBuilder: (context, child, progress) {
                            if (progress == null) return child;
                            return const Center(
                              child: SizedBox(
                                width: 24,
                                height: 24,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              ),
                            );
                          },
                        ),
                      )
                    : Center(
                        child: Icon(
                          Icons.shopping_bag_outlined,
                          size: 40,
                          color: isOutOfStock
                              ? AppColors.textMuted
                              : AppColors.primaryBlue.withValues(alpha: 0.5),
                        ),
                      ),
              ),
            ),

            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(
                product.name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: isOutOfStock ? AppColors.textMuted : AppColors.textPrimary,
                ),
              ),
            ),
            const SizedBox(height: 4),

            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(
                Helpers.formatPrice(product.price),
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: isOutOfStock ? AppColors.textMuted : AppColors.primaryBlue,
                ),
              ),
            ),

            // Add button
            Padding(
              padding: const EdgeInsets.all(12),
              child: isOutOfStock
                  ? Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      decoration: BoxDecoration(
                        color: AppColors.divider,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Text(
                        'غير متوفر',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textMuted,
                        ),
                      ),
                    )
                  : GestureDetector(
                      onTap: _animateAdd,
                      child: AnimatedBuilder(
                        animation: _addController,
                        builder: (context, child) {
                          return Transform.scale(
                            scale: 1.0 + (_addController.value * 0.2),
                            child: Container(
                              width: double.infinity,
                              padding: const EdgeInsets.symmetric(vertical: 10),
                              decoration: BoxDecoration(
                                gradient: AppGradients.primary,
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: const Row(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Icon(Icons.add, color: Colors.white, size: 16),
                                  SizedBox(width: 4),
                                  Text(
                                    'أضف',
                                    style: TextStyle(
                                      fontSize: 12,
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
    );
  }
}

class _SubcategoryChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _SubcategoryChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 10),
        decoration: BoxDecoration(
          color: selected ? AppColors.primaryBlue : Colors.white,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(
            color: selected ? AppColors.primaryBlue : AppColors.divider,
          ),
        ),
        alignment: Alignment.center,
        child: Text(
          label,
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: selected ? Colors.white : AppColors.textPrimary,
          ),
        ),
      ),
    );
  }
}