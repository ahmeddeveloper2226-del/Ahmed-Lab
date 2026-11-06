import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'main_shell.dart' show AnimatedNavItem;
import '../../providers/driver_provider.dart';

class DriverMainShell extends ConsumerStatefulWidget {
  final StatefulNavigationShell navigationShell;
  const DriverMainShell({super.key, required this.navigationShell});

  @override
  ConsumerState<DriverMainShell> createState() => _DriverMainShellState();
}

class _DriverMainShellState extends ConsumerState<DriverMainShell>
    with TickerProviderStateMixin {
  late int _currentIndex;
  late List<AnimationController> _controllers;
  late List<Animation<double>> _animations;

  final _labels = ['الرئيسية', 'طلباتي', 'حسابي'];
  final _icons = [
    Icons.map_rounded,
    Icons.local_shipping_rounded,
    Icons.person_rounded,
  ];

  @override
  void initState() {
    super.initState();
    _currentIndex = widget.navigationShell.currentIndex;
    _controllers = List.generate(
      3,
      (i) => AnimationController(vsync: this, duration: const Duration(milliseconds: 400)),
    );
    _animations = _controllers
        .map((c) => Tween<double>(begin: 0, end: 1).animate(
              CurvedAnimation(parent: c, curve: Curves.elasticOut),
            ))
        .toList();
    _controllers[_currentIndex].forward();
  }

  @override
  void didUpdateWidget(covariant DriverMainShell oldWidget) {
    super.didUpdateWidget(oldWidget);
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
    final activeOrdersAsync = ref.watch(driverActiveOrdersProvider);
    final activeCount = activeOrdersAsync.maybeWhen(data: (orders) => orders.length, orElse: () => 0);

    return Scaffold(
      body: widget.navigationShell,
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
              children: List.generate(3, (index) {
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
                        badgeCount: index == 1 ? activeCount : 0,
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