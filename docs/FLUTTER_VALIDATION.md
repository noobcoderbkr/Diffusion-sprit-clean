# Flutter Windows validation — 2026-10-27

Environment: Windows x64, Flutter 3.47.8, Dart 3.13.7, Python 3.13.14,
Pillow 12.3.0, PyInstaller 6.21.0, Visual Studio C++ Build Tools 2026.

| Check | Result |
| --- | --- |
| Python unittest discover -s tests -v | 22 passed, including existing Tk/UI/legacy tests |
| New engine vs v0.1.0 | Pixel equality for 27 region/blend/view combinations |
| JSON worker | Unicode paths, errors and recovery, full-resolution save, source preservation passed |
| flutter analyze --no-pub | No issues |
| flutter test --no-pub | 4 passed |
| Flutter editor flow with actual Python subprocess | Open base/patch, preview, move and draw selection, switch language preserving selection, save PNG, cancel open passed |
| Windows Release build | Successful, x64 executable and plugin/engine DLLs generated |
| PyInstaller worker | Built in isolated project environment without Tk or NumPy |
| Frozen-worker smoke test | Passed from unrelated working directory, Korean paths, preview/save pixel equality |
| Third-party notices | 46 full installed license files collected; bundled asset and external text included |
| Stable-code preservation | Original Python entry points, engine/UI modules, requirements and legacy build script have no diff from v0.1.0 |

The real Windows app launched and exposed the expected Korean editor controls
through accessibility. The computer-use helper could not activate the captured
window (failed to activate captured window), so native-dialog mouse interaction
and visual layout were not manually certified. The Flutter editor integration
test substitutes only the native file dialog result and uses the actual Python
process for opening, previewing and saving. A clean machine without Python and
with a fresh VC++ runtime installation has not been tested.

An actual Dart-to-Python test caught Windows stdin code-page corruption of Korean
paths. Both protocol endpoints now explicitly use UTF-8, and source/frozen
worker tests exercise non-ASCII paths.

Reproduce full build/checks with scripts/build_flutter.ps1. GitHub Actions
configuration is included; remote CI results must be evaluated separately from
these local results. The PR is left unmerged; main and v0.1.0 are not updated.
