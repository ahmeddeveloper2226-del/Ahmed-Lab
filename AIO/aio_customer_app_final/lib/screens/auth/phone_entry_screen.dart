import 'package:flutter/material.dart';
import '../../core/utils/error_helpers.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/animations/custom_animations.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/helpers.dart';
import '../../providers/auth_provider.dart';

class PhoneEntryScreen extends ConsumerStatefulWidget {
  const PhoneEntryScreen({super.key});

  @override
  ConsumerState<PhoneEntryScreen> createState() => _PhoneEntryScreenState();
}

class _PhoneEntryScreenState extends ConsumerState<PhoneEntryScreen> {
  final _phoneController = TextEditingController();
  bool _isValid = false;
  bool _isLoading = false;

  void _validatePhone(String value) {
    setState(() {
      _isValid = Helpers.isValidEgyptianPhone(value);
    });
  }

  Future<void> _sendCode() async {
    if (!_isValid || _isLoading) return;
    
    setState(() => _isLoading = true);
    
    try {
      final phone = Helpers.formatPhone(_phoneController.text);
      print('🔥 Sending code to: $phone');
      
      await ref.read(authNotifierProvider.notifier).verifyPhone(phone);
      
      // Check if the notifier state has error
      final state = ref.read(authNotifierProvider);
      if (state.hasError) {
        throw state.error!;
      }
      
      if (mounted) {
        print('🔥 Code sent successfully, navigating to OTP');
        context.push('/otp?phone=$phone');
      }
    } catch (e) {
      print('🔥 Error sending code: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('فشل إرسال الرمز: ${friendlyErrorMessage(e)}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
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
                'رقم هاتفك',
                style: TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.w900,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
            const SizedBox(height: 8),
            const FadeSlideIn(
              delay: Duration(milliseconds: 100),
              child: Text(
                'سنرسل لك رمز التحقق على هذا الرقم',
                style: TextStyle(
                  fontSize: 16,
                  color: AppColors.textSecondary,
                ),
              ),
            ),
            const SizedBox(height: 40),
            FadeSlideIn(
              delay: const Duration(milliseconds: 200),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.05),
                      blurRadius: 20,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: AppColors.background,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text('+20', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
                          SizedBox(width: 4),
                          Icon(Icons.arrow_drop_down, size: 18),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextField(
                        controller: _phoneController,
                        keyboardType: TextInputType.phone,
                        onChanged: _validatePhone,
                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                        decoration: const InputDecoration(
                          hintText: '101 234 5678',
                          border: InputBorder.none,
                          contentPadding: EdgeInsets.symmetric(vertical: 18),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const Spacer(),
            FadeSlideIn(
              delay: const Duration(milliseconds: 300),
              child: GestureDetector(
                onTap: _isValid && !_isLoading ? _sendCode : null,
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 300),
                  padding: const EdgeInsets.symmetric(vertical: 18),
                  decoration: BoxDecoration(
                    gradient: _isValid && !_isLoading ? AppGradients.primary : null,
                    color: _isValid && !_isLoading ? null : AppColors.divider,
                    borderRadius: BorderRadius.circular(20),
                    boxShadow: _isValid && !_isLoading
                        ? [BoxShadow(color: AppColors.primaryBlue.withValues(alpha: 0.3), blurRadius: 20, offset: const Offset(0, 8))]
                        : null,
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
                          'إرسال الرمز',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                            color: _isValid && !_isLoading ? Colors.white : AppColors.textMuted,
                          ),
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
    _phoneController.dispose();
    super.dispose();
  }
}