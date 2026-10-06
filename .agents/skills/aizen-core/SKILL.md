---
name: aizen-core
description: Shared core of the Aizen suite (v25) — authority levels A0–A4, evidence labels, decisions and options, git and local-only hand-off, code quality (least code, the reuse ladder), numbers and projections, workspace layout, the quality gate (check.py), the code map (graph.py) and capacity projections. Loaded by every Aizen skill through its brief or its "Read first" line; not a standalone skill, do not trigger it directly.
---

# Aizen core — the rules every Aizen skill shares (v25)

One copy of the rules that used to be repeated in every skill. Entry skills (`aizen-build`, `aizen-init`, …)
and knowledge packs point here instead of restating them.

**Read first:** `references/core/rules.md` — authority, questions, lanes, code, git, evidence, output.

## What lives here

| Need | Read / run |
|---|---|
| who may do what (A0–A4), when to ask, `BLOCKED` / `HANDOFF` | `references/core/rules.md` |
| options, recommendations, research before proposing | `references/core/decisions.md` |
| least code, the reuse ladder, size signals, `ponytail:` debt markers | `references/core/code-quality.md` |
| comments, functions, naming — language-independent style | `references/core/code-style.md` |
| evidence labels, report shape, numbers with sources | `references/core/evidence.md`, `references/core/numbers.md` |
| challenging an upstream artifact | `references/core/challenge.md` |
| branches, backups, rollback; local-only hand-off and PR text | `references/core/git.md`, `references/core/git-handoff.md` |
| where files live (`.aizen/`), source priority, vendored knowledge | `references/core/workspace.md` |
| MCP tools (context7, sequentialthinking) | `references/core/mcp.md` |
| code map: who calls what, blast radius | `references/core/code-map.md` → `scripts/core/graph.py` |
| quality gate: lint, types, build, tests, secrets, deps → evidence JSON | `scripts/core/check.py` |
| run contract: sheet, rules, verifier, hooks, backlog — the gate that decides done | `scripts/core/guard.py` · `references/core/verifier.md` · `assets/core/contract.default.json` |
| the project map `.aizen/PROJECT.md` (one file, table of contents) | `scripts/core/project.py` · `references/core/workspace.md` |
| capacity, growth, contention projections | `scripts/core/capacity.py` |
| templates | `assets/core/pr-draft-template.md`, `assets/core/evidence-record.json` |

## Working principles — Karpathy's four, and where Aizen enforces each

The behavioural guidelines from [andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)
(MIT, vendored with worked examples in `references/core/vendor/karpathy-guidelines/`). Aizen states each one in its
own rules so it is checked, not just recommended:

| Principle | In Aizen | Checked by |
|---|---|---|
| **Think before coding** — state assumptions, show interpretations, push back with a simpler option, stop when unclear | plan time only: every question in the plan with options and a default (`references/core/rules.md` Questions, `references/core/decisions.md`); the plan's "Simpler option" line; facts are measured, labelled `[verified]/[inferred]/[unverified]` | the owner confirms part by part; `state.py approve` refuses unconfirmed modules |
| **Simplicity first** — minimum code, nothing speculative, no single-use abstractions, no handling of impossible cases | `references/core/code-quality.md` §1: reuse ladder, items 5–5b, the "senior engineer / 200 → 50" question | reviewer simplicity check (`references/review/code.md` axis 7) |
| **Surgical changes** — touch only what you must, match the style, clean up only your own orphans, mention other dead code | `references/core/code-quality.md` §1 items 1, 3 and "every changed line traces to the request"; `references/dev/out-of-scope.md` | reviewer: lines tracing to no id, churn, deleted or "improved" pre-existing code |
| **Goal-driven execution** — turn the task into checks, test first, `step → verify` | each plan module carries its Tests and Done; `dev` makes them runnable before coding (aizen-build, dev role, step 3); `check.py` evidence | tester and reviewer judge against the plan at a pinned SHA |

Trade-off, as upstream says: the rigor is for non-trivial work. A typo fix or an obvious one-liner still gets a
smallest diff and a check, not a ceremony — size changes the plan, not the principles.

## Paths

Every Aizen path `references/<topic>/…`, `assets/<topic>/…` or `scripts/<topic>/…` belongs to the skill whose
`manifest.json` lists `<topic>` under `topics`. This pack owns `core`. Run scripts by absolute path:
`uv run "<CORE_DIR>/scripts/core/check.py" …` (`<CORE_DIR>` = this skill's folder; a brief prints it).
