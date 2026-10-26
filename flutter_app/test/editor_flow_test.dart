import 'dart:convert';
import 'dart:io';
import 'package:file_selector_platform_interface/file_selector_platform_interface.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:region_compositor/main.dart';

class Dialogs extends FileSelectorPlatform {
  String? input;
  String? output;
  @override
  Future<XFile?> openFile({
    List<XTypeGroup>? acceptedTypeGroups,
    String? initialDirectory,
    String? confirmButtonText,
  }) async => input == null ? null : XFile(input!);
  @override
  Future<FileSaveLocation?> getSaveLocation({
    List<XTypeGroup>? acceptedTypeGroups,
    SaveDialogOptions options = const SaveDialogOptions(),
  }) async => output == null ? null : FileSaveLocation(output!);
}

void main() {
  testWidgets(
    'Open, move/resize region, preview, switch language and save via real Python',
    (tester) async {
      final original = FileSelectorPlatform.instance;
      final dialogs = Dialogs();
      FileSelectorPlatform.instance = dialogs;
      late Directory directory;
      await tester.runAsync(() async {
        directory = await Directory.systemTemp.createTemp('region-editor-');
        final fixture = File('${directory.path}/한글 image.png');
        await fixture.writeAsBytes(
          base64Decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=',
          ),
        );
        dialogs.input = fixture.path;
        dialogs.output = '${directory.path}/result.png';
      });
      Future<void> finishWork() async {
        for (var i = 0; i < 200; i++) {
          await tester.runAsync(
            () => Future<void>.delayed(const Duration(milliseconds: 25)),
          );
          await tester.pump(const Duration(milliseconds: 200));
          if (find.byType(LinearProgressIndicator).evaluate().isEmpty) return;
        }
        fail('Worker did not finish');
      }

      try {
        await tester.binding.setSurfaceSize(const Size(1240, 840));
        await tester.pumpWidget(
          const MaterialApp(
            home: Editor(language: 'en', onLanguage: ignore),
          ),
        );
        await tester.tap(find.text('Open base image'));
        await tester.pump();
        await finishWork();
        await tester.tap(find.text('Open patch image'));
        await tester.pump();
        await finishWork();
        expect(find.byType(Image), findsOneWidget);
        expect(find.textContaining('Operation failed'), findsNothing);
        final area = tester.getRect(find.byType(Image));
        await tester.dragFrom(area.center, const Offset(30, 20));
        await tester.pump(const Duration(milliseconds: 200));
        await finishWork();
        // New rectangle from empty space.
        await tester.dragFrom(
          area.topLeft + const Offset(10, 10),
          const Offset(100, 80),
        );
        await tester.pump(const Duration(milliseconds: 200));
        await finishWork();
        final sliderBefore = tester
            .widget<Slider>(find.byType(Slider).first)
            .value;
        await tester.pumpWidget(
          const MaterialApp(
            home: Editor(language: 'ko', onLanguage: ignore),
          ),
        );
        expect(
          tester.widget<Slider>(find.byType(Slider).first).value,
          sliderBefore,
        );
        await tester.tap(find.text('PNG 저장'));
        await tester.pump();
        await finishWork();
        expect(find.textContaining('저장 완료'), findsOneWidget);
        await tester.runAsync(
          () async => expect(await File(dialogs.output!).exists(), isTrue),
        );
        // Canceling an image dialog preserves the current image and edit.
        dialogs.input = null;
        await tester.tap(find.text('기준 이미지 열기'));
        await tester.pumpAndSettle();
        expect(find.byType(Image), findsOneWidget);
      } finally {
        await tester.pumpWidget(const SizedBox.shrink());
        await tester.binding.setSurfaceSize(null);
        FileSelectorPlatform.instance = original;
        await tester.runAsync(() => directory.delete(recursive: true));
      }
    },
  );
}

void ignore(String _) {}
