from pathlib import Path
import string
import tempfile
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image
from compositor_app import RegionCompositorApp, TkinterDnD
from ui_support import TEXT, load_language, save_language


class LanguageTests(unittest.TestCase):
    def test_every_translation_has_matching_parameters(self):
        self.assertEqual(set(TEXT['en']), set(TEXT['ko']))
        formatter = string.Formatter()
        for key in TEXT['en']:
            parameters = lambda value: {name for _, name, _, _ in formatter.parse(value) if name is not None}
            self.assertEqual(parameters(TEXT['en'][key]), parameters(TEXT['ko'][key]), key)

    def test_settings_persist_and_invalid_settings_fall_back(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.json'
            self.assertEqual(load_language(path), 'ko')
            save_language('en', path)
            self.assertEqual(load_language(path), 'en')
            for value in ['broken JSON', '[]', '{"language":"xx"}']:
                path.write_text(value, encoding='utf-8')
                self.assertEqual(load_language(path), 'ko')


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)
        try:
            self.root = TkinterDnD.Tk() if TkinterDnD is not None else tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f'Tk display unavailable: {exc}')
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.app = RegionCompositorApp(self.root, language='ko', preference_path=self.path / 'settings.json')
        self.root.update_idletasks()

    def load_images(self):
        base, patch_image = self.path / 'base.png', self.path / 'patch.png'
        Image.new('RGBA', (80, 60), (20, 40, 60, 255)).save(base)
        Image.new('RGBA', (160, 120), (220, 100, 80, 255)).save(patch_image)
        self.app.load_image_path(base, 'base')
        self.app.load_image_path(patch_image, 'patch')
        self.app.feather_var.set(0)
        self.app.edge_match.set(False)
        self.root.update_idletasks()

    def test_language_switch_preserves_edit_and_relaunch_preference(self):
        self.load_images()
        self.app.set_rect(.2, .2, .4, .4)
        self.app.opacity_var.set(65)
        before = self.app.compose().tobytes()
        self.app.change_language(code='en')
        self.root.update_idletasks()
        self.assertEqual(self.app.text('export').get(), 'Save PNG…')
        self.assertEqual(self.app.file_menu.entrycget(0, 'label'), 'Open base image…')
        self.assertEqual(self.app.compose().tobytes(), before)
        self.assertEqual(load_language(self.path / 'settings.json'), 'en')
        self.app.change_language(code='ko')
        self.root.update_idletasks()
        self.assertEqual(self.app.text('export').get(), 'PNG로 저장…')
        self.assertEqual(self.app.compose().tobytes(), before)

    def test_save_controls_disabled_until_both_images_loaded(self):
        self.assertIn('disabled', self.app.export_button.state())
        self.load_images()
        self.assertNotIn('disabled', self.app.export_button.state())

    def test_export_preserves_base_and_cancelled_replace_does_nothing(self):
        self.load_images()
        before = self.app.base.path.read_bytes()
        output = self.path / 'result.png'
        with patch('compositor_app.filedialog.asksaveasfilename', return_value=str(output)):
            self.app.save_as()
        self.assertTrue(output.is_file())
        self.assertEqual(self.app.base.path.read_bytes(), before)
        with patch('compositor_app.messagebox.askyesno', return_value=False):
            self.app.save_png()
        self.assertEqual(self.app.base.path.read_bytes(), before)

    def test_confirmed_replace_saves_and_refreshes_base(self):
        self.load_images()
        expected = self.app.compose().tobytes()
        with patch('compositor_app.messagebox.askyesno', return_value=True):
            self.app.save_png()
        self.assertEqual(self.app.base.image.tobytes(), expected)
        with Image.open(self.app.base.path) as result:
            self.assertEqual(result.tobytes(), expected)

    def test_invalid_image_error_uses_current_language(self):
        self.app.change_language(code='en')
        with patch('compositor_app.messagebox.showerror') as dialog:
            self.app.load_image_path(self.path / 'missing.png', 'base')
        self.assertEqual(dialog.call_args.args[0], 'Unable to open image')

    def test_keyboard_nudge_uses_base_image_pixels(self):
        self.load_images()
        before = self.app.rect[:]
        self.app.nudge(1, 0, 1)
        self.assertAlmostEqual(self.app.rect[0] - before[0], 1 / 80)

    def test_drop_accepts_unicode_paths_with_spaces_and_recovers_from_invalid_files(self):
        path = self.path / '이미지 with spaces.png'
        Image.new('RGBA', (20, 20), 'red').save(path)
        self.app.handle_file_drop(SimpleNamespace(data='{' + str(path) + '}'), 'base')
        self.assertEqual(self.app.base.path, path)
        with patch('compositor_app.messagebox.showinfo') as dialog:
            self.app.handle_file_drop(SimpleNamespace(data='{missing file.txt}'), 'patch')
        dialog.assert_called_once()
        self.app.handle_file_drop(SimpleNamespace(data='{' + str(path) + '}'), 'patch')
        self.assertEqual(self.app.patch.path, path)


if __name__ == '__main__':
    unittest.main()
