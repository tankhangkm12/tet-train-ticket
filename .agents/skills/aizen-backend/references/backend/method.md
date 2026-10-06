# Backend implementation — steps (v24)

Used by `dev` with `KIND=be`.

## Rules

1. **Plan + docs are the spec.** Every change traces to a requirement, step or finding id. Nothing invented.
2. **Missing or ambiguous → simplest option that fits the plan**, listed under `Deviations:`; never ask mid-build.
   Contradicts the agreed plan or contract → `BLOCKED`.
3. **The API contract is frozen.** A contract that does not fit is a change request with reason and cost — never a
   quiet edit or an extra field "while here".
4. **Schema changes** follow `references/db/method.md` (migration with rollback, lock budget). They belong to a
   `db` unit.
5. **Stay inside the task**: nearby tests/types/fixtures needed for the behaviour are fine; unrelated cleanup is not.
6. **Tests**: run the existing ones; add focused regression tests for what you changed. Existing tests failing
   because behaviour was meant to change → update them when the plan says so, else `BLOCKED`.

## Steps

- **D0 Locate.** Code, tests, docs, `git status`; branch/worktree from the brief; record the start SHA.
- **D1 Read.** The brief's doc sections and the **nearest similar module** (the pattern to copy). Behaviour the plan
  does not settle (error precedence, trimming, repeat calls, limits, empty states) → the simplest default, listed
  under `Deviations`.
- **D2 Task type**: bug → `references/dev/bugfix.md` · refactor → `references/dev/refactor.md` · new module →
  `references/dev/scaffold.md` · open core choice → `BLOCKED` (`references/dev/solution-options.md`) · outside the plan →
  `references/dev/out-of-scope.md`.
- **D3 Code.** The least code that meets the module's Done (`principles.md`, `references/core/code-quality.md`), commit each green step;
  back up what git does not hold before touching it.
- **D4 Quality gate.** Build/type-check, lint+format (touched files), tests — commands quoted with counts.
  Red already on the base → report, do not fix silently. Self-review the diff with `checklist.md`.
- **D5 Verify per id.** Happy path, each documented error case, the permission case: request → response →
  expected, in the report.
- **D6 Hand off.** the quality-gate command from the brief; PR text from `assets/core/pr-draft-template.md` (with the
  Rollback block) → `.aizen/runs/<TASK>/reports/pr-body-<unit>.md`; report + push/PR commands for the owner.

## Guides (load only what the change touches)

| Change touches | Read |
|---|---|
| any backend code | `principles.md`, `checklist.md` (before hand-off) |
| endpoints, errors, pagination | `api-contract.md` |
| layering, module boundaries | `architecture.md`, `module-boundaries.md` |
| transactions, locks, money, idempotency | `data-concurrency.md` |
| logs, secrets, PII | `security-logging.md` |
| several services, events, outbox | `microservices.md` |
| queues, event streams, consumers, DLQ (Kafka, RabbitMQ) | `messaging.md` |
| file upload/download, buckets (S3, MinIO, R2) | `object-storage.md` |
| config, health, env vars | `infrastructure.md` |
| stack specifics | `stacks/java.md` · `stacks/python.md` · `stacks/typescript-nestjs.md` · new stack: `stacks/_new-stack.md` |

All in `references/backend/`.

## Integrator (`UNIT=int`)

Create `int/<TASK>` from the base in your worktree, merge the listed branches in order, record each SHA, run build
+ quick checks. No feature work. A conflict in a unit's logic: resolve only when the intended behaviour is clear
from the docs; otherwise `HANDOFF` to that unit's owner with both sides.

## Fix rounds (`ROUND ≥ 1`)

Fix only the listed finding ids, one commit per group; report each as `fixed @<sha>` or `not fixed — why`, with
checks re-run on the new SHA.
