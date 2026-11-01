"""Drive the designer in a real browser and capture the visual-evidence screenshots.

    uv run --no-project --with playwright playwright install chromium
    uv run --no-project --with playwright python scripts/capture_visual.py [out_dir]

Starts ``scripts/dev_server.py`` (fake CUPS, scratch history and image dirs) on a free
port, runs every scenario of the acceptance rows ldx-live-preview, ldx-history-panel
and ldx-ux, asserts the limits it shows, and writes PNGs plus ``manifest.json`` (row ->
shots -> the state/interaction names each one shows) to ``out_dir``
(default ``scripts/tmp/visual``, git-ignored).
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'scripts' / 'tmp' / 'visual'
SERVER_CMD = [
    'uv', 'run', '--no-project', '--with', 'flask', '--with', 'pillow', '--with', 'cairosvg',
    '--with', 'matplotlib', 'python', str(ROOT / 'scripts' / 'dev_server.py'),
]
DESKTOP = {'width': 1100, 'height': 1000}
PHONE = {'width': 360, 'height': 900}
APP = '.app'

manifest = {}


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def api(base, method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read() or b'{}')


class Capture:
    def __init__(self, page, row):
        self.page, self.row = page, row

    def shot(self, name, shows, target=None, full=True):
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / f'{name}.png'
        if target:
            self.page.locator(target).first.screenshot(path=str(path))
        else:
            self.page.screenshot(path=str(path), full_page=full)
        manifest.setdefault(self.row, []).append({'path': str(path), 'shows': list(shows)})
        return path


def data(page, expr):
    return page.evaluate(f"() => {{ const d = Alpine.$data(document.querySelector('{APP}')); return {expr}; }}")


def settle(page):
    page.wait_for_timeout(450)
    page.wait_for_function(
        f"() => !Alpine.$data(document.querySelector('{APP}')).rendering")
    page.wait_for_timeout(100)


def open_app(page, base, stock=None, orientation=None):
    page.goto(base + '/')
    page.wait_for_selector('[data-testid=frame]')
    page.wait_for_function(f"() => Alpine.$data(document.querySelector('{APP}')).rendered.image")
    if stock:
        page.select_option('[data-testid=stock]', stock)
    if orientation and data(page, 'd.doc.orientation') != orientation:
        page.click('[data-testid=orientation]')
    settle(page)


def add_text(page, text, size=None):
    page.click('[data-testid=add-text]')
    page.fill('[data-testid=p-text]', text)
    if size is not None:
        page.fill('[data-testid=p-size]', str(size))
        page.press('[data-testid=p-size]', 'Tab')
    settle(page)


def overlay(page, index=-1):
    return page.locator('.overlay:visible').nth(index)


def nudge_to_top(page, block_index):
    """Move a vertically-centred block up with the arrow keys so a second block fits."""
    overlay(page, block_index).focus()
    for _ in range(40):
        if data(page, f"d.info(d.doc.blocks[{block_index}].id).bbox_mm[1]") <= 2.5:
            break
        page.keyboard.press('ArrowUp')
    settle(page)


def drag(page, locator, dx, dy):
    box = locator.bounding_box()
    x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + dx / 2, y + dy / 2, steps=6)
    page.mouse.move(x + dx, y + dy, steps=6)
    page.mouse.up()
    settle(page)


def live_preview(browser, base):
    ctx = browser.new_context(viewport=DESKTOP, color_scheme='light')
    page = ctx.new_page()
    cap = Capture(page, 'ldx-live-preview')

    open_app(page, base, '11354', 'landscape')
    cap.shot('preview-01-empty', ['empty label'])

    # two blocks of different sizes + type-to-update
    add_text(page, 'Flour\nT55', 16)
    nudge_to_top(page, 0)
    add_text(page, 'Best before 2027', 9)
    before = data(page, 'd.rendered.image.length') + hash(data(page, 'd.rendered.image'))
    cap.shot('preview-02-two-texts', ['two text blocks of different sizes'])
    page.fill('[data-testid=p-text]', 'Best before 2028 - keep dry')
    settle(page)
    after = data(page, 'd.rendered.image.length') + hash(data(page, 'd.rendered.image'))
    assert before != after, 'the preview did not change after typing'
    cap.shot('preview-03-type-updates', ['type in a field and see the preview update'])

    # image selected with its corner handle
    page.click('[data-testid=icons] summary')
    page.click('[aria-label="Add icon leaf"]')
    settle(page)
    assert page.locator('[data-testid=handle]:visible').count() == 1
    cap.shot('preview-04-image-selected', ['image block selected with corner handle'])

    # overflowing block with its error
    add_text(page, 'THIS TEXT IS FAR TOO WIDE FOR THE LABEL', 30)
    assert data(page, 'd.problems().some(p => p.kind === "error")')
    cap.shot('preview-05-overflow', ['overflowing block with error'])

    # 30252 frames, then 11354 portrait
    page.reload()
    page.wait_for_selector('[data-testid=frame]')
    add_text(page, 'Pantry', 14)
    page.select_option('[data-testid=stock]', '30252')
    settle(page)
    if data(page, 'd.doc.orientation') != 'landscape':
        page.click('[data-testid=orientation]')
    settle(page)
    assert data(page, 'd.canvasW') == 89 and data(page, 'd.canvasH') == 28
    cap.shot('preview-06-30252-landscape', ['30252 landscape frame'])
    page.select_option('[data-testid=stock]', '11354')
    page.click('[data-testid=orientation]')
    settle(page)
    assert data(page, 'd.canvasW') == 32 and data(page, 'd.canvasH') == 57
    cap.shot('preview-07-11354-portrait', ['11354 portrait frame'])

    # click a text block and edit it in place
    open_app(page, base, '11354', 'landscape')
    add_text(page, 'Edit me', 14)
    overlay(page).click()
    page.wait_for_selector('[data-testid=inplace]:visible')
    page.fill('[data-testid=inplace]', 'Edited in place\nsecond line')
    settle(page)
    assert data(page, 'd.doc.blocks[0].text') == 'Edited in place\nsecond line'
    cap.shot('preview-08-edit-in-place', ['click a text block and edit it in place'])
    page.keyboard.press('Escape')
    assert data(page, 'd.doc.blocks[0].text') == 'Edit me', 'Esc must cancel the edit'

    # drag to the label edge (limit)
    open_app(page, base, '11354', 'landscape')
    add_text(page, 'Drag me', 14)
    page.fill('[data-testid=p-boxwidth]', '25')
    page.press('[data-testid=p-boxwidth]', 'Tab')
    page.click('[data-testid=p-align-left]')
    settle(page)
    drag(page, overlay(page), 900, 0)
    x = data(page, 'd.doc.blocks[0].x_mm')
    assert x == 56, x  # canvas 57 mm wide minus the 1 mm that must stay on the label
    cap.shot('preview-09-drag-limit', ['drag a block to the label edge (limit)'])

    # scale an image to the label width (limit): portrait 11354 is 32 mm wide
    open_app(page, base, '11354', 'portrait')
    page.click('[data-testid=icons] summary')
    page.click('[aria-label="Add icon house"]')
    settle(page)
    overlay(page).focus()
    for _ in range(4):
        page.keyboard.press('ArrowLeft')
    settle(page)
    handle = page.locator('[data-testid=handle]:visible')
    drag(page, handle, 600, 0)
    width = data(page, 'd.doc.blocks[0].width_mm')
    assert width == data(page, 'd.canvasW') == 32, width
    cap.shot('preview-10-scale-limit', ['scale an image by its corner handle to the label width (limit)'])

    # arrow-key nudge
    open_app(page, base, '11354', 'landscape')
    add_text(page, 'Nudge', 14)
    nudge_to_top(page, 0)
    x0 = data(page, 'd.doc.blocks[0].x_mm')
    overlay(page).focus()
    for _ in range(6):
        page.keyboard.press('ArrowRight')
    settle(page)
    assert data(page, 'd.doc.blocks[0].x_mm') == x0 + 3
    cap.shot('preview-11-arrow-nudge', ['arrow-key nudge'])
    ctx.close()


def history_panel(browser, base):
    ctx = browser.new_context(viewport=DESKTOP, color_scheme='light')
    page = ctx.new_page()
    cap = Capture(page, 'ldx-history-panel')

    open_app(page, base, '11354', 'landscape')
    page.wait_for_selector('[data-testid=h-empty]:visible')
    cap.shot('history-01-empty', ['empty history'])
    page.click('[data-testid=history-toggle]')
    page.wait_for_selector('[data-testid=history]', state='hidden')
    cap.shot('history-02-collapsed', ['collapsed panel', 'collapse and expand'], target='.history')
    page.click('[data-testid=history-toggle]')
    page.wait_for_selector('[data-testid=history]:visible')
    cap.shot('history-03-expanded-again', ['collapse and expand'], target='.history')

    def block(i, text, size=14, y=None):
        return {'type': 'text', 'id': f'b{i}', 'text': text, 'x_mm': 2, 'y_mm': y, 'width_mm': None,
                'align': 'center', 'font_family': 'DejaVu Sans', 'font_size_pt': size,
                'bold': True, 'italic': False, 'underline': False, 'shrink_to_fit': False}

    seeds = [
        ('Flour', '11354', 'landscape', [block(1, 'Flour\nT55', 18)]),
        ('Sugar', '11354', 'landscape', [block(1, 'Sugar', 24)]),
        ('Return address', '30252', 'landscape', [block(1, 'A. Baker\n1 Mill Lane', 12)]),
        ('Spice jar', '11354', 'portrait',
         [block(1, 'Cumin', 16, 2), {'type': 'image', 'id': 'b2', 'src': 'icon:leaf', 'x_mm': 8, 'y_mm': 20,
                                      'width_mm': 14, 'mono': 'threshold', 'threshold': 128}]),
    ]
    ids = {}
    for name, stock, orientation, blocks in seeds:
        doc = {'label_size': stock, 'orientation': orientation, 'copies': 1, 'name': name, 'blocks': blocks}
        ids[name] = api(base, 'POST', '/labels', {'doc': doc})['label']['id']
        time.sleep(0.01)
    api(base, 'PUT', f"/labels/{ids['Sugar']}/star", {'starred': True})
    api(base, 'POST', f"/labels/{ids['Flour']}/print", {})
    page.reload()
    page.wait_for_selector('[data-testid=label-list] li')
    page.wait_for_function("() => [...document.images].filter(i => i.closest('.label-row')).every(i => i.complete && i.naturalWidth)")
    names = page.locator('.label-row .name').all_inner_texts()
    assert names[0] == 'Sugar', names  # the starred label sorts first
    cap.shot('history-04-list', ['list with starred and unstarred labels'])

    page.fill('[data-testid=h-search]', 'zzz-no-such-label')
    page.wait_for_selector('[data-testid=h-empty]:visible')
    cap.shot('history-05-no-matches', ['search with no matches'], target='.history')
    page.fill('[data-testid=h-search]', '')
    page.wait_for_function("() => document.querySelectorAll('.label-row').length === 4")

    page.check('[data-testid=h-starred]')
    page.wait_for_function("() => document.querySelectorAll('.label-row').length === 1")
    cap.shot('history-06-starred-only', ['starred-only filter on'], target='.history')
    page.uncheck('[data-testid=h-starred]')
    page.wait_for_function("() => document.querySelectorAll('.label-row').length === 4")

    # open into the editor
    page.locator('.label-row', has_text='Return address').locator('[data-testid=h-open]').click()
    settle(page)
    assert data(page, 'd.doc.name') == 'Return address' and data(page, 'd.doc.label_size') == '30252'
    assert page.locator('[data-testid=editing]').inner_text().startswith('Editing: Return address')
    cap.shot('history-07-open', ['open a label into the editor'])

    # duplicate
    page.locator('.label-row', has_text='Spice jar').locator('[data-testid=h-dup]').click()
    page.wait_for_function("() => document.querySelectorAll('.label-row').length === 5")
    cap.shot('history-08-duplicate', ['duplicate a label'])

    # re-print from history
    page.locator('.label-row', has_text='Sugar').locator('[data-testid=h-reprint]').click()
    page.wait_for_selector('[data-testid=toast]:has-text("Re-printed")')
    page.wait_for_function("() => document.querySelector('.label-row .meta').innerText.includes('printed 1x')")
    cap.shot('history-09-reprint', ['re-print from history'])

    # toggle a star and watch it move to the top
    row = page.locator('.label-row', has_text='Return address')
    assert page.locator('.label-row .name').all_inner_texts().index('Return address') > 1
    cap.shot('history-10-star-before', ['toggle a star and see it move to the top'], target='.history')
    row.locator('[data-testid=h-star]').click()
    page.wait_for_function("() => document.querySelector('.label-row .name').innerText === 'Return address'"
                           " || document.querySelectorAll('.label-row')[1].querySelector('.name').innerText === 'Return address'")
    top_two = page.locator('.label-row .name').all_inner_texts()[:2]
    assert 'Return address' in top_two, top_two
    cap.shot('history-11-star-after', ['toggle a star and see it move to the top'], target='.history')

    # multi-select delete: two rows
    page.locator('.label-row', has_text='Flour').locator('.row-check').check()
    page.locator('.label-row', has_text='Spice jar').first.locator('.row-check').check()
    cap.shot('history-12-multi-selected', ['multi-select delete'], target='.history')
    page.click('[data-testid=h-delete]')
    page.wait_for_selector('[data-testid=toast]:has-text("Deleted 2")')
    page.wait_for_function("() => document.querySelectorAll('.label-row').length === 3")
    cap.shot('history-13-multi-deleted', ['multi-select delete'], target='.history')

    # select-all then delete
    page.check('[data-testid=h-all]')
    assert page.locator('.row-check:checked').count() == 3
    cap.shot('history-14-select-all', ['select-all then delete'], target='.history')
    page.click('[data-testid=h-delete]')
    page.wait_for_selector('[data-testid=h-empty]:visible')
    cap.shot('history-15-all-deleted', ['select-all then delete'], target='.history')

    # narrow layout, with rows to show
    for name, stock, orientation, blocks in seeds[:3]:
        doc = {'label_size': stock, 'orientation': orientation, 'copies': 1, 'name': name, 'blocks': blocks}
        api(base, 'POST', '/labels', {'doc': doc})
    narrow = browser.new_context(viewport=PHONE, color_scheme='light')
    p2 = narrow.new_page()
    p2.goto(base + '/')
    p2.wait_for_selector('[data-testid=label-list] li')
    p2.wait_for_function("() => [...document.images].filter(i => i.closest('.label-row')).every(i => i.complete && i.naturalWidth)")
    assert p2.evaluate('() => document.documentElement.scrollWidth') <= 360, 'horizontal scroll at 360px'
    Capture(p2, 'ldx-history-panel').shot('history-16-narrow-360', ['narrow 360px layout'])
    narrow.close()
    ctx.close()


def ux(browser, base, scratch):
    fail_flag = Path(scratch) / 'fail'
    ctx = browser.new_context(viewport=DESKTOP, color_scheme='light')
    page = ctx.new_page()
    cap = Capture(page, 'ldx-ux')
    requests = []
    page.on('request', lambda r: requests.append(r.url) if r.url.endswith('/render') else None)

    open_app(page, base, '11354', 'landscape')
    add_text(page, 'Ready to print', 16)
    page.wait_for_function("() => document.querySelector('[data-testid=printer-badge]').innerText.includes('idle')")
    cap.shot('ux-01-light', ['light mode', 'printer status badge (ok and error)'])

    # copies stepper limits
    page.fill('[data-testid=copies]', '150')
    page.press('[data-testid=copies]', 'Tab')
    assert data(page, 'd.doc.copies') == 99 and page.is_disabled('[data-testid=copies-inc]')
    cap.shot('ux-02-copies-99', ['copies stepper at 1 and 99 (limits)'], target='.toolbar')
    page.fill('[data-testid=copies]', '0')
    page.press('[data-testid=copies]', 'Tab')
    assert data(page, 'd.doc.copies') == 1 and page.is_disabled('[data-testid=copies-dec]')
    cap.shot('ux-03-copies-1', ['copies stepper at 1 and 99 (limits)'], target='.toolbar')

    # Ctrl+Enter prints
    page.click('body', position={'x': 5, 'y': 5})
    page.keyboard.press('Control+Enter')
    page.wait_for_selector('[data-testid=toast]:has-text("Sent 1 copy")')
    assert data(page, 'd.editingId') is not None
    cap.shot('ux-04-ctrl-enter-prints-success-toast', ['Ctrl/Cmd+Enter prints', 'success toast'])

    # Ctrl+P re-renders without the browser print dialog
    page.evaluate("() => { window.__prevented = null; window.addEventListener('keydown', e => { if (e.key.toLowerCase() === 'p') window.__prevented = e.defaultPrevented; }); }")
    before = len(requests)
    page.keyboard.press('Control+P')
    page.wait_for_function("() => window.__prevented === true")
    page.wait_for_timeout(150)
    assert len(requests) == before + 1, 'Ctrl+P must trigger one immediate /render'
    cap.shot('ux-05-ctrl-p-rerender', ['Ctrl/Cmd+P re-renders without the browser print dialog'])

    # failure toast + badge error (fake printer refuses)
    fail_flag.write_text('1')
    page.keyboard.press('Control+Enter')
    page.wait_for_selector('[data-testid=toast].error')
    page.evaluate(f"() => Alpine.$data(document.querySelector('{APP}')).pollStatus()")
    page.wait_for_function("() => document.querySelector('[data-testid=printer-badge]').classList.contains('err')")
    cap.shot('ux-06-failure-toast-and-error-badge', ['failure toast', 'printer status badge (ok and error)'])
    fail_flag.unlink()

    # reload restores last stock, font and orientation
    page.select_option('[data-testid=stock]', '30252')
    page.click('[data-testid=orientation]')  # 30252 defaults to portrait; this makes it landscape
    page.click('.canvas-pane .frame', position={'x': 30, 'y': 6})  # deselect so the defaults show
    page.select_option('[data-testid=default-font]', 'DejaVu Serif')
    settle(page)
    page.reload()
    page.wait_for_selector('[data-testid=frame]')
    page.wait_for_function("() => Alpine.$data(document.querySelector('.app')).fonts.length > 0")
    page.wait_for_timeout(200)
    assert page.input_value('[data-testid=stock]') == '30252'
    assert data(page, 'd.doc.orientation') == 'landscape'
    assert page.input_value('[data-testid=default-font]') == 'DejaVu Serif'
    cap.shot('ux-07-reload-restores', ['reload restores last stock, font and orientation'])
    ctx.close()

    # dark mode (system scheme) and the manual toggle
    dark = browser.new_context(viewport=DESKTOP, color_scheme='dark')
    p = dark.new_page()
    open_app(p, base, '11354', 'landscape')
    add_text(p, 'Dark mode', 16)
    assert data(p, 'd.theme') == 'dark'
    Capture(p, 'ldx-ux').shot('ux-08-dark', ['dark mode'])
    p.click('[data-testid=theme]')
    assert data(p, 'd.theme') == 'light'
    p.click('[data-testid=theme]')
    assert data(p, 'd.theme') == 'dark'
    dark.close()

    # 360 px phone width
    phone = browser.new_context(viewport=PHONE, color_scheme='light')
    p = phone.new_page()
    open_app(p, base, '11354', 'landscape')
    add_text(p, 'Phone', 16)
    assert p.evaluate('() => document.documentElement.scrollWidth') <= 360, 'horizontal scroll at 360px'
    Capture(p, 'ldx-ux').shot('ux-09-phone-360', ['360px phone width'])
    phone.close()


def main():
    scratch = tempfile.mkdtemp(prefix='ldx-visual-')
    port = free_port()
    env = dict(os.environ, LABEL_MEMORY_FILE=str(Path(scratch) / 'saved_labels.json'),
               LABEL_IMAGE_DIR=str(Path(scratch) / 'images'), FAKE_CUPS_DIR=scratch)
    env.pop('LABEL_FONT_DIRS', None)
    server = subprocess.Popen(SERVER_CMD + [str(port)], env=env, cwd=ROOT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f'http://127.0.0.1:{port}'
    try:
        for _ in range(120):
            try:
                urllib.request.urlopen(base + '/status', timeout=1)
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise SystemExit('dev server did not start')
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            live_preview(browser, base)
            history_panel(browser, base)
            ux(browser, base, scratch)
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(f'{sum(len(v) for v in manifest.values())} screenshots -> {OUT}')


if __name__ == '__main__':
    main()
