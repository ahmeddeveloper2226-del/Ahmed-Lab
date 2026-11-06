import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/animations/custom_animations.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/auth_provider.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  bool _isGoogleLoading = false;
  bool _isAppleLoading = false;

  Future<void> _signInWithGoogle() async {
    setState(() => _isGoogleLoading = true);
    await ref.read(authNotifierProvider.notifier).signInWithGoogle();
    if (!mounted) return;
    setState(() => _isGoogleLoading = false);
    final error = ref.read(authNotifierProvider).error;
    if (error != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_friendlyAuthErrorMessage(error))),
      );
    }
    // On success the router redirects automatically once Firebase's
    // authStateChanges stream fires (see app_router.dart).
  }

  Future<void> _signInWithApple() async {
    setState(() => _isAppleLoading = true);
    await ref.read(authNotifierProvider.notifier).signInWithApple();
    if (!mounted) return;
    setState(() => _isAppleLoading = false);
    final error = ref.read(authNotifierProvider).error;
    if (error != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_friendlyAuthErrorMessage(error))),
      );
    }
  }

  /// Translates whatever _authRepo/AuthNotifier threw into something a user
  /// should actually see. Previously this just interpolated the raw error
  /// object into the SnackBar text — for a DioException that means the
  /// user sees the ENTIRE multi-paragraph "This exception was thrown
  /// because the response has a status code of 401..." explanation text,
  /// which is meant for a developer's console, not an end user.
  String _friendlyAuthErrorMessage(Object error) {
    final text = error.toString();
    if (text.contains('401') || text.contains('DioException')) {
      return 'تعذر تسجيل الدخول. حاول مرة أخرى بعد قليل.';
    }
    if (text.contains('network') || text.contains('SocketException')) {
      return 'تحقق من اتصالك بالإنترنت وحاول مرة أخرى.';
    }
    return 'تعذر تسجيل الدخول. حاول مرة أخرى.';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppGradients.primary),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Spacer(),
                ScaleBounce(
                  child: Container(
                    width: 100,
                    height: 100,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(28),
                    ),
                    child: const Center(
                      child: Padding(
                        padding: EdgeInsets.all(16),
                        child: Image(
                          image: AssetImage('assets/images/logo_mark.png'),
                          fit: BoxFit.contain,
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 32),
                const FadeSlideIn(
                  child: Text(
                    'مرحبا بك في AIO',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                FadeSlideIn(
                  delay: const Duration(milliseconds: 100),
                  child: Text(
                    'كل ما تحتاجه في مكان واحد',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 16,
                      color: Colors.white.withValues(alpha: 0.8),
                    ),
                  ),
                ),
                const Spacer(),
                FadeSlideIn(
                  delay: const Duration(milliseconds: 200),
                  child: _SocialButton(
                    icon: Icons.g_mobiledata,
                    label: 'Google',
                    onTap: _isGoogleLoading ? null : _signInWithGoogle,
                    color: const Color(0xFF4285F4),
                    textColor: Colors.white,
                    isLoading: _isGoogleLoading,
                  ),
                ),
                const SizedBox(height: 12),
                FadeSlideIn(
                  delay: const Duration(milliseconds: 400),
                  child: _SocialButton(
                    icon: Icons.apple,
                    label: 'Apple',
                    onTap: _isAppleLoading ? null : _signInWithApple,
                    color: Colors.black,
                    textColor: Colors.white,
                    isLoading: _isAppleLoading,
                  ),
                ),
                const SizedBox(height: 32),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _SocialButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback? onTap;
  final Color color;
  final Color textColor;
  final bool isLoading;

  const _SocialButton({
    required this.icon,
    required this.label,
    required this.onTap,
    required this.color,
    required this.textColor,
    this.isLoading = false,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 24),
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.1),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (isLoading)
              SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(strokeWidth: 2, color: textColor),
              )
            else
              Icon(icon, color: textColor, size: 24),
            const SizedBox(width: 12),
            Text(
              label,
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: textColor,
              ),
            ),
          ],
        ),
      ),
    );
  }
}