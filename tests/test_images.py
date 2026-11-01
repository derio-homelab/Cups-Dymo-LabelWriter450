"""Upload storage, icons, SVG loading and mono conversion (R5, R6, R7)."""

import io
from pathlib import Path

import pytest
from PIL import Image

from cups_dymo_label_printer import images

ICONS = Path(images.__file__).parent / "static" / "icons"


@pytest.fixture(autouse=True)
def image_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("LABEL_IMAGE_DIR", str(tmp_path / "imgs"))
    monkeypatch.delenv("LABEL_MAX_UPLOAD_MB", raising=False)
    images.clear_cache()
    return tmp_path / "imgs"


def encoded(fmt, size=(40, 20), color="black"):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, fmt)
    return buf.getvalue()


def gradient():
    img = Image.new("L", (256, 16))
    img.putdata([x for _ in range(16) for x in range(256)])
    return img


def test_store_png_and_jpeg(image_dir):
    for fmt, ext in (("PNG", "png"), ("JPEG", "jpg")):
        ref = images.store_upload(encoded(fmt), f"x.{ext}")
        assert ref.startswith("upload:") and ref.endswith(f".{ext}")
        assert (image_dir / ref.split(":", 1)[1]).exists()


def test_store_svg_sniffed_from_bytes_not_extension():
    svg = (ICONS / "star.svg").read_bytes()
    assert images.store_upload(svg, "whatever.bin").endswith(".svg")


def test_type_comes_from_bytes_not_filename():
    with pytest.raises(images.UnsupportedImage):
        images.store_upload(b"just text", "pretty.png")


def test_gif_is_rejected():
    gif = io.BytesIO()
    Image.new("P", (4, 4)).save(gif, "GIF")
    with pytest.raises(images.UnsupportedImage):
        images.store_upload(gif.getvalue(), "a.gif")


def test_size_limit(monkeypatch):
    monkeypatch.setenv("LABEL_MAX_UPLOAD_MB", "1")
    big = encoded("PNG")[:8] + b"\0" * (1024 * 1024 + 1)
    with pytest.raises(images.ImageTooLarge):
        images.store_upload(big, "big.png")


def test_content_addressed_dedup(image_dir):
    data = encoded("PNG")
    a = images.store_upload(data, "a.png")
    b = images.store_upload(data, "b.png")
    assert a == b
    assert len(list(image_dir.iterdir())) == 1


def test_default_image_dir_beside_memory_file(monkeypatch, tmp_path):
    monkeypatch.delenv("LABEL_IMAGE_DIR")
    monkeypatch.setenv("LABEL_MEMORY_FILE", str(tmp_path / "data" / "saved_labels.json"))
    assert images.image_dir() == str(tmp_path / "data" / "images")


def test_list_icons():
    icons = images.list_icons()
    assert len(icons) >= 20
    star = next(i for i in icons if i["name"] == "star")
    assert star["url"] == "/static/icons/star.svg"
    assert all(set(i) == {"name", "url"} for i in icons)


def test_load_icon_at_width_via_cairosvg():
    img = images.load_image("icon:star", width_px=200)
    assert img.width == 200
    assert img.height == 200          # lucide icons are square
    assert img.getbbox() is not None


def test_load_upload_scales_and_keeps_aspect():
    ref = images.store_upload(encoded("PNG", size=(100, 50)), "a.png")
    img = images.load_image(ref, width_px=40)
    assert img.size == (40, 20)


def test_missing_refs_raise():
    with pytest.raises(images.ImageMissing):
        images.load_image("upload:" + "0" * 64 + ".png", width_px=10)
    with pytest.raises(images.ImageMissing):
        images.load_image("icon:no-such-icon", width_px=10)
    with pytest.raises(images.ImageMissing):
        images.load_image("upload:../../etc/passwd", width_px=10)


def test_threshold_and_dither_are_mode_1_and_differ():
    g = gradient()
    t = images.to_mono(g, "threshold", 128)
    d = images.to_mono(g, "dither", 128)
    assert t.mode == "1" and d.mode == "1"
    assert t.tobytes() != d.tobytes()


def test_threshold_level_matters():
    g = gradient()
    low = images.to_mono(g, "threshold", 50)
    high = images.to_mono(g, "threshold", 200)
    assert sum(high.convert("L").histogram()[:128]) > sum(low.convert("L").histogram()[:128])


def test_render_cache_is_lru_bounded():
    ref = images.store_upload(encoded("PNG", size=(30, 30)), "a.png")
    first = images.load_mono(ref, 20, "threshold", 128)
    assert images.load_mono(ref, 20, "threshold", 128) is first
    for w in range(1, 80):
        images.load_mono(ref, w, "threshold", 128)
    assert images.cache_size() <= 64


def test_decompression_bomb_upload_refused():
    buf = io.BytesIO()
    Image.new("1", (20000, 20000), 1).save(buf, "PNG")   # tiny file, 400 Mpx
    assert len(buf.getvalue()) < 5 * 1024 * 1024
    with pytest.raises(images.UnsupportedImage):
        images.store_upload(buf.getvalue(), "bomb.png")


def test_load_refuses_over_pixel_budget_raster():
    ref = images.store_upload(encoded("PNG", size=(10, 1000)), "tall.png")
    with pytest.raises(images.ImageTooLarge):
        images.load_image(ref, width_px=2000)    # 2000 x 200000 px


def test_load_refuses_over_pixel_budget_svg():
    svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1000"><rect width="1" height="1000"/></svg>'
    ref = images.store_upload(svg, "tall.svg")
    with pytest.raises(images.ImageTooLarge):
        images.load_image(ref, width_px=2000)
