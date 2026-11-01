"""
Label image generation.

``render`` turns a ``LabelDoc`` into a pure black-and-white (mode ``1``) image
plus per-block layout results; ``create_label_image`` is the v1 single-text
wrapper kept for existing callers.
"""

from dataclasses import dataclass
from typing import Literal

from PIL import Image, ImageDraw

from . import fonts, images
from .config import DEFAULT_DPI, DEFAULT_FONT_SIZE, DEFAULT_LABEL_SIZE
from .document import (
    DEFAULT_MARGIN_MM,
    ImageBlock,
    LabelDoc,
    TextBlock,
    canvas_mm,
    from_flat,
    pt_to_px,
)

AlignmentType = Literal['left', 'center', 'right']

MIN_SHRINK_PT = 6
SHRINK_ITERATIONS = 12
TEXT_RASTER_BUDGET_FACTOR = 4   # per block: sum(line px area) <= 4 x canvas area
TEXT_THRESHOLD = 128


@dataclass
class RenderResult:
    image: Image.Image
    blocks: list


@dataclass
class TextLayout:
    """Pure layout of one text block (no drawing): lines and where they go."""
    lines: list
    positions: list          # (x_px, y_px) of each line's top-left
    widths: list             # measured px width of each line
    font: object
    resolved: fonts.ResolvedFont
    size_pt: float
    ascent: int
    descent: int
    box: tuple               # (x, y, w, h) in px
    overflow: bool
    over_budget: bool = False


def _mm_to_px(mm: float, dpi: int) -> float:
    return mm * dpi / 25.4


def _layout_text_block(block: TextBlock, canvas_px: tuple, dpi: int,
                       size_pt: float) -> TextLayout:
    canvas_w, canvas_h = canvas_px
    resolved = fonts.resolve(block.font_family, block.bold, block.italic)
    font = fonts.open_font(resolved, max(1, pt_to_px(size_pt, dpi)))
    ascent, descent = font.getmetrics()
    line_h = ascent + descent

    lines = block.text.split('\n')
    widths = [font.getlength(line) for line in lines]
    box_x = _mm_to_px(block.x_mm, dpi)
    if block.width_mm is None:
        box_w = max(1.0, canvas_w - box_x - _mm_to_px(DEFAULT_MARGIN_MM, dpi))
    else:
        box_w = _mm_to_px(block.width_mm, dpi)
    total_h = line_h * len(lines)
    if block.y_mm is None:
        box_y = (canvas_h - total_h) / 2
    else:
        box_y = _mm_to_px(block.y_mm, dpi)

    positions = []
    for i, width in enumerate(widths):
        if block.align == 'left':
            x = box_x
        elif block.align == 'right':
            x = box_x + box_w - width
        else:
            x = box_x + (box_w - width) / 2
        positions.append((x, box_y + i * line_h))

    over_budget = (
        sum(widths) * line_h > TEXT_RASTER_BUDGET_FACTOR * canvas_w * canvas_h
    )
    overflow = (
        over_budget
        or max(widths) > box_w + 0.5
        or total_h > canvas_h + 0.5
        or box_y < -0.5
        or box_y + total_h > canvas_h + 0.5
        or box_x < -0.5
        or box_x + box_w > canvas_w + 0.5
        or min(x for x, _ in positions) < -0.5
        or max(x + w for (x, _), w in zip(positions, widths)) > canvas_w + 0.5
    )
    return TextLayout(lines, positions, widths, font, resolved, size_pt,
                      ascent, descent, (box_x, box_y, box_w, total_h), overflow,
                      over_budget)


def _fit_text_block(block: TextBlock, canvas_px: tuple, dpi: int) -> TextLayout:
    """Layout at the requested size, or (shrink_to_fit) the largest size that fits.

    A bounded binary search over [MIN_SHRINK_PT, requested size]; fitting is
    monotone in size, so SHRINK_ITERATIONS halvings are enough.
    """
    layout = _layout_text_block(block, canvas_px, dpi, block.font_size_pt)
    if not (block.shrink_to_fit and layout.overflow) or block.font_size_pt <= MIN_SHRINK_PT:
        return layout
    smallest = _layout_text_block(block, canvas_px, dpi, MIN_SHRINK_PT)
    if smallest.overflow:
        return smallest
    lo, hi, best = MIN_SHRINK_PT, block.font_size_pt, smallest
    for _ in range(SHRINK_ITERATIONS):
        mid = (lo + hi) / 2
        candidate = _layout_text_block(block, canvas_px, dpi, mid)
        if candidate.overflow:
            hi = mid
        else:
            lo, best = mid, candidate
    return best


def _draw_text(draw: ImageDraw.ImageDraw, block: TextBlock, layout: TextLayout,
               canvas_px: tuple) -> None:
    """Draw visible lines only; an over-budget block is not drawn at all."""
    if layout.over_budget:
        return
    canvas_w, canvas_h = canvas_px
    line_h = layout.ascent + layout.descent
    thickness = max(1, round(layout.font.size / 15)) if hasattr(layout.font, 'size') else 1
    for line, (x, y), width in zip(layout.lines, layout.positions, layout.widths):
        if x + width < 0 or x > canvas_w or y + line_h < 0 or y > canvas_h:
            continue    # wholly off-canvas
        draw.text((x, y), line, fill=0, font=layout.font)
        if block.underline and line:
            line_y = y + layout.ascent + layout.descent / 2
            draw.line([(x, line_y), (x + width, line_y)], fill=0, width=thickness)


def _bbox_mm(box: tuple, dpi: int) -> list:
    return [round(v * 25.4 / dpi, 3) for v in box]


def _draw_image(canvas: Image.Image, block: ImageBlock, dpi: int) -> dict:
    width_px = max(1, min(round(_mm_to_px(block.width_mm, dpi)), canvas.width))
    result = {
        'id': block.id, 'overflow': False, 'font_substituted': False, 'missing': False,
        'bbox_mm': [block.x_mm, block.y_mm, block.width_mm, block.width_mm],
    }
    try:
        mono = images.load_mono(block.src, width_px, block.mono, block.threshold)
    except images.ImageMissing:
        result['missing'] = True
        return result
    left, top = round(_mm_to_px(block.x_mm, dpi)), round(_mm_to_px(block.y_mm, dpi))
    canvas.paste(mono.convert('L'), (left, top))
    result['overflow'] = (left < 0 or top < 0 or left + mono.width > canvas.width
                          or top + mono.height > canvas.height)
    result['bbox_mm'] = _bbox_mm((_mm_to_px(block.x_mm, dpi), _mm_to_px(block.y_mm, dpi),
                                  mono.width, mono.height), dpi)
    return result


def render(doc: LabelDoc, dpi: int = DEFAULT_DPI) -> RenderResult:
    """Render a document to a mode-``1`` image and per-block layout results."""
    width_mm, height_mm = canvas_mm(doc)
    canvas_px = (int(width_mm * dpi / 25.4), int(height_mm * dpi / 25.4))
    canvas = Image.new('L', canvas_px, 255)
    draw = ImageDraw.Draw(canvas)

    results = []
    for block in doc.blocks:
        if isinstance(block, TextBlock):
            layout = _fit_text_block(block, canvas_px, dpi)
            _draw_text(draw, block, layout, canvas_px)
            results.append({
                'id': block.id,
                'bbox_mm': _bbox_mm(layout.box, dpi),
                'overflow': layout.overflow,
                'font_substituted': layout.resolved.substituted,
                'missing': False,
                'size_pt': layout.size_pt,
            })
        elif isinstance(block, ImageBlock):
            results.append(_draw_image(canvas, block, dpi))

    mono = canvas.point(lambda p: 255 if p >= TEXT_THRESHOLD else 0).convert('1')
    return RenderResult(mono, results)


def create_label_image(
    text: str,
    label_size: str = DEFAULT_LABEL_SIZE,
    font_size: int = DEFAULT_FONT_SIZE,
    align: AlignmentType = 'center',
    dpi: int = DEFAULT_DPI
) -> Image.Image:
    """
    Create an RGB label image for single-text input (v1 contract).

    ``font_size`` is in pixels at ``dpi``. Raises ValueError for an unknown
    label size.
    """
    doc = from_flat(
        {'text': text, 'label_size': label_size, 'font_size': font_size, 'align': align},
        dpi=dpi,
    )
    return render(doc, dpi).image.convert('RGB')
