# Upstream: redis

Vendored, unmodified, into Aizen. Do not edit these files — change `vendor.lock.json` and run
`node bin/vendor.js sync redis`; put Aizen's own view in the pack's guides instead.

| | |
|---|---|
| Source | https://github.com/redis/agent-skills |
| Commit | `a84871d065f398fed55e1633f66b66f731eb4e2b` (branch `main`) |
| Licence | MIT — see `LICENSE` in this folder |
| Copied | `skills/redis-core/SKILL.md` → `core/guide.md`<br>`skills/redis-core/references` → `core/references`<br>`skills/redis-connections/SKILL.md` → `connections/guide.md`<br>`skills/redis-connections/references` → `connections/references`<br>`skills/redis-clustering/SKILL.md` → `clustering/guide.md`<br>`skills/redis-clustering/references` → `clustering/references`<br>`skills/redis-security/SKILL.md` → `security/guide.md`<br>`skills/redis-security/references` → `security/references`<br>`skills/redis-observability/SKILL.md` → `observability/guide.md`<br>`skills/redis-observability/references` → `observability/references` |

Official Redis guidance: data structures and key naming, connections/pipelining, cluster hash tags, ACL/TLS hardening, observability. Search, semantic cache and Iris dropped (not in the stack).

**Precedence:** this is how to do things right *in this tool*. Aizen core rules still decide how much to build and
who decides (`references/core/workspace.md` §3 in aizen-core): an upstream "ask the user first", "announce",
"install" or "deploy" step becomes a plan question or an A3 item, never an action on its own.
