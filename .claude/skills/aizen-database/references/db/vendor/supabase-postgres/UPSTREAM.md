# Upstream: supabase-postgres-best-practices

Vendored, unmodified, into Aizen. Do not edit these files — change `vendor.lock.json` and run
`node bin/vendor.js sync supabase-postgres-best-practices`; put Aizen's own view in the pack's guides instead.

| | |
|---|---|
| Source | https://github.com/supabase/agent-skills |
| Commit | `c9be0e931b7930f7d02126d04774d904c381e7d7` (branch `main`) |
| Licence | MIT — see `LICENSE` in this folder |
| Copied | `skills/supabase-postgres-best-practices/SKILL.md` → `guide.md`<br>`skills/supabase-postgres-best-practices/references` → `references` |

Generic Postgres rules by impact (query, connections, RLS, schema, locking, data access, monitoring). Supabase-specific notes inside rules apply only on Supabase.

**Precedence:** this is how to do things right *in this tool*. Aizen core rules still decide how much to build and
who decides (`references/core/workspace.md` §3 in aizen-core): an upstream "ask the user first", "announce",
"install" or "deploy" step becomes a plan question or an A3 item, never an action on its own.
