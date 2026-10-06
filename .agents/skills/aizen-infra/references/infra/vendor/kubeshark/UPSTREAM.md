# Upstream: kubeshark

Vendored, unmodified, into Aizen. Do not edit these files — change `vendor.lock.json` and run
`node bin/vendor.js sync kubeshark`; put Aizen's own view in the pack's guides instead.

| | |
|---|---|
| Source | https://github.com/LukasNiessen/kubernetes-skill |
| Commit | `34f93c1e409156958cc7c410ab1aa88ab512f10f` (branch `main`) |
| Licence | MIT — see `LICENSE` in this folder |
| Copied | `SKILL.md` → `guide.md`<br>`references` → `references` |

Failure-mode workflow for Kubernetes manifests and Helm (insecure defaults, resource starvation, exposure, privilege sprawl, fragile rollouts, API drift).

**Precedence:** this is how to do things right *in this tool*. Aizen core rules still decide how much to build and
who decides (`references/core/workspace.md` §3 in aizen-core): an upstream "ask the user first", "announce",
"install" or "deploy" step becomes a plan question or an A3 item, never an action on its own.
