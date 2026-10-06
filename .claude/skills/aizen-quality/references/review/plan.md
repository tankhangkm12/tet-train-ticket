# Reviewing an execution plan

Every role executes the plan faithfully, so a plan defect is caught by no later gate — it shows up as rework
across units. Judge it against the documents it plans from, never against taste.

Inputs: `.aizen/runs/<TASK>/plan.md`, the documents it cites (read them — do not trust the plan's summary),
the repo structure, `.aizen/runs/<TASK>/state.md`, and the state of any wave already running.

## 1. Axes, heaviest first

1. **Traceability both ways.** Every in-scope requirement id lands in exactly one unit or in "out of scope"
   with a reason; every unit cites ids that exist. List both sets and the difference — never sample.
2. **Root cause is measured.** A fix premise stated as fact without `[verified]` evidence needs a measurement
   unit first.
3. **Write sets are disjoint per wave** — including the forgotten collisions: DI modules, routers, migration
   sequence, lockfiles, i18n bundles, shared enums, the error catalog (`references/flow/parallel.md`).
4. **Order is real and acyclic.** Each `After` points at a unit that produces what is needed; no unit needs a
   later wave to compile; an infra unit never waits on a deploy target nobody creates.
5. **Every needed role is there.** Delivery-path work (new deployable, env var, secret name, real-environment
   migration, CI step, alert an NFR needs) without an `infra` unit; behaviour changes with no test lens.
6. **One purpose per unit**, reviewable in one pass; no refactor mixed into a feature.
7. **Doc gaps settled, not deferred.** An open contradiction that a scheduled unit depends on is a BLOCKER.
8. **Buildable without questions.** Each module fixes its interface, data, files and test cases; a design
   choice left to the dev (a name, a status code, an algorithm for core logic) is a SHOULD-FIX.
9. **Risk-module detail** (`references/plan/planning-method.md`): exact write set, commands, checks, backup and
   rollback per unit; destructive or recovery steps have a tested rollback.
10. **No time estimates**, and no unit that is really a decision in disguise ("investigate whether…" is a
   question for the owner in that module).

## 2. Severity

| Level | Examples |
|---|---|
| **BLOCKER** | requirement in no unit · dependency cycle · overlapping write sets in one wave · unit scheduled on an unresolved contradiction · unmeasured root cause stated as fact · destructive step without a tested rollback |
| **SHOULD-FIX** | oversized unit · missing test lens for a real change · vague "Checks" |
| **SUGGESTION** | ordering or grouping that would read better |

Finding format: `references/review/method.md`. Also report the coverage table
(`id · unit · lens · status`) and, past three units, the wave graph as ASCII.

Re-review after a plan change: read "Plan changes" first, then check only what moved plus traceability and
order — the two things a re-cut breaks most often.
