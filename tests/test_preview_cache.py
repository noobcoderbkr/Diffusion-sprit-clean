import base64
import io
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image
from backend import worker


class PreviewCacheTests(unittest.TestCase):
    def test_repeated_preview_preserves_pixels_and_reloads_replaced_file(self):
        with TemporaryDirectory() as folder:
            base, overlay, replacement = [Path(folder) / name for name in
                                          ('기준.png', 'patch.png', 'replacement.png')]
            Image.new('RGBA', (32, 24), (1, 2, 3, 127)).save(base)
            Image.new('RGBA', (64, 48), (201, 72, 44, 230)).save(overlay)
            request = dict(command='preview', base=str(base), patch=str(overlay),
                           rect=[.125, .125, .5, .5], feather=2, edgeMatch=False)
            expected = worker.dispatch(request)
            cache = worker.PreviewCache()
            with patch.object(worker, 'load', wraps=worker.load) as read:
                for mode in ('base', 'patch', 'composite', 'composite'):
                    request['mode'] = mode
                    result = worker.dispatch(request, cache)
                    if mode == 'composite':
                        self.assertEqual(result, expected)
                self.assertEqual(read.call_count, 2)
                Image.new('RGBA', (64, 48), (33, 155, 220, 220)).save(replacement)
                stat = overlay.stat()
                os.utime(replacement, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                replacement.replace(overlay)
                changed = worker.dispatch(request, cache)
                self.assertEqual(read.call_count, 3)
                self.assertNotEqual(changed, expected)
                output = Path(folder) / 'export.png'
                worker.dispatch(dict(request, command='save', output=str(output)), cache)
                self.assertEqual(read.call_count, 5)
                with Image.open(output) as saved, Image.open(
                    io.BytesIO(base64.b64decode(changed['png']))
                ) as preview:
                    self.assertEqual(saved.tobytes(), preview.tobytes())

    def test_cache_evicts_and_does_not_retain_oversized_images(self):
        with TemporaryDirectory() as folder:
            first, second, large = [Path(folder) / name for name in ('a.png', 'b.png', 'big.png')]
            for path, size in [(first, (2, 2)), (second, (2, 2)), (large, (3, 3))]:
                Image.new('RGBA', size).save(path)
            cache = worker.PreviewCache(max_bytes=16)
            first_image = cache.get(first)
            self.assertIs(cache.get(first), first_image)
            self.assertIsNot(cache.get(large), cache.get(large))
            self.assertIs(cache.get(first), first_image)
            cache.get(second)
            self.assertIsNot(cache.get(first), first_image)
