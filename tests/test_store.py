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


# --- operations (R13, R14, R15, R25) ----------------------------------------

@pytest.fixture()
def store(tmp_path):
    return LabelStore(tmp_path / "saved_labels.json", now=Clock())


def test_update_keeps_id_and_bumps_updated_at_only(store):
    label = store.create(text_doc("Old"))
    store.set_star(label["id"], True)
    updated = store.update(label["id"], text_doc("New", label_size="30252"))

    assert updated["id"] == label["id"]
    assert updated["updated_at"] > updated["created_at"]
    assert updated["created_at"] == label["created_at"]
    assert updated["starred"] is True
    assert updated["print_count"] == 0 and updated["last_printed_at"] is None
    assert updated["label_size"] == "30252"
    assert updated["blocks"][0]["text"] == "New"
    assert store.get(label["id"]) == updated


def test_update_renames_in_place(store):
    label = store.create(text_doc("Flour"))
    doc = text_doc("Flour")
    doc.name = "Kitchen jar"
    assert store.update(label["id"], doc)["name"] == "Kitchen jar"
    assert [l["name"] for l in store.list()] == ["Kitchen jar"]


def test_update_unknown_id_raises(store):
    with pytest.raises(store_mod.LabelNotFound):
        store.update("nope", text_doc("x"))


def test_duplicate_is_a_fresh_copy(store):
    label = store.create(text_doc("Orig"))
    store.set_star(label["id"], True)
    store.record_print(text_doc("Orig"), label["id"])
    original = store.get(label["id"])

    dup = store.duplicate(label["id"])
    assert dup["id"] != label["id"]
    assert dup["created_at"] > original["created_at"]
    assert dup["starred"] is False
    assert dup["last_printed_at"] is None and dup["print_count"] == 0
    assert dup["blocks"] == original["blocks"] and dup["name"] == original["name"]
    assert store.get(label["id"]) == original


def test_set_star_persists(store, tmp_path):
    label = store.create(text_doc("Star me"))
    assert store.set_star(label["id"], True)["starred"] is True
    assert LabelStore(tmp_path / "saved_labels.json").get(label["id"])["starred"] is True
    assert store.set_star(label["id"], False)["starred"] is False


def _seed(store):
    a = store.create(text_doc("banana"))
    b = store.create(text_doc("Apple"))
    c = store.create(text_doc("cherry"))
    store.record_print(text_doc("banana"), a["id"])  # a printed last
    return a["id"], b["id"], c["id"]


def test_list_sorts(store):
    a, b, c = _seed(store)
    # last_printed (default): printed first, then never-printed in list order
    assert [l["id"] for l in store.list()] == [a, c, b]
    assert [l["id"] for l in store.list(sort="created")] == [c, b, a]
    assert [l["id"] for l in store.list(sort="name")] == [b, a, c]  # case-insensitive


@pytest.mark.parametrize("sort", ["last_printed", "created", "name"])
def test_starred_first_under_every_sort(store, sort):
    a, b, c = _seed(store)
    store.set_star(c, True)
    assert store.list(sort=sort)[0]["id"] == c


def test_last_printed_puts_nulls_last(store):
    a, b, c = _seed(store)
    store.record_print(text_doc("Apple"), b)
    assert [l["id"] for l in store.list()] == [b, a, c]


def test_unknown_sort_rejected(store):
    with pytest.raises(ValueError):
        store.list(sort="size")


def test_starred_only_filter(store):
    a, b, c = _seed(store)
    store.set_star(b, True)
    assert [l["id"] for l in store.list(starred_only=True)] == [b]


def test_search_is_case_insensitive_over_name_and_all_text_blocks(store):
    doc = LabelDoc.from_json({"label_size": "11354", "name": "Pantry", "blocks": [
        {"type": "text", "text": "Flour"},
        {"type": "image", "src": "icon:star"},
        {"type": "text", "text": "best before\nJune"},
    ]})
    hit = store.create(doc)
    store.create(text_doc("Other"))
    for q in ("pantry", "FLOUR", "june", "Before"):
        assert [l["id"] for l in store.list(q=q)] == [hit["id"]], q
    assert store.list(q="nothing") == []
    assert len(store.list(q="  ")) == 2


def test_create_with_empty_name_uses_first_non_empty_line(store):
    doc = LabelDoc.from_json({"label_size": "11354", "name": "  ", "blocks": [
        {"type": "image", "src": "icon:star"},
        {"type": "text", "text": "\n  \n  Flour  \nT55"},
        {"type": "text", "text": "Second"},
    ]})
    assert store.create(doc)["name"] == "Flour"


def test_update_with_empty_name_uses_default_too(store):
    label = store.create(text_doc("One"))
    assert store.update(label["id"], text_doc("Two\nThree"))["name"] == "Two"


def test_delete_many(store):
    a, b, c = _seed(store)
    assert store.delete([a, c, "unknown"]) == 2
    assert [l["id"] for l in store.list()] == [b]


def test_failed_mutations_roll_back(store, monkeypatch):
    label = store.create(text_doc("One"))
    before = store.list()

    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(store_mod.os, "replace", boom)
    for op in (lambda: store.update(label["id"], text_doc("Two")),
               lambda: store.duplicate(label["id"]),
               lambda: store.set_star(label["id"], True),
               lambda: store.delete([label["id"]]),
               lambda: store.record_print(text_doc("One"), label["id"])):
        with pytest.raises(StoreError):
            op()
        assert store.list() == before


def test_concurrent_mutations_are_serialised(tmp_path):
    import threading

    path = tmp_path / "saved_labels.json"
    store = LabelStore(path)
    threads = [threading.Thread(target=store.create, args=(text_doc(f"L{i}"),))
               for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(store.list()) == 20
    assert len(json.loads(path.read_text(encoding="utf-8"))["labels"]) == 20


# --- record_print (R16) -----------------------------------------------------

def test_record_print_without_id_bumps_a_content_match(store):
    label = store.create(text_doc("Same"))
    doc = text_doc("Same")
    doc.blocks[0].id = "other-block-id"  # block ids do not count
    doc.copies = 5                        # nor do copies
    doc.name = "renamed"                  # nor does the name

    bumped = store.record_print(doc)
    assert bumped["id"] == label["id"]
    assert bumped["print_count"] == 1
    assert bumped["last_printed_at"] is not None
    assert bumped["name"] == label["name"]
    assert len(store.list()) == 1
    assert store.record_print(text_doc("Same"))["print_count"] == 2


def test_record_print_without_match_creates_a_printed_entry(store):
    store.create(text_doc("Same"))
    for different in (text_doc("Other"), text_doc("Same", label_size="30252"),
                      text_doc("Same", bold=True)):
        entry = store.record_print(different)
        assert entry["print_count"] == 1
        assert entry["last_printed_at"] == entry["created_at"]
    assert len(store.list()) == 4


def test_record_print_orientation_is_part_of_the_content(store):
    store.create(text_doc("Same"))
    doc = text_doc("Same")
    doc.orientation = "portrait"
    store.record_print(doc)
    assert len(store.list()) == 2


def test_record_print_with_id_bumps_that_entry(store):
    a = store.create(text_doc("A"))
    store.create(text_doc("B"))
    entry = store.record_print(text_doc("B"), a["id"])
    assert entry["id"] == a["id"] and entry["print_count"] == 1


def test_record_print_create_rolls_back_on_failure(store, monkeypatch):
    def boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(store_mod.os, "replace", boom)
    with pytest.raises(StoreError):
        store.record_print(text_doc("New"))
    assert store.list() == []
