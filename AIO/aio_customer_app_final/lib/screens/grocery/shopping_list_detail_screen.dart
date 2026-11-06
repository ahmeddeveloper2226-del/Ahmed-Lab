import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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

class ShoppingListDetailScreen extends ConsumerStatefulWidget {
  final String listId;
  const ShoppingListDetailScreen({super.key, required this.listId});

  @override
  ConsumerState<ShoppingListDetailScreen> createState() => _ShoppingListDetailScreenState();
}

class _ShoppingListDetailScreenState extends ConsumerState<ShoppingListDetailScreen> {
  final _addController = TextEditingController();
  bool _addingToCart = false;

  Future<void> _addItem() async {
    final name = _addController.text.trim();
    if (name.isEmpty) return;
    _addController.clear();
    final repo = ref.read(shoppingListRepositoryProvider);
    await repo.addItem(widget.listId, name: name);
    ref.invalidate(shoppingListDetailProvider(widget.listId));
  }

  Future<void> _toggleItem(ShoppingListItem item) async {
    final repo = ref.read(shoppingListRepositoryProvider);
    await repo.toggleItem(widget.listId, item.id, !item.isChecked);
    ref.invalidate(shoppingListDetailProvider(widget.listId));
  }

  Future<void> _deleteItem(ShoppingListItem item) async {
    final repo = ref.read(shoppingListRepositoryProvider);
    await repo.deleteItem(widget.listId, item.id);
    ref.invalidate(shoppingListDetailProvider(widget.listId));
  }

  Future<void> _addAllToCart() async {
    setState(() => _addingToCart = true);
    try {
      final repo = ref.read(shoppingListRepositoryProvider);
      final result = await repo.addListToCart(widget.listId);
      ref.read(cartProvider.notifier).loadCart();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(
            result.skippedCount == 0
                ? 'تمت إضافة ${result.addedCount} عنصر إلى السلة'
                : 'أُضيف ${result.addedCount} عنصر، وتعذر إيجاد ${result.skippedCount} عنصر',
          ),
          backgroundColor: _kGreenDark,
        ));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تعذرت إضافة القائمة للسلة')));
      }
    } finally {
      if (mounted) setState(() => _addingToCart = false);
    }
  }

  void _share(ShoppingListDetail list) {
    Clipboard.setData(ClipboardData(text: list.shareCode));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('تم نسخ كود المشاركة — شاركه مع العيلة أو الأصحاب')),
    );
  }

  Future<void> _deleteList(BuildContext context, String listName) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('حذف القائمة؟'),
        content: Text('هيتم حذف "$listName" وكل عناصرها نهائيًا.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(dialogContext).pop(false), child: const Text('إلغاء')),
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('حذف', style: TextStyle(color: AppColors.error, fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    try {
      final repo = ref.read(shoppingListRepositoryProvider);
      await repo.deleteList(widget.listId);
      ref.invalidate(shoppingListsProvider);
      if (mounted) context.pop();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تعذر حذف القائمة الآن')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final detailAsync = ref.watch(shoppingListDetailProvider(widget.listId));

    return Scaffold(
      backgroundColor: _kGreenBg,
      body: detailAsync.when(
        loading: () => const Center(child: CircularProgressIndicator(color: _kGreen)),
        error: (e, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('تعذر تحميل القائمة'),
              TextButton(
                onPressed: () => ref.invalidate(shoppingListDetailProvider(widget.listId)),
                child: const Text('إعادة المحاولة', style: TextStyle(color: _kGreen)),
              ),
            ],
          ),
        ),
        data: (list) => Column(
          children: [
            Container(
              padding: const EdgeInsets.fromLTRB(20, 60, 20, 20),
              decoration: const BoxDecoration(
                gradient: LinearGradient(colors: [_kGreen, _kGreenDark], begin: Alignment.topLeft, end: Alignment.bottomRight),
                borderRadius: BorderRadius.vertical(bottom: Radius.circular(28)),
              ),
              child: Row(
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
                  Expanded(
                    child: Text(list.name,
                        style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w800),
                        overflow: TextOverflow.ellipsis),
                  ),
                  GestureDetector(
                    onTap: () => _share(list),
                    child: Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(12)),
                      child: const Icon(Icons.share_rounded, color: Colors.white, size: 18),
                    ),
                  ),
                  const SizedBox(width: 8),
                  GestureDetector(
                    onTap: () => _deleteList(context, list.name),
                    child: Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(12)),
                      child: const Icon(Icons.delete_outline_rounded, color: Colors.white, size: 18),
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _addController,
                      onSubmitted: (_) => _addItem(),
                      decoration: InputDecoration(
                        hintText: 'أضف عنصر... مثال: أرز 2 كيلو',
                        filled: true,
                        fillColor: Colors.white,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  GestureDetector(
                    onTap: _addItem,
                    child: Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(color: _kGreen, borderRadius: BorderRadius.circular(14)),
                      child: const Icon(Icons.add_rounded, color: Colors.white),
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: list.items.isEmpty
                  ? Center(
                      child: Text('القائمة فاضية، ابدأ بإضافة عناصر', style: TextStyle(color: AppColors.textSecondary)),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.fromLTRB(20, 8, 20, 100),
                      itemCount: list.items.length,
                      itemBuilder: (context, i) {
                        final item = list.items[i];
                        return Dismissible(
                          key: ValueKey(item.id),
                          direction: DismissDirection.endToStart,
                          onDismissed: (_) => _deleteItem(item),
                          background: Container(
                            alignment: Alignment.centerRight,
                            padding: const EdgeInsets.only(right: 20),
                            margin: const EdgeInsets.only(bottom: 10),
                            decoration: BoxDecoration(color: AppColors.error, borderRadius: BorderRadius.circular(16)),
                            child: const Icon(Icons.delete_rounded, color: Colors.white),
                          ),
                          child: Container(
                            margin: const EdgeInsets.only(bottom: 10),
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
                            child: CheckboxListTile(
                              value: item.isChecked,
                              onChanged: (_) => _toggleItem(item),
                              activeColor: _kGreen,
                              controlAffinity: ListTileControlAffinity.leading,
                              contentPadding: EdgeInsets.zero,
                              title: Text(
                                item.name,
                                style: TextStyle(
                                  fontWeight: FontWeight.w600,
                                  decoration: item.isChecked ? TextDecoration.lineThrough : null,
                                  color: item.isChecked ? AppColors.textMuted : AppColors.textPrimary,
                                ),
                              ),
                              subtitle: item.unit != null
                                  ? Text('${item.quantity.toStringAsFixed(item.quantity == item.quantity.roundToDouble() ? 0 : 1)} ${item.unit}')
                                  : null,
                            ),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
      floatingActionButton: detailAsync.maybeWhen(
        data: (list) => list.items.isEmpty
            ? null
            : FloatingActionButton.extended(
                backgroundColor: _kGreenDark,
                onPressed: _addingToCart ? null : _addAllToCart,
                icon: _addingToCart
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.shopping_cart_checkout_rounded),
                label: const Text('أضف الكل للسلة', style: TextStyle(fontWeight: FontWeight.w700)),
              ),
        orElse: () => null,
      ),
    );
  }
}
