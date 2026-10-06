# Build flow — one flow for every task (v25)

You are the main session. You run this flow, dispatch roles, merge branches and talk to the owner. Roles do the
specialist work. State lives in `.aizen/runs/<TASK>/`. Below, `state.py` means
`uv run "<SKILL_DIR>/scripts/flow/state.py"` and `graph.py` means `uv run "<CORE_DIR>/scripts/core/graph.py"`
(`<SKILL_DIR>` = this skill's folder, `<CORE_DIR>` = the `aizen-core` folder next to it).

**Two phases.** Plan and design are slow and talked through with the owner **module by module**. Once the owner
approves, the plan is the contract: build, test, review and fix run to the end **without asking the owner anything**.

Size changes the plan, not the flow: a one-module task gets a one-module plan (you may write that plan and
build that module yourself); tester and reviewer still run.

## S0 — Intake (you)

1. `state.py init --task <TASK> --goal "<the owner's prompt>"` (resuming → `state.py status --task <TASK>`, read
   `state.md`; never re-ask what `## Agreed` already holds).
2. Code map: `graph.py --project <ROOT>` (`references/core/code-map.md`). Exit 3 = graphify missing → its
   install command goes to S2 as an A3 item; use grep meanwhile.
3. Read `CLAUDE.md`/`AGENTS.md`, `.aizen/{conventions,lessons}.md`, then ask the map (`graphify query`) or skim
   only the code the prompt names.

## S1 — Plan and design (1 × planner)

Dispatch `planner` with `state.py brief --task <TASK> --role planner [--stage discover|design]`. It measures
facts itself and writes `.aizen/runs/<TASK>/plan.md` in the module shape (`references/plan/method.md`): scope,
then one block per **module** (= unit: behaviour, interface/contract, data, files/write set, tests, risk,
options, open questions), then delivery (order, A3 actions, rollback). Risk modules (auth, money/stock/quota,
tenants, schema/data migration, concurrency, public contract, CI/CD/IaC, live systems, secrets, destructive,
production) carry the extra detail of `references/plan/planning-method.md`.

New product area or unclear behaviour → `STAGE=discover` / `STAGE=design`: requirements/design docs first,
in the same dispatch.

## S2 — Confirm with the owner, part by part (you)

Walk the plan in this order; each step is one question round (Claude Code: AskUserQuestion, ≤ 4 questions,
recommended option first; Antigravity: `ask_question`; otherwise one numbered message):

1. **Scope** — goal, in / out of scope, acceptance criteria. → `state.py answer --task <TASK> --module scope --text "<the owner's answer>"`
2. **Each module, in plan order** — its design in ≤ 15 lines (behaviour, interface, data, files, tests, risk)
   plus its options and questions. → `state.py answer --task <TASK> --module <unit> --text "…"`
3. **Delivery** — build order/waves, the A3 actions to pre-approve (installs incl. graphify, local DB,
   downloads), base branch, models. → `--module delivery`
4. Every change the owner asks for goes into the plan (small: edit it yourself; structural: re-dispatch the planner
   with the owner's words as `--inputs`), then re-confirm **only that module**.
5. **Approve** — "approve plan <TASK> (vN)?" → `state.py approve --task <TASK> --text "<the owner's words>"`.
   It refuses while `scope`, `delivery` or any `## Module <id>` of `.aizen/runs/<TASK>/plan.md` has no recorded answer
   — the rule "never skip a module" is enforced, not remembered.

Never batch everything into one card, never skip a module, never start a writer before `approve`
(`state.py` refuses the brief).

## S3 — Build (N × dev, one message per wave)

- Per unit: `git worktree add .aizen/worktrees/<TASK>-<unit> -b feature/<TASK>-<unit> <base>`, its own ports and DB name.
- `state.py brief --task <TASK> --role dev --kind <be|fe|db|ui> --unit <unit> --sha <start SHA>
  --write-set "<globs>" --a3 "<approved A3 actions>"` → dispatch **all units of a wave in one message**. Infra
  units: `--role devops --unit <unit>`.
- Units that share a file or an unsettled seam run in sequence, not in parallel.
- On return: read the report, then **check the files** — diff, commits, tests, `Deviations:`. A claim the files
  do not support is a finding.

## S4 — Integrate (you, git only)

More than one unit → integration worktree, `int/<TASK>` from the base, `git merge --no-ff` each unit branch in
plan order. Clean merge is yours. Conflict → `git merge --abort` and dispatch a `dev` with `UNIT=int` naming
both branches and the agreed behaviour. Never resolve a conflict by hand. Then, in the `int/<TASK>` worktree:
`check.py --task <TASK> --unit int` → `evidence/int.json` (the guard requires it PASS at the int tip).

## S5 — Test (1 × tester)

`state.py brief --task <TASK> --role tester --lens <a,b,…> --sha <SHA>` on `int/<TASK>` (or the single unit
branch). Lenses from the diff: always `functional`; add `integration` (several units/services), `ui` (screens),
`database` (migrations, queries), `security` (auth, input, secrets), `concurrency-perf` (locks, money, load).
Two testers only when a heavy lens would dominate (`--unit <lens>` each).

## S6 — Review (1–2 × reviewer)

`state.py brief --task <TASK> --role reviewer --lens <…> --sha <SHA>`, preferably on a different model than the
devs. Verdict PASS / CHANGES_REQUIRED / INCOMPLETE with findings (BLOCKER / SHOULD-FIX / SUGGESTION).
Any risk module in the plan → also a second reviewer with `--lens redteam` (data loss, secrets, irreversible
steps, authZ bypass); its BLOCKER is never overruled by the first reviewer.

## S7 — Fix loop (≤ 2 rounds, no questions)

While a BLOCKER/SHOULD-FIX or an open product BUG remains: `state.py round --task <TASK>` (exit 3 past the
limit) → dispatch the owning `dev` units with only those finding ids → re-integrate → re-test affected lenses →
delta review of the new SHA. Still open after round 2 → stop and give the owner options (another round with a
changed approach, re-plan that module, accept the risk, stop).

## Only reasons to talk to the owner after `approve`

A role returns `BLOCKED` because the next step needs an A3 action not approved in S2, any A4, risks data loss,
or would contradict the agreed plan (the plan is wrong or impossible). Then ask **one** focused question,
re-open only that module (`answer --module <unit>`), and continue. Everything else — small gaps, naming,
the simplest way to do an agreed thing — the roles decide and list under `Deviations:`.

## S8 — Finish (you)

Merge the units' `pr-body-<unit>.md` into `.aizen/runs/<TASK>/reports/pr-body.md`. Risk module that ships →
add the release/rollback packet (`assets/infra/release-packet.md`). One summary: what changed per module, checks with
numbers, verdict, open risks, `Deviations:`, and one copy-paste block:

```bash
git push -u origin <branch>
gh pr create --draft --base <target> --head <branch> --title "<title>" --body-file .aizen/runs/<TASK>/reports/pr-body.md
```

Collect `L-nn` lessons into `.aizen/knowledge/lessons.md`. A lesson about the skill itself (a step, brief, script or rule
that was wrong or missing) also goes to the skill feedback log: `feedback.py log --skill aizen-build …`
(`aizen-skill-creator/scripts/authoring/feedback.py`, see the repo's `continuous-improvement` rule). Record in
`.aizen/knowledge/` what this task changed: new `D-nn` in `decisions.md`, the module's design/API/data docs, a
flow in `system/flows.md` — `.aizen/PROJECT.md` is compiled from them. Then `guard.py done --run <TASK>`
(aizen-core): it checks the contract and marks the run done, or prints what is still open.

## Checks between steps

| Check | If it fails |
|---|---|
| every module confirmed and `approve` recorded before any dev/tester | back to S2 |
| unit write sets disjoint in one wave | run them in sequence |
| report claims match files/SHA/tests | finding; re-dispatch |
| reviewer did not author the code | re-dispatch to a fresh reviewer |
| backup taken before any migration/data change | stop the unit |
| nothing pushed by an agent | push only in the final block |
