# Code quality — small, clear, fast where it matters (v25)

Applies to every role that writes code, tests, migrations, pipelines or IaC. The repository's linter,
formatter and conventions win on style; these rules win on substance unless the docs say otherwise.

## 1. Write less

1. **Smallest diff that fully solves the task.** No unrelated reformatting, renames or "cleanups".
2. **Climb the reuse ladder; stop at the first rung that solves it.**
   1. Does this need to exist at all? A guess about the future → do not build it (YAGNI).
   2. Does the repo already have it — helper, type, component, query, pattern? Use it (code map, grep).
   3. Does the language's standard library do it?
   4. Does the platform do it natively — a DB constraint, an HTTP header, HTML `<dialog>`, form validation,
      CSS `:has()` / `@container`, a framework feature?
   5. Does a dependency the repo **already has** do it?
   6. Only then write the least custom code. A new dependency is never a rung: it is a decision (item 6).
   Say in one line which rung you stopped at when it is not obvious.
3. **Clean up only your own mess.** Your diff adds no dead code (commented-out blocks, unused
   imports/params/exports, unreachable branches, TODO without an issue ID) and removes what *your change* made
   unused. Dead code that was there before is **mentioned, not deleted** — one row under `## Proposals`
   (`references/dev/out-of-scope.md`), unless the plan asks for the cleanup.
4. **No duplication**: the second copy of logic becomes one function; the third is a finding.
5. **No speculative generality**: no feature, option, abstraction, layer or config key nobody asked for, and
   no abstraction for code used once.
5b. **No defence against the impossible.** Validate where data enters (requests, messages, files, env, partner
   responses — item 8); inside, trust what types and callers already guarantee. A null check on a value the type
   system makes non-null, a `try` around code that cannot throw, a fallback for a state no caller can produce, is
   noise that hides the real error paths.
6. **Dependencies are a decision** (A3 to install; `decisions.md` §6 for options): prefer the standard
   library and what the repo already has.
7. **Mark a deliberate shortcut.** When the simple version is chosen knowingly over a sturdier one (a global
   lock instead of per-user, an in-memory cache instead of Redis), leave one comment where it lives:
   `ponytail: <what was simplified> — upgrade to <the sturdier version> when <measurable trigger>`.
   It is debt with an exit condition, not an apology; `grep -rn "ponytail:"` lists the debt.
8. **Never simplified away**: input validation at boundaries, error handling that prevents data loss,
   authorization, secrets handling, accessibility. Least code means least *unnecessary* code.

### Before you hand it over — two questions

- **Does every changed line trace to the request?** (a plan id, a finding id, or the owner's words). A line that
  does not — a drive-by rename, reformat, "improvement" of adjacent code or comments — comes out of the diff.
- **Would a senior engineer call this overcomplicated?** If 200 lines could be 50 without losing a requirement,
  a validation or an error path, rewrite it as 50.

## 2. Write clearly

- Names say what, in the domain's words; functions do one thing; early returns over nesting.
- Size signals (function, file, class, module, component): `references/review/code-standards.md` §Size and
  shape — the one source; crossing a line forces a question, not an automatic split.
- Language-independent style (comments, functions, naming): `code-style.md`.
- Types precise at boundaries; errors handled where they can be handled, typed/coded where they cross a
  boundary; no swallowed exceptions.
- Comments explain *why* (a workaround, a business rule with its ID), never *what*.

## 3. Fast where it matters — measured

- **Correct and simple first.** Optimise only a path that is hot (profile, APM, `EXPLAIN`, bundle report)
  or that a requirement's number (NFR) says is too slow.
- Avoid the known scale traps from the start: N+1 queries, unbounded lists or page sizes, work inside
  loops that can be batched, unnecessary re-renders on large lists, blocking I/O on hot paths, loading a
  whole table/file into memory, missing timeouts.
- An optimisation ships with its before/after numbers (`numbers.md`) and keeps readability; a clever
  line that saves nothing measurable is a defect.

## 4. Self-check before handing over

```
[ ] diff contains only the task          [ ] no dead / duplicated code
[ ] every changed line traces to the task [ ] no pre-existing code "improved" in passing
[ ] lowest ladder rung, or said why not  [ ] names and sizes within the signals
[ ] errors handled, nothing swallowed    [ ] no scale trap on a hot path
[ ] lint + format + type-check clean     [ ] tests for the behaviour changed
[ ] optimisation claims have numbers     [ ] shortcuts carry a `ponytail:` trigger
[ ] Deviations line written
```

`reviewer` judges the same list (review-code §quality); a failed item is a finding, not a style note.
