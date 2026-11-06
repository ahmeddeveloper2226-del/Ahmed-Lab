import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/animations/custom_animations.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/auth_provider.dart';

class OtpScreen extends ConsumerStatefulWidget {
  const OtpScreen({super.key});

  @override
  ConsumerState<OtpScreen> createState() => _OtpScreenState();
}

class _OtpScreenState extends ConsumerState<OtpScreen>
    with TickerProviderStateMixin {
  final List<TextEditingController> _controllers = List.generate(
    6,
    (_) => TextEditingController(),
  );
  final List<FocusNode> _focusNodes = List.generate(6, (_) => FocusNode());
  final List<AnimationController> _boxControllers = [];
  final List<Animation<double>> _boxAnimations = [];

  int _secondsRemaining = 60;
  Timer? _timer;
  bool _canResend = false;
  String _errorMessage = '';
  bool _isVerifying = false;

  @override
  void initState() {
    super.initState();
    for (int i = 0; i < 6; i++) {
      final ctrl = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 400),
      );
      _boxControllers.add(ctrl);
      _boxAnimations.add(
        Tween<double>(begin: 0, end: 1).animate(
          CurvedAnimation(parent: ctrl, curve: Curves.elasticOut),
        ),
      );
      Future.delayed(Duration(milliseconds: 100 * i), () {
        if (mounted) ctrl.forward();
      });
    }
    _startTimer();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNodes[0].requestFocus();
    });
  }

  void _startTimer() {
    _timer?.cancel();
    setState(() {
      _secondsRemaining = 60;
      _canResend = false;
    });
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_secondsRemaining > 0) {
        setState(() => _secondsRemaining--);
      } else {
        setState(() => _canResend = true);
        timer.cancel();
      }
    });
  }

  void _onDigitEntered(int index, String value) {
    if (value.isNotEmpty) {
      if (index < 5) {
        _focusNodes[index + 1].requestFocus();
      } else {
        _focusNodes[index].unfocus();
        _verifyCode();
      }
    }
  }

  void _onBackspace(int index, String value) {
    if (value.isEmpty && index > 0) {
      _focusNodes[index - 1].requestFocus();
    }
  }

  Future<void> _verifyCode() async {
    final code = _controllers.map((c) => c.text).join();
    if (code.length != 6 || _isVerifying) return;

    setState(() {
      _errorMessage = '';
      _isVerifying = true;
    });

    print('🔥 Verifying OTP: $code');

    try {
      await ref.read(authNotifierProvider.notifier).verifyOtp(code);
      
      // Wait a bit for state to update, then check
      await Future.delayed(const Duration(milliseconds: 500));
      
      final state = ref.read(authNotifierProvider);
      print('🔥 Auth state after verify: $state');

      if (state.hasError) {
        throw state.error!;
      }

      if (state.hasValue && mounted) {
        print('🔥 OTP verified, navigating to categories');
        context.go('/categories');
      }
    } catch (e) {
      print('🔥 OTP verification error: $e');
      if (mounted) {
        setState(() {
          _errorMessage = 'رمز التحقق غير صحيح';
          _isVerifying = false;
        });
        for (var ctrl in _boxControllers) {
          ctrl.reverse().then((_) => ctrl.forward());
        }
      }
    }
  }

  Future<void> _resendCode() async {
    if (!_canResend) return;
    _startTimer();
    final phone = GoRouterState.of(context).uri.queryParameters['phone'] ?? '';
    if (phone.isNotEmpty) {
      print('🔥 Resending code to: $phone');
      await ref.read(authNotifierProvider.notifier).verifyPhone(phone);
    }
  }

  @override
  Widget build(BuildContext context) {
    final phone = GoRouterState.of(context).uri.queryParameters['phone'] ?? '';

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios, color: AppColors.textPrimary),
          onPressed: () => context.pop(),
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const FadeSlideIn(
              child: Text(
                'رمز التحقق',
                style: TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.w900,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
            const SizedBox(height: 8),
            FadeSlideIn(
              delay: const Duration(milliseconds: 100),
              child: Text(
                'أدخل الرمز المكون من 6 أرقام المرسل إلى $phone',
                style: const TextStyle(
                  fontSize: 16,
                  color: AppColors.textSecondary,
                ),
              ),
            ),
            const SizedBox(height: 40),

            FadeSlideIn(
              delay: const Duration(milliseconds: 200),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: List.generate(6, (index) {
                  return AnimatedBuilder(
                    animation: _boxAnimations[index],
                    builder: (context, child) {
                      final hasError = _errorMessage.isNotEmpty;
                      return Transform.scale(
                        scale: _boxAnimations[index].value,
                        child: Container(
                          width: 50,
                          height: 60,
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(
                              color: hasError
                                  ? AppColors.error
                                  : _controllers[index].text.isNotEmpty
                                      ? AppColors.primaryBlue
                                      : AppColors.divider,
                              width: hasError ? 2 : 1.5,
                            ),
                            boxShadow: _controllers[index].text.isNotEmpty
                                ? [
                                    BoxShadow(
                                      color: AppColors.primaryBlue.withValues(alpha: 0.2),
                                      blurRadius: 12,
                                      offset: const Offset(0, 4),
                                    ),
                                  ]
                                : null,
                          ),
                          child: Center(
                            child: TextField(
                              controller: _controllers[index],
                              focusNode: _focusNodes[index],
                              textAlign: TextAlign.center,
                              keyboardType: TextInputType.number,
                              maxLength: 1,
                              style: const TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.w700,
                                color: AppColors.textPrimary,
                              ),
                              decoration: const InputDecoration(
                                counterText: '',
                                border: InputBorder.none,
                              ),
                              onChanged: (value) => _onDigitEntered(index, value),
                              onSubmitted: (_) => _onDigitEntered(index, _controllers[index].text),
                            ),
                          ),
                        ),
                      );
                    },
                  );
                }),
              ),
            ),

            if (_errorMessage.isNotEmpty) ...[
              const SizedBox(height: 16),
              FadeSlideIn(
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
                  decoration: BoxDecoration(
                    color: AppColors.error.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.error_outline, color: AppColors.error, size: 18),
                      const SizedBox(width: 8),
                      Text(
                        _errorMessage,
                        style: const TextStyle(
                          color: AppColors.error,
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],

            const Spacer(),

            FadeSlideIn(
              delay: const Duration(milliseconds: 300),
              child: Center(
                child: _canResend
                    ? TextButton(
                        onPressed: _resendCode,
                        child: const Text(
                          'إعادة إرسال الرمز',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: AppColors.primaryBlue,
                          ),
                        ),
                      )
                    : Text(
                        'إعادة الإرسال بعد $_secondsRemaining ثانية',
                        style: const TextStyle(
                          fontSize: 14,
                          color: AppColors.textMuted,
                        ),
                      ),
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    for (var c in _controllers) {
      c.dispose();
    }
    for (var f in _focusNodes) {
      f.dispose();
    }
    for (var c in _boxControllers) {
      c.dispose();
    }
    super.dispose();
  }
}