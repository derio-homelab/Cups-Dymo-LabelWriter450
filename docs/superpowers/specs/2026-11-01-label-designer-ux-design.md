# Label designer UX — design

Issue: derio-homelab/Cups-Dymo-LabelWriter450#2. Base: `bb908be`.

## Context

The designer (`cups_dymo_label_printer`, Flask on :5000) renders one text block in one font
(`label_generator.py:create_label_image`), previews it as a PNG below the form via a button
(`web_app.py:/preview`), fixes the canvas to the stock's `width_mm × height_mm`
(`config.py:LABEL_SIZES`), and saves every print to `saved_labels.json` (`web_app.py:_save_label`,
de-duplicated on `(text, label_size, font_size, align, copies)`) without any UI for it. The
top-level `web_app/` is an unused legacy copy; `setup.sh` runs `python3 -m
cups_dymo_label_printer.web_app`. CI (`.github/workflows/`) builds the image and lints; pytest
never runs in CI.

## Requirements

R1. `GET /fonts` lists a curated catalog of families — DejaVu Sans, DejaVu Serif, DejaVu Sans Mono, Liberation Sans, Liberation Serif, Liberation Mono, Noto Sans, Noto Serif — each with the styles (`regular`, `bold`, `italic`, `bold-italic`) whose files were found by scanning the directories in `FONT_DIRS` (env `LABEL_FONT_DIRS`, default `/usr/share/fonts`); a family with no file found is omitted, and code names font files, never absolute font paths (`DEFAULT_FONT_PATH` is replaced by `DEFAULT_FONT_FAMILY = 'DejaVu Sans'`, bold).
R2. A label holds any number of blocks; each text block has its own family, size in points (a number, fractions allowed), bold, italic, underline and alignment, so one label can mix sizes and styles.
R3. A bold/italic request for a family that lacks that style renders the nearest available style, and the editor disables the toggles the chosen family does not support; underline is drawn by the renderer for every family. A family that is not installed falls back to `DEFAULT_FONT_FAMILY`, then to the first available catalog family, then to PIL's default font, and the render reports `font_substituted: true` for that block instead of failing.
R4. Text blocks lay out multi-line text line by line using the font's line height, each line aligned within the block's box.
R5. An image block shows an uploaded PNG, JPEG or SVG, or one of a built-in set of about 20 MIT-licensed SVG icons shipped in the package (listed by `GET /icons` as `[{name, url}]`), at a position and width (aspect ratio kept) set per block.
R6. `POST /images` accepts an upload up to `LABEL_MAX_UPLOAD_MB` (default 5) — larger is refused with 413, any other type with 400 — and stores it content-addressed (sha256) in `LABEL_IMAGE_DIR` (default: an `images/` directory beside `LABEL_MEMORY_FILE`), so saved labels that use it survive restarts.
R7. Each image block chooses `threshold` (level 0–255, default 128) or `dither` (Floyd–Steinberg) conversion; the rendered label is pure black-and-white (PIL mode `1`), and the preview shows exactly that output.
R8. `POST /render` renders a label document with the same renderer `/print` uses and returns JSON `{success, image: "data:image/png;base64,…", width_mm, height_mm, blocks: [{id, bbox_mm: [x, y, w, h], overflow, font_substituted, missing}]}` — `bbox_mm` measured from the label's top-left as designed; `missing` marks an image block whose file is gone (nothing is drawn for it in the PNG; the editor overlay outlines it); `/preview` keeps working as a compatibility alias for the old single-text payload, returning `{success, image}` as today.
R9. The designer shows the render inside a frame drawn at the stock's real aspect ratio with the label's outline and rounded corners, re-rendering debounced (~250 ms) after any change of text or setting.
R10. On the preview the user can click a text block to edit its text in place (a `<textarea>` overlaid on the block's box, plain text with `\n` newlines), drag any block to move it, drag an image's corner handle to scale it, and nudge the selected block with the arrow keys (0.5 mm per press).
R11. Each label has an orientation named by the canvas's shape: `portrait` (taller than wide: short edge × long edge of the stock) or `landscape` (wider than tall); a new label defaults to the shape of the stock's `width_mm × height_mm` (portrait for 30252, landscape for 11354). The preview shows the design as drawn; before submission to CUPS the rendered image is rotated 90° when its aspect differs from the stock's CUPS media (`wNNNhNNN`), and the job is sent with `orientation-requested=3` (portrait, no CUPS auto-rotation) beside the existing `fit-to-page`, so the printed result matches the preview; orientation is saved and restored with the label.
R12. `saved_labels.json` holds `{"version": 2, "labels": [...]}`; each label has `id`, `name`, `label_size`, `orientation`, `copies`, `starred`, `created_at`, `updated_at`, `last_printed_at`, `print_count` and `blocks`; an old version-1 list loads as one centred text block per entry (DejaVu Sans Bold, its pixel `font_size` converted to `px × 72 / 300` points, its `align`), orientation the stock's shape, with unknown (`null`) timestamps, in its original order, and the first write keeps a `saved_labels.v1.json` backup.
R13. A `/labels` API lists (with text search over name and all text blocks, case-insensitive; sort `last_printed` (default), `created` or `name`; a `starred` filter), creates, reads, updates in place (including `name`), deletes (one or many), duplicates, stars/unstars, and re-prints a saved label, and serves `GET /labels/<id>/thumbnail.png` (the renderer's output at 100 DPI; a missing image is simply absent from it). `GET /memory` keeps working as a compatibility alias returning the labels in the active default sort as a list of v2 labels each also carrying the flat fields `text` (its text blocks joined by `\n`), `font_size` (the first text block's size in pixels) and `align`; `DELETE /memory {ids}` returns `{success, remaining}` in that same shape.
R14. Updating a saved label keeps its `id` and sets a new `updated_at`; Duplicate creates a new entry (new `id`, new `created_at`, unstarred, never printed) from a copy and leaves the original untouched.
R15. Starred labels sort above unstarred ones under every sort, and the star state is persisted.
R16. Printing a design opened from history saves it in place, then prints it, and bumps that entry's `last_printed_at` and `print_count`; printing an unsaved design bumps the existing entry whose content (blocks, stock, orientation) is identical, otherwise creates a new entry; the response names the entry, and the editor keeps editing it. If saving fails before printing, nothing prints and the call fails (500); if the history write fails after CUPS accepted the job, the call succeeds with the job id and a `warning` that history was not updated.
R17. A history panel, collapsible, lists saved labels with a renderer-made thumbnail each, search, sort, a *Starred only* filter, a star toggle, Open (re-fills the editor), Duplicate, Re-print without opening, a checkbox per label, select-all and Delete of the selection — implementing the *Saved labels* scenarios of `Acceptance_Tests.md`, which this change rewrites for the block model, re-print bumping and starred-first sorting (see Testing).
R18. Ctrl/⌘+Enter prints and Ctrl/⌘+P re-renders the preview (suppressing the browser's print dialog).
R19. The editor shows a printer status badge from `/status`, toast messages for print success and failure, and an error for a block that overflows the label; a per-block *shrink to fit* option reduces its size (down to 6 pt) until it fits instead.
R20. The page is usable at 360 px width, follows the system dark/light scheme with a manual toggle, has a copies stepper (1–99), and remembers the last-used stock, font and orientation in the browser.
R21. The legacy top-level `web_app/` is removed, leaving one UI.
R22. The Docker image installs the fonts (`fonts-dejavu-core`, `fonts-liberation`, `fonts-noto-core`) and the SVG rasterizer (`python3-cairosvg`), and `docker build` stays green in CI.
R23. CI runs the pytest suite on every push.
R24. `Acceptance_Tests.md` gains scenarios for fonts, images, preview, orientation, history, stars and general UX.
R25. The editor has a name field for the label; a label saved with an empty name gets the first non-empty line of its first text block, and renaming is a normal in-place update.

## Design

### Stack

- Backend: Flask (existing), Pillow, `cairosvg` for SVG rasterization. No database: the JSON file
  stays the only persistent state, plus the image directory.
- Frontend: Alpine.js 3 **vendored** into `cups_dymo_label_printer/static/vendor/alpine.min.js`
  (no CDN, no build step), plain ES modules and CSS in `static/`. The container blocks DNS and a
  LAN client may be offline, so nothing is fetched from the internet at runtime.

### Modules

| Module | Responsibility |
| --- | --- |
| `fonts.py` | Curated catalog (family → style → file name candidates); scans `FONT_DIRS` once (cached), `list_fonts()`, `resolve(family, bold, italic) -> (path, synthetic_underline)` with nearest-style fallback (R1, R3). |
| `document.py` | Label document dataclasses/validation: `LabelDoc`, `TextBlock`, `ImageBlock`; `from_json`/`to_json`; content key for de-duplication; v1 → v2 migration (R12). |
| `label_generator.py` | `render(doc, dpi=300) -> RenderResult(image, blocks=[{id, bbox_mm, overflow, font_substituted, missing}])`; the old `create_label_image(text, ...)` stays as a thin wrapper building a one-block doc and returning `render(...).image.convert('RGB')` (still pure black/white pixels), so its existing callers and tests keep their RGB contract. Text layout per line (R4), underline, shrink-to-fit (R19), images via `images.py` (R5, R7), canvas from stock + orientation (R11). Final image converted to mode `1` (text thresholded at 128; image blocks pre-converted per their mode). |
| `images.py` | Upload validation (size, type sniffed from bytes, not the extension), sha256 storage in `LABEL_IMAGE_DIR`, icon lookup in `static/icons/*.svg`, load-to-PIL (SVG via cairosvg at target px width), mono conversion (R6, R7). |
| `store.py` | `LabelStore` over the JSON file: load+migrate, list(q, sort, starred), create, get, update, delete(ids), duplicate, set_star, record_print(doc, id=None) implementing R14–R16. Timestamps ISO-8601 UTC. Atomic write (temp file + `os.replace`). Thread lock around mutations. |
| `printer_service.py` | `print_image` gains rotation to the media aspect (R11) — pure helper `orient_for_media(image, label_size)` unit-tested; CUPS options gain `orientation-requested: '3'` (unit-tested for both orientations), the rest unchanged. |
| `web_app.py` | Routes: `/`, `/fonts`, `/icons`, `/images` (POST, GET `/images/<name>`), `/render`, `/preview` (compat), `/print`, `/status`, `/labels` (GET list, POST create, DELETE `{ids}`), `/labels/<id>` (GET, PUT, DELETE), `/labels/<id>/duplicate` (POST), `/labels/<id>/star` (PUT `{starred}`), `/labels/<id>/print` (POST), `/labels/<id>/thumbnail.png` (GET), `/memory` (compat). |

### Document schema (v2)

```json
{
  "version": 2,
  "labels": [{
    "id": "uuid", "name": "Kitchen jar",
    "label_size": "30252", "orientation": "landscape", "copies": 1,
    "starred": false,
    "created_at": "2026-11-01T18:00:00Z", "updated_at": "…", "last_printed_at": "…",
    "print_count": 3,
    "blocks": [
      {"type": "text", "id": "b1", "text": "Flour\nT55", "x_mm": 2, "y_mm": 2,
       "width_mm": null, "align": "center", "font_family": "DejaVu Sans",
       "font_size_pt": 14, "bold": true, "italic": false, "underline": false,
       "shrink_to_fit": false},
      {"type": "image", "id": "b2", "src": "upload:3f2a….png", "x_mm": 60, "y_mm": 4,
       "width_mm": 20, "mono": "dither", "threshold": 128}
    ]
  }]
}
```

- Coordinates are mm from the top-left of the label **as designed** (after orientation).
  `width_mm: null` = label width minus 2 mm margins. `y_mm: null` = vertically centred (used by
  migrated entries, so they render as before).
- `src` is `upload:<sha256>.<ext>` or `icon:<name>`; uploads referenced by no label are kept
  (no GC in this change).
- Font size: points, a float (`9.6` is valid); pixels = `round(pt × dpi / 72)`. Migration and
  the flat-payload compat path (whose `font_size` is pixels) convert with `px × 72 / 300`, so a
  migrated label renders at exactly its old pixel size (unit-tested round trip).
- `name` is set by the editor's name field; when saved empty it is filled with the first
  non-empty line of the first text block (R25).
- Orientation: `portrait` canvas = `(min(w, h), max(w, h))` mm, `landscape` = `(max, min)`.
- Content key for R16: canonical JSON of `label_size`, `orientation` and `blocks` with block `id`s
  stripped (copies excluded).

### Print and preview

`/render` and `/print` both call `label_generator.render`. `/print` body: `{doc, id?, copies}`.
With `id` → `store.update(id, doc)` (failure → 500, nothing printed) then print then
`record_print`; without → print then `record_print(doc)`, which bumps a content match or creates.
A `record_print` failure after a successful print returns 200 `{success: true, job_id, warning}`.
Response: `{success, job_id, label, warning?}`. The old flat payload (`text`, `label_size`,
`font_size` in px, `align`, `copies`) stays **accepted** by `/print` and `/preview` and is
converted with the migration helper (`/print` with empty text still 400 `No text provided`; a doc
with no non-empty text block and no image block likewise). Behaviour around it changes as listed
under Testing.

Orientation at print: `orient_for_media` compares the rendered image's aspect with the media's
`wNNNhNNN`; if they differ it rotates 90° (direction fixed in code, confirmed on paper by the
post-merge Test Plan). The job carries `orientation-requested=3` so the cups-filters image path
does not auto-rotate the already-oriented image a second time; `fit-to-page` stays.

### Editor UI

One page (`templates/index.html` + `static/app.js`, `static/app.css`), Alpine component:

- **Toolbar**: label name field, stock select, orientation toggle, copies stepper, Save, Print,
  printer badge, theme toggle.
- **Canvas**: the label frame (CSS aspect-ratio from the stock+orientation, outline, radius ~
  2 mm scaled), the `/render` PNG as background, and an absolutely-positioned overlay `div` per
  block from the returned `bbox_mm` (a `missing` image block gets a dashed outline here, never in
  the PNG). Click a text overlay → a `<textarea>` in place (plain text, `\n` newlines);
  pointer-drag moves (`x_mm/y_mm` from pointer delta ÷ px-per-mm); image corner handle scales;
  arrows nudge 0.5 mm. Every change → debounced render. Overflowing blocks get a red outline +
  message.
- **Block inspector** (side panel; stacks below on narrow screens): add text / add image (upload
  or icon picker), font family (from `/fonts`), size, B/I/U (disabled when unsupported),
  alignment, shrink to fit, image mono mode + threshold, delete block, block order.
- **History panel**: collapsible; search box, sort select, starred-only toggle, select-all,
  Delete selected; per row thumbnail (`GET /labels/<id>/thumbnail.png`, cache-busted by
  `updated_at`), name, last printed, star, Open, Duplicate, Re-print, checkbox.
- Toasts, Ctrl/⌘+Enter / Ctrl/⌘+P, `localStorage` (try/catch) for last stock/font/orientation
  and theme. Editing state shows "Editing: <name>" with an unsaved marker; Save button does
  `PUT` (or `POST` when unsaved).

### Infra

- Dockerfile runtime stage: `fonts-dejavu-core fonts-liberation fonts-noto-core
  python3-cairosvg`; pyproject adds `cairosvg` (pip resolves to the apt one through
  `--system-site-packages`).
- CI: new `Tests` workflow — ubuntu-latest, Python 3.12, `apt-get install fonts-dejavu-core
  fonts-liberation libcairo2`, `pip install flask pillow cairosvg pytest pytest-cov pytest-mock`,
  `pytest`. Tests that need a real font point `LABEL_FONT_DIRS` at a vendored OFL fixture
  (`tests/fixtures/fonts/`: Liberation Sans 2.x regular + bold, with its `LICENSE` (SIL OFL 1.1)
  beside it) so they pass on any host. A `tests/conftest.py` installs a fake `cups` module in
  `sys.modules` for the whole session, so no test needs pycups (the CI job installs none).
- Delete `web_app/`; README notes the single UI and the new env vars.

### Error handling

- Invalid doc (unknown stock, unknown block type, bad numbers) → 400 with a message.
- Missing image file / unknown icon → nothing is drawn for the block, `/render` reports it
  `missing: true` (the editor outlines it), and `/print` returns 400 naming the block.
- Unknown font family → fallback chain of R3, reported as `font_substituted`, never an error.
- Persistence failures are no longer silent: logged, and the API returns 500 for the mutating
  call (the in-memory state is rolled back) — except the post-print history write of R16, which
  returns success with a `warning`.

### Testing

Unit tests per module: fonts catalog + fallback, document validation + migration (an old v1 file
fixture), renderer (dimensions per stock × orientation, multi-line heights, underline pixels,
mixed sizes, image threshold vs dither produce pure 1-bit, shrink-to-fit, overflow flag),
`orient_for_media` + print options, store (edit keeps id, duplicate new id, stars float, sorts,
search, content-match bump, backup on migration, atomic write, name defaulting), routes (status
codes, upload limits, `/render` shape, `/icons`, thumbnail, `/memory` alias shape, print
save-failure vs history-write-failure paths), font fallback chain, fractional-pt round trip.
The UI is checked in a browser against the Flask app with stubbed CUPS (visual evidence per the
UI rows).

Existing expectations this change deliberately rewrites:

| Where | Today | After |
| --- | --- | --- |
| `tests/test_web_app.py:182` | re-print of identical content gets a new id | keeps the same id, `print_count` 2 |
| `tests/test_web_app.py:183,240,275` | flat `text` read from `/memory` / the file | `/memory` still carries flat `text`; the file read goes through `labels[...]` blocks |
| `tests/test_web_app.py:239` | file is a bare list | file is `{"version": 2, "labels": [...]}` |
| `Acceptance_Tests.md` *Should store printed labels…* | remove + re-insert at top | re-print bumps `last_printed_at`; content match bumps instead of duplicating |
| `Acceptance_Tests.md` *Should allow selecting a saved label…* | re-fills text/font_size/align | re-fills the editor's blocks, stock, orientation, copies, name |
| `Acceptance_Tests.md` *Should load saved labels…* | most recent first | starred first, then the active sort (default last printed) |

`tests/test_label_generator.py:24-25` (RGB, white corner) stay valid through the wrapper.

## Verification

gate: tester
- ldx-print-orientation: live — whether landscape text reads the right way on 30252 Address and 11354 Multipurpose stock is only visible on paper from the real LabelWriter 450
- ldx-print-mono: live — how threshold vs dither output looks on thermal paper can only be judged on a physical print

## Test Plan

Post-merge, operator-driven, on the real LabelWriter 450:

1. Deploy the image (`docker compose up --build -d`); open `:5000`.
2. 30252 Address, landscape, two text blocks of different sizes → print; the printed label
   matches the preview (text runs along the 89 mm edge, same way up as on screen).
3. Same design in portrait → print; matches the preview.
4. 11354 Multipurpose, landscape and portrait → print each; both match their previews.
5. Add an uploaded photo with `dither` and an icon with `threshold` → print; both are legible
   and match the preview.
6. Restart the container; the history still lists the labels with their images and
   orientation; Re-print one from history.
</content>
</invoke>

## Implementation Plans

| Plan | Repo | File | Depends on |
|------|------|------|------------|
| 2026-11-01-label-designer-ux | `derio-homelab/Cups-Dymo-LabelWriter450` | `2026-11-01-label-designer-ux` | — |
