# Redis — engine notes

Redis is a data store with its own failure modes, not "just a cache". Version first: `INFO server`
(`redis_version`; Redis 7.x vs 8.x, or Valkey/KeyDB, differ in commands and licence) — cite redis.io/docs for it.

## Aizen rules for Redis

- **Decide what Redis is for, per key family**: cache (losable, has a TTL, a source of truth elsewhere),
  ephemeral state (sessions, rate limits — losable with a known user impact), or primary data (needs
  persistence, replication and a backup answer in `backup-dr.md`). The plan names which, per key prefix.
- **Every cache key has a TTL and an invalidation story** (write-through, delete-on-write, or TTL-only with the
  stale window stated). Cache-aside reads handle a miss storm: request coalescing or a short lock for hot keys.
- **No unbounded keys or values**: a growing list, set or stream gets a cap (`LTRIM`, `XADD … MAXLEN ~`) or a
  retention job; the growth answer goes in the database doc like any table (`growth-forecast.md`).
- **Never in application code**: `KEYS`, `FLUSHALL`/`FLUSHDB`, unpaged `SMEMBERS`/`HGETALL` on large keys,
  `MONITOR` in production. Destructive or keyspace-wide commands against a shared instance are A3.
- **Connections**: one pool or multiplexed client per process, timeouts set, sized with
  `references/db/connections.md`; serverless/edge runtimes need an HTTP-based or pooled client.
- **Memory policy** (`maxmemory`, `maxmemory-policy`) is stated in the infrastructure doc; a cache uses an
  eviction policy, primary data uses `noeviction` and alerts before the limit.

## Deeper — Redis Inc.'s own guidance (vendored, MIT)

| Need | Read |
|---|---|
| data structure per access pattern, key naming, transactions | `references/db/vendor/redis/core/guide.md` |
| pooling vs multiplexing, pipelining, `SCAN` instead of blocking commands, client-side caching, timeouts | `references/db/vendor/redis/connections/guide.md` |
| Redis Cluster hash tags, `CROSSSLOT`, replica reads | `references/db/vendor/redis/clustering/guide.md` |
| ACL users, TLS, network exposure, dangerous commands | `references/db/vendor/redis/security/guide.md` |
| what to monitor (memory, latency, slowlog, keyspace) | `references/db/vendor/redis/observability/guide.md` |
