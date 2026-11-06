import 'package:flutter/material.dart';

class AnimationDurations {
  AnimationDurations._();

  static const Duration instant = Duration(milliseconds: 100);
  static const Duration fast = Duration(milliseconds: 200);
  static const Duration normal = Duration(milliseconds: 300);
  static const Duration slow = Duration(milliseconds: 500);
  static const Duration verySlow = Duration(milliseconds: 800);

  static const Duration pageTransition = Duration(milliseconds: 400);
  static const Duration staggerDelay = Duration(milliseconds: 60);
  static const Duration shimmerCycle = Duration(milliseconds: 1500);
  static const Duration bounce = Duration(milliseconds: 600);
  static const Duration pulse = Duration(milliseconds: 1200);
}

class AnimationCurves {
  AnimationCurves._();

  static const Curve defaultCurve = Curves.easeInOutCubic;
  static const Curve bounce = Curves.elasticOut;
  static const Curve decelerate = Curves.decelerate;
  static const Curve accelerate = Curves.easeInCubic;
  static const Curve spring = Curves.fastOutSlowIn;
  static const Curve overshoot = Curves.easeOutBack;
}

class AnimationOffsets {
  AnimationOffsets._();

  static const Offset fromBottom = Offset(0, 0.3);
  static const Offset fromTop = Offset(0, -0.3);
  static const Offset fromLeft = Offset(-0.3, 0);
  static const Offset fromRight = Offset(0.3, 0);
  static const Offset scaleDown = Offset(0.8, 0.8);
  static const Offset none = Offset.zero;
}
