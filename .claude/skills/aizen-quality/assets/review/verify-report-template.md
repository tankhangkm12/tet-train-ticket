# Verification — <TASK> <summary | release packet | PR body> @ <SHA>

> **VERIFY · <TASK> · <PASS | FAIL (n BLOCKER, m SHOULD-FIX)>**
> Checked: <draft path> against <count> sources
> Commission: <n> claims — <p> PASS · <f> FAIL · <u> UNSUPPORTED
> Omission: <n> items in sources — <k> missing from the draft
> Next: <coordinator fixes and re-submits | ready for the owner>

Independence: <checked by a different agent than the author | `[self-verified — weaker]`>

## 1. Commission — each claim against its source

| # | Claim in the draft | Source | What the source says | Verdict |
|---|---|---|---|---|
| 1 | tests 48/48 green | `evidence-api.json` @ 3f2a9c1 | 46 passed, 2 failed | **FAIL** |
| 2 | review clean | `review.md` @ 3f2a9c1 | F-3 SHOULD-FIX open | **FAIL** |
| 3 | p95 under 300 ms | — | no measurement exists | **UNSUPPORTED** |

## 2. Omission — what the sources hold and the draft must carry

| # | Item found in sources | Where | In the draft? |
|---|---|---|---|
| 1 | secrets step UNVERIFIED (no gitleaks) | `evidence-api.json` | **MISSING** |
| 2 | `Deviations:` added a retry wrapper | `dev-api.md` | yes |

## 3. Fixes

| # | Severity | What is wrong | Source of truth | Fix |
|---|---|---|---|---|
| F-1 | BLOCKER | test count overstated | `evidence-api.json` | quote 46/48, name the 2 failures |

## 4. Verdict

<PASS — ready for the owner> | <FAIL — fix against the sources, then re-verify; this note is not edited>
