"""Smoke test: the package imports with no per-test cups stub (CI has no pycups)."""


def test_package_imports_without_pycups():
    import cups_dymo_label_printer.web_app as web_app

    assert web_app.app is not None
