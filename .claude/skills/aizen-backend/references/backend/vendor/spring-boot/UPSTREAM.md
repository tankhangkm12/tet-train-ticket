# Upstream: dr-jskill-spring-boot

Vendored, unmodified, into Aizen. Do not edit these files — change `vendor.lock.json` and run
`node bin/vendor.js sync dr-jskill-spring-boot`; put Aizen's own view in the pack's guides instead.

| | |
|---|---|
| Source | https://github.com/jdubois/dr-jskill |
| Commit | `5c0ef67e402f764783c7fa5d90c357b4260fc8d6` (branch `main`) |
| Licence | Apache-2.0 — see `LICENSE` in this folder |
| Copied | `references/SPRING-BOOT-4.md` → `spring-boot-4.md`<br>`references/PROJECT-SETUP.md` → `project-setup.md`<br>`references/CONFIGURATION.md` → `configuration.md`<br>`references/DATABASE.md` → `database.md`<br>`references/SECURITY.md` → `security.md`<br>`references/TEST.md` → `test.md`<br>`references/LOGGING.md` → `logging.md`<br>`references/DOCKER.md` → `docker.md` |

Julien Dubois' (JHipster) Spring Boot 4 practices. Only the reference pages; the project generator scripts, front-end and cloud pages are not vendored.

**Precedence:** this is how to do things right *in this tool*. Aizen core rules still decide how much to build and
who decides (`references/core/workspace.md` §3 in aizen-core): an upstream "ask the user first", "announce",
"install" or "deploy" step becomes a plan question or an A3 item, never an action on its own.
