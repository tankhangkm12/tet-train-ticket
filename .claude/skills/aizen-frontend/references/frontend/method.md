# Frontend implementation — steps (v24)

Used by `dev` with `KIND=fe`.

## Rules

1. **Design + contract are the spec.** Every screen, state and field traces to `SCR`/`CMP`/endpoint.
2. **Never invent an endpoint, field or response shape.** Missing → contract gap in the report.
3. **Mocks are generated from the contract** and regenerated when its version changes.
4. **Every documented state is built**: loading, empty, partial, each error code, permission-denied,
   offline/stale, submitting, success.
5. **Server validation is mirrored, never contradicted**; its error codes drive the messages.
6. **Shared pieces** (design system, router, global state, i18n) only when in your write set.
7. **Build the design, not a guess.** Tokens and components from the UI design; taste (`style/<style>.md`) only
   fills gaps the design and the repo's design system leave. A new font/icon/motion library is A3.
8. **Look at it before you say it is done** — in a real browser (`visual-check.md`). No browser → visual rows
   `[unverified]`.

## Steps

- **F0 Locate.** Branch/worktree, start SHA; frontend doc, UI design (`<app>-ui.md`, `design-tokens.json`,
  `ui-exports/`), contract + version.
- **F1 Read.** Screens and every endpoint they touch, incl. the error list. List what the design does not settle
  (focus, stale list after mutation, double submit, optimistic rollback, partial failure) → simplest default,
  listed under `Deviations`; never ask mid-build.
- **F2 Build.** Mock from the contract, own dev-server port, the least code that meets the module's Done (`principles.md`), commit each
  green step. Spec is an image → `image-to-code.md`.
- **F3 Quality gate.** Build, type-check, lint, tests with counts; bundle budget; self-review with `checklist.md`
  and `web-interface-guidelines.md`.
- **F4 Verify per screen in the browser** (`visual-check.md`, `scripts/frontend/uikit.py`): each state and breakpoint —
  screenshot, console, diff vs export, contrast. ≤ 3 fix rounds per screen. Against the real API once the
  backend is integrated; mock vs real differences are findings.
- **F5 Hand off.** the quality-gate command from the brief; PR text with the state table (screenshot paths) →
  `.aizen/runs/<TASK>/reports/pr-body-<unit>.md`; report + push/PR commands for the owner.

## Guides (load only what the change touches)

| Change touches | Read |
|---|---|
| any frontend code | `principles.md`, `checklist.md` (before hand-off) |
| React / Next | `react.md` |
| API calls, errors, token refresh | `api-calls.md` |
| tokens in DOM/storage, logs | `security-logging.md` |
| accessibility, forms, focus | `accessibility.md`, `web-interface-guidelines.md` |
| visual style | `style/<style>.md` (taste, minimalist, soft, brutalist, redesign) + §Style overrides |

All in `references/frontend/`. Integrator and fix rounds: same as `references/backend/method.md`.

## Style overrides (win over every `style/*.md` guide)

1. **Priority:** the owner's decisions → the approved UI design (`<app>-ui.md`, `design-tokens.json`,
   exports) → the repo's design system and components → `references/frontend/web-interface-guidelines.md` → the style
   guide. The guide only fills what those leave open; it never changes an approved token, layout or
   component, and never `transition: all` or endless motion without a pause control.
2. **No new dependency** (font, icon set, motion or UI library) without the owner's yes (A3). Use what
   the repo already has; name the package you would want and why in the report.
3. **No external assets in committed code** — no placeholder-image services (picsum, Unsplash…), CDN
   fonts or remote scripts unless the owner approved them. Placeholders are local files or CSS.
4. **Accessibility beats aesthetics:** WCAG 2.2 AA contrast, measured (dev (fe) / tester: `uikit.py
   contrast`; `dev` (ui): the WCAG formula in `references/frontend/accessibility.md`, working shown), visible focus,
   `prefers-reduced-motion` honoured, touch targets ≥ 24 px.
5. Lines telling the agent *not to ask*, to "roll the dice" or to change "global variables" silently do
   not apply — `references/core/decisions.md` does. A choice among this guide's variants, dials or
   archetypes is made **once per project** as options to the owner, recorded as a `D-nn`, then reused.
6. **Stay inside the task.** Only the files of the current task change. An audit ("scan the codebase",
   "fix every generic pattern") is reported as a findings list; restyling other screens, swapping the
   font, and legal, cookie-consent, SEO or 404 additions are separate tasks the owner approves.
7. **No invented facts.** Names, copy, prices, dates and numbers come from the contract, fixtures or
   the owner — never an invented brand or product name, never realistic personal data, never ®/©/™ as
   decoration.
8. Report which rules you applied: `Style: <name> §<section>` per screen, and every rule you skipped
   because of 1–7.
