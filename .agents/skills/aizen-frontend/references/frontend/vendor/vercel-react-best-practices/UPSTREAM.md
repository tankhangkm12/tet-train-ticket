# Upstream: vercel-react-best-practices

Vendored, unmodified, into Aizen. Do not edit these files — change `vendor.lock.json` and run
`node bin/vendor.js sync vercel-react-best-practices`; put Aizen's own view in the pack's guides instead.

| | |
|---|---|
| Source | https://github.com/vercel-labs/agent-skills |
| Commit | `063bee94c3f4df8453406c830b0a7df0f2860278` (branch `main`) |
| Licence | MIT — see `LICENSE` in this folder |
| Copied | `skills/react-best-practices/SKILL.md` → `guide.md`<br>`skills/react-best-practices/rules` → `rules` |

Kept the six highest-impact categories (waterfalls, bundle, server, client fetching, re-render, rendering). Dropped js-* micro-optimisations and advanced-* patterns: Aizen optimises only measured hot paths (core/code-quality.md §3).

**Precedence:** this is how to do things right *in this tool*. Aizen core rules still decide how much to build and
who decides (`references/core/workspace.md` §3 in aizen-core): an upstream "ask the user first", "announce",
"install" or "deploy" step becomes a plan question or an A3 item, never an action on its own.
