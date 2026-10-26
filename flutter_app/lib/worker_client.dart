import 'dart:async';
import 'dart:convert';
import 'dart:io';

class WorkerClient {
  Process? _process;
  Future<void>? _starting;
  bool _closed = false;
  int _id = 0;
  final _pending = <int, Completer<Map<String, dynamic>>>{};

  Future<void> _start() async {
    if (_closed) throw StateError('Worker closed');
    if (_process != null) return;
    final packaged = File(
      '${File(Platform.resolvedExecutable).parent.path}/engine/region_worker.exe',
    );
    final root =
        Platform.environment['REGION_COMPOSITOR_ROOT'] ??
        Directory.current.parent.path;
    final process = await Process.start(
      packaged.existsSync()
          ? packaged.path
          : (Platform.environment['REGION_COMPOSITOR_PYTHON'] ?? 'python'),
      packaged.existsSync() ? [] : ['-u', '-m', 'backend.worker'],
      workingDirectory: packaged.existsSync() ? packaged.parent.path : root,
      runInShell: false,
    );
    if (_closed) {
      process.kill();
      throw StateError('Worker closed');
    }
    _process = process;
    process.stdin.encoding = utf8;
    // Drain stderr without exposing users' paths in logs.
    process.stderr.listen((_) {});
    process.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen((line) {
          try {
            final response = jsonDecode(line) as Map<String, dynamic>;
            final completer = _pending.remove(response['id']);
            if (completer == null) return;
            if (response['ok'] == true) {
              completer.complete(
                Map<String, dynamic>.from(response['result'] as Map),
              );
            } else {
              completer.completeError(StateError(response['error'] as String));
            }
          } catch (error) {
            _fail(error);
          }
        }, onError: _fail);
    unawaited(
      process.exitCode.then((code) {
        if (identical(_process, process)) {
          _process = null;
          _starting = null;
          _fail(StateError('Image worker exited ($code)'));
        }
      }),
    );
  }

  void _fail(Object error) {
    for (final request in _pending.values) {
      request.completeError(error);
    }
    _pending.clear();
  }

  Future<Map<String, dynamic>> request(Map<String, dynamic> data) async {
    try {
      await (_starting ??= _start());
    } catch (_) {
      _starting = null;
      rethrow;
    }
    final id = ++_id;
    final completer = Completer<Map<String, dynamic>>();
    _pending[id] = completer;
    try {
      _process!.stdin.writeln(jsonEncode({...data, 'id': id}));
      return await completer.future.timeout(const Duration(minutes: 3));
    } on TimeoutException {
      // A stuck native operation must not block all subsequent requests.
      _process?.kill();
      rethrow;
    } finally {
      _pending.remove(id);
    }
  }

  void close() {
    _closed = true;
    _process?.kill();
    _fail(StateError('Worker closed'));
  }
}
