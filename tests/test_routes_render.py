"""Routes: /fonts, /icons, /images, /render, /preview compat, /print with a doc."""

import base64
import importlib
import io
from pathlib import Path

import pytest
from PIL import Image

from cups_dymo_label_printer import fonts

FIXTURES = Path(__file__).parent / "fixtures" / "fonts"


class _Printer:
    def __init__(self):
        self.calls = []

    def print_image(self, image, label_size, copies=1, job_title="Label"):
        self.calls.append((image.size, label_size, copies))
        return 7


@pytest.fixture()
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("LABEL_FONT_DIRS", str(FIXTURES))
    monkeypatch.setenv("LABEL_MEMORY_FILE", str(tmp_path / "saved_labels.json"))
    monkeypatch.setenv("LABEL_IMAGE_DIR", str(tmp_path / "images"))
    monkeypatch.setenv("LABEL_MAX_UPLOAD_MB", "1")
    fonts.reset_cache()
    import cups_dymo_label_printer.web_app as web_app
    importlib.reload(web_app)
    web_app.app.config["TESTING"] = True
    web_app.printer_service = _Printer()
    yield web_app.app.test_client(), web_app
    fonts.reset_cache()


def png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "black").save(buf, "PNG")
    return buf.getvalue()


def upload(client, data, name="a.png"):
    return client.post("/images", data={"file": (io.BytesIO(data), name)},
                       content_type="multipart/form-data")


DOC = {
    "label_size": "30252",
    "blocks": [
        {"type": "text", "id": "t1", "text": "Flour\nT55", "font_family": "Liberation Sans",
         "font_size_pt": 14, "bold": True, "x_mm": 2, "y_mm": 2},
        {"type": "image", "id": "i1", "src": "icon:star", "x_mm": 2, "y_mm": 40, "width_mm": 12},
    ],
}


def test_fonts_lists_fixture_family(client):
    c, _ = client
    assert c.get("/fonts").get_json() == [
        {"family": "Liberation Sans", "styles": ["regular", "bold"]}
    ]


def test_icons_lists_at_least_twenty(client):
    c, _ = client
    icons = c.get("/icons").get_json()
    assert len(icons) >= 20
    assert {"name", "url"} == set(icons[0])
    assert c.get(icons[0]["url"]).status_code == 200


def test_upload_roundtrip(client):
    c, _ = client
    resp = upload(c, png_bytes())
    assert resp.status_code == 200
    ref = resp.get_json()["ref"]
    assert ref.startswith("upload:")
    served = c.get("/images/" + ref.split(":", 1)[1])
    assert served.status_code == 200
    assert served.data == png_bytes()
    assert served.mimetype == "image/png"


def test_upload_over_limit_is_413(client):
    c, _ = client
    resp = upload(c, b"\x89PNG\r\n\x1a\n" + b"0" * (1024 * 1024 + 10))
    assert resp.status_code == 413
    assert resp.get_json()["success"] is False


def test_upload_wrong_type_is_400(client):
    c, _ = client
    resp = upload(c, b"plain text", "a.txt")
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False


def test_upload_without_file_is_400(client):
    c, _ = client
    assert c.post("/images", data={}, content_type="multipart/form-data").status_code == 400


def test_missing_image_is_404(client):
    c, _ = client
    assert c.get("/images/" + "0" * 64 + ".png").status_code == 404
    assert c.get("/images/..%2Fsecret").status_code == 404


def test_render_two_block_doc(client):
    c, _ = client
    resp = c.post("/render", json=DOC)
    data = resp.get_json()
    assert resp.status_code == 200 and data["success"] is True
    assert (data["width_mm"], data["height_mm"]) == (28, 89)
    assert data["image"].startswith("data:image/png;base64,")
    png = Image.open(io.BytesIO(base64.b64decode(data["image"].split(",", 1)[1])))
    assert png.mode == "1" and png.size == (int(28 * 300 / 25.4), int(89 * 300 / 25.4))
    assert [b["id"] for b in data["blocks"]] == ["t1", "i1"]
    for b in data["blocks"]:
        assert set(b) == {"id", "bbox_mm", "overflow", "font_substituted", "missing"}
        assert len(b["bbox_mm"]) == 4


def test_render_accepts_doc_wrapper(client):
    c, _ = client
    assert c.post("/render", json={"doc": DOC}).get_json()["success"] is True


def test_render_bad_stock_is_400(client):
    c, _ = client
    resp = c.post("/render", json=dict(DOC, label_size="BAD"))
    assert resp.status_code == 400
    assert "Unknown label size" in resp.get_json()["error"]


def test_render_reports_missing_image(client):
    c, _ = client
    doc = {"label_size": "11354", "blocks": [
        {"type": "image", "id": "gone", "src": "upload:" + "b" * 64 + ".png",
         "x_mm": 1, "y_mm": 1, "width_mm": 10}]}
    block = c.post("/render", json=doc).get_json()["blocks"][0]
    assert block["missing"] is True


def test_preview_flat_payload_still_works(client):
    c, _ = client
    resp = c.post("/preview", json={"text": "Hi\nthere", "label_size": "11354",
                                    "font_size": 40, "align": "left"})
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True and data["image"].startswith("data:image/png;base64,")


def test_print_accepts_a_doc(client):
    c, web_app = client
    resp = c.post("/print", json={"doc": DOC, "copies": 2})
    assert resp.status_code == 200
    assert resp.get_json()["job_id"] == 7
    size, label_size, copies = web_app.printer_service.calls[0]
    assert (label_size, copies) == ("30252", 2)
    assert size == (int(28 * 300 / 25.4), int(89 * 300 / 25.4))


def test_print_doc_without_content_is_400(client):
    c, _ = client
    resp = c.post("/print", json={"doc": {"label_size": "11354", "blocks": [
        {"type": "text", "text": "  "}]}})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "No text provided"


def test_print_doc_with_missing_image_is_400_naming_block(client):
    c, web_app = client
    doc = {"label_size": "11354", "blocks": [
        {"type": "image", "id": "gone", "src": "upload:" + "c" * 64 + ".png",
         "x_mm": 1, "y_mm": 1, "width_mm": 10}]}
    resp = c.post("/print", json={"doc": doc})
    assert resp.status_code == 400
    assert "gone" in resp.get_json()["error"]
    assert web_app.printer_service.calls == []


def test_render_huge_image_width_is_400(client):
    c, _ = client
    doc = {"label_size": "11354", "blocks": [
        {"type": "image", "src": "icon:star", "x_mm": 0, "y_mm": 0, "width_mm": 1e7}]}
    resp = c.post("/render", json=doc)
    assert resp.status_code == 400


def test_render_extreme_aspect_upload_is_400(client):
    c, _ = client
    buf = io.BytesIO()
    Image.new("1", (4, 20000), 1).save(buf, "PNG")
    ref = upload(c, buf.getvalue()).get_json()["ref"]
    doc = {"label_size": "11354", "blocks": [
        {"type": "image", "src": ref, "x_mm": 0, "y_mm": 0, "width_mm": 50}]}
    assert c.post("/render", json=doc).status_code == 400


def test_upload_decompression_bomb_is_400(client):
    c, _ = client
    buf = io.BytesIO()
    Image.new("1", (20000, 20000), 1).save(buf, "PNG")
    assert upload(c, buf.getvalue()).status_code == 400


def test_images_served_with_hardening_headers(client):
    c, _ = client
    png_ref = upload(c, png_bytes()).get_json()["ref"]
    svg = (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
           b'<script>alert(1)</script><rect width="10" height="10"/></svg>')
    svg_ref = upload(c, svg, "x.svg").get_json()["ref"]
    for ref in (png_ref, svg_ref):
        resp = c.get("/images/" + ref.split(":", 1)[1])
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["Content-Security-Policy"] == (
            "default-src 'none'; style-src 'unsafe-inline'; sandbox")
    assert "attachment" in c.get("/images/" + svg_ref.split(":", 1)[1]).headers["Content-Disposition"]


def test_traversal_names_are_404(client):
    c, _ = client
    for name in ("..%2F..%2Fetc%2Fpasswd", "%2e%2e%2fx.png", "a.png", "A" * 64 + ".png"):
        assert c.get("/images/" + name).status_code == 404


def test_svg_external_references_are_not_fetched(client, tmp_path):
    c, _ = client
    secret = tmp_path / "secret.png"
    Image.new("RGB", (20, 20), "red").save(secret)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'viewBox="0 0 20 20"><image width="20" height="20" href="file://{secret}"/>'
           f'<image width="20" height="20" xlink:href="http://127.0.0.1:9/x.png"/></svg>').encode()
    ref = upload(c, svg, "x.svg").get_json()["ref"]
    from cups_dymo_label_printer import images
    img = images.load_image(ref, 20)
    assert img.getpixel((10, 10)) == (255, 255, 255)   # nothing was loaded


@pytest.mark.parametrize("value", ["Infinity", "NaN", "1e300"])
def test_render_rejects_hostile_numbers_with_400(client, value):
    c, _ = client
    body = ('{"label_size": "11354", "blocks": [{"type": "text", "text": "a", "x_mm": %s}]}'
            % value)
    resp = c.post("/render", data=body, content_type="application/json")
    assert resp.status_code == 400


@pytest.mark.parametrize("field,value", [("bold", 1), ("font_family", 7), ("id", [1])])
def test_render_rejects_wrong_types_with_400(client, field, value):
    c, _ = client
    doc = {"label_size": "11354", "blocks": [{"type": "text", "text": "a", field: value}]}
    assert c.post("/render", json=doc).status_code == 400


def test_hostile_text_doc_never_500(client):
    import time
    blocks = [{"type": "text", "id": f"b{i}", "text": "\n".join(["W" * 10] * 50),
               "font_size_pt": 286, "y_mm": 0, "font_family": "Liberation Sans"}
              for i in range(30)]
    start = time.monotonic()
    resp = c = client[0].post("/render", json={"label_size": "30323", "blocks": blocks})
    assert time.monotonic() - start < 2
    assert resp.status_code in (200, 400)
