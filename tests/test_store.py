"""LabelStore: v1 -> v2 migration, atomic persistence, rollback (R12)."""

import json
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cups_dymo_label_printer import store as store_mod
from cups_dymo_label_printer.document import LabelDoc
from cups_dymo_label_printer.store import LabelStore, StoreError

V1_FIXTURE = Path(__file__).parent / "fixtures" / "saved_labels_v1.json"


class Clock:
    """Injectable ``now()``: each call advances one second."""

    def __init__(self):
        self.t = datetime(2026, 11, 1, 18, 0, 0, tzinfo=timezone.utc)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t


def text_doc(text, label_size="11354", **block):
    return LabelDoc.from_json({
        "label_size": label_size,
        "blocks": [{"type": "text", "id": "t1", "text": text, **block}],
    })


@pytest.fixture()
def v1_path(tmp_path):
    path = tmp_path / "saved_labels.json"
    shutil.copyfile(V1_FIXTURE, path)
    return path


# --- migration -------------------------------------------------------------

def test_v1_file_loads_as_text_block_labels_in_original_order(v1_path):
    original = json.loads(V1_FIXTURE.read_text(encoding="utf-8"))
    labels = LabelStore(v1_path).list()

    assert [l["id"] for l in labels] == [e["id"] for e in original]
    for label, entry in zip(labels, original):
        assert label["label_size"] == entry["label_size"]
        assert label["copies"] == entry["copies"]
        assert label["starred"] is False
        assert label["created_at"] is None
        assert label["updated_at"] is None
        assert label["last_printed_at"] is None
        assert label["print_count"] == 0
        [block] = label["blocks"]
        assert block["type"] == "text"
        assert block["text"] == entry["text"]
        assert block["font_family"] == "DejaVu Sans"
        assert block["bold"] is True
        assert block["align"] == entry["align"]
        assert block["y_mm"] is None  # vertically centred, as before
        assert block["font_size_pt"] == entry["font_size"] * 72 / 300


def test_v1_orientation_is_the_stock_shape(v1_path):
    by_size = {l["label_size"]: l for l in LabelStore(v1_path).list()}
    assert by_size["11354"]["orientation"] == "landscape"  # 57 x 32
    assert by_size["30252"]["orientation"] == "portrait"   # 28 x 89


def test_v1_load_does_not_write(v1_path):
    before = v1_path.read_bytes()
    LabelStore(v1_path).list()
    assert v1_path.read_bytes() == before
    assert not (v1_path.parent / "saved_labels.v1.json").exists()


def test_first_persist_writes_v2_and_byte_identical_v1_backup(v1_path):
    original = v1_path.read_bytes()
    store = LabelStore(v1_path, now=Clock())
    store.create(text_doc("New"))

    data = json.loads(v1_path.read_text(encoding="utf-8"))
    assert data["version"] == 2
    assert len(data["labels"]) == 3
    backup = v1_path.parent / "saved_labels.v1.json"
    assert backup.read_bytes() == original


def test_existing_backup_is_never_overwritten(v1_path):
    backup = v1_path.parent / "saved_labels.v1.json"
    backup.write_bytes(b"older backup")
    LabelStore(v1_path, now=Clock()).create(text_doc("New"))
    assert backup.read_bytes() == b"older backup"
    copies = sorted(p.name for p in v1_path.parent.glob("saved_labels.v1*.json"))
    assert len(copies) == 2
    other = next(p for p in v1_path.parent.glob("saved_labels.v1*.json") if p != backup)
    assert other.read_bytes() == V1_FIXTURE.read_bytes()


def test_v2_file_round_trips(v1_path):
    store = LabelStore(v1_path, now=Clock())
    store.create(text_doc("New"))
    first = store.list()

    reloaded = LabelStore(v1_path).list()
    assert reloaded == first
    # a second persist from a v2 file makes no further backup
    LabelStore(v1_path, now=Clock()).create(text_doc("Again"))
    assert len(list(v1_path.parent.glob("saved_labels.v1*.json"))) == 1


def test_missing_file_loads_empty_and_creates_on_first_mutation(tmp_path):
    path = tmp_path / "saved_labels.json"
    store = LabelStore(path, now=Clock())
    assert store.list() == []
    assert not path.exists()
    store.create(text_doc("One"))
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 2
    assert not (tmp_path / "saved_labels.v1.json").exists()


@pytest.mark.parametrize("content", [
    b"{not json",
    b'"a string"',
    b'{"version": 3, "labels": []}',
    b'{"version": 2, "labels": "nope"}',
])
def test_corrupt_file_loads_empty_and_is_kept_until_a_mutation(tmp_path, content):
    path = tmp_path / "saved_labels.json"
    path.write_bytes(content)
    store = LabelStore(path, now=Clock())

    assert store.list() == []
    assert path.read_bytes() == content  # reading never rewrites it

    store.create(text_doc("One"))
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 2
    kept = list(tmp_path.glob("saved_labels.corrupt*.json"))
    assert [p.read_bytes() for p in kept] == [content]


def test_invalid_v2_entry_is_skipped_and_original_kept(tmp_path):
    path = tmp_path / "saved_labels.json"
    good = LabelStore(tmp_path / "other.json", now=Clock()).create(text_doc("Good"))
    raw = json.dumps({"version": 2, "labels": [good, {"id": "x", "label_size": "BAD"}]})
    path.write_text(raw, encoding="utf-8")

    store = LabelStore(path, now=Clock())
    assert [l["id"] for l in store.list()] == [good["id"]]
    store.create(text_doc("Two"))
    kept = list(tmp_path.glob("saved_labels.corrupt*.json"))
    assert [p.read_text(encoding="utf-8") for p in kept] == [raw]


def test_unreadable_file_refuses_mutations(tmp_path, monkeypatch):
    path = tmp_path / "saved_labels.json"
    path.write_text("[]", encoding="utf-8")
    real_open = open

    def fake_open(file, *args, **kwargs):
        if str(file) == str(path) and "r" in (args[0] if args else kwargs.get("mode", "r")):
            raise PermissionError("denied")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", fake_open)
    store = LabelStore(path, now=Clock())
    assert store.list() == []
    with pytest.raises(StoreError):
        store.create(text_doc("One"))
    monkeypatch.undo()
    assert path.read_text(encoding="utf-8") == "[]"


# --- atomic write + rollback ----------------------------------------------

def test_write_goes_through_a_temp_file_and_os_replace(tmp_path, monkeypatch):
    path = tmp_path / "saved_labels.json"
    calls = []
    real_replace = os.replace

    def spy(src, dst):
        calls.append((Path(src), Path(dst)))
        return real_replace(src, dst)

    monkeypatch.setattr(store_mod.os, "replace", spy)
    LabelStore(path, now=Clock()).create(text_doc("One"))
    assert calls and calls[-1][1] == path
    assert calls[-1][0].parent == path.parent and calls[-1][0] != path


def test_failed_replace_keeps_file_rolls_back_and_raises(v1_path, monkeypatch):
    store = LabelStore(v1_path, now=Clock())
    store.create(text_doc("Kept"))
    before_bytes = v1_path.read_bytes()
    before_state = store.list()

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(store_mod.os, "replace", boom)
    with pytest.raises(StoreError):
        store.create(text_doc("Lost"))

    assert v1_path.read_bytes() == before_bytes
    assert store.list() == before_state
    assert sorted(p.name for p in v1_path.parent.iterdir()) == [
        "saved_labels.json", "saved_labels.v1.json"]  # no temp file left behind


def test_failed_first_persist_retries_the_backup_later(v1_path, monkeypatch):
    original = v1_path.read_bytes()
    store = LabelStore(v1_path, now=Clock())
    real_replace = os.replace

    def boom(src, dst):
        if Path(dst) == v1_path:
            raise OSError("disk full")
        return real_replace(src, dst)

    monkeypatch.setattr(store_mod.os, "replace", boom)
    with pytest.raises(StoreError):
        store.create(text_doc("Lost"))
    assert v1_path.read_bytes() == original
    assert len(store.list()) == 2

    monkeypatch.setattr(store_mod.os, "replace", real_replace)
    store.create(text_doc("Saved"))
    assert json.loads(v1_path.read_text(encoding="utf-8"))["version"] == 2
    assert (v1_path.parent / "saved_labels.v1.json").read_bytes() == original


def test_timestamps_are_utc_iso(tmp_path):
    label = LabelStore(tmp_path / "s.json", now=Clock()).create(text_doc("One"))
    assert label["created_at"] == "2026-11-01T18:00:01.000Z"
    assert label["updated_at"] == label["created_at"]
