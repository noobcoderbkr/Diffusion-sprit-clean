"""Exercise the frozen worker independently of Python module imports at runtime."""
import base64
import io
import json
from pathlib import Path
import subprocess
import tempfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
worker = ROOT / 'flutter_app/build/windows/x64/runner/Release/engine/region_worker.exe'
with tempfile.TemporaryDirectory() as folder:
    directory = Path(folder)
    base, patch, output = [directory / name for name in ('기준 이미지.png', '패치.png', '결과.png')]
    Image.new('RGBA', (81, 63), (10, 20, 30, 255)).save(base)
    Image.new('RGBA', (162, 126), (210, 100, 50, 255)).save(patch)
    settings = dict(base=str(base), patch=str(patch), rect=[.25, .25, .5, .5],
                    opacity=100, feather=0, edgeMatch=False)
    requests = [dict(command='inspect', path=str(base)),
                dict(settings, command='preview'),
                dict(settings, command='save', output=str(output))]
    result = subprocess.run([str(worker)], cwd=directory, input='\n'.join(
        json.dumps(dict(request, id=i), ensure_ascii=False) for i, request in enumerate(requests)) + '\n',
        encoding='utf-8', capture_output=True, check=True, timeout=60)
    responses = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(responses) == 3 and all(r['ok'] for r in responses), responses
    with Image.open(output) as saved:
        assert saved.size == (81, 63)
        assert saved.getpixel((0, 0)) == (10, 20, 30, 255)
        assert saved.getpixel((40, 30)) == (210, 100, 50, 255)
        with Image.open(io.BytesIO(base64.b64decode(responses[1]['result']['png']))) as preview:
            assert saved.tobytes() == preview.tobytes()
print('Frozen worker: Unicode paths, preview and full-resolution save passed')
