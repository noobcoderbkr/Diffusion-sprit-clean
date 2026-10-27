# RegionCompositor logo

Current artwork is the user's supplied "RegionCompositor 앱 아이콘과 워드마크.png"
(2026-10-27). It replaces the earlier overlapping-square logo.

- Unmodified source with wordmark: docs/images/region-compositor-wordmark.png.
- Isolated app symbol: flutter_app/assets/region_compositor.png.
- Windows ICO: flutter_app/windows/runner/resources/app_icon.ico.
- ICO resolutions: 16, 20, 24, 32, 40, 48, 64, 128 and 256 pixels.
- The app bar and Windows executable/window/taskbar use the symbol. The English
  and Korean README files display the supplied full image with its wordmark.
- The original stable Python app and v0.1.0 are unchanged.

The supplied source is retained byte-for-byte. The built-in image generation
edit tool isolated the upper symbol and removed the background/wordmark for
small app-icon use. Pillow only converts that asset into the multi-size ICO.
Rebuild with python scripts/build_app_icon.py (also called by the bundle build).
No image-generation service is used during builds or application runtime.

## Icon extraction prompt

Edit target: supplied RegionCompositor logo sheet. Extract ONLY the existing
upper app-icon symbol onto a genuinely transparent background, deleting all
background, external shadow and all wordmark text. Preserve the original symbol
exactly: overlapping tilted rounded image panels, blue mountain/moon scene on
left, orange/purple sunset lake scene on right, white dashed selection rectangle
with four white square handles. Do not redesign, simplify, recolor, change
geometry, add details or alter internal artwork. Center this unchanged symbol
in a square canvas with equal tight 6% padding, making it large and clear as a
Windows app icon. No letters, no wordmark. Transparent outside the silhouette;
keep white selection handles and dashes opaque. This is precise background
extraction and isolation, not a new logo design.
