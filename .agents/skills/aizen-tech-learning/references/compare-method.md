# Compare by architecture, not by opinion

1. **Fix the operation and the workload** from the intake (e.g. "GET 1 KB value, 100k/s, 1 node"). Every
   alternative is judged on that same operation.
2. **Map each alternative** the same way as the main technology: its components and one mermaid diagram of the
   path the operation takes. Name the alternative's components in plain words (the C-IDs belong to the main
   technology).
3. **Walk the same layers** (L1–L5) and write, per layer, the mechanism and its counted cost.
4. **Table**: one row per layer (or per mechanism that differs), one column per technology. Each cell = mechanism
   + cost + source when not obvious.
5. **Verdict as conditions**: "Choose X when <mechanism condition>". Never "X is better".

## A good row vs a rejected row

| Layer | Redis 7.2 | Memcached 1.6 |
|---|---|---|
| L2 good | 1 command thread, no locks; O(1) dict lookup | worker threads + per-item locks; O(1) hash lookup |
| L3 good | 1 `epoll_wait` serves all sockets; `write` per reply | `epoll` per worker thread (libevent); scales across cores |
| ~~L2 rejected~~ | ~~fast~~ | ~~faster with many cores~~ |

The rejected row states an outcome without the mechanism; `scripts/check_tree.py` fails cells that are only an
adjective (fast, slow, tốt, cao, …).

## Numbers

- Prefer numbers from the project's docs, source code, papers or reproducible benchmarks; give the version and
  hardware they came from.
- A number you derived (e.g. "1 syscall per 100 requests with pipelining depth 100") is fine — show the
  arithmetic.
- Anything else is `estimate` and says so.
