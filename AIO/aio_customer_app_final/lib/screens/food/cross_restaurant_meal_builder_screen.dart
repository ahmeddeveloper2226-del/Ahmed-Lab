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

class CrossRestaurantMealBuilderScreen extends ConsumerStatefulWidget {
  const CrossRestaurantMealBuilderScreen({super.key});

  @override
  ConsumerState<CrossRestaurantMealBuilderScreen> createState() => _CrossRestaurantMealBuilderScreenState();
}

class _CrossRestaurantMealBuilderScreenState extends ConsumerState<CrossRestaurantMealBuilderScreen> {
  final _queryController = TextEditingController();
  int _partySize = 1;
  bool _addingToCart = false;

  @override
  void dispose() {
    _queryController.dispose();
    super.dispose();
  }

  void _build() {
    final query = _queryController.text.trim();
    if (query.length < 3) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('اكتب طلبك بشكل أوضح شوية')),
      );
      return;
    }
    FocusScope.of(context).unfocus();
    ref.read(crossRestaurantMealBuilderProvider.notifier).build(query, partySize: _partySize);
  }

  Future<void> _addMealToCart(CrossRestaurantBuiltMeal meal) async {
    setState(() => _addingToCart = true);
    try {
      final repo = ref.read(mealBuilderRepositoryProvider);
      final result = await repo.addCrossRestaurantMealToCart(items: meal.items);
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
    final state = ref.watch(crossRestaurantMealBuilderProvider);

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
                      const Text('🌍', style: TextStyle(fontSize: 20)),
                      const SizedBox(width: 8),
                      const Expanded(
                        child: Text('وجبة من كل المطاعم', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w800)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'اكتب اللي عايزه، وهندور لك على أفضل المطاعم اللي تقدر تجهزه — ممكن الوجبة تجمع أصناف من أكتر من مطعم',
                    style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 13),
                  ),
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
                      const Text('وصف الوجبة', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _queryController,
                        maxLines: 3,
                        minLines: 2,
                        decoration: InputDecoration(
                          hintText: 'مثال: غدا صحي لشخصين بحد أقصى ٣٠٠ جنيه',
                          filled: true,
                          fillColor: _kFoodBg,
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
                        ),
                      ),
                      const SizedBox(height: 14),
                      Row(
                        children: [
                          const Text('عدد الأفراد', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                          const Spacer(),
                          IconButton(
                            onPressed: _partySize > 1 ? () => setState(() => _partySize--) : null,
                            icon: const Icon(Icons.remove_circle_outline_rounded, color: _kFood),
                          ),
                          Text('$_partySize', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                          IconButton(
                            onPressed: _partySize < 12 ? () => setState(() => _partySize++) : null,
                            icon: const Icon(Icons.add_circle_outline_rounded, color: _kFood),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          onPressed: state.isLoading ? null : _build,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: _kFood,
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                          ),
                          icon: const Icon(Icons.auto_awesome_rounded, size: 18),
                          label: const Text('ابحث وابنِ الوجبة', style: TextStyle(fontWeight: FontWeight.w700)),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                if (state.isLoading)
                  const Padding(
                    padding: EdgeInsets.only(top: 20),
                    child: Center(
                      child: Column(
                        children: [
                          CircularProgressIndicator(color: _kFood),
                          SizedBox(height: 12),
                          Text('بندور في المطاعم القريبة منك على أفضل الأصناف...', style: TextStyle(color: AppColors.textSecondary, fontSize: 13), textAlign: TextAlign.center),
                        ],
                      ),
                    ),
                  ),
                if (state.error != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 20),
                    child: Center(child: Text(state.error!, style: const TextStyle(color: AppColors.error), textAlign: TextAlign.center)),
                  ),
                if (state.meal != null) _CrossRestaurantMealResult(meal: state.meal!),
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

class _CrossRestaurantMealResult extends StatelessWidget {
  final CrossRestaurantBuiltMeal meal;
  const _CrossRestaurantMealResult({required this.meal});

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
          if (meal.restaurantsUsed.isNotEmpty) ...[
            const SizedBox(height: 10),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: meal.restaurantsUsed
                  .map((name) => Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(color: _kFoodBg, borderRadius: BorderRadius.circular(10)),
                        child: Text(name, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: _kFoodDark)),
                      ))
                  .toList(),
            ),
          ],
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
                          Row(
                            children: [
                              const Icon(Icons.storefront_rounded, size: 11, color: _kFoodDark),
                              const SizedBox(width: 3),
                              Text(item.shopName, style: const TextStyle(fontSize: 11, color: _kFoodDark, fontWeight: FontWeight.w600)),
                            ],
                          ),
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
