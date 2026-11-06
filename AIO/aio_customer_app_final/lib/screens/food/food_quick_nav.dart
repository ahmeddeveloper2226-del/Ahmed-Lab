import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Food-only floating shortcut to the cross-restaurant meal builder — the
/// free-text version that can mix items from several restaurants. Same
/// overlay approach as GroceryQuickNav/PharmacyQuickNav/ElectronicsQuickNav.
/// The per-restaurant meal builder stays where it is (inside each
/// restaurant's own shop screen); this is the second, app-wide option.
class FoodQuickNav extends StatelessWidget {
  const FoodQuickNav({super.key});

  static const _orange = Color(0xFFF97316);
  static const _orangeDark = Color(0xFFC2410C);

  @override
  Widget build(BuildContext context) {
    return Positioned(
      left: 12,
      top: MediaQuery.of(context).size.height * 0.32,
      child: GestureDetector(
        onTap: () => context.push('/meal-builder/cross-restaurant'),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [_orange, _orangeDark], begin: Alignment.topCenter, end: Alignment.bottomCenter),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [BoxShadow(color: _orange.withValues(alpha: 0.35), blurRadius: 16, offset: const Offset(0, 6))],
          ),
          child: const Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.auto_awesome_rounded, color: Colors.white, size: 22),
              SizedBox(height: 3),
              Text('ابنِ وجبة', style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w700)),
            ],
          ),
        ),
      ),
    );
  }
}
