# Verification — checking a summary against its sources

Used for `LENS=verify`: the coordinator's final summary, a release packet or a PR body is checked before
the owner acts on it. One rule: **a claim is `PASS` only when a named source, read now, says exactly it.**
The same claim checked by two agents must get the same verdict.

## 1. Sources

| Counts | Does not count |
|---|---|
| `.aizen/runs/<TASK>/evidence/<unit|main>.json` (command, exit code, SHA) | the summary restating a number |
| a role report at its path, with the SHA it ran on | "it was discussed" |
| a review finding quoted with report path and severity | a paraphrase of "quality" |
| branch / SHA / merge state read from `git` now | "probably merged" |
| `.aizen/runs/<TASK>/state.md` decision and log | a decision assumed to be made |

Support that only points back into the summary is `UNSUPPORTED`.

## 2. Commission — each claim

| Claim | Verify by |
|---|---|
| a metric (coverage, p95, test counts) | the evidence file or report: value, denominator, command, SHA |
| a status (unit done, check green) | evidence at the **current** SHA — older evidence is stale |
| a quality statement | the reviewer finding; the summary may not soften or upgrade severity |
| a decision | `state.md ## Decision` in the owner's words |

`FAIL` = the source says something else · `UNSUPPORTED` = no source says it. Both block.

## 3. Omission — the pass that catches a rosy summary

Build this list from the sources, ignoring the summary, then check each is in it: every open BLOCKER or
SHOULD-FIX · every open BUG · every `UNVERIFIED` or failing check · every `[agent-chosen]` or `[unverified]`
item · every `Deviations:` line other than `none` · every pending A3. Missing bad news is a `BLOCKER`; missing
good news is fine.

## 4. Severity and limits

`BLOCKER`: wrong value or status, `UNSUPPORTED` claim, dropped bad news, softened severity, a secret value
present. `SHOULD-FIX`: a percentage with no denominator, imprecise but true wording.
Verification never edits the summary or a source, never judges whether a design is sound (that is review),
and never passes what it could not check.
