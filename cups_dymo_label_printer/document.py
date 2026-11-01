"""
Label document model (v2): blocks on a canvas, validation, conversion helpers.

Coordinates are millimetres from the top-left of the label *as designed*
(after orientation). ``width_mm`` of ``None`` means "label width minus margins";
``y_mm`` of ``None`` means "vertically centred".
"""

import json
from dataclasses import dataclass, field
from typing import Any, Optional, Union

from .config import (
    DEFAULT_FONT_BOLD,
    DEFAULT_FONT_FAMILY,
    DEFAULT_LABEL_SIZE,
    LABEL_SIZES,
)

DEFAULT_MARGIN_MM = 2
DEFAULT_THRESHOLD = 128
ORIENTATIONS = ('portrait', 'landscape')
ALIGNMENTS = ('left', 'center', 'right')
MONO_MODES = ('threshold', 'dither')
V1_DPI = 300  # v1 payloads carried font size in pixels at 300 DPI


def pt_to_px(pt: float, dpi: int) -> int:
    return round(pt * dpi / 72)


def px_to_pt(px: float, dpi: int = V1_DPI) -> float:
    return px * 72 / dpi


def _number(value: Any, name: str, *, positive: bool = False,
            nullable: bool = False) -> Optional[float]:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


@dataclass
class TextBlock:
    id: str = ''
    text: str = ''
    x_mm: float = DEFAULT_MARGIN_MM
    y_mm: Optional[float] = None
    width_mm: Optional[float] = None
    align: str = 'center'
    font_family: str = DEFAULT_FONT_FAMILY
    font_size_pt: float = 12
    bold: bool = False
    italic: bool = False
    underline: bool = False
    shrink_to_fit: bool = False
    type: str = field(default='text', init=False)

    def validate(self) -> None:
        if self.align not in ALIGNMENTS:
            raise ValueError(f"Unknown alignment: {self.align}")
        _number(self.font_size_pt, 'font_size_pt', positive=True)
        _number(self.x_mm, 'x_mm')
        _number(self.y_mm, 'y_mm', nullable=True)
        _number(self.width_mm, 'width_mm', positive=True, nullable=True)
        if not isinstance(self.text, str):
            raise ValueError("text must be a string")

    def to_json(self) -> dict:
        return {
            'type': 'text', 'id': self.id, 'text': self.text,
            'x_mm': self.x_mm, 'y_mm': self.y_mm, 'width_mm': self.width_mm,
            'align': self.align, 'font_family': self.font_family,
            'font_size_pt': self.font_size_pt, 'bold': self.bold,
            'italic': self.italic, 'underline': self.underline,
            'shrink_to_fit': self.shrink_to_fit,
        }


@dataclass
class ImageBlock:
    id: str = ''
    src: str = ''
    x_mm: float = DEFAULT_MARGIN_MM
    y_mm: float = DEFAULT_MARGIN_MM
    width_mm: float = 20
    mono: str = 'threshold'
    threshold: int = DEFAULT_THRESHOLD
    type: str = field(default='image', init=False)

    def validate(self) -> None:
        if not isinstance(self.src, str) or not self.src:
            raise ValueError("image src is required")
        if self.mono not in MONO_MODES:
            raise ValueError(f"Unknown mono mode: {self.mono}")
        _number(self.threshold, 'threshold')
        if not 0 <= self.threshold <= 255:
            raise ValueError("threshold must be between 0 and 255")
        _number(self.x_mm, 'x_mm')
        _number(self.y_mm, 'y_mm')
        _number(self.width_mm, 'width_mm', positive=True)

    def to_json(self) -> dict:
        return {
            'type': 'image', 'id': self.id, 'src': self.src,
            'x_mm': self.x_mm, 'y_mm': self.y_mm, 'width_mm': self.width_mm,
            'mono': self.mono, 'threshold': self.threshold,
        }


Block = Union[TextBlock, ImageBlock]
_BLOCK_TYPES = {'text': TextBlock, 'image': ImageBlock}


def default_orientation(label_size: str) -> str:
    size = LABEL_SIZES[label_size]
    return 'portrait' if size['width_mm'] <= size['height_mm'] else 'landscape'


def _block_from_json(raw: Any, index: int) -> Block:
    if not isinstance(raw, dict):
        raise ValueError("block must be an object")
    kind = raw.get('type')
    cls = _BLOCK_TYPES.get(kind)
    if cls is None:
        raise ValueError(f"Unknown block type: {kind}")
    names = set(cls.__dataclass_fields__) - {'type'}
    block = cls(**{k: v for k, v in raw.items() if k in names})
    if not block.id:
        block.id = f"b{index + 1}"
    block.validate()
    return block


@dataclass
class LabelDoc:
    label_size: str = DEFAULT_LABEL_SIZE
    orientation: str = ''
    copies: int = 1
    name: str = ''
    blocks: list = field(default_factory=list)

    @classmethod
    def from_json(cls, raw: Any) -> 'LabelDoc':
        if not isinstance(raw, dict):
            raise ValueError("document must be an object")
        label_size = raw.get('label_size', DEFAULT_LABEL_SIZE)
        if label_size not in LABEL_SIZES:
            raise ValueError(f"Unknown label size: {label_size}")
        orientation = raw.get('orientation') or default_orientation(label_size)
        if orientation not in ORIENTATIONS:
            raise ValueError(f"Unknown orientation: {orientation}")
        blocks = raw.get('blocks', [])
        if not isinstance(blocks, list):
            raise ValueError("blocks must be a list")
        try:
            copies = int(raw.get('copies', 1))
        except (TypeError, ValueError):
            raise ValueError("copies must be an integer") from None
        return cls(
            label_size=label_size,
            orientation=orientation,
            copies=copies,
            name=str(raw.get('name') or ''),
            blocks=[_block_from_json(b, i) for i, b in enumerate(blocks)],
        )

    def to_json(self) -> dict:
        return {
            'label_size': self.label_size,
            'orientation': self.orientation,
            'copies': self.copies,
            'name': self.name,
            'blocks': [b.to_json() for b in self.blocks],
        }


def canvas_mm(doc: LabelDoc) -> tuple:
    size = LABEL_SIZES[doc.label_size]
    short, long_ = sorted((size['width_mm'], size['height_mm']))
    return (short, long_) if doc.orientation == 'portrait' else (long_, short)


def from_flat(payload: dict) -> LabelDoc:
    """Convert a v1 flat payload (font size in pixels at 300 DPI) to a document."""
    label_size = payload.get('label_size', DEFAULT_LABEL_SIZE)
    if label_size not in LABEL_SIZES:
        raise ValueError(f"Unknown label size: {label_size}")
    block = TextBlock(
        id='b1',
        text=payload.get('text', ''),
        align=payload.get('align', 'center'),
        font_family=DEFAULT_FONT_FAMILY,
        font_size_pt=px_to_pt(int(payload.get('font_size', 40))),
        bold=DEFAULT_FONT_BOLD,
    )
    block.validate()
    return LabelDoc(
        label_size=label_size,
        orientation=default_orientation(label_size),
        copies=int(payload.get('copies', 1)),
        blocks=[block],
    )


def content_key(doc: LabelDoc) -> str:
    """Canonical JSON of stock, orientation and blocks (ids and copies excluded)."""
    blocks = []
    for block in doc.blocks:
        data = block.to_json()
        data.pop('id', None)
        blocks.append(data)
    return json.dumps(
        {'label_size': doc.label_size, 'orientation': doc.orientation, 'blocks': blocks},
        sort_keys=True, separators=(',', ':'),
    )
