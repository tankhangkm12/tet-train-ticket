# Step checklist — done criteria and evidence

Read before starting a step and before writing its report. `gate.py` checks the files marked (gate); the rest is
evidence you paste into `.aizen/runs/init/reports/step-<N>.md`.

| Step | Done when | Evidence in the report |
|---|---|---|
| pre | `.aizen/runs/init/inputs.md` lists repo + docs (gate); `.gitignore` has `.aizen/` (gate) | output of `check_inputs.py` |
| 0 | `.git/` exists (gate); `origin` = given URL; `develop` exists (gate); remote content handled with the user | `git remote -v`, `git branch -a` |
| 1 | `plans/plan.md` exists (gate); every open question answered; user said "ok" (gate: `Approved: yes`) | plan summary, Q&A list |
| 2 | layout matches plan; app starts; `GET /health` → 200 | tree (2 levels), curl output |
| 3 | `Dockerfile` + `docker-compose.yml`/`compose.yaml` (gate); every service healthy | `docker compose ps`, curl `/health` |
| 4 | `.env.example` + `.env` (gate); `.env` git-ignored (gate); one config module; missing var stops startup | startup log with a var removed |
| 5 | startup connects to every infra service or exits non-zero; `/health/ready` per dependency; user "ok" (gate) | ready JSON all up; log + exit code with one service stopped |
| 6 | every external tool used through an interface; one composition root | list `interface → implementation → wired in` |
| 7 | request-id in response header and every log line; error/validation/logging/timing layers; auth + guard; tests pass | 2 log lines with same id, 401/403 curl, test output |
| 8 | `README.md` (gate) has every section of `readme-template.md`; every `.env.example` var documented | section list, var diff = empty |
| 9 | `.aizen/runs/init/graphify/` not empty (gate); review table filled; gaps fixed or listed; user "ok" (gate) | review table from `graphify-review.md` |
| 10 | `gate.py 11` exits 0; clean rebuild works; tests pass; `git status` clean; user "ok" (gate) | handover block (SKILL.md Output) |

## Report rules

- `Status: done` only with evidence; `Status: skipped` only with `Skip-approved-by: user — <quote>`.
- Checkpoint steps add `Approved: yes` **after** the user's "ok", never before.
- Keep evidence short: the command and the lines that prove it, not full logs.
