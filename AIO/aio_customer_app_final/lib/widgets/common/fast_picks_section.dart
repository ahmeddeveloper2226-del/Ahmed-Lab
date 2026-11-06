import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:shimmer/shimmer.dart';
import '../../core/theme/app_theme.dart';
import '../../data/models/product_model.dart';

// ═════════════════════════════════════════════════════════════════════════════
//  AIO Fast Picks — shared "fire sale" rail used in three places:
//    • Home screen: 2 rows, sliding right, ALL categories        (rows: 2)
//    • Category screen: 1 row, sliding right, THIS category only (rows: 1)
//    • Shop screen: 1 row, sliding right, THIS shop's own products (rows: 1)
//  Same visual language as the rest of the app (white cards, soft shadow,
//  primary-blue accents) with a fire/sale motif layered on top since these
//  are specifically discounted items — an orange-red flame badge with the
//  discount percentage, and a warm gradient glow around the section itself.
// ═════════════════════════════════════════════════════════════════════════════

class AppFireColors {
  AppFireColors._();

  static const Color flameOrange = Color(0xFFFF7A1A);
  static const Color flameRed = Color(0xFFEF4444);
  static const Color flameDeep = Color(0xFFC2410C);

  static const LinearGradient flameGradient = LinearGradient(
    colors: [flameOrange, flameRed],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}

class FastPicksSection extends StatelessWidget {
  final List<ProductResponse> products;
  final int rows;
  final EdgeInsets padding;
  final bool showHeader;

  const FastPicksSection({
    super.key,
    required this.products,
    this.rows = 1,
    this.padding = const EdgeInsets.fromLTRB(20, 24, 0, 20),
    this.showHeader = true,
  });

  static const double _cardWidth = 118;
  static const double _cardHeight = 178;
  static const double _rowSpacing = 12;

  @override
  Widget build(BuildContext context) {
    if (products.isEmpty) return const SizedBox.shrink();

    final sectionHeight = rows * _cardHeight + (rows - 1) * _rowSpacing;

    return Padding(
      padding: padding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (showHeader) ...[
            Padding(
              padding: const EdgeInsets.only(left: 4, right: 20),
              child: _FastPicksHeader(),
            ),
            const SizedBox(height: 14),
          ],
          SizedBox(
            height: sectionHeight,
            child: rows == 1
                ? ListView.separated(
                    scrollDirection: Axis.horizontal,
                    physics: const BouncingScrollPhysics(),
                    padding: const EdgeInsets.only(right: 20),
                    itemCount: products.length,
                    separatorBuilder: (_, __) => const SizedBox(width: 12),
                    itemBuilder: (context, index) => SizedBox(
                      width: _cardWidth,
                      child: FastPickCard(product: products[index]),
                    ),
                  )
                : GridView.builder(
                    scrollDirection: Axis.horizontal,
                    physics: const BouncingScrollPhysics(),
                    padding: const EdgeInsets.only(right: 20),
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: rows,
                      mainAxisSpacing: 12,
                      crossAxisSpacing: _rowSpacing,
                      childAspectRatio: _cardWidth / _cardHeight,
                    ),
                    itemCount: products.length,
                    itemBuilder: (context, index) => FastPickCard(product: products[index]),
                  ),
          ),
        ],
      ),
    );
  }
}

/// "الأكثر توفيرًا" header with a small animated-looking flame mark — kept
/// as a lightweight const-ish row rather than importing an icon pack.
class _FastPicksHeader extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(7),
          decoration: const BoxDecoration(
            gradient: AppFireColors.flameGradient,
            shape: BoxShape.circle,
          ),
          child: const Icon(Icons.local_fire_department_rounded, color: Colors.white, size: 16),
        ),
        const SizedBox(width: 10),
        const Text(
          'AIO Fast Picks',
          style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800, color: AppColors.textPrimary),
        ),
        const SizedBox(width: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            gradient: AppFireColors.flameGradient,
            borderRadius: BorderRadius.circular(20),
          ),
          child: const Text(
            'عروض سريعة',
            style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: Colors.white),
          ),
        ),
      ],
    );
  }
}

class FastPickCard extends StatelessWidget {
  final ProductResponse product;
  const FastPickCard({super.key, required this.product});

  @override
  Widget build(BuildContext context) {
    final hasDiscount = product.is_on_sale && product.sale_price != null;
    final displayPrice = hasDiscount ? product.sale_price! : product.price;

    return GestureDetector(
      onTap: () => context.push('/product/${product.id}'),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: AppFireColors.flameOrange.withValues(alpha: 0.18)),
          boxShadow: [
            BoxShadow(
              color: AppFireColors.flameOrange.withValues(alpha: 0.10),
              blurRadius: 14,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Stack(
                children: [
                  Positioned.fill(
                    child: (product.image_url != null && product.image_url!.isNotEmpty)
                        ? Image.network(
                            product.image_url!,
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => Container(
                              color: AppColors.background,
                              child: const Icon(Icons.inventory_2_outlined, color: AppColors.textMuted),
                            ),
                          )
                        : Container(
                            color: AppColors.background,
                            child: const Icon(Icons.inventory_2_outlined, color: AppColors.textMuted),
                          ),
                  ),
                  // Warm gradient wash across the bottom of the image so the
                  // discount badge always reads clearly regardless of the
                  // photo underneath.
                  Positioned(
                    left: 0,
                    right: 0,
                    bottom: 0,
                    height: 36,
                    child: Container(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.bottomCenter,
                          end: Alignment.topCenter,
                          colors: [Colors.black.withValues(alpha: 0.35), Colors.transparent],
                        ),
                      ),
                    ),
                  ),
                  if (hasDiscount)
                    Positioned(
                      top: 8,
                      right: 8,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          gradient: AppFireColors.flameGradient,
                          borderRadius: BorderRadius.circular(20),
                          boxShadow: [
                            BoxShadow(
                              color: AppFireColors.flameRed.withValues(alpha: 0.45),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.local_fire_department_rounded, color: Colors.white, size: 12),
                            const SizedBox(width: 2),
                            Text(
                              '${product.discount_percent ?? 0}%-',
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w800,
                                color: Colors.white,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  if (!product.in_stock)
                    Positioned.fill(
                      child: Container(
                        color: Colors.black.withValues(alpha: 0.45),
                        alignment: Alignment.center,
                        child: const Text(
                          'نفذت الكمية',
                          style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 12),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 7, 8, 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    product.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: AppColors.textPrimary),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.baseline,
                    textBaseline: TextBaseline.alphabetic,
                    children: [
                      Text(
                        '${displayPrice.toStringAsFixed(0)} ج.م',
                        style: const TextStyle(
                          fontSize: 12.5,
                          fontWeight: FontWeight.w800,
                          color: AppFireColors.flameDeep,
                        ),
                      ),
                      if (hasDiscount) ...[
                        const SizedBox(width: 6),
                        Text(
                          '${product.price.toStringAsFixed(0)}',
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textMuted,
                            decoration: TextDecoration.lineThrough,
                            decorationColor: AppColors.textMuted,
                          ),
                        ),
                      ],
                    ],
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

class FastPickShimmerCard extends StatelessWidget {
  const FastPickShimmerCard({super.key});

  @override
  Widget build(BuildContext context) {
    return Shimmer.fromColors(
      baseColor: AppColors.shimmerBase,
      highlightColor: AppColors.shimmerHighlight,
      child: Container(
        width: 118,
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18)),
      ),
    );
  }
}
