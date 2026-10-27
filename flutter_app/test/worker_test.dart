import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:region_compositor/worker_client.dart';

void main() {
  test(
    'Dart starts Python worker, recovers from errors, and saves PNG',
    () async {
      final directory = await Directory.systemTemp.createTemp('region-bridge-');
      final worker = WorkerClient();
      try {
        final fixture = File('${directory.path}/한글 image.png');
        await fixture.writeAsBytes(
          base64Decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=',
          ),
        );
        final info = await worker.request({
          'command': 'inspect',
          'path': fixture.path,
        });
        expect(info['width'], 1);
        await expectLater(
          worker.request({'command': 'invalid'}),
          throwsStateError,
        );
        final output = '${directory.path}/결과.png';
        final response = await worker.request({
          'command': 'save',
          'base': fixture.path,
          'patch': fixture.path,
          'output': output,
          'rect': [0, 0, 1, 1],
        });
        expect(response['width'], 1);
        expect(await File(output).length(), greaterThan(0));
      } finally {
        worker.close();
        await directory.delete(recursive: true);
      }
    },
  );
}
