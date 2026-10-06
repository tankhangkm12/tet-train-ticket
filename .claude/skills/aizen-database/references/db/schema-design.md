# Schema design → `<unit>-database.md` (one module or service per run)

Written by `dev` (db), or by `planner` (design) at the DB stage — then the performance sections (template §6–§9)
may say "not assessed". Path: `references/core/workspace.md` §2.1 (`<unit>` = module in a
monolith, service in microservices).

Input: `<module>-design.md` for every module in the unit. Schema is the hardest thing to change once
real data exists: challenge first, write second. Enough detail to write migrations without asking.

Derive from the module design, not imagination: every table traces to an LLD operation, and every line
of the LLD's stage-4 handoff list gets a concrete constraint. No module design yet → say it will likely
be redone, ask whether to write it first. UI designs or a frontend architecture available → every input,
filter, list column and state is a schema requirement; filter/sort fields need indexes.

## Step 1 — Forks (≈ 7–10 questions, one per turn)

1. DBMS + version; own schema/database or shared.
2. Primary key type (auto-increment / UUID and which version / ULID / business code) and why.
3. Hard vs soft delete per table; audit columns.
4. History/versioning — which data keeps history, which is overwritten (ties to stage 0 audit row).
5. Normalization level; accepted duplication and who keeps copies in sync.
6. Multi-branch / multi-tenant / multi-language; time partitioning for large tables.
7. Files/media: where stored, and whether file metadata is created **before** its parent record
   (presigned upload → nullable FK or staging table). Decide here, not in stage 5.
8. Money representation and rounding, time storage (UTC `timestamptz`, `date` for pure dates) —
   offer the owner's standards (`references/design/design-standards.md`) as the recommended option.

### Team conventions — decided once per project, recorded as a `D-nn`, then reused

Some teams standardise table rules beyond the engine's defaults. Offer them as options in fork 3/5, never as
silent defaults; the choice goes to `.aizen/config/conventions.md`.

| Convention | Gain | Cost / when not |
|---|---|---|
| Audit columns on every table (`created_at`, `updated_at`, `created_by`, `updated_by`, `version` for optimistic locking) | traceability, concurrency control for free | noise on pure lookup/junction tables — say which tables are exempt |
| A comment on every column and every enum value (`COMMENT '1: active, 2: deleted'` / `COMMENT ON COLUMN`) | the schema explains itself to the next agent | none worth skipping; enum values must match the doc's enum table |
| Soft delete (`deleted_at NULL`) | audit trail, undo | every query and UNIQUE index must exclude deleted rows; FK `ON DELETE CASCADE` contradicts it (Step 4) |
| Vertical split of wide tables (> ~20 columns): hot list columns in the main table, large rarely-read text in a 1-1 detail table | smaller rows in the buffer pool, cheaper list queries | an extra join on detail screens; only when the list query is hot |
| Table-prefixed column names (`order_id`, `order_status` inside `orders`) | unambiguous JOIN output | fights ORMs and the naming in `references/backend/principles.md` §6 (plain `id`, FK `<singular>_id`); recommend against unless the team already uses it |
| `NOT NULL DEFAULT ''` / `DEFAULT 0` everywhere | fewer null branches | a fake value hides "unknown"; prefer `NOT NULL` without a sentinel default, and `NULL` only where unknown is a real state |

Index rule worth repeating: never a single-column index on a low-cardinality flag (`status`, `is_deleted`) —
the optimizer ignores it; combine it with a selective column (`(tenant_id, status, created_at)`), or use a
partial index (`WHERE deleted_at IS NULL`) where the engine has one. Name indexes `idx_<table>_<cols>` /
`uq_<table>_<cols>` unless the repo already has a pattern.

## Step 2 — Doubts before writing

Over/under-normalization · many-to-many without junction · free-text enums · **FK across service
boundaries** · missing UNIQUE where business demands uniqueness · JSON columns replacing design ·
fast-growing tables without a plan.

## Step 3 — Write (template `assets/db/database.md`)

1. Conventions (table naming, PK, time columns, soft delete, money, enums)
2. Relations + ASCII ERD + table `relation · type · FK · on parent delete`
3. Per table: `column · type · null · default · constraint · meaning` + keys table (PK/UNIQUE→which
   LLD rule/FK+ON DELETE/CHECK)
4. Indexes: `name · table · columns · type · query or screen served · LLD §`. An index that serves no
   named query is removed.
5. Enums & data rules; rules the schema cannot express and where they are enforced
6. Heavy queries expected — with the plan evidence when `dev` (db) owns the doc
7. Growth, partitioning and retention (`dev` (db))
8. Database-side code: procedures, functions, triggers, scheduled jobs (`dev` (db))
9. Connections: pool size per instance, timeouts (`dev` (db))
10. Migration & seed order, rollback per step, backfill for brownfield under traffic
11. Syntax verification table
12. Doubts · Assumptions & risks

## Step 4 — Verify syntax implements the decision

When turning a decision into DDL/config, check the function really produces what was chosen. Real
failures: chose UUIDv7 but wrote `gen_random_uuid()` (v4); chose Argon2id but example uses bcrypt;
chose cursor pagination but query uses OFFSET; chose soft delete but FK is `ON DELETE CASCADE`.
Research the function in official docs; unsure → Assumptions, never guess.

## Exit gate

| # | Check | Result + evidence |
|---|---|---|
| 1 | Every LLD handoff line → a named UNIQUE/CHECK/PK | |
| 2 | Every table traces to an LLD operation | |
| 3 | Every index traces to a query/screen | |
| 4 | Every UI field has storage; every filter/sort has an index | |
| 5 | No FK to another service's table (only reference ids) | |
| 6 | Every VARCHAR has a length, numbers have units, enums list all values | |
| 7 | Every migration step has a rollback | |
| 8 | Every concrete syntax verified (name the functions checked + source) | |
| 9 | (`dev` (db)) Every table expected to pass ~10M rows or grow without bound has a growth, partitioning or retention answer | |
| 10 | (`dev` (db)) Every procedure/function/trigger/job lives in a versioned migration with rollback and a test | |
| 11 | (`dev` (db)) Pool size × instances (+ migrations, jobs, admin) ≤ the server's connection limit, with headroom | |
| 12 | (`dev` (db)) Every heavy query has a plan captured on representative data, or is marked `[unverified]` | |

When `planner` (design) writes this document as the fallback, rows 9–12 read "not assessed — no db unit".
