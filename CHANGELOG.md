# Changelog

## Unreleased — Faster previews

- Reuse decoded preview inputs within a 128 MiB pixel cache and reload changed files.
- Encode preview PNGs with lighter lossless compression and avoid a redundant full-size copy.
- Preserve full-resolution export, which still reads the source files directly.

## 0.2.1 — Flutter main application

- Flutter is the only desktop UI and the default run/build path.
- Removed Tkinter interfaces, legacy launchers, historical variants and obsolete UI docs/screenshots.
- Preserved the Pillow compositing algorithm and 27 pixel-output regression baselines.
- Retained image opening, region editing, preview, PNG saving and Korean/English switching.
- Updated the supplied logo and single-EXE installer with bundled Python/runtime DLLs.
