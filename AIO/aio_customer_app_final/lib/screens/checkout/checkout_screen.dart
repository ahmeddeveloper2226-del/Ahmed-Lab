import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../../core/animations/custom_animations.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/helpers.dart';
import '../../core/utils/error_helpers.dart';
import '../../providers/cart_provider.dart';
import '../../providers/checkout_provider.dart';
import '../../providers/profile_provider.dart';
import '../../data/repositories/order_repository.dart';
import '../../widgets/checkout/branch_picker_section.dart';
import 'package:aio_customer_app/core/extensions/context_extensions.dart';

class CheckoutScreen extends ConsumerStatefulWidget {
  const CheckoutScreen({super.key});

  @override
  ConsumerState<CheckoutScreen> createState() => _CheckoutScreenState();
}

class _CheckoutScreenState extends ConsumerState<CheckoutScreen> {
  int _currentStep = 0;
  String? _selectedAddressId;
  String? _paymentUrl;
  bool _isProcessing = false;

  final _steps = ['السلة', 'العنوان', 'الدفع'];

  /// Builds the billing_data Paymob requires (spec: checkout_router.py
  /// validates first_name, last_name, email, phone_number, city, country,
  /// street, building, floor, apartment before ever calling Paymob).
  ///
  /// Neither UserProfileResponse nor AddressResponse track these as
  /// separate structured fields today (full_name is one field; addresses
  /// are one free-text full_address, not street/building/floor/apartment).
  /// Rather than silently sending an empty map — which 422s on EVERY
  /// checkout — this makes the best honest use of what's actually on
  /// file and uses clearly-marked placeholders ("NA") only for the
  /// fields we genuinely don't collect yet. AIO currently only operates
  /// in Cairo (see the delivery spec), so city/country are safe constants
  /// rather than guesses.
  Map<String, dynamic> _buildBillingData({
    required dynamic profile, // UserProfileResponse
    required dynamic address, // AddressResponse
  }) {
    final fullName = (profile?.full_name as String?)?.trim();
    String firstName = 'AIO';
    String lastName = 'Customer';
    if (fullName != null && fullName.isNotEmpty) {
      final parts = fullName.split(RegExp(r'\s+'));
      firstName = parts.first;
      lastName = parts.length > 1 ? parts.sublist(1).join(' ') : parts.first;
    }

    final phone = (profile?.phone_number as String?) ?? 'NA';
    final email = (profile?.email as String?) ?? '${phone == 'NA' ? 'customer' : phone}@aio-noemail.app';
    final street = (address?.full_address as String?)?.trim();

    return {
      'first_name': firstName,
      'last_name': lastName,
      'email': email,
      'phone_number': phone,
      'city': 'Cairo',
      'country': 'EG',
      'street': (street == null || street.isEmpty) ? 'NA' : street,
      'building': 'NA',
      'floor': 'NA',
      'apartment': 'NA',
    };
  }

  Future<void> _proceedToPayment() async {
    if (_selectedAddressId == null) return;

    setState(() => _isProcessing = true);
    try {
      final branchSelections = ref.read(checkoutBranchSelectionsProvider);
      final profile = ref.read(profileProvider).valueOrNull;
      final addresses = ref.read(addressesProvider).valueOrNull ?? [];
      final selectedAddress = addresses.where((a) => a.id == _selectedAddressId).firstOrNull;

      final response = await ref.read(orderRepositoryProvider).checkout(
        _selectedAddressId!,
        _buildBillingData(profile: profile, address: selectedAddress),
        branchSelections: branchSelections.isEmpty ? null : branchSelections,
      );
      setState(() {
        _paymentUrl = response.payment_url;
        _currentStep = 2;
        _isProcessing = false;
      });
    } catch (e) {
      setState(() => _isProcessing = false);
      if (mounted) context.showSnackBar('حدث خطأ في الدفع', isError: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cartAsync = ref.watch(cartProvider);
    final addressesAsync = ref.watch(addressesProvider);

    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        title: const Text('إتمام الطلب'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new),
          onPressed: () => context.pop(),
        ),
      ),
      body: _paymentUrl != null
          ? WebViewWidget(
              controller: WebViewController()
                ..setJavaScriptMode(JavaScriptMode.unrestricted)
                ..loadRequest(Uri.parse(_paymentUrl!)),
            )
          : Column(
              children: [
                // Step indicator
                Container(
                  padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 24),
                  color: Colors.white,
                  child: Row(
                    children: List.generate(_steps.length * 2 - 1, (index) {
                      if (index.isOdd) {
                        final stepIndex = index ~/ 2;
                        return Expanded(
                          child: Container(
                            height: 2,
                            margin: const EdgeInsets.symmetric(horizontal: 8),
                            decoration: BoxDecoration(
                              gradient: stepIndex < _currentStep
                                  ? AppGradients.primary
                                  : null,
                              color: stepIndex < _currentStep
                                  ? null
                                  : AppColors.divider,
                              borderRadius: BorderRadius.circular(1),
                            ),
                          ),
                        );
                      }
                      final stepIndex = index ~/ 2;
                      final isActive = stepIndex <= _currentStep;
                      final isCurrent = stepIndex == _currentStep;

                      return AnimatedContainer(
                        duration: const Duration(milliseconds: 300),
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          gradient: isActive ? AppGradients.primary : null,
                          color: isActive ? null : AppColors.divider,
                          shape: BoxShape.circle,
                          boxShadow: isCurrent
                              ? [
                                  BoxShadow(
                                    color: AppColors.primaryBlue.withValues(alpha: 0.3),
                                    blurRadius: 12,
                                    offset: const Offset(0, 4),
                                  ),
                                ]
                              : null,
                        ),
                        child: Center(
                          child: Text(
                            '${stepIndex + 1}',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w700,
                              color: isActive ? Colors.white : AppColors.textMuted,
                            ),
                          ),
                        ),
                      );
                    }),
                  ),
                ),

                // Step content
                Expanded(
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 300),
                    child: _buildStepContent(cartAsync, addressesAsync),
                  ),
                ),

                // Bottom action
                if (_currentStep < 2)
                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: const BorderRadius.vertical(
                        top: Radius.circular(32),
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.08),
                          blurRadius: 30,
                          offset: const Offset(0, -10),
                        ),
                      ],
                    ),
                    child: SafeArea(
                      child: Row(
                        children: [
                          if (_currentStep > 0)
                            Expanded(
                              child: OutlinedButton(
                                onPressed: () => setState(() => _currentStep--),
                                child: const Text('السابق'),
                              ),
                            ),
                          if (_currentStep > 0) const SizedBox(width: 12),
                          Expanded(
                            flex: 2,
                            child: GestureDetector(
                              onTap: _currentStep == 0
                                  ? () => setState(() => _currentStep++)
                                  : _isProcessing
                                      ? null
                                      : _proceedToPayment,
                              child: Container(
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
                                child: _isProcessing
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
                                        _currentStep == 0 ? 'اختيار العنوان' : 'الدفع الآن',
                                        textAlign: TextAlign.center,
                                        style: const TextStyle(
                                          fontSize: 16,
                                          fontWeight: FontWeight.w700,
                                          color: Colors.white,
                                        ),
                                      ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
    );
  }

  Widget _buildStepContent(AsyncValue<dynamic> cartAsync, AsyncValue<dynamic> addressesAsync) {
    switch (_currentStep) {
      case 0:
        return cartAsync.when(
          data: (cart) {
            // One picker per distinct shop in the cart (spec: "the customer
            // selects Store -> Branch"). Each picker silently renders
            // nothing for a single-location shop, so this is a no-op for
            // the overwhelming majority of carts.
            final shopIds = <String>{};
            final shopNames = <String, String>{};
            for (final item in cart.items) {
              shopIds.add(item.shop_id);
              shopNames[item.shop_id] = item.shop_name;
            }

            return ListView(
              physics: const BouncingScrollPhysics(),
              padding: const EdgeInsets.all(20),
              children: [
              ...shopIds.map((shopId) => BranchPickerSection(
                    shopId: shopId,
                    shopName: shopNames[shopId] ?? '',
                  )),
              ...cart.items.map((item) => FadeSlideIn(
                child: Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 48,
                        height: 48,
                        decoration: BoxDecoration(
                          color: AppColors.background,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.shopping_bag_outlined, color: AppColors.primaryBlue),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(item.name, style: const TextStyle(fontWeight: FontWeight.w600)),
                            Text('x${item.quantity}', style: const TextStyle(color: AppColors.textMuted)),
                          ],
                        ),
                      ),
                      Text(
                        Helpers.formatPrice(item.subtotal),
                        style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.primaryBlue),
                      ),
                    ],
                  ),
                ),
              )),
              const SizedBox(height: 12),
              FadeSlideIn(
                child: Container(
                  padding: const EdgeInsets.all(20),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('الإجمالي', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                      Text(
                        Helpers.formatPrice(cart.total),
                        style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: AppColors.primaryBlue),
                      ),
                    ],
                  ),
                ),
              ),
              ],
            );
          },
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (err, _) => Center(child: Text(friendlyErrorMessage(err))),
        );

      case 1:
        return addressesAsync.when(
          data: (addresses) => ListView(
            physics: const BouncingScrollPhysics(),
            padding: const EdgeInsets.all(20),
            children: [
              GestureDetector(
                onTap: () => context.push('/addresses/add'),
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: AppColors.primaryBlue.withValues(alpha: 0.3)),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.add_location_alt, color: AppColors.primaryBlue),
                      SizedBox(width: 12),
                      Text(
                        'إضافة عنوان جديد',
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          color: AppColors.primaryBlue,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              ...addresses.map((address) => GestureDetector(
                onTap: () => setState(() => _selectedAddressId = address.id),
                child: FadeSlideIn(
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    margin: const EdgeInsets.only(bottom: 12),
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      border: _selectedAddressId == address.id
                          ? Border.all(color: AppColors.primaryBlue, width: 2)
                          : null,
                      boxShadow: _selectedAddressId == address.id
                          ? [
                              BoxShadow(
                                color: AppColors.primaryBlue.withValues(alpha: 0.15),
                                blurRadius: 20,
                                offset: const Offset(0, 4),
                              ),
                            ]
                          : [
                              BoxShadow(
                                color: Colors.black.withValues(alpha: 0.04),
                                blurRadius: 15,
                                offset: const Offset(0, 4),
                              ),
                            ],
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 24,
                          height: 24,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            border: Border.all(
                              color: _selectedAddressId == address.id
                                  ? AppColors.primaryBlue
                                  : AppColors.divider,
                              width: 2,
                            ),
                            color: _selectedAddressId == address.id
                                ? AppColors.primaryBlue
                                : Colors.transparent,
                          ),
                          child: _selectedAddressId == address.id
                              ? const Icon(Icons.check, color: Colors.white, size: 14)
                              : null,
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                address.label ?? 'عنوان',
                                style: const TextStyle(fontWeight: FontWeight.w700),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                address.full_address,
                                style: const TextStyle(color: AppColors.textMuted, fontSize: 13),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              )),
            ],
          ),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (err, _) => Center(child: Text(friendlyErrorMessage(err))),
        );

      default:
        return const SizedBox();
    }
  }
}
