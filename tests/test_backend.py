import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image
from backend.engine import Compositor
from backend.worker import dispatch


class BackendTests(unittest.TestCase):
    def test_pixel_parity_with_stable_engine(self):
        base = Image.new('RGBA', (83, 61), (20, 40, 60, 255))
        patch = Image.new('RGBA', (161, 123), (220, 100, 80, 180))
        cases = json.loads((Path(__file__).parent / 'compositing_baselines.json').read_text())
        self.assertEqual(len(cases), 27)
        for case in cases:
            with self.subTest(case=case):
                new = Compositor(base, patch, case['rect'], case['opacity'], case['feather'], case['edge'])
                self.assertEqual(hashlib.sha256(new.compose(case['mode']).tobytes()).hexdigest(), case['sha256'])

    def test_protocol_and_full_resolution_save(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            base, patch = root / '기준 이미지.png', root / 'patch.png'
            output = root / '결과.png'
            Image.new('RGBA', (81, 63), (10, 20, 30, 255)).save(base)
            Image.new('RGBA', (162, 126), (210, 100, 50, 255)).save(patch)
            request = dict(base=str(base), patch=str(patch), rect=[.25, .25, .5, .5], opacity=100, feather=0, edgeMatch=False)
            source = base.read_bytes()
            commands = [dict(id=1, command='inspect', path=str(base)),
                        dict(request, id=2, command='preview'),
                        dict(request, id=3, command='save', output=str(output)),
                        dict(request, id=4, command='save', output=str(base)),
                        dict(id=5, command='unknown')]
            process = subprocess.run([sys.executable, '-u', '-m', 'backend.worker'],
                input='\n'.join(json.dumps(c) for c in commands) + '\n',
                capture_output=True, text=True, check=True)
            responses = [json.loads(line) for line in process.stdout.splitlines()]
            self.assertEqual([r['id'] for r in responses], [1, 2, 3, 4, 5])
            self.assertEqual([r['ok'] for r in responses], [True, True, True, False, False])
            import base64
            with Image.open(io.BytesIO(base64.b64decode(responses[1]['result']['png']))) as preview:
                with Image.open(output) as saved:
                    self.assertEqual(saved.size, (81, 63))
                    self.assertEqual(saved.tobytes(), preview.tobytes())
                    self.assertEqual(saved.getpixel((0, 0)), (10, 20, 30, 255))
            self.assertEqual(source, base.read_bytes())
            self.assertEqual(list(root.glob('.region-*')), [])

    def test_validation_and_worker_recovery(self):
        for rect in ([0, 0, 0, 1], [1, 0, .5, .5], [float('nan'), 0, .5, .5]):
            with self.assertRaises(ValueError):
                dispatch(dict(command='preview', rect=rect))
        process = subprocess.run([sys.executable, '-m', 'backend.worker'],
            input='not json\n[]\n{"id":9,"command":"unknown"}\n',
            capture_output=True, text=True, check=True)
        responses = [json.loads(line) for line in process.stdout.splitlines()]
        self.assertEqual(len(responses), 3)
        self.assertEqual(responses[-1]['id'], 9)
        self.assertTrue(all(not item['ok'] for item in responses))


if __name__ == '__main__':
    unittest.main()
