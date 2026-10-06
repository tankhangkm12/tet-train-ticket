# Graphify review (step 9)

Read at step 9. Tool: <https://github.com/Graphify-Labs/graphify> (Python package `graphifyy`), driven by the
installed `graphify` skill.

## Run

1. Check the tool: `graphify --help` (or the `graphify` skill). Missing → print `pip install graphifyy` and ask
   before installing.
2. From `<P>` run the graphify skill on the source folder (e.g. `/graphify src --no-viz` or with HTML for the
   user). It writes `graphify-out/` (git-ignored).
3. Review using `graphify-out/GRAPH_REPORT.md` and queries such as
   `graphify query "which modules import the pino/pg/redis library directly?"` and
   `graphify path "HealthController" "Database"`.
4. When the review is done move the output into the agent workspace:
   `mv graphify-out .aizen/runs/init/graphify/graphify-out` (PowerShell: `Move-Item graphify-out .aizen/runs/init/graphify/`).

## Review table (copy into `.aizen/runs/init/reports/step-9.md`)

| Check | Expected (plan/docs) | Seen in graph | OK? |
|---|---|---|---|
| Modules/layers | the layout in plan | communities / top-level nodes | |
| External libs only in `infrastructure/` | adapters only | importers of each lib | |
| Business code depends on interfaces | core interfaces | edges module → core | |
| One composition root | main/app only | who constructs implementations | |
| Request-id → logger path | middleware → context → logger | path query | |
| Auth guard on protected routes | per plan | edges route → guard | |
| Every planned infra has a client + ready check | plan infra list | nodes per dependency | |
| No orphan / unused files | none | isolated nodes | |
| Naming/conventions from docs | docs | node names | |

Gap found → fix on `feature/init-9-graphify-fixes`, re-run graphify (`--update`), update the table. Show the table
at the checkpoint.
