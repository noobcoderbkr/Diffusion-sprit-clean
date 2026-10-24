# Interface design

The 2026-09-15 interface update applies selected Apple Human Interface Guidelines to a Windows-first Tkinter application. It does not claim full HIG conformance, native macOS behavior, Liquid Glass rendering, or complete assistive-technology support.

| Reference | Applied choice |
| --- | --- |
| [Layout](https://developer.apple.com/design/human-interface-guidelines/layout) | Large central image preview, grouped editing controls, consistent spacing, and a scrollable inspector when vertical space is limited. |
| [Typography](https://developer.apple.com/design/human-interface-guidelines/typography) | System font, distinct title/section/body styles, regular or bold weights, and readable secondary labels. |
| [Toolbars](https://developer.apple.com/design/human-interface-guidelines/toolbars) | A focused header with language selection and one prominent save action. Less frequent file replacement stays in the File menu. |
| [Buttons](https://developer.apple.com/design/human-interface-guidelines/buttons) | Explicit action names, consistent controls, and unavailable save/swap actions disabled until both images are loaded. |
| [Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility) | Dark text on light surfaces, blue emphasis, keyboard focus, keyboard selection movement, and textual status rather than color alone. |

## Color and behavior

- Main text: `#1D1D1F`; secondary text: `#5D626B`.
- White inspector cards over a neutral `#F3F4F6` background.
- Action blue: `#0066CC`, with white button labels and a darker hover state.
- Selection handles use both a white outline and a blue border to remain visible across images.
- A native file dialog handles file selection. Export uses a separate name by default; original replacement has a cancel-first confirmation.

The language selector updates bound text without rebuilding the editing state. Translation keys and format parameters are checked by tests. Preferences are stored outside the project; preference-write failures do not cancel language switching.

## Platform limits

Tkinter/ttk provides keyboard navigation and native menus/dialogs, but screen-reader exposure varies by platform and Tk build. Full screen-reader compatibility and macOS behavior have not been certified. The default inspector scrolls when the window is short; no controls are intentionally removed at smaller sizes. The main window has a minimum client size of 960 × 640.

No Apple fonts, SF Symbols assets, or copied Apple illustrations are bundled. The README screenshots use an original geometric robot fixture created for UI verification.
