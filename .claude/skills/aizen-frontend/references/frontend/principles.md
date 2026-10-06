# Frontend coding principles (v24)

Shared style first: `references/core/code-style.md` (language in code, the four kinds of comments, functions,
immutability, banned names, size signals). This file adds only what is specific to frontend code.

## 1. Components

- **User-facing strings never live in a component** — they come from the i18n catalog or a strings module.
- No boolean flag props that switch a component's behaviour — that is two components wearing one name.
- No nested ternaries in JSX beyond one level; never drop a state branch for brevity.
- Keep render pure — no fetching, no writing storage, no DOM measurement during render; side effects live in event
  handlers or effects.

```tsx
/**
 * Cancel-order action for the order detail screen.
 * Per shop-frontend.md §4.1 (SCR-12, CMP-30); endpoint EP-08.
 * Renders: confirming · submitting · error-per-code · success.
 */
function useCancelOrder(orderId: string) {
  // Step 1: guard double submit — in-handler, not only the disabled button
  // Step 2: POST EP-08 with the intent's Idempotency-Key (api-contract.md §6)
  // Step 3: on success invalidate the orders list + this detail (api-contract.md §7)
  // Step 4: map each errorCode to its designed state; 403 → permission state, never login redirect
}
```

## 2. Strict types
- `strict` on; **no `any`** (use `unknown` + narrowing); no `as` to silence the compiler; no
  `@ts-ignore` without a why-comment and a task id.
- **API types are generated from `<unit>-api.yaml` or derived from it** — never hand-maintained
  duplicates that drift from the contract.
- Props are typed exactly: no `object`, no index signatures standing in for a real shape, no optional
  props that are actually required.
- Anything crossing the boundary (API response, URL params, `localStorage`, a third-party callback) is
  `unknown` until it is validated or narrowed. A response is not typed just because you wrote a type.

## 3. Composition over abstraction
Prefer composition (children, slots, render props) to configuration flags. Extract a shared component
or hook only when: ≥ 2 real usages exist · it wraps an external dependency · the design system defines
it · the owner asked. A one-usage "reusable" component is a guess about the future that makes today's
code harder to read. Splitting a long component into local sub-components needs no abstraction at all.

## 4. Errors
- Never swallow. No empty `catch`, no `catch → return null` without surfacing something.
- **`errorCode` is the branch, `message` is for humans** (`references/backend/api-contract.md` §3). Every code an endpoint
  can return has a designed state; an unmapped code still renders something honest, never a blank.
- The API client translates transport errors (`AxiosError`, `fetch` rejection, timeout, abort) into the
  app's error shape **once** — raw SDK errors never reach a component.
- An aborted request is not an error: an unmount or a superseded query is discarded silently.
- Every route has an **error boundary** whose fallback is a designed state; a boundary that renders a
  bare string is an unfinished state, not a safety net.
- Throwing to a boundary is for render-time failures. A failed user action is **state**, shown in
  place — not an exception that blanks the screen.

## 5. Async
- One style: `async/await` with an explicit loading state; no floating promises.
- Every request can be **cancelled**, and every effect that starts one cleans it up on unmount or when
  its inputs change — an unguarded `setState` after unmount is a bug and often a leak.
- **Out-of-order responses**: a slower earlier request must never overwrite a newer result. Key the
  result by its input, or abort the previous one.
- Independent work runs in parallel (`Promise.all`), dependent work is sequential and says why.
- Retries only where `references/backend/api-contract.md` §6 allows them, with backoff and a max.
- Effects have correct, complete dependencies; an effect that exists to synchronise state that could be
  derived during render should not exist.

## 6. Naming
| Thing | Style | Examples |
|---|---|---|
| Component files | PascalCase or kebab per repo, consistently | `OrderDetail.tsx` / `order-detail.tsx` |
| Components | PascalCase | `OrderDetail`, `CancelOrderDialog` |
| Hooks | `use` + intent | `useCancelOrder`, `useOrderList` |
| Handlers | `handle<Thing><Event>` / prop `on<Thing><Event>` | `handleSubmitClick`, `onOrderCancel` |
| Booleans | `is/has/can/should` | `isSubmitting`, `canCancel` |
| Constants | UPPER_SNAKE | `MAX_PAGE_SIZE` |
| Routes | plural kebab | `/orders/:id/cancel` |
| Test ids | stable, intent-named | `order-cancel-submit` |
| Public env vars | the framework's public prefix, and **public by definition** | `NEXT_PUBLIC_API_BASE_URL` |

Folders group by **feature**, not by file type: `features/orders/` beats a global `components/` holding
everything. Shared UI lives where the design system says.
