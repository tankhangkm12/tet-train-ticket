# Git flow, checkpoints, backup and rollback (v25)

Every change is made so that the owner can undo it at any moment. Git is the backup for everything it
tracks; `.aizen/backups/` is the backup for what it does not.

## 1. Branch model

`git.model` in `.aizen/config/conventions.md`: `auto` (default) · `gitflow` · `github`. The repository's own
convention (CONTRIBUTING, `git branch -r`, history) wins; note it once in the report.

| Model | Long-lived | Task branches from | Merge target |
|---|---|---|---|
| **gitflow** (`auto` picks it when `develop` exists, or the repo has no convention yet) | `main` (released), `develop` (integration) | `develop`; `hotfix/*` from `main`; `release/*` from `develop` | `develop` (hotfix → `main` and `develop`) |
| **github** (`auto` picks it when there is only `main`/`master`) | `main` | `main` | `main` |

Task branch names — `<type>/<TASK>-<nn>-<desc>`:

| Type | For |
|---|---|
| `feature/` | new behaviour (any unit: backend, frontend, db, infra) |
| `bugfix/` · `hotfix/` | a fix · an urgent fix to released code (gitflow: from `main`) |
| `refactor/` · `test/` · `docs/` · `ci/` · `infra/` · `chore/` | as named |
| `int/<TASK>` | local only: merge of a parallel wave's branches for combined tests (`parallel.md` §4) |
| `backup/<TASK>-<n>` | local only: a named checkpoint before a risky rewrite (§3) |

Parallel writers on one task use one branch each, per unit: `feature/SHOP-42-order-api`,
`feature/SHOP-42-payment-api`, `feature/SHOP-42-web` (`state.py brief` derives `feature/<TASK>-<unit>`).

A team convention (branch pattern such as `feature/{ticket}-{slug}`, commit subject format) in `CONTRIBUTING.md` or
`.aizen/config/conventions.md` replaces the defaults here where they differ.

Never create `develop`, `release/*` or any branch on the remote (A4 — the owner creates remote branches). Creating `develop`
locally for a repo that has none is a decision — ask once, record it as `D-nn`.

## 2. Before the first edit — every task

```
git status --porcelain            # unrelated changes? → ask; never stash or commit the owner's work silently
git fetch                         # A0
git switch -c <task-branch> origin/<base>     # or from local base if there is no remote
git rev-parse HEAD                # record: start SHA  → report "Rollback" section
```

Never edit on a protected branch, on a detached HEAD or outside a git repository. Worktrees for parallel roles are created the same way:
`git worktree add .aizen/worktrees/<TASK>-<unit> -b feature/<TASK>-<unit> <base>`.

## 3. Checkpoints during the work

- **Commit per step** — one logical change, builds, passes its focused test:
  ```
  <type>(<scope>): <imperative summary> [<TASK>]

  <why; requirement IDs / doc sections>
  ```
  Types: `feat fix refactor perf test docs chore build ci style`. Never commit secrets, `.env`, build
  output, dumps or commented-out code. Never `--no-verify` — a failing hook is fixed or reported.
- **Before a risky rewrite** (large refactor, rebase, generated-code regeneration, mass rename): create
  `git branch backup/<TASK>-<n>` at the current commit. Local, instant, deletable later (A3 if unpushed
  work would be lost).
- After the owner has looked at a PR, add commits; do not rewrite reviewed ones.
- Committing is local and reversible: A2. If the plan says the owner commits themselves, leave changes
  uncommitted and list them.

## 4. Backup of what git does not hold

Before changing anything git cannot restore — take the backup, check it exists and is non-empty, record
it, then proceed:

| Thing | Backup | Restore command in the report |
|---|---|---|
| local database (migration, data fix, seed reset) | `pg_dump -Fc` / `mysqldump --single-transaction` via `docker compose exec` into `.aizen/backups/<TASK>/<db>-<time>.dump` | `pg_restore --clean -d <db> <file>` / `mysql <db> < <file>` |
| a git-ignored or generated file you will overwrite (local config, fixtures) | copy to `.aizen/backups/<TASK>/` | `cp` back |
| Penpot/Figma page you will change heavily | export the page/board first into `.aizen/backups/<TASK>/` | re-import or redraw from export |

`.aizen/backups/` must be git-ignored (dumps can hold personal data); check `.gitignore` and ask the owner
to add it if missing. Shared/staging data is backed up only by the owner or devops through an approved A3
action; production is the owner's (A4).

## 5. Rollback — always written, never improvised

Every report ends its evidence with:

```
Rollback: branch <task-branch> from <base>@<start-sha>; commits <sha1..shaN>
  undo all, keep history:   git revert --no-edit <start-sha>..HEAD
  discard the branch (A3):  git switch <base> && git branch -D <task-branch>
  back to a checkpoint (A3): git reset --hard <sha>
  data:                     <restore command from §4, or "none touched">
```

Running a rollback that discards work is A3; reverting a merged change on a protected branch is A4
(the owner merges the revert).

Handing work over (local-only, rebase, PR text, commands for the owner): `git-handoff.md`.
