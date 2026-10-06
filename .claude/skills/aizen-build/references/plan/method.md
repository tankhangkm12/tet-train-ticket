# Planning — a plan the owner can confirm module by module (v25)

The plan is what the owner confirms part by part and what every role then follows without asking. Write it so
each module can be read, judged and approved on its own, and so a dev can build it without thinking twice.

## Steps

1. **Locate.** Read only the docs and code this change needs (code map first: `references/core/code-map.md`);
   `.aizen/runs/<TASK>/state.md` when resuming — `## Agreed` is settled, do not reopen it.
2. **Measure, never ask facts.** Paths, versions, config, current behaviour → read-only tools, labelled. An
   unverified assumption becomes a measurement module first. Only preferences and risk choices become
   questions, each with choices and a recommended default.
3. **Root cause first** for bugs: `[verified]` only when reproduced or the causing line was read at this SHA.
4. **Split into modules** (below) and write `.aizen/runs/<TASK>/plan.md`. Risk module → add the fields of
   `planning-method.md`.
5. **Decide the details now.** Anything a dev would otherwise have to think about — names, signatures, status
   codes, columns, file paths, edge cases, test cases — goes in the module. Open choices go to the owner as
   questions with a default; the dev never chooses between designs.
6. **Self-challenge**: is there a simpler plan? which module is most likely wrong? (`references/core/challenge.md`).
7. **Return** ≤ 15 lines: plan path, modules, questions per module.

## Plan shape

```text
# <TASK> — <goal>                                   Plan vN · Base: <branch> @ <sha>
## Scope
Goal: <one checkable sentence>
In: <…>   Out: <…>
Acceptance: AC-1 <given/when/then> · AC-2 …
Simpler option: <the simplest approach that would also work; why this plan is not simpler>

## Module <unit-id> — <name>          kind be|fe|db|ui (dev) or infra (devops) · after: <unit> | parallel
Does: <behaviour in 2–4 lines, which AC it covers>
Interface: <endpoint / function signatures / events / screen states — exact>
Data: <tables, columns, migrations, cache keys — exact; or none>
Files (write set): <globs>
Tests: <cases that prove it, incl. the failure cases>
Risk: <none | trigger + what could go wrong> (risk → planning-method.md fields)
Options: A (recommended) … · B … — only when there is a real choice
Questions: <preference/risk only, choices + default>

## Delivery
Order / waves: <unit, unit → unit>
A3 to pre-approve: <exact actions: installs, local DB, downloads — or none>
Checks: <commands>  ·  Backup: <what / none, why>  ·  Rollback: <how>
```

## Modules — how parallel work stays safe

- A module = one unit = one dev (or devops) with a **disjoint write set**. Shared hot files (router, DI module,
  lockfile, migration registry, i18n bundle) get one owner; others list the lines they need.
- Modules that share only **settled** seams (the contract/schema written in the plan) may run in one wave.
- Cannot be made disjoint → sequence them. Prefer fewer, larger modules: each costs a dispatch, a worktree, a merge.
- Detail: `references/flow/parallel.md`.

## Changes after approval

Facts changed (a module is impossible, a BUG has no owner, the owner asks for more) → show that module before →
after and why, re-confirm **only that module** (`state.py answer --module <unit>`), bump the plan version.
Never rewrite history: retired modules get `~~id~~ replaced by …`.
