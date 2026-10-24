"""Language resources and small, portable preference storage helpers."""
import json
import os
from pathlib import Path

LANGUAGES = {'ko': '한국어', 'en': 'English'}
TEXT = {
    'ko': {
        'subtitle': '필요한 부분만, 자연스럽게.', 'language': '언어',
        'images': '이미지', 'base': '기준 이미지', 'patch': '합성 이미지',
        'open_base': '기준 이미지 열기…', 'open_patch': '합성 이미지 열기…',
        'empty_file': '선택한 파일 없음', 'drop_hint': '파일을 버튼 위로 끌어 놓아도 열 수 있습니다.',
        'drop_off': '파일 열기 버튼으로 이미지를 선택하세요.',
        'region': '선택 영역', 'region_hint': '드래그로 이동하거나 모서리로 크기를 조절하세요.',
        'x': '가로 위치', 'y': '세로 위치', 'w': '너비', 'h': '높이',
        'lock': '가로세로 비율 고정', 'reset': '영역 초기화',
        'blend': '블렌딩', 'opacity': '불투명도', 'feather': '경계 부드럽게',
        'edge_match': '경계 색상 맞추기', 'guide': '선택 영역 표시',
        'preview': '미리보기', 'view_composite': '합성 결과', 'view_base': '기준', 'view_patch': '합성본',
        'swap': '이미지 맞바꾸기', 'export': 'PNG로 저장…', 'replace': '기준 파일 덮어쓰기…',
        'empty_title': '두 이미지로 시작하세요',
        'empty_body': '기준 이미지와 수정한 이미지를 열면\n선택한 부분만 합성할 수 있습니다.',
        'ready': '이미지 두 개를 열어 시작하세요.', 'need_patch': '합성 이미지를 열어 편집을 시작하세요.',
        'dimensions': '출력 {width} × {height} px  ·  원본 크기 유지',
        'selection': '선택 {width} × {height} px',
        'saved': '저장 완료: {name}', 'replaced': '기준 파일 저장 완료: {name}',
        'file_menu': '파일', 'view_menu': '보기', 'language_menu': '언어', 'quit': '종료',
        'image_files': '이미지 파일', 'all_files': '모든 파일', 'png_files': 'PNG 이미지',
        'no_image': '이미지가 필요합니다', 'need_both': '먼저 기준 이미지와 합성 이미지를 모두 열어주세요.',
        'open_failed': '이미지를 열 수 없습니다', 'open_error': '다른 이미지 파일을 선택해 주세요.\n\n{error}',
        'save_failed': '저장할 수 없습니다', 'save_error': '파일 위치와 쓰기 권한을 확인해 주세요.\n\n{error}',
        'confirm_title': '기준 파일을 덮어쓸까요?',
        'confirm_body': '합성 결과로 다음 파일을 교체합니다.\n\n{path}\n\n원본을 보관하려면 취소 후 PNG로 저장을 사용하세요.',
        'drop_error': 'PNG, JPG, WebP, BMP, TIFF 이미지 파일을 놓아주세요.',
        'settings_error': '언어는 변경됐지만 설정을 저장하지 못했습니다.',
        'missing_pillow': 'Pillow가 필요합니다.\n설치: python -m pip install -r requirements.txt',
    },
    'en': {
        'subtitle': 'Make every detail fit.', 'language': 'Language',
        'images': 'Images', 'base': 'Base image', 'patch': 'Patch image',
        'open_base': 'Open base image…', 'open_patch': 'Open patch image…',
        'empty_file': 'No file selected', 'drop_hint': 'You can also drop files onto the buttons.',
        'drop_off': 'Choose an image using either Open button.',
        'region': 'Selection', 'region_hint': 'Drag to move. Use a corner to resize.',
        'x': 'X position', 'y': 'Y position', 'w': 'Width', 'h': 'Height',
        'lock': 'Lock aspect ratio', 'reset': 'Reset selection',
        'blend': 'Blending', 'opacity': 'Opacity', 'feather': 'Feather',
        'edge_match': 'Match edge colors', 'guide': 'Show selection',
        'preview': 'Preview', 'view_composite': 'Composite', 'view_base': 'Base', 'view_patch': 'Patch',
        'swap': 'Swap images', 'export': 'Save PNG…', 'replace': 'Replace base file…',
        'empty_title': 'Start with two images',
        'empty_body': 'Open your base and edited images,\nthen blend only the area you choose.',
        'ready': 'Open two images to get started.', 'need_patch': 'Open a patch image to start editing.',
        'dimensions': 'Output {width} × {height} px  ·  Original size',
        'selection': 'Selection {width} × {height} px',
        'saved': 'Saved: {name}', 'replaced': 'Base file saved: {name}',
        'file_menu': 'File', 'view_menu': 'View', 'language_menu': 'Language', 'quit': 'Quit',
        'image_files': 'Image files', 'all_files': 'All files', 'png_files': 'PNG image',
        'no_image': 'Images required', 'need_both': 'Open both a base image and a patch image first.',
        'open_failed': 'Unable to open image', 'open_error': 'Choose another image file.\n\n{error}',
        'save_failed': 'Unable to save', 'save_error': 'Check the location and write permissions.\n\n{error}',
        'confirm_title': 'Replace the base file?',
        'confirm_body': 'The composite will replace this file:\n\n{path}\n\nTo keep the original, cancel and use Save PNG.',
        'drop_error': 'Drop a PNG, JPG, WebP, BMP, or TIFF image file.',
        'settings_error': 'Language changed, but the preference could not be saved.',
        'missing_pillow': 'Pillow is required.\nInstall: python -m pip install -r requirements.txt',
    },
}


def translate(language, key, **values):
    return TEXT.get(language, TEXT['en'])[key].format(**values)


def settings_path():
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    return base / 'RegionCompositor' / 'settings.json'


def load_language(path=None):
    try:
        value = json.loads((path or settings_path()).read_text(encoding='utf-8'))
        language = value.get('language') if isinstance(value, dict) else None
        return language if language in LANGUAGES else 'ko'
    except (OSError, ValueError, TypeError):
        return 'ko'


def save_language(language, path=None):
    if language not in LANGUAGES:
        raise ValueError('Unsupported language')
    path = path or settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps({'language': language}, ensure_ascii=False), encoding='utf-8')
    temporary.replace(path)
