import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:geocoding/geocoding.dart';
import '../../core/theme/app_theme.dart';
import '../../providers/cart_provider.dart';
import '../../data/models/address_model.dart';
import '../../data/repositories/profile_repository.dart';
import '../../data/services/location_service.dart';
import '../../providers/profile_provider.dart';
import '../ai_assistant/ai_assistant_overlay.dart';

class MainShell extends ConsumerStatefulWidget {
  final StatefulNavigationShell navigationShell;
  const MainShell({super.key, required this.navigationShell});

  @override
  ConsumerState<MainShell> createState() => _MainShellState();
}

class _MainShellState extends ConsumerState<MainShell>
    with TickerProviderStateMixin {
  late int _currentIndex;
  late List<AnimationController> _controllers;
  late List<Animation<double>> _animations;

  final _labels = ['الرئيسية', 'بحث', 'طلباتي', 'حسابي'];
  final _icons = [
    Icons.grid_view_rounded,
    Icons.search_rounded,
    Icons.receipt_long_rounded,
    Icons.person_rounded,
  ];

  @override
  void initState() {
    super.initState();
    _currentIndex = widget.navigationShell.currentIndex;
    _controllers = List.generate(
      4,
      (i) => AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 400),
      ),
    );
    _animations = _controllers
        .map((c) => Tween<double>(begin: 0, end: 1).animate(
              CurvedAnimation(parent: c, curve: Curves.elasticOut),
            ))
        .toList();
    _controllers[_currentIndex].forward();

    // This shell is what the router lands the user on right after a
    // successful login (Google/Apple/phone — all of them), so it's the one
    // place that covers every sign-in method instead of duplicating this in
    // each login screen. Runs once per cold start of the shell, not once
    // per tab switch.
    WidgetsBinding.instance.addPostFrameCallback((_) => _ensureDefaultLocation());
  }

  /// If the customer has no saved addresses at all yet, silently detects
  /// their current location (after the OS permission prompt) and saves it
  /// as a "Default" address — so there's always at least one address ready
  /// at checkout instead of forcing a first-time "add an address" detour.
  /// Deliberately best-effort: permission denied, location services off, or
  /// any network hiccup here just means no default gets created yet — never
  /// blocks or interrupts using the app, and there's no error shown for it.
  Future<void> _ensureDefaultLocation() async {
    try {
      final existing = await ref.read(profileRepositoryProvider).getAddresses();
      if (existing.isNotEmpty) return;

      final locationService = ref.read(locationServiceProvider);
      final result = await locationService.getCurrentLocation();
      if (!result.isSuccess) return;

      String fullAddress = '${result.lat}, ${result.lng}';
      try {
        final placemarks = await placemarkFromCoordinates(result.lat!, result.lng!);
        if (placemarks.isNotEmpty) {
          final p = placemarks.first;
          final parts = [p.street, p.subLocality, p.locality, p.administrativeArea]
              .where((s) => s != null && s.trim().isNotEmpty)
              .toList();
          if (parts.isNotEmpty) fullAddress = parts.join('، ');
        }
      } catch (_) {
        // Reverse geocoding failed (e.g. no network) — fall back to raw
        // coordinates rather than skipping the default address entirely;
        // lat/lng alone is still enough for delivery routing.
      }

      await ref.read(profileRepositoryProvider).createAddress(
            AddressCreateRequest(
              label: 'Default',
              full_address: fullAddress,
              lat: result.lat,
              lng: result.lng,
              is_default: true,
            ),
          );
      ref.invalidate(addressesProvider);
    } catch (_) {
      // Best-effort, as above — a failed background save is invisible to
      // the user and just means they'll add an address manually later.
    }
  }

  @override
  void didUpdateWidget(covariant MainShell oldWidget) {
    super.didUpdateWidget(oldWidget);
    // The shell rebuilds with a new navigationShell whenever the active
    // branch changes — whether from a tab tap, the system back button, or
    // a deep link — so syncing the icon animation here (rather than only
    // inside the tap handler) keeps it correct for every case.
    final newIndex = widget.navigationShell.currentIndex;
    if (newIndex != _currentIndex) {
      _controllers[_currentIndex].reverse();
      _controllers[newIndex].forward();
      _currentIndex = newIndex;
    }
  }

  void _onTap(int index) {
    widget.navigationShell.goBranch(
      index,
      // Tapping the already-selected tab resets that tab's own navigation
      // stack back to its root instead of doing nothing.
      initialLocation: index == widget.navigationShell.currentIndex,
    );
  }

  @override
  void dispose() {
    for (var c in _controllers) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cartCount = ref.watch(cartItemCountProvider);

    return Scaffold(
      // Stacked so the FAB/panel float above whichever tab is active,
      // rather than needing to be added to each of the 4 tab screens
      // individually.
      body: Stack(
        children: [
          widget.navigationShell,
          const AiAssistantOverlay(),
        ],
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.08),
              blurRadius: 20,
              offset: const Offset(0, -5),
            ),
          ],
        ),
        child: SafeArea(
          top: false,
          child: SizedBox(
            height: 80,
            child: Row(
              children: List.generate(4, (index) {
                return Expanded(
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: () => _onTap(index),
                    child: SizedBox(
                      height: double.infinity,
                      child: AnimatedNavItem(
                        icon: _icons[index],
                        label: _labels[index],
                        isSelected: _currentIndex == index,
                        animation: _animations[index],
                        badgeCount: index == 0 ? cartCount : 0,
                      ),
                    ),
                  ),
                );
              }),
            ),
          ),
        ),
      ),
    );
  }
}

class AnimatedNavItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final bool isSelected;
  final Animation<double> animation;
  final int badgeCount;

  const AnimatedNavItem({
    super.key,
    required this.icon,
    required this.label,
    required this.isSelected,
    required this.animation,
    this.badgeCount = 0,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: animation,
      builder: (context, child) {
        final scale = 1.0 + (animation.value * 0.15);
        final translateY = -8 * animation.value;

        return SizedBox(
          width: 70,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Transform.translate(
                offset: Offset(0, translateY),
                child: Transform.scale(
                  scale: scale,
                  child: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: isSelected
                        ? BoxDecoration(
                            gradient: AppGradients.primary,
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: AppColors.primaryBlue.withValues(alpha: 0.4),
                                blurRadius: 12,
                                offset: const Offset(0, 4),
                              ),
                            ],
                          )
                        : null,
                    child: Stack(
                      clipBehavior: Clip.none,
                      children: [
                        Icon(
                          icon,
                          color: isSelected ? Colors.white : AppColors.textMuted,
                          size: 24,
                        ),
                        if (badgeCount > 0)
                          Positioned(
                            right: -6,
                            top: -6,
                            child: Container(
                              padding: const EdgeInsets.all(4),
                              decoration: const BoxDecoration(
                                color: AppColors.error,
                                shape: BoxShape.circle,
                              ),
                              child: Text(
                                '$badgeCount',
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontSize: 9,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 4),
              Text(
                label,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                  color: isSelected ? AppColors.primaryBlue : AppColors.textMuted,
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}