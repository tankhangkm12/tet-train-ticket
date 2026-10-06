# Messaging — queues and event streams (Kafka, RabbitMQ)

For async work inside one service (jobs, emails, exports) and for events between services. Which broker is a
design decision (HLD / `references/design/architecture-options.md`); this page is how to use the chosen one
correctly. Cross-service invariants (outbox, saga, publisher port): `microservices.md` §2–§7.

## 1. Rules for every broker

1. **At-least-once is the default; design for duplicates.** Every consumer is idempotent: a processed-message
   table keyed by message id (unique constraint, same transaction as the effect), or an operation that is
   naturally idempotent (upsert by business key, conditional state transition). "Exactly once" claims need the
   broker's transactional feature *and* an idempotent sink — state which, with evidence.
2. **Publish after commit**: DB write + publish = outbox (`microservices.md` §4). Never publish inside the DB
   transaction, never publish before it commits.
3. **Every message has**: a stable id, a type with a version (`order.placed.v1`), the aggregate key, a
   timestamp, a correlation/request id, and a schema. Breaking changes → a new version, consumers of both
   during the overlap (`references/api-ux/evolution.md`).
4. **Retries are bounded and visible**: exponential backoff with jitter and a max; then a dead-letter
   destination with the error, the attempt count and the original payload. A DLQ without an owner and an alert
   is a silent data-loss path — the plan names both.
5. **Ordering only where the domain needs it**, and only per key: Kafka per partition (key = aggregate id),
   RabbitMQ per queue with one consumer (or single-active-consumer). Global ordering is almost never required —
   say so when it is not.
6. **Poison messages never block the stream**: parse/validate first; an unprocessable message goes to the DLQ
   with its reason instead of being retried forever.
7. **Consumers are sized with numbers**: throughput per consumer, partitions/queues, lag budget
   (`scripts/core/capacity.py throughput`, `references/core/numbers.md`).
8. Creating topics/queues/exchanges on a shared broker, changing retention, replaying or purging: A3; production: A4.

## 2. Kafka

- Producer: `acks=all`, `enable.idempotence=true`, key = aggregate id, compression on; never fire-and-forget for
  business events — handle the send callback/future.
- Consumer: commit offsets **after** the effect is durable (manual commit, or the framework's after-record mode);
  `max.poll.interval.ms` above the slowest handling time; rebalance-safe (no in-memory state keyed by partition
  without revoke handling).
- Schemas through a Schema Registry (Avro / JSON Schema / Protobuf) with a compatibility mode chosen once
  (BACKWARD is the usual default); topic naming `<domain>.<entity>.<event>`.
- Retention and partition count are sizing decisions with numbers; partitions can grow, never shrink.

**Deeper — Confluent's own guidance (vendored, Apache-2.0):** `references/backend/vendor/confluent-kafka/java/guide.md`
and `references/backend/vendor/confluent-kafka/python/guide.md`, with consumer patterns, multi-event topics and
schema rules in each `references/` and runnable producer/consumer samples. Their "ask these three questions
first" gate is answered by the plan; nothing is scaffolded without it.

## 3. RabbitMQ

- **Topology as code**: exchanges, queues, bindings and policies declared by the application at startup or by
  IaC — never clicked in the UI. Durable exchanges and queues; persistent messages for business events.
- **Quorum queues** for anything that must survive a node loss (classic mirrored queues are removed in 4.x);
  **streams** when consumers need replay.
- **Publisher confirms** on, and handle returns for unroutable messages (`mandatory`); an unconfirmed publish is
  not sent.
- **Manual acks** after the effect is durable; `prefetch` (QoS) set deliberately — start low (10–50) and measure;
  `nack` with `requeue=false` routes to the dead-letter exchange.
- **Retries** via a delayed retry queue (per-message TTL + DLX back to the work queue) or the delayed-message
  plugin (a plugin install is A3); never an immediate requeue loop.
- One connection per process, one channel per thread/consumer; connection recovery enabled in the client.
- Versions: 3.13 vs 4.x differ (AMQP 1.0 native, classic mirroring removed) — cite rabbitmq.com/docs for the
  version in use. `[unverified]` until checked.
