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

<!-- fr:journal kind=review scope=spec id=spec-review-r1 created=2026-11-01T18:49:06+00:00 -->
### spec-review-r1 · review · independent spec review: 15 findings (14 in, 1 out)

fr-spec-reviewer checked the spec against the 10 operator decisions (all honoured, with fixture-licence wording drift in sr-7) and against codebase reality, citing file:line for label_generator.py, config.py, web_app.py, printer_service.py, templates/index.html, setup.sh, Dockerfile, pyproject.toml, .github/workflows, web_app/, Acceptance_Tests.md and tests/. Findings raised: sr-1..sr-13 and sr-15 (in scope), sr-14 (out of scope).

<!-- fr:journal kind=finding scope=spec id=sr-1 created=2026-11-01T18:49:06+00:00 state=open review_scope=in -->
### sr-1 · finding [open] (reviewer: in scope) · "existing clients and tests keep working" is false: tests/Saved-labels scenarios contradict R7/R12/R16

tests/test_web_app.py:182,183,239,240,275, tests/test_label_generator.py:24-25 and Acceptance_Tests.md:129,141,179 conflict with mode-1 output, the v2 file shape and re-print bumping. Fix: list the rewritten expectations, decide what create_label_image returns, reword as 'payloads stay accepted'.

<!-- fr:journal kind=finding scope=spec id=sr-2 created=2026-11-01T18:49:06+00:00 state=open review_scope=in -->
### sr-2 · finding [open] (reviewer: in scope) · GET/DELETE /memory compat alias response shape undefined

web_app.py:172-184 returns flat entries today; v2 has no text/font_size/align. Fix: define the alias shape and order, and test it.

<!-- fr:journal kind=finding scope=spec id=sr-3 created=2026-11-01T18:49:06+00:00 state=open review_scope=in -->
### sr-3 · finding [open] (reviewer: in scope) · Pre-rotation ignores CUPS fit-to-page/auto-rotation

printer_service.py:130-134 sends fit-to-page and no orientation-requested; cups-filters may auto-rotate again. Fix: pin orientation-requested=3, test the options.

<!-- fr:journal kind=finding scope=spec id=sr-4 created=2026-11-01T18:49:06+00:00 state=open review_scope=in -->
### sr-4 · finding [open] (reviewer: in scope) · portrait = stock width x height mislabels wide stocks (11354, 99012)

config.py:18-23,42-47. Fix: name orientation by the canvas shape and derive it per stock.

<!-- fr:journal kind=finding scope=spec id=sr-5 created=2026-11-01T18:49:06+00:00 state=open review_scope=in -->
### sr-5 · finding [open] (reviewer: in scope) · No rule for a missing family; DEFAULT_FONT_PATH fate unstated

config.py:59, label_generator.py:81-85. Fix: fallback chain plus a substitution flag; replace DEFAULT_FONT_PATH.

<!-- fr:journal kind=finding scope=spec id=sr-6 created=2026-11-01T18:49:06+00:00 state=open review_scope=in -->
### sr-6 · finding [open] (reviewer: in scope) · font_size_pt must allow fractions for a faithful migration

40 px = 9.6 pt. Fix: float pt, round(pt*dpi/72), same conversion on the compat path, round-trip test.

<!-- fr:journal kind=finding scope=spec id=sr-7 created=2026-11-01T18:49:06+00:00 state=open review_scope=in -->
### sr-7 · finding [open] (reviewer: in scope) · DejaVu is not OFL; fixture contradicts the fonts-apt-scan wording

Fix: use Liberation Sans (OFL) as the fixture and ship its licence.

<!-- fr:journal kind=finding scope=spec id=sr-8 created=2026-11-01T18:49:06+00:00 state=open review_scope=in -->
### sr-8 · finding [open] (reviewer: in scope) · CI test job lacks the cups module imported at load

printer_service.py:11, web_app.py:16,20. Fix: a session-wide conftest fake cups.

<!-- fr:journal kind=finding scope=spec id=sr-9 created=2026-11-01T18:49:06+00:00 state=open review_scope=in -->
### sr-9 · finding [open] (reviewer: in scope) · Thumbnail route and /icons missing from routes/R13/Testing

Fix: define both with their shapes; add route tests.

<!-- fr:journal kind=finding scope=spec id=sr-10 created=2026-11-01T18:49:06+00:00 state=open review_scope=in -->
### sr-10 · finding [open] (reviewer: in scope) · History-write failure after CUPS accepted the job reports a failed print

Fix: 500 with no print when the pre-print save fails; 200 plus a warning when the post-print write fails.

<!-- fr:journal kind=finding scope=spec id=sr-11 created=2026-11-01T18:49:06+00:00 state=open review_scope=in -->
### sr-11 · finding [open] (reviewer: in scope) · Missing-image outline in the preview breaks preview == print

Fix: report missing:true; the overlay draws the outline, never the PNG.

<!-- fr:journal kind=finding scope=spec id=sr-12 created=2026-11-01T18:49:06+00:00 state=open review_scope=in -->
### sr-12 · finding [open] (reviewer: in scope) · "contenteditable textarea" contradicts itself

Fix: pick a <textarea>.

<!-- fr:journal kind=finding scope=spec id=sr-13 created=2026-11-01T18:49:06+00:00 state=open review_scope=in -->
### sr-13 · finding [open] (reviewer: in scope) · /render response format unspecified

Fix: give the JSON shape and the bbox convention.

<!-- fr:journal kind=finding scope=spec id=sr-14 created=2026-11-01T18:49:06+00:00 state=open review_scope=out -->
### sr-14 · finding [open] (reviewer: out of scope) · No volume for saved_labels.json/images; rebuild-redeploy drops history

docker-compose.yml has no volumes; LABEL_MEMORY_FILE defaults to a relative path (web_app.py:21). Follow-up: a named volume plus LABEL_MEMORY_FILE=/data/saved_labels.json.

<!-- fr:journal kind=finding scope=spec id=sr-15 created=2026-11-01T18:49:06+00:00 state=open review_scope=in -->
### sr-15 · finding [open] (reviewer: in scope) · Label name stored and searched but never settable

Fix: a name field plus name in PUT/POST, or always derive it.

<!-- fr:journal kind=finding scope=spec id=sr-1-resolved created=2026-11-01T18:49:06+00:00 state=fixed resolves=sr-1 -->
### sr-1-resolved · finding [fixed] · resolves sr-1: "existing clients and tests keep working" is false: tests/Saved-labels scenarios contradict R7/R12/R16

create_label_image converts render output to RGB (pure black/white), so test_label_generator stays valid; the Testing section gains a table of rewritten expectations; Print and preview now says payloads stay accepted.

<!-- fr:journal kind=finding scope=spec id=sr-2-resolved created=2026-11-01T18:49:06+00:00 state=fixed resolves=sr-2 -->
### sr-2-resolved · finding [fixed] · resolves sr-2: GET/DELETE /memory compat alias response shape undefined

R13 defines GET /memory as v2 labels plus flat text/font_size(px)/align in the default sort; DELETE returns {success, remaining} in the same shape.

<!-- fr:journal kind=finding scope=spec id=sr-3-resolved created=2026-11-01T18:49:06+00:00 state=fixed resolves=sr-3 -->
### sr-3-resolved · finding [fixed] · resolves sr-3: Pre-rotation ignores CUPS fit-to-page/auto-rotation

R11 and Design pin orientation-requested=3 beside fit-to-page; the options are unit-tested for both orientations.

<!-- fr:journal kind=finding scope=spec id=sr-4-resolved created=2026-11-01T18:49:06+00:00 state=fixed resolves=sr-4 -->
### sr-4-resolved · finding [fixed] · resolves sr-4: portrait = stock width x height mislabels wide stocks (11354, 99012)

R11: orientation named by canvas shape (portrait = taller than wide); defaults to the stock's shape; the canvas formula is in the schema notes.

<!-- fr:journal kind=finding scope=spec id=sr-5-resolved created=2026-11-01T18:49:06+00:00 state=fixed resolves=sr-5 -->
### sr-5-resolved · finding [fixed] · resolves sr-5: No rule for a missing family; DEFAULT_FONT_PATH fate unstated

R1 replaces DEFAULT_FONT_PATH with DEFAULT_FONT_FAMILY; R3 gives the fallback chain with font_substituted; Error handling and Testing updated.

<!-- fr:journal kind=finding scope=spec id=sr-6-resolved created=2026-11-01T18:49:06+00:00 state=fixed resolves=sr-6 -->
### sr-6-resolved · finding [fixed] · resolves sr-6: font_size_pt must allow fractions for a faithful migration

R2: fractional points; schema notes use round(pt*dpi/72) and the same conversion on the compat path, with a round-trip test.

<!-- fr:journal kind=finding scope=spec id=sr-7-resolved created=2026-11-01T18:49:06+00:00 state=fixed resolves=sr-7 -->
### sr-7-resolved · finding [fixed] · resolves sr-7: DejaVu is not OFL; fixture contradicts the fonts-apt-scan wording

The fixture is now Liberation Sans 2.x (OFL 1.1) with its LICENSE beside it.

<!-- fr:journal kind=finding scope=spec id=sr-8-resolved created=2026-11-01T18:49:06+00:00 state=fixed resolves=sr-8 -->
### sr-8-resolved · finding [fixed] · resolves sr-8: CI test job lacks the cups module imported at load

Infra: tests/conftest.py installs a session-wide fake cups module.

<!-- fr:journal kind=finding scope=spec id=sr-9-resolved created=2026-11-01T18:49:06+00:00 state=fixed resolves=sr-9 -->
### sr-9-resolved · finding [fixed] · resolves sr-9: Thumbnail route and /icons missing from routes/R13/Testing

R5 defines GET /icons [{name,url}]; R13 defines the thumbnail (100 DPI); the full route list is in the web_app row; route tests listed.

<!-- fr:journal kind=finding scope=spec id=sr-10-resolved created=2026-11-01T18:49:06+00:00 state=fixed resolves=sr-10 -->
### sr-10-resolved · finding [fixed] · resolves sr-10: History-write failure after CUPS accepted the job reports a failed print

R16, Print and preview, and Error handling: a pre-print save failure gives 500 and no print; a post-print history-write failure gives 200 plus a warning.

<!-- fr:journal kind=finding scope=spec id=sr-11-resolved created=2026-11-01T18:49:06+00:00 state=fixed resolves=sr-11 -->
### sr-11-resolved · finding [fixed] · resolves sr-11: Missing-image outline in the preview breaks preview == print

R8 adds missing:true; nothing is drawn in the PNG; the editor overlay outlines the block.

<!-- fr:journal kind=finding scope=spec id=sr-12-resolved created=2026-11-01T18:49:06+00:00 state=fixed resolves=sr-12 -->
### sr-12-resolved · finding [fixed] · resolves sr-12: "contenteditable textarea" contradicts itself

R10 and Editor UI specify a <textarea> with plain \n text.

<!-- fr:journal kind=finding scope=spec id=sr-13-resolved created=2026-11-01T18:49:06+00:00 state=fixed resolves=sr-13 -->
### sr-13-resolved · finding [fixed] · resolves sr-13: /render response format unspecified

R8 gives the full /render JSON shape and the bbox convention.

<!-- fr:journal kind=finding scope=spec id=sr-14-resolved created=2026-11-01T18:49:06+00:00 state=open resolves=sr-14 out_of_scope=true -->
### sr-14-resolved · finding [out-of-scope] · resolves sr-14: No volume for saved_labels.json/images; rebuild-redeploy drops history

Pre-existing: saved_labels.json already has no volume before this change (docker-compose.yml, web_app.py:21); this change only places images beside it, and a container restart keeps both.

<!-- fr:journal kind=finding scope=spec id=sr-15-resolved created=2026-11-01T18:49:06+00:00 state=fixed resolves=sr-15 -->
### sr-15-resolved · finding [fixed] · resolves sr-15: Label name stored and searched but never settable

New R25: an editor name field, name allowed in POST/PUT, defaulted from the first text line when empty; the Toolbar lists the field.

<!-- fr:journal kind=decision scope=spec id=exit-baseline created=2026-11-01T18:49:07+00:00 -->
### exit-baseline · decision · exit when spec-review resolved

The exit when spec-review resolved; `fr verification set` and `deliver` compare against it.

```yaml
row_gates:
  ldx-acceptance-doc: none
  ldx-fonts: none
  ldx-history-model: none
  ldx-history-panel: none
  ldx-image-build: none
  ldx-images: none
  ldx-label-name: none
  ldx-live-preview: none
  ldx-orientation: none
  ldx-print-mono: tester
  ldx-print-orientation: tester
  ldx-single-ui: none
  ldx-ux: none
row_kinds:
  ldx-acceptance-doc: none
  ldx-fonts: none
  ldx-history-model: none
  ldx-history-panel: none
  ldx-image-build: none
  ldx-images: none
  ldx-label-name: none
  ldx-live-preview: none
  ldx-orientation: none
  ldx-print-mono: live
  ldx-print-orientation: live
  ldx-single-ui: none
  ldx-ux: none
run_gate: tester
run_kind: none
```

<!-- fr:journal kind=decision scope=spec id=phase-split-2026-11-01-label-designer-ux-p2 created=2026-11-01T18:51:37+00:00 -->
### phase-split-2026-11-01-label-designer-ux-p2 · decision · ask: history store, /labels API and print flow (R12-R16, R25) are their own ask

<!-- fr:journal kind=decision scope=spec id=phase-split-2026-11-01-label-designer-ux-p3 created=2026-11-01T18:51:42+00:00 -->
### phase-split-2026-11-01-label-designer-ux-p3 · decision · ask: the designer UI, history panel and UX (R9, R10, R17-R21, R24) are their own ask

<!-- fr:journal kind=decision scope=spec id=tier-2026-11-01-label-designer-ux-p2 created=2026-11-01T18:51:46+00:00 -->
### tier-2026-11-01-label-designer-ux-p2 · decision · hard: phase 2 migrates the only persistent user data (saved_labels.json v1 to v2) and changes the print/save path every print relies on

<!-- fr:journal kind=finding scope=spec id=sr-14-resolved-2 created=2026-11-01T22:24:29+00:00 state=open resolves=sr-14 tracked_by=https://github.com/derio-homelab/Cups-Dymo-LabelWriter450/issues/4 -->
### sr-14-resolved-2 · finding [deferred → https://github.com/derio-homelab/Cups-Dymo-LabelWriter450/issues/4] · resolves sr-14: No volume for saved_labels.json/images; rebuild-redeploy drops history

Filed at deliver as https://github.com/derio-homelab/Cups-Dymo-LabelWriter450/issues/4.

<!-- fr:journal kind=discovery scope=spec id=test-plan-step-1 created=2026-11-02T05:39:12+00:00 -->
### test-plan-step-1 · discovery · Test Plan step 1: ran

Step: Deploy the image (`docker compose up --build -d`); open `:5000`.

Evidence: GET /labels, /fonts, /icons 200 on http://192.168.10.34:5000; printer 3 usb://DYMO/LabelWriter%20450?serial=18012409565683 none; paper matched the preview (operator, 2026-11-02)

<!-- fr:journal kind=discovery scope=spec id=test-plan-step-2 created=2026-11-02T06:33:21+00:00 -->
### test-plan-step-2 · discovery · Test Plan step 2: ran

Step: 30252 Address, landscape, two text blocks of different sizes → print; the printed label matches the preview (text runs along the 89 mm edge, same way up as on screen).

Evidence: label 05cde009-5cad-4081-95d5-cf7b4fb525e4 'Text': 30252 landscape, text[22pt, 14pt], printed x2; operator: 99010 (EU equivalent of 30252, same 28×89 mm); paper matched the preview (operator, 2026-11-02)

<!-- fr:journal kind=discovery scope=spec id=test-plan-step-3 created=2026-11-02T06:34:02+00:00 -->
### test-plan-step-3 · discovery · Test Plan step 3: ran

Step: Same design in portrait → print; matches the preview.

Evidence: label 05cde009-5cad-4081-95d5-cf7b4fb525e4 'Text': 30252 portrait, text[22pt, 14pt], printed x3; paper matched the preview (operator, 2026-11-02)

<!-- fr:journal kind=discovery scope=spec id=test-plan-step-4 created=2026-11-02T06:40:29+00:00 -->
### test-plan-step-4 · discovery · Test Plan step 4: ran

Step: 11354 Multipurpose, landscape and portrait → print each; both match their previews.

Evidence: label 05cde009-5cad-4081-95d5-cf7b4fb525e4 'Text': 11354 landscape, text[22pt, 14pt], printed x5 | label 05cde009-5cad-4081-95d5-cf7b4fb525e4 'Text': 11354 portrait, text[22pt, 14pt], printed x6; operator: in landscape, bottom right was cut off; paper matched the preview (operator, 2026-11-02)
