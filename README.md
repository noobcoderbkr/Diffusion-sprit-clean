# RegionCompositor

<img src="docs/images/region-compositor-wordmark.png" alt="RegionCompositor" width="360">

[한국어](README.ko.md)

A Flutter Windows desktop app for compositing selected regions of two images.
The app runs its bundled Python/Pillow engine locally. No Python installation,
server, AI model or API key is needed for the installed version.

## Download

[Download the Windows installer from the latest release](https://github.com/noobcoderbkr/Diffusion-sprit-clean/releases/latest).
Run the Setup EXE to install the app and its engine. A portable ZIP is also available.

## Features

- Open PNG, JPEG, WebP, BMP and TIFF images.
- Draw, move and resize the selection or adjust X/Y/width/height sliders.
- Preview opacity, feathering and edge color matching.
- Save a full-resolution PNG while preserving both input files.
- Switch Korean/English without losing edits; language preference persists.
- All image processing stays on the computer.

## Develop and build

Requirements: Windows x64, Flutter 3.47.8, Python 3.13 and Visual Studio C++ tools.

```powershell
.\run.bat
.\build.ps1
```

The launcher prepares a project-local Python environment and starts Flutter.
The build script runs tests and bundles Python with the Windows app.
See [build/install instructions](docs/FLUTTER_WINDOWS.md),
[validation](docs/FLUTTER_VALIDATION.md) and [branding](docs/BRANDING.md).

## Layout

- `flutter_app/`: main application and Windows runner.
- `backend/`: headless Python/Pillow worker and compositing engine.
- `tests/`: engine baselines and worker integration tests.
- `scripts/`, `packaging/`: run, build and single-EXE installer packaging.

## License

Project-author code is under the [non-commercial, no-redistribution license](LICENSE).
[Third-party licenses](docs/THIRD_PARTY_NOTICES.md) remain independent.
