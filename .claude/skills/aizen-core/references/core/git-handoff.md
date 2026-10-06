# Git hand-off — local-only, rebase, PR text (v25)

Open at the hand-off step. Branches, checkpoints, backup and rollback: `git.md`.

## 1. Local-only: nothing leaves the machine from an agent

Everything an agent does stays local — commits, task branches, `.aizen/`, worktrees. `.aizen/` and `.aizen/worktrees/`
are listed in `.git/info/exclude` and never committed.

A4 for agents (never): `git push` in any form · creating/deleting remote branches or tags ·
opening, editing, approving, merging a PR/MR · review comments · releases · changing remotes, push URLs or
`pushInsteadOf` · `git add -f` of an excluded path.

Allowed: `git fetch` (A0) · read-only `gh pr view --comments` / `gh api` GET of a PR (A0) · `git pull` /
`git merge origin/…` (A3 — changes the working tree).

What the agent does instead — in the report, as a copy-paste block for the owner, with **absolute paths** (the owner may
run it from any folder; `gh` must run inside the project):
```
git push -u origin <task-branch>
cd "<project>" && gh pr create --draft --base <target> --head <task-branch> --title "<title>" --body-file "<workspace>/.aizen/runs/<TASK>/reports/pr-body.md"
```
Before handing over, confirm no `.aizen/` file is staged or committed. Repo PR templates and branch/commit
conventions (`CONTRIBUTING.md`, `.github/pull_request_template.md`) win over these defaults.

## 2. Rebase before a Draft PR

`git fetch` → `git branch backup/<TASK>-<n>` → `git rebase origin/<target>`. Per conflict read both
sides and the commit that caused the other side; keep both changes by default; never take ours/theirs
for a whole file blindly. Semantic conflict (both sides change the same behaviour, or the other side
contradicts the docs) → `git rebase --abort` and ask. Lockfiles: take the target's, regenerate.
Migration numbering clash: renumber **yours**, never a merged one. Re-run the quality gate after.

## 3. Draft PR content

Write the full description from `assets/core/pr-draft-template.md` (the repo's own PR template wins) to
`.aizen/runs/<TASK>/reports/pr-body.md`, including the Rollback block. Hand the owner the push and
`gh pr create --draft … --body-file …` / `glab mr create --draft …` commands (§1); the owner runs them. No reviewers
unless the owner names them.

Review feedback (the owner pastes or points to it; in the `team` flow the agent may read it with read-only
`gh pr view --comments` / `gh api` GET): one new commit per group of comments; never reply on the host;
feedback that contradicts the docs is asked about, not applied. Do not start a unit that depends on
this PR until the owner says it is merged or the host shows it merged.
