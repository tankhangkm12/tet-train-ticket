# Discovery — what exists and what is needed (v24)

Used by `planner` when `STAGE=discover`, or before planning in an unfamiliar repo.

## Rules

1. **Describe what exists, not what should.** Record the strange thing the code does, cite where, note the doubt.
2. **Label every behavioural claim** (`references/discover/onboard/confidence-labels.md`): `[verified from code]` ·
   `[verified at runtime]` · `[inferred]` · `[unknown — needs <who>]`.
3. **Contradictions are recorded, not resolved.** Code vs docs vs comments — both sides quoted; the owner decides.
4. **Requirements describe the problem, not the solution.** No stack, tables, endpoints or components.
5. **Every requirement is testable** — concrete values, at least one negative AC. NFRs are numbers with a scale
   basis (users now / 12–24 months, peak rps, data per user, retention), projected with `scripts/core/capacity.py`.
   "Nhanh", "thân thiện", "phù hợp" are rejected on sight.
6. **Scope out is written down**, each row with its reason and "revisit when".
7. Reading source is free; **touching a running system** (run the app, any DB, logs, external APIs) is A3.

## Scope (every task, part of the plan)

Turn the short prompt into facts without asking the owner: read README, `.aizen/knowledge/`, the repo tree and
`git log` of the named paths; measure versions, contracts, configs. Record in the plan:
goal (checkable) · out of scope · constraints (measured) · done-when · assumptions (`verified` + evidence, or the
command that would verify it) · risk signals (live cluster, secrets, production, migration, destructive,
multi-service — unsure = true) · questions (preferences/risk only, with choices and a default).

## Onboard (legacy / new repo) — K0–K6

- **K0 Locate** what docs exist and how old (`git log` on them).
- **K1 Survey** wide and shallow (`references/discover/onboard/survey.md`): entry points, routes, schema, jobs,
  consumers, outbound calls, config key names (never values), tests, churn → system map (`assets/discover/system-map.md`)
  with a **Not found** table. Show it before going deep.
- **K2 Deep read** per service (`references/discover/onboard/as-built.md`): validation, permission checks,
  transaction boundaries, retries, idempotency, uniqueness by constraint vs by code.
- **K3 Write as-built docs** into `.aizen/knowledge/` with labels; decisions found in code marked
  `[reconstructed — never approved]`.
- **K4 Contradictions and unknowns**, each naming who could answer.
- **K5 Risk map** (`references/discover/onboard/risk-map.md`) ranked by impact × how quietly it fails.
- Report from `assets/discover/onboard-report-template.md`.
- **K6 Conventions** for coding agents (`references/discover/onboard/conventions.md`) → `.aizen/config/conventions.md`.
- Docs vs code drift → `references/discover/onboard/reconcile.md`.

## Requirements (new idea) — Q0–Q5

- **Q0 Problem** (`references/discover/requirements/stage-idea.md`): who has it, what it costs, all actors,
  what "solved" looks like, what is out, constraints, success metric → `assets/discover/idea.md`.
- **Q1 SRS in passes**, one per actor/journey (`references/discover/requirements/stage-srs.md`): steps, data,
  failure at each step, permissions → `FR`/`BR`/`NFR`; each `FR` gets Given/When/Then `AC`s incl. a negative one
  → `assets/discover/requirements.md`.
- **Q2 CORE pass**: money, points, stock, quota, multi-step state, several actors on one record, duplicates and
  races, external calls that fail midway → failure paths written in full.
- **Q3 Quality gate**: SRS exit gate row by row; requirements with ≥ 1 AC / total.
- Traceability: `references/design/traceability.md`.

## Handover

| To | Must contain |
|---|---|
| design | FR/BR with failure paths, NFR numbers + measurement, CORE marks, permission rules |
| tester | ACs in Given/When/Then with concrete values, negative cases |
| plan | priorities, scope out, CORE list, confidence per area |
