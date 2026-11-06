import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/helpers.dart';
import '../../data/models/meal_builder_model.dart';
import '../../providers/cart_provider.dart';
import '../../providers/meal_builder_provider.dart';
import '../../data/repositories/meal_builder_repository.dart';

const _kFood = Color(0xFFF97316);
const _kFoodDark = Color(0xFFC2410C);
const _kFoodBg = Color(0xFFFFF7ED);

class MealBuilderScreen extends ConsumerStatefulWidget {
  final String shopId;
  const MealBuilderScreen({super.key, required this.shopId});

  @override
  ConsumerState<MealBuilderScreen> createState() => _MealBuilderScreenState();
}

class _MealBuilderScreenState extends ConsumerState<MealBuilderScreen> {
  String? _selectedType;
  int _partySize = 2;
  bool _addingToCart = false;

  void _build(String mealType) {
    setState(() => _selectedType = mealType);
    ref.read(mealBuilderProvider(widget.shopId).notifier).build(
          mealType,
          partySize: mealType == 'family' ? _partySize : 1,
        );
  }

  Future<void> _addMealToCart(BuiltMeal meal) async {
    setState(() => _addingToCart = true);
    try {
      final repo = ref.read(mealBuilderRepositoryProvider);
      final result = await repo.addMealToCart(shopId: widget.shopId, items: meal.items);
      ref.read(cartProvider.notifier).loadCart();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(
            result.skippedCount == 0 ? 'تمت إضافة الوجبة كاملة للسلة' : 'أُضيف ${result.addedCount} صنف من الوجبة',
          ),
          backgroundColor: _kFoodDark,
        ));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تعذرت إضافة الوجبة للسلة')));
      }
    } finally {
      if (mounted) setState(() => _addingToCart = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final mealTypesAsync = ref.watch(mealTypesProvider);
    final state = ref.watch(mealBuilderProvider(widget.shopId));

    return Scaffold(
      backgroundColor: _kFoodBg,
      body: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          SliverToBoxAdapter(
            child: Container(
              padding: const EdgeInsets.fromLTRB(20, 60, 20, 26),
              decoration: const BoxDecoration(
                gradient: LinearGradient(colors: [_kFood, _kFoodDark], begin: Alignment.topLeft, end: Alignment.bottomRight),
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
                      const Text('🍽️', style: TextStyle(fontSize: 20)),
                      const SizedBox(width: 8),
                      const Text('بناء الوجبة', style: TextStyle(color: Colors.white, fontSize: 19, fontWeight: FontWeight.w800)),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text('اختار نوع الوجبة، وهنجهزلك أصناف من قائمة المطعم تناسبها',
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 13)),
                ],
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 100),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                mealTypesAsync.when(
                  loading: () => const Center(child: CircularProgressIndicator(color: _kFood)),
                  error: (e, _) => const SizedBox.shrink(),
                  data: (types) => GridView.count(
                    crossAxisCount: 2,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    mainAxisSpacing: 12,
                    crossAxisSpacing: 12,
                    childAspectRatio: 1.5,
                    children: types.map((t) {
                      final selected = t.id == _selectedType;
                      return GestureDetector(
                        onTap: () => _build(t.id),
                        child: AnimatedContainer(
                          duration: const Duration(milliseconds: 200),
                          decoration: BoxDecoration(
                            color: selected ? _kFood : Colors.white,
                            borderRadius: BorderRadius.circular(18),
                            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 10, offset: const Offset(0, 3))],
                          ),
                          alignment: Alignment.center,
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(t.emoji, style: const TextStyle(fontSize: 26)),
                              const SizedBox(height: 6),
                              Text(
                                t.labelAr,
                                style: TextStyle(
                                  fontSize: 12.5,
                                  fontWeight: FontWeight.w700,
                                  color: selected ? Colors.white : AppColors.textPrimary,
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ),
                if (_selectedType == 'family') ...[
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
                    child: Row(
                      children: [
                        const Text('عدد الأفراد', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                        const Spacer(),
                        IconButton(
                          onPressed: _partySize > 2 ? () => setState(() => _partySize--) : null,
                          icon: const Icon(Icons.remove_circle_outline_rounded, color: _kFood),
                        ),
                        Text('$_partySize', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                        IconButton(
                          onPressed: _partySize < 12 ? () => setState(() => _partySize++) : null,
                          icon: const Icon(Icons.add_circle_outline_rounded, color: _kFood),
                        ),
                        TextButton(
                          onPressed: () => _build('family'),
                          child: const Text('تحديث', style: TextStyle(color: _kFoodDark, fontWeight: FontWeight.w700)),
                        ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 20),
                if (state.isLoading)
                  const Padding(
                    padding: EdgeInsets.only(top: 30),
                    child: Center(
                      child: Column(
                        children: [
                          CircularProgressIndicator(color: _kFood),
                          SizedBox(height: 12),
                          Text('بنجهزلك الوجبة المناسبة...', style: TextStyle(color: AppColors.textSecondary, fontSize: 13)),
                        ],
                      ),
                    ),
                  ),
                if (state.error != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 20),
                    child: Center(child: Text(state.error!, style: const TextStyle(color: AppColors.error), textAlign: TextAlign.center)),
                  ),
                if (state.meal != null) _MealResult(meal: state.meal!),
              ]),
            ),
          ),
        ],
      ),
      floatingActionButton: state.meal != null
          ? FloatingActionButton.extended(
              backgroundColor: _kFoodDark,
              onPressed: _addingToCart ? null : () => _addMealToCart(state.meal!),
              icon: _addingToCart
                  ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.shopping_cart_checkout_rounded),
              label: Text('أضف الوجبة (${Helpers.formatPrice(state.meal!.totalPrice)})', style: const TextStyle(fontWeight: FontWeight.w700)),
            )
          : null,
    );
  }
}

class _MealResult extends StatelessWidget {
  final BuiltMeal meal;
  const _MealResult({required this.meal});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(meal.mealTitle, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
          const SizedBox(height: 4),
          Text('${meal.items.length} أصناف · ${Helpers.formatPrice(meal.totalPrice)}',
              style: TextStyle(fontSize: 12.5, color: AppColors.textSecondary)),
          const SizedBox(height: 14),
          ...meal.items.map((item) => Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(color: _kFoodBg, borderRadius: BorderRadius.circular(10)),
                      alignment: Alignment.center,
                      child: Text('${item.quantity}×', style: const TextStyle(fontWeight: FontWeight.w800, color: _kFoodDark, fontSize: 12)),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(item.product.name, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
                          if (item.reason.isNotEmpty)
                            Text(item.reason, style: TextStyle(fontSize: 11.5, color: AppColors.textSecondary)),
                        ],
                      ),
                    ),
                    Text(Helpers.formatPrice(item.product.price * item.quantity),
                        style: const TextStyle(fontWeight: FontWeight.w700, color: _kFoodDark)),
                  ],
                ),
              )),
        ],
      ),
    );
  }
}
