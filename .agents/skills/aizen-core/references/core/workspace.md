# Workspace — where things live (v25)

Everything an Aizen agent writes to do its work lives under `.aizen/` at the workspace root (the project root
unless `CLAUDE.md`/`AGENTS.md` names another). The product itself (code, the notes a skill produces) lives where
the owner wants it. `.aizen/` is local-only (`.git/info/exclude`, never staged) unless the owner sets
`"share_knowledge": true` in `config/guard.json` — then `knowledge/` and `PROJECT.md` can be committed.

## 1. Layout

```
.aizen/
├── PROJECT.md              👁 the project map — the one file the owner reads (compiled by scripts/core/project.py)
├── backlog.md              ✍ work to come: BL-nn · skill · status · after · run (agents propose, the owner approves)
├── config/
│   ├── guard.json          require_task · share_knowledge
│   └── conventions.md      one page: naming, patterns, commands — read before the first edit
├── knowledge/              understanding the project — outlives every run
│   ├── system/             overview · requirements · architecture · flows · data · infrastructure · security · test-plan
│   ├── modules/<module>/   <module>-design.md (LLD) · <module>-database.md · <module>-api.md + .yaml
│   ├── apps/<app>/         <app>-frontend.md · <app>-ui.md · design-tokens.json · ui-exports/
│   ├── decisions.md        D-nn decision log
│   └── lessons.md          L-nn lessons from past runs
├── runs/<RUN>/             one run of one skill — read state.md first when resuming
│   ├── run.json        🔒  skill, goal, status, backlog item, outputs, owner's decision, log
│   ├── state.md            the human view (aizen-build: written by scripts/flow/state.py)
│   ├── plan.md             the plan (aizen-build planner; any skill that plans)
│   ├── sheet.md        ✍  steps the agent ticks with checkable evidence + the guard's checks
│   ├── ledger.jsonl    🔒  every file write and command, with who did it (hooks)
│   ├── waivers.json    🔒  steps waived, with reason and hashed evidence
│   ├── evidence/       🔒  check.py results (<unit|main|int>.json) and rule results
│   ├── reports/            role reports: dev-<unit>.md · test[-<lens>].md · review[-redteam].md · pr-body[-<unit>].md
│   ├── verdict.json        the independent verifier's judgement
│   └── work/               intermediate files of the run
├── worktrees/<RUN>-<unit>/ git worktrees of parallel units
├── cache/                  re-creatable: eval/<skill>/ (benchmarks), import/<name>/baseline/, prepush.json
├── backups/<RUN>/          DB dumps and copies taken before a change (git.md §4)
└── archive/<RUN>/          runs that finished (moved here by the guard)
```

🔒 written only by the Aizen scripts and hooks (an agent edit is denied) · ✍ filled by the agent, checked by the
guard · 👁 read-only, compiled. `<RUN>` = the task id for aizen-build (`SHOP-42`), `<skill>-<yyyymmdd>-<slug>`
for the others. The graphify code map stays in `graphify-out/` at the root (the tool decides that path).

## Contract — how every run ends

Every entry skill declares a `contract` in its `manifest.json` (`docs/aizen-skill-standard.md`); the guard
(`scripts/core/guard.py`, run by the agent's Stop hook) holds the run to it: the sheet's evidence checks out,
the deterministic rules pass, an independent verifier passes the expectations. Only then is the run `done`.
Start: `guard.py start --skill <skill> --goal "…"` (aizen-build: `state.py init`). Owner needed:
`guard.py ask`, then `guard.py go` with their answer.

Microservices: `knowledge/services/<svc>/` holds `<svc>-overview.md`, `<svc>-api.md` + `.yaml`, `<svc>-database.md`,
`<svc>-infrastructure.md` and `modules/<module>/<module>-design.md`. Names are lower-kebab-case.

## 2. Logical names → paths (under `.aizen/knowledge/`)

| Logical name | Monolith | Microservices |
|---|---|---|
| system map · idea · requirements · architecture · security · test plan | `system/<name>.md` | same |
| module design (LLD) | `modules/<m>/<m>-design.md` | `services/<svc>/modules/<m>/<m>-design.md` |
| database doc | `modules/<m>/<m>-database.md` | `services/<svc>/<svc>-database.md` |
| API contract | `modules/<m>/<m>-api.md` + `.yaml` | `services/<svc>/<svc>-api.md` + `.yaml` |
| frontend architecture · UI design | `apps/<app>/<app>-frontend.md` · `<app>-ui.md` | same |
| infrastructure doc | `system/infrastructure.md` | `services/<svc>/<svc>-infrastructure.md` |

An existing repo with its own docs folder keeps it; record the mapping in `.aizen/config/conventions.md`.

## 3. Priority when sources conflict

```
The owner's direct instruction > docs > plan > repo conventions > these skills' defaults
```

Following the higher source is never silent: note the conflict in one line. A direct instruction that contradicts
docs on business logic, schema or a public contract → confirm once before acting.

Inside "these skills' defaults" there is a second order:

```
core rules (references/core/) > the pack's own method and guides > vendored upstream knowledge (…/vendor/…)
```

Vendored knowledge is best practice copied from the people who build the tool (React from Vercel, Redis from
Redis, Kafka from Confluent, …), pinned to a commit and listed in `vendor.lock.json` of the Aizen repo. It says
**how to do a thing right in that tool**; core rules decide **how much to build and who decides**. So a vendored
rule never overrides the authority levels, the questions-only-before-approve rule, least code, local-only git or
the owner's decisions: when a vendored guide says "ask the user first", "announce", "install X", "add an
abstraction" or "deploy", the core rule wins and the vendored step becomes a plan question or an A3 item. A
vendored rule that conflicts with a pack guide on substance → follow the pack guide, cite both in the report.

## 4. Traceability IDs

| Prefix | Meaning | Created by |
|---|---|---|
| `FR` `NFR` `BR` `AC` | requirements, rules, acceptance criteria | planner (discover) |
| `SCR` `CMP` | screen, frontend component | planner (design) or dev (ui), whoever first |
| `EP` · `THR` `CTL` | endpoint/event · threat, control | planner (design) |
| `TC` `BUG` | test case, bug | tester |
| `F` | review finding | reviewer |
| `D` | decision | whoever records it in `decisions.md` |
| `U` `X` `R` | unknown, contradiction, risk in as-built docs | planner (discover) |
| `L` | lesson | any role |

IDs are never renumbered once published; retire with `~~FR-07~~ removed D-12`.
