# Frontend — React / Next.js

Read after `principles.md` (strict-type rules in §2 apply). Repo ESLint/Prettier/
Tailwind config wins. State management, data fetching, UI kit, styling, router (Pages/App) from .aizen/knowledge/repo;
silent → ask (one question with researched options). Never add a library without approval.

## 1. Spec inputs
Besides docs: UI design (Figma/images), API contract, screen list. Every screen in scope needs its states:
loading · empty · error · success · forbidden. A state missing from the docs → ask, do not invent UI.

## 2. Names & files
Components PascalCase (file per repo: `OrderCard.tsx` or `order-card.tsx`) · hooks `useXxx` · props type
`<Component>Props` · handlers `onXxx` (prop) / `handleXxx` (internal) · Next.js route files by framework convention.

## 3. Components
Function components, one main component per file · presentational components do not call APIs; data and
side effects in hooks/containers/server components per repo pattern · explicit prop types, no blind prop
spreading to DOM · stable `key` (ids, not index for reorderable lists) · no state derivable from props/state;
no `useEffect` to sync derived state · complete effect dependencies and cleanup for listeners/timers/
subscriptions · App Router: server components by default, `"use client"` only for state/effects/events.

## 4. Data & API
Through the repo's API client/service/hooks, never ad-hoc `fetch` in components · types from the contract
(generated if the repo generates) · handle the envelope once in the client layer (unwrap `data`, map
`errorCode` to messages from the docs) · every request handles loading/error/empty · money/time formatted
only at display from minor units / UTC ISO.

## 5. Text, accessibility, safety
i18n for all user-facing text if the repo has i18n · semantic elements (`button`, `a`, `label`), `alt` text,
labelled form fields, keyboard reachable · no `dangerouslySetInnerHTML` with user data · no secrets in client bundles.

## 6. Styling
Repo system only (Tailwind / CSS Modules / styled-components / UI kit); design tokens, no ad-hoc colors;
inline styles only for dynamic values.

## 7. Comments
TSDoc on exported components/hooks naming the screen/spec and IDs:
```tsx
/**
 * Cancel button with confirmation dialog.
 * Screen "Order detail" — UI spec §3.2 (FR-07); visible only when the order is cancellable (BR-02).
 */
export function CancelOrderButton({ order, onCancelled }: CancelOrderButtonProps) {
```

## 8. Manual verification (F6)
Walk each screen state in the browser (or the agent's browser tool) against the design and ACs: happy path,
each documented error message, empty/loading/error states, permission-hidden actions, responsive
breakpoints named in the docs.

## Deeper — Vercel's React and Next.js performance rules (vendored, MIT)

70 rules from Vercel Engineering, ranked by impact; the 52 that matter most are pinned in
`vendor/vercel-react-best-practices/` (`UPSTREAM.md` says what was left out and why). Index:
`references/frontend/vendor/vercel-react-best-practices/guide.md`; one file per rule in its `rules/` folder,
each with a wrong and a right example. Load by prefix for what the change touches:

| Change touches | Rule prefix (impact) |
|---|---|
| sequential awaits, data loading in pages/routes | `async-` (critical) |
| imports, heavy components, third-party scripts | `bundle-` (critical) |
| Server Components, server actions, caching, RSC props | `server-` (high) |
| client fetching, global listeners, localStorage | `client-` (medium-high) |
| re-renders, memo, effects, derived state, transitions | `rerender-` (medium) |
| hydration, long lists, SVG, conditional rendering | `rendering-` (medium) |

Measure first (`references/core/code-quality.md` §3): a rule is applied to a hot path or a measured problem, and
the report says which rule and what number moved.
