"""Collect resolved SDK/package notices for the Windows bundle; fail if missing."""
import importlib.metadata
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

ROOT = Path(__file__).resolve().parents[1]
config = ROOT / 'flutter_app/.dart_tool/package_config.json'
sections = []


def add(name, path):
    if not path.is_file():
        raise FileNotFoundError(f'Missing license for {name}: {path}')
    sections.append(f'===== {name} =====\n{path.read_text(encoding="utf-8")}\n')


for package in json.loads(config.read_text())['packages']:
    if package['name'] == 'region_compositor':
        continue
    uri = package['rootUri']
    directory = (Path(url2pathname(urlparse(uri).path)) if uri.startswith('file:')
                 else (config.parent / unquote(uri)).resolve())
    candidates = [directory / name for name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt')]
    # SDK packages inherit Flutter's repository license.
    if directory.parent.name == 'packages' and package['name'].startswith('flutter'):
        candidates.append(directory.parent.parent / 'LICENSE')
    license_file = next((p for p in candidates if p.is_file()), None)
    if license_file is None:
        raise FileNotFoundError(f'Missing package license: {package["name"]}')
    add(package['name'], license_file)

for package_name in ('Pillow', 'pyinstaller'):
    distribution = importlib.metadata.distribution(package_name)
    notices = [f for f in distribution.files if 'licenses/' in str(f).replace('\\', '/')
               and Path(str(f)).name.lower().startswith(('license', 'copying'))]
    if not notices:
        raise FileNotFoundError(f'Missing notices: {package_name}')
    for notice in notices:
        add(f'{package_name} {distribution.version} / {notice.name}', Path(distribution.locate_file(notice)))

add(f'Python {sys.version.split()[0]}', Path(sys.base_prefix) / 'LICENSE.txt')
output = ROOT / 'flutter_app/assets/THIRD_PARTY_LICENSES.txt'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text('\n'.join(sections), encoding='utf-8')
print(f'Collected {len(sections)} notice files into {output.name}')
