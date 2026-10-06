# <unit> — database

> Updated: <YYYY-MM-DD> · Owner: `dev` (db) (or `planner` (design) while `dev` (db) is off) · Input: `<module>-design.md` · Engine: <DBMS + version> · Schema: `<name>`

## 1. Conventions
| Item | Rule |
|---|---|
| Table naming | |
| Primary key | |
| Time columns | |
| Soft delete | |
| Money | |
| Enums | |

## 2. Relations
```
users 1 ----< orders 1 ----< order_items >---- 1 products
```
| Relation | Type | FK | On parent delete |
|---|---|---|---|

## 3. Tables
### 3.1 `<table>` — <one line>
| Column | Type | Null | Default | Constraint | Meaning |
|---|---|---|---|---|---|

| Key | Columns | Notes (implements LLD rule #) |
|---|---|---|
| PK | | |
| UNIQUE | | |
| FK | | ON DELETE … |
| CHECK | | |

## 4. Indexes
| Name | Table | Columns | Type | Query/screen served | LLD § |
|---|---|---|---|---|---|

## 5. Enums & data rules
### 5.1 `<enum>`
| Value | Meaning | Can move to |
|---|---|---|
### 5.2 Rules the schema cannot express
| Rule | Enforced where | Why not in DB |
|---|---|---|

## 6. Heavy queries
| # | Query | Frequency | Index used | Plan evidence (M-nn, data size) | Target |
|---|---|---|---|---|---|

## 7. Growth, partitioning & retention
| Table | Rows now / growth per month | Strategy (none · index only · partition · archive · summary table) | Partition key & interval | Pre-create job | Retention & how old data leaves |
|---|---|---|---|---|---|

## 8. Database-side code
| Object | Kind (procedure · function · trigger · job · view · materialized view) | Why in the DB, not the app | Migration | Test | Refresh / schedule |
|---|---|---|---|---|---|

## 9. Connections
| Consumer | Instances | Pool max per instance | Acquire timeout | Statement timeout | Lock timeout |
|---|---|---|---|---|---|
Server connection limit: · Reserved for migrations/admin: · Total at peak ≤ limit? · Pooler (none / PgBouncer / RDS Proxy / ProxySQL):

## 10. Migration & seed
| Order | Content | Depends on | Lock taken / expected duration | Rollback |
|---|---|---|---|---|
Seed data: · Brownfield backfill under traffic (batch size, throttle):

## 11. Syntax verification
| Decision | Syntax used | Verified? (source) |
|---|---|---|

## 12. Doubts
## 13. Assumptions & risks

## 14. Growth model & scaling (`references/db/growth-forecast.md`, `references/db/scaling-ladder.md`)
Assumptions (low / expected / high): users · monthly growth · rows per user per month · peak factor · retention
| Threshold | Crossed at (expected) | Crossed at (high) | Chosen rung | Trigger for next rung | Alert |
|---|---|---|---|---|---|
Last re-forecast (date, real vs projected):

## 15. Engine decision (`references/db/engine-selection.md`)
Engine + version: · ADR link: · Revisit when:
| Store | Workload it owns | Source of truth? | Fed by (outbox / CDC / none) | Owner |
|---|---|---|---|---|

## 16. Backup & DR (`references/db/backup-dr.md`)
RPO: · RTO: · Retention: · Method: · Off-site copy: · Encrypted:
| Drill date | Restored to | Measured RTO | Data lost | Problems |
|---|---|---|---|---|

## 17. Personal data inventory (`references/db/security-compliance.md`)
Applicable law packs:
| Table.column | Category | Sensitive? | Purpose / basis | Retention | Readers | Leaves country? | Masked outside prod? |
|---|---|---|---|---|---|---|---|
