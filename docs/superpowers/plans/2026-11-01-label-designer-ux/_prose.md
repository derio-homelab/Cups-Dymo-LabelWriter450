# Label designer UX — implementation plan

Spec: `docs/superpowers/specs/2026-11-01-label-designer-ux-design.md` (issue #2).

Three agentic phases, one per independently reviewable ask:

1. **Renderer** (skeleton). The smoke comes first: a session-wide fake `cups` plus a new `Tests` CI
   workflow, green on a trivial test. Then the font catalog, the document model, the multi-block
   renderer, images, orientation at print, the render routes and the Docker dependencies. Every
   later phase builds on `render()` and the document model.
2. **History**: the v2 store with migration, the operations and the `/labels` API, plus the print
   flow (edit in place, content-match bump). This phase changes the only persistent user data, so
   it runs on the `hard` tier.
3. **UI**: the Alpine-based designer with the in-label preview and inline editing, the history
   panel, the UX items, the legacy `web_app/` removal and the docs.

Test command (local; it needs no pycups):

```bash
uv run --no-project --with flask --with pillow --with cairosvg --with pytest --with pytest-cov --with pytest-mock python -m pytest
```

Post-merge physical-print checks are the spec's Test Plan (rows `ldx-print-orientation` and
`ldx-print-mono`, `verify: live`, gate `tester`). They are not phases.
