# Upstream: planetscale-postgres-internals

Vendored, unmodified, into Aizen. Do not edit these files — change `vendor.lock.json` and run
`node bin/vendor.js sync planetscale-postgres-internals`; put Aizen's own view in the pack's guides instead.

| | |
|---|---|
| Source | https://github.com/planetscale/database-skills |
| Commit | `73b20b7eb64716d8c7100c054f0677c0c6e77e30` (branch `main`) |
| Licence | MIT — see `LICENSE` in this folder |
| Copied | `skills/postgres/references/mvcc-vacuum.md` → `references/mvcc-vacuum.md`<br>`skills/postgres/references/mvcc-transactions.md` → `references/mvcc-transactions.md`<br>`skills/postgres/references/index-optimization.md` → `references/index-optimization.md`<br>`skills/postgres/references/optimization-checklist.md` → `references/optimization-checklist.md` |

Only the vendor-neutral internals (MVCC, VACUUM, index audit, optimisation checklist). PlanetScale CLI, pooling and hosting pages dropped.

**Precedence:** this is how to do things right *in this tool*. Aizen core rules still decide how much to build and
who decides (`references/core/workspace.md` §3 in aizen-core): an upstream "ask the user first", "announce",
"install" or "deploy" step becomes a plan question or an A3 item, never an action on its own.
