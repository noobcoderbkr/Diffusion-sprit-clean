# Validation — 2026-09-16

Verified locally on Windows using Python 3.12.14, Pillow 12.3.0, Tk 8.6, and tkinterdnd2 0.4.4.1.

- All 19 automated tests passed, including the seven tests that instantiate a real Tk/TkinterDnD window. No tests were skipped in the final run.
- The actual desktop window was inspected in Korean and English. Selection coordinates, loaded images, and blend values remained unchanged when the language selector was used.
- The main controls fit the default 1240 × 840 client area with both images loaded. The inspector supports scrolling in smaller windows and with long filenames.
- The Korean and English README screenshots were captured from this application using generated geometric test images, without private user images.
- The preserved legacy implementation still matches its original recovery checksum. Core compositing behavior is inherited, while the new UI supplies translated file operations and PNG export.

## Packaged executable

- Built a Windows x64, one-file, windowed executable using Python 3.12.14 and PyInstaller 6.22.3. `build.ps1` runs the tests before packaging; all 19 passed with no skips.
- Launched the copied EXE from an independent folder without application source files. Opened generated 80 × 60 base and 160 × 120 patch images through native dialogs, composed the selection, and saved a PNG.
- Verified the exported PNG is 80 × 60 and changed pixels stay inside the selected rectangle (20, 15)–(60, 45). Actual changed bounds were (22, 16)–(58, 44).
- Executable size: 20,456,910 bytes. SHA-256: `cab8cf43b5e125e93b61a77f5b64fc732b489b7bb66348a8625e13ba62735e69`.
- GUI language switching was verified in the source application. Native drag-and-drop in the packaged EXE, a separate clean Windows machine, cross-platform behavior, and full screen-reader compatibility have not been verified.
