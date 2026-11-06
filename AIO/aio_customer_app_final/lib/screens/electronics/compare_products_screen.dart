import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/helpers.dart';
import '../../data/models/product_model.dart';
import '../../providers/cart_provider.dart';
import '../../providers/product_provider.dart';

const _kCompare = Color(0xFF4F46E5);
const _kCompareDark = Color(0xFF3730A3);
const _kCompareBg = Color(0xFFEEF2FF);

// Fixed row order the request asked for — any other attribute the store
// filled in on a product (e.g. "colour") just doesn't get a row, since
// this table is specifically the 7 comparison fields, not a dump of
// every attribute.
const List<MapEntry<String, String>> _kSpecRows = [
  MapEntry('processor', 'المعالج'),
  MapEntry('display', 'الشاشة'),
  MapEntry('battery', 'البطارية'),
  MapEntry('ram', 'الرام'),
  MapEntry('storage', 'التخزين'),
  MapEntry('camera', 'الكاميرا'),
];

class CompareProductsScreen extends ConsumerStatefulWidget {
  const CompareProductsScreen({super.key});

  @override
  ConsumerState<CompareProductsScreen> createState() => _CompareProductsScreenState();
}

class _CompareProductsScreenState extends ConsumerState<CompareProductsScreen> {
  final _searchController = TextEditingController();
  final List<ProductSearchResult> _selected = [];

  void _add(ProductSearchResult product) {
    if (_selected.length >= 4 || _selected.any((p) => p.id == product.id)) return;
    setState(() {
      _selected.add(product);
      _searchController.clear();
    });
  }

  void _remove(String productId) {
    setState(() => _selected.removeWhere((p) => p.id == productId));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _kCompareBg,
      body: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          SliverToBoxAdapter(
            child: Container(
              padding: const EdgeInsets.fromLTRB(20, 60, 20, 24),
              decoration: const BoxDecoration(
                gradient: LinearGradient(colors: [_kCompare, _kCompareDark], begin: Alignment.topLeft, end: Alignment.bottomRight),
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
                      const Icon(Icons.compare_arrows_rounded, color: Colors.white, size: 22),
                      const SizedBox(width: 8),
                      const Text('قارن قبل ما تشتري', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w800)),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text('اختار من 2 إلى 4 منتجات وشوف المواصفات جنب بعض', style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 13)),
                ],
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 100),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                if (_selected.isNotEmpty) ...[
                  SizedBox(
                    height: 40,
                    child: ListView.separated(
                      scrollDirection: Axis.horizontal,
                      itemCount: _selected.length,
                      separatorBuilder: (_, __) => const SizedBox(width: 8),
                      itemBuilder: (context, i) {
                        final p = _selected[i];
                        return Chip(
                          label: Text(p.name, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                          backgroundColor: Colors.white,
                          deleteIcon: const Icon(Icons.close_rounded, size: 16),
                          onDeleted: () => _remove(p.id),
                        );
                      },
                    ),
                  ),
                  const SizedBox(height: 14),
                ],
                if (_selected.length < 4)
                  Container(
                    padding: const EdgeInsets.all(4),
                    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
                    child: Column(
                      children: [
                        TextField(
                          controller: _searchController,
                          onChanged: (_) => setState(() {}),
                          decoration: InputDecoration(
                            hintText: 'ابحث عن منتج تضيفه للمقارنة...',
                            prefixIcon: const Icon(Icons.search_rounded, color: _kCompare),
                            border: InputBorder.none,
                            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
                          ),
                        ),
                        if (_searchController.text.trim().length >= 2)
                          Consumer(
                            builder: (context, ref, _) {
                              final resultsAsync = ref.watch(searchProductsProvider(
                                (query: _searchController.text.trim(), categoryId: 'electronics'),
                              ));
                              return resultsAsync.when(
                                loading: () => const Padding(
                                  padding: EdgeInsets.all(16),
                                  child: Center(child: CircularProgressIndicator(color: _kCompare)),
                                ),
                                error: (e, _) => const SizedBox.shrink(),
                                data: (results) {
                                  final filtered = results.where((p) => !_selected.any((s) => s.id == p.id)).take(6).toList();
                                  if (filtered.isEmpty) {
                                    return const Padding(
                                      padding: EdgeInsets.all(16),
                                      child: Text('لا توجد نتائج', style: TextStyle(color: AppColors.textSecondary, fontSize: 12)),
                                    );
                                  }
                                  return Column(
                                    children: filtered.map((p) {
                                      return ListTile(
                                        leading: const Icon(Icons.devices_rounded, color: _kCompare),
                                        title: Text(p.name, style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600)),
                                        subtitle: Text('${p.shop_name} · ${Helpers.formatPrice(p.price)}', style: const TextStyle(fontSize: 11.5)),
                                        trailing: const Icon(Icons.add_circle_rounded, color: _kCompare),
                                        onTap: () => _add(p),
                                      );
                                    }).toList(),
                                  );
                                },
                              );
                            },
                          ),
                      ],
                    ),
                  ),
                const SizedBox(height: 20),
                if (_selected.length < 2)
                  Padding(
                    padding: const EdgeInsets.only(top: 20),
                    child: Center(
                      child: Text('اختار منتجين على الأقل عشان نعرض المقارنة', style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
                    ),
                  )
                else
                  Consumer(
                    builder: (context, ref, _) {
                      final idsKey = _selected.map((p) => p.id).join(',');
                      final compareAsync = ref.watch(compareProductsProvider(idsKey));
                      return compareAsync.when(
                        loading: () => const Padding(
                          padding: EdgeInsets.only(top: 30),
                          child: Center(child: CircularProgressIndicator(color: _kCompare)),
                        ),
                        error: (e, _) => const Padding(
                          padding: EdgeInsets.only(top: 30),
                          child: Center(child: Text('تعذر تحميل المقارنة الآن')),
                        ),
                        data: (products) => _CompareTable(products: products),
                      );
                    },
                  ),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

class _CompareTable extends ConsumerWidget {
  final List<ProductResponse> products;
  const _CompareTable({required this.products});

  Future<void> _addToCart(WidgetRef ref, BuildContext context, ProductResponse product) async {
    try {
      await ref.read(cartProvider.notifier).updateItem(product.id, 1);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('تمت إضافة ${product.name} للسلة'), backgroundColor: _kCompareDark));
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تعذرت إضافة المنتج للسلة')));
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Only render rows where at least one of the compared products
    // actually has a value for that spec — an empty "Camera" row across
    // every column (e.g. comparing routers) is just noise.
    final visibleRows = _kSpecRows.where((row) {
      return products.any((p) => (p.attributes?[row.key] as String?)?.trim().isNotEmpty == true);
    }).toList();

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Container(
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
        padding: const EdgeInsets.all(14),
        child: Table(
          defaultVerticalAlignment: TableCellVerticalAlignment.middle,
          columnWidths: {
            0: const FixedColumnWidth(100),
            for (int i = 0; i < products.length; i++) i + 1: const FixedColumnWidth(150),
          },
          children: [
            TableRow(children: [
              const SizedBox(),
              ...products.map((p) => Padding(
                    padding: const EdgeInsets.all(8),
                    child: Column(
                      children: [
                        Container(
                          height: 70,
                          width: 70,
                          decoration: BoxDecoration(color: _kCompareBg, borderRadius: BorderRadius.circular(14)),
                          child: (p.image_url != null && p.image_url!.isNotEmpty)
                              ? ClipRRect(
                                  borderRadius: BorderRadius.circular(14),
                                  child: Image.network(p.image_url!, fit: BoxFit.cover,
                                      errorBuilder: (c, e, s) => const Icon(Icons.devices_rounded, color: _kCompare)),
                                )
                              : const Icon(Icons.devices_rounded, color: _kCompare, size: 30),
                        ),
                        const SizedBox(height: 6),
                        Text(p.name, textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                      ],
                    ),
                  )),
            ]),
            _row('السعر', products.map((p) => Helpers.formatPrice(p.sale_price ?? p.price)).toList(), highlight: true),
            for (final spec in visibleRows)
              _row(
                spec.value,
                products
                    .map((p) => (p.attributes?[spec.key] as String?)?.trim().isNotEmpty == true
                        ? p.attributes![spec.key] as String
                        : '—')
                    .toList(),
              ),
            TableRow(children: [
              const SizedBox(),
              ...products.map((p) => Padding(
                    padding: const EdgeInsets.all(8),
                    child: SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: () => _addToCart(ref, context, p),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: _kCompare,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 10),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                        child: const Text('أضف للسلة', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                      ),
                    ),
                  )),
            ]),
          ],
        ),
      ),
    );
  }

  TableRow _row(String label, List<String> values, {bool highlight = false}) {
    return TableRow(
      decoration: const BoxDecoration(border: Border(top: BorderSide(color: AppColors.divider, width: 1))),
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
          child: Text(label, style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: highlight ? _kCompareDark : AppColors.textSecondary)),
        ),
        ...values.map((v) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
              child: Text(
                v,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 12.5,
                  fontWeight: highlight ? FontWeight.w800 : FontWeight.w600,
                  color: highlight ? _kCompareDark : AppColors.textPrimary,
                ),
              ),
            )),
      ],
    );
  }
}
