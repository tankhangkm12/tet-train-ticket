# Design — how it will be built (v24)

Used by `planner` when `STAGE=design`. Output: docs in `.aizen/knowledge/`, never code.

## Rules

1. **Decide nothing consequential.** 2–3 researched options on the same criteria, numbers, separate
   recommendation (`references/core/decisions.md`; `architecture-options.md`, `core-flow-options.md`,
   `fe-options.md`). The owner's defaults (`design-standards.md`) are offered as the recommended option, never
   applied silently.
2. **Research before proposing** — official docs with date, known pitfalls — or the option is `[unverified]`.
3. **Size before choosing** — users, rps, growth, connections, cost via `scripts/core/capacity.py` (`references/core/numbers.md`).
4. **Every requirement lands or is explicitly out** (`traceability.md`): FR/BR → LLD → table/constraint → endpoint → screen.
5. **Rules enforced only in code are not enforced.** "Exactly one", "never duplicate" → UNIQUE, CHECK, PK or atomic
   update — or documented as a race.
6. **The contract is a promise.** Changing an approved one = decision + impact table + new version.
7. **Contradictions stop the work** — conflict table, ask. Diagrams are ASCII; render the important ones with archify when it is installed (`diagrams.md`).

## Stages

| Stage | Output | Guide | Template |
|---|---|---|---|
| HLD | `architecture.md` (+ `<svc>-overview.md`) | `stage-hld.md` | `assets/design/architecture.md` |
| LLD | `<module>-design.md` | `stage-lld.md` | `assets/design/module-design.md` |
| DB | `<unit>-database.md` | `references/db/schema-design.md` | `assets/db/database.md` |
| API | `<unit>-api.md` + `.yaml` | `stage-api.md` | `assets/design/api.md` |
| Frontend | `<app>-frontend.md` | `frontend-design.md` | `assets/design/frontend.md` |
| Security | `security.md` | `threat-model.md`, `authz-matrix.md` | `assets/design/security.md` |
| Rendered diagrams (optional) | `diagrams/<slug>/<slug>.html` next to the doc | `diagrams.md` (archify, when installed) | — |

All guides are in `references/design/`. Pick only the stages the task needs; small changes edit the existing doc.

Each stage: read SRS + existing docs + `decisions.md` → 2–4 objections to the input → write from the template
(drop sections that do not apply) → print the stage's exit gate row by row with evidence → record decisions
(`decision-log.md`).

## Contract (API stage) is done when

- every endpoint has request, response, **every error with code and status**, auth and ownership rule,
  pagination/limits, idempotency where a retry could duplicate an effect;
- error codes come from one catalog, one status each;
- the `.yaml` is valid and can generate the mock the frontend builds against;
- it carries a version. API-consumer cost (calls per screen, contention) → `references/api-ux/method.md`.

## Frontend design

Screens `SCR-nn` (purpose, actor, data, actions, permissions, FR); for every screen the state table (loading,
empty, partial, each error code, permission-denied, offline/stale, submitting, success); component tree
`CMP-nn`; one owner per piece of state; routes with guards; budgets as numbers. Missing data → **Contract gaps**.

## Security

Data value, plausible attacker, compliance, existing controls → trust boundaries → STRIDE per boundary and CORE
flow → each `THR-nn` with scenario, likelihood, impact and a control `CTL-nn` or a risk for the owner to accept →
authZ matrix: endpoint × actor with the ownership condition.

## Change

Before editing an approved doc: impact table (sections, tables, endpoints, screens, tests, work already built on
the old version). The owner approves; then edit, bump the version, add the `D-nn` row with "Replaces".
