import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';
import '../../data/models/shopping_list_model.dart';
import '../../data/repositories/shopping_list_repository.dart';
import '../../providers/cart_provider.dart';
import '../../providers/shopping_list_provider.dart';

const _kGreen = Color(0xFF10B981);
const _kGreenDark = Color(0xFF047857);
const _kGreenBg = Color(0xFFF0FDF7);

const List<String> _quickDishes = ['كشري', 'مكرونة بشاميل', 'لازانيا', 'فتة', 'كبسة', 'ملوخية'];

class AiRecipeScreen extends ConsumerStatefulWidget {
  const AiRecipeScreen({super.key});

  @override
  ConsumerState<AiRecipeScreen> createState() => _AiRecipeScreenState();
}

class _AiRecipeScreenState extends ConsumerState<AiRecipeScreen> {
  final _dishController = TextEditingController();
  int _servings = 4;
  bool _addingToCart = false;

  void _search() {
    FocusScope.of(context).unfocus();
    ref.read(recipeSearchProvider.notifier).search(_dishController.text, _servings);
  }

  Future<void> _addMatchedToCart(RecipeParseResult result) async {
    final ids = result.ingredients.where((i) => i.matched && i.productId != null).map((i) => i.productId!).toList();
    if (ids.isEmpty) return;
    setState(() => _addingToCart = true);
    try {
      final repo = ref.read(shoppingListRepositoryProvider);
      final res = await repo.addRecipeToCart(ids);
      ref.read(cartProvider.notifier).loadCart();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('تمت إضافة ${res.addedCount} مكوّن إلى السلة'),
          backgroundColor: _kGreenDark,
        ));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تعذرت إضافة المكونات للسلة')));
      }
    } finally {
      if (mounted) setState(() => _addingToCart = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(recipeSearchProvider);

    return Scaffold(
      backgroundColor: _kGreenBg,
      body: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          SliverToBoxAdapter(
            child: Container(
              padding: const EdgeInsets.fromLTRB(20, 60, 20, 26),
              decoration: const BoxDecoration(
                gradient: LinearGradient(colors: [_kGreen, _kGreenDark], begin: Alignment.topLeft, end: Alignment.bottomRight),
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
                      const Icon(Icons.auto_awesome_rounded, color: Colors.white, size: 22),
                      const SizedBox(width: 8),
                      const Text('تسوق بالوصفة بالذكاء الاصطناعي',
                          style: TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w800)),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text('اكتب اسم الطبق وهنجيبلك كل المكونات جاهزة للسلة',
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 13)),
                ],
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 100),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      TextField(
                        controller: _dishController,
                        onSubmitted: (_) => _search(),
                        decoration: InputDecoration(
                          hintText: 'اسم الطبق، مثال: كشري',
                          prefixIcon: const Icon(Icons.restaurant_menu_rounded, color: _kGreen),
                          filled: true,
                          fillColor: _kGreenBg,
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: _quickDishes.map((d) {
                          return GestureDetector(
                            onTap: () {
                              _dishController.text = d;
                              _search();
                            },
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                              decoration: BoxDecoration(color: _kGreenBg, borderRadius: BorderRadius.circular(16)),
                              child: Text(d, style: const TextStyle(fontSize: 12.5, color: _kGreenDark, fontWeight: FontWeight.w600)),
                            ),
                          );
                        }).toList(),
                      ),
                      const SizedBox(height: 16),
                      Row(
                        children: [
                          const Text('عدد الأفراد', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                          const Spacer(),
                          _ServingsStepper(
                            servings: _servings,
                            onChanged: (v) => setState(() => _servings = v),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: state.isLoading ? null : _search,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: _kGreen,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 15),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                          ),
                          child: state.isLoading
                              ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                              : const Text('اجهز المكونات', style: TextStyle(fontWeight: FontWeight.w700)),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                if (state.error != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 10),
                    child: Center(child: Text(state.error!, style: const TextStyle(color: AppColors.error))),
                  ),
                if (state.result != null) _RecipeResult(result: state.result!),
              ]),
            ),
          ),
        ],
      ),
      floatingActionButton: state.result != null && state.result!.ingredients.any((i) => i.matched)
          ? FloatingActionButton.extended(
              backgroundColor: _kGreenDark,
              onPressed: _addingToCart ? null : () => _addMatchedToCart(state.result!),
              icon: _addingToCart
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.shopping_cart_checkout_rounded),
              label: const Text('أضف المتاح للسلة', style: TextStyle(fontWeight: FontWeight.w700)),
            )
          : null,
    );
  }
}

class _ServingsStepper extends StatelessWidget {
  final int servings;
  final ValueChanged<int> onChanged;
  const _ServingsStepper({required this.servings, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(color: _kGreenBg, borderRadius: BorderRadius.circular(12)),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            onPressed: servings > 1 ? () => onChanged(servings - 1) : null,
            icon: const Icon(Icons.remove_rounded, size: 18),
            color: _kGreenDark,
            constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
            padding: EdgeInsets.zero,
          ),
          SizedBox(
            width: 26,
            child: Text('$servings', textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w800)),
          ),
          IconButton(
            onPressed: servings < 20 ? () => onChanged(servings + 1) : null,
            icon: const Icon(Icons.add_rounded, size: 18),
            color: _kGreenDark,
            constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
            padding: EdgeInsets.zero,
          ),
        ],
      ),
    );
  }
}

class _RecipeResult extends StatelessWidget {
  final RecipeParseResult result;
  const _RecipeResult({required this.result});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('مكونات ${result.dishName} — ${result.servings} أفراد',
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
          const SizedBox(height: 12),
          ...result.ingredients.map((ing) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Row(
                  children: [
                    Container(
                      width: 34,
                      height: 34,
                      decoration: BoxDecoration(
                        color: ing.matched ? _kGreenBg : AppColors.background,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      alignment: Alignment.center,
                      child: Icon(
                        ing.matched ? Icons.check_circle_rounded : Icons.help_outline_rounded,
                        color: ing.matched ? _kGreen : AppColors.textMuted,
                        size: 18,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(ing.ingredientName, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5)),
                          Text(
                            ing.matched ? '${ing.quantityLabel} · ${ing.shopName ?? ''}' : '${ing.quantityLabel} · غير متوفر حاليًا',
                            style: TextStyle(fontSize: 11.5, color: AppColors.textSecondary),
                          ),
                        ],
                      ),
                    ),
                    if (ing.matched && ing.price != null)
                      Text('${ing.price!.toStringAsFixed(0)} ج.م', style: const TextStyle(fontWeight: FontWeight.w700, color: _kGreenDark)),
                  ],
                ),
              )),
        ],
      ),
    );
  }
}
