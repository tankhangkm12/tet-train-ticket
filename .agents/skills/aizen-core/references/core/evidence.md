# Evidence, numbers and reports (v25)

The owner steers from what agents report. A confident wrong number, or a claim of DONE that the files
do not support, steers the owner wrong. So claims carry evidence proportionate to the work, and reports are short enough to actually be read.

## 1. Numbers — computed, or not stated

Measured metrics below; projections (capacity, growth, cost) follow `numbers.md`.

Every metric: `<value> — <formula> — <source: command/file/tool> — <when>`.
Example: `coverage 72.4% (412/569 lines) — covered/total — vitest --coverage @3f2a9c1 — 2026-09-23`.

Missing any part → do not state the number; ask the question instead ("không đo được coverage — chưa
có công cụ; thêm công cụ hay chấp nhận unit này không có số coverage?").

Never estimated: coverage · latency/throughput/bundle size · requirement coverage · defect counts ·
progress · cost — each is measured, or projected with a formula and inputs (`numbers.md`), never
guessed. **Effort and time are never estimated at all** — size is scope (IDs, files).
Always state the denominator and exclusions ("12/14 pass, 2 fail: BUG-03, BUG-04"; "p95 excluding
warm-up").

| Role | Reports |
|---|---|
| planner | requirements with ≥1 AC / total · ids placed in exactly one unit / total · endpoints, screens, threats fully specified / total |
| dev (be, fe) | ids verified / ids in unit · build, lint, tests: pass/fail counts with the command |
| dev (db) | queries meeting target / in scope · p95 before → after with data size · pool total vs connection limit |
| dev (ui) | screens × states designed / required · contrast pairs passing / checked |
| tester | ACs with ≥1 TC / ACs in scope · passed/failed/skipped/flaky · coverage with tool · perf vs NFR |
| reviewer | findings by severity · claims confirmed / checked (verify lens) |
| devops | apply result · rollback rehearsed yes/no · cost delta with source |

## 2. Evidence records

**Every check:** record enough to reproduce the relevant check: command/method, result, changed files, target revision when meaningful, and the Rollback block (`git.md` §5). Do not create a formal evidence appendix for a two-line fix unless it helps.

**Risk modules / merge-release readiness:** every check, run or review names: task · role/instance · time · source SHA (and contract hash or
artifact digest when relevant) · environment · command or method · exit status · raw output path ·
limitations. Redact credentials and personal data when collecting, not later. Template:
`assets/core/evidence-record.json`; `check.py` writes `evidence/<unit|main>.json` in this shape.

- **Claims are not facts.** An agent's "DONE" is checked against the files, branch, SHA and output.
  Trust the file; report the gap.
- **Evidence goes stale.** A test or review at SHA `a` says nothing about SHA `b`. Re-run what the
  change affects.
- **Hashes show change, not truth.** A matching hash proves the file is the same, not that the log is
  honest or the check was complete.

## 3. Report shape

File: `.aizen/runs/<TASK>/reports/<role>[-<unit>].md` — the exact name is in your brief.

```markdown
> **<ROLE> · <TASK> <UNIT> · <STATUS>**
> Done: <finished, with the measured number>
> Now: <in hand, where it stopped>
> Blocked: <what, by what — or "nothing">
> Decide: <numbered items for the owner — or "nothing">
> Next: <one action, and who does it>
> Deviations: <none — or each place the work differs from the owner's instruction or the docs, and why>
> HANDOFF: needs <role> — <what>          (only when the lane stopped the work; one line per handoff)

## Needs your decision     — `[agent-chosen]` first; each with options + recommendation
## Measured                — only metrics that changed or gate this step
## Challenges              — raised and received, with status
## Findings / Details      — role-specific, bounded; evidence in the appendix
## For other roles         — one line per role that must know something
## Rollback                — `git.md` §5 block: branch, start SHA, commits, backups, commands
## Appendix                — raw evidence, long output, commands to reproduce
```

`STATUS` ∈ `WAITING_FOR_OWNER` · `BLOCKED` · `DONE` · `IN_PROGRESS`. A role stopped by its lane returns
`BLOCKED` with its `HANDOFF` line(s) and whatever it finished inside the lane.

**HANDOFF line** — `HANDOFF: needs <role> — <what>` when the work
needs another role's lane or specialist work; the coordinator dispatches that role, the reporting role never
does the work itself.

In a fix round (`ROUND≥1` in the brief) the report lists, per finding id, `fixed @<sha>` / `not fixed — why`
and the checks re-run on the new SHA.

Caps: chat return ≤ 15 lines, Deviations line included (it says where the report is) · report body ≈ 120 lines before the
appendix · one finding ≤ 6 lines (problem · scenario · evidence · direction) · quoted output ≤ 10
lines in the body.

**Deviations line — every finish.** Every report ends with the changed files, the checks and
`Deviations: none` (or the list). A deviation is anything done differently from what
the owner agreed or what the docs say: a different approach, an extra file, a skipped check, a detail the plan
left open and you chose.
It is how the owner audits obedience in one glance; an unreported deviation is a defect of the report.

Writing rules: numbers over adjectives · name things by ID · bad news first · no effort, no
self-praise ("thành công tốt đẹp" carries no information) · do not restate the plan · "I could not
verify X" is one of the most useful lines a report can carry.
