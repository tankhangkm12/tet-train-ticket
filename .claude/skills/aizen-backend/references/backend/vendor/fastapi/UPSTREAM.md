# Upstream: fastapi

Vendored, unmodified, into Aizen. Do not edit these files — change `vendor.lock.json` and run
`node bin/vendor.js sync fastapi`; put Aizen's own view in the pack's guides instead.

| | |
|---|---|
| Source | https://github.com/fastapi/fastapi |
| Commit | `52159d7e7018df55b57a0b8fdd6c1193e48b2b57` (branch `master`) |
| Licence | MIT — see `LICENSE` in this folder |
| Copied | `fastapi/.agents/skills/fastapi/SKILL.md` → `guide.md`<br>`fastapi/.agents/skills/fastapi/references` → `references` |

The official FastAPI skill shipped inside the FastAPI repository: Annotated dependencies, response models, Pydantic v2, routing, streaming/SSE.

**Precedence:** this is how to do things right *in this tool*. Aizen core rules still decide how much to build and
who decides (`references/core/workspace.md` §3 in aizen-core): an upstream "ask the user first", "announce",
"install" or "deploy" step becomes a plan question or an A3 item, never an action on its own.
