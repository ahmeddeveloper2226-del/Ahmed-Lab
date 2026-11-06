import 'package:flutter/material.dart';
import '../../core/utils/error_helpers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_staggered_animations/flutter_staggered_animations.dart';
import 'package:go_router/go_router.dart';
import '../../core/animations/custom_animations.dart';
import '../../core/theme/app_theme.dart';
import '../../data/models/shop_model.dart';
import '../../providers/category_provider.dart';
import '../../providers/product_provider.dart';
import '../../providers/shop_provider.dart';
import '../../widgets/common/fast_picks_section.dart';
import '../../widgets/common/loading_shimmer.dart';
import '../grocery/grocery_quick_nav.dart';
import '../pharmacy/pharmacy_quick_nav.dart';
import '../electronics/electronics_quick_nav.dart';
import '../food/food_quick_nav.dart';

class ShopsScreen extends ConsumerWidget {
  final String categoryId;
  final String categoryName;

  const ShopsScreen({
    super.key,
    required this.categoryId,
    required this.categoryName,
  });

  // ═════════════════════════════════════════════════════════════════════════════
  //  Header gradient per category — Grocery = Green, Clothes = Grey,
  //  Restaurants = Orange, Electronics = Blue, Pharmacies = Light Blue.
  // ═════════════════════════════════════════════════════════════════════════════
  LinearGradient _headerGradient() {
    final name = categoryName.toLowerCase();

    if (name.contains('ملابس') || name.contains('clothes') || name.contains('fashion')) {
      return const LinearGradient(
        colors: [Color(0xFF6B7280), Color(0xFF1C1C1E)], // Light Grey → Grey
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
      );
    }
    if (name.contains('بقالة') || name.contains('grocery') || name.contains('خضار')) {
      return const LinearGradient(
        colors: [Color(0xFF4ADE80), Color(0xFF16A34A)], // Fresh Green → Deep Green
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
      );
    }
    if (name.contains('إلكترونيات') || name.contains('electronics') || name.contains('لابتوب') || name.contains('موبايل')) {
      return const LinearGradient(
        colors: [Color(0xFF3B82F6), Color(0xFF1E3A8A)], // Blue → Dark Blue
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
      );
    }
    if (name.contains('مطاعم') || name.contains('restaurants') || name.contains('أكل') || name.contains('food') || name.contains('برجر')) {
      return const LinearGradient(
        colors: [Color(0xFFFDBA74), Color(0xFFF97316)], // Soft Peach → Vibrant Orange
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
      );
    }
    if (name.contains('صيدلية') || name.contains('pharmacy') || name.contains('pharma') || name.contains('medicine') || name.contains('دواء')) {
      return const LinearGradient(
        colors: [Color(0xFF7DD3FC), Color(0xFF0284C7)], // Light Medical Blue → Professional Blue
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
      );
    }

    // Default fallback
    return AppGradients.primary;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final shopsAsync = ref.watch(shopsForCategoryProvider(categoryId));
    final subcategoriesAsync = ref.watch(subcategoriesForCategoryProvider(categoryId));
    final selectedSubcategoryId = ref.watch(selectedSubcategoryProvider(categoryId));

    // Filtered client-side rather than re-fetching per chip tap — a
    // category's shop list is small enough that this is instant and avoids
    // a network round trip on every tap.
    List<ShopResponse> visibleShops(List<ShopResponse> shops) {
      if (selectedSubcategoryId == null) return shops;
      return shops.where((s) => s.subcategory_id == selectedSubcategoryId).toList();
    }

    return Scaffold(
      backgroundColor: AppColors.background,
      body: Stack(
        children: [
          CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          // Animated header
          SliverToBoxAdapter(
            child: Container(
              padding: const EdgeInsets.fromLTRB(20, 60, 20, 24),
              decoration: BoxDecoration(
                gradient: _headerGradient(),
                borderRadius: const BorderRadius.vertical(
                  bottom: Radius.circular(32),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      GestureDetector(
                        onTap: () => context.pop(),
                        child: Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.2),
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: const Icon(
                            Icons.arrow_back_ios_new,
                            color: Colors.white,
                            size: 18,
                          ),
                        ),
                      ),
                      const Spacer(),
                      GestureDetector(
                        onTap: () => context.push('/cart'),
                        child: Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.2),
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: const Icon(
                            Icons.shopping_cart_outlined,
                            color: Colors.white,
                            size: 20,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  Text(
                    categoryName,
                    style: const TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.w900,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'اختر المحل المفضل لك',
                    style: TextStyle(
                      fontSize: 16,
                      color: Colors.white.withValues(alpha: 0.8),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Subcategory pill row — same visual pattern as the reference
          // screenshot's "All / Smartphones / Headphones / ..." selector,
          // just scoped to this category's own subcategories.
          SliverToBoxAdapter(
            child: subcategoriesAsync.when(
              data: (subcategories) {
                if (subcategories.isEmpty) return const SizedBox.shrink();
                return Padding(
                  padding: const EdgeInsets.only(top: 16),
                  child: SizedBox(
                    height: 44,
                    child: ListView(
                      scrollDirection: Axis.horizontal,
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      children: [
                        _SubcategoryChip(
                          label: 'الكل',
                          selected: selectedSubcategoryId == null,
                          onTap: () => ref.read(selectedSubcategoryProvider(categoryId).notifier).state = null,
                        ),
                        for (final sub in subcategories) ...[
                          const SizedBox(width: 8),
                          _SubcategoryChip(
                            label: sub.name,
                            selected: selectedSubcategoryId == sub.id,
                            onTap: () => ref.read(selectedSubcategoryProvider(categoryId).notifier).state = sub.id,
                          ),
                        ],
                      ],
                    ),
                  ),
                );
              },
              // No subcategories for this category (or still loading) — the
              // row simply doesn't render rather than showing an empty/loading
              // placeholder that would jump the layout once data arrives.
              loading: () => const SizedBox.shrink(),
              error: (_, __) => const SizedBox.shrink(),
            ),
          ),

          // ── AIO Fast Picks — this category's sale items only, 1 row sliding right ──
          SliverToBoxAdapter(
            child: Consumer(
              builder: (context, ref, _) {
                final fastPicksAsync = ref.watch(categoryFastPicksProvider(categoryId));
                return fastPicksAsync.when(
                  data: (products) => FastPicksSection(
                    products: products,
                    rows: 1,
                    padding: const EdgeInsets.fromLTRB(20, 20, 0, 4),
                  ),
                  loading: () => const SizedBox.shrink(),
                  error: (_, __) => const SizedBox.shrink(),
                );
              },
            ),
          ),

          // Shops list
          SliverPadding(
            padding: const EdgeInsets.all(20),
            sliver: shopsAsync.when(
              data: (allShops) {
                final shops = visibleShops(allShops);
                return shops.isEmpty
                  ? SliverToBoxAdapter(
                      child: FadeSlideIn(
                        child: Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const SizedBox(height: 60),
                              Icon(
                                Icons.storefront_outlined,
                                size: 80,
                                color: AppColors.textMuted.withValues(alpha: 0.5),
                              ),
                              const SizedBox(height: 16),
                              const Text(
                                'لا يوجد محلات حالياً',
                                style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.textSecondary,
                                ),
                              ),
                              const SizedBox(height: 8),
                              const Text(
                                'تفقد لاحقاً - محلات جديدة قادمة!',
                                style: TextStyle(
                                  fontSize: 14,
                                  color: AppColors.textMuted,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    )
                  : SliverList(
                      delegate: SliverChildBuilderDelegate(
                        (context, index) {
                          final shop = shops[index];
                          return AnimationConfiguration.staggeredList(
                            position: index,
                            duration: const Duration(milliseconds: 500),
                            child: SlideAnimation(
                              verticalOffset: 50,
                              child: FadeInAnimation(
                                child: GestureDetector(
                                  onTap: () => context.push('/shop/${shop.id}'),
                                  child: Container(
                                    margin: const EdgeInsets.only(bottom: 16),
                                    padding: const EdgeInsets.all(20),
                                    decoration: BoxDecoration(
                                      color: Colors.white,
                                      borderRadius: BorderRadius.circular(24),
                                      boxShadow: [
                                        BoxShadow(
                                          color: Colors.black.withValues(alpha: 0.04),
                                          blurRadius: 20,
                                          offset: const Offset(0, 4),
                                        ),
                                      ],
                                    ),
                                    child: Row(
                                      children: [
                                        Container(
                                          width: 64,
                                          height: 64,
                                          decoration: BoxDecoration(
                                            gradient: LinearGradient(
                                              colors: [
                                                AppColors.primaryBlue.withValues(alpha: 0.15),
                                                AppColors.accentCyan.withValues(alpha: 0.1),
                                              ],
                                              begin: Alignment.topLeft,
                                              end: Alignment.bottomRight,
                                            ),
                                            borderRadius: BorderRadius.circular(20),
                                          ),
                                          child: shop.logo_url != null && shop.logo_url!.isNotEmpty
                                              ? ClipRRect(
                                                  borderRadius: BorderRadius.circular(20),
                                                  child: Image.network(
                                                    shop.logo_url!,
                                                    width: 64,
                                                    height: 64,
                                                    fit: BoxFit.cover,
                                                    // Falls back to the store icon instead of a
                                                    // broken-image glyph if the URL 404s or the
                                                    // network request fails.
                                                    errorBuilder: (context, error, stackTrace) => const Icon(
                                                      Icons.store_rounded,
                                                      color: AppColors.primaryBlue,
                                                      size: 28,
                                                    ),
                                                    loadingBuilder: (context, child, progress) {
                                                      if (progress == null) return child;
                                                      return const Center(
                                                        child: SizedBox(
                                                          width: 20,
                                                          height: 20,
                                                          child: CircularProgressIndicator(strokeWidth: 2),
                                                        ),
                                                      );
                                                    },
                                                  ),
                                                )
                                              : const Icon(
                                                  Icons.store_rounded,
                                                  color: AppColors.primaryBlue,
                                                  size: 28,
                                                ),
                                        ),
                                        const SizedBox(width: 16),
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Text(
                                                shop.name,
                                                style: const TextStyle(
                                                  fontSize: 18,
                                                  fontWeight: FontWeight.w700,
                                                  color: AppColors.textPrimary,
                                                ),
                                              ),
                                              const SizedBox(height: 6),
                                              Row(
                                                children: [
                                                  Container(
                                                    padding: const EdgeInsets.symmetric(
                                                      horizontal: 8,
                                                      vertical: 4,
                                                    ),
                                                    decoration: BoxDecoration(
                                                      color: const Color(0xFFFEF3C7),
                                                      borderRadius: BorderRadius.circular(8),
                                                    ),
                                                    child: Row(
                                                      mainAxisSize: MainAxisSize.min,
                                                      children: [
                                                        const Icon(
                                                          Icons.star_rounded,
                                                          color: Color(0xFFF59E0B),
                                                          size: 14,
                                                        ),
                                                        const SizedBox(width: 4),
                                                        Text(
                                                          shop.rating.toStringAsFixed(1),
                                                          style: const TextStyle(
                                                            fontSize: 12,
                                                            fontWeight: FontWeight.w700,
                                                            color: Color(0xFF92400E),
                                                          ),
                                                        ),
                                                      ],
                                                    ),
                                                  ),
                                                  const SizedBox(width: 8),
                                                  const Text(
                                                    'توصيل سريع',
                                                    style: TextStyle(
                                                      fontSize: 12,
                                                      color: AppColors.textMuted,
                                                    ),
                                                  ),
                                                ],
                                              ),
                                            ],
                                          ),
                                        ),
                                        Container(
                                          padding: const EdgeInsets.all(10),
                                          decoration: BoxDecoration(
                                            color: AppColors.background,
                                            borderRadius: BorderRadius.circular(14),
                                          ),
                                          child: const Icon(
                                            Icons.arrow_forward_ios,
                                            color: AppColors.primaryBlue,
                                            size: 16,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          );
                        },
                        childCount: shops.length,
                      ),
                    );
              },
              loading: () => SliverList(
                delegate: SliverChildBuilderDelegate(
                  (context, index) => const Padding(
                    padding: EdgeInsets.only(bottom: 16),
                    child: ShopShimmerCard(),
                  ),
                  childCount: 5,
                ),
              ),
              error: (err, _) => SliverToBoxAdapter(
                child: Center(
                  child: Column(
                    children: [
                      const SizedBox(height: 60),
                      const Icon(Icons.error_outline, size: 48, color: AppColors.error),
                      const SizedBox(height: 16),
                      Text(friendlyErrorMessage(err)),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: () => ref.invalidate(shopsForCategoryProvider(categoryId)),
                        child: const Text('إعادة المحاولة'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
          ),
          if (categoryId == 'grocery') const GroceryQuickNav(),
          if (categoryId == 'pharmacies') const PharmacyQuickNav(),
          if (categoryId == 'electronics') const ElectronicsQuickNav(),
          if (categoryId == 'food') const FoodQuickNav(),
        ],
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




