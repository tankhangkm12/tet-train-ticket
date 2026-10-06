---
name: aizen-frontend
description: Aizen knowledge pack (v24) — frontend principles, React/Next performance rules (Vercel), API calls, accessibility, visual checks, style guides, UI design process, tokens and handoff. Loaded by Aizen roles through their brief; not a standalone skill, do not trigger it directly — use aizen-build.
---

# Frontend and UI design knowledge — Aizen pack (v24)

Owns the topics `frontend`, `ui`: every `references/<topic>/…`, `assets/<topic>/…` and `scripts/<topic>/…` path for them
lives here. Shared rules (authority, evidence, code quality, style) are in `aizen-core`; the flow and roles are in
`aizen-build`.

- **Used by:** dev `KIND=fe|ui`; tester (ui lens); reviewer (frontend, ui lenses).
- **Entry points:** `references/frontend/method.md` · `references/ui/method.md` — each has a "Guides" table; load only the rows the change touches.
- Tool: `scripts/frontend/uikit.py` (contrast, palette, screenshots). Templates: `assets/ui/ui.md`, `assets/ui/design-tokens.json`, `assets/frontend/playwright-cli.config.json`.

## Upstream knowledge (vendored, pinned)

Best practice from the people who build the tools, copied verbatim at a pinned commit (`vendor.lock.json`
in the Aizen repo). It says how to do a thing right in that tool; Aizen core rules still decide how much to build
and who decides (`references/core/workspace.md` §3).

| Source | Details |
|---|---|
| Vercel — React and Next.js best practices | `references/frontend/vendor/vercel-react-best-practices/UPSTREAM.md` |
