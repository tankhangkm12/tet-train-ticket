---
name: aizen-backend
description: Aizen knowledge pack (v24) — backend principles, architecture, module boundaries, API contract, data concurrency, messaging (Kafka, RabbitMQ), object storage (S3), microservices, stacks (Spring Boot, FastAPI, NestJS), API consumer cost. Loaded by Aizen roles through their brief; not a standalone skill, do not trigger it directly — use aizen-build.
---

# Backend and API-consumer knowledge — Aizen pack (v24)

Owns the topics `backend`, `api-ux`: every `references/<topic>/…`, `assets/<topic>/…` and `scripts/<topic>/…` path for them
lives here. Shared rules (authority, evidence, code quality, style) are in `aizen-core`; the flow and roles are in
`aizen-build`.

- **Used by:** dev `KIND=be`; reviewer (code, api-ux lenses); aizen-init.
- **Entry points:** `references/backend/method.md` · `references/api-ux/method.md` — each has a "Guides" table; load only the rows the change touches.
- Tool: `scripts/api-ux/apikit.py` (consumer journeys, contract diffs). Template: `assets/api-ux/api-ux-report-template.md`.

## Upstream knowledge (vendored, pinned)

Best practice from the people who build the tools, copied verbatim at a pinned commit (`vendor.lock.json`
in the Aizen repo). It says how to do a thing right in that tool; Aizen core rules still decide how much to build
and who decides (`references/core/workspace.md` §3).

| Source | Details |
|---|---|
| Confluent — Kafka Java/Python clients | `references/backend/vendor/confluent-kafka/UPSTREAM.md` |
| FastAPI maintainers — official FastAPI skill | `references/backend/vendor/fastapi/UPSTREAM.md` |
| Julien Dubois — Spring Boot 4 practices | `references/backend/vendor/spring-boot/UPSTREAM.md` |
