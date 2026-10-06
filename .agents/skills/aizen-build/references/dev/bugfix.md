# Bug fix — diagnose in the plan, then fix without asking (v25)

A wrong hypothesis hides the real bug, so the cause is settled before code changes. **Phase 1 is planning**
(planner, or you when you plan a one-module fix): its output is the bug's module in the plan, and the owner picks
the fix option when the owner confirms that module. **Phase 2 is the dev's**, after `approve`, with no questions.

Inputs usually: a `BUG-nn` report from `tester`, a review finding, or the owner's description. Missing facts
are measured; preferences go into the module's questions.

## Phase 1 — Diagnose (change nothing, not even one character)

1. **Symptom precisely:** expected vs actual (values, messages, status codes, what the screen shows);
   conditions (always? which data? concurrency? which environment/browser?); since when (which change?).
2. **Reproduce**, in order of confidence — say which one you achieved:
   - backend: re-run the exact flow with the failing data (API client / curl) · logs, stack traces, data;
   - frontend: re-run it in the browser (console, network tab, the failing response's `errorCode` and
     `requestId`); say whether it reproduces against the **mock**, the **real API** or both — that alone
     often localises it;
   - reasoning from code only is the weakest; say "not reproduced; hypothesis from code reading".
3. **Root cause:** walk back from the symptom to where the data or state first goes wrong. Separate
   *symptom* ("API 500", "the list still shows the cancelled order"), *crash site* ("items[0] undefined
   at line 42") and **root cause** ("the join does not select children", "the cancel mutation never
   invalidates the orders query"). Fixing the crash site is fixing a symptom — not allowed.
4. **Check the docs:** is the code wrong, or are the docs wrong/silent? Docs wrong/silent → a doc issue:
   a question with options in the module; never decide the correct behaviour yourself.
5. **Search** (`references/core/decisions.md` §7) when the bug touches a library, framework or engine: known issues,
   changelogs, fixed versions.

## Phase 1 output — the bug's module in the plan

```markdown
**Symptom:** expected … / actual …
**Reproduction:** <how, where> — or "not reproduced; inferred from code"
**Failing cases:** - <condition 1> - <condition 2>
**Root cause:** <1–3 sentences> — evidence `path:line`
**Doc reference:** <ID/§ that defines correct behaviour> — or "docs silent → question below"
**Blast radius:** other places with the same flaw; data already wrong?
**Fix options** (decisions.md §6 — ≥3 when they exist, one may be "document and leave"):
| | A | B | C |
|---|---|---|---|
| change | … | … | … |
| files / risk | … | … | … |
| covers other occurrences? | … | … | … |
I lean to A because …
**Risk of the fix:** what could break; who calls this
**Not yet verified:** …
```
Code follows project convention but the convention is risky → frame as (A) deviate / (B) keep and accept.

## Phase 2 — Fix (dev, after `approve`)

- Task branch `bugfix/<TASK>-<desc>` (released code under gitflow: `hotfix/<TASK>-<desc>` from `main`),
  start SHA recorded (`references/core/git.md` §2). The files must be in the approved write set.
- Implement exactly the approved option at the root cause, with the least code. A better idea mid-way →
  `## Proposals`; the approved option cannot work → `BLOCKED`.
- Smallest diff (`references/core/code-quality.md`): no reformatting, renaming or tidying outside the fix; other smells →
  report only.
- A focused regression test that fails before the fix and passes after, when its path is in the task
  envelope/scope; otherwise the reproduction steps go to the report for `tester`. Either way add
  "For other roles: TEST — independent regression for BUG-nn".
- Run the module's test suite; re-run the reproduction and record before/after.
- Data already wrong: never write a data-fix script on your own and never repair server data from the
  client — report it (irreversible; a data fix is its own task with a backup, `references/core/git.md` §4). Corrupted
  persisted client state (storage, cache) is reported with what would clear it.
- Commit `fix(scope): … [TASK]` with `Refs BUG-nn`.

Continue with the quality gate and hand-off steps of `references/backend/method.md` (be) or `references/frontend/method.md` (fe). The report adds **Root cause** (1 line),
**Regression test needed** and the Rollback block. Self-critique: could this fix hide another bug; where
else does the same flaw exist?
