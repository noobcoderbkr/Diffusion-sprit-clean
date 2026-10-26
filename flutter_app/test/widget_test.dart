import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:region_compositor/main.dart';
import 'package:region_compositor/region.dart';

void main() {
  test('Selection stays inside image at every edge', () {
    expect(boundedRegion(-1, 2, .5, .5), const Rect.fromLTWH(0, .5, .5, .5));
    expect(boundedRegion(.9, .9, 2, 2), const Rect.fromLTWH(0, 0, 1, 1));
    expect(boundedRegion(0, 0, 0, 0).size, const Size(.01, .01));
  });
  testWidgets('Language switches controls without replacing editor', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1240, 840));
    await tester.pumpWidget(
      const MaterialApp(
        home: Editor(language: 'ko', onLanguage: ignore),
      ),
    );
    expect(find.text('기준 이미지 열기'), findsOneWidget);
    expect(
      tester
          .widget<FilledButton>(find.widgetWithText(FilledButton, 'PNG 저장'))
          .onPressed,
      isNull,
    );
    await tester.pumpWidget(
      const MaterialApp(
        home: Editor(language: 'en', onLanguage: ignore),
      ),
    );
    expect(find.text('Open base image'), findsOneWidget);
    expect(find.text('Save PNG'), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.binding.setSurfaceSize(null);
  });
}

void ignore(String _) {}
