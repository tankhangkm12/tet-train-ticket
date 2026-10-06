# Parallel work — units, isolation, integration, resuming (v25)

Independent units run at the same time; each runs its own checks; they meet in one integration step.

## 1. How many

The plan's chosen option sets the number of `dev` instances. Limits that still apply: the host (Claude Code runs
up to ~20 sub-agents at once), machine resources (each member needs its own ports, containers, DB), and any number
the owner set when confirming delivery. Every extra unit costs a dispatch, a worktree and a merge — prefer fewer, larger units.

## 2. When two writers may run at the same time — all three, or sequence them

1. **Seams settled** — contract version, schema, event shape, env var and port names are in the plan. A writer that
   needs to change a seam stops and reports; it never edits the other side's assumption.
2. **Disjoint files** — write sets compared path by path. Forgotten collisions: DI modules, routers, migration
   registries, lockfiles, i18n bundles, shared enums, error catalog, generated clients. A shared hot file gets **one**
   owner; others list the lines they need in their report.
3. **Isolation** — each code writer in its own worktree and branch
   (`git worktree add .aizen/worktrees/<TASK>-<unit> -b feature/<TASK>-<unit> <base>`). Two agents never share a checkout.

**Runtime isolation** — give every member its own:

| Resource | How |
|---|---|
| ports | block per member (`3000+100k`, `5432+k`) passed as env vars on the command, never written to `.env` |
| docker compose | `docker compose -p <TASK>-<unit>` |
| database / test DB / caches | `<db>_<unit>`, cache dir under its worktree |
| browser | its own Playwright session `-s=<TASK>-<unit>`; never `close-all` / `kill-all` |

Creating a worktree is A2; deleting one that holds unpushed work is A3.

## 3. Waves

A wave = members launched together because none can invalidate another: dependencies finished → write sets
compared → isolation assigned. **Launch every member of a wave in one message.** A wave of one is normal.
The next wave starts after a clean wave without asking the owner. A failed check is fixed by the owning unit; an
unapproved A3, an A4 or a plan that cannot work stops the flow (`BLOCKED`).

## 4. Integration

Separate branches passing their own tests do not prove combined behaviour.

1. `int/<TASK>` from the base; `git merge --no-ff` each unit branch in plan order; record every SHA (coordinator, git only).
2. Conflict → `git merge --abort`; a `dev` with `UNIT=int` resolves it from the docs, or hands each side back to its owner.
3. The tester runs against `int/<TASK>`; review and fix rounds run on the integrated SHA.
4. Failures go back to the unit that caused them, on its own branch; then re-integrate.

Merging into a shared branch is A4 — the owner does it.

## 5. Resuming and stopping

- `uv run "<SKILL_DIR>/scripts/flow/state.py" status --task <TASK>` and `state.md` first; check current SHAs and whether files changed.
- An action whose result is unknown is checked, never repeated.
- Never start a replacement writer while the old one might still be writing.
- Cleanup of worktrees and `int/*` branches is a separate step after the owner pushed or abandoned the work (A3 if
  anything unpushed would be lost).

## 6. Bounded effort

Two correction attempts for a persistent failure inside one run, then stop and report. Flaky test: ≤ 2 reruns, all
recorded. Fix loop across the task: ≤ 2 rounds.
