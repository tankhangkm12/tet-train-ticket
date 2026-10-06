[aizen-brief TASK={{TASK}} ROLE={{ROLE}} KIND={{KIND}} UNIT={{UNIT}} STAGE={{STAGE}} LENS={{LENS}} ROUND={{ROUND}}]

Read `{{SKILL_DIR}}/agents/{{ROLE}}.md` and `{{CORE_DIR}}/references/core/rules.md` first and follow them.
Paths: `agents/` is under {{SKILL_DIR}}. Every `references/<topic>/…`, `assets/<topic>/…` and `scripts/<topic>/…`
path resolves through this table (Aizen packs installed next to each other):
{{PACKS}}
`.aizen/` is always {{ROOT}}/.aizen, also when you work in a worktree.

## Task
Goal: {{GOAL}}
Your part: {{PART}}
Done when: {{DONE}}

## Agreement
The owner confirmed the plan module by module: .aizen/runs/{{TASK}}/plan.md + .aizen/runs/{{TASK}}/state.md
(## Agreed, ## Approval). Once approved it is the contract: do not ask the owner anything — build exactly that.
Plan silent on a detail → take the simplest option that fits it and list it under `Deviations:`.
Only stop for: an A3 action not listed below, any A4, data loss, or a step that would break the agreed plan.

## Where
Project root: {{ROOT}}
Code workdir: {{WORKDIR}}  ·  Branch: {{BRANCH}} @ {{SHA}}
Write set (your lane): {{WRITE_SET}}
Runtime (yours alone): ports {{PORTS}} · compose project {{TASK}}-{{UNIT}} · DB {{DB}} · browser session {{TASK}}-{{UNIT}}

## Inputs
{{INPUTS}}

## Allowed A3 (approved with the plan)
{{A3}}

## Commands
Code map (ask before reading files): {{GRAPH}}
Optional tools: {{OPTIONAL}}
Quality gate: uv run "{{CORE_DIR}}/scripts/core/check.py" --task {{TASK}} --unit {{CHECK_UNIT}} --project "{{WORKDIR_CMD}}"

## Report
Full report: .aizen/runs/{{TASK}}/reports/{{REPORT}}  ·  Return ≤ 15 lines ending with `Deviations:`.
Write the report file yourself with your file tool — the guard records who wrote it and refuses a report the
coordinator wrote. Every finding and every area you judge PASS cites its evidence as `path:line` at the SHA you
worked on; the guard opens each citation and fails the report when the line does not exist.
