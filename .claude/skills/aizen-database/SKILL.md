---
name: aizen-database
description: Aizen knowledge pack (v24) — schema design and team conventions, migrations, concurrency, performance, connections, growth, partitioning, HA/DR, compliance; engines PostgreSQL, MySQL, MongoDB, Redis, Elasticsearch. Loaded by Aizen roles through their brief; not a standalone skill, do not trigger it directly — use aizen-build.
---

# Database knowledge — Aizen pack (v24)

Owns the topics `db`: every `references/<topic>/…`, `assets/<topic>/…` and `scripts/<topic>/…` path for them
lives here. Shared rules (authority, evidence, code quality, style) are in `aizen-core`; the flow and roles are in
`aizen-build`.

- **Used by:** dev `KIND=db`; planner (DB questions); tester (database lens); reviewer (database lens).
- **Entry points:** `references/db/method.md` — each has a "Guides" table; load only the rows the change touches.
- Templates: `assets/db/` (database doc, growth report, scaling options, engine ADR, DR runbook).

## Upstream knowledge (vendored, pinned)

Best practice from the people who build the tools, copied verbatim at a pinned commit (`vendor.lock.json`
in the Aizen repo). It says how to do a thing right in that tool; Aizen core rules still decide how much to build
and who decides (`references/core/workspace.md` §3).

| Source | Details |
|---|---|
| Supabase — Postgres best practices | `references/db/vendor/supabase-postgres/UPSTREAM.md` |
| PlanetScale — MySQL and Postgres internals | `references/db/vendor/planetscale-mysql/UPSTREAM.md` |
| Redis Inc. — Redis core, connections, clustering, security, observability | `references/db/vendor/redis/UPSTREAM.md` |
| Elastic — index design, query optimisation, reindex | `references/db/vendor/elastic/UPSTREAM.md` |
