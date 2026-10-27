import 'dart:ui';

Rect boundedRegion(double x, double y, double w, double h) {
  w = w.clamp(.01, 1.0);
  h = h.clamp(.01, 1.0);
  return Rect.fromLTWH(x.clamp(0.0, 1.0 - w), y.clamp(0.0, 1.0 - h), w, h);
}
