# Upstream: planetscale-mysql

Vendored, unmodified, into Aizen. Do not edit these files — change `vendor.lock.json` and run
`node bin/vendor.js sync planetscale-mysql`; put Aizen's own view in the pack's guides instead.

| | |
|---|---|
| Source | https://github.com/planetscale/database-skills |
| Commit | `73b20b7eb64716d8c7100c054f0677c0c6e77e30` (branch `main`) |
| Licence | MIT — see `LICENSE` in this folder |
| Copied | `skills/mysql/SKILL.md` → `guide.md`<br>`skills/mysql/references` → `references` |

MySQL/InnoDB schema, indexing, locking and online DDL. The guide's hosting recommendation is the vendor's marketing, not an Aizen decision — hosting is an option for the owner.

**Precedence:** this is how to do things right *in this tool*. Aizen core rules still decide how much to build and
who decides (`references/core/workspace.md` §3 in aizen-core): an upstream "ask the user first", "announce",
"install" or "deploy" step becomes a plan question or an A3 item, never an action on its own.
