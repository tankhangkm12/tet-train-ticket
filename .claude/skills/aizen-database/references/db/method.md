# Database work — steps (v24)

Used by `dev` with `KIND=db`, and by `planner`/`reviewer` for DB questions. Correct first, then fast, then cheap
to keep — every claim with a number.

## Rules

1. **Measure, never guess.** A performance claim carries a plan or timing on stated data; before/after on the same data.
2. **Representative data or say so.** A plan on 100 rows says nothing about 100 million → `[unverified]` + what data it needs.
3. **Correctness before speed.** A constraint the business needs (UNIQUE, CHECK, FK) is never dropped for speed.
4. **Every DB object is a migration** — tables, indexes, procedures, triggers, views, jobs, partitions — versioned,
   with a rollback, never typed into a server by hand.
5. **Lock budget first.** Every DDL on a table with real data states the lock, the expected duration on the largest
   table, and `lock_timeout` / online method (`migrations.md`).
6. **No hidden business rules** in triggers/procedures; each one listed in the database doc (`db-code.md`).
7. **Options, not decisions** — engine, key type, partitioning, retention, instance size, pooler: options with numbers.
8. **Version-true syntax** — name the engine version, cite the official doc (`engines/*.md`).
9. **Project before deciding** — table size, connections → RAM, pool per instance via `scripts/core/capacity.py`.
10. Local DB only (`docker compose exec`, Testcontainers). Any shared DB is A3; production is A4.

## Steps

- **DB0 Locate** migrations folder and tool (Flyway, Liquibase, Alembic, Prisma, TypeORM, Knex…), engine + version
  from compose/IaC/driver config, ORM and pool settings.
- **DB1 Read and challenge** the module design and the code issuing the queries: rules without a constraint, list
  screens without an index, tables without a growth answer, transactions holding locks across a network call.
- **DB2 Work.** Dump the local DB before any migration or data change (`references/core/git.md` §4). One change at
  a time when measuring; commit each step.
- **DB3 Measure** before and after on the same data: plan, timing (median of ≥ 5 warm runs + the cold run), rows,
  buffers read.
- **DB4 Verify** migrations up → down → up on a local DB; tests for DB-side code; the database doc's exit gate.
- **DB5 Hand off.** What the backend must change (query shape, pool, retry on serialization failure) under
  "For other roles". Anything for a shared/production DB → the exact command, its verification query and rollback.

## Guides (in `references/db/`)

| Task | Read → template |
|---|---|
| schema, new table, index | `schema-design.md` → `assets/db/database.md` |
| slow query, EXPLAIN, N+1 | `performance.md` + `engines/<engine>.md` |
| engine specifics (each ends with a "Deeper" table into vendored upstream rules) | `engines/postgresql.md` · `engines/mysql.md` · `engines/mongodb.md` · `engines/redis.md` · `engines/elasticsearch.md` · new engine: `engines/_new-engine.md` |
| growth forecast | `growth-forecast.md` → `assets/db/growth-report.md` |
| scaling, replicas, sharding | `scaling-ladder.md` → `assets/db/scaling-options.md` |
| choosing an engine | `engine-selection.md` → `assets/db/engine-adr.md` |
| partitioning, retention, archive | `partitioning-retention.md` |
| locks, deadlocks, hot rows, isolation | `concurrency.md` |
| data across services, outbox, CDC, saga | `microservices-data.md` |
| backup, PITR, DR, HA | `backup-dr.md`, `ha-replication.md` → `assets/db/dr-runbook.md` |
| PII, PDPL, GDPR | `security-compliance.md` + `compliance/*.md` |
| procedures, triggers, views, jobs | `db-code.md` |
| pools, timeouts | `connections.md` |
| engine config, machine size | `engine-tuning.md` |
| safe migration, backfill | `migrations.md` |
