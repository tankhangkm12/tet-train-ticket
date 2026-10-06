---
name: aizen-skill-eval
description: "Evaluate an agent skill against a baseline (v3) - trigger tests (explicit, implicit, guidance, negative controls), runs with and without the skill or old vs new version by independent runners, LLM-as-a-judge grading on Outcome, Process, Style and Efficiency, an A/B comparator for customizations, and benchmark aggregation. Use when validating, benchmarking or regression-testing a skill, building an eval set, or proving a change made a skill better (đánh giá skill, test skill, benchmark skill, so sánh skill cũ và mới). Not for: writing or changing a skill (aizen-skill-creator) or importing one (aizen-skill-importer) — those call this skill for their eval step."
---

# aizen-skill-eval — prove a skill helps, with numbers (v3)

The one place for skill evaluation in Aizen. `aizen-skill-creator` and `aizen-skill-importer` use these roles
and scripts for their eval / A/B steps; you can also run it alone on any skill.

**Read first:** `references/core/rules.md` (aizen-core); the eval JSON formats in `references/eval/schemas.md`.


## Run contract (enforced by the guard)

`<CORE_DIR>` = the aizen-core folder next to this skill. Start: `uv run "<CORE_DIR>/scripts/core/guard.py" start --skill aizen-skill-eval --goal "evaluate <skill>"`; after the owner confirms the success criteria, `uv run "<CORE_DIR>/scripts/core/guard.py" go --run <RUN> --text "…"`. Graders follow `references/core/verifier.md` (aizen-core) — the same judge the guard uses.
- Fill `.aizen/runs/<RUN>/sheet.md` as you go: tick a step only with evidence the guard can check —
  `file:<path>` · `cmd:<the command you ran>` · `out:"<a line it printed>"` · `sha:<commit>` · `url:<source cited in the output>`.
- The Stop hook runs the contract (`manifest.json` → `contract`): open items → you continue with the exact list.
  `uv run "<CORE_DIR>/scripts/core/guard.py" check --run <RUN>` shows it any time. A step that truly does not apply:
  `uv run "<CORE_DIR>/scripts/core/guard.py" waive --run <RUN> --step <id> --reason "…" --evidence <file | real output>`.
- Never write `run.json`, the ledger, waivers or evidence yourself, and never say "done" — the guard marks the run
  done and archives it.

## Workflow

1. **Success criteria.** For the skill under test write what must come out (Outcome), which steps or tools must
   be used in which order (Process), the format and location rules (Style), and a step or token budget
   (Efficiency). Confirm them with the user.
2. **Eval set** → `skills/<name>/evals/evals.json` (`references/eval/schemas.md`), at least one case per category:
   explicit trigger (names the skill), implicit trigger (describes the goal), guidance request, and a **negative
   control** that shares keywords but must not trigger it (name the skill that owns it). Each case: `id`,
   `prompt`, `should_trigger`, `expected_output`, checkable `expectations`.
3. **Runs.** Workspace `<REPO>/.aizen/cache/eval/<name>/iteration-<N>/eval-<id>/{with_skill,baseline}/run-<k>/`. Dispatch
   all runs in one message (Claude Code: Agent tool, `general-purpose`; Antigravity: `invoke_subagent`), each with
   `references/eval/runner.md` and its `mode`. No sub-agent tool → run them yourself in turn and label the
   result `[not independent]`.
4. **Grade** each run with `references/eval/grader.md` → `grading.json`. Customization A/B (importer, improve):
   also `references/eval/comparator.md` with the agreed change list → PASS / FAIL per item.
5. **Aggregate**: `uv run "<SKILL_DIR>/scripts/eval/aggregate_benchmark.py" <iteration dir> --skill-name <name>`
   → `review.md`: pass rate with vs without, time and tokens, failing expectations.
6. **Diagnose and report**: trigger misses → the `description`; process/style misses → concrete examples or
   fewer degrees of freedom in the skill; waste → say what not to do. Every new failure becomes an eval case,
   so the set grows into a regression suite.

## Gotchas

- One subjective prompt is testing by vibe — use the set.
- Without negative controls a skill that triggers on everything looks perfect.
- Capable models route around broken instructions: read the transcripts for retries and detours, not only
  the final output.

## Knowledge

| Need | Read |
|---|---|
| evals.json, grading.json, benchmark formats | `references/eval/schemas.md` |
| running one version | `references/eval/runner.md` |
| grading a run (expectations, evidence) | `references/eval/grader.md` |
| A/B of a customization | `references/eval/comparator.md` |
| aggregation | `scripts/eval/aggregate_benchmark.py` |

`references/eval/grader.md`, `references/eval/schemas.md` and the aggregation script come from Anthropic's
skill-creator (Apache 2.0, `LICENSE.txt` in this folder).
