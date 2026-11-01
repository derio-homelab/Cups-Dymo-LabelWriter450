"""
Font catalog: a curated set of families, located by file name in FONT_DIRS.

The code names font *files* (never absolute paths); directories come from the
``LABEL_FONT_DIRS`` environment variable (os.pathsep-separated, default
``/usr/share/fonts``) and are scanned recursively once, then cached.
"""

import functools
import os
from typing import NamedTuple, Optional, Union

from PIL import ImageFont

from .config import DEFAULT_FONT_FAMILY

STYLES = ('regular', 'bold', 'italic', 'bold-italic')
DEFAULT_FONT_DIR = '/usr/share/fonts'

CATALOG: dict[str, dict[str, list[str]]] = {
    'DejaVu Sans': {
        'regular': ['DejaVuSans.ttf'],
        'bold': ['DejaVuSans-Bold.ttf'],
        'italic': ['DejaVuSans-Oblique.ttf'],
        'bold-italic': ['DejaVuSans-BoldOblique.ttf'],
    },
    'DejaVu Serif': {
        'regular': ['DejaVuSerif.ttf'],
        'bold': ['DejaVuSerif-Bold.ttf'],
        'italic': ['DejaVuSerif-Italic.ttf'],
        'bold-italic': ['DejaVuSerif-BoldItalic.ttf'],
    },
    'DejaVu Sans Mono': {
        'regular': ['DejaVuSansMono.ttf'],
        'bold': ['DejaVuSansMono-Bold.ttf'],
        'italic': ['DejaVuSansMono-Oblique.ttf'],
        'bold-italic': ['DejaVuSansMono-BoldOblique.ttf'],
    },
    'Liberation Sans': {
        'regular': ['LiberationSans-Regular.ttf'],
        'bold': ['LiberationSans-Bold.ttf'],
        'italic': ['LiberationSans-Italic.ttf'],
        'bold-italic': ['LiberationSans-BoldItalic.ttf'],
    },
    'Liberation Serif': {
        'regular': ['LiberationSerif-Regular.ttf'],
        'bold': ['LiberationSerif-Bold.ttf'],
        'italic': ['LiberationSerif-Italic.ttf'],
        'bold-italic': ['LiberationSerif-BoldItalic.ttf'],
    },
    'Liberation Mono': {
        'regular': ['LiberationMono-Regular.ttf'],
        'bold': ['LiberationMono-Bold.ttf'],
        'italic': ['LiberationMono-Italic.ttf'],
        'bold-italic': ['LiberationMono-BoldItalic.ttf'],
    },
    'Noto Sans': {
        'regular': ['NotoSans-Regular.ttf'],
        'bold': ['NotoSans-Bold.ttf'],
        'italic': ['NotoSans-Italic.ttf'],
        'bold-italic': ['NotoSans-BoldItalic.ttf'],
    },
    'Noto Serif': {
        'regular': ['NotoSerif-Regular.ttf'],
        'bold': ['NotoSerif-Bold.ttf'],
        'italic': ['NotoSerif-Italic.ttf'],
        'bold-italic': ['NotoSerif-BoldItalic.ttf'],
    },
}

# Nearest-style preference per requested style.
_NEAREST = {
    'regular': ('regular', 'bold', 'italic', 'bold-italic'),
    'bold': ('bold', 'regular', 'bold-italic', 'italic'),
    'italic': ('italic', 'regular', 'bold-italic', 'bold'),
    'bold-italic': ('bold-italic', 'bold', 'italic', 'regular'),
}

FontType = Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]


class ResolvedFont(NamedTuple):
    path: Optional[str]
    style: str
    substituted: bool


def font_dirs() -> list[str]:
    raw = os.environ.get('LABEL_FONT_DIRS') or DEFAULT_FONT_DIR
    return [d for d in raw.split(os.pathsep) if d]


@functools.lru_cache(maxsize=None)
def _scan(dirs: tuple[str, ...]) -> dict[str, dict[str, str]]:
    """Return {family: {style: path}} for catalog files found under dirs."""
    found: dict[str, str] = {}
    for directory in dirs:
        for root, _subdirs, files in os.walk(directory):
            for name in sorted(files):
                found.setdefault(name, os.path.join(root, name))
    result: dict[str, dict[str, str]] = {}
    for family, styles in CATALOG.items():
        for style in STYLES:
            for candidate in styles.get(style, []):
                if candidate in found:
                    result.setdefault(family, {})[style] = found[candidate]
                    break
    return result


def _available() -> dict[str, dict[str, str]]:
    return _scan(tuple(font_dirs()))


def reset_cache() -> None:
    _scan.cache_clear()


def list_fonts() -> list[dict]:
    available = _available()
    return [
        {'family': family,
         'styles': [s for s in STYLES if s in available[family]]}
        for family in CATALOG if family in available
    ]


def _nearest(files: dict[str, str], bold: bool, italic: bool) -> tuple[str, str]:
    wanted = 'bold-italic' if bold and italic else 'bold' if bold else 'italic' if italic else 'regular'
    for style in _NEAREST[wanted]:
        if style in files:
            return style, files[style]
    raise LookupError(wanted)  # unreachable: scan only records non-empty families


def resolve(family: str, bold: bool = False, italic: bool = False) -> ResolvedFont:
    """Resolve a family/style request to a font file, falling back gracefully."""
    available = _available()
    substituted = family not in available
    chain = [family] if not substituted else []
    chain += [f for f in (DEFAULT_FONT_FAMILY, *CATALOG) if f in available]
    if chain:
        style, path = _nearest(available[chain[0]], bold, italic)
        return ResolvedFont(path, style, substituted)
    return ResolvedFont(None, 'regular', True)


def open_font(resolved: ResolvedFont, size_px: int) -> FontType:
    if resolved.path:
        try:
            return ImageFont.truetype(resolved.path, size_px)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size=size_px)
    except TypeError:  # Pillow < 10.1 has no sized default font
        return ImageFont.load_default()


def load(family: str, bold: bool, italic: bool, size_px: int) -> FontType:
    return open_font(resolve(family, bold, italic), size_px)
