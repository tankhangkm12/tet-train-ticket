# Running the owner on Claude Code (v25)

## Dispatch

- One role instance = one **Agent** tool call. Prompt = the full output of
  `uv run "<SKILL_DIR>/scripts/flow/state.py" brief …` (header line first); it already names the absolute paths of
  `agents/<role>.md` and `references/core/rules.md`.
- `subagent_type`: `general-purpose` for every role — the planner writes its plan file, and the reviewer
  brief already says READ-ONLY. Never `Plan`/`Explore`: they cannot write their report.
- A wave = all Agent calls of that wave **in one message** so they run in parallel.
- Code writers get their own worktree. Either create it yourself (`git worktree add`) and name it in the brief,
  or pass `isolation: "worktree"` and let the harness create it — then read the branch name from the result.

## Models

| Role | Default | Why |
|---|---|---|
| planner | strongest (opus) | one plan drives every other dispatch; quality matters most here |
| dev | sonnet | the plan already decided the design; opus only for risk modules |
| tester | sonnet | |
| reviewer | a different model than the devs (opus when devs ran sonnet) | independence comes from a different context **and** model |
| devops | opus | blast radius |

The owner may override any of these when the owner confirms delivery.

## Confirming the plan

One **AskUserQuestion** call per part (scope, each module, delivery): the module's options first with the
recommended one labelled "(Recommended)", then its questions (≤ 4 per call; put the ≤ 15-line design summary in
the question text or in a message just before). Record each with `state.py answer --module <part>`, then
`state.py approve`.

## Dispatch failed

Agent tool error, missing skill path, permission denial → stop, show the exact error, and tell the owner what to
check. Do not silently do the role's work instead (a one-module task you chose to build yourself is the exception).
