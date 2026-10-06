---
name: aizen-design
description: Aizen knowledge pack (v24) — scope, legacy onboarding (as-built docs), idea and SRS requirements, HLD/LLD, API contract, frontend architecture, authorization matrix, threat model. Loaded by Aizen roles through their brief; not a standalone skill, do not trigger it directly — use aizen-build.
---

# Discovery and design knowledge — Aizen pack (v24)

Owns the topics `discover`, `design`: every `references/<topic>/…`, `assets/<topic>/…` and `scripts/<topic>/…` path for them
lives here. Shared rules (authority, evidence, code quality, style) are in `aizen-core`; the flow and roles are in
`aizen-build`.

- **Used by:** planner (`STAGE=discover|design`); reviewer (design, plan, as-built lenses).
- **Entry points:** `references/discover/method.md` · `references/design/method.md` — each has a "Guides" table; load only the rows the change touches.
- Templates: `assets/discover/` (idea, requirements, system map, onboarding report) and `assets/design/` (architecture, module design, API, security, frontend architecture).
