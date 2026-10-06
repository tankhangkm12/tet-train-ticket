---
name: aizen-tech-learning
description: "Research a technology in depth for one concrete workload - trace one operation from the application layer down through runtime, OS/kernel, network and hardware to explain the algorithm and mechanism that make it efficient there, draw Mermaid architecture diagrams linked by component IDs, compare alternatives architecture-to-architecture, then write a checked markdown note and publish it as a tree page in Notion. Use when the user wants to learn, research, deep-dive or evaluate a technology, framework, database or tool, or asks why X is fast or how X compares to Y (nghiên cứu công nghệ, học sâu, tìm hiểu bản chất, vì sao X nhanh, so sánh kiến trúc X và Y, ghi vào Notion). Not for: designing a schema, writing or reviewing code, or building CI/CD (all aizen-build), or turning a video into a skill (aizen-video-to-skill)."
---

# aizen-tech-learning — understand why a technology wins, layer by layer (v4)

You explain **the mechanism**, not the brochure: follow one real operation of the user's workload down the stack,
show where the time and copies go, and compare alternatives on the same path. The note is a tree: thesis → a
component map (IDs `C1…Cn`) → one branch per layer → core algorithm → comparison, all linked by those IDs.

**Read first:** `rules/research.md`, `references/core/mcp.md` (aizen-core). Use context7 for library docs when available.


## Run contract (enforced by the guard)

`<CORE_DIR>` = the aizen-core folder next to this skill. Step 0 starts the run: `uv run "<CORE_DIR>/scripts/core/guard.py" start --skill aizen-tech-learning --goal "<technology> for <workload>" --output <note path>`; after the intake answers, `uv run "<CORE_DIR>/scripts/core/guard.py" go --run <RUN> --text "<the owner's answers>"`. Writing the note before `go` is refused.
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

## Workflow

0. **Intake (one round, then stop and wait).** Ask only what is missing, each with your proposal:
   - technology and version (propose the latest stable);
   - **the reference workload** — one sentence the whole note hangs on, e.g. "cache, 100k GET/s, 1 KB values,
     1 node" (propose the most common one for this technology);
   - alternatives to compare (propose 2–3 that solve the same workload differently);
   - Notion parent page, and the markdown path (default `./tech-tree/<technology>.md`).
1. **Sources.** Collect the official docs, the source repo at the version's tag, the design paper or talk.
   Locate in the source the files that implement the hot path of the operation — you will link them.
2. **Thesis** (3 lines): the problem before it, the one or two design choices that win this workload (C-IDs),
   the price paid.
3. **Component map.** Table of `C1…Cn` (component · data structure/state · thread/process) and a mermaid
   `flowchart` whose edges say what flows. Every later section refers to these IDs — that is what links the
   architecture together. `references/diagram-guide.md`.
4. **Descend the layers** L1 application/API → L2 runtime/engine → L3 OS/kernel → L4 network → L5 hardware, for
   the one operation. Per layer: a `sequenceDiagram`, **Why it is efficient here** (the mechanism and its
   counted cost: copies, syscalls, round-trips, O(…), locks), **Observe** (a command that shows it, e.g.
   `strace -c`, `perf`, `ss -ti`) and a source link. A layer that does not matter gets one line
   `Not relevant: <reason>` — never skip silently. What to look for: `references/layer-guide.md`.
5. **Core algorithm.** The key structure or protocol (event loop, LSM-tree, B+tree, Raft, …): steps,
   invariants, complexity, and the **breaking point** — the workload that makes it slow and why.
6. **Compare by architecture.** Each alternative runs the same operation through the same layers, with its own
   diagram; a table per layer with mechanism + cost per cell; the verdict as "choose X when <condition>".
   `references/compare-method.md`.
7. **In practice (short).** Quick start, the production settings that tune the mechanisms above (say which
   C-ID/layer each one affects), SDKs; AI agent / MCP integration only when it exists.
8. **Write and check.** Fill `references/tree-template.md` in the user's language into the markdown file, then
   `uv run "<SKILL_DIR>/scripts/check_tree.py" <file>` (add `--min-alternatives 1` when the user named only one
   alternative). Fix until PASS.
9. **Publish to Notion.** `uv run "<SKILL_DIR>/scripts/to_notion.py" <file>` → `<file>.notion.md` + the title
   (the `#` heading becomes the page title; tables become Notion `<table>`; URLs become links; markup
   characters are escaped; mermaid stays a `mermaid` code block, which Notion renders). Then `notion-search`
   for that title under the parent: found → `notion-update-page`, else `notion-create-pages` with the
   converted file as `content`, parent = the page the user named. Fetch the page once to confirm tables and
   diagrams rendered. Notion missing or failing → keep the markdown file and tell the user once.
10. **Report:** the file path and Notion link, the thesis in 3 lines, layers marked not relevant, and every
    claim left as `not found`, `[projected]` or `[unverified]`.

## Quality bar

- Depth means a mechanism with a cost, linked to source code — not more adjectives or more sections.
- One operation, followed all the way down, beats a survey of every feature.
- If the reader cannot say after reading why it is fast **in this workload** and when it stops being fast, the
  note is not done.

## Knowledge

| Need | Read |
|---|---|
| what to look for per layer, common mechanisms, observe commands | `references/layer-guide.md` |
| comparison method and table | `references/compare-method.md` |
| mermaid conventions that render in Notion | `references/diagram-guide.md` |
| note skeleton (the checker keys on its headings) | `references/tree-template.md` |
| source and publishing rules | `rules/research.md` |
