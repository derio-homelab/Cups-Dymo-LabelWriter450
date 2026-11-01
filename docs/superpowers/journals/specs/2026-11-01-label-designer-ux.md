<!-- fr:journal-schema=3 -->
# Journal: 2026-11-01-label-designer-ux

<!-- fr:journal kind=discovery scope=spec id=operator-brief created=2026-11-01T18:43:18+00:00 input=true -->
### operator-brief · discovery · Operator brief: issue #2 verbatim

# Label designer UX: fonts, images, live in-label preview, landscape/portrait, browsable history (edit in place / duplicate), starred labels

## Goal

Make the label designer (`cups_dymo_label_printer`, the Flask app on :5000) good enough that people reach for it instead of a word processor: rich labels, a preview that **is** the label, both orientations, and a history you can actually browse, re-use and curate.

## Today (as of `bb908be`)

- **Content:** one text block per label, one font. `label_generator.py` always loads `DEFAULT_FONT_PATH` (DejaVuSans-Bold) at `font_size`, falling back to PIL's default font. There are no images.
- **Layout:** `create_label_image()` sizes the canvas from `LABEL_SIZES[...]['width_mm'/'height_mm']` at 300 DPI, so orientation is fixed per stock. For example, the 30252 Address label renders 28 × 89 mm portrait.
- **Preview:** a separate *Preview Label* button POSTs to `/preview` and shows the returned PNG **below** the form. It doesn't update as you type, and it isn't shown in the shape of the physical label.
- **History:** the backend already saves every printed label (`_save_label`, de-duplicated on `(text, label_size, font_size, align, copies)`, newest first). It persists it to `LABEL_MEMORY_FILE` and serves it at `GET/DELETE /memory`. **The page has no history UI at all:** neither template calls `/memory`. `Acceptance_Tests.md` already specifies one (expand/collapse, select to re-fill, delete, multi-select delete, select-all), but it was never built. Users conclude there is no save function.
- Saved entries carry no timestamps, so there's nothing to sort or show besides insertion order.
- `web_app/` (top-level `app.py` and `templates/index.html`) appears to be a legacy copy. `setup.sh` starts `python3 -m cups_dymo_label_printer.web_app`.

## Requests

### 1. Fonts
- [ ] Choose a font family (and weight) per text block from a curated set installed in the image (e.g. DejaVu, Liberation, Noto; list them via an endpoint, don't hard-code paths).
- [ ] Bold, italic and underline where the family supports them.
- [ ] Mixed sizes on one label (e.g. a large title line plus a small subtitle).

### 2. Images
- [ ] Add an image (upload PNG/JPEG/SVG, or pick from a small built-in icon set) and position and scale it.
- [ ] Render for the printer: monochrome thermal at 300 DPI, so convert with a threshold or dithering choice and show that result in the preview.
- [ ] Bounded upload size, and images stored next to the saved labels (not only in memory), so history entries that use them survive restarts.

### 3. Live preview *in* the label
- [ ] The preview is the label: drawn at the stock's real aspect ratio with the label's outline and rounded corners, and updated as you type or change any setting (debounced).
- [ ] What you see is what prints: the preview comes from the same renderer as `/print`, server-side, so fonts and dithering match exactly.
- [ ] Optional: edit directly on the preview (click a text block to edit it; drag to move a block or image).

### 4. Landscape and portrait
- [ ] An orientation toggle per label. Landscape rotates the canvas, and the job is sent so the printed result matches the preview (verify with the 30252 Address and 11354 Multipurpose stocks).
- [ ] Orientation is saved with the label and restored when the label is re-opened.

### 5. A browsable history
- [ ] A visible history panel (implementing the existing *Saved labels* scenarios in `Acceptance_Tests.md`), with a thumbnail per label rendered by the real renderer.
- [ ] Search or filter by text. Sort by last printed (default), created, or name.
- [ ] **Edit in place:** opening a saved label and saving changes **updates that entry** (same `id`, new `updated_at`). It doesn't create a new one.
- [ ] **Duplicate and edit:** a *Duplicate* action creates a new entry (new `id`) from a copy, and leaves the original untouched.
- [ ] Re-print straight from history without opening the editor.
- [ ] Record `created_at`, `updated_at` and `last_printed_at` (and optionally a print count) per entry.
- [ ] Revisit the de-duplication rule. With in-place edits and explicit duplicates, de-duplicating on print should probably become "re-printing an existing entry bumps `last_printed_at`" instead of rewriting entries.

### 6. Stars
- [ ] Star or unstar any saved label. Starred labels always sort above unstarred ones, under whatever sort is active.
- [ ] A *Starred only* filter, and the star state persisted in the saved-labels file.

### 7. General UX
- [ ] Keyboard: Ctrl/⌘+Enter prints, and Ctrl/⌘+P previews.
- [ ] Multi-line text is laid out correctly (today's y-position maths assumes a single line).
- [ ] Clear feedback: a printer status badge (from `/status`), toast messages for print success or failure, and an error when text overflows the label (or auto-shrink-to-fit as an option).
- [ ] Usable on a phone (responsive layout); dark mode.
- [ ] Copies stepper. Remember the last-used stock, font and orientation.
- [ ] Remove or retire the legacy `web_app/` copy so there is one UI.

## Data model and migration

`saved_labels.json` is the only persistent state, and existing deployments already have entries. The new schema needs:
- a `version` field;
- per-label `orientation`, `starred`, timestamps, and a list of blocks (text or image, each with its own font, size, position and alignment) instead of the single `text`, `font_size` and `align`;
- image references.

Old entries must load as a single centred text block, with `created_at` unknown.

## Acceptance

- [ ] `Acceptance_Tests.md` gains scenarios for each section above, and the existing *Saved labels* scenarios pass against the real UI.
- [ ] Unit tests cover the renderer (fonts, images, orientation, multi-line) and the history operations (edit in place keeps the `id`, duplicate creates a new one, stars float, migration of an old file).
- [ ] The Docker image installs the font set, and `docker build` stays green in CI.

<!-- fr:journal kind=decision scope=spec id=isolation-host-worktree created=2026-11-01T18:43:18+00:00 decided_by=operator -->
### isolation-host-worktree · decision · Isolation: host worktree (no devcontainer profile)

FR_ISOLATION_TARGET=worktree chosen over running fr-init first.

decider: operator (round 1)

<!-- fr:journal kind=decision scope=spec id=on-label-editing-full created=2026-11-01T18:43:18+00:00 decided_by=operator -->
### on-label-editing-full · decision · On-preview editing: full inline editing

Select, drag, scale images, and type directly on the preview (R10). Chosen over select+drag only and over deferring.

decider: operator (round 1)

<!-- fr:journal kind=decision scope=spec id=frontend-alpine-vendored created=2026-11-01T18:43:18+00:00 decided_by=operator -->
### frontend-alpine-vendored · decision · Frontend: Alpine.js vendored, no build

Alpine.js vendored into static/; no CDN, no Node build step.

decider: operator (round 1)

<!-- fr:journal kind=decision scope=spec id=fonts-apt-scan created=2026-11-01T18:43:18+00:00 decided_by=operator -->
### fonts-apt-scan · decision · Fonts: apt-installed in image + curated catalog scan

fonts-dejavu-core, fonts-liberation, fonts-noto-core via apt; catalog resolved by scanning FONT_DIRS; tests use a vendored OFL fixture font (R1, R22).

decider: operator (round 1)

<!-- fr:journal kind=decision scope=spec id=svg-cairosvg created=2026-11-01T18:43:18+00:00 decided_by=operator -->
### svg-cairosvg · decision · SVG: cairosvg + built-in SVG icon set

python3-cairosvg rasterizes uploads and ~20 MIT icons (R5, R22).

decider: operator (round 1)

<!-- fr:journal kind=decision scope=spec id=print-open-entry-saves created=2026-11-01T18:43:18+00:00 decided_by=operator -->
### print-open-entry-saves · decision · Printing an opened entry saves in place, then prints

R16. Duplicate remains the explicit fork.

decider: operator (round 1)

<!-- fr:journal kind=decision scope=spec id=print-new-autosave-bump created=2026-11-01T18:43:18+00:00 decided_by=operator -->
### print-new-autosave-bump · decision · Printing a new design auto-saves; content match bumps

R16: identical content (blocks, stock, orientation) bumps last_printed_at/print_count instead of creating a duplicate.

decider: operator (round 1)

<!-- fr:journal kind=decision scope=spec id=legacy-delete created=2026-11-01T18:43:18+00:00 decided_by=operator -->
### legacy-delete · decision · Delete legacy web_app/

R21.

decider: operator (round 1)

<!-- fr:journal kind=decision scope=spec id=ci-pytest-job created=2026-11-01T18:43:18+00:00 decided_by=operator -->
### ci-pytest-job · decision · Add a pytest CI job

R23: new GitHub Actions workflow running pytest.

decider: operator (round 1)

<!-- fr:journal kind=decision scope=spec id=verification-tests-live-tester created=2026-11-01T18:43:18+00:00 decided_by=operator -->
### verification-tests-live-tester · decision · Verification: tests + agent browser check pre-merge; live rows post-merge; gate tester

Recorded in the spec's ## Verification: gate tester; ldx-print-orientation and ldx-print-mono are live.

decider: operator (round 1)
