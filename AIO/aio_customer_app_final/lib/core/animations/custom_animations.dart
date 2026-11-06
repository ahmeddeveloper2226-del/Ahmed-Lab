import 'package:flutter/material.dart';
import 'animation_constants.dart';

// Fade + Slide entrance animation
class FadeSlideIn extends StatelessWidget {
  final Widget child;
  final Offset offset;
  final Duration delay;
  final Duration duration;
  final Curve curve;

  const FadeSlideIn({
    super.key,
    required this.child,
    this.offset = const Offset(0, 0.2),
    this.delay = Duration.zero,
    this.duration = AnimationDurations.normal,
    this.curve = AnimationCurves.defaultCurve,
  });

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0.0, end: 1.0),
      duration: duration,
      curve: curve,
      builder: (context, value, child) {
        return Opacity(
          opacity: value,
          child: Transform.translate(
            offset: Offset(offset.dx * (1 - value) * 100, offset.dy * (1 - value) * 100),
            child: child,
          ),
        );
      },
      child: child,
    );
  }
}

// Scale bounce animation
class ScaleBounce extends StatefulWidget {
  final Widget child;
  final Duration delay;
  final VoidCallback? onTap;

  const ScaleBounce({
    super.key,
    required this.child,
    this.delay = Duration.zero,
    this.onTap,
  });

  @override
  State<ScaleBounce> createState() => _ScaleBounceState();
}

class _ScaleBounceState extends State<ScaleBounce>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: AnimationDurations.bounce,
    );
    _animation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: AnimationCurves.bounce),
    );
    Future.delayed(widget.delay, () {
      if (mounted) _controller.forward();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        _controller.reset();
        _controller.forward();
        widget.onTap?.call();
      },
      child: AnimatedBuilder(
        animation: _animation,
        builder: (context, child) {
          return Transform.scale(
            scale: _animation.value,
            child: child,
          );
        },
        child: widget.child,
      ),
    );
  }
}

// Pulse animation for badges/notifications
class PulseAnimation extends StatefulWidget {
  final Widget child;
  final Duration duration;

  const PulseAnimation({
    super.key,
    required this.child,
    this.duration = AnimationDurations.pulse,
  });

  @override
  State<PulseAnimation> createState() => _PulseAnimationState();
}

class _PulseAnimationState extends State<PulseAnimation>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: widget.duration,
    );
    _controller.repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Transform.scale(
          scale: 1.0 + (_controller.value * 0.15),
          child: child,
        );
      },
      child: widget.child,
    );
  }
}

// Shimmer effect
class ShimmerEffect extends StatefulWidget {
  final Widget child;
  final bool isLoading;

  const ShimmerEffect({
    super.key,
    required this.child,
    this.isLoading = true,
  });

  @override
  State<ShimmerEffect> createState() => _ShimmerEffectState();
}

class _ShimmerEffectState extends State<ShimmerEffect>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: AnimationDurations.shimmerCycle,
    );
    if (widget.isLoading) _controller.repeat();
  }

  @override
  void didUpdateWidget(covariant ShimmerEffect oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isLoading) {
      _controller.repeat();
    } else {
      _controller.stop();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isLoading) return widget.child;

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return ShaderMask(
          shaderCallback: (bounds) {
            return LinearGradient(
              colors: [
                Colors.grey.shade300,
                Colors.grey.shade100,
                Colors.grey.shade300,
              ],
              stops: const [0.0, 0.5, 1.0],
              begin: Alignment(-1.0 + _controller.value * 2, 0),
              end: Alignment(1.0 + _controller.value * 2, 0),
            ).createShader(bounds);
          },
          child: widget.child,
        );
      },
    );
  }
}

// Staggered list animation wrapper
class StaggeredList extends StatelessWidget {
  final List<Widget> children;
  final Duration delay;
  final Axis direction;
  final ScrollPhysics? physics;
  final EdgeInsets padding;

  const StaggeredList({
    super.key,
    required this.children,
    this.delay = AnimationDurations.staggerDelay,
    this.direction = Axis.vertical,
    this.physics,
    this.padding = EdgeInsets.zero,
  });

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: physics,
      padding: padding,
      shrinkWrap: true,
      children: List.generate(children.length, (index) {
        return FadeSlideIn(
          delay: delay * index,
          duration: AnimationDurations.normal,
          child: children[index],
        );
      }),
    );
  }
}

// Animated gradient background
class AnimatedGradientBackground extends StatefulWidget {
  final Widget child;
  final List<Color> colors;

  const AnimatedGradientBackground({
    super.key,
    required this.child,
    required this.colors,
  });

  @override
  State<AnimatedGradientBackground> createState() => _AnimatedGradientBackgroundState();
}

class _AnimatedGradientBackgroundState extends State<AnimatedGradientBackground>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 5),
    );
    _controller.repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: widget.colors,
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              stops: [
                0.0,
                0.5 + (_controller.value * 0.2),
                1.0,
              ],
            ),
          ),
          child: child,
        );
      },
      child: widget.child,
    );
  }
}

// Hero-like page transition
class CreativePageRoute<T> extends PageRouteBuilder<T> {
  final Widget child;

  CreativePageRoute({required this.child})
      : super(
          pageBuilder: (context, animation, secondaryAnimation) => child,
          transitionsBuilder: (context, animation, secondaryAnimation, child) {
            const begin = Offset(1.0, 0.0);
            const end = Offset.zero;
            const curve = Curves.easeInOutCubic;

            var tween = Tween(begin: begin, end: end).chain(
              CurveTween(curve: curve),
            );

            var fadeTween = Tween<double>(begin: 0.0, end: 1.0);

            return FadeTransition(
              opacity: animation.drive(fadeTween),
              child: SlideTransition(
                position: animation.drive(tween),
                child: child,
              ),
            );
          },
          transitionDuration: AnimationDurations.pageTransition,
        );
}
