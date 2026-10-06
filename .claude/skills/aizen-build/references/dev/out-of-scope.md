# Work outside the plan: note it, never do it (v25)

Out of scope = any change not traceable to the agreed plan: performance tweaks, refactors, renames, cleanups, a
bug you stumbled on (even one line), extra validation/logging/caching/retries/indexes, new or upgraded
dependencies, tool config, doc edits.

Why strict: unrequested changes slow the review, make reverts harder and slip behaviour past what the owner agreed.
Good ideas still matter — they become their own task.

## What to do

1. Do not build it and do not stop the unit for it.
2. Add one row to your report under `## Proposals` (the coordinator lists them in the final summary; the owner
   decides later, as a new task):

   ```markdown
   | P-1 | N+1 query listing orders | `order.repository.ts:88` | 51 queries for 50 orders, 420 ms [verified] | suggest: new task |
   ```
3. Severe (data loss, security hole, the agreed plan cannot work) → return `BLOCKED` now with that row; this is
   the only case that interrupts the flow.

**Allowed without a proposal:** registering your new module in the app wiring, and fixing type/lint errors your
own change caused — only inside your write set. Unsure → it is out of scope.
