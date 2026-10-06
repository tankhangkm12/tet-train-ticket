# Upstream: elastic-elasticsearch

Vendored, unmodified, into Aizen. Do not edit these files — change `vendor.lock.json` and run
`node bin/vendor.js sync elastic-elasticsearch`; put Aizen's own view in the pack's guides instead.

| | |
|---|---|
| Source | https://github.com/elastic/agent-skills |
| Commit | `baa511126ba2dc37b52e273b52734f8e4e0d323c` (branch `main`) |
| Licence | Apache-2.0 — see `LICENSE` in this folder |
| Copied | `skills/elasticsearch/elasticsearch-index-design/SKILL.md` → `index-design/guide.md`<br>`skills/elasticsearch/elasticsearch-index-design/references` → `index-design/references`<br>`skills/elasticsearch/elasticsearch-query-optimization/SKILL.md` → `query-optimization/guide.md`<br>`skills/elasticsearch/elasticsearch-query-optimization/references` → `query-optimization/references`<br>`skills/elasticsearch/elasticsearch-reindex/SKILL.md` → `reindex/guide.md`<br>`skills/elasticsearch/elasticsearch-reindex/references` → `reindex/references` |

Official Elastic guidance for mappings, query profiling and reindex-based mapping changes. Commands use the `elastic` CLI; any write to a shared cluster is A3.

**Precedence:** this is how to do things right *in this tool*. Aizen core rules still decide how much to build and
who decides (`references/core/workspace.md` §3 in aizen-core): an upstream "ask the user first", "announce",
"install" or "deploy" step becomes a plan question or an A3 item, never an action on its own.
