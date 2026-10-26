import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'region.dart';
import 'worker_client.dart';

void main() {
  LicenseRegistry.addLicense(() async* {
    yield LicenseEntryWithLineBreaks([
      'RegionCompositor bundled components',
    ], await rootBundle.loadString('assets/THIRD_PARTY_LICENSES.txt'));
  });
  runApp(const CompositorApp());
}

class CompositorApp extends StatefulWidget {
  const CompositorApp({super.key});
  @override
  State<CompositorApp> createState() => _CompositorAppState();
}

class _CompositorAppState extends State<CompositorApp> {
  String language = 'ko';
  File get preference => File(
    '${Platform.environment['APPDATA'] ?? Directory.systemTemp.path}/RegionCompositor/flutter_language.txt',
  );
  @override
  void initState() {
    super.initState();
    preference
        .readAsString()
        .then((value) {
          if (mounted && ['ko', 'en'].contains(value.trim())) {
            setState(() => language = value.trim());
          }
        })
        .catchError((Object _) {});
  }

  void changeLanguage(String value) {
    setState(() => language = value);
    () async {
      try {
        await preference.parent.create(recursive: true);
        await preference.writeAsString(value);
      } catch (_) {
        /* Language remains usable when preferences are read-only. */
      }
    }();
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    title: 'RegionCompositor',
    locale: Locale(language),
    supportedLocales: const [Locale('ko'), Locale('en')],
    localizationsDelegates: GlobalMaterialLocalizations.delegates,
    theme: ThemeData(
      useMaterial3: true,
      colorSchemeSeed: const Color(0xff3561dd),
      scaffoldBackgroundColor: const Color(0xfff3f5f9),
    ),
    home: Editor(language: language, onLanguage: changeLanguage),
  );
}

class Editor extends StatefulWidget {
  const Editor({super.key, required this.language, required this.onLanguage});
  final String language;
  final ValueChanged<String> onLanguage;
  @override
  State<Editor> createState() => _EditorState();
}

class _EditorState extends State<Editor> {
  final worker = WorkerClient();
  String? base, patch;
  int width = 1, height = 1;
  Uint8List? preview;
  Rect region = const Rect.fromLTWH(.25, .25, .5, .5);
  double opacity = 100, feather = 24;
  bool edgeMatch = true, guide = true, loading = false, rendering = false;
  bool dirty = false, saving = false;
  int revision = 0;
  String mode = 'composite';
  String? error;
  String? savedPath;
  Timer? debounce;
  Offset? dragStart;
  Rect? dragRegion;
  String dragMode = 'draw';
  String tr(String ko, String en) => widget.language == 'ko' ? ko : en;
  bool get ready => base != null && patch != null;
  bool get busy => loading || saving;

  @override
  void dispose() {
    debounce?.cancel();
    worker.close();
    super.dispose();
  }

  Future<void> open(bool isBase) async {
    try {
      final file = await openFile(
        acceptedTypeGroups: [
          const XTypeGroup(
            label: 'Images',
            extensions: ['png', 'jpg', 'jpeg', 'webp', 'bmp', 'tif', 'tiff'],
          ),
        ],
      );
      if (file == null || !mounted) return;
      setState(() {
        loading = true;
        error = null;
        savedPath = null;
        revision++;
      });
      final data = await worker.request({
        'command': 'inspect',
        'path': file.path,
      });
      if (!mounted) return;
      setState(() {
        if (isBase) {
          base = file.path;
          width = data['width'] as int;
          height = data['height'] as int;
          preview = base64Decode(data['png'] as String);
        } else {
          patch = file.path;
        }
      });
      changed();
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Map<String, dynamic> parameters(String command) => {
    'command': command,
    'base': base,
    'patch': patch,
    'rect': [region.left, region.top, region.width, region.height],
    'opacity': opacity,
    'feather': feather,
    'edgeMatch': edgeMatch,
    'mode': mode,
  };

  void changed() {
    revision++;
    savedPath = null;
    dirty = true;
    debounce?.cancel();
    debounce = Timer(const Duration(milliseconds: 160), render);
  }

  Future<void> render() async {
    if (!ready || rendering || busy || !mounted) return;
    final requestedRevision = revision;
    setState(() {
      rendering = true;
      dirty = false;
      error = null;
    });
    try {
      final data = await worker.request(parameters('preview'));
      if (mounted && requestedRevision == revision) {
        setState(() => preview = base64Decode(data['png'] as String));
      }
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) {
        setState(() => rendering = false);
        if (dirty) unawaited(render());
      }
    }
  }

  Future<void> save() async {
    try {
      final target = await getSaveLocation(
        suggestedName: 'composite.png',
        acceptedTypeGroups: [
          const XTypeGroup(label: 'PNG', extensions: ['png']),
        ],
      );
      if (target == null || !mounted) return;
      var path = target.path;
      if (!path.toLowerCase().endsWith('.png')) path += '.png';
      if (File(path).existsSync()) {
        final confirmed = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: Text(tr('기존 파일을 대체할까요?', 'Replace existing file?')),
            content: Text(path),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: Text(tr('취소', 'Cancel')),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: Text(tr('대체', 'Replace')),
              ),
            ],
          ),
        );
        if (confirmed != true || !mounted) return;
      }
      setState(() {
        saving = true;
        error = null;
      });
      await worker.request({...parameters('save'), 'output': path});
      if (mounted) setState(() => savedPath = path);
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) {
        setState(() => saving = false);
        if (dirty) unawaited(render());
      }
    }
  }

  Widget slider(
    String label,
    double value,
    double max,
    ValueChanged<double> change, {
    double min = 0,
  }) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Row(
        children: [
          Expanded(child: Text(label)),
          Text(value.toStringAsFixed(1)),
        ],
      ),
      Slider(
        value: value.clamp(min, max),
        min: min,
        max: max,
        onChanged: busy
            ? null
            : (v) {
                setState(() => change(v));
                changed();
              },
      ),
    ],
  );

  void updateRegion(double x, double y, double w, double h) {
    region = boundedRegion(x, y, w, h);
  }

  Widget inspector() => SizedBox(
    width: 300,
    child: ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text(
          tr('이미지', 'Images'),
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 12),
        FilledButton.tonalIcon(
          onPressed: busy ? null : () => open(true),
          icon: const Icon(Icons.image_outlined),
          label: Text(tr('기준 이미지 열기', 'Open base image')),
        ),
        Text(
          base?.split(Platform.pathSeparator).last ??
              tr('선택된 이미지 없음', 'No image selected'),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 12),
        FilledButton.tonalIcon(
          onPressed: busy ? null : () => open(false),
          icon: const Icon(Icons.layers_outlined),
          label: Text(tr('합성 이미지 열기', 'Open patch image')),
        ),
        Text(
          patch?.split(Platform.pathSeparator).last ??
              tr('선택된 이미지 없음', 'No image selected'),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
        const Divider(height: 36),
        Row(
          children: [
            Expanded(
              child: Text(
                tr('선택 영역', 'Selection'),
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
            TextButton(
              onPressed: busy
                  ? null
                  : () {
                      setState(
                        () => region = const Rect.fromLTWH(.25, .25, .5, .5),
                      );
                      changed();
                    },
              child: Text(tr('초기화', 'Reset')),
            ),
          ],
        ),
        slider(
          tr('가로 위치 (%)', 'X (%)'),
          region.left * 100,
          100,
          (v) => updateRegion(v / 100, region.top, region.width, region.height),
        ),
        slider(
          tr('세로 위치 (%)', 'Y (%)'),
          region.top * 100,
          100,
          (v) =>
              updateRegion(region.left, v / 100, region.width, region.height),
        ),
        slider(
          tr('너비 (%)', 'Width (%)'),
          region.width * 100,
          100,
          (v) => updateRegion(region.left, region.top, v / 100, region.height),
          min: 1,
        ),
        slider(
          tr('높이 (%)', 'Height (%)'),
          region.height * 100,
          100,
          (v) => updateRegion(region.left, region.top, region.width, v / 100),
          min: 1,
        ),
        const Divider(height: 36),
        Text(
          tr('합성 설정', 'Blending'),
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 12),
        slider(tr('불투명도 (%)', 'Opacity (%)'), opacity, 100, (v) => opacity = v),
        slider(
          tr('경계 부드럽게 (px)', 'Feather (px)'),
          feather,
          200,
          (v) => feather = v,
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(tr('경계 색상 맞춤', 'Match edge colors')),
          value: edgeMatch,
          onChanged: busy
              ? null
              : (v) {
                  setState(() => edgeMatch = v);
                  changed();
                },
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(tr('영역 가이드', 'Selection guide')),
          value: guide,
          onChanged: (v) => setState(() => guide = v),
        ),
        const SizedBox(height: 12),
        Text(
          tr(
            '빈 곳 드래그: 새 영역\n영역 안 드래그: 이동\n모서리 드래그: 크기 조절',
            'Drag empty space to select\nDrag inside to move\nDrag corners to resize',
          ),
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    ),
  );

  Widget canvas() => LayoutBuilder(
    builder: (context, bounds) {
      if (preview == null) {
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.photo_library_outlined,
                size: 64,
                color: Colors.blueGrey,
              ),
              const SizedBox(height: 16),
              Text(
                tr(
                  '기준 이미지와 합성 이미지를 열어 시작하세요.',
                  'Open a base image and a patch to begin.',
                ),
              ),
            ],
          ),
        );
      }
      final fitted = applyBoxFit(
        BoxFit.contain,
        Size(width.toDouble(), height.toDouble()),
        Size(bounds.maxWidth - 32, bounds.maxHeight - 32),
      ).destination;
      Offset point(Offset local) => Offset(
        (local.dx / fitted.width).clamp(0.0, 1.0),
        (local.dy / fitted.height).clamp(0.0, 1.0),
      );
      return Center(
        child: SizedBox(
          width: fitted.width,
          height: fitted.height,
          child: GestureDetector(
            onPanStart: busy || !guide
                ? null
                : (details) {
                    dragStart = point(details.localPosition);
                    dragRegion = region;
                    final p = dragStart!;
                    const corners = ['nw', 'ne', 'sw', 'se'];
                    final points = [
                      region.topLeft,
                      region.topRight,
                      region.bottomLeft,
                      region.bottomRight,
                    ];
                    dragMode = region.contains(p) ? 'move' : 'draw';
                    for (var i = 0; i < points.length; i++) {
                      if ((p.dx - points[i].dx).abs() * fitted.width < 14 &&
                          (p.dy - points[i].dy).abs() * fitted.height < 14) {
                        dragMode = corners[i];
                        break;
                      }
                    }
                  },
            onPanUpdate: busy || !guide
                ? null
                : (details) {
                    if (dragStart == null || dragRegion == null) return;
                    final p = point(details.localPosition),
                        start = dragStart!,
                        old = dragRegion!;
                    setState(() {
                      if (dragMode == 'move') {
                        updateRegion(
                          old.left + p.dx - start.dx,
                          old.top + p.dy - start.dy,
                          old.width,
                          old.height,
                        );
                      } else {
                        final anchor = switch (dragMode) {
                          'nw' => old.bottomRight,
                          'ne' => old.bottomLeft,
                          'sw' => old.topRight,
                          'se' => old.topLeft,
                          _ => start,
                        };
                        final rect = Rect.fromPoints(anchor, p);
                        updateRegion(
                          rect.left,
                          rect.top,
                          rect.width,
                          rect.height,
                        );
                      }
                    });
                    changed();
                  },
            onPanEnd: (_) {
              dragStart = null;
              dragRegion = null;
            },
            child: Stack(
              fit: StackFit.expand,
              children: [
                CustomPaint(painter: CheckerPainter()),
                Image.memory(preview!, fit: BoxFit.fill, gaplessPlayback: true),
                if (guide)
                  IgnorePointer(
                    child: CustomPaint(painter: RegionPainter(region)),
                  ),
              ],
            ),
          ),
        ),
      );
    },
  );

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('RegionCompositor'),
      actions: [
        DropdownButton<String>(
          value: widget.language,
          underline: const SizedBox.shrink(),
          items: const [
            DropdownMenuItem(value: 'ko', child: Text('한국어')),
            DropdownMenuItem(value: 'en', child: Text('English')),
          ],
          onChanged: (v) {
            if (v != null) widget.onLanguage(v);
          },
        ),
        IconButton(
          tooltip: tr('라이선스', 'Licenses'),
          icon: const Icon(Icons.info_outline),
          onPressed: () => showLicensePage(
            context: context,
            applicationName: 'RegionCompositor',
            applicationLegalese:
                'Copyright © 2026 noobcoderbkr.\n${tr('사용자 코드: 비상업적 사용만 허용, 재배포 금지. 제3자 구성요소는 각 라이선스 적용.', 'Application code: non-commercial use only, no redistribution. Third-party components retain their own licenses.')}',
          ),
        ),
        const SizedBox(width: 12),
        FilledButton.icon(
          onPressed: ready && !busy ? save : null,
          icon: const Icon(Icons.save_alt),
          label: Text(tr('PNG 저장', 'Save PNG')),
        ),
        const SizedBox(width: 20),
      ],
    ),
    body: Column(
      children: [
        if (busy || rendering) const LinearProgressIndicator(minHeight: 2),
        Expanded(
          child: Row(
            children: [
              inspector(),
              const VerticalDivider(width: 1),
              Expanded(
                child: Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(12),
                      child: Wrap(
                        spacing: 8,
                        children: [
                          for (final item in [
                            ('composite', tr('합성', 'Composite')),
                            ('base', tr('기준', 'Base')),
                            ('patch', tr('패치', 'Patch')),
                          ])
                            ChoiceChip(
                              label: Text(item.$2),
                              selected: mode == item.$1,
                              onSelected: busy
                                  ? null
                                  : (_) {
                                      setState(() => mode = item.$1);
                                      changed();
                                    },
                            ),
                        ],
                      ),
                    ),
                    Expanded(child: canvas()),
                    Padding(
                      padding: const EdgeInsets.all(12),
                      child: Text(
                        base == null
                            ? tr(
                                '로컬 이미지 처리 · 외부 업로드 없음',
                                'Local processing · No uploads',
                              )
                            : '$width × $height px',
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        if (error != null)
          Container(
            width: double.infinity,
            color: Theme.of(context).colorScheme.errorContainer,
            padding: const EdgeInsets.all(12),
            child: SelectableText(
              '${tr('작업 실패. Python 실행 환경과 이미지 파일을 확인하세요.', 'Operation failed. Check the Python runtime and image files.')}\n$error',
            ),
          ),
        if (savedPath != null)
          Padding(
            padding: const EdgeInsets.all(8),
            child: SelectableText('${tr('저장 완료', 'Saved')}: $savedPath'),
          ),
      ],
    ),
  );
}

class RegionPainter extends CustomPainter {
  RegionPainter(this.region);
  final Rect region;
  @override
  void paint(Canvas canvas, Size size) {
    final rect = Rect.fromLTWH(
      region.left * size.width,
      region.top * size.height,
      region.width * size.width,
      region.height * size.height,
    );
    canvas.drawRect(rect, Paint()..color = const Color(0x223561dd));
    canvas.drawRect(
      rect,
      Paint()
        ..color = Colors.white
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3,
    );
    canvas.drawRect(
      rect,
      Paint()
        ..color = const Color(0xff3561dd)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5,
    );
    for (final p in [
      rect.topLeft,
      rect.topRight,
      rect.bottomLeft,
      rect.bottomRight,
    ]) {
      canvas.drawCircle(p, 5, Paint()..color = Colors.white);
      canvas.drawCircle(
        p,
        5,
        Paint()
          ..color = const Color(0xff3561dd)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2,
      );
    }
  }

  @override
  bool shouldRepaint(RegionPainter old) => old.region != region;
}

class CheckerPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(Offset.zero & size, Paint()..color = Colors.white);
    final paint = Paint()..color = const Color(0xffe4e7ed);
    for (double y = 0; y < size.height; y += 16) {
      for (double x = 0; x < size.width; x += 16) {
        if (((x ~/ 16) + (y ~/ 16)).isEven) {
          canvas.drawRect(
            Rect.fromLTWH(x, y, 16, 16).intersect(Offset.zero & size),
            paint,
          );
        }
      }
    }
  }

  @override
  bool shouldRepaint(CheckerPainter old) => false;
}
