import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/animations/custom_animations.dart';
import '../../../core/theme/app_theme.dart';
import '../../../providers/auth_provider.dart';
import '../../../providers/driver_provider.dart';

class DriverProfileScreen extends ConsumerWidget {
  const DriverProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = FirebaseAuth.instance.currentUser;

    return Scaffold(
      backgroundColor: AppColors.background,
      body: CustomScrollView(
        physics: const BouncingScrollPhysics(),
        slivers: [
          SliverToBoxAdapter(
            child: Container(
              padding: const EdgeInsets.fromLTRB(24, 60, 24, 32),
              decoration: const BoxDecoration(
                gradient: AppGradients.primary,
                borderRadius: BorderRadius.vertical(bottom: Radius.circular(32)),
              ),
              child: Column(
                children: [
                  ScaleBounce(
                    child: Container(
                      width: 100,
                      height: 100,
                      decoration: BoxDecoration(
                        color: Colors.white,
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(color: Colors.black.withValues(alpha: 0.15), blurRadius: 20, offset: const Offset(0, 8)),
                        ],
                      ),
                      child: const Icon(Icons.two_wheeler_rounded, color: AppColors.primaryBlue, size: 48),
                    ),
                  ),
                  const SizedBox(height: 16),
                  FadeSlideIn(
                    child: Text(
                      user?.displayName ?? 'السائق',
                      style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: Colors.white),
                    ),
                  ),
                  const SizedBox(height: 4),
                  if (user?.phoneNumber != null)
                    Text(user!.phoneNumber!, style: TextStyle(color: Colors.white.withValues(alpha: 0.85))),
                ],
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.all(20),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                FadeSlideIn(
                  child: Container(
                    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
                    child: Column(
                      children: [
                        const ListTile(
                          leading: Icon(Icons.badge_outlined, color: AppColors.primaryBlue),
                          title: Text('حالة الحساب'),
                          subtitle: Text('نشط'),
                        ),
                        const Divider(height: 1),
                        ListTile(
                          leading: const Icon(Icons.logout_rounded, color: AppColors.error),
                          title: const Text('تسجيل الخروج', style: TextStyle(color: AppColors.error)),
                          onTap: () async {
                            await ref.read(authNotifierProvider.notifier).signOut();
                            ref.invalidate(driverActiveOrdersProvider);
                            ref.invalidate(driverOffersProvider);
                            if (context.mounted) context.go('/role-selection');
                          },
                        ),
                      ],
                    ),
                  ),
                ),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}