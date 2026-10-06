# Lens: concurrency-perf (`tester` v24)

Brief header `LENS=concurrency-perf`. Shared lens rules (files, isolation, report, lane): `references/test/method.md`.

## Attacks
What happens when two actors hit the same record at once, and when the load the NFR promises arrives:
lost updates, double spend, oversell, deadlocks, lock waits, pool exhaustion, latency past target.

## Oracle
LLD concurrency mechanism per CORE operation (`D-nn`: version column, conditional update, row lock,
unique key, idempotency key) · NFR numbers (p95/p99, rps, error rate, pool size) · `[projected]` figures
from `references/core/numbers.md` that the design was built on.

## Techniques
- **Races:** N parallel actors on one key started by a barrier (latch, `asyncio.gather`, `Promise.all`), not
  sleeps; assert the invariant (one winner, stock never < 0, one event). Every CORE op gets ≥ 1 race case.
- **Lock contention:** measure rejection/retry rate and wait time at the NFR key rate; compare with
  `scripts/core/capacity.py contention --rps-per-key <low,exp,high> --window-ms <tx ms> --retries <n>`.
- **Load profile from the NFR:** warm-up, steady load at target rps, spike if the NFR names a peak; record
  p50/p95/p99, throughput, error rate, pool usage. Compare with `capacity.py throughput` / `connections`.
- Report measured next to projected; a gap > 2x is a finding even when the NFR passes.
- Repeat a race ≥ 20 times (state the count); one failure is a BUG, never flaky noise.

## Files
`<repo test root>/concurrency-perf/...` or suffix `.concurrency`; load scripts in the repo's perf folder
under `concurrency-perf/`. Tools per repo or approved (k6, Locust, JMeter, Gatling).

## Environment
Local and disposable only: own compose project `-p <TASK>-test-cperf`, own DB, own ports. Any shared or
staging load run is A3 (the owner's yes, per run). Say the machine (cores, RAM) with every number.

## Report
`.aizen/runs/<TASK>/reports/test-concurrency-perf.md`: table `scenario · target · measured p95 · rps ·
errors · projected · verdict`, race table `operation · actors × runs · invariant held`, BUG table
(`BUG-concurrency-perf-nn`).

## Never
Claim a number you did not measure (label `[projected]`) · load anything but local/approved targets ·
tune pools, indexes or code yourself (`HANDOFF: needs `dev` (be) / `dev` (db)).
