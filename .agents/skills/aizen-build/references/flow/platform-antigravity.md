# Running the owner on Antigravity (v25)

## Dispatch

- Define each role once per session: `define_subagent` with name `aizen-<role>` (planner, dev, tester,
  reviewer, devops) and the content of `agents/<role>.md` + `references/core/rules.md` as its instructions.
- One role instance = one `invoke_subagent` call; prompt = the full output of `uv run "<SKILL_DIR>/scripts/flow/state.py" brief …`,
  header line first, nothing before it.
- A wave = every `invoke_subagent` of that wave **in one turn**; collect with `manage_subagents` /
  `send_message`, then read the report files (files are the fact).
- Never invoke yourself or an agent that is not an Aizen role.

## Models

Main session and `planner`/`reviewer`/`devops` on `pro`; `dev`/`tester` may run on `flash`. On `flash`
for the planner, say once that planning is weaker. The reviewer should not run on the same model as the devs
when a choice exists.

## Confirming the plan

Confirm the plan part by part with `ask_question` (scope, each module, delivery; recommended option first).
Record each answer with `state.py answer --module <part>`, then `state.py approve`.

## Dispatch failed

Subagent not found, not allowed, any error → stop, report the exact error text, ask the owner to check the
Antigravity version and the agent definitions. Never retry under another agent name.

## MCP tools

The main session may use read-only MCP tools to understand the task. Cluster or cloud **changes** go through
`devops` with an A3 quote relayed to the owner.
