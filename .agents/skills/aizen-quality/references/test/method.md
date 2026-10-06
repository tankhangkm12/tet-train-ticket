# Independent testing — steps (v24)

Used by `tester`. Prove with evidence whether the system does what the docs promise — including every way it must
fail. Never change product code; never claim an unrun check passed.

## Rules

1. **Independent.** Never test code you wrote in this run; if unavoidable, label `[self-tested]`.
2. **Docs are the oracle.** Every case cites an `AC`/`FR`/`BR`/error code/`NFR`/plan step. Code and docs disagree →
   a finding, never an assertion of what the code does.
3. **Missing expected behaviour → never invent it**: write the case as a question in the report (`Q-n`), test
   what the plan does settle, and go on; a gap that blocks every case → `BLOCKED`.
4. **Trustworthy tests**: deterministic, isolated, synthetic data, no sleeps as synchronisation, no real external
   services unless approved.
5. **Never hide a failure.** Flaky → ≤ 2 reruns, every attempt reported. A product-bug test stays red.
6. **Pin what you tested**: SHA, contract version, environment, tool versions.
7. **Missing environment** (seeded DB, container, pipeline step) → request in the report, not a change you make.
8. **Own runtime**: ports, compose project `<TASK>-test`, DB `<db>_test`, browser session from the brief.
9. **Lane**: test code, fixtures, test config only. Product code, migrations, IaC, CI → `BUG` + `HANDOFF`.

## Lenses — one report, one section per lens

The brief lists lenses (`LENS=functional,ui,…`); the guide for each is `references/test/lenses/<lens>.md`:
`functional` · `integration` · `concurrency-perf` · `security` · `ui` · `database` · `infra` (validate only, never apply).
A risk outside your lenses → one line `HANDOFF: needs tester LENS=<lens> — <what>`.

## Steps

- **T0 Locate.** Target branch + SHA, plan, ACs, contract, dev reports, open BUGs, existing tests.
- **T1 Design** (`test-design.md`): boundaries, errors, races, repeats, permissions, traceability to ids.
  New epic without a strategy → `test-strategy.md` → `assets/test/test-plan.md`.
- **T2 Write** per `test-levels.md`, in the repo's frameworks and conventions (UI: `@playwright/test`;
  `references/frontend/visual-check.md` + `scripts/frontend/uikit.py` for evidence).
- **T3 Run and triage** the new tests and the full existing suite. Each failure: test bug (fix the test) · product
  bug (`bug-report.md`) · doc ambiguity (ask) · environment/flaky (≤ 2 reruns).
- **T4 Report** `.aizen/runs/<TASK>/reports/test.md` from `assets/test/test-lens-report.md`: SHA, counts with denominators,
  ACs covered/uncovered, perf vs NFR, and the BUG table
  `| ID | Title | Severity | Repro | Evidence |` with ids `BUG-<lens>-nn` (stable across rounds).
  Severity: Critical/High → BLOCKER, Medium → SHOULD-FIX, Low → SUGGESTION.
- **T5** the quality-gate command from the brief; return ≤ 15 lines.

## Fix rounds (`ROUND ≥ 1`)

Re-run only lenses with open bugs or touched by the fix, at the new SHA. Fill the Re-test table
(`VERIFIED` / `REOPENED` / `STILL_OPEN` per bug id), add bugs the fix introduced. The BUG table lists only what is
open at this SHA.
