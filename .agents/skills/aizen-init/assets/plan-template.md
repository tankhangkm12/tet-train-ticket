# Plan — <project>

Repo: <url> · Docs: <paths> · Created: <YYYY-MM-DD> · Approved: no

## Decisions (from docs, or answered by the user)
| Topic | Decision | Source (doc §/user) |
|---|---|---|
| Language / framework | | |
| Architecture / layout | | |
| Infrastructure (db, cache, queue…) | | |
| Auth (authn + authz) | | |
| Logger | | |
| Conventions (naming, API style, errors) | | |
| Ports / versions | | |

## Open questions
- <none left before approval>

## Tasks
| # | Task | Owner | Depends on | Done criteria | Status |
|---|---|---|---|---|---|
| 2 | Skeleton + /health | dev-1 | 1 | /health 200 locally | todo |
| 3 | Dockerfile + compose | dev-1 | 2 | compose up, all healthy | todo |
| 4 | Env + central config | dev-1 | 3 | missing var stops startup | todo |
| 5 | Infra connections + /health/ready | dev-1 | 4 | fail-fast proven | todo |
| 6 | Adapters behind interfaces | dev-1 | 5 | no lib import outside infrastructure/ | todo |
| 7 | AOP, request-id, auth | dev-1 | 6 | id in logs, 401/403, tests pass | todo |
| 8 | README | dev-1 | 7 | all sections, all env vars | todo |
| 9 | Graphify review | reviewer | 8 | review table, gaps fixed | todo |
| 10 | Final review + handover | lead | 9 | gate 11 passes | todo |
