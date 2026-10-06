# Code style — what every language shares (v25)

The language- and layer-independent part of how Aizen code reads. Backend and frontend principles
(`references/backend/principles.md`, `references/frontend/principles.md`) add only what is specific to them.
The repository's linter, formatter and written conventions win on style; these rules fill what they leave open.

## 1. Language in code

Identifiers, files, folders, tables, columns, endpoints, routes, events and log messages: **English**.
Comments and docstrings: the owner's chat language unless the repo already uses another. User-facing text
never lives in logic — it comes from a message catalog, enum or i18n bundle, so it can be reviewed and
translated without touching code.

## 2. Comments — four kinds, each in its place

| Kind | Where | Content |
|---|---|---|
| Docstring | every exported function, class, component, hook | what it does or renders, inputs, output, errors it throws |
| Doc reference | top of code implementing a requirement; next to a business rule | `Per LLD order §4.1 (FR-05, BR-02)` |
| Step comments | inside multi-step flows (use cases, handlers, jobs, wizards) | numbered steps matching the doc or PR flow |
| Why | a non-obvious choice: workaround, lock, mandatory order, odd value, partner or browser quirk | the reason, not a restatement |

Never: restating code (`// increment i`), commented-out code, names or dates (git has them), `TODO` without a
task id. Test: deleting the comment loses no information → delete it. A deliberate shortcut gets a `ponytail:`
marker (`code-quality.md` §1).

## 3. Functions

- One job; soft ceiling ~30 lines → extract well-named private helpers (or child components).
- Guard clauses and early return; happy path at the lowest indentation; nesting ≤ 2 levels.
- More than 3 parameters → one named object. No boolean flag parameter that switches behaviour — that is two
  functions sharing a name; split them.
- Never mutate inputs (parameters, props, state).
- Shorter wins only when equally clear: no nested ternaries, no multi-step one-liners, no abbreviations, never
  drop a validation or a state branch for brevity. Unsure → the more readable form.

## 4. Immutability and side effects

`const`/`final`/frozen by default · pure calculations; side effects (DB, HTTP, events, storage, DOM) in the
orchestrating layer or event handler · no module-level mutable state shared across requests or components ·
clock, random and id generators are injected or wrapped so behaviour is reproducible in tests.

## 5. Naming

- Names say what, in the domain's words. Booleans `is/has/can/should`; constants `UPPER_SNAKE`.
- Banned: `data2`, `temp`, `tmp`, `res2`, `obj`, `doStuff`, `handle`/`process` alone, bare `manager`/`helper`,
  `Wrapper`/`Container` with no meaning, catch-all `utils`/`common` files (split by topic: `date.util.ts`,
  `money.util.ts`). If you must open the file to know what it does, rename it.
- File, folder and identifier casing per language: the backend and frontend principles.

## 6. Size and shape

Signals and how to act on them: `references/review/code-standards.md` §Size and shape (the one source).
