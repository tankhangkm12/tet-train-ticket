# Upstream: docker

Vendored, unmodified, into Aizen. Do not edit these files — change `vendor.lock.json` and run
`node bin/vendor.js sync docker`; put Aizen's own view in the pack's guides instead.

| | |
|---|---|
| Source | https://github.com/docker/skills |
| Commit | `f79172733725e2fd236343ee7b963c446ed85d09` (branch `main`) |
| Licence | Apache-2.0 — see `LICENSE` in this folder |
| Copied | `skills/docker-build-strategies` → `build-strategies`<br>`skills/docker-compose-patterns` → `compose-patterns`<br>`skills/docker-destructive-guardrails` → `destructive-guardrails` |

Official Docker guidance: multi-stage builds, layer caching, non-root images, Compose health/dependency patterns, and which commands destroy state. The guardrail tiers map onto Aizen A3.

**Precedence:** this is how to do things right *in this tool*. Aizen core rules still decide how much to build and
who decides (`references/core/workspace.md` §3 in aizen-core): an upstream "ask the user first", "announce",
"install" or "deploy" step becomes a plan question or an A3 item, never an action on its own.
