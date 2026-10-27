# Flutter validation — 0.2.1

Flutter is the only desktop UI. The Python backend runs without Tk imports.

- Python backend: 3 tests pass, including 27 original-engine pixel baselines,
  protocol recovery, Unicode paths, source preservation and full-resolution save.
- Flutter: 4 tests cover bounded selections, language switching, a real Python
  subprocess and the editor open/drag/preview/save flow. Native dialog results
  are substituted in the editor test.
- Full build runs Flutter analysis, Flutter tests, Windows Release compilation,
  isolated PyInstaller bundling and the frozen worker smoke test.
- The installer includes the app, Python engine, app-local Microsoft VC++ runtime,
  supplied logo and third-party license notices.

Environment: Windows x64, Flutter 3.47.8, Dart 3.13.7, Python 3.13.14,
Pillow 12.3.0, PyInstaller 6.21.0, Inno Setup 6.7.3.

The 0.2.1 installer passed temporary installation, payload hash verification,
installed Python worker processing, Flutter launch and removal. A fresh Windows VM and
manual native-dialog/visual-layout certification remain outside this validation.

Reproduce: build.ps1 followed by scripts/build_installer.ps1.
