"""
Image blocks: upload storage, built-in icons, loading and 1-bit conversion.

Uploads are content-addressed (sha256) in ``LABEL_IMAGE_DIR`` (default: an
``images/`` directory beside ``LABEL_MEMORY_FILE``). References are
``upload:<sha256>.<ext>`` or ``icon:<name>``.
"""

import hashlib
import io
import os
import re
import threading
from collections import OrderedDict
from typing import Optional

from PIL import Image

ICON_DIR = os.path.join(os.path.dirname(__file__), 'static', 'icons')
DEFAULT_MAX_UPLOAD_MB = 5
CACHE_LIMIT = 64
MAX_RENDER_PIXELS = 4_000_000     # budget for one rasterized/resized image
MAX_UPLOAD_PIXELS = 25_000_000    # decoded size cap for uploaded PNG/JPEG

Image.MAX_IMAGE_PIXELS = MAX_UPLOAD_PIXELS

_UPLOAD_RE = re.compile(r'^upload:([0-9a-f]{64}\.(?:png|jpg|svg))$')
_ICON_RE = re.compile(r'^icon:([a-z0-9-]+)$')


class UnsupportedImage(ValueError):
    """Upload is not a PNG, JPEG or SVG."""


class ImageTooLarge(ValueError):
    """Upload exceeds LABEL_MAX_UPLOAD_MB."""


class ImageMissing(LookupError):
    """Reference does not resolve to a file."""


def image_dir() -> str:
    explicit = os.environ.get('LABEL_IMAGE_DIR')
    if explicit:
        return explicit
    memory = os.environ.get('LABEL_MEMORY_FILE', 'saved_labels.json')
    return os.path.join(os.path.dirname(memory), 'images')


def max_upload_bytes() -> int:
    raw = os.environ.get('LABEL_MAX_UPLOAD_MB')
    try:
        mb = float(raw) if raw else DEFAULT_MAX_UPLOAD_MB
    except ValueError:
        mb = DEFAULT_MAX_UPLOAD_MB
    return int(mb * 1024 * 1024)


def _sniff(data: bytes) -> Optional[str]:
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if data.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    head = data[:2048].lstrip(b'\xef\xbb\xbf \t\r\n')
    if head.startswith((b'<svg', b'<?xml', b'<!--', b'<!DOCTYPE svg')) and b'<svg' in data[:65536]:
        return 'svg'
    return None


def store_upload(data: bytes, filename: str = '') -> str:
    """Validate and store an upload; the type is sniffed from bytes, not the name."""
    if len(data) > max_upload_bytes():
        raise ImageTooLarge('Upload is too large')
    ext = _sniff(data)
    if ext is None:
        raise UnsupportedImage('Only PNG, JPEG and SVG images are supported')
    if ext != 'svg':
        try:
            with Image.open(io.BytesIO(data)) as probe:   # header only, no decode
                too_big = probe.width * probe.height > MAX_UPLOAD_PIXELS
        except Exception as exc:
            raise UnsupportedImage('Image could not be read') from exc
        if too_big:
            raise UnsupportedImage('Image dimensions are too large')
    name = f'{hashlib.sha256(data).hexdigest()}.{ext}'
    directory = image_dir()
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, name)
    if not os.path.exists(path):
        tmp = f'{path}.{os.getpid()}.{threading.get_ident()}.tmp'
        with open(tmp, 'wb') as fh:
            fh.write(data)
        os.replace(tmp, path)
    return f'upload:{name}'


def upload_path(name: str) -> str:
    """Path of a stored upload by file name; ImageMissing if absent or malformed."""
    if not _UPLOAD_RE.match(f'upload:{name}'):
        raise ImageMissing(name)
    path = os.path.join(image_dir(), name)
    if not os.path.isfile(path):
        raise ImageMissing(name)
    return path


def list_icons() -> list:
    try:
        names = sorted(f[:-4] for f in os.listdir(ICON_DIR) if f.endswith('.svg'))
    except OSError:
        return []
    return [{'name': n, 'url': f'/static/icons/{n}.svg'} for n in names]


def _read_ref(ref: str) -> tuple:
    """Return (bytes, is_svg) for a reference, or raise ImageMissing."""
    match = _UPLOAD_RE.match(ref or '')
    if match:
        path = upload_path(match.group(1))
        is_svg = path.endswith('.svg')
    else:
        match = _ICON_RE.match(ref or '')
        if not match:
            raise ImageMissing(ref)
        path = os.path.join(ICON_DIR, f'{match.group(1)}.svg')
        if not os.path.isfile(path):
            raise ImageMissing(ref)
        is_svg = True
    with open(path, 'rb') as fh:
        return fh.read(), is_svg


_VIEWBOX_RE = re.compile(rb'viewBox\s*=\s*"\s*[-\d.e]+[ ,]+[-\d.e]+[ ,]+([\d.e]+)[ ,]+([\d.e]+)\s*"')
_DIM_RE = re.compile(rb'<svg[^>]*?\s%s\s*=\s*"([\d.]+)(?:px)?"')


def _svg_aspect(data: bytes) -> float:
    """Height/width of an SVG from its viewBox or width/height (rasterized probe as fallback)."""
    head = data[:65536]
    pair = None
    match = _VIEWBOX_RE.search(head)
    if match:
        pair = (match.group(1), match.group(2))
    else:
        w, h = (re.search(_DIM_RE.pattern % name, head) for name in (b'width', b'height'))
        if w and h:
            pair = (w.group(1), h.group(1))
    if pair:
        try:
            w, h = float(pair[0]), float(pair[1])
            if w > 0 and h > 0:
                return h / w
        except ValueError:
            pass
    import cairosvg
    probe = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=data, output_width=64)))
    return probe.height / probe.width


def _check_budget(width_px: float, height_px: float) -> None:
    if width_px * height_px > MAX_RENDER_PIXELS:
        raise ImageTooLarge('Image would be rendered too large')


def load_image(ref: str, width_px: int) -> Image.Image:
    """Load a reference as an RGB image ``width_px`` wide, aspect kept, on white."""
    width_px = max(1, int(width_px))
    data, is_svg = _read_ref(ref)
    if is_svg:
        import cairosvg
        try:
            _check_budget(width_px, width_px * _svg_aspect(data))
            data = cairosvg.svg2png(bytestring=data, output_width=width_px)
        except ImageTooLarge:
            raise
        except Exception as exc:  # malformed SVG
            raise ImageMissing(ref) from exc
    try:
        img = Image.open(io.BytesIO(data))
        if not is_svg:
            _check_budget(width_px, width_px * img.height / img.width)
        img.load()
    except ImageTooLarge:
        raise
    except Exception as exc:
        raise ImageMissing(ref) from exc
    rgba = img.convert('RGBA')
    if rgba.width != width_px:
        height = max(1, round(rgba.height * width_px / rgba.width))
        rgba = rgba.resize((width_px, height), Image.Resampling.LANCZOS)
    flat = Image.new('RGB', rgba.size, 'white')
    flat.paste(rgba, mask=rgba.split()[3])
    return flat


def to_mono(img: Image.Image, mode: str = 'threshold', threshold: int = 128) -> Image.Image:
    """Convert to a pure black-and-white (mode ``1``) image."""
    gray = img.convert('L')
    if mode == 'dither':
        return gray.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
    return gray.point(lambda p: 255 if p >= threshold else 0).convert('1')


_cache: 'OrderedDict[tuple, Image.Image]' = OrderedDict()
_cache_lock = threading.Lock()


def load_mono(ref: str, width_px: int, mono: str = 'threshold',
              threshold: int = 128) -> Image.Image:
    """Cached load + mono conversion (LRU bounded to CACHE_LIMIT entries)."""
    key = (ref, int(width_px), mono, int(threshold))
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    result = to_mono(load_image(ref, width_px), mono, threshold)
    with _cache_lock:
        _cache[key] = result
        while len(_cache) > CACHE_LIMIT:
            _cache.popitem(last=False)
    return result


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def cache_size() -> int:
    return len(_cache)
