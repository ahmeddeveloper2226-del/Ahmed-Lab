import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/animations/custom_animations.dart';
import '../../core/theme/app_theme.dart';
import '../../data/models/address_model.dart';
import '../../data/repositories/profile_repository.dart';
import '../../providers/profile_provider.dart';
import 'package:aio_customer_app/core/extensions/context_extensions.dart';

class AddAddressScreen extends ConsumerStatefulWidget {
  const AddAddressScreen({super.key});

  @override
  ConsumerState<AddAddressScreen> createState() => _AddAddressScreenState();
}

class _AddAddressScreenState extends ConsumerState<AddAddressScreen> {
  final _labelController = TextEditingController();
  final _addressController = TextEditingController();
  bool _isDefault = false;
  bool _isLoading = false;

  Future<void> _saveAddress() async {
    if (_addressController.text.isEmpty) return;

    setState(() => _isLoading = true);
    try {
      await ref.read(profileRepositoryProvider).createAddress(
        AddressCreateRequest(
          label: _labelController.text.isEmpty ? null : _labelController.text,
          full_address: _addressController.text,
          is_default: _isDefault,
        ),
      );
      ref.invalidate(addressesProvider);
      if (mounted) context.pop();
    } catch (e) {
      if (mounted) context.showSnackBar('حدث خطأ', isError: true);
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('عنوان جديد'),
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
              child: TextField(
                controller: _labelController,
                decoration: const InputDecoration(
                  labelText: 'الاسم (اختياري)',
                  hintText: 'مثال: المنزل، العمل',
                ),
              ),
            ),
            const SizedBox(height: 16),
            FadeSlideIn(
              delay: const Duration(milliseconds: 100),
              child: TextField(
                controller: _addressController,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: 'العنوان بالتفصيل',
                  hintText: 'الشارع، الحي، المدينة',
                ),
              ),
            ),
            const SizedBox(height: 16),
            FadeSlideIn(
              delay: const Duration(milliseconds: 200),
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Row(
                  children: [
                    const Text(
                      'تعيين كعنوان افتراضي',
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const Spacer(),
                    Switch.adaptive(
                      value: _isDefault,
                      onChanged: (v) => setState(() => _isDefault = v),
                      activeColor: AppColors.primaryBlue,
                    ),
                  ],
                ),
              ),
            ),
            const Spacer(),
            FadeSlideIn(
              delay: const Duration(milliseconds: 300),
              child: GestureDetector(
                onTap: _isLoading ? null : _saveAddress,
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
                      : const Text(
                          'حفظ العنوان',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                            color: Colors.white,
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
    _labelController.dispose();
    _addressController.dispose();
    super.dispose();
  }
}
