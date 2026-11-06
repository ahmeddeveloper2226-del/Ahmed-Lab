import 'dart:async';
import '../../core/utils/error_helpers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_staggered_animations/flutter_staggered_animations.dart';
import 'package:go_router/go_router.dart';
import '../../core/animations/custom_animations.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/helpers.dart';
import '../../data/models/category_model.dart';
import '../../data/models/shop_model.dart';
import '../../providers/category_provider.dart';
import '../../providers/product_provider.dart';
import '../../providers/profile_provider.dart';
import '../../providers/shop_provider.dart';
import '../../widgets/common/fast_picks_section.dart';
import '../../widgets/common/loading_shimmer.dart';

class CategoriesScreen extends ConsumerWidget {
  const CategoriesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final categoriesAsync = ref.watch(categoriesProvider);
    final addressesAsync = ref.watch(addressesProvider);

    return Scaffold(
      body: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          // ── Header (unchanged) ──
          SliverToBoxAdapter(
            child: Container(
              padding: const EdgeInsets.fromLTRB(24, 60, 24, 24),
              decoration: const BoxDecoration(
                gradient: AppGradients.primary,
                borderRadius: BorderRadius.vertical(bottom: Radius.circular(32)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      GestureDetector(
                        onTap: () => context.push('/addresses'),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: Colors.white.withValues(alpha: 0.2),
                                borderRadius: BorderRadius.circular(14),
                              ),
                              child: const Icon(Icons.location_on_outlined, color: Colors.white, size: 20),
                            ),
                            const SizedBox(width: 12),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('التوصيل إلى', style: TextStyle(fontSize: 12, color: Colors.white.withValues(alpha: 0.7))),
                                ConstrainedBox(
                                  constraints: const BoxConstraints(maxWidth: 180),
                                  child: addressesAsync.when(
                                    data: (addresses) {
                                      final defaultAddress = addresses.where((a) => a.is_default).firstOrNull ?? addresses.firstOrNull;
                                      return Text(
                                        defaultAddress?.full_address ?? 'أضف عنوان توصيل',
                                        overflow: TextOverflow.ellipsis,
                                        maxLines: 1,
                                        style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white),
                                      );
                                    },
                                    loading: () => const Text('...', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white)),
                                    error: (e, st) => const Text('أضف عنوان توصيل', style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Colors.white)),
                                  ),
                                ),
                              ],
                            ),
                          ],
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
                          child: const Icon(Icons.shopping_cart_outlined, color: Colors.white, size: 20),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  const Text('اكتشف كل شيء', style: TextStyle(fontSize: 32, fontWeight: FontWeight.w900, color: Colors.white, height: 1.2)),
                  const Text('في مكان واحد', style: TextStyle(fontSize: 32, fontWeight: FontWeight.w300, color: Colors.white, height: 1.2)),
                ],
              ),
            ),
          ),

          // ── Categories: 2 columns, soft gradient cards with colored glows ──
          SliverPadding(
            padding: const EdgeInsets.all(20),
            sliver: categoriesAsync.when(
              data: (categories) {
                if (categories.isEmpty) {
                  return SliverToBoxAdapter(
                    child: FadeSlideIn(
                      child: Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const SizedBox(height: 60),
                            Container(
                              width: 140,
                              height: 140,
                              decoration: BoxDecoration(
                                gradient: LinearGradient(
                                  colors: [
                                    AppColors.primaryBlue.withValues(alpha: 0.1),
                                    AppColors.accentCyan.withValues(alpha: 0.05),
                                  ],
                                ),
                                shape: BoxShape.circle,
                              ),
                              child: Icon(
                                Icons.category_outlined,
                                size: 56,
                                color: AppColors.primaryBlue.withValues(alpha: 0.4),
                              ),
                            ),
                            const SizedBox(height: 24),
                            const Text(
                              'سيتم اضافة فئات قريبا',
                              style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
                            ),
                          ],
                        ),
                      ),
                    ),
                  );
                }
                return SliverGrid(
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 4,
                    mainAxisSpacing: 10,
                    crossAxisSpacing: 10,
                    childAspectRatio: 0.8,
                  ),
                  delegate: SliverChildBuilderDelegate(
                    (context, index) {
                      final category = categories[index];
                      final icon = Helpers.getCategoryIcon(category.id);
                      final imageUrl = _getCategoryImageUrl(category);
                      final colors = _getCategoryColors(category);

                      return AnimationConfiguration.staggeredGrid(
                        position: index,
                        columnCount: 4,
                        duration: const Duration(milliseconds: 500),
                        child: ScaleAnimation(
                          child: FadeInAnimation(
                            child: _CategoryCard(
                              category: category,
                              colors: colors,
                              icon: icon,
                              imageUrl: imageUrl,
                              onTap: () => context.push('/shops/${category.id}?name=${category.name}'),
                            ),
                          ),
                        ),
                      );
                    },
                    childCount: categories.length,
                  ),
                );
              },
              loading: () => SliverGrid(
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 4,
                  mainAxisSpacing: 10,
                  crossAxisSpacing: 10,
                  childAspectRatio: 0.8,
                ),
                delegate: SliverChildBuilderDelegate(
                  (context, index) => const CategoryShimmerCard(),
                  childCount: 8,
                ),
              ),
              error: (err, _) => SliverToBoxAdapter(
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.error_outline, size: 48, color: AppColors.error),
                      const SizedBox(height: 16),
                      Text(friendlyErrorMessage(err)),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        onPressed: () => ref.invalidate(categoriesProvider),
                        child: const Text('إعادة المحاولة'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),

          // ── Promo banner carousel — grocery & clothes, swipeable ──
          const SliverToBoxAdapter(child: _PromoBannerCarousel()),

          // ── AIO Fast Picks — sale items across every category, 1 row sliding right ──
          SliverToBoxAdapter(
            child: Consumer(
              builder: (context, ref, _) {
                final fastPicksAsync = ref.watch(fastPicksProvider);
                return fastPicksAsync.when(
                  data: (products) => FastPicksSection(products: products, rows: 1),
                  loading: () => Padding(
                    padding: const EdgeInsets.fromLTRB(20, 24, 0, 20),
                    child: SizedBox(
                      height: 178,
                      child: ListView.separated(
                        scrollDirection: Axis.horizontal,
                        physics: const NeverScrollableScrollPhysics(),
                        itemCount: 4,
                        separatorBuilder: (_, __) => const SizedBox(width: 12),
                        itemBuilder: (_, __) => const FastPickShimmerCard(),
                      ),
                    ),
                  ),
                  error: (_, __) => const SizedBox.shrink(),
                );
              },
            ),
          ),

          // ── Top rated stores, with a category filter row ──
          const SliverToBoxAdapter(child: _TopRatedStoresSection()),
        ],
      ),
    );
  }

  // ═════════════════════════════════════════════════════════════════════════════
  //  Category Colors — Clothes = Grey, Electronics = Dark Blue
  // ═════════════════════════════════════════════════════════════════════════════
  List<Color> _getCategoryColors(CategoryResponse category) {
    final name = category.name.toLowerCase();

    if (name.contains('ملابس') || name.contains('clothes') || name.contains('fashion')) {
      return [const Color(0xFF6B7280), const Color(0xFF1C1C1E)]; // Light Grey → Grey
    }
    if (name.contains('بقالة') || name.contains('grocery') || name.contains('خضار')) {
      return [const Color(0xFF4ADE80), const Color(0xFF16A34A)]; // Fresh Green → Deep Green
    }
    if (name.contains('إلكترونيات') || name.contains('electronics') || name.contains('لابتوب') || name.contains('موبايل')) {
      return [const Color(0xFF3B82F6), const Color(0xFF1E3A8A)]; // Blue → Dark Blue
    }
    if (name.contains('مطاعم') || name.contains('restaurants') || name.contains('أكل') || name.contains('food') || name.contains('برجر')) {
      return [const Color(0xFFFDBA74), const Color(0xFFF97316)]; // Soft Peach → Vibrant Orange
    }
    if (name.contains('صيدلية') || name.contains('pharmacy') || name.contains('pharma') || name.contains('medicine') || name.contains('دواء')) {
      return [const Color(0xFF7DD3FC), const Color(0xFF0284C7)]; // Light Medical Blue → Professional Blue
    }

    // Default fallback
    return [const Color(0xFF3B82F6), const Color(0xFF1E3A8A)];
  }

  // ═════════════════════════════════════════════════════════════════════════════
  //  Images — replace these URLs with your own
  // ═════════════════════════════════════════════════════════════════════════════
  String _getCategoryImageUrl(CategoryResponse category) {
    if (category.imageUrl != null && category.imageUrl!.isNotEmpty) {
      return category.imageUrl!;
    }
    final name = category.name.toLowerCase();

    if (name.contains('ملابس') || name.contains('clothes') || name.contains('fashion')) {
      return 'https://res.cloudinary.com/dhanjaap5/image/upload/v1785712901/clothes-removebg-preview_io4old.png';
    }
    if (name.contains('بقالة') || name.contains('grocery') || name.contains('خضار')) {
      return 'https://res.cloudinary.com/dhanjaap5/image/upload/v1785712208/grocery-removebg-preview_uqmvah.png';
    }
    if (name.contains('مطاعم') || name.contains('food') || name.contains('مطعم') || name.contains('برجر')) {
      return 'https://res.cloudinary.com/dhanjaap5/image/upload/v1785712733/new_food-removebg-preview_vuhtmd.png';
    }
    if (name.contains('صيدليات') || name.contains('pharma') || name.contains('medicine') || name.contains('دواء')) {
      return 'https://res.cloudinary.com/dhanjaap5/image/upload/v1785712445/medicine-removebg-preview_pega0h.png';
    }
    if (name.contains('إلكترونيات') || name.contains('electronics') || name.contains('لابتوب') || name.contains('موبايل')) {
      return 'https://res.cloudinary.com/dhanjaap5/image/upload/v1785712143/electronics-removebg-preview_hpfygi.png';
    }

    // Default fallback
    return 'https://res.cloudinary.com/dhanjaap5/image/upload/v1785712255/food-removebg-preview_nkl0zs.png';
  }
}

// ═════════════════════════════════════════════════════════════════════════════
//  Soft Gradient Category Card with Colored Glow
// ═════════════════════════════════════════════════════════════════════════════

class _CategoryCard extends StatelessWidget {
  const _CategoryCard({
    required this.category,
    required this.colors,
    required this.icon,
    required this.imageUrl,
    required this.onTap,
  });

  final CategoryResponse category;
  final List<Color> colors;
  final IconData icon;
  final String imageUrl;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final glowColor = colors[1];

    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          // Soft gradient background
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              colors[0],
              colors[1],
            ],
          ),
          borderRadius: BorderRadius.circular(16),
          // Soft neon border — thinner at this size, a 2px border on a
          // quarter-width tile reads as chunky rather than a glow edge.
          border: Border.all(
            color: colors[0].withValues(alpha: 0.6),
            width: 1,
          ),
          // Colored glow shadow — scaled down; the original's 24-40px
          // blur radii were sized for a half-width card and just bleed
          // into neighboring tiles at quarter-width.
          boxShadow: [
            BoxShadow(
              color: glowColor.withValues(alpha: 0.45),
              blurRadius: 10,
              offset: const Offset(0, 5),
            ),
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.12),
              blurRadius: 6,
              offset: const Offset(0, 3),
            ),
          ],
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(16),
          child: Stack(
            children: [
              // ── Soft top gloss ──
              Positioned(
                top: -16,
                left: -10,
                right: -10,
                child: Container(
                  height: 40,
                  decoration: BoxDecoration(
                    gradient: RadialGradient(
                      center: const Alignment(0, 1),
                      radius: 0.8,
                      colors: [
                        Colors.white.withValues(alpha: 0.25),
                        Colors.white.withValues(alpha: 0.05),
                        Colors.transparent,
                      ],
                      stops: const [0.0, 0.5, 1.0],
                    ),
                  ),
                ),
              ),

              // ── Bottom inner shadow ──
              Positioned(
                bottom: 0,
                left: 0,
                right: 0,
                height: 30,
                child: Container(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.bottomCenter,
                      end: Alignment.topCenter,
                      colors: [
                        Colors.black.withValues(alpha: 0.12),
                        Colors.transparent,
                      ],
                    ),
                  ),
                ),
              ),

              // ── Center product image ──
              Positioned.fill(
                child: Center(
                  child: Container(
                    margin: const EdgeInsets.only(bottom: 22),
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.15),
                          blurRadius: 6,
                          offset: const Offset(0, 3),
                        ),
                      ],
                    ),
                    child: ClipOval(
                      child: Image.network(
                        imageUrl,
                        width: 44,
                        height: 44,
                        fit: BoxFit.cover,
                        loadingBuilder: (context, child, loadingProgress) {
                          if (loadingProgress == null) return child;
                          return Container(
                            color: Colors.white.withValues(alpha: 0.15),
                            child: Center(
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white.withValues(alpha: 0.7),
                              ),
                            ),
                          );
                        },
                        errorBuilder: (_, __, ___) => Container(
                          color: Colors.white.withValues(alpha: 0.15),
                          child: Icon(icon, size: 20, color: Colors.white.withValues(alpha: 0.9)),
                        ),
                      ),
                    ),
                  ),
                ),
              ),

              // ── Bottom semi-transparent pill with neon border ──
              Positioned(
                bottom: 6,
                left: 6,
                right: 6,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 5),
                  decoration: BoxDecoration(
                    color: colors[1].withValues(alpha: 0.45),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: colors[0].withValues(alpha: 0.60),
                      width: 1,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: glowColor.withValues(alpha: 0.35),
                        blurRadius: 5,
                        spreadRadius: 0,
                      ),
                    ],
                  ),
                  child: Text(
                    category.name,
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w800,
                      color: Colors.white,
                      letterSpacing: 0.2,
                    ),
                    overflow: TextOverflow.ellipsis,
                    maxLines: 1,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ═════════════════════════════════════════════════════════════════════════════
//  Promo Banner Carousel — swipeable, one image reveals the next (grocery/clothes)
// ═════════════════════════════════════════════════════════════════════════════

class _PromoBannerCarousel extends StatefulWidget {
  const _PromoBannerCarousel();

  @override
  State<_PromoBannerCarousel> createState() => _PromoBannerCarouselState();
}

class _PromoBannerCarouselState extends State<_PromoBannerCarousel> {
  static const _banners = [
    (
      imageUrl: 'https://res.cloudinary.com/dhanjaap5/image/upload/v1785727587/new_one_vibuqv.png',
      categoryId: 'grocery',
      categoryName: 'البقالة',
    ),
    (
      imageUrl: 'https://res.cloudinary.com/dhanjaap5/image/upload/v1785727589/second_newone_rh0juo.png',
      categoryId: 'clothes',
      categoryName: 'الملابس',
    ),
  ];

  late final PageController _controller;
  Timer? _autoSlideTimer;
  int _currentPage = 0;

  @override
  void initState() {
    super.initState();
    _controller = PageController();
    // Auto-advances like a real app's promo carousel — the user can still
    // swipe manually at any time; each manual swipe just resets this timer
    // via onPageChanged below rather than fighting it.
    _autoSlideTimer = Timer.periodic(const Duration(seconds: 4), (_) {
      if (!_controller.hasClients) return;
      final next = (_currentPage + 1) % _banners.length;
      _controller.animateToPage(
        next,
        duration: const Duration(milliseconds: 500),
        curve: Curves.easeInOut,
      );
    });
  }

  @override
  void dispose() {
    _autoSlideTimer?.cancel();
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 0),
      child: Column(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: Container(
              height: 220,
              width: double.infinity,
              color: AppColors.background,
              child: PageView.builder(
                controller: _controller,
                itemCount: _banners.length,
                onPageChanged: (index) => setState(() => _currentPage = index),
                itemBuilder: (context, index) {
                  final banner = _banners[index];
                  return GestureDetector(
                    onTap: () => context.push('/shops/${banner.categoryId}?name=${banner.categoryName}'),
                    child: Image.network(
                      banner.imageUrl,
                      // BoxFit.cover was cropping the top/bottom of these
                      // specific images because the fixed 150px height
                      // didn't match their actual aspect ratio. .contain
                      // guarantees the WHOLE image is always visible
                      // regardless of its real proportions — the taller
                      // 220px frame plus the background color behind it
                      // means any leftover space on the sides reads as a
                      // clean margin rather than an awkward letterbox gap.
                      fit: BoxFit.contain,
                      width: double.infinity,
                      loadingBuilder: (context, child, progress) {
                        if (progress == null) return child;
                        return Container(
                          color: AppColors.background,
                          child: const Center(child: CircularProgressIndicator(strokeWidth: 2)),
                        );
                      },
                      errorBuilder: (_, __, ___) => Container(color: AppColors.background),
                    ),
                  );
                },
              ),
            ),
          ),
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(
              _banners.length,
              (index) => AnimatedContainer(
                duration: const Duration(milliseconds: 250),
                margin: const EdgeInsets.symmetric(horizontal: 3),
                width: _currentPage == index ? 18 : 6,
                height: 6,
                decoration: BoxDecoration(
                  color: _currentPage == index ? AppColors.primaryBlue : AppColors.divider,
                  borderRadius: BorderRadius.circular(3),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ═════════════════════════════════════════════════════════════════════════════
//  Top Rated Stores — category filter chips + horizontally scrolling shop cards
// ═════════════════════════════════════════════════════════════════════════════

class _TopRatedStoresSection extends ConsumerWidget {
  const _TopRatedStoresSection();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final categoriesAsync = ref.watch(categoriesProvider);
    final selectedCategoryId = ref.watch(topRatedCategoryFilterProvider);
    final topRatedAsync = ref.watch(topRatedShopsProvider);

    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 28, 20, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'الأعلى تقييمًا',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: AppColors.textPrimary),
          ),
          const SizedBox(height: 14),

          // Category filter chips — same pattern as the subcategory pill
          // row elsewhere in the app, just filtering top-level categories
          // here instead of subcategories within one shop/category.
          categoriesAsync.when(
            data: (categories) {
              if (categories.isEmpty) return const SizedBox.shrink();
              return SizedBox(
                height: 40,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  children: [
                    _FilterChip(
                      label: 'الكل',
                      selected: selectedCategoryId == null,
                      onTap: () => ref.read(topRatedCategoryFilterProvider.notifier).state = null,
                    ),
                    for (final category in categories) ...[
                      const SizedBox(width: 8),
                      _FilterChip(
                        label: category.name,
                        selected: selectedCategoryId == category.id,
                        onTap: () => ref.read(topRatedCategoryFilterProvider.notifier).state = category.id,
                      ),
                    ],
                  ],
                ),
              );
            },
            loading: () => const SizedBox(height: 40),
            error: (_, __) => const SizedBox.shrink(),
          ),

          const SizedBox(height: 16),

          topRatedAsync.when(
            data: (shops) {
              if (shops.isEmpty) {
                return const Padding(
                  padding: EdgeInsets.symmetric(vertical: 24),
                  child: Center(
                    child: Text('لا توجد متاجر في هذا التصنيف بعد', style: TextStyle(color: AppColors.textMuted)),
                  ),
                );
              }
              return SizedBox(
                height: 168,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: shops.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 12),
                  itemBuilder: (context, index) => _TopRatedShopCard(shop: shops[index]),
                ),
              );
            },
            loading: () => const SizedBox(
              height: 168,
              child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
            ),
            error: (err, _) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 24),
              child: Center(child: Text('تعذر تحميل المتاجر: ${friendlyErrorMessage(err)}')),
            ),
          ),
        ],
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _FilterChip({required this.label, required this.selected, required this.onTap});

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
          border: Border.all(color: selected ? AppColors.primaryBlue : AppColors.divider),
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

class _TopRatedShopCard extends StatelessWidget {
  final ShopResponse shop;
  const _TopRatedShopCard({required this.shop});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => context.push('/shop/${shop.id}'),
      child: Container(
        width: 140,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(18),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 12, offset: const Offset(0, 4))],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: SizedBox(
                width: double.infinity,
                height: 80,
                child: (shop.logo_url != null && shop.logo_url!.isNotEmpty)
                    ? Image.network(
                        shop.logo_url!,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => Container(
                          color: AppColors.background,
                          child: const Icon(Icons.storefront_rounded, color: AppColors.primaryBlue),
                        ),
                      )
                    : Container(
                        color: AppColors.background,
                        child: const Icon(Icons.storefront_rounded, color: AppColors.primaryBlue),
                      ),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              shop.name,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                const Icon(Icons.star_rounded, color: Colors.amber, size: 16),
                const SizedBox(width: 2),
                Text(
                  shop.rating.toStringAsFixed(1),
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.textMuted),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}