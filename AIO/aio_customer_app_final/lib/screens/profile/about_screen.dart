import 'package:flutter/material.dart';
import '../../core/animations/custom_animations.dart';
import '../../core/theme/app_theme.dart';

class AboutScreen extends StatelessWidget {
  const AboutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(title: const Text('عن التطبيق')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          FadeSlideIn(
            child: Center(
              child: Container(
                width: 96,
                height: 96,
                margin: const EdgeInsets.only(bottom: 20),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(28),
                  boxShadow: [
                    BoxShadow(color: AppColors.primaryBlue.withValues(alpha: 0.3), blurRadius: 24, offset: const Offset(0, 10)),
                  ],
                ),
                child: const Center(
                  child: Padding(
                    padding: EdgeInsets.all(14),
                    child: Image(
                      image: AssetImage('assets/images/logo_mark.png'),
                      fit: BoxFit.contain,
                    ),
                  ),
                ),
              ),
            ),
          ),
          const FadeSlideIn(
            delay: Duration(milliseconds: 100),
            child: Center(
              child: Text('AIO', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800, color: AppColors.textPrimary)),
            ),
          ),
          const SizedBox(height: 4),
          const FadeSlideIn(
            delay: Duration(milliseconds: 150),
            child: Center(
              child: Text('الإصدار 1.0.0', style: TextStyle(fontSize: 13, color: AppColors.textMuted)),
            ),
          ),
          const SizedBox(height: 28),
          FadeSlideIn(
            delay: const Duration(milliseconds: 200),
            child: Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
              child: const Text(
                'AIO هو تطبيقك الشامل للتوصيل — كل ما تحتاجه في مكان واحد. '
                'تسوق من البقالة والمطاعم والصيدليات والملابس والإلكترونيات، '
                'واطلب توصيل سريع وآمن مباشرة إلى باب منزلك.\n\n'
                'يتيح لك التطبيق أيضًا تتبع طلبك مباشرة على الخريطة، والتواصل '
                'مع السائق عبر الدردشة أو المكالمات الصوتية داخل التطبيق حتى '
                'وصول طلبك بأمان.',
                style: TextStyle(fontSize: 14, color: AppColors.textSecondary, height: 1.8),
              ),
            ),
          ),
          const SizedBox(height: 20),
          FadeSlideIn(
            delay: const Duration(milliseconds: 250),
            child: Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: AppColors.primaryBlue.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.code_rounded, color: AppColors.primaryBlue),
                      ),
                      const SizedBox(width: 12),
                      const Text('تم التطوير بواسطة', style: TextStyle(fontSize: 13, color: AppColors.textMuted)),
                    ],
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    'IntelligentEra Tech Company',
                    style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800, color: AppColors.textPrimary),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}