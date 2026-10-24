import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


v1 = load_module('region_compositor', ROOT / 'region_compositor.py')
v2 = load_module('region_compositor_v2', ROOT / 'versions' / 'region_compositor_v2.py')


class Value:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


def legacy_app(base, patch, opacity=100, feather=0):
    app = object.__new__(v1.RegionCompositorApp)
    app.base = v1.LoadedImage(Path('base.png'), base)
    app.patch = v1.LoadedImage(Path('patch.png'), patch)
    app.rect = [0.25, 0.25, 0.5, 0.5]
    app.opacity_var = Value(opacity)
    app.feather_var = Value(feather)
    app.edge_match = Value(False)
    return app


class CompositeTests(unittest.TestCase):
    def setUp(self):
        self.base = Image.new('RGBA', (80, 60), (20, 40, 60, 255))
        self.patch = Image.new('RGBA', (160, 120), (220, 100, 80, 255))

    def assertSameImage(self, actual, expected):
        self.assertEqual(actual.size, expected.size)
        self.assertEqual(actual.tobytes(), expected.tobytes())

    def assertOutsideUnchanged(self, result, box):
        left, top, right, bottom = box
        for y in range(self.base.height):
            for x in range(self.base.width):
                if not (left <= x < right and top <= y < bottom):
                    self.assertEqual(result.getpixel((x, y)), self.base.getpixel((x, y)))

    def test_legacy_changes_only_selected_region(self):
        result = legacy_app(self.base, self.patch).compose()
        self.assertEqual(result.size, self.base.size)
        self.assertEqual(result.getpixel((40, 30)), (220, 100, 80, 255))
        self.assertOutsideUnchanged(result, (20, 15, 60, 45))

    def test_legacy_uses_corresponding_relative_crop(self):
        patch = Image.new('RGBA', (160, 120), (0, 0, 255, 255))
        patch.paste((255, 0, 0, 255), (40, 30, 120, 90))
        result = legacy_app(self.base, patch).compose()
        self.assertEqual(result.getpixel((20, 15)), (255, 0, 0, 255))
        self.assertEqual(result.getpixel((59, 44)), (255, 0, 0, 255))

    def test_legacy_zero_opacity_and_transparent_patch(self):
        self.assertSameImage(legacy_app(self.base, self.patch, opacity=0).compose(), self.base)
        transparent = Image.new('RGBA', self.patch.size, (200, 100, 50, 0))
        self.assertSameImage(legacy_app(self.base, transparent).compose(), self.base)

    def test_legacy_feather_blends_inward(self):
        result = legacy_app(self.base, self.patch, feather=5).compose()
        self.assertEqual(result.getpixel((20, 15)), self.base.getpixel((20, 15)))
        self.assertEqual(result.getpixel((40, 30)), self.patch.getpixel((80, 60)))
        self.assertOutsideUnchanged(result, (20, 15, 60, 45))

    def test_legacy_png_replacement_in_temporary_directory(self):
        app = legacy_app(self.base, self.patch)
        expected = app.compose()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'base.png'
            self.base.save(path)
            app.save_image_replacing(expected, path)
            with Image.open(path) as result:
                self.assertSameImage(result, expected)
            self.assertEqual([p.name for p in Path(directory).iterdir()], ['base.png'])

    def test_v2_stretch_keeps_output_size_and_outside_pixels(self):
        options = v2.CompositeOptions(black_to_alpha=False, feather=0)
        result = v2.composite_images(self.base, self.patch, (20, 15, 40, 30), options)
        self.assertEqual(result.size, self.base.size)
        self.assertEqual(result.getpixel((40, 30)), (220, 100, 80, 255))
        self.assertOutsideUnchanged(result, (20, 15, 60, 45))

    def test_v2_contain_preserves_empty_margins(self):
        patch = Image.new('RGBA', (40, 20), (255, 0, 0, 255))
        options = v2.CompositeOptions(fit_mode='contain', black_to_alpha=False, feather=0)
        result = v2.composite_images(self.base, patch, (20, 10, 40, 40), options)
        self.assertEqual(result.getpixel((40, 11)), self.base.getpixel((40, 11)))
        self.assertEqual(result.getpixel((40, 30)), (255, 0, 0, 255))
        self.assertOutsideUnchanged(result, (20, 10, 60, 50))

    def test_v2_black_mask_can_be_disabled(self):
        patch = Image.new('RGBA', (40, 30), (0, 0, 0, 255))
        masked = v2.composite_images(self.base, patch, (20, 15, 40, 30), v2.CompositeOptions(feather=0))
        self.assertSameImage(masked, self.base)
        options = v2.CompositeOptions(black_to_alpha=False, feather=0)
        unmasked = v2.composite_images(self.base, patch, (20, 15, 40, 30), options)
        self.assertEqual(unmasked.getpixel((40, 30)), (0, 0, 0, 255))

    def test_v2_negative_position_clips_to_canvas(self):
        options = v2.CompositeOptions(black_to_alpha=False, feather=0)
        result = v2.composite_images(self.base, self.patch, (-10, -5, 20, 15), options)
        self.assertEqual(result.getpixel((0, 0)), (220, 100, 80, 255))
        self.assertOutsideUnchanged(result, (0, 0, 10, 10))

    def test_v2_cli_writes_png(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            base = directory / 'base.png'
            patch = directory / 'patch.png'
            output = directory / 'result.png'
            self.base.save(base)
            self.patch.save(patch)
            completed = subprocess.run([
                sys.executable, str(ROOT / 'versions' / 'region_compositor_v2.py'),
                '--base', str(base), '--patch', str(patch), '--out', str(output),
                '--x', '20', '--y', '15', '--w', '40', '--h', '30',
                '--no-black-to-alpha', '--feather', '0',
            ], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            with Image.open(output) as result:
                self.assertEqual(result.size, self.base.size)
                self.assertOutsideUnchanged(result, (20, 15, 60, 45))


if __name__ == '__main__':
    unittest.main()
