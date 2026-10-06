# Elasticsearch — engine notes

Elasticsearch is a search index, not the source of truth: every document can be rebuilt from the primary store,
and the plan says how (reindex job, CDC, outbox consumer). Version first: `GET /` (8.x vs 9.x; OpenSearch is a
different engine — `_new-engine.md`).

## Aizen rules for Elasticsearch

- **Explicit mappings** for every index the code writes; dynamic mapping off (`"dynamic": "strict"`) or
  constrained to known patterns. A field's type cannot change in place — a type change is a new index plus
  reindex plus alias swap, planned as a migration with rollback (the alias points back).
- **Aliases in application code, never concrete index names**, so reindexing and rollover are invisible to it.
- **Sync path stated**: how writes reach the index (synchronous dual-write is a consistency risk; prefer an
  outbox or CDC consumer, `references/db/microservices-data.md`), what lag the product accepts, and how a full
  rebuild runs.
- **Filters in filter context**, scoring only where relevance matters; no leading wildcards; pagination with
  `search_after` + point-in-time, never deep `from`/`size`.
- Shard count is a sizing decision with numbers (`scripts/core/capacity.py`, `references/db/engine-tuning.md`), not a default.
- Any write to a shared cluster (index create/delete, reindex, settings) is A3; production is A4.

## Deeper — Elastic's own guidance (vendored, Apache-2.0)

| Need | Read |
|---|---|
| field types per access pattern, text + keyword multi-fields, mapping explosion, shard settings | `references/db/vendor/elastic/index-design/guide.md` |
| a slow query: profile first, then move clauses to filter context, remove leading wildcards | `references/db/vendor/elastic/query-optimization/guide.md` |
| changing a mapping safely: new index, reindex, alias swap | `references/db/vendor/elastic/reindex/guide.md` |

Their commands use Elastic's `elastic` CLI; with plain HTTP, the same requests go through `curl` to the cluster.
