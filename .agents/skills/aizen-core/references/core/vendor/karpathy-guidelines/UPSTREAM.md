# Upstream: karpathy-guidelines

Vendored, unmodified, into Aizen. Do not edit these files — change `vendor.lock.json` and run
`node bin/vendor.js sync karpathy-guidelines`; put Aizen's own view in the pack's guides instead.

| | |
|---|---|
| Source | https://github.com/multica-ai/andrej-karpathy-skills |
| Commit | `2c606141936f1eeef17fa3043a72095b4765b9c2` (branch `main`) |
| Licence | MIT — see `LICENSE` in this folder |
| Copied | `skills/karpathy-guidelines/SKILL.md` → `guide.md`<br>`EXAMPLES.md` → `examples.md` |

The four behavioural principles (think before coding, simplicity first, surgical changes, goal-driven execution) and their worked examples. Aizen's operative wording lives in references/core/code-quality.md and references/core/rules.md; the mapping is in aizen-core SKILL.md. The upstream README states MIT without a LICENSE file — the MIT text here names the plugin author.

**Precedence:** this is how to do things right *in this tool*. Aizen core rules still decide how much to build and
who decides (`references/core/workspace.md` §3 in aizen-core): an upstream "ask the user first", "announce",
"install" or "deploy" step becomes a plan question or an A3 item, never an action on its own.
