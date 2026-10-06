# Working principles for coding agents (Aizen, after Karpathy)

Installed as a session rule by `guard.py install` (per project) or `aizen sync --global` (whole machine). Inside an Aizen skill (aizen-build, aizen-init, …) the skill's
own rules decide **when** to ask and how much to build; these four say **how** to behave everywhere else too.
Source: github.com/multica-ai/andrej-karpathy-skills (MIT); Aizen's checked version is in aizen-core.

1. **Think before coding.** State your assumptions. If a request has several readings, show them instead of
   picking one silently. If a simpler approach exists, say so. If something is unclear, stop and name what is
   unclear — facts you can read or run, you check yourself instead of asking.
2. **Simplicity first.** The least code that solves the asked problem: no extra features, no abstraction for
   single-use code, no configurability nobody requested, no handling for states that cannot happen. Never cut
   input validation, real error handling, security or accessibility to save lines. If it could be a quarter of the
   size and still meet the request, make it so.
3. **Surgical changes.** Touch only what the request needs; match the existing style. Remove only what your own
   change made unused; mention other dead code or problems you notice — do not fix them in passing. Every changed
   line traces to the request.
4. **Goal-driven execution.** Turn the request into checks before changing code ("fix the bug" → a test that
   reproduces it, then make it pass). For several steps, say `step → verify: <check>` and run each check. Do not
   call it done until the checks ran on the final version.

For a trivial change (a typo, an obvious one-liner) use judgment: same principles, no ceremony.

## Aizen runs end at the gate, not at "done"

In a project with `.aizen/`: start every Aizen skill with `guard.py start` (aizen-build: `state.py init`), tick
`.aizen/runs/<RUN>/sheet.md` only with evidence a script can check, let an independent agent judge, and never
claim the work finished — the guard (`aizen-core/scripts/core/guard.py`) decides at your Stop and tells you
exactly what is still open. Skipping a step is allowed only through `guard.py waive` with a reason and evidence.
Read `.aizen/PROJECT.md` first to understand the project; never edit it — change its sources.

