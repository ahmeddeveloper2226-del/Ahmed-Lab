import 'package:flutter/material.dart';

class Helpers {
  Helpers._();

  static String formatPrice(double price) {
    return '${price.toStringAsFixed(2)} ج.م';
  }

  static String formatPhone(String phone) {
    if (phone.startsWith('+20')) {
      return phone;
    }
    if (phone.startsWith('0')) {
      return '+20${phone.substring(1)}';
    }
    return '+20$phone';
  }

  static bool isValidEgyptianPhone(String phone) {
    final clean = phone.replaceAll(RegExp(r'\D'), '');
    return clean.length == 11 && clean.startsWith('01');
  }

  // Explicit mapping for known categories — deterministic and semantically
  // correct (e.g. pharmacies always get a medical-cross icon, never
  // something unrelated from a hash collision). Falls back to the
  // hash-based pool below for any category id not listed here, so this
  // never breaks for categories added later.
  static const Map<String, Color> _categoryColors = {
    'grocery': Color(0xFF10B981),      // Green
    'clothes': Color(0xFFF59E0B),      // Amber
    'food': Color(0xFFEF4444),         // Red
    'electronics': Color(0xFF3B82F6),  // Blue
    'pharmacies': Color(0xFF06B6D4),   // Cyan — reads as medical/clean
  };

  static const Map<String, IconData> _categoryIcons = {
    'grocery': Icons.local_grocery_store_rounded,
    'clothes': Icons.checkroom_rounded,
    'food': Icons.restaurant_rounded,
    'electronics': Icons.devices_rounded,
    'pharmacies': Icons.local_pharmacy_rounded,
  };

  static Color getCategoryColor(String categoryId) {
    if (_categoryColors.containsKey(categoryId)) {
      return _categoryColors[categoryId]!;
    }
    final colors = [
      const Color(0xFFEF4444), // Food - Red
      const Color(0xFF10B981), // Grocery - Green
      const Color(0xFF8B5CF6), // Marketplace - Purple
      const Color(0xFFF59E0B), // Fashion - Amber
      const Color(0xFF3B82F6), // Electronics - Blue
      const Color(0xFFEC4899), // Beauty - Pink
    ];
    return colors[categoryId.hashCode % colors.length];
  }

  static IconData getCategoryIcon(String categoryId) {
    if (_categoryIcons.containsKey(categoryId)) {
      return _categoryIcons[categoryId]!;
    }
    final icons = [
      Icons.restaurant,
      Icons.local_grocery_store,
      Icons.shopping_bag,
      Icons.checkroom,
      Icons.devices,
      Icons.spa,
    ];
    return icons[categoryId.hashCode % icons.length];
  }
}