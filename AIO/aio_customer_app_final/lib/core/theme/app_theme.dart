import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/cupertino.dart';

class AppColors {
  AppColors._();

  // Primary Blue Gradient
  static const Color primaryBlue = Color(0xFF2563EB);
  static const Color primaryLight = Color(0xFF3B82F6);
  static const Color primaryDark = Color(0xFF1D4ED8);
  static const Color accentCyan = Color(0xFF06B6D4);
  static const Color accentSky = Color(0xFF0EA5E9);

  // Backgrounds
  static const Color background = Color(0xFFF8FAFC);
  static const Color surface = Colors.white;
  static const Color cardBg = Colors.white;
  static const Color darkBackground = Color(0xFF0F172A);

  // Text
  static const Color textPrimary = Color(0xFF1E293B);
  static const Color textSecondary = Color(0xFF64748B);
  static const Color textMuted = Color(0xFF94A3B8);
  static const Color textOnPrimary = Colors.white;

  // Status
  static const Color success = Color(0xFF10B981);
  static const Color error = Color(0xFFEF4444);
  static const Color warning = Color(0xFFF59E0B);
  static const Color info = Color(0xFF3B82F6);

  // Misc
  static const Color divider = Color(0xFFE2E8F0);
  static const Color shadow = Color(0x1A000000);
  static const Color shimmerBase = Color(0xFFE2E8F0);
  static const Color shimmerHighlight = Color(0xFFF1F5F9);
}

class AppTheme {
  AppTheme._();

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: const ColorScheme.light(
        primary: AppColors.primaryBlue,
        onPrimary: AppColors.textOnPrimary,
        secondary: AppColors.accentCyan,
        onSecondary: AppColors.textOnPrimary,
        surface: AppColors.surface,
        onSurface: AppColors.textPrimary,
        error: AppColors.error,
        onError: AppColors.textOnPrimary,
      ),
      scaffoldBackgroundColor: AppColors.background,
      fontFamily: 'Cairo',
      textTheme: _textTheme,
      appBarTheme: _appBarTheme,
      bottomNavigationBarTheme: _bottomNavTheme,
      cardTheme: _cardTheme,
      elevatedButtonTheme: _elevatedButtonTheme,
      outlinedButtonTheme: _outlinedButtonTheme,
      textButtonTheme: _textButtonTheme,
      inputDecorationTheme: _inputDecorationTheme,
      chipTheme: _chipTheme,
      dividerTheme: _dividerTheme,
      snackBarTheme: _snackBarTheme,
      pageTransitionsTheme: const PageTransitionsTheme(
        builders: {
          TargetPlatform.android: ZoomPageTransitionsBuilder(),
          TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
          TargetPlatform.macOS: CupertinoPageTransitionsBuilder(),
        },
      ),
    );
  }

  static ThemeData get darkTheme {
    return lightTheme.copyWith(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: AppColors.darkBackground,
    );
  }

  static TextTheme get _textTheme {
    return const TextTheme(
      displayLarge: TextStyle(
        fontSize: 32, fontWeight: FontWeight.bold, color: AppColors.textPrimary,
      ),
      displayMedium: TextStyle(
        fontSize: 28, fontWeight: FontWeight.bold, color: AppColors.textPrimary,
      ),
      displaySmall: TextStyle(
        fontSize: 24, fontWeight: FontWeight.w600, color: AppColors.textPrimary,
      ),
      headlineLarge: TextStyle(
        fontSize: 22, fontWeight: FontWeight.w700, color: AppColors.textPrimary,
      ),
      headlineMedium: TextStyle(
        fontSize: 20, fontWeight: FontWeight.w600, color: AppColors.textPrimary,
      ),
      headlineSmall: TextStyle(
        fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.textPrimary,
      ),
      titleLarge: TextStyle(
        fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.textPrimary,
      ),
      titleMedium: TextStyle(
        fontSize: 14, fontWeight: FontWeight.w600, color: AppColors.textPrimary,
      ),
      titleSmall: TextStyle(
        fontSize: 12, fontWeight: FontWeight.w600, color: AppColors.textSecondary,
      ),
      bodyLarge: TextStyle(
        fontSize: 16, fontWeight: FontWeight.normal, color: AppColors.textPrimary,
      ),
      bodyMedium: TextStyle(
        fontSize: 14, fontWeight: FontWeight.normal, color: AppColors.textPrimary,
      ),
      bodySmall: TextStyle(
        fontSize: 12, fontWeight: FontWeight.normal, color: AppColors.textSecondary,
      ),
      labelLarge: TextStyle(
        fontSize: 14, fontWeight: FontWeight.w500, color: AppColors.textSecondary,
      ),
      labelMedium: TextStyle(
        fontSize: 12, fontWeight: FontWeight.w500, color: AppColors.textMuted,
      ),
      labelSmall: TextStyle(
        fontSize: 10, fontWeight: FontWeight.w500, color: AppColors.textMuted,
      ),
    );
  }

  static AppBarTheme get _appBarTheme {
    return AppBarTheme(
      elevation: 0,
      centerTitle: true,
      backgroundColor: AppColors.background,
      foregroundColor: AppColors.textPrimary,
      systemOverlayStyle: SystemUiOverlayStyle.dark,
      titleTextStyle: _textTheme.headlineSmall?.copyWith(
        color: AppColors.textPrimary,
      ),
    );
  }

  static BottomNavigationBarThemeData get _bottomNavTheme {
    return const BottomNavigationBarThemeData(
      backgroundColor: AppColors.surface,
      selectedItemColor: AppColors.primaryBlue,
      unselectedItemColor: AppColors.textMuted,
      type: BottomNavigationBarType.fixed,
      elevation: 8,
      showSelectedLabels: true,
      showUnselectedLabels: true,
      selectedLabelStyle: TextStyle(
        fontSize: 11, fontWeight: FontWeight.w600, fontFamily: 'Cairo',
      ),
      unselectedLabelStyle: TextStyle(
        fontSize: 11, fontWeight: FontWeight.w500, fontFamily: 'Cairo',
      ),
    );
  }

  static CardThemeData get _cardTheme {
    return CardThemeData(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
      ),
      color: AppColors.cardBg,
      margin: EdgeInsets.zero,
    );
  }

  static ElevatedButtonThemeData get _elevatedButtonTheme {
    return ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        elevation: 0,
        backgroundColor: AppColors.primaryBlue,
        foregroundColor: AppColors.textOnPrimary,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        textStyle: const TextStyle(
          fontSize: 16, fontWeight: FontWeight.w600, fontFamily: 'Cairo',
        ),
      ),
    );
  }

  static OutlinedButtonThemeData get _outlinedButtonTheme {
    return OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.primaryBlue,
        side: const BorderSide(color: AppColors.primaryBlue, width: 1.5),
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        textStyle: const TextStyle(
          fontSize: 16, fontWeight: FontWeight.w600, fontFamily: 'Cairo',
        ),
      ),
    );
  }

  static TextButtonThemeData get _textButtonTheme {
    return TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: AppColors.primaryBlue,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        textStyle: const TextStyle(
          fontSize: 14, fontWeight: FontWeight.w600, fontFamily: 'Cairo',
        ),
      ),
    );
  }

  static InputDecorationTheme get _inputDecorationTheme {
    return InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surface,
      contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: BorderSide.none,
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.divider, width: 1),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.primaryBlue, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.error, width: 1.5),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: AppColors.error, width: 2),
      ),
      hintStyle: const TextStyle(
        color: AppColors.textMuted, fontSize: 14, fontFamily: 'Cairo',
      ),
      labelStyle: const TextStyle(
        color: AppColors.textSecondary, fontSize: 14, fontFamily: 'Cairo',
      ),
    );
  }

  static ChipThemeData get _chipTheme {
    return ChipThemeData(
      backgroundColor: AppColors.background,
      selectedColor: AppColors.primaryBlue,
      labelStyle: const TextStyle(
        fontSize: 13, fontWeight: FontWeight.w500, fontFamily: 'Cairo',
      ),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
    );
  }

  static DividerThemeData get _dividerTheme {
    return const DividerThemeData(
      color: AppColors.divider,
      thickness: 1,
      space: 1,
    );
  }

  static SnackBarThemeData get _snackBarTheme {
    return SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
      ),
      contentTextStyle: const TextStyle(
        fontSize: 14, fontWeight: FontWeight.w500, fontFamily: 'Cairo',
      ),
    );
  }
}

// Gradient helpers
class AppGradients {
  AppGradients._();

  static const LinearGradient primary = LinearGradient(
    colors: [AppColors.primaryBlue, AppColors.accentCyan],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient primaryHorizontal = LinearGradient(
    colors: [AppColors.primaryBlue, AppColors.accentSky],
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
  );

  static const LinearGradient surface = LinearGradient(
    colors: [Colors.white, Color(0xFFF1F5F9)],
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
  );

  static const LinearGradient shimmer = LinearGradient(
    colors: [AppColors.shimmerBase, AppColors.shimmerHighlight, AppColors.shimmerBase],
    stops: [0.0, 0.5, 1.0],
    begin: Alignment(-1.0, -0.3),
    end: Alignment(1.0, 0.3),
  );

  static LinearGradient cardGradient(Color color) {
    return LinearGradient(
      colors: [color.withValues(alpha: 0.15), color.withValues(alpha: 0.05)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    );
  }
}
