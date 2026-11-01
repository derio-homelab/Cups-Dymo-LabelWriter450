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
