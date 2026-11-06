import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/animations/custom_animations.dart';
import '../../../core/theme/app_theme.dart';
import '../../../providers/auth_provider.dart';

class DriverLoginScreen extends ConsumerStatefulWidget {
  const DriverLoginScreen({super.key});

  @override
  ConsumerState<DriverLoginScreen> createState() => _DriverLoginScreenState();
}

class _DriverLoginScreenState extends ConsumerState<DriverLoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _phoneController = TextEditingController();
  bool _isLoading = false;

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);
    await ref.read(authNotifierProvider.notifier).loginAsDriver(_phoneController.text.trim());
    if (!mounted) return;
    setState(() => _isLoading = false);

    final error = ref.read(authNotifierProvider).error;
    if (error != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'لم يتم العثور على حساب سائق بهذا الرقم. تأكد من إضافتك كسائق أولاً.',
          ),
        ),
      );
    }
    // On success the router redirects automatically into the driver shell
    // (see app_router.dart) once the role claim/override is in place.
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppGradients.primary),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  IconButton(
                    onPressed: () => context.go('/role-selection'),
                    icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    width: 80,
                    height: 80,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(24),
                    ),
                    child: const Icon(Icons.two_wheeler_rounded, color: AppColors.primaryBlue, size: 40),
                  ),
                  const SizedBox(height: 24),
                  const FadeSlideIn(
                    child: Text(
                      'تسجيل دخول السائق',
                      style: TextStyle(
                        fontSize: 26,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  FadeSlideIn(
                    delay: const Duration(milliseconds: 100),
                    child: Text(
                      'أدخل اسمك ورقم هاتفك المسجل لدينا',
                      style: TextStyle(fontSize: 14, color: Colors.white.withValues(alpha: 0.85)),
                    ),
                  ),
                  const SizedBox(height: 32),
                  FadeSlideIn(
                    delay: const Duration(milliseconds: 150),
                    child: Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Column(
                        children: [
                          TextFormField(
                            controller: _nameController,
                            textAlign: TextAlign.right,
                            decoration: const InputDecoration(
                              labelText: 'الاسم الكامل',
                              prefixIcon: Icon(Icons.person_outline_rounded),
                            ),
                            validator: (value) {
                              if (value == null || value.trim().length < 2) {
                                return 'يرجى إدخال اسمك الكامل';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 16),
                          TextFormField(
                            controller: _phoneController,
                            textAlign: TextAlign.right,
                            keyboardType: TextInputType.phone,
                            decoration: const InputDecoration(
                              labelText: 'رقم الهاتف',
                              hintText: '+201234567890',
                              prefixIcon: Icon(Icons.phone_outlined),
                            ),
                            validator: (value) {
                              if (value == null || value.trim().length < 8) {
                                return 'يرجى إدخال رقم هاتف صحيح';
                              }
                              return null;
                            },
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  FadeSlideIn(
                    delay: const Duration(milliseconds: 200),
                    child: Text(
                      'لا حاجة لرمز تحقق — تتم إضافة السائقين فقط من خلال مقابلة شخصية مع الإدارة.',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 12, color: Colors.white.withValues(alpha: 0.75)),
                    ),
                  ),
                  const SizedBox(height: 24),
                  FadeSlideIn(
                    delay: const Duration(milliseconds: 250),
                    child: SizedBox(
                      height: 56,
                      child: ElevatedButton(
                        onPressed: _isLoading ? null : _submit,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.white,
                          foregroundColor: AppColors.primaryBlue,
                        ),
                        child: _isLoading
                            ? const SizedBox(
                                width: 24, height: 24,
                                child: CircularProgressIndicator(strokeWidth: 2, color: AppColors.primaryBlue),
                              )
                            : const Text('دخول', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}