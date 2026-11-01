"""Run the designer against a fake CUPS, for local browsing and the visual capture.

    LABEL_MEMORY_FILE=... LABEL_IMAGE_DIR=... python scripts/dev_server.py [port]

Touch ``$FAKE_CUPS_DIR/fail`` (default: beside LABEL_MEMORY_FILE) to make the fake
printer report an error and refuse jobs; remove it to heal.
"""

import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

memory = Path(os.environ.setdefault('LABEL_MEMORY_FILE', str(ROOT / 'scripts' / 'tmp' / 'dev' / 'saved_labels.json')))
os.environ.setdefault('LABEL_IMAGE_DIR', str(memory.parent / 'images'))
os.environ.setdefault('LABEL_FONT_DIRS', str(ROOT / 'tests' / 'fixtures' / 'fonts'))
memory.parent.mkdir(parents=True, exist_ok=True)
FAIL_FLAG = Path(os.environ.get('FAKE_CUPS_DIR', memory.parent)) / 'fail'


class FakeConnection:
    """Stands in for ``cups.Connection``; jobs are counted, not printed."""

    jobs = 0

    def printFile(self, *_, **__):
        if FAIL_FLAG.exists():
            raise RuntimeError('CUPS is not accepting jobs (fake)')
        FakeConnection.jobs += 1
        return FakeConnection.jobs

    def getPrinters(self):
        if FAIL_FLAG.exists():
            raise RuntimeError('printer offline (fake)')
        return {'dymo': {'state': 'idle'}}


sys.modules['cups'] = types.SimpleNamespace(Connection=FakeConnection)

from cups_dymo_label_printer.web_app import run_app  # noqa: E402

if __name__ == '__main__':
    run_app(host='127.0.0.1', port=int(sys.argv[1]) if len(sys.argv) > 1 else 5000)
