"""Convert the project logo into a multi-resolution Windows icon."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
with Image.open(ROOT / 'flutter_app/assets/region_compositor.png') as image:
    image.convert('RGBA').save(
        ROOT / 'flutter_app/windows/runner/resources/app_icon.ico',
        format='ICO',
        sizes=[(size, size) for size in (16, 20, 24, 32, 40, 48, 64, 128, 256)],
    )
