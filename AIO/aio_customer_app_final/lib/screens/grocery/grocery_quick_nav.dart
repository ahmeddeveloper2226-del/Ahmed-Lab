import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// AIO Exclusive — Grocery-only quick access rail for Smart Shopping Lists
/// and AI Recipe Shopping. Deliberately a small floating side pill rather
/// than any change to the category's existing header/grid/shop list, per
/// "don't affect the inside category look" — it overlays on top instead of
/// occupying layout space.
class GroceryQuickNav extends StatelessWidget {
  const GroceryQuickNav({super.key});

  static const _green = Color(0xFF10B981);
  static const _greenDark = Color(0xFF059669);

  @override
  Widget build(BuildContext context) {
    return Positioned(
      left: 12,
      top: MediaQuery.of(context).size.height * 0.32,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 6),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [_green, _greenDark],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
          borderRadius: BorderRadius.circular(22),
          boxShadow: [
            BoxShadow(color: _green.withValues(alpha: 0.35), blurRadius: 16, offset: const Offset(0, 6)),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _NavButton(
              icon: Icons.checklist_rounded,
              label: 'قوائمي',
              onTap: () => context.push('/grocery/lists'),
            ),
            Container(height: 1, width: 26, color: Colors.white.withValues(alpha: 0.3), margin: const EdgeInsets.symmetric(vertical: 8)),
            _NavButton(
              icon: Icons.auto_awesome_rounded,
              label: 'وصفة',
              onTap: () => context.push('/grocery/recipe'),
            ),
          ],
        ),
      ),
    );
  }
}

class _NavButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  const _NavButton({required this.icon, required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: Colors.white, size: 22),
            const SizedBox(height: 3),
            Text(
              label,
              style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w700),
            ),
          ],
        ),
      ),
    );
  }
}
