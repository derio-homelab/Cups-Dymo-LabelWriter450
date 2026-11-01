"""Routes: /labels API, thumbnail, /memory compatibility alias (R13-R16)."""

import importlib
import io
import json
import shutil
from pathlib import Path

import pytest
from PIL import Image

from cups_dymo_label_printer import fonts

FIXTURES = Path(__file__).parent / "fixtures"


class _Printer:
    def __init__(self):
        self.calls = []

    def print_image(self, image, label_size, copies=1, job_title="Label"):
        self.calls.append((image.size, label_size, copies))
        return 9


def _load(monkeypatch, tmp_path):
    monkeypatch.setenv("LABEL_FONT_DIRS", str(FIXTURES / "fonts"))
    monkeypatch.setenv("LABEL_MEMORY_FILE", str(tmp_path / "saved_labels.json"))
    monkeypatch.setenv("LABEL_IMAGE_DIR", str(tmp_path / "images"))
    fonts.reset_cache()
    import cups_dymo_label_printer.web_app as web_app
    importlib.reload(web_app)
    web_app.app.config["TESTING"] = True
    web_app.printer_service = _Printer()
    return web_app.app.test_client(), web_app


@pytest.fixture()
def client(monkeypatch, tmp_path):
    yield _load(monkeypatch, tmp_path)
    fonts.reset_cache()


def doc(text, label_size="11354", **extra):
    return {"label_size": label_size,
            "blocks": [{"type": "text", "id": "t1", "text": text}], **extra}


def create(c, text, **extra):
    resp = c.post("/labels", json={"doc": doc(text, **extra)})
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["label"]


# --- list / create / read / update / delete ---------------------------------

def test_list_starts_empty(client):
    c, _ = client
    assert c.get("/labels").get_json() == {"success": True, "labels": []}


def test_create_returns_the_saved_label(client):
    c, web_app = client
    label = create(c, "Flour\nT55", name="")
    assert label["name"] == "Flour"
    assert label["print_count"] == 0 and label["starred"] is False
    assert web_app.store.get(label["id"]) == label


def test_create_accepts_a_bare_doc(client):
    c, _ = client
    resp = c.post("/labels", json=doc("Bare"))
    assert resp.status_code == 201


def test_create_rejects_an_invalid_doc(client):
    c, _ = client
    resp = c.post("/labels", json={"doc": doc("x", label_size="BAD")})
    assert resp.status_code == 400 and resp.get_json()["success"] is False


def test_list_filters_search_and_sort(client):
    c, _ = client
    a = create(c, "banana")
    b = create(c, "Apple")
    c.put(f"/labels/{a['id']}/star", json={"starred": True})

    def ids(query):
        return [l["id"] for l in c.get("/labels" + query).get_json()["labels"]]

    assert ids("") == [a["id"], b["id"]]
    assert ids("?sort=name") == [a["id"], b["id"]]  # starred first, still
    assert ids("?sort=created") == [a["id"], b["id"]]
    assert ids("?q=APP") == [b["id"]]
    assert ids("?starred=true") == [a["id"]]
    assert ids("?starred=false") == [a["id"], b["id"]]
    assert c.get("/labels?sort=size").status_code == 400


def test_get_put_delete_one(client):
    c, _ = client
    label = create(c, "Old")

    assert c.get(f"/labels/{label['id']}").get_json()["label"] == label

    resp = c.put(f"/labels/{label['id']}", json={"doc": doc("New", name="Renamed")})
    updated = resp.get_json()["label"]
    assert resp.status_code == 200
    assert updated["id"] == label["id"] and updated["name"] == "Renamed"
    assert updated["blocks"][0]["text"] == "New"

    assert c.delete(f"/labels/{label['id']}").get_json() == {"success": True}
    assert c.get(f"/labels/{label['id']}").status_code == 404


@pytest.mark.parametrize("method,path,body", [
    ("get", "/labels/nope", None),
    ("put", "/labels/nope", {"doc": doc("x")}),
    ("delete", "/labels/nope", None),
    ("post", "/labels/nope/duplicate", None),
    ("put", "/labels/nope/star", {"starred": True}),
    ("post", "/labels/nope/print", {}),
    ("get", "/labels/nope/thumbnail.png", None),
])
def test_unknown_id_is_404(client, method, path, body):
    c, _ = client
    resp = getattr(c, method)(path, json=body)
    assert resp.status_code == 404


def test_delete_many(client):
    c, _ = client
    a, b, d = create(c, "a"), create(c, "b"), create(c, "d")
    resp = c.delete("/labels", json={"ids": [a["id"], d["id"], "unknown"]})
    assert resp.get_json() == {"success": True, "deleted": 2}
    assert [l["id"] for l in c.get("/labels").get_json()["labels"]] == [b["id"]]
    assert c.delete("/labels", json={"ids": "a"}).status_code == 400


def test_duplicate(client):
    c, _ = client
    label = create(c, "Orig")
    resp = c.post(f"/labels/{label['id']}/duplicate")
    dup = resp.get_json()["label"]
    assert resp.status_code == 201
    assert dup["id"] != label["id"] and dup["blocks"] == label["blocks"]
    assert len(c.get("/labels").get_json()["labels"]) == 2


def test_star_and_unstar(client):
    c, web_app = client
    label = create(c, "Star")
    assert c.put(f"/labels/{label['id']}/star", json={"starred": True}).get_json()["label"]["starred"]
    assert web_app.store.get(label["id"])["starred"] is True
    assert c.put(f"/labels/{label['id']}/star", json={"starred": False}).get_json()["label"]["starred"] is False
    assert c.put(f"/labels/{label['id']}/star", json={"starred": "yes"}).status_code == 400


def test_mutation_store_failure_is_500_and_rolled_back(client, monkeypatch):
    c, web_app = client
    label = create(c, "Keep")
    from cups_dymo_label_printer import store as store_mod

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(store_mod.os, "replace", boom)
    for resp in (c.post("/labels", json={"doc": doc("x")}),
                 c.put(f"/labels/{label['id']}", json={"doc": doc("y")}),
                 c.delete(f"/labels/{label['id']}"),
                 c.delete("/labels", json={"ids": [label["id"]]}),
                 c.post(f"/labels/{label['id']}/duplicate"),
                 c.put(f"/labels/{label['id']}/star", json={"starred": True})):
        assert resp.status_code == 500 and resp.get_json()["success"] is False
    assert [l for l in web_app.store.list()] == [label]


# --- re-print ---------------------------------------------------------------

def test_reprint_from_history_bumps_the_entry(client):
    c, web_app = client
    label = create(c, "Again", copies=2)
    resp = c.post(f"/labels/{label['id']}/print", json={})
    data = resp.get_json()
    assert resp.status_code == 200 and data["job_id"] == 9
    assert data["label"]["id"] == label["id"] and data["label"]["print_count"] == 1
    assert web_app.printer_service.calls[0][1:] == ("11354", 2)

    data = c.post(f"/labels/{label['id']}/print", json={"copies": 4}).get_json()
    assert data["label"]["print_count"] == 2
    assert web_app.printer_service.calls[1][2] == 4


def test_reprint_with_a_missing_image_is_400(client):
    c, web_app = client
    raw = {"label_size": "11354", "blocks": [
        {"type": "image", "id": "i1", "src": "upload:" + "0" * 64 + ".png"}]}
    label = c.post("/labels", json={"doc": raw}).get_json()["label"]
    resp = c.post(f"/labels/{label['id']}/print", json={})
    assert resp.status_code == 400 and web_app.printer_service.calls == []


def test_reprint_history_failure_is_200_with_warning(client, monkeypatch):
    c, web_app = client
    label = create(c, "Again")
    from cups_dymo_label_printer import store as store_mod

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(store_mod.os, "replace", boom)
    data = c.post(f"/labels/{label['id']}/print", json={}).get_json()
    assert data["success"] is True and "warning" in data
    assert data["label"]["id"] == label["id"]


# --- thumbnail --------------------------------------------------------------

def test_thumbnail_is_a_100_dpi_png(client):
    c, _ = client
    landscape = create(c, "Thumb")
    portrait = create(c, "Thumb", label_size="30252")
    for label, size in ((landscape, (224, 125)), (portrait, (110, 350))):
        resp = c.get(f"/labels/{label['id']}/thumbnail.png")
        assert resp.status_code == 200 and resp.mimetype == "image/png"
        assert Image.open(io.BytesIO(resp.data)).size == size


def test_thumbnail_leaves_a_missing_image_out(client):
    c, _ = client
    raw = {"label_size": "11354", "blocks": [
        {"type": "image", "id": "i1", "src": "upload:" + "0" * 64 + ".png"}]}
    label = c.post("/labels", json={"doc": raw}).get_json()["label"]
    resp = c.get(f"/labels/{label['id']}/thumbnail.png")
    assert resp.status_code == 200
    image = Image.open(io.BytesIO(resp.data)).convert("L")
    assert image.getextrema() == (255, 255)  # blank: the missing image is simply absent


# --- /memory compatibility alias ----------------------------------------------

def test_memory_lists_v2_labels_with_flat_fields(client):
    c, _ = client
    raw = {"label_size": "30252", "blocks": [
        {"type": "text", "id": "a", "text": "One", "font_size_pt": 9.6, "align": "left"},
        {"type": "image", "id": "i", "src": "icon:star"},
        {"type": "text", "id": "b", "text": "Two\nThree", "font_size_pt": 20},
    ]}
    saved = c.post("/labels", json={"doc": raw}).get_json()["label"]
    create(c, "")  # no non-empty text: flat text is empty

    memory = c.get("/memory").get_json()
    assert [m["id"] for m in memory] == [l["id"] for l in c.get("/labels").get_json()["labels"]]
    entry = next(m for m in memory if m["id"] == saved["id"])
    assert {k: v for k, v in entry.items() if k not in ("text", "font_size", "align")} == saved
    assert entry["text"] == "One\nTwo\nThree"
    assert entry["font_size"] == 40  # 9.6 pt at 300 DPI
    assert entry["align"] == "left"


def test_memory_delete_returns_remaining_in_the_same_shape(client):
    c, _ = client
    a, b = create(c, "a"), create(c, "b")
    data = c.delete("/memory", json={"ids": [a["id"]]}).get_json()
    assert data["success"] is True
    assert data["remaining"] == c.get("/memory").get_json()
    assert [m["id"] for m in data["remaining"]] == [b["id"]]
    assert data["remaining"][0]["text"] == "b"


def test_memory_serves_a_migrated_v1_file(monkeypatch, tmp_path):
    shutil.copyfile(FIXTURES / "saved_labels_v1.json", tmp_path / "saved_labels.json")
    c, _ = _load(monkeypatch, tmp_path)
    original = json.loads((FIXTURES / "saved_labels_v1.json").read_text(encoding="utf-8"))
    memory = c.get("/memory").get_json()
    assert [(m["id"], m["text"], m["font_size"], m["align"]) for m in memory] == [
        (e["id"], e["text"], e["font_size"], e["align"]) for e in original]
    fonts.reset_cache()


def test_migrated_over_cap_label_reprints_and_thumbnails(monkeypatch, tmp_path):
    entry = {"id": "long", "text": "x" * 2500, "label_size": "11354", "font_size": 40,
             "align": "center", "copies": 1}
    (tmp_path / "saved_labels.json").write_text(json.dumps([entry]), encoding="utf-8")
    c, web_app = _load(monkeypatch, tmp_path)
    assert c.get("/labels/long/thumbnail.png").status_code == 200
    resp = c.post("/labels/long/print", json={})
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()["label"]["print_count"] == 1
    fonts.reset_cache()


@pytest.mark.parametrize("method,path", [
    ("delete", "/labels"),
    ("delete", "/memory"),
    ("put", "/labels/{id}/star"),
    ("post", "/labels/{id}/print"),
])
def test_a_non_object_body_is_400_json(client, method, path):
    c, web_app = client
    label = create(c, "x")
    resp = getattr(c, method)(path.format(id=label["id"]), json=[label["id"]])
    assert resp.status_code == 400
    assert resp.get_json()["success"] is False
    assert web_app.store.list() == [label] and web_app.printer_service.calls == []
