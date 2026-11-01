"""Session-wide test setup: a fake ``cups`` module so no test needs pycups."""

import sys
import types


class _FakeConnection:
    def __init__(self):
        self.printers = {"dymo": {"state": "idle"}}

    def printFile(self, *_, **__):
        return 1

    def getPrinters(self):
        return self.printers


# Installed at import time, before any package module is collected/imported.
sys.modules["cups"] = types.SimpleNamespace(Connection=_FakeConnection)
