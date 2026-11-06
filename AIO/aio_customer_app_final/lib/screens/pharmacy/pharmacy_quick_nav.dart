import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// AIO Exclusive — Pharmacies-only floating shortcut to 'My Medications'
/// (Refill Reminder). Same overlay approach as GroceryQuickNav: it sits
/// on top of the existing category screen via a Stack instead of taking
/// up layout space, so the shop grid/header underneath is untouched.
class PharmacyQuickNav extends StatelessWidget {
  const PharmacyQuickNav({super.key});

  static const _blue = Color(0xFF0EA5E9);
  static const _blueDark = Color(0xFF0369A1);

  @override
  Widget build(BuildContext context) {
    return Positioned(
      left: 12,
      top: MediaQuery.of(context).size.height * 0.32,
      child: GestureDetector(
        onTap: () => context.push('/medications'),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
          decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [_blue, _blueDark], begin: Alignment.topCenter, end: Alignment.bottomCenter),
            borderRadius: BorderRadius.circular(20),
            boxShadow: [BoxShadow(color: _blue.withValues(alpha: 0.35), blurRadius: 16, offset: const Offset(0, 6))],
          ),
          child: const Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.medication_rounded, color: Colors.white, size: 22),
              SizedBox(height: 3),
              Text('أدويتي', style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w700)),
            ],
          ),
        ),
      ),
    );
  }
}
