import 'package:flutter/material.dart';
import '../../core/utils/error_helpers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/animations/custom_animations.dart';
import '../../core/theme/app_theme.dart';
import '../../data/repositories/auth_repository.dart';
import '../../providers/profile_provider.dart';

class EmailVerificationScreen extends ConsumerStatefulWidget {
  const EmailVerificationScreen({super.key});

  @override
  ConsumerState<EmailVerificationScreen> createState() => _EmailVerificationScreenState();
}

class _EmailVerificationScreenState extends ConsumerState<EmailVerificationScreen> {
  final _emailController = TextEditingController();
  final _codeController = TextEditingController();
  bool _codeSent = false;
  bool _isLoading = false;
  int _expiresIn = 0;

  Future<void> _sendCode() async {
    if (_emailController.text.isEmpty) return;

    setState(() => _isLoading = true);
    try {
      print('🔥 Sending email code to: ${_emailController.text}');
      final response = await ref.read(authRepositoryProvider).sendEmailVerificationCode(
        _emailController.text,
      );
      setState(() {
        _codeSent = true;
        _expiresIn = response.expires_in_seconds;
        _isLoading = false;
      });
      print('🔥 Email code sent, expires in: $_expiresIn');
    } catch (e) {
      print('🔥 Error sending email code: $e');
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('حدث خطأ: ${friendlyErrorMessage(e)}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _verifyCode() async {
    if (_codeController.text.length != 6) return;

    setState(() => _isLoading = true);
    try {
      print('🔥 Verifying email code: ${_codeController.text}');
      await ref.read(authRepositoryProvider).verifyEmailCode(_codeController.text);
      ref.invalidate(profileProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('تم توثيق البريد الإلكتروني بنجاح'),
            backgroundColor: Colors.green,
          ),
        );
        context.pop();
      }
    } catch (e) {
      print('🔥 Error verifying email code: $e');
      setState(() => _isLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('رمز التحقق غير صحيح: ${friendlyErrorMessage(e)}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('توثيق البريد'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new),
          onPressed: () => context.pop(),
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            FadeSlideIn(
              child: Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      AppColors.primaryBlue.withValues(alpha: 0.1),
                      AppColors.accentCyan.withValues(alpha: 0.05),
                    ],
                  ),
                  borderRadius: BorderRadius.circular(24),
                ),
                child: const Icon(
                  Icons.email_outlined,
                  size: 64,
                  color: AppColors.primaryBlue,
                ),
              ),
            ),
            const SizedBox(height: 32),
            FadeSlideIn(
              delay: const Duration(milliseconds: 100),
              child: Text(
                _codeSent ? 'أدخل الرمز' : 'أدخل بريدك الإلكتروني',
                style: const TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
            const SizedBox(height: 8),
            FadeSlideIn(
              delay: const Duration(milliseconds: 150),
              child: Text(
                _codeSent
                    ? 'أرسلنا رمز التحقق إلى ${_emailController.text}'
                    : 'سنرسل لك رمز تحقق مكون من 6 أرقام',
                style: const TextStyle(
                  fontSize: 14,
                  color: AppColors.textMuted,
                ),
              ),
            ),
            const SizedBox(height: 32),

            if (!_codeSent) ...[
              FadeSlideIn(
                delay: const Duration(milliseconds: 200),
                child: TextField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(
                    labelText: 'البريد الإلكتروني',
                    hintText: 'example@email.com',
                  ),
                ),
              ),
            ] else ...[
              FadeSlideIn(
                delay: const Duration(milliseconds: 200),
                child: TextField(
                  controller: _codeController,
                  keyboardType: TextInputType.number,
                  maxLength: 6,
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 8,
                  ),
                  decoration: const InputDecoration(
                    labelText: 'رمز التحقق',
                    counterText: '',
                  ),
                ),
              ),
            ],

            const Spacer(),

            FadeSlideIn(
              delay: const Duration(milliseconds: 300),
              child: GestureDetector(
                onTap: _isLoading
                    ? null
                    : _codeSent
                        ? _verifyCode
                        : _sendCode,
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(vertical: 18),
                  decoration: BoxDecoration(
                    gradient: AppGradients.primary,
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.primaryBlue.withValues(alpha: 0.3),
                        blurRadius: 20,
                        offset: const Offset(0, 8),
                      ),
                    ],
                  ),
                  child: _isLoading
                      ? const Center(
                          child: SizedBox(
                            width: 24,
                            height: 24,
                            child: CircularProgressIndicator(
                              color: Colors.white,
                              strokeWidth: 2,
                            ),
                          ),
                        )
                      : Text(
                          _codeSent ? 'تحقق' : 'إرسال الرمز',
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
                          ),
                        ),
                ),
              ),
            ),

            if (_codeSent) ...[
              const SizedBox(height: 16),
              Center(
                child: TextButton(
                  onPressed: _isLoading ? null : _sendCode,
                  child: const Text('إعادة إرسال الرمز'),
                ),
              ),
            ],

            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _emailController.dispose();
    _codeController.dispose();
    super.dispose();
  }
}