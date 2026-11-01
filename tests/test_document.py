"""Label document model, validation and v1 conversion helpers (R2, R12)."""

import pytest

from cups_dymo_label_printer import document
from cups_dymo_label_printer.document import (
    ImageBlock, LabelDoc, TextBlock, canvas_mm, content_key, from_flat, pt_to_px,
)


def _doc(**over):
    base = {"label_size": "11354", "blocks": [{"type": "text", "text": "Hi"}]}
    base.update(over)
    return base


def test_unknown_stock_is_rejected():
    with pytest.raises(ValueError, match="Unknown label size: X"):
        LabelDoc.from_json(_doc(label_size="X"))


def test_orientation_validated_and_defaults_to_stock_shape():
    assert LabelDoc.from_json(_doc(label_size="30252")).orientation == "portrait"
    assert LabelDoc.from_json(_doc(label_size="11354")).orientation == "landscape"
    assert LabelDoc.from_json(_doc(orientation="portrait")).orientation == "portrait"
    with pytest.raises(ValueError, match="orientation"):
        LabelDoc.from_json(_doc(orientation="sideways"))


def test_block_types():
    doc = LabelDoc.from_json(_doc(blocks=[
        {"type": "text", "text": "a", "font_size_pt": 9.6},
        {"type": "image", "src": "icon:star", "x_mm": 3, "y_mm": 4, "width_mm": 10},
    ]))
    assert isinstance(doc.blocks[0], TextBlock)
    assert doc.blocks[0].font_size_pt == 9.6
    assert isinstance(doc.blocks[1], ImageBlock)
    assert doc.blocks[1].mono == "threshold" and doc.blocks[1].threshold == 128
    assert doc.blocks[0].id != doc.blocks[1].id
    with pytest.raises(ValueError, match="Unknown block type: video"):
        LabelDoc.from_json(_doc(blocks=[{"type": "video"}]))


@pytest.mark.parametrize("bad", [
    {"type": "text", "text": "a", "font_size_pt": "big"},
    {"type": "text", "text": "a", "font_size_pt": 0},
    {"type": "text", "text": "a", "align": "justify"},
    {"type": "image", "src": "icon:x", "mono": "gray"},
    {"type": "image", "src": "icon:x", "threshold": 300},
    {"type": "image", "src": ""},
])
def test_bad_block_values_rejected(bad):
    with pytest.raises(ValueError):
        LabelDoc.from_json(_doc(blocks=[bad]))


def test_json_round_trip():
    raw = _doc(label_size="30252", orientation="landscape", copies=3, name="Jar", blocks=[
        {"type": "text", "id": "b1", "text": "Flour", "x_mm": 2, "y_mm": 2, "width_mm": None,
         "align": "left", "font_family": "Liberation Sans", "font_size_pt": 14,
         "bold": True, "italic": False, "underline": True, "shrink_to_fit": True},
        {"type": "image", "id": "b2", "src": "upload:ab.png", "x_mm": 60, "y_mm": 4,
         "width_mm": 20, "mono": "dither", "threshold": 90},
    ])
    doc = LabelDoc.from_json(raw)
    assert doc.to_json() == raw


def test_canvas_mm_per_orientation():
    assert canvas_mm(LabelDoc.from_json(_doc(label_size="30252", orientation="portrait"))) == (28, 89)
    assert canvas_mm(LabelDoc.from_json(_doc(label_size="30252", orientation="landscape"))) == (89, 28)
    assert canvas_mm(LabelDoc.from_json(_doc(label_size="11354"))) == (57, 32)


def test_from_flat_builds_one_centred_text_block():
    doc = from_flat({"text": "Hello", "label_size": "11354", "font_size": 40, "align": "right"})
    (block,) = doc.blocks
    assert isinstance(block, TextBlock)
    assert (block.text, block.align, block.bold) == ("Hello", "right", True)
    assert block.font_family == "DejaVu Sans"
    assert block.font_size_pt == pytest.approx(9.6)
    assert block.y_mm is None
    assert pt_to_px(9.6, 300) == 40


def test_from_flat_defaults():
    doc = from_flat({"text": "x"})
    assert doc.label_size == "11354"
    assert doc.blocks[0].align == "center"
    assert pt_to_px(doc.blocks[0].font_size_pt, 300) == 40


def test_content_key_ignores_ids_and_copies():
    a = LabelDoc.from_json(_doc(copies=1, blocks=[{"type": "text", "id": "x", "text": "Hi"}]))
    b = LabelDoc.from_json(_doc(copies=5, blocks=[{"type": "text", "id": "y", "text": "Hi"}]))
    c = LabelDoc.from_json(_doc(blocks=[{"type": "text", "id": "x", "text": "Ho"}]))
    assert content_key(a) == content_key(b)
    assert content_key(a) != content_key(c)


def test_defaults_are_module_constants():
    assert document.DEFAULT_MARGIN_MM == 2
    assert document.DEFAULT_THRESHOLD == 128


@pytest.mark.parametrize("width", [0, -5, 90, 1e9])
def test_image_width_bounded_by_label_long_edge(width):
    with pytest.raises(ValueError, match="width_mm"):
        LabelDoc.from_json(_doc(label_size="30252", blocks=[
            {"type": "image", "src": "icon:star", "width_mm": width}]))


def test_image_width_at_long_edge_ok():
    LabelDoc.from_json(_doc(label_size="30252", blocks=[
        {"type": "image", "src": "icon:star", "width_mm": 89}]))


def test_font_size_capped_at_label_long_edge_in_points():
    cap = 89 * 72 / 25.4
    LabelDoc.from_json(_doc(label_size="30252", blocks=[
        {"type": "text", "text": "a", "font_size_pt": cap}]))
    with pytest.raises(ValueError, match="font_size_pt"):
        LabelDoc.from_json(_doc(label_size="30252", blocks=[
            {"type": "text", "text": "a", "font_size_pt": cap + 1}]))
    with pytest.raises(ValueError, match="font_size_pt"):
        from_flat({"text": "a", "font_size": 10 ** 6})


@pytest.mark.parametrize("blocks,match", [
    ([{"type": "text", "text": "x" * 2001}], "text"),
    ([{"type": "text", "text": "\n" * 50}], "lines"),
    ([{"type": "text", "text": "a"}] * 31, "blocks"),
])
def test_size_caps(blocks, match):
    with pytest.raises(ValueError, match=match):
        LabelDoc.from_json(_doc(blocks=blocks))


def test_size_caps_boundaries_ok():
    LabelDoc.from_json(_doc(blocks=[{"type": "text", "text": "x" * 2000}]))
    LabelDoc.from_json(_doc(blocks=[{"type": "text", "text": "\n" * 49}]))
    LabelDoc.from_json(_doc(blocks=[{"type": "text", "text": "a"}] * 30))
