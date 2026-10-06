---
name: aizen-skill-creator
description: "Create a new Aizen skill or improve an existing one to the Aizen standard (v4) - interview, design note, scaffold SKILL.md + manifest (topics, requires), link shared rules from aizen-core instead of copying them, register README and docs (usage guide + prompt template), evaluate against a baseline with aizen-skill-eval, then npm test, sync and commit. Also logs and fixes skill feedback. Use when the user wants to create, write, edit, improve, benchmark or fix a skill in Aizen-Skills (tạo skill, viết skill, sửa skill, cải thiện skill). Not for: copying a skill or knowledge from GitHub or another folder (aizen-skill-importer), evaluating a skill without changing it (aizen-skill-eval), or using an existing skill."
---

# aizen-skill-creator — build Aizen skills that pass the standard (v4)

You create and improve skills **inside the Aizen-Skills repo** so that every skill has one shape, links shared
knowledge instead of copying it, is documented for the user, and passes `npm test`.

**Read first:** `references/authoring/rules.md`, `references/core/rules.md` (aizen-core), then the standard
`<REPO>/docs/aizen-skill-standard.md` (`<REPO>` = the Aizen-Skills checkout; `scripts/authoring/new_skill.py`
finds it, or ask the user for the path).


## Run contract (enforced by the guard)

`<CORE_DIR>` = the aizen-core folder next to this skill. Start: `uv run "<CORE_DIR>/scripts/core/guard.py" start --skill aizen-skill-creator --run <skill-name> --goal "…"` (the run id is the new skill's name); the confirmed design note goes to `.aizen/runs/<RUN>/work/design-note.md`, then `uv run "<CORE_DIR>/scripts/core/guard.py" go --run <RUN> --text "<the owner's ok>"`.
- Fill `.aizen/runs/<RUN>/sheet.md` as you go: tick a step only with evidence the guard can check —
  `file:<path>` · `cmd:<the command you ran>` · `out:"<a line it printed>"` · `sha:<commit>` · `url:<source cited in the output>`.
- The Stop hook runs the contract (`manifest.json` → `contract`): open items → you continue with the exact list.
  `uv run "<CORE_DIR>/scripts/core/guard.py" check --run <RUN>` shows it any time. A step that truly does not apply:
  `uv run "<CORE_DIR>/scripts/core/guard.py" waive --run <RUN> --step <id> --reason "…" --evidence <file | real output>`.
- When everything deterministic passes, dispatch a **fresh** verifier (another model if you can) with
  `references/core/verifier.md` + the output of `uv run "<CORE_DIR>/scripts/core/guard.py" verify-brief --run <RUN>`. It writes `verdict.json`
  itself; ≥ 80% of the expectations, each pass citing `path:line`, or you fix and dispatch it again.
- Never write `run.json`, the ledger, waivers or evidence yourself, and never say "done" — the guard marks the run
  done and archives it.

## Workflow — new skill

1. **Interview (one round, then stop and wait).** Ask only what you cannot read yourself, each with a proposed
   answer: what the skill lets an agent do · 3 real prompts that must trigger it · prompts that must not (and
   which existing skill owns them — read every `skills/*/SKILL.md` description first) · the exact output · what
   is deterministic enough for a script · what needs the user's confirmation. Propose the name (`aizen-<what>`).
2. **Placement (SOLID).** Is this a new **entry** (a workflow the user triggers) or knowledge for an existing
   **pack** (a topic)? New knowledge in an existing area goes into that pack's topic folder, not a new skill.
   Anything already in `aizen-core` (authority, evidence, git, code quality, MCP) is linked, never repeated.
3. **Design note (confirm before writing).** ≤ 15 lines: name, kind, topics, requires, description, workflow
   steps, files, eval prompts. Wait for "ok".
4. **Scaffold.** `uv run "<SKILL_DIR>/scripts/authoring/new_skill.py" <name> --description "<…>" --title "<…>"` —
   creates only `SKILL.md` + `manifest.json`; never overwrites an existing skill.
5. **Write the skill** to the standard: `SKILL.md` lean (≤ ~150 lines) with imperative steps; long knowledge in
   `references/` with "when to read"; repeatable logic in `scripts/` (stdlib, `--help`, `--selfcheck`); hard limits
   in `rules/`. Create a folder only when it has a file.
6. **Register the docs** — the rows `new_skill.py` printed: `README.md` skill table, `docs/huong-dan-su-dung.md`
   §2 and §4, a `/<name>` prompt in `docs/prompt-mau.md`. A script with `--selfcheck` → one line in
   `tests/check-scripts.js`.
7. **Evaluate** with `aizen-skill-eval` when the skill drives judgment or multi-step work; a pure reference
   pack may skip it — say so.
8. **Finish:** `npm test` green → `node bin/cli.js sync` → `git add <the files you changed>` →
   `git commit -m "feat(<name>): …"`. Push only when the user says so for this push; else print the command.
   Report: files created, test result, eval numbers, `Deviations:` from the design note.

## Workflow — improve an existing skill

1. Read the whole skill, the user's complaint or goal, and its open feedback
   (`uv run "<SKILL_DIR>/scripts/authoring/feedback.py" list --skill <name> --open`); reproduce the weakness with one prompt.
2. Copy the current version to `<REPO>/.aizen/cache/import/<name>/baseline/` (never inside `skills/`).
3. Propose the change as a short diff summary (files, what changes, why) → wait for "ok".
4. Edit; bump `manifest.json` version (patch / minor / major) and any `(vN)` in headings to match; update the
   docs rows if triggers or usage changed.
5. Add one eval case per fixed problem (the logged `prompt`) and run the A/B of `aizen-skill-eval`
   (baseline vs with_skill), then step 8 above (`fix(<name>): …` or `feat(<name>): …`).
6. Mark the fixed entries: `feedback.py resolve --skill <name> --id <n> --commit <sha>`.

## Writing well

- `description` decides triggering: what · "Use when …" (English + Vietnamese keywords) · "Not for: …" naming
  the skills that own the near-misses.
- Explain why a step exists instead of shouting MUST; give one input → output example per non-obvious step.
- Every backtick path and markdown link must resolve — `npm test` fails otherwise. `references|assets|scripts/<topic>/…`
  resolves to the skill whose manifest lists the topic.
- Bundle what every run would rewrite (parsers, validators, API calls) into `scripts/`.

## Knowledge

| Need | Read |
|---|---|
| structure, manifest, docs rows, git rules | `<REPO>/docs/aizen-skill-standard.md` |
| rules for authoring and importing | `references/authoring/rules.md` |
| eval set, runs, grading, benchmark | `references/eval/schemas.md`, `references/eval/grader.md` (aizen-skill-eval) |
| skill feedback log (`log` / `list` / `resolve`) | `scripts/authoring/feedback.py`, `<CORE_DIR>/rules/continuous-improvement.md` (aizen-core) |
| skeleton | `assets/authoring/skill-template.md` |
