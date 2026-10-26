"""One JSON request/response per line. No sockets, shell commands or Tk dependency."""
import base64
import io
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import warnings

from PIL import Image, ImageOps
from backend.engine import Compositor

# Reject decompression bombs rather than attempting unbounded allocations.
Image.MAX_IMAGE_PIXELS = 40_000_000
warnings.simplefilter('error', Image.DecompressionBombWarning)


def number(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Expected a number')
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError('Number outside supported range')
    return value


def load(path):
    with Image.open(path) as image:
        return ImageOps.exif_transpose(image).convert('RGBA')


def png(image):
    data = io.BytesIO()
    image.save(data, 'PNG')
    return base64.b64encode(data.getvalue()).decode('ascii')


def dispatch(request):
    command = request.get('command')
    if command == 'inspect':
        image = load(request['path'])
        size = image.size
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        return dict(width=size[0], height=size[1], png=png(image))
    if command not in ('preview', 'save'):
        raise ValueError('Unknown command')
    rect = request.get('rect', [.25, .25, .5, .5])
    if not isinstance(rect, list) or len(rect) != 4:
        raise ValueError('Invalid rectangle')
    x, y, w, h = [number(v, 0, 1) for v in rect]
    if w < .01 or h < .01 or x + w > 1.000001 or y + h > 1.000001:
        raise ValueError('Rectangle must be inside image')
    opacity = number(request.get('opacity', 100), 0, 100)
    feather = number(request.get('feather', 24), 0, 200)
    edge = request.get('edgeMatch', True)
    if not isinstance(edge, bool):
        raise ValueError('Invalid edge matching flag')
    base, patch = load(request['base']), load(request['patch'])
    mode = request.get('mode', 'composite')
    if mode not in ('base', 'patch', 'composite'):
        raise ValueError('Invalid preview mode')
    result = Compositor(base, patch, rect, opacity, feather, edge).compose(
        'composite' if command == 'save' else mode)
    if command == 'preview':
        result.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        return dict(png=png(result))
    destination = Path(request['output']).resolve()
    # Saving to either source is deliberately disallowed in the Flutter UI.
    if destination in (Path(request['base']).resolve(), Path(request['patch']).resolve()):
        raise ValueError('Choose a different output file to preserve the source')
    if destination.suffix.lower() != '.png':
        raise ValueError('Output must have a .png extension')
    fd, temporary = tempfile.mkstemp(prefix='.region-', suffix='.png', dir=destination.parent)
    os.close(fd)
    try:
        result.save(temporary, 'PNG')
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return dict(output=str(destination), width=result.width, height=result.height)


def main():
    # Windows otherwise decodes redirected stdin using the system code page.
    sys.stdin.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    for line in sys.stdin:
        request = {}
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError('Expected a JSON object')
            response = dict(id=request.get('id'), ok=True, result=dispatch(request))
        except Exception as error:
            response = dict(id=request.get('id') if isinstance(request, dict) else None,
                            ok=False, error=str(error))
        print(json.dumps(response, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
