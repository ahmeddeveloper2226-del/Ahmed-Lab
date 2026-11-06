import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// AIO Exclusive — Electronics-only floating shortcut to 'Compare Before
/// Buying'. Same overlay approach as GroceryQuickNav/PharmacyQuickNav.
class ElectronicsQuickNav extends StatelessWidget {
  const ElectronicsQuickNav({super.key});

  static const _indigo = Color(0xFF4F46E5);
  static const _indigoDark = Color(0xFF3730A3);

  @override
  Widget build(BuildContext context) {
    return Positioned(
      left: 12,
      top: MediaQuery.of(context).size.height * 0.32,
      child: GestureDetector(
        onTap: () => context.push('/compare-products'),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [_indigo, _indigoDark], begin: Alignment.topCenter, end: Alignment.bottomCenter),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [BoxShadow(color: _indigo.withValues(alpha: 0.35), blurRadius: 16, offset: const Offset(0, 6))],
          ),
          child: const Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.compare_arrows_rounded, color: Colors.white, size: 22),
              SizedBox(height: 3),
              Text('قارن', style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w700)),
            ],
          ),
        ),
      ),
    );
  }
}
