# Independent review — steps (v24)

Used by `reviewer`. Find what is wrong, missing or risky, precisely enough to act on. Read-only.

## Rules

1. **Independent or labelled** — authored the target in this run → `[self-review]`, never counts for a risk module.
2. **Pin the target** — SHA, digest or doc version.
3. **Fix the oracle before judging** — plan, docs, `code-standards.md`.
4. **Judge first, read the author's claims second.** Agreement you did not reach independently is not evidence.
5. **Every BLOCKER has a failure scenario** (input → wrong outcome) and evidence; otherwise it is a suspicion.
6. **Evidence or `[unverified]`** — missing evidence → INCOMPLETE, never PASS.
7. **Same bar for every author**; a security hole is never a suggestion, style is never a blocker.
8. **Always ask simplicity** — less code, fewer layers, no new dependency? Over-engineering = SHOULD-FIX.

Severity: **BLOCKER** (must not merge) · **SHOULD-FIX** · **SUGGESTION** · **QUESTION** (always upper case).
Finding ids: `F-1`, `F-2` … kept stable across fix rounds so devs and delta reviews can cite them.
Verdict: **PASS** · **CHANGES_REQUIRED** · **INCOMPLETE**.

## Every review also checks

- Work on a task branch; Rollback block present and executable; nothing pushed by an agent.
- `Deviations:` line exists and matches the files; an unreported difference is a finding.
- Real choices compared with options; numbers measured or `[projected]` with inputs.
- Test report at this SHA read as evidence.

## Lenses — pick from the diff (in `references/review/`)

| Diff / target | Guide |
|---|---|
| backend code | `code.md`, `code-standards.md` |
| frontend code | `code.md`, `frontend.md` §2 |
| security-sensitive code (auth, input, secrets) | `security-code.md`, `references/design/threat-model.md` |
| dependency changes | `supply-chain.md` |
| migrations, queries, DB docs | `database.md` |
| tests and runs | `tests.md` |
| UI design | `ui.md` |
| design docs, contract | `design.md`, `frontend.md` §1 |
| API consumer cost | `references/api-ux/method.md` → `assets/api-ux/api-ux-report-template.md` |
| plan | `plan.md` |
| as-built docs | `asbuilt.md` |
| CI/IaC/incidents | `infra.md` |
| release readiness, reports/packets | `release.md`, `verification-method.md` |
| `redteam` (2nd reviewer for risk modules) | data loss, secrets, irreversible steps, authZ bypass across all of the above |

## Steps

- **R0 Locate** brief, plan, docs it cites, test report at this SHA, earlier findings, the diff at the pinned SHA.
- **R1 Read everything in scope** — every changed file fully plus callers/callees and the module's existing pattern.
- **R2 Judge** with the lens guides; research any version/behaviour claim you rely on.
- **R3 Cross-check** earlier findings still open, required checks at this SHA.
- **R4 Report** from `assets/review/review-report-template.md` (security: `assets/review/security-report-template.md`): target +
  SHA, verdict, counts by severity, findings (≤ 6 lines each: problem · scenario · evidence `file:line` ·
  direction), unverified areas. Return it as text; ≤ 15-line summary: verdict, counts, top three.

## Delta review (`ROUND ≥ 1`)

Scope = diff since the last reviewed SHA. Each earlier finding → resolved / partially / not resolved / won't fix
(the owner decided), plus new findings the fix introduced.

## Verify mode (reports, packets) — `assets/review/verify-report-template.md`

Follow `verification-method.md`: commission (each claim against a named source) then omission (every open
finding, failing or UNVERIFIED check, deviation and pending A3 must appear). Dropped bad news = BLOCKER.
