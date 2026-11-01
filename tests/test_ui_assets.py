"""The designer page and its static assets (Alpine is vendored; no external URLs)."""

import re
from pathlib import Path

import pytest

from cups_dymo_label_printer import web_app

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ('/static/vendor/alpine.min.js', '/static/app.js', '/static/app.css')


@pytest.fixture
def client():
    web_app.app.config['TESTING'] = True
    return web_app.app.test_client()


def test_index_references_the_vendored_assets(client):
    html = client.get('/').get_data(as_text=True)
    for asset in ASSETS:
        assert asset in html


@pytest.mark.parametrize('asset', ASSETS)
def test_each_asset_is_served(client, asset):
    response = client.get(asset)
    assert response.status_code == 200
    assert len(response.data) > 100


def test_page_has_no_external_script_or_stylesheet(client):
    html = client.get('/').get_data(as_text=True)
    urls = re.findall(r'(?:src|href)\s*=\s*["\'](https?:)?//', html)
    assert urls == []
    assert 'http://' not in html and 'https://' not in html


def test_alpine_is_the_pinned_release(client):
    js = client.get('/static/vendor/alpine.min.js').get_data(as_text=True)
    assert '3.14.1' in js
    assert (ROOT / 'cups_dymo_label_printer/static/vendor/LICENSE').is_file()


def test_page_controls_are_labelled(client):
    html = client.get('/').get_data(as_text=True)
    for hook in ('data-testid="name"', 'data-testid="stock"', 'data-testid="copies"',
                 'data-testid="save"', 'data-testid="print"', 'data-testid="history"'):
        assert hook in html


def test_app_js_guards_every_local_storage_access():
    js = (ROOT / 'cups_dymo_label_printer/static/app.js').read_text()
    uses = [m.start() for m in re.finditer(r'localStorage', js)]
    assert uses
    for pos in uses:
        before = js[:pos]
        assert before.rfind('try {') > before.rfind('} catch'), pos


def test_legacy_web_app_directory_is_gone():
    assert not (ROOT / 'web_app').exists()
