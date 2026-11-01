"""Renderer: blocks, multi-line, underline, shrink-to-fit, overflow, mode 1 (R2, R4, R7)."""

from pathlib import Path

import pytest
from PIL import Image, ImageChops

from cups_dymo_label_printer import fonts
from cups_dymo_label_printer.config import DEFAULT_DPI, LABEL_SIZES
from cups_dymo_label_printer.document import LabelDoc
from cups_dymo_label_printer.label_generator import create_label_image, render

FIXTURES = Path(__file__).parent / "fixtures" / "fonts"


@pytest.fixture(autouse=True)
def fixture_fonts(monkeypatch):
    monkeypatch.setenv("LABEL_FONT_DIRS", str(FIXTURES))
    fonts.reset_cache()
    yield
    fonts.reset_cache()


def text_block(text="Hello", **over):
    block = {"type": "text", "id": "t", "text": text, "font_family": "Liberation Sans",
             "font_size_pt": 12, "align": "left", "x_mm": 2, "y_mm": 2}
    block.update(over)
    return block


def doc_of(*blocks, label_size="11354", orientation=None):
    raw = {"label_size": label_size, "blocks": list(blocks)}
    if orientation:
        raw["orientation"] = orientation
    return LabelDoc.from_json(raw)


def dark(img):
    return sum(img.convert("L").histogram()[:128])


def ink_bbox(img):
    return ImageChops.invert(img.convert("L")).getbbox()


@pytest.mark.parametrize("label_size", list(LABEL_SIZES))
@pytest.mark.parametrize("orientation", ["portrait", "landscape"])
def test_render_is_mode_1_at_canvas_size(label_size, orientation):
    result = render(doc_of(text_block(), label_size=label_size, orientation=orientation))
    w, h = LABEL_SIZES[label_size]["width_mm"], LABEL_SIZES[label_size]["height_mm"]
    short, long_ = sorted((w, h))
    cw, ch = (short, long_) if orientation == "portrait" else (long_, short)
    assert result.image.mode == "1"
    assert result.image.size == (int(cw * DEFAULT_DPI / 25.4), int(ch * DEFAULT_DPI / 25.4))


def test_multi_line_block_is_taller_than_single_line():
    one = render(doc_of(text_block("A"))).blocks[0]
    three = render(doc_of(text_block("A\nB\nC"))).blocks[0]
    h1, h3 = one["bbox_mm"][3], three["bbox_mm"][3]
    assert h3 == pytest.approx(3 * h1, rel=0.02)
    assert ink_bbox(render(doc_of(text_block("A\nB\nC"))).image) is not None


def test_mixed_sizes_have_proportional_heights():
    result = render(doc_of(
        text_block("Big", id="a", font_size_pt=24, y_mm=1),
        text_block("Small", id="b", font_size_pt=8, y_mm=20),
        label_size="30323", orientation="landscape",
    ))
    big, small = (b["bbox_mm"][3] for b in result.blocks)
    assert big / small == pytest.approx(3.0, rel=0.1)


def test_underline_adds_pixels_below_the_text():
    plain = render(doc_of(text_block("Hamburg", underline=False))).image
    under = render(doc_of(text_block("Hamburg", underline=True))).image
    assert dark(under) > dark(plain)
    diff = ImageChops.difference(plain.convert("L"), under.convert("L"))
    left, top, right, bottom = diff.getbbox()
    assert (bottom - top) <= 12            # a thin strip
    assert (right - left) > 100            # spanning the text


def test_overflow_reported_and_cleared_by_shrink_to_fit():
    big = text_block("Hello World", font_size_pt=60)
    over = render(doc_of(big)).blocks[0]
    assert over["overflow"] is True
    fitted = render(doc_of(dict(big, shrink_to_fit=True))).blocks[0]
    assert fitted["overflow"] is False
    assert 6 <= fitted["size_pt"] < 60


def test_shrink_stops_at_six_points():
    result = render(doc_of(text_block("W" * 80, font_size_pt=30, shrink_to_fit=True))).blocks[0]
    assert result["overflow"] is True
    assert result["size_pt"] == 6


def test_unknown_family_reports_font_substituted():
    result = render(doc_of(text_block(font_family="Comic Nope"))).blocks[0]
    assert result["font_substituted"] is True
    assert render(doc_of(text_block())).blocks[0]["font_substituted"] is False


def test_block_result_shape():
    (block,) = render(doc_of(text_block())).blocks
    assert set(block) >= {"id", "bbox_mm", "overflow", "font_substituted", "missing"}
    assert block["id"] == "t" and block["missing"] is False
    assert len(block["bbox_mm"]) == 4


def test_vertical_centering_when_y_is_none():
    result = render(doc_of(text_block(y_mm=None)))
    _, y, _, h = result.blocks[0]["bbox_mm"]
    assert y + h / 2 == pytest.approx(32 / 2, abs=0.3)


def test_alignment_places_text_within_box():
    left = ink_bbox(render(doc_of(text_block("Hi", align="left"))).image)
    right = ink_bbox(render(doc_of(text_block("Hi", align="right"))).image)
    assert left[0] < right[0]


def test_create_label_image_wrapper_contract():
    image = create_label_image("Hello World")
    assert image.mode == "RGB"
    assert image.getpixel((0, 0)) == (255, 255, 255)
    assert sum(image.convert("L").histogram()[1:255]) == 0
    assert image.size == (int(57 * 300 / 25.4), int(32 * 300 / 25.4))


def test_icon_block_is_drawn_pure_mono():
    img_block = {"type": "image", "id": "i", "src": "icon:star", "x_mm": 5, "y_mm": 5, "width_mm": 15}
    result = render(doc_of(img_block))
    assert result.image.mode == "1"
    assert dark(result.image) > 100
    info = result.blocks[0]
    assert info["missing"] is False
    assert info["bbox_mm"][:2] == [5, 5]
    assert info["bbox_mm"][2] == pytest.approx(15, abs=0.1)
    assert info["bbox_mm"][3] == pytest.approx(15, abs=0.1)


def test_missing_image_draws_nothing_and_is_flagged(monkeypatch, tmp_path):
    monkeypatch.setenv("LABEL_IMAGE_DIR", str(tmp_path))
    gone = {"type": "image", "id": "i", "src": "upload:" + "a" * 64 + ".png",
            "x_mm": 5, "y_mm": 5, "width_mm": 15}
    result = render(doc_of(gone))
    assert result.blocks[0]["missing"] is True
    assert dark(result.image) == 0


def test_image_width_clamped_to_canvas_width():
    block = {"type": "image", "id": "i", "src": "icon:star", "x_mm": 0, "y_mm": 0, "width_mm": 57}
    # 57 mm is the full canvas width of 11354 landscape: allowed, never wider than the canvas
    result = render(doc_of(block))
    assert result.image.size[0] == int(57 * 300 / 25.4)
    assert result.blocks[0]["missing"] is False


def test_shrink_to_fit_is_a_bounded_search(monkeypatch):
    from cups_dymo_label_printer import label_generator as lg
    calls = []
    real = lg._layout_text_block
    monkeypatch.setattr(lg, "_layout_text_block",
                        lambda *a, **k: calls.append(1) or real(*a, **k))
    result = render(doc_of(text_block("Hello World", font_size_pt=150, shrink_to_fit=True)))
    assert result.blocks[0]["overflow"] is False
    assert len(calls) <= 15
    # and it lands near the largest size that fits (not far below it)
    size = result.blocks[0]["size_pt"]
    probe = render(doc_of(text_block("Hello World", font_size_pt=size + 1)))
    assert probe.blocks[0]["overflow"] is True


def test_hostile_doc_renders_fast_without_exceptions(client_app=None):
    import time
    blocks = [text_block("\n".join(["W" * 10] * 50), id=f"b{i}", font_size_pt=286, y_mm=0)
              for i in range(30)]
    doc = doc_of(*blocks, label_size="30323")
    start = time.monotonic()
    result = render(doc)
    assert time.monotonic() - start < 2
    assert all(b["overflow"] for b in result.blocks)
    assert dark(result.image) == 0       # over-budget blocks are not drawn


def test_offcanvas_lines_are_skipped(monkeypatch):
    from cups_dymo_label_printer import label_generator as lg
    drawn = []
    real = lg.ImageDraw.ImageDraw.text
    monkeypatch.setattr(lg.ImageDraw.ImageDraw, "text",
                        lambda self, xy, *a, **k: drawn.append(xy) or real(self, xy, *a, **k))
    # 3 lines, the box starts far below the canvas bottom: nothing visible
    render(doc_of(text_block("a\nb\nc", y_mm=100)))
    assert drawn == []


@pytest.mark.parametrize("x_mm", [50, -30])
def test_horizontal_extent_flags_overflow(x_mm):
    result = render(doc_of(text_block("Hello", x_mm=x_mm, align="left")))
    assert result.blocks[0]["overflow"] is True


def test_centered_block_straddling_left_edge_overflows():
    assert render(doc_of(text_block("Hi", x_mm=-30, align="center"))).blocks[0]["overflow"] is True


def test_default_width_is_canvas_minus_x_minus_margin():
    result = render(doc_of(text_block("Hi", x_mm=20)))
    x, _, w, _ = result.blocks[0]["bbox_mm"]
    assert x == pytest.approx(20, abs=0.1)
    assert w == pytest.approx(57 - 20 - 2, abs=0.1)


def test_image_leaving_canvas_overflows():
    inside = {"type": "image", "id": "i", "src": "icon:star", "x_mm": 5, "y_mm": 5, "width_mm": 15}
    assert render(doc_of(inside)).blocks[0]["overflow"] is False
    for x, y in ((50, 5), (5, 25), (-5, 5)):
        out = dict(inside, x_mm=x, y_mm=y)
        assert render(doc_of(out)).blocks[0]["overflow"] is True
