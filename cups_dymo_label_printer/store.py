"""
Saved-label history (v2) over a JSON file (R12-R16, R25).

The file holds ``{"version": 2, "labels": [...]}``. A version-1 file (a bare list
of flat entries) is migrated on load and backed up byte-for-byte to
``<stem>.v1.json`` by the first write. A file that cannot be parsed loads empty
and is left untouched until the first mutation, which keeps a copy of it as
``<stem>.corrupt.json`` before writing. Every write is atomic (temp file in the
same directory + ``os.replace``); a failed write raises ``StoreError`` and
rolls the in-memory state back. One lock serialises every read and mutation.
"""

import copy
import json
import logging
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from .config import DEFAULT_FONT_SIZE
from .document import LabelDoc, TextBlock, from_flat, pt_to_px

log = logging.getLogger(__name__)

VERSION = 2


class StoreError(Exception):
    """The history file could not be written (or read for a mutation)."""


class LabelNotFound(KeyError):
    """No saved label has the given id."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace(
        '+00:00', 'Z')


def default_name(doc: LabelDoc) -> str:
    """The first non-empty line of the first text block (R25)."""
    for block in doc.blocks:
        if isinstance(block, TextBlock):
            for line in block.text.splitlines():
                if line.strip():
                    return line.strip()
            return ''
    return ''


DESIGN_FIELDS = ('name', 'label_size', 'orientation', 'copies', 'blocks')


def _named(doc: LabelDoc) -> LabelDoc:
    """A copy of ``doc`` whose empty name is replaced by its default (R25)."""
    doc = copy.deepcopy(doc)
    if not doc.name.strip():
        doc.name = default_name(doc)
    return doc


def _migrate_v1_entry(entry: dict) -> dict:
    flat = dict(entry)
    if flat.get('align') not in ('left', 'center', 'right'):
        flat['align'] = 'center'  # v1 drew unknown alignments centred
    return _entry(str(entry.get('id') or uuid.uuid4()), _named(from_flat(flat)), None)


def _entry(label_id: str, doc: LabelDoc, stamp: Optional[str]) -> dict:
    data = doc.to_json()
    return {
        'id': label_id,
        'name': data['name'],
        'label_size': data['label_size'],
        'orientation': data['orientation'],
        'copies': data['copies'],
        'starred': False,
        'created_at': stamp,
        'updated_at': stamp,
        'last_printed_at': None,
        'print_count': 0,
        'blocks': data['blocks'],
    }


def _validated_v2_entry(raw: dict) -> dict:
    if not isinstance(raw, dict) or not isinstance(raw.get('id'), str) or not raw['id']:
        raise ValueError('label needs an id')
    doc = LabelDoc.from_json(raw)
    entry = _entry(raw['id'], doc, None)
    for key in ('created_at', 'updated_at', 'last_printed_at'):
        value = raw.get(key)
        if value is not None:
            if not isinstance(value, str):
                raise ValueError(f'{key} must be a string')
            parse_timestamp(value)
        entry[key] = value
    if not isinstance(raw.get('starred', False), bool):
        raise ValueError('starred must be a boolean')
    entry['starred'] = raw.get('starred', False)
    count = raw.get('print_count', 0)
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError('print_count must be a non-negative integer')
    entry['print_count'] = count
    return entry


SORT_FIELDS = {'last_printed': 'last_printed_at', 'created': 'created_at', 'name': None}
SORTS = tuple(SORT_FIELDS)
DEFAULT_SORT = 'last_printed'


def parse_timestamp(value: str) -> datetime:
    moment = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _matches(label: dict, needle: str) -> bool:
    if not needle:
        return True
    haystacks = [label['name']] + [b['text'] for b in label['blocks'] if b['type'] == 'text']
    return any(needle in h.casefold() for h in haystacks)


def _sorted(labels: list, sort: str) -> list:
    """Starred first; then by name (A-Z) or newest timestamp first, unknown last. Stable."""
    field = SORT_FIELDS[sort]
    if field is None:
        ordered = sorted(labels, key=lambda l: l['name'].casefold())
    else:
        dated = sorted((l for l in labels if l[field]),
                       key=lambda l: parse_timestamp(l[field]), reverse=True)
        ordered = dated + [l for l in labels if not l[field]]
    return sorted(ordered, key=lambda l: not l['starred'])


class LabelStore:
    def __init__(self, path, now: Callable[[], datetime] = _utc_now):
        self._path = Path(path)
        self._now = now
        self._lock = threading.Lock()
        self._labels: list = []
        self._v1_bytes: Optional[bytes] = None       # pending v1 backup
        self._corrupt_bytes: Optional[bytes] = None  # pending copy of a lossy load
        self._unreadable = False
        self._load()

    # --- loading ------------------------------------------------------------

    def _load(self) -> None:
        try:
            with open(self._path, 'rb') as fh:
                raw = fh.read()
        except FileNotFoundError:
            return
        except OSError:
            log.exception('cannot read label history %s; mutations refused', self._path)
            self._unreadable = True
            return
        try:
            data = json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, ValueError):
            log.error('label history %s is not valid JSON; loading empty', self._path)
            self._corrupt_bytes = raw
            return
        if isinstance(data, list):
            self._labels = self._load_entries(data, _migrate_v1_entry, raw)
            self._v1_bytes = raw
            self._corrupt_bytes = None  # the v1 backup already keeps everything
        elif (isinstance(data, dict) and data.get('version') == VERSION
              and isinstance(data.get('labels'), list)):
            self._labels = self._load_entries(data['labels'], _validated_v2_entry, raw)
        else:
            log.error('label history %s has an unknown shape; loading empty', self._path)
            self._corrupt_bytes = raw

    def _load_entries(self, items: list, convert, raw: bytes) -> list:
        labels, seen = [], set()
        for item in items:
            try:
                entry = convert(item)
                if entry['id'] in seen:
                    raise ValueError(f"duplicate id {entry['id']}")
            except (ValueError, TypeError, AttributeError) as e:
                log.warning('skipping unreadable saved label in %s: %s', self._path, e)
                self._corrupt_bytes = raw
                continue
            seen.add(entry['id'])
            labels.append(entry)
        return labels

    # --- persistence --------------------------------------------------------

    def _write_atomic(self, path: Path, payload: bytes) -> None:
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f'.{path.name}.', suffix='.tmp')
        try:
            with os.fdopen(fd, 'wb') as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def _keep_copy(self, suffix: str, payload: bytes) -> None:
        """Write ``payload`` to ``<stem>.<suffix>.json`` unless already there; never overwrite."""
        stem = self._path.stem
        n = 0
        while True:
            name = f'{stem}.{suffix}.json' if n == 0 else f'{stem}.{suffix}.{n}.json'
            target = self._path.with_name(name)
            if not target.exists():
                self._write_atomic(target, payload)
                return
            if target.read_bytes() == payload:
                return
            n += 1

    def _persist(self) -> None:
        if self._unreadable:
            raise StoreError(f'label history {self._path} is unreadable; not overwriting it')
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            if self._v1_bytes is not None:
                self._keep_copy('v1', self._v1_bytes)
            if self._corrupt_bytes is not None:
                self._keep_copy('corrupt', self._corrupt_bytes)
            payload = json.dumps({'version': VERSION, 'labels': self._labels},
                                 ensure_ascii=False, indent=1).encode('utf-8')
            self._write_atomic(self._path, payload)
        except OSError as e:
            log.exception('cannot write label history %s', self._path)
            raise StoreError(f'Could not save label history: {e}') from e
        self._v1_bytes = None
        self._corrupt_bytes = None

    def _mutate(self, change: Callable[[], object]):
        """Apply ``change`` under the lock, persist, and roll back on any failure."""
        with self._lock:
            snapshot = copy.deepcopy(self._labels)
            try:
                result = change()
                self._persist()
            except BaseException:
                self._labels = snapshot
                raise
            return copy.deepcopy(result)

    # --- queries ------------------------------------------------------------

    def _find(self, label_id: str) -> dict:
        for entry in self._labels:
            if entry['id'] == label_id:
                return entry
        raise LabelNotFound(label_id)

    def get(self, label_id: str) -> dict:
        with self._lock:
            return copy.deepcopy(self._find(label_id))

    def list(self, q: Optional[str] = None, sort: str = DEFAULT_SORT,
             starred_only: bool = False) -> list:
        """Labels matching ``q`` (case-insensitive, name + every text block), starred first."""
        if sort not in SORTS:
            raise ValueError(f'Unknown sort: {sort}')
        needle = (q or '').strip().casefold()
        with self._lock:
            labels = [l for l in self._labels
                      if (not starred_only or l['starred']) and _matches(l, needle)]
            return copy.deepcopy(_sorted(labels, sort))

    # --- mutations ----------------------------------------------------------

    def _new_entry(self, doc: LabelDoc) -> dict:
        return _entry(str(uuid.uuid4()), _named(doc), _iso(self._now()))

    def create(self, doc: LabelDoc) -> dict:
        def change():
            entry = self._new_entry(doc)
            self._labels.insert(0, entry)
            return entry
        return self._mutate(change)

    def update(self, label_id: str, doc: LabelDoc) -> dict:
        """Replace a label's design in place: same id, new ``updated_at`` (R14, R25)."""
        def change():
            entry = self._find(label_id)
            entry.update({k: v for k, v in _named(doc).to_json().items() if k in DESIGN_FIELDS})
            entry['updated_at'] = _iso(self._now())
            return entry
        return self._mutate(change)

    def duplicate(self, label_id: str) -> dict:
        """A new, unstarred, never-printed copy; the original is untouched (R14)."""
        def change():
            source = self._find(label_id)
            stamp = _iso(self._now())
            entry = copy.deepcopy(source)
            entry.update(id=str(uuid.uuid4()), starred=False, created_at=stamp,
                         updated_at=stamp, last_printed_at=None, print_count=0)
            self._labels.insert(self._labels.index(source), entry)
            return entry
        return self._mutate(change)

    def set_star(self, label_id: str, starred: bool) -> dict:
        def change():
            entry = self._find(label_id)
            entry['starred'] = bool(starred)
            return entry
        return self._mutate(change)

    def delete(self, ids) -> int:
        """Delete every label whose id is in ``ids``; returns how many went."""
        wanted = set(ids)

        def change():
            before = len(self._labels)
            self._labels = [l for l in self._labels if l['id'] not in wanted]
            return before - len(self._labels)
        return self._mutate(change)

    def record_print(self, doc: LabelDoc, label_id: Optional[str] = None) -> dict:
        """Bump ``last_printed_at`` and ``print_count`` of the printed entry (R16)."""
        def change():
            entry = self._find(label_id)
            entry['last_printed_at'] = _iso(self._now())
            entry['print_count'] += 1
            return entry
        return self._mutate(change)


def flat_fields(label: dict) -> dict:
    """The v1 flat view (``text``, ``font_size`` px at 300 DPI, ``align``) of a label."""
    texts = [b for b in label['blocks'] if b.get('type') == 'text']
    first = texts[0] if texts else None
    return {
        'text': '\n'.join(b['text'] for b in texts),
        'font_size': pt_to_px(first['font_size_pt'], 300) if first else DEFAULT_FONT_SIZE,
        'align': first['align'] if first else 'center',
    }
