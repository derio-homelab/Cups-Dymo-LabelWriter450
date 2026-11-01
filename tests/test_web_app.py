import importlib
import json
import os
import sys
import types

import pytest


class _StubPrinterService:
    def __init__(self):
        self.print_image_return = 123
        self.print_image_side_effect = None
        self.status_payload = {"state": "idle"}
        self.calls = []

    def print_image(self, image, label_size, copies=1, job_title="Label"):
        if self.print_image_side_effect:
            raise self.print_image_side_effect
        self.calls.append((label_size, copies, job_title))
        return self.print_image_return

    def get_printer_status(self):
        return self.status_payload


@pytest.fixture()
def app_client(monkeypatch, tmp_path):
    class FakeConnection:
        def __init__(self):
            self.printers = {"dymo": {"state": "idle"}}

        def printFile(self, *_, **__):
            return 1

        def getPrinters(self):
            return self.printers

    fake_module = types.SimpleNamespace(Connection=FakeConnection)
    monkeypatch.setitem(sys.modules, "cups", fake_module)

    monkeypatch.setenv("LABEL_MEMORY_FILE", str(tmp_path / "saved_labels.json"))

    import cups_dymo_label_printer.printer_service as ps
    importlib.reload(ps)
    import cups_dymo_label_printer.web_app as web_app
    importlib.reload(web_app)

    web_app.app.config["TESTING"] = True
    return web_app.app.test_client(), web_app


def test_preview_returns_base64_png(app_client):
    client, web_app = app_client

    resp = client.post(
        "/preview",
        json={"text": "Hello", "label_size": "11354", "font_size": 40, "align": "center"},
    )

    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["image"].startswith("data:image/png;base64,")


def test_preview_invalid_label_size(app_client):
    client, _ = app_client

    resp = client.post("/preview", json={"text": "Hello", "label_size": "BAD"})

    data = resp.get_json()
    assert resp.status_code == 400
    assert data["success"] is False
    assert "Unknown label size" in data["error"]


def test_print_submits_job_and_returns_id(app_client, monkeypatch):
    client, web_app = app_client
    stub = _StubPrinterService()
    stub.print_image_return = 123
    monkeypatch.setattr(web_app, "printer_service", stub)

    resp = client.post(
        "/print",
        json={"text": "Print Me", "label_size": "11354", "font_size": 40, "align": "center", "copies": 1},
    )

    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["job_id"] == 123
    assert "Print job" in data["message"]


def test_print_rejects_empty_text(app_client):
    client, _ = app_client

    resp = client.post("/print", json={"text": "", "label_size": "11354"})

    data = resp.get_json()
    assert resp.status_code == 400
    assert data["success"] is False
    assert data["error"] == "No text provided"


def test_print_rejects_invalid_label_size(app_client, monkeypatch):
    client, web_app = app_client
    stub = _StubPrinterService()
    stub.print_image_side_effect = ValueError("Unknown label size: BAD")
    monkeypatch.setattr(web_app, "printer_service", stub)

    resp = client.post("/print", json={"text": "Hello", "label_size": "BAD"})

    data = resp.get_json()
    assert resp.status_code == 400
    assert data["success"] is False
    assert "Unknown label size" in data["error"]


def test_print_surfaces_cups_failure(app_client, monkeypatch):
    client, web_app = app_client
    stub = _StubPrinterService()
    stub.print_image_side_effect = RuntimeError("Failed to print: connection error")
    monkeypatch.setattr(web_app, "printer_service", stub)

    resp = client.post("/print", json={"text": "Hello", "label_size": "11354"})

    data = resp.get_json()
    assert resp.status_code == 500
    assert data["success"] is False
    assert "Failed to print" in data["error"]


def test_status_returns_printer_info(app_client, monkeypatch):
    client, web_app = app_client
    stub = _StubPrinterService()
    stub.status_payload = {"state": "idle"}
    monkeypatch.setattr(web_app, "printer_service", stub)

    resp = client.get("/status")

    data = resp.get_json()
    assert resp.status_code == 200
    assert data == {"state": "idle"}


def _label_payload(text: str):
    return {"text": text, "label_size": "11354", "font_size": 40, "align": "center", "copies": 1}


def test_memory_starts_empty(app_client):
    client, _ = app_client

    resp = client.get("/memory")

    assert resp.status_code == 200
    assert resp.get_json() == []


def test_memory_adds_on_print_and_dedup(app_client, monkeypatch):
    client, web_app = app_client
    stub = _StubPrinterService()
    monkeypatch.setattr(web_app, "printer_service", stub)

    payload = _label_payload("Hello")

    resp1 = client.post("/print", json=payload)
    assert resp1.status_code == 200

    resp_list_1 = client.get("/memory")
    first_list = resp_list_1.get_json()
    assert len(first_list) == 1
    first_id = first_list[0]["id"]

    resp2 = client.post("/print", json=payload)
    assert resp2.status_code == 200

    resp_list_2 = client.get("/memory")
    second_list = resp_list_2.get_json()
    assert len(second_list) == 1
    assert second_list[0]["id"] == first_id  # content match bumps in place (R16)
    assert second_list[0]["print_count"] == 2
    assert second_list[0]["text"] == "Hello"


def test_memory_delete_selected(app_client, monkeypatch):
    client, web_app = app_client
    stub = _StubPrinterService()
    monkeypatch.setattr(web_app, "printer_service", stub)

    payload1 = _label_payload("First")
    payload2 = _label_payload("Second")
    client.post("/print", json=payload1)
    client.post("/print", json=payload2)

    current = client.get("/memory").get_json()
    ids = [entry["id"] for entry in current]
    delete_id = ids[0]

    resp_delete = client.delete("/memory", json={"ids": [delete_id]})
    assert resp_delete.status_code == 200

    remaining = client.get("/memory").get_json()
    remaining_ids = [entry["id"] for entry in remaining]
    assert delete_id not in remaining_ids
    assert len(remaining) == 1


def test_memory_delete_all_via_select_all(app_client, monkeypatch):
    client, web_app = app_client
    stub = _StubPrinterService()
    monkeypatch.setattr(web_app, "printer_service", stub)

    client.post("/print", json=_label_payload("One"))
    client.post("/print", json=_label_payload("Two"))

    current = client.get("/memory").get_json()
    all_ids = [entry["id"] for entry in current]

    resp_delete = client.delete("/memory", json={"ids": all_ids})
    assert resp_delete.status_code == 200

    remaining = client.get("/memory").get_json()
    assert remaining == []


def test_persistence_writes_file_on_print(app_client, monkeypatch, tmp_path):
    client, web_app = app_client
    stub = _StubPrinterService()
    monkeypatch.setattr(web_app, "printer_service", stub)

    payload = _label_payload("Persist Me")
    resp = client.post("/print", json=payload)
    assert resp.status_code == 200

    memory_file = os.environ["LABEL_MEMORY_FILE"]
    assert os.path.exists(memory_file)
    data = json.loads(open(memory_file, "r", encoding="utf-8").read())
    assert data["version"] == 2
    assert len(data["labels"]) == 1
    assert data["labels"][0]["blocks"][0]["text"] == "Persist Me"


def test_persistence_loads_on_startup(monkeypatch, tmp_path):
    # Pre-seed file
    memory_file = tmp_path / "seed.json"
    seeded = [{"id": "abc", "text": "Seed", "label_size": "11354", "font_size": 40, "align": "center", "copies": 1}]
    memory_file.write_text(json.dumps(seeded), encoding="utf-8")

    class FakeConnection:
        def __init__(self):
            self.printers = {"dymo": {"state": "idle"}}

        def printFile(self, *_, **__):
            return 1

        def getPrinters(self):
            return self.printers

    fake_module = types.SimpleNamespace(Connection=FakeConnection)
    monkeypatch.setitem(sys.modules, "cups", fake_module)
    monkeypatch.setenv("LABEL_MEMORY_FILE", str(memory_file))

    import cups_dymo_label_printer.printer_service as ps
    importlib.reload(ps)
    import cups_dymo_label_printer.web_app as web_app
    importlib.reload(web_app)

    web_app.app.config["TESTING"] = True
    client = web_app.app.test_client()

    resp = client.get("/memory")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) == 1
    assert data[0]["text"] == "Seed"


# --- print flow (R16) -------------------------------------------------------

def _doc(text):
    return {"label_size": "11354", "blocks": [{"type": "text", "id": "t1", "text": text}]}


def test_print_names_the_entry_it_saved(app_client, monkeypatch):
    client, web_app = app_client
    monkeypatch.setattr(web_app, "printer_service", _StubPrinterService())

    data = client.post("/print", json={"doc": _doc("Hi")}).get_json()
    assert data["success"] is True and "warning" not in data
    assert data["label"]["id"] == web_app.store.list()[0]["id"]
    assert data["label"]["print_count"] == 1


def test_print_with_id_saves_in_place_then_prints_then_bumps(app_client, monkeypatch):
    client, web_app = app_client
    stub = _StubPrinterService()
    monkeypatch.setattr(web_app, "printer_service", stub)
    from cups_dymo_label_printer.document import LabelDoc
    saved = web_app.store.create(LabelDoc.from_json(_doc("Draft")))

    doc = _doc("Edited")
    doc["name"] = "Jar"
    resp = client.post("/print", json={"doc": doc, "id": saved["id"], "copies": 3})
    data = resp.get_json()

    assert resp.status_code == 200 and stub.calls == [("11354", 3, "Label")]
    assert data["label"]["id"] == saved["id"]
    [entry] = web_app.store.list()
    assert entry["id"] == saved["id"]
    assert entry["name"] == "Jar" and entry["blocks"][0]["text"] == "Edited"
    assert entry["copies"] == 3 and entry["print_count"] == 1
    assert entry["updated_at"] >= entry["created_at"]


def test_print_with_unknown_id_is_404_and_prints_nothing(app_client, monkeypatch):
    client, web_app = app_client
    stub = _StubPrinterService()
    monkeypatch.setattr(web_app, "printer_service", stub)

    resp = client.post("/print", json={"doc": _doc("x"), "id": "missing"})
    assert resp.status_code == 404 and stub.calls == []


def test_pre_print_save_failure_is_500_and_prints_nothing(app_client, monkeypatch):
    client, web_app = app_client
    stub = _StubPrinterService()
    monkeypatch.setattr(web_app, "printer_service", stub)
    from cups_dymo_label_printer import store as store_mod
    from cups_dymo_label_printer.document import LabelDoc
    saved = web_app.store.create(LabelDoc.from_json(_doc("Draft")))

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(store_mod.os, "replace", boom)
    resp = client.post("/print", json={"doc": _doc("Edited"), "id": saved["id"]})
    data = resp.get_json()

    assert resp.status_code == 500 and data["success"] is False
    assert stub.calls == []
    assert web_app.store.get(saved["id"])["blocks"][0]["text"] == "Draft"


def test_post_print_history_failure_is_200_with_warning(app_client, monkeypatch):
    client, web_app = app_client
    stub = _StubPrinterService()
    monkeypatch.setattr(web_app, "printer_service", stub)
    from cups_dymo_label_printer import store as store_mod

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(store_mod.os, "replace", boom)
    resp = client.post("/print", json={"doc": _doc("Hi")})
    data = resp.get_json()

    assert resp.status_code == 200
    assert data["success"] is True and data["job_id"] == 123
    assert "history" in data["warning"]
    assert data["label"] is None
    assert len(stub.calls) == 1
    assert web_app.store.list() == []


def test_post_print_bump_failure_with_id_still_names_the_saved_entry(app_client, monkeypatch):
    client, web_app = app_client
    monkeypatch.setattr(web_app, "printer_service", _StubPrinterService())
    from cups_dymo_label_printer.document import LabelDoc
    from cups_dymo_label_printer.store import StoreError
    saved = web_app.store.create(LabelDoc.from_json(_doc("Draft")))

    def fail(*_args, **_kwargs):
        raise StoreError("disk full")

    monkeypatch.setattr(web_app.store, "record_print", fail)
    data = client.post("/print", json={"doc": _doc("Edited"), "id": saved["id"]}).get_json()
    assert data["success"] is True and "warning" in data
    assert data["label"]["id"] == saved["id"]
    assert data["label"]["blocks"][0]["text"] == "Edited"
