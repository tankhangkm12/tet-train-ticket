# Upstream: confluent-kafka-clients

Vendored, unmodified, into Aizen. Do not edit these files — change `vendor.lock.json` and run
`node bin/vendor.js sync confluent-kafka-clients`; put Aizen's own view in the pack's guides instead.

| | |
|---|---|
| Source | https://github.com/confluentinc/agent-skills |
| Commit | `db79f9e411674839a12d7c01d3434c54cf137266` (branch `main`) |
| Licence | Apache-2.0 — see `LICENSE` in this folder |
| Copied | `skills/developing-kafka-java-client/SKILL.md` → `java/guide.md`<br>`skills/developing-kafka-java-client/references` → `java/references`<br>`skills/developing-kafka-python-client/SKILL.md` → `python/guide.md`<br>`skills/developing-kafka-python-client/references` → `python/references` |

Official Confluent producer/consumer patterns and Schema Registry serializers for Java and Python, with sample code. Their HARD-GATE / announce steps are replaced by Aizen's plan questions (core/workspace.md §3).

**Precedence:** this is how to do things right *in this tool*. Aizen core rules still decide how much to build and
who decides (`references/core/workspace.md` §3 in aizen-core): an upstream "ask the user first", "announce",
"install" or "deploy" step becomes a plan question or an A3 item, never an action on its own.
