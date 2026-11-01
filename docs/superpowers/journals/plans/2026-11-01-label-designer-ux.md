<!-- fr:journal-schema=3 -->
# Journal: 2026-11-01-label-designer-ux

<!-- fr:journal kind=discovery scope=plan id=p1-d1 created=2026-11-01T19:11:33+00:00 phase=1 -->
### p1-d1 · discovery · Lucide 0.460 renamed two icons (phase 1)

lucide-static 0.460.0 has no home.svg or alert-triangle.svg; shipped upstream names house.svg and triangle-alert.svg (20 real files + ISC LICENSE copied from the npm package).

<!-- fr:journal kind=discovery scope=plan id=p1-d2 created=2026-11-01T19:11:33+00:00 phase=1 -->
### p1-d2 · discovery · hadolint and CI evidence (phase 1)

hadolint was not installed; installed via brew (2.15.1); hadolint --failure-threshold error Dockerfile exit 0 (warnings only). yamllint ran locally (only a truthy warning on 'on:', same as other workflows). CI on pushed head 2bc5036: Tests green, Build green. Static-Analysis (markdownlint) is red on spec/journal/acceptance-report markdown files that are not phase-1 code.

<!-- fr:journal kind=discovery scope=plan id=p1-d3 created=2026-11-01T19:11:33+00:00 phase=1 -->
### p1-d3 · discovery · pytest needs pythonpath in CI (phase 1)

CI collected no package because the repo root was not on sys.path; added pythonpath = ['.'] to pytest ini options.

<!-- fr:journal kind=discovery scope=plan id=p1-d4 created=2026-11-01T19:11:33+00:00 phase=1 -->
### p1-d4 · discovery · cairosvg sizes from width/height, cairo caps surfaces (phase 1)

cairosvg sizes the canvas from root width/height before viewBox, and cairo refuses surfaces > 32767 px (INVALID_SIZE), so SVG sizing is probed by rasterizing once at 64 px and mapped to ImageTooLarge.

<!-- fr:journal kind=finding scope=plan id=p1-f1 created=2026-11-01T19:11:33+00:00 phase=1 state=open review_scope=in -->
### p1-f1 · finding [open] (reviewer: in scope) · unbounded image render dimensions (phase 1)

width_mm/uploads/SVGs could force huge rasters. Fixed: image width_mm <= label long edge, width clamped to canvas, pixel budget (4 Mpx) checked before rasterize/resize, SVG sized by a probe and rendered with fixed output_width/height (aspect cap 50:1), uploads over 25 Mpx refused with 400.

<!-- fr:journal kind=finding scope=plan id=p1-f2 created=2026-11-01T19:11:33+00:00 phase=1 state=open review_scope=in -->
### p1-f2 · finding [open] (reviewer: in scope) · stored XSS via uploaded SVG served inline (phase 1)

GET /images/<name> now sends nosniff and a sandboxing CSP on every response, SVG as Content-Disposition attachment; name strictly validated; cairosvg stays in safe mode (test shows external file:// and http image hrefs are not fetched).

<!-- fr:journal kind=finding scope=plan id=p1-f3 created=2026-11-01T19:11:33+00:00 phase=1 state=open review_scope=in -->
### p1-f3 · finding [open] (reviewer: in scope) · render DoS via unbounded document sizes and linear shrink loop (phase 1)

font_size_pt capped at the label long edge in points, text <= 2000 chars, <= 50 lines per block, <= 30 blocks; shrink-to-fit is a 12-iteration binary search over [6 pt, requested].

<!-- fr:journal kind=finding scope=plan id=p1-f4 created=2026-11-01T19:11:33+00:00 phase=1 state=open review_scope=in -->
### p1-f4 · finding [open] (reviewer: in scope) · SVG pixel-budget check bypassable via regex aspect inference (phase 1)

The viewBox/width/height regex disagreed with cairosvg sizing. Regex removed; one probe render gives the real aspect, then output_width and output_height are both fixed by us.

<!-- fr:journal kind=finding scope=plan id=p1-f5 created=2026-11-01T19:11:33+00:00 phase=1 state=open review_scope=out -->
### p1-f5 · finding [open] (reviewer: out of scope) · Static-Analysis markdownlint is red on generated docs (phase 1)

MD022/MD032/MD060 errors in docs/superpowers specs/journals and docs/acceptance/report_linked.md (tool-generated), not touched by this phase.

<!-- fr:journal kind=finding scope=plan id=p1-f1-resolved created=2026-11-01T19:11:33+00:00 phase=1 state=fixed resolves=p1-f1 -->
### p1-f1-resolved · finding [fixed] · resolves p1-f1: unbounded image render dimensions (phase 1)

bounded dimensions; tests in test_document, test_images, test_render, test_routes_render

<!-- fr:journal kind=finding scope=plan id=p1-f2-resolved created=2026-11-01T19:11:33+00:00 phase=1 state=fixed resolves=p1-f2 -->
### p1-f2-resolved · finding [fixed] · resolves p1-f2: stored XSS via uploaded SVG served inline (phase 1)

headers, attachment for SVG, strict name regex, safe-mode test

<!-- fr:journal kind=finding scope=plan id=p1-f3-resolved created=2026-11-01T19:11:33+00:00 phase=1 state=fixed resolves=p1-f3 -->
### p1-f3-resolved · finding [fixed] · resolves p1-f3: render DoS via unbounded document sizes and linear shrink loop (phase 1)

caps and bounded binary search with iteration-count test

<!-- fr:journal kind=finding scope=plan id=p1-f4-resolved created=2026-11-01T19:11:33+00:00 phase=1 state=fixed resolves=p1-f4 -->
### p1-f4-resolved · finding [fixed] · resolves p1-f4: SVG pixel-budget check bypassable via regex aspect inference (phase 1)

probe-based sizing; shape tests for single-quoted, width/height-only, nested viewBox, units, extreme aspect

<!-- fr:journal kind=discovery scope=plan id=no-refactor-p1-t1 created=2026-11-01T19:11:33+00:00 phase=1 -->
### no-refactor-p1-t1 · discovery · no-refactor-because P1.T1 (phase 1)

conftest and smoke test are minimal; nothing to clean

<!-- fr:journal kind=discovery scope=plan id=no-refactor-p1-t6 created=2026-11-01T19:11:33+00:00 phase=1 -->
### no-refactor-p1-t6 · discovery · no-refactor-because P1.T6 (phase 1)

orient_for_media is a small pure function wired in one place; nothing to clean

<!-- fr:journal kind=discovery scope=plan id=no-refactor-p1-t7 created=2026-11-01T19:11:33+00:00 phase=1 -->
### no-refactor-p1-t7 · discovery · no-refactor-because P1.T7 (phase 1)

route handlers share _doc_from_request/_png_data_url helpers from the start; nothing to clean

<!-- fr:journal kind=discovery scope=plan id=no-refactor-p1-t8 created=2026-11-01T19:11:33+00:00 phase=1 -->
### no-refactor-p1-t8 · discovery · no-refactor-because P1.T8 (phase 1)

single Dockerfile package-list edit; nothing to clean

<!-- fr:journal kind=review scope=plan id=p1-review-r1 created=2026-11-01T19:26:29+00:00 phase=1 -->
### p1-review-r1 · review · Phase 1 code review: 10 findings (9 in, 1 out) (phase 1)

A dispatched general-purpose reviewer (superpowers:requesting-code-review template) reviewed bb908be..39ba726 against the spec and plan phase 1, ran the suite (137 passed) and probe scripts. Findings raised: p1-r1 to p1-r9 (in), p1-r10 (out). The orchestrator verified each against the code (receiving-code-review), and the implementer fixed p1-r1 to p1-r9 in 90e4d46, e9f8fe7 and 21395e8, each with a test; the suite is 173 passed.

<!-- fr:journal kind=finding scope=plan id=p1-r1 created=2026-11-01T19:26:29+00:00 phase=1 state=open review_scope=in -->
### p1-r1 · finding [open] (reviewer: in scope) · Text rasterization still a render DoS; only the global MAX_IMAGE_PIXELS blocked huge lines (as a 500) (phase 1)

label_generator.py _draw_text rasterized every line at full size. Fix: skip off-canvas lines, per-block raster budget leading to overflow; the bomb guard is scoped to image decode.

<!-- fr:journal kind=finding scope=plan id=p1-r2 created=2026-11-01T19:26:29+00:00 phase=1 state=open review_scope=in -->
### p1-r2 · finding [open] (reviewer: in scope) · Overflow ignored horizontal off-canvas extent (phase 1)

label_generator.py:89-94. Fix: check the line x extent; width_mm=None = canvas − x − margin.

<!-- fr:journal kind=finding scope=plan id=p1-r3 created=2026-11-01T19:26:29+00:00 phase=1 state=open review_scope=in -->
### p1-r3 · finding [open] (reviewer: in scope) · Validation accepted inf/nan/huge coords and wrong types (500s) (phase 1)

document.py _number. Fix: isfinite, coordinate bounds, type checks; 400.

<!-- fr:journal kind=finding scope=plan id=p1-r4 created=2026-11-01T19:26:29+00:00 phase=1 state=open review_scope=in -->
### p1-r4 · finding [open] (reviewer: in scope) · Image blocks never reported overflow (phase 1)

label_generator.py:138. Fix: compare the pasted box with the canvas.

<!-- fr:journal kind=finding scope=plan id=p1-r5 created=2026-11-01T19:26:29+00:00 phase=1 state=open review_scope=in -->
### p1-r5 · finding [open] (reviewer: in scope) · Malformed SVG accepted at upload (phase 1)

images.py store_upload only sniffed. Fix: probe-rasterize at upload.

<!-- fr:journal kind=finding scope=plan id=p1-r6 created=2026-11-01T19:26:29+00:00 phase=1 state=open review_scope=in -->
### p1-r6 · finding [open] (reviewer: in scope) · Raster uploads fully decoded and RGBA-converted before downscale (phase 1)

images.py:173-181. Fix: draft()/reduce before convert.

<!-- fr:journal kind=finding scope=plan id=p1-r7 created=2026-11-01T19:26:29+00:00 phase=1 state=open review_scope=in -->
### p1-r7 · finding [open] (reviewer: in scope) · open_font reloaded the TTF on every layout (phase 1)

fonts.py:148. Fix: lru_cache.

<!-- fr:journal kind=finding scope=plan id=p1-r8 created=2026-11-01T19:26:29+00:00 phase=1 state=open review_scope=in -->
### p1-r8 · finding [open] (reviewer: in scope) · Compat routes changed behaviour undocumented (unknown align, whitespace-only text → 400) (phase 1)

Kept the stricter behaviour; documented in the spec's rewrite table.

<!-- fr:journal kind=finding scope=plan id=p1-r9 created=2026-11-01T19:26:29+00:00 phase=1 state=open review_scope=in -->
### p1-r9 · finding [open] (reviewer: in scope) · Tests workflow installed unpinned deps (phase 1)

.github/workflows/Tests.yaml. Fix: pin to the pyproject constraints.

<!-- fr:journal kind=finding scope=plan id=p1-r10 created=2026-11-01T19:26:29+00:00 phase=1 state=open review_scope=out -->
### p1-r10 · finding [open] (reviewer: out of scope) · copies unbounded (negative/zero/huge) passed to CUPS (phase 1)

Pre-existing: v1 /print did int(data.get('copies', 1)) with no bounds (web_app.py at bb908be).

<!-- fr:journal kind=finding scope=plan id=p1-r1-resolved created=2026-11-01T19:26:29+00:00 phase=1 state=fixed resolves=p1-r1 -->
### p1-r1-resolved · finding [fixed] · resolves p1-r1: Text rasterization still a render DoS; only the global MAX_IMAGE_PIXELS blocked huge lines (as a 500) (phase 1)

90e4d46 — test_hostile_doc_renders_fast_without_exceptions, test_offcanvas_lines_are_skipped, test_hostile_text_doc_never_500, test_pillow_global_bomb_limit_is_not_changed.

<!-- fr:journal kind=finding scope=plan id=p1-r2-resolved created=2026-11-01T19:26:29+00:00 phase=1 state=fixed resolves=p1-r2 -->
### p1-r2-resolved · finding [fixed] · resolves p1-r2: Overflow ignored horizontal off-canvas extent (phase 1)

90e4d46 — test_horizontal_extent_flags_overflow[50/-30], test_centered_block_straddling_left_edge_overflows, test_default_width_is_canvas_minus_x_minus_margin.

<!-- fr:journal kind=finding scope=plan id=p1-r3-resolved created=2026-11-01T19:26:29+00:00 phase=1 state=fixed resolves=p1-r3 -->
### p1-r3-resolved · finding [fixed] · resolves p1-r3: Validation accepted inf/nan/huge coords and wrong types (500s) (phase 1)

90e4d46 — test_non_finite_out_of_range_and_wrong_types_rejected, test_render_rejects_hostile_numbers_with_400, test_render_rejects_wrong_types_with_400.

<!-- fr:journal kind=finding scope=plan id=p1-r4-resolved created=2026-11-01T19:26:29+00:00 phase=1 state=fixed resolves=p1-r4 -->
### p1-r4-resolved · finding [fixed] · resolves p1-r4: Image blocks never reported overflow (phase 1)

90e4d46 — test_image_leaving_canvas_overflows.

<!-- fr:journal kind=finding scope=plan id=p1-r5-resolved created=2026-11-01T19:26:29+00:00 phase=1 state=fixed resolves=p1-r5 -->
### p1-r5-resolved · finding [fixed] · resolves p1-r5: Malformed SVG accepted at upload (phase 1)

90e4d46 — test_junk_svg_upload_refused.

<!-- fr:journal kind=finding scope=plan id=p1-r6-resolved created=2026-11-01T19:26:29+00:00 phase=1 state=fixed resolves=p1-r6 -->
### p1-r6-resolved · finding [fixed] · resolves p1-r6: Raster uploads fully decoded and RGBA-converted before downscale (phase 1)

90e4d46 — test_raster_is_downscaled_before_rgba_convert, test_jpeg_uses_draft_mode.

<!-- fr:journal kind=finding scope=plan id=p1-r7-resolved created=2026-11-01T19:26:29+00:00 phase=1 state=fixed resolves=p1-r7 -->
### p1-r7-resolved · finding [fixed] · resolves p1-r7: open_font reloaded the TTF on every layout (phase 1)

90e4d46 — test_opened_fonts_are_cached.

<!-- fr:journal kind=finding scope=plan id=p1-r8-resolved created=2026-11-01T19:26:29+00:00 phase=1 state=fixed resolves=p1-r8 -->
### p1-r8-resolved · finding [fixed] · resolves p1-r8: Compat routes changed behaviour undocumented (unknown align, whitespace-only text → 400) (phase 1)

e9f8fe7 — both rows added to the spec's deliberate-rewrite table.

<!-- fr:journal kind=finding scope=plan id=p1-r9-resolved created=2026-11-01T19:26:29+00:00 phase=1 state=fixed resolves=p1-r9 -->
### p1-r9-resolved · finding [fixed] · resolves p1-r9: Tests workflow installed unpinned deps (phase 1)

21395e8 — pinned pip install; suite passes on the pinned versions locally (Python 3.12).

<!-- fr:journal kind=finding scope=plan id=p1-r10-resolved created=2026-11-01T19:26:29+00:00 phase=1 state=open resolves=p1-r10 out_of_scope=true -->
### p1-r10-resolved · finding [out-of-scope] · resolves p1-r10: copies unbounded (negative/zero/huge) passed to CUPS (phase 1)

Not caused by this change: the v1 /print already passed int(copies) to CUPS unbounded. Note: document.py now rejects non-integer copies (test_bad_copies_rejected) but the range bound remains a follow-up.

<!-- fr:journal kind=finding scope=plan id=p1-f5-resolved created=2026-11-01T19:26:29+00:00 phase=1 state=fixed resolves=p1-f5 -->
### p1-f5-resolved · finding [fixed] · resolves p1-f5: Static-Analysis markdownlint is red on generated docs (phase 1)

The executor tagged this out of scope, but the failing markdown (spec, journals, acceptance report) was added by this branch, so this change caused it. Fixed in 597bfd0 (.markdownlintignore for fr-generated markdown, spec lint fixes); markdownlint-cli 0.50.0 is clean.

<!-- fr:journal kind=decision scope=plan id=p2-dec1 created=2026-11-01T19:41:04+00:00 phase=2 -->
### p2-dec1 · decision · /labels response shapes and status codes (phase 2)

`/labels` responses are `{success, labels}` (list) and `{success, label}` (one), with 201
for create and duplicate, `{success, deleted: n}` for bulk delete and `{success: true}` for
a single delete; unknown id 404, invalid doc / sort / `starred` / `ids` 400, a store write
failure 500 (state rolled back). `starred` query filter accepts `1|true|yes`. POST /labels
accepts `{doc}` or a bare doc, and allows a design with no content (only printing refuses
it). `/memory` keeps its old bare-list shape (compat alias).

<!-- fr:journal kind=decision scope=plan id=p2-dec2 created=2026-11-01T19:41:04+00:00 phase=2 -->
### p2-dec2 · decision · History file safety beyond the v1 backup (phase 2)

A file that cannot be parsed, has an unknown shape/version, or has v2 entries that fail
validation (those entries are skipped) loads as what is readable and is not rewritten
until a mutation; that first mutation first writes the original bytes to
`saved_labels.corrupt.json`. Backups are never overwritten: an existing `.v1.json` /
`.corrupt.json` with different bytes gets a numbered sibling (`.v1.1.json`), identical
bytes are a no-op (so a failed first persist retries cleanly). A file that exists but
cannot be read (OSError) loads empty and every mutation raises StoreError rather than
overwrite it. Timestamps are ISO-8601 UTC with milliseconds (`...T18:00:01.000Z`), parsed
(not string-compared) for sorting.

<!-- fr:journal kind=decision scope=plan id=p2-dec3 created=2026-11-01T19:41:04+00:00 phase=2 -->
### p2-dec3 · decision · v1 migration details (phase 2)

v1 ids are preserved; a migrated entry is named by the R25 default (first non-empty line
of its text); an unknown v1 `align` migrates as `center` (what v1 drew); a v1 entry that
from_flat still rejects is skipped with a warning (the byte-identical v1 backup keeps it).
Duplicate is inserted directly above its source and keeps the source's name.

<!-- fr:journal kind=discovery scope=plan id=p2-d1 created=2026-11-01T19:41:04+00:00 phase=2 -->
### p2-d1 · discovery · Fixture captured from bb908be, with its capture script committed (phase 2)

tests/fixtures/saved_labels_v1.json was produced by `git archive bb908be
cups_dymo_label_printer` into a scratch dir and calling that version's `_save_label` on two
payloads (30252/60px/left/copies 2 and 11354/40px/center); the script is
tests/fixtures/capture_saved_labels_v1.py (not collected by pytest) and was re-run to
confirm it reproduces the file shape. v1 entries carry no `name`.

<!-- fr:journal kind=discovery scope=plan id=p2-d2 created=2026-11-01T19:41:04+00:00 phase=2 -->
### p2-d2 · discovery · Sequencing deviations inside the phase (phase 2)

`_mutate` (lock + snapshot + persist + rollback) existed from T1 because T1's rollback test
needed it; P2.T2.S3 then verified every mutation routes through it, extracted the shared
`_named` (R25 default) helper used by create/update/migration, and added a 20-thread
concurrency test. The file-shape assertion at tests/test_web_app.py:239-240 was rewritten
in T3 (not T4) because T3 is the commit that switched the file to v2; :275 gained v2
assertions in T4.

<!-- fr:journal kind=discovery scope=plan id=p2-d3 created=2026-11-01T19:41:04+00:00 phase=2 -->
### p2-d3 · discovery · Acceptance rows now backed by tests, not flipped here (phase 2)

ldx-history-model (R12-R16) is now verified by tests/test_store.py (unit) and
tests/test_routes_labels.py + tests/test_web_app.py print-flow tests (api), all run by the
Tests workflow; its row was not edited this phase (still not-implemented, `levels: {}`) and
should be moved to `ci` with those refs. ldx-label-name has its backend (default name,
rename via PUT) but needs the phase-3 editor field. Suite also green on Python 3.9 with the
CI-pinned deps.

<!-- fr:journal kind=discovery scope=plan id=no-refactor-p2-t1 created=2026-11-01T19:41:04+00:00 phase=2 -->
### no-refactor-p2-t1 · discovery · no-refactor-because P2.T1 (phase 2)

_persist/_write_atomic/_keep_copy were written as the single write path from the start (one temp+os.replace helper used for the main file and both backups); nothing left to clean

<!-- fr:journal kind=discovery scope=plan id=no-refactor-p2-t3 created=2026-11-01T19:41:04+00:00 phase=2 -->
### no-refactor-p2-t3 · discovery · no-refactor-because P2.T3 (phase 2)

the print flow was split into _render_for_print and _print_and_record as it was written, and T4's re-print route reuses both; nothing left to clean

<!-- fr:journal kind=discovery scope=plan id=no-refactor-p2-t4 created=2026-11-01T19:41:04+00:00 phase=2 -->
### no-refactor-p2-t4 · discovery · no-refactor-because P2.T4 (phase 2)

route error mapping lives in one _label_route decorator from the start, and /memory DELETE was moved onto the shared _ids_from_request/_fail helpers in the same commit; nothing left to clean

<!-- fr:journal kind=review scope=plan id=p2-review-r1 created=2026-11-01T20:01:57+00:00 phase=2 -->
### p2-review-r1 · review · Phase 2 code review: 8 findings (7 in, 1 out) (phase 2)

A dispatched general-purpose reviewer (superpowers:requesting-code-review template) reviewed ccf3223..f3c61e6 against the spec and plan phase 2, focused on data safety. It ran the suite (244 passed) and probes over 17 odd v1 entries, routes and thumbnail cost. Findings raised: p2-r1 to p2-r7 (in), p2-r8 (out). The orchestrator verified p2-r1, p2-r5 and p2-r6 against store.py and web_app.py; the implementer fixed all seven with tests (suite: 308 passed). A follow-up security review tightened p2-r4: backups take the source file's mode, masked 0o777. The orchestrator also checked that the new `migrated` text-cap exemption is only read from the history file, never from requests.

<!-- fr:journal kind=finding scope=plan id=p2-r1 created=2026-11-01T20:01:57+00:00 phase=2 state=open review_scope=in -->
### p2-r1 · finding [open] (reviewer: in scope) · v1 migration silently dropped entries failing v2 validation (phase 2)

store.py _migrate_v1_entry/_load_entries skipped on ValueError (font_size over cap, <=0 or null, long text, unknown stock, null copies/text).

<!-- fr:journal kind=finding scope=plan id=p2-r2 created=2026-11-01T20:01:57+00:00 phase=2 state=open review_scope=in -->
### p2-r2 · finding [open] (reviewer: in scope) · Non-object JSON body gave HTML 500 on four routes (phase 2)

web_app.py _ids_from_request, star, re-print.

<!-- fr:journal kind=finding scope=plan id=p2-r3 created=2026-11-01T20:01:57+00:00 phase=2 state=open review_scope=in -->
### p2-r3 · finding [open] (reviewer: in scope) · Thumbnail re-rendered every request, uncacheable (phase 2)

web_app.py thumbnail route: no-cache, no ETag.

<!-- fr:journal kind=finding scope=plan id=p2-r4 created=2026-11-01T20:01:57+00:00 phase=2 state=open review_scope=in -->
### p2-r4 · finding [open] (reviewer: in scope) · Atomic write left history/backups at 0600 (phase 2)

store.py mkstemp mode carried by os.replace.

<!-- fr:journal kind=finding scope=plan id=p2-r5 created=2026-11-01T20:01:57+00:00 phase=2 state=open review_scope=in -->
### p2-r5 · finding [open] (reviewer: in scope) · Content-match bump ignored printed name/copies and bumped the first match (phase 2)

store.py _content_match/record_print.

<!-- fr:journal kind=finding scope=plan id=p2-r6 created=2026-11-01T20:01:57+00:00 phase=2 state=open review_scope=in -->
### p2-r6 · finding [open] (reviewer: in scope) · Non-StoreError exceptions after a successful print returned 500 (phase 2)

web_app.py /print post-print except was too narrow.

<!-- fr:journal kind=finding scope=plan id=p2-r7 created=2026-11-01T20:01:57+00:00 phase=2 state=open review_scope=in -->
### p2-r7 · finding [open] (reviewer: in scope) · Sort route tests passed trivially (phase 2)

tests/test_routes_labels.py:91-96.

<!-- fr:journal kind=finding scope=plan id=p2-r8 created=2026-11-01T20:01:57+00:00 phase=2 state=open review_scope=out -->
### p2-r8 · finding [open] (reviewer: out of scope) · History file has no persistent volume; a future volume must mount a directory (os.replace over a single-file bind mount fails with EBUSY) (phase 2)

Same root as sr-14: docker-compose.yml has had no volume since before this change. The EBUSY note constrains the follow-up fix.

<!-- fr:journal kind=finding scope=plan id=p2-r1-resolved created=2026-11-01T20:01:57+00:00 phase=2 state=fixed resolves=p2-r1 -->
### p2-r1-resolved · finding [fixed] · resolves p2-r1: v1 migration silently dropped entries failing v2 validation (phase 2)

5974207 — lenient v1 path; test_v1_entry_that_v1_could_hold_is_kept (23 cases), test_v1_duplicate_ids_get_a_new_id_instead_of_being_dropped, test_v1_non_dict_item_is_the_only_thing_skipped, test_v1_empty_list_migrates_to_an_empty_v2_file, test_editing_a_migrated_long_text_label_applies_the_caps_again, test_migrated_over_cap_label_reprints_and_thumbnails.

<!-- fr:journal kind=finding scope=plan id=p2-r2-resolved created=2026-11-01T20:01:57+00:00 phase=2 state=fixed resolves=p2-r2 -->
### p2-r2-resolved · finding [fixed] · resolves p2-r2: Non-object JSON body gave HTML 500 on four routes (phase 2)

255f75d — test_a_non_object_body_is_400_json (4 routes).

<!-- fr:journal kind=finding scope=plan id=p2-r3-resolved created=2026-11-01T20:01:57+00:00 phase=2 state=fixed resolves=p2-r3 -->
### p2-r3-resolved · finding [fixed] · resolves p2-r3: Thumbnail re-rendered every request, uncacheable (phase 2)

b5f30f7 — immutable cache when versioned, ETag/304 otherwise, LRU keyed by (id, updated_at, content_key); test_versioned_thumbnail_is_immutable, test_unversioned_thumbnail_revalidates_by_etag, test_thumbnail_renders_once_per_version, test_thumbnail_cache_is_bounded.

<!-- fr:journal kind=finding scope=plan id=p2-r4-resolved created=2026-11-01T20:01:57+00:00 phase=2 state=fixed resolves=p2-r4 -->
### p2-r4-resolved · finding [fixed] · resolves p2-r4: Atomic write left history/backups at 0600 (phase 2)

f965523 + e1eae6e — mode preserved; backups take the source mode; masked 0o777; test_atomic_write_keeps_the_existing_mode, test_a_new_file_gets_the_umask_default, test_backups_take_the_source_mode_not_the_umask, test_corrupt_copy_takes_the_source_mode, test_main_write_keeps_0640, test_special_mode_bits_are_never_propagated.

<!-- fr:journal kind=finding scope=plan id=p2-r5-resolved created=2026-11-01T20:01:57+00:00 phase=2 state=fixed resolves=p2-r5 -->
### p2-r5-resolved · finding [fixed] · resolves p2-r5: Content-match bump ignored printed name/copies and bumped the first match (phase 2)

a6df57a — adopts the printed copies and an explicit name; bumps the most recently printed match; rule appended to spec R16; test_content_match_adopts_an_explicit_name, test_duplicate_then_print_bumps_the_most_recently_printed_match and 3 more.

<!-- fr:journal kind=finding scope=plan id=p2-r6-resolved created=2026-11-01T20:01:57+00:00 phase=2 state=fixed resolves=p2-r6 -->
### p2-r6-resolved · finding [fixed] · resolves p2-r6: Non-StoreError exceptions after a successful print returned 500 (phase 2)

7a8105f — test_unexpected_post_print_history_error_is_200_with_warning (both print routes).

<!-- fr:journal kind=finding scope=plan id=p2-r7-resolved created=2026-11-01T20:01:57+00:00 phase=2 state=fixed resolves=p2-r7 -->
### p2-r7-resolved · finding [fixed] · resolves p2-r7: Sort route tests passed trivially (phase 2)

4e46bff — test_list_sorts_with_nothing_starred, test_list_starred_filter_forms, and 2 more; mutation-checked by breaking the sort/starred passthrough (3 failed).

<!-- fr:journal kind=finding scope=plan id=p2-r8-resolved created=2026-11-01T20:01:57+00:00 phase=2 state=open resolves=p2-r8 out_of_scope=true -->
### p2-r8-resolved · finding [out-of-scope] · resolves p2-r8: History file has no persistent volume; a future volume must mount a directory (os.replace over a single-file bind mount fails with EBUSY) (phase 2)

Not caused by this change: the compose file has had no volume for saved_labels.json since before this branch (sr-14). Filed with sr-14 as one follow-up, carrying the directory-mount constraint.

<!-- fr:journal kind=decision scope=plan id=p3-dec1 created=2026-11-01T20:36:15+00:00 phase=3 -->
### p3-dec1 · decision · Select options are server-rendered; font selects use :selected (phase 3)

Alpine x-model on a select whose options are created later by x-for loses its value (reload showed the first stock). The stock options are rendered by Jinja and the font selects bind option :selected with an @change handler.

<!-- fr:journal kind=decision scope=plan id=p3-dec2 created=2026-11-01T20:36:15+00:00 phase=3 -->
### p3-dec2 · decision · Text boxes keep width_mm null when dragged; a Box width field was added (phase 3)

Moving a null-width text block shrinks its box (renderer: label width minus x minus margin), so the box is not rigid. A Box width (mm) inspector field (blank = auto) lets a user fix it; the drag-limit evidence uses 25 mm. The keep-1-mm clamp uses the last rendered bbox.

<!-- fr:journal kind=discovery scope=plan id=p3-d1 created=2026-11-01T20:36:15+00:00 phase=3 -->
### p3-d1 · discovery · Alpine 3.14.1 package ships no LICENSE file (phase 3)

npm pack alpinejs@3.14.1 contains dist/cdn.min.js (copied unmodified to static/vendor/alpine.min.js) but no LICENSE; static/vendor/LICENSE carries the MIT text with the upstream copyright line and names the version.

<!-- fr:journal kind=discovery scope=plan id=p3-d2 created=2026-11-01T20:36:15+00:00 phase=3 -->
### p3-d2 · discovery · Dev machine lacks the catalog fonts; matplotlib supplies real DejaVu (phase 3)

scripts/dev_server.py adds matplotlib's bundled DejaVu directory (when importable) to LABEL_FONT_DIRS beside tests/fixtures/fonts, so the capture shows several real families. The capture asserts the limits it shows (drag clamp 56 mm, scale = label width, copies 1/99, no horizontal scroll at 360 px, Ctrl+P prevented plus one /render).

<!-- fr:journal kind=discovery scope=plan id=p3-d3 created=2026-11-01T20:36:15+00:00 phase=3 -->
### p3-d3 · discovery · Acceptance matrix (phase 3)

ldx-single-ui and ldx-acceptance-doc moved to ci with refs. ldx-live-preview, ldx-history-panel, ldx-ux and ldx-label-name stay not-implemented: they await the orchestrator's visual-evidence acceptance and have no automated browser test in CI (the Playwright capture is not a CI job).

<!-- fr:journal kind=discovery scope=plan id=no-refactor-p3-t1 created=2026-11-01T20:36:15+00:00 phase=3 -->
### no-refactor-p3-t1 · discovery · no-refactor-because P3.T1 (phase 3)

the shell and assets were written once as their final shape; nothing to clean

<!-- fr:journal kind=discovery scope=plan id=no-refactor-p3-t5 created=2026-11-01T20:36:15+00:00 phase=3 -->
### no-refactor-p3-t5 · discovery · no-refactor-because P3.T5 (phase 3)

shortcuts, status polling and storage helpers were written as single small functions; nothing to clean

<!-- fr:journal kind=discovery scope=plan id=no-refactor-p3-t6 created=2026-11-01T20:36:15+00:00 phase=3 -->
### no-refactor-p3-t6 · discovery · no-refactor-because P3.T6 (phase 3)

a deletion plus docs; nothing to clean

<!-- fr:journal kind=review scope=plan id=p3-review-r1 created=2026-11-01T22:17:06+00:00 phase=3 -->
### p3-review-r1 · review · Phase 3 code + visual review: 25 findings over 5 passes, all verified fixed (phase 3)

A dispatched general-purpose reviewer (superpowers:requesting-code-review template) reviewed 0bc7793..a9358f6, then re-verified each fix round (0e19249, 76fdeb0, 08e5d44, 3439a07). Every pass re-ran scripts/capture_visual.py and the reviewer's own Playwright probes (limits, races, XSS, keyboard, failed fetches, localStorage throwing, dark at 360 px), opening every shot. Findings p3-r1 to p3-r25 were raised and all are verified fixed, with assertions in review_checks() or pytest tests. The final pass raised none. Vendored Alpine 3.14.1 matches the npm dist sha256. The orchestrator verified p3-r1, p3-r2 and p3-r16 against the code, and reclassified p3-r15 and p3-r16 from out to in scope, because store.duplicate and the renderer are this branch's code.

<!-- fr:journal kind=finding scope=plan id=p3-r1 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r1 · finding [open] (reviewer: in scope) · In-flight Save/Print reply reset editingId after Open; next Save overwrote the wrong label (phase 3)

In-flight Save/Print reply reset editingId after Open; next Save overwrote the wrong label.

<!-- fr:journal kind=finding scope=plan id=p3-r2 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r2 · finding [open] (reviewer: in scope) · afterSave snapshotted the current doc; in-flight edits lost the unsaved marker (phase 3)

afterSave snapshotted the current doc; in-flight edits lost the unsaved marker.

<!-- fr:journal kind=finding scope=plan id=p3-r3 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r3 · finding [open] (reviewer: in scope) · Ctrl/Cmd+Enter printed stale uncommitted number-field values (phase 3)

Ctrl/Cmd+Enter printed stale uncommitted number-field values.

<!-- fr:journal kind=finding scope=plan id=p3-r4 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r4 · finding [open] (reviewer: in scope) · Bulk delete had no confirmation (phase 3)

Bulk delete had no confirmation.

<!-- fr:journal kind=finding scope=plan id=p3-r5 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r5 · finding [open] (reviewer: in scope) · Dragging an auto-width text block lagged the pointer; glyphs could leave the label (phase 3)

Dragging an auto-width text block lagged the pointer; glyphs could leave the label.

<!-- fr:journal kind=finding scope=plan id=p3-r6 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r6 · finding [open] (reviewer: in scope) · Corner-handle scale ignored label height; handle clipped (phase 3)

Corner-handle scale ignored label height; handle clipped.

<!-- fr:journal kind=finding scope=plan id=p3-r7 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r7 · finding [open] (reviewer: in scope) · Open/New/reload discarded unsaved edits without asking (phase 3)

Open/New/reload discarded unsaved edits without asking.

<!-- fr:journal kind=finding scope=plan id=p3-r8 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r8 · finding [open] (reviewer: in scope) · Committing the in-place textarea lost keyboard focus (phase 3)

Committing the in-place textarea lost keyboard focus.

<!-- fr:journal kind=finding scope=plan id=p3-r9 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r9 · finding [open] (reviewer: in scope) · No maxlength 2000; unnamed render error (phase 3)

No maxlength 2000; unnamed render error.

<!-- fr:journal kind=finding scope=plan id=p3-r10 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r10 · finding [open] (reviewer: in scope) · History error shown with the empty state; raw 'Failed to fetch' (phase 3)

History error shown with the empty state; raw 'Failed to fetch'.

<!-- fr:journal kind=finding scope=plan id=p3-r11 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r11 · finding [open] (reviewer: in scope) · Empty names showed blank rows and aria-labels (phase 3)

Empty names showed blank rows and aria-labels.

<!-- fr:journal kind=finding scope=plan id=p3-r12 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r12 · finding [open] (reviewer: in scope) · Toasts covered history row buttons (phase 3)

Toasts covered history row buttons.

<!-- fr:journal kind=finding scope=plan id=p3-r13 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r13 · finding [open] (reviewer: in scope) · addImage placed new images over existing content (phase 3)

addImage placed new images over existing content.

<!-- fr:journal kind=finding scope=plan id=p3-r14 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r14 · finding [open] (reviewer: in scope) · Matrix rows not moved after shipping the UI (phase 3)

Matrix rows not moved after shipping the UI.

<!-- fr:journal kind=finding scope=plan id=p3-r15 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r15 · finding [open] (reviewer: in scope) · Duplicate kept an identical name (store.duplicate, this branch) (phase 3)

Duplicate kept an identical name (store.duplicate, this branch).

<!-- fr:journal kind=finding scope=plan id=p3-r16 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r16 · finding [open] (reviewer: in scope) · Image blocks painted opaque white over other content (renderer, this branch) (phase 3)

Image blocks painted opaque white over other content (renderer, this branch).

<!-- fr:journal kind=finding scope=plan id=p3-r17 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r17 · finding [open] (reviewer: in scope) · Confirm dialog did not take focus or trap Tab (phase 3)

Confirm dialog did not take focus or trap Tab.

<!-- fr:journal kind=finding scope=plan id=p3-r18 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r18 · finding [open] (reviewer: in scope) · Scaling to max tripped a false overflow (phase 3)

Scaling to max tripped a false overflow.

<!-- fr:journal kind=finding scope=plan id=p3-r19 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r19 · finding [open] (reviewer: in scope) · Stacked top-centre toasts covered the toolbar (phase 3)

Stacked top-centre toasts covered the toolbar.

<!-- fr:journal kind=finding scope=plan id=p3-r20 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r20 · finding [open] (reviewer: in scope) · Frozen text width not re-clamped on stock/orientation change (phase 3)

Frozen text width not re-clamped on stock/orientation change.

<!-- fr:journal kind=finding scope=plan id=p3-r21 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r21 · finding [open] (reviewer: in scope) · History actions enabled while busy; delete during print left a dangling editingId (phase 3)

History actions enabled while busy; delete during print left a dangling editingId.

<!-- fr:journal kind=finding scope=plan id=p3-r22 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r22 · finding [open] (reviewer: in scope) · Dialog focus used a fixed 30 ms setTimeout (race; capture flake) (phase 3)

Dialog focus used a fixed 30 ms setTimeout (race; capture flake).

<!-- fr:journal kind=finding scope=plan id=p3-r23 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r23 · finding [open] (reviewer: in scope) · Images placed at x/y 0 or flush with an edge (corner clipping, false overflow) (phase 3)

Images placed at x/y 0 or flush with an edge (corner clipping, false overflow).

<!-- fr:journal kind=finding scope=plan id=p3-r24 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r24 · finding [open] (reviewer: in scope) · Bottom toasts covered Search/Sort and row controls at 360 px (phase 3)

Bottom toasts covered Search/Sort and row controls at 360 px.

<!-- fr:journal kind=finding scope=plan id=p3-r25 created=2026-11-01T22:17:06+00:00 phase=3 state=open review_scope=in -->
### p3-r25 · finding [open] (reviewer: in scope) · In-flow toast strip off-screen when scrolled (history action feedback invisible) (phase 3)

In-flow toast strip off-screen when scrolled (history action feedback invisible).

<!-- fr:journal kind=finding scope=plan id=p3-r1-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r1 -->
### p3-r1-resolved · finding [fixed] · resolves p3-r1: In-flight Save/Print reply reset editingId after Open; next Save overwrote the wrong label (phase 3)

Fixed in 8ca37db/f82c538/0e19249; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r2-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r2 -->
### p3-r2-resolved · finding [fixed] · resolves p3-r2: afterSave snapshotted the current doc; in-flight edits lost the unsaved marker (phase 3)

Fixed in 8ca37db/f82c538/0e19249; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r3-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r3 -->
### p3-r3-resolved · finding [fixed] · resolves p3-r3: Ctrl/Cmd+Enter printed stale uncommitted number-field values (phase 3)

Fixed in 8ca37db/f82c538/0e19249; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r4-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r4 -->
### p3-r4-resolved · finding [fixed] · resolves p3-r4: Bulk delete had no confirmation (phase 3)

Fixed in 8ca37db/f82c538/0e19249; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r5-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r5 -->
### p3-r5-resolved · finding [fixed] · resolves p3-r5: Dragging an auto-width text block lagged the pointer; glyphs could leave the label (phase 3)

Fixed in 8ca37db/f82c538/0e19249; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r6-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r6 -->
### p3-r6-resolved · finding [fixed] · resolves p3-r6: Corner-handle scale ignored label height; handle clipped (phase 3)

Fixed in 0e19249, 76fdeb0; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r7-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r7 -->
### p3-r7-resolved · finding [fixed] · resolves p3-r7: Open/New/reload discarded unsaved edits without asking (phase 3)

Fixed in 8ca37db/f82c538/0e19249; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r8-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r8 -->
### p3-r8-resolved · finding [fixed] · resolves p3-r8: Committing the in-place textarea lost keyboard focus (phase 3)

Fixed in 8ca37db/f82c538/0e19249; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r9-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r9 -->
### p3-r9-resolved · finding [fixed] · resolves p3-r9: No maxlength 2000; unnamed render error (phase 3)

Fixed in 8ca37db/f82c538/0e19249; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r10-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r10 -->
### p3-r10-resolved · finding [fixed] · resolves p3-r10: History error shown with the empty state; raw 'Failed to fetch' (phase 3)

Fixed in 8ca37db/f82c538/0e19249; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r11-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r11 -->
### p3-r11-resolved · finding [fixed] · resolves p3-r11: Empty names showed blank rows and aria-labels (phase 3)

Fixed in 8ca37db/f82c538/0e19249; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r12-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r12 -->
### p3-r12-resolved · finding [fixed] · resolves p3-r12: Toasts covered history row buttons (phase 3)

Fixed in 0e19249, 08e5d44, 3439a07; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r13-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r13 -->
### p3-r13-resolved · finding [fixed] · resolves p3-r13: addImage placed new images over existing content (phase 3)

Fixed in 8ca37db, 76fdeb0, 08e5d44; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r14-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r14 -->
### p3-r14-resolved · finding [fixed] · resolves p3-r14: Matrix rows not moved after shipping the UI (phase 3)

Fixed in d554416..7246c69; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r15-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r15 -->
### p3-r15-resolved · finding [fixed] · resolves p3-r15: Duplicate kept an identical name (store.duplicate, this branch) (phase 3)

Fixed in c1b4851; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r16-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r16 -->
### p3-r16-resolved · finding [fixed] · resolves p3-r16: Image blocks painted opaque white over other content (renderer, this branch) (phase 3)

Fixed in c1b4851; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r17-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r17 -->
### p3-r17-resolved · finding [fixed] · resolves p3-r17: Confirm dialog did not take focus or trap Tab (phase 3)

Fixed in 76fdeb0, 08e5d44; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r18-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r18 -->
### p3-r18-resolved · finding [fixed] · resolves p3-r18: Scaling to max tripped a false overflow (phase 3)

Fixed in 76fdeb0; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r19-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r19 -->
### p3-r19-resolved · finding [fixed] · resolves p3-r19: Stacked top-centre toasts covered the toolbar (phase 3)

Fixed in 76fdeb0, 08e5d44; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r20-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r20 -->
### p3-r20-resolved · finding [fixed] · resolves p3-r20: Frozen text width not re-clamped on stock/orientation change (phase 3)

Fixed in 76fdeb0, 08e5d44; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r21-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r21 -->
### p3-r21-resolved · finding [fixed] · resolves p3-r21: History actions enabled while busy; delete during print left a dangling editingId (phase 3)

Fixed in 76fdeb0; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r22-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r22 -->
### p3-r22-resolved · finding [fixed] · resolves p3-r22: Dialog focus used a fixed 30 ms setTimeout (race; capture flake) (phase 3)

Fixed in 08e5d44; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r23-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r23 -->
### p3-r23-resolved · finding [fixed] · resolves p3-r23: Images placed at x/y 0 or flush with an edge (corner clipping, false overflow) (phase 3)

Fixed in 08e5d44; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r24-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r24 -->
### p3-r24-resolved · finding [fixed] · resolves p3-r24: Bottom toasts covered Search/Sort and row controls at 360 px (phase 3)

Fixed in 08e5d44; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.

<!-- fr:journal kind=finding scope=plan id=p3-r25-resolved created=2026-11-01T22:17:06+00:00 phase=3 state=fixed resolves=p3-r25 -->
### p3-r25-resolved · finding [fixed] · resolves p3-r25: In-flow toast strip off-screen when scrolled (history action feedback invisible) (phase 3)

Fixed in 3439a07; verified by the reviewer's re-run capture and probes; asserted in scripts/capture_visual.py review_checks() or pytest.
