import 'package:flutter/material.dart';

class AppConstants {
  AppConstants._();

  static const String appName = 'AIO';
  static const String appTagline = 'All in One';
  static const String appDescription = 'Everything you think of is here';

  static const Duration splashDuration = Duration(seconds: 2);
  static const Duration pageTransitionDuration = Duration(milliseconds: 400);
  static const Duration snackBarDuration = Duration(seconds: 3);

  static const String egyptCountryCode = '+20';
  static const int egyptPhoneLength = 11;

  static const Map<String, String> orderStatusLabels = {
    'pending': 'قيد الانتظار',
    'preparing': 'جاري التحضير',
    'out_for_delivery': 'في الطريق',
    'delivered': 'تم التوصيل',
    'cancelled': 'تم الإلغاء',
  };

  static const Map<String, Color> orderStatusColors = {
    'pending': Color(0xFFF59E0B),
    'preparing': Color(0xFF3B82F6),
    'out_for_delivery': Color(0xFF8B5CF6),
    'delivered': Color(0xFF10B981),
    'cancelled': Color(0xFFEF4444),
  };
}
