# Plan — <TASK> — <title>

> Plan vN · State: `DRAFT` | `APPROVED <date>` · Base: `<branch>` @ `<sha>` · Updated: <YYYY-MM-DD>
> Integration branch: `int/<TASK>` · Finish: push + `gh pr create --draft … --body-file .aizen/runs/<TASK>/reports/pr-body.md`
> commands for the owner (agents never push) · State: `.aizen/runs/<TASK>/state.md`
> Environments for agents: `local` <, `ENV-02 staging` — every apply still A3> · Production: never agents (A4)

## 1. Goal and scope
Goal: <one checkable sentence>
In scope: <ids> · Out of scope: <items + reason>
Simpler option considered: <the simplest approach that would also work; why this plan is not simpler>

## 2. Sources
| Doc | Location | Version / commit / date read | Confidence |
|---|---|---|---|

## 3. Units
| Unit | Kind | Covers | Write set (exact) | Commands | Checks | Backup | Rollback | After |
|---|---|---|---|---|---|---|---|---|
| measure | — (read-only) | root cause of BUG-01 | — | `EXPLAIN …` | result recorded | — | — | — |
| api | be | FR-01, BR-02 | `src/modules/order/**`, `src/app.module.ts` | `npm test -- order`, `npm run lint` | tests green, check.py PASS | — | revert commit | measure |
| web | fe | SCR-02 | `web/src/order/**` | `pnpm test order`, `pnpm build` | states × breakpoints screenshots | — | revert commit | measure |
| deploy | infra (devops) | NFR-03, `ORDER_TTL` | `deploy/order/**`, `.github/workflows/order.yml` | `helm lint deploy/order`, `actionlint` | lint green, non-prod apply via A3 | state backup path | `helm rollback order <rev>` | api |

Waves: 1 = measure · 2 = api ‖ web · 3 = deploy (no check-in: the approved plan runs to the end).
Test lenses: <functional + …> · Second reviewer: `redteam` when a risk module exists · No infra unit: <say so when none>
Each unit also gets its design block from `references/plan/method.md` (Does / Interface / Data / Tests / Questions).

## 4. Requirements traceability
| Id | Doc § | Requirement (near-verbatim) | Unit | Test | Status |
|---|---|---|---|---|---|

## 5. Risks
| # | Risk | Impact | Mitigation / owner |
|---|---|---|---|

## 6. Options and questions for the owner
A (recommended): <waves, parallel or sequential, models> — why · B: <…>
| # | Question | Choices | Default | Blocks |
|---|---|---|---|---|

## 7. Plan changes
| Date | Change | Reason | Approved by |
|---|---|---|---|

## 8. Approval
| Part | Confirmed by the owner (date, the owner's words) |
|---|---|
| scope | |
| <unit> | |
| delivery | |

Plan approved: <date, the owner's quoted words> (`state.py approve`).
