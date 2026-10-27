# Flutter Windows UI / Flutter 윈도우 UI

This branch adds a Flutter main app with an app-managed local Python worker.
The worker runs in a separate OS process, not inside the Dart VM. It is bundled
with the app for distribution: users do not need a Python installation, server,
or network connection. No model/AI feature is introduced by this migration.

Flutter가 메인 앱이며 기존 Python/Pillow 합성 코드는 앱이 관리하는 로컬
프로세스에서 실행됩니다. Dart VM에 CPython을 직접 임베딩하는 FFI 방식은
아닙니다. 배포 폴더에 Python 런타임을 포함하므로 별도 Python 설치나 서버가
필요하지 않습니다. 향후 AI/분석 작업도 worker 명령을 추가하는 형태로 확장할
수 있지만, 현재 AI 모델이나 분석 기능을 추가한 것은 아닙니다.

## Run from source

Requirements: Windows x64, Flutter 3.47.8 / Dart 3.13.7, Python 3.13,
Visual Studio C++ desktop workload and Windows SDK. Flutter plugins need
symlink permission (typically Windows Developer Mode or an elevated build shell).
No system setting is changed by this project. This session used a local
directory junction for the file-selector plugin instead of changing settings.

From the repository root:

```powershell
python -m venv .venv-flutter
.\.venv-flutter\Scripts\python.exe -m pip install -r requirements-flutter.txt pyinstaller==6.21.0
cd flutter_app
flutter pub get
cd ..
.\.venv-flutter\Scripts\python.exe scripts/collect_licenses.py
$env:REGION_COMPOSITOR_ROOT = (Get-Location).Path
$env:REGION_COMPOSITOR_PYTHON = (Resolve-Path .venv-flutter/Scripts/python.exe).Path
cd flutter_app
flutter run -d windows
```

Python's executable and repository root are passed as separate process arguments,
never interpolated into a shell command. For a packaged build the adjacent
`engine/region_worker.exe` takes precedence over development environment settings.

## Build a distributable

### Single installer EXE

`RegionCompositor-Setup-v0.2.0-flutter.2-x64.exe` is the recommended download.
It contains the complete Flutter/Python bundle, app-local Microsoft VC++ runtime
DLLs and notices. Run it once to install; ZIP extraction or a separate Python
installation is not required. Default location:
`%LOCALAPPDATA%/Programs/RegionCompositor`. It creates a Start menu shortcut,
offers a desktop shortcut, and supports removal through Windows Installed Apps.
Installation is per user. User image files and language preferences are retained.

To package a previously checked Release folder, use the official Inno Setup
6.7.3 compiler and the x64 CRT folder from your licensed Visual Studio installation:

```powershell
.\scripts\build_installer.ps1 -Iscc 'C:\tools\inno\ISCC.exe' `
  -CrtDirectory 'C:\path\to\VC\Redist\MSVC\VERSION\x64\Microsoft.VC145.CRT'
```

The script includes the compiler's original license and writes a SHA-256 checksum.
It does not download tools or change machine settings. The setup was validated
with a temporary installation: all 84 bundle files matched their source hashes,
the local runtime/notices were present, the installed Python worker processed an
image, the Flutter app launched, and uninstall completed. A fresh Windows VM
has not been tested. The installer is not code-signed.

References: [Inno Setup](https://jrsoftware.org/isinfo.php),
[Microsoft app-local runtime deployment](https://learn.microsoft.com/en-us/cpp/windows/determining-which-dlls-to-redistribute).

### Portable ZIP / release folder

```powershell
.\scripts\build_flutter.ps1
```

This creates a dedicated `.venv-flutter`, runs Python tests, collects licenses,
runs Flutter analysis/tests, builds Windows Release, freezes Python with
PyInstaller, and copies the worker and notices into the Flutter release folder.
The script fails on any failed check. Output:
`flutter_app/build/windows/x64/runner/Release/`.
Ship that **whole folder**, including `engine/`, `data/`, DLLs and license files.
Launching only the exe after copying it elsewhere will not work. The Microsoft
Visual C++ runtime may be required on a clean Windows installation. This build
is not code-signed and has no installer or auto-updater.

## Editing workflow

1. Open the base and patch images (PNG/JPEG/WebP/BMP/TIFF). Paths with spaces
   and Korean characters are supported. EXIF orientation is normalized.
2. Drag outside the selected rectangle to draw a new region; drag inside it
   to move; drag a corner to resize. Sliders also adjust X/Y/width/height.
3. Adjust opacity, feather and edge color matching. Switch Composite/Base/Patch
   views. Preview is debounced; stale responses cannot replace newer edits.
4. Save PNG writes a full-resolution composite, regardless of preview mode.
   Existing output replacement requires confirmation. Saving over either input
   is rejected. A temporary file in the output directory is atomically replaced.
5. Switch 한국어/English without losing image or edit state. Language is stored
   at `%APPDATA%/RegionCompositor/flutter_language.txt`. Legacy settings are separate.

기준/합성 이미지 열기 → 영역 그리기·이동·모서리 조절 → 합성 설정 → PNG 저장.
한영 전환은 편집 상태를 유지합니다. 입력 이미지 덮어쓰기는 허용하지 않습니다.
라이선스 버튼에서 앱 및 제3자 구성요소의 고지를 확인할 수 있습니다.

## Engine and protocol

The stable `region_compositor.py`, `compositor_app.py`, `ui_support.py` and
`versions/` are unchanged. `backend/engine.py` copies the original seven pure
Pillow methods verbatim from ff7de566, avoiding Tk imports in the worker.
Parity tests compare pixels against the preserved implementation. Selection
uses the same relative crop in both images, rather than stretching the whole
patch into the rectangle.

`python -u -m backend.worker` reads UTF-8 JSON lines on stdin and replies on
stdout with matching `id`, `ok`, and `result` or `error`. Commands: `inspect`,
`preview`, `save`. Only one preview is in flight; newer edits trigger another
after it completes. Previews are limited to 1600px on the longest side; saving
uses the original resolution. Input images above 40 million pixels are rejected.
There are no sockets, upload endpoints or telemetry. Images are reopened for
each operation, so input files should not be externally modified during editing.

Errors stay in the UI, with localized context and Python diagnostic details.
Worker termination fails pending requests; subsequent requests restart it.
A three-minute timeout kills a stuck worker. Closing the editor terminates it.
Future model tasks should define explicit commands and independently review
model licenses, resource use and cancellation needs.

## Scope and recovery

Flutter is an additional entry point. `python region_compositor.py` and the
original build script remain available. `v0.1.0` stays at ff7de566; no release
asset is replaced. The PR targets main but is left unmerged for review.
There is no zoom/pan, aspect lock, drag-and-drop file import, JPEG export or
pixel nudge shortcut in this initial Flutter UI. These legacy features remain
available in the Tk app. Windows x64 is the only configured Flutter target.

See [licensing review](THIRD_PARTY_NOTICES.md) and
[validation results](FLUTTER_VALIDATION.md).
