"""Font catalog, scanning and fallback chain (R1, R3)."""

import os
from pathlib import Path

import pytest
from PIL import ImageFont

from cups_dymo_label_printer import fonts

FIXTURES = Path(__file__).parent / "fixtures" / "fonts"


@pytest.fixture()
def fixture_fonts(monkeypatch):
    monkeypatch.setenv("LABEL_FONT_DIRS", str(FIXTURES))
    fonts.reset_cache()
    yield
    fonts.reset_cache()


@pytest.fixture()
def empty_fonts(monkeypatch, tmp_path):
    monkeypatch.setenv("LABEL_FONT_DIRS", str(tmp_path))
    fonts.reset_cache()
    yield
    fonts.reset_cache()


def test_list_fonts_reports_only_families_with_files(fixture_fonts):
    assert fonts.list_fonts() == [
        {"family": "Liberation Sans", "styles": ["regular", "bold"]}
    ]


def test_catalog_has_the_eight_curated_families():
    assert list(fonts.CATALOG) == [
        "DejaVu Sans", "DejaVu Serif", "DejaVu Sans Mono",
        "Liberation Sans", "Liberation Serif", "Liberation Mono",
        "Noto Sans", "Noto Serif",
    ]


def test_scan_is_recursive_and_multiple_dirs(monkeypatch, tmp_path):
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    (nested / "LiberationSans-Regular.ttf").write_bytes(
        (FIXTURES / "LiberationSans-Regular.ttf").read_bytes()
    )
    monkeypatch.setenv(
        "LABEL_FONT_DIRS", os.pathsep.join([str(tmp_path), "/nonexistent-dir"])
    )
    fonts.reset_cache()
    assert fonts.list_fonts() == [{"family": "Liberation Sans", "styles": ["regular"]}]
    fonts.reset_cache()


def test_resolve_exact_style(fixture_fonts):
    r = fonts.resolve("Liberation Sans", bold=True, italic=False)
    assert Path(r.path).name == "LiberationSans-Bold.ttf"
    assert r.style == "bold"
    assert r.substituted is False


def test_resolve_nearest_style_when_missing(fixture_fonts):
    r = fonts.resolve("Liberation Sans", bold=True, italic=True)
    assert Path(r.path).name == "LiberationSans-Bold.ttf"
    assert r.style == "bold"
    assert r.substituted is False
    r = fonts.resolve("Liberation Sans", bold=False, italic=True)
    assert Path(r.path).name == "LiberationSans-Regular.ttf"


def test_unknown_family_falls_back_to_first_available(fixture_fonts):
    # DEFAULT_FONT_FAMILY (DejaVu Sans) is absent from the fixture dir too.
    r = fonts.resolve("Noto Serif", bold=False, italic=False)
    assert Path(r.path).name == "LiberationSans-Regular.ttf"
    assert r.substituted is True


def test_unknown_family_falls_back_to_default_family(monkeypatch, tmp_path):
    dejavu = tmp_path / "DejaVuSans.ttf"
    dejavu.write_bytes((FIXTURES / "LiberationSans-Regular.ttf").read_bytes())
    monkeypatch.setenv("LABEL_FONT_DIRS", str(tmp_path))
    fonts.reset_cache()
    # Pretend DejaVu Sans regular is present (name is what the scan keys on).
    r = fonts.resolve("Nonexistent Family", bold=True, italic=False)
    assert Path(r.path).name == "DejaVuSans.ttf"
    assert r.substituted is True
    fonts.reset_cache()


def test_empty_dirs_fall_back_to_pil_default(empty_fonts):
    r = fonts.resolve("Liberation Sans", bold=False, italic=False)
    assert r.path is None
    assert r.substituted is True
    assert fonts.list_fonts() == []
    font = fonts.load("Liberation Sans", False, False, 30)
    assert isinstance(font, (ImageFont.ImageFont, ImageFont.FreeTypeFont))


def test_load_returns_truetype_for_resolved_file(fixture_fonts):
    font = fonts.load("Liberation Sans", True, False, 40)
    assert isinstance(font, ImageFont.FreeTypeFont)
    assert font.size == 40


def test_opened_fonts_are_cached(fixture_fonts):
    a = fonts.load("Liberation Sans", True, False, 40)
    b = fonts.load("Liberation Sans", True, False, 40)
    assert a is b
    assert fonts.load("Liberation Sans", True, False, 41) is not a
