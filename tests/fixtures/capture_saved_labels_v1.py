"""Provenance of ``saved_labels_v1.json``: a capture, not a construction.

The fixture was produced by running the pre-v2 code (commit bb908be) itself:

    mkdir -p /tmp/v1/pkg
    git archive bb908be cups_dymo_label_printer | tar -x -C /tmp/v1/pkg
    uv run --no-project --with flask --with pillow python -I \
        tests/fixtures/capture_saved_labels_v1.py /tmp/v1/pkg /tmp/v1/saved_labels_v1.json

It calls that version's ``_save_label`` on two payloads; ``_save_label`` inserts at
the top, so the file lists them newest first. Not collected by pytest.
"""

import os
import sys
import types

pkgdir, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, pkgdir)
sys.modules['cups'] = types.SimpleNamespace(Connection=lambda: None)
os.environ['LABEL_MEMORY_FILE'] = out

from cups_dymo_label_printer import web_app  # noqa: E402  (the bb908be copy)

web_app._save_label({'text': 'Flour\nT55', 'label_size': '30252', 'font_size': 60,
                     'align': 'left', 'copies': 2})
web_app._save_label({'text': 'Kitchen jar', 'label_size': '11354', 'font_size': 40,
                     'align': 'center', 'copies': 1})
