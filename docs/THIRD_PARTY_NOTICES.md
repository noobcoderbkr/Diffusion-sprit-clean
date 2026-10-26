# Licensing review — Flutter Windows branch

Reviewed 2026-10-27. This is a component inventory and distribution checklist,
not an assurance about all jurisdictions or the rights in users' images.

## Project author's terms

The v0.1.0 tree at ff7de566 had no LICENSE file. Earlier conversation supplied
the author's non-commercial/no-redistribution terms. This branch adds that
text, renamed for RegionCompositor, without changing the stable tag. It is a
source-available custom license, not an OSI open-source license. It does not
override third-party rights. The owner's requested GitHub branch/PR work is
authorized by the current task. Others need the owner's written permission
for commercial use or redistribution. Historical versions' licensing is not
retroactively settled by adding a license on this branch.

## Components

| Component | Terms / source | Handling |
| --- | --- | --- |
| Flutter framework and generated Windows runner | [BSD-3-Clause](https://github.com/flutter/flutter/blob/stable/LICENSE) | Include generated Flutter NOTICES and package licenses |
| Dart SDK | [BSD-3-Clause and bundled notices](https://github.com/dart-lang/sdk/blob/main/LICENSE) | Preserve SDK/runtime notices |
| file_selector and federated implementations | [BSD-3-Clause](https://github.com/flutter/packages/blob/main/packages/file_selector/file_selector/LICENSE) | Resolved license texts collected from pub cache |
| Python | [PSF license and included notices](https://docs.python.org/3/license.html) | Include installed Python LICENSE.txt |
| Pillow 12.3.0 | [MIT-CMU and bundled third-party notices](https://github.com/python-pillow/Pillow/blob/main/LICENSE) | Include full wheel license, including codec notices |
| PyInstaller 6.21.0 | [GPL with distribution exception](https://pyinstaller.org/en/stable/license.html) | Bootloader exception permits bundled proprietary apps; include license and exception |
| Other resolved Dart dependencies | Individual package LICENSE files | Full inventory in THIRD_PARTY_LICENSES.txt, including dev dependencies |

The Flutter worker imports Pillow only, and excludes Tkinter/tkinterdnd2 from
the frozen bundle. The unchanged legacy UI still has its original Tk/Tcl and
tkinterdnd2 dependencies; a legacy distribution needs their own notices.

`scripts/collect_licenses.py` collects actual installed license texts and fails
if a package notice is missing. Flutter's engine NOTICES also ship in its
generated data folder. Do not remove either from a distribution. The app's
information button opens Flutter's license screen with the collected notices.

No AI model, model weights, paid API, external font, or sample photo is added.
The name “Diffusion” does not introduce a Stable Diffusion dependency.
Users must have permission to process their input images; the project license
does not grant image, likeness, trademark, or model rights. Images remain local
in this implementation; no analytics or image upload feature is added.

Before publishing a binary, retain these notices, review the exact bundled
versions, and supply the Microsoft Visual C++ runtime under Microsoft's terms
when needed. See [Flutter Windows distribution documentation](https://docs.flutter.dev/platform-integration/windows/building).
