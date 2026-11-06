import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';
import '../../data/models/shopping_list_model.dart';
import '../../data/repositories/shopping_list_repository.dart';
import '../../providers/shopping_list_provider.dart';

const _kGreen = Color(0xFF10B981);
const _kGreenDark = Color(0xFF047857);
const _kGreenBg = Color(0xFFF0FDF7);

class ShoppingListsScreen extends ConsumerWidget {
  const ShoppingListsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final listsAsync = ref.watch(shoppingListsProvider);

    return Scaffold(
      backgroundColor: _kGreenBg,
      body: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          SliverToBoxAdapter(
            child: Container(
              padding: const EdgeInsets.fromLTRB(20, 60, 20, 28),
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  colors: [_kGreen, _kGreenDark],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
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
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.2),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: const Icon(Icons.arrow_forward_rounded, color: Colors.white, size: 20),
                        ),
                      ),
                      const SizedBox(width: 12),
                      const Text('🛒', style: TextStyle(fontSize: 22)),
                      const SizedBox(width: 8),
                      const Text(
                        'قوائم التسوق الذكية',
                        style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w800),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'اعمل قائمة لأي مناسبة، واستخدمها كل ما احتجت',
                    style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 13),
                  ),
                ],
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 100),
            sliver: listsAsync.when(
              loading: () => const SliverToBoxAdapter(
                child: Padding(
                  padding: EdgeInsets.only(top: 60),
                  child: Center(child: CircularProgressIndicator(color: _kGreen)),
                ),
              ),
              error: (e, _) => SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.only(top: 60),
                  child: Center(
                    child: Column(
                      children: [
                        const Icon(Icons.error_outline_rounded, color: AppColors.textMuted, size: 40),
                        const SizedBox(height: 12),
                        const Text('تعذر تحميل قوائمك'),
                        TextButton(
                          onPressed: () => ref.invalidate(shoppingListsProvider),
                          child: const Text('إعادة المحاولة', style: TextStyle(color: _kGreen)),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              data: (lists) {
                if (lists.isEmpty) {
                  return SliverToBoxAdapter(child: _EmptyState(onCreate: () => _showCreateSheet(context, ref)));
                }
                return SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (context, index) {
                      final list = lists[index];
                      final occasion = ListOccasion.byId(list.occasion);
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 14),
                        child: Dismissible(
                          key: ValueKey(list.id),
                          direction: DismissDirection.endToStart,
                          confirmDismiss: (_) => _confirmDelete(context, list.name),
                          onDismissed: (_) async {
                            final repo = ref.read(shoppingListRepositoryProvider);
                            try {
                              await repo.deleteList(list.id);
                            } catch (e) {
                              // Nothing to roll back to visually — the item
                              // is already gone from the list on screen, so
                              // just let the next load reconcile it.
                            } finally {
                              ref.invalidate(shoppingListsProvider);
                            }
                          },
                          background: Container(
                            alignment: Alignment.centerRight,
                            padding: const EdgeInsets.only(right: 20),
                            decoration: BoxDecoration(color: AppColors.error, borderRadius: BorderRadius.circular(20)),
                            child: const Icon(Icons.delete_rounded, color: Colors.white),
                          ),
                          child: _ListCard(
                            list: list,
                            occasion: occasion,
                            onTap: () => context.push('/grocery/lists/${list.id}'),
                          ),
                        ),
                      );
                    },
                    childCount: lists.length,
                  ),
                );
              },
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: _kGreen,
        onPressed: () => _showCreateSheet(context, ref),
        icon: const Icon(Icons.add_rounded),
        label: const Text('قائمة جديدة', style: TextStyle(fontWeight: FontWeight.w700)),
      ),
    );
  }

  void _showCreateSheet(BuildContext context, WidgetRef ref) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _CreateListSheet(
        onCreated: (list) {
          ref.invalidate(shoppingListsProvider);
          context.push('/grocery/lists/${list.id}');
        },
      ),
    );
  }

  Future<bool> _confirmDelete(BuildContext context, String listName) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('حذف القائمة؟'),
        content: Text('هيتم حذف "$listName" وكل عناصرها نهائيًا.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('إلغاء'),
          ),
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('حذف', style: TextStyle(color: AppColors.error, fontWeight: FontWeight.w700)),
          ),
        ],
      ),
    );
    return confirmed ?? false;
  }
}

class _EmptyState extends StatelessWidget {
  final VoidCallback onCreate;
  const _EmptyState({required this.onCreate});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 50),
      child: Column(
        children: [
          const Text('📋', style: TextStyle(fontSize: 56)),
          const SizedBox(height: 16),
          const Text('لسه معملتش أي قائمة', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          Text(
            'اعمل قائمة للتسوق الأسبوعي أو رمضان أو أي مناسبة',
            style: TextStyle(fontSize: 13, color: AppColors.textSecondary),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: onCreate,
            style: ElevatedButton.styleFrom(backgroundColor: _kGreen, foregroundColor: Colors.white),
            child: const Text('ابدأ قائمة جديدة'),
          ),
        ],
      ),
    );
  }
}

class _ListCard extends StatelessWidget {
  final ShoppingListSummary list;
  final ListOccasion occasion;
  final VoidCallback onTap;

  const _ListCard({required this.list, required this.occasion, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final progress = list.itemCount == 0 ? 0.0 : list.checkedCount / list.itemCount;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 12, offset: const Offset(0, 4))],
        ),
        child: Row(
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(color: _kGreenBg, borderRadius: BorderRadius.circular(16)),
              alignment: Alignment.center,
              child: Text(occasion.emoji, style: const TextStyle(fontSize: 24)),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(list.name, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text('${list.itemCount} عنصر · ${occasion.label}',
                      style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
                  const SizedBox(height: 8),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: progress,
                      minHeight: 5,
                      backgroundColor: AppColors.divider,
                      valueColor: const AlwaysStoppedAnimation(_kGreen),
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_left_rounded, color: AppColors.textMuted),
          ],
        ),
      ),
    );
  }
}

class _CreateListSheet extends ConsumerStatefulWidget {
  final void Function(ShoppingListDetail) onCreated;
  const _CreateListSheet({required this.onCreated});

  @override
  ConsumerState<_CreateListSheet> createState() => _CreateListSheetState();
}

class _CreateListSheetState extends ConsumerState<_CreateListSheet> {
  final _controller = TextEditingController();
  String _occasion = 'custom';
  bool _saving = false;

  Future<void> _create() async {
    final name = _controller.text.trim();
    if (name.isEmpty) return;
    setState(() => _saving = true);
    try {
      final repo = ref.read(shoppingListRepositoryProvider);
      final list = await repo.createList(name: name, occasion: _occasion);
      if (mounted) {
        Navigator.of(context).pop();
        widget.onCreated(list);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _saving = false);
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تعذر إنشاء القائمة')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Container(
        padding: const EdgeInsets.all(24),
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(color: AppColors.divider, borderRadius: BorderRadius.circular(4)),
              ),
            ),
            const SizedBox(height: 20),
            const Text('قائمة تسوق جديدة', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
            const SizedBox(height: 16),
            TextField(
              controller: _controller,
              autofocus: true,
              decoration: InputDecoration(
                hintText: 'اسم القائمة، مثال: تسوق الأسبوع',
                filled: true,
                fillColor: _kGreenBg,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
              ),
            ),
            const SizedBox(height: 16),
            const Text('المناسبة', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: ListOccasion.all.map((o) {
                final selected = o.id == _occasion;
                return GestureDetector(
                  onTap: () => setState(() => _occasion = o.id),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
                    decoration: BoxDecoration(
                      color: selected ? _kGreen : _kGreenBg,
                      borderRadius: BorderRadius.circular(18),
                    ),
                    child: Text(
                      '${o.emoji} ${o.label}',
                      style: TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w700,
                        color: selected ? Colors.white : _kGreenDark,
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _saving ? null : _create,
                style: ElevatedButton.styleFrom(
                  backgroundColor: _kGreen,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                ),
                child: _saving
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Text('إنشاء القائمة', style: TextStyle(fontWeight: FontWeight.w700)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
