# Backend coding principles (v24)

Shared style first: `references/core/code-style.md` (language in code, the four kinds of comments, functions,
immutability, banned names, size signals). This file adds only what is specific to backend code.

## 1. A use case, commented the shared way

```ts
/**
 * Cancels an order on behalf of its buyer.
 * Per LLD order §4.1 (FR-05, BR-02).
 * @throws OrderNotFoundException  order does not exist or is not owned by caller
 * @throws BusinessRuleException    status does not allow cancel (BR-02)
 */
async cancel(orderId: string, actor: Actor): Promise<Order> {
  // Step 1: load with ownership in the query (IDOR protection, 404 instead of 403)
  // Step 2: guard status (BR-02)
  // Step 3: atomic transition PENDING→CANCELLED; 0 rows = concurrent change (D-07)
  // Step 4: enqueue OrderCancelled in outbox inside the same transaction
}
```

## 2. Strict types
| Lang | Rule |
|---|---|
| TypeScript | `strict`; **no `any`** (use `unknown` + narrowing); no `as` casts to silence the compiler |
| Python | full type hints for params and returns; Pydantic/dataclass for structured data; no `dict[str, Any]` payloads; mypy/pyright strict |
| Java | concrete generics, no raw types; **no `Map<String,Object>` DTOs**; `Optional<T>` for absent return values, never return null from public methods |
External data (HTTP, messages, config, partner responses) passes a validation layer before becoming an internal type.

## 3. SOLID as a tool
**S** and **O** first (maintainability). Abstractions (interface, base class, strategy, factory) only
when: wrapping an external dependency · ≥ 2 real implementations exist · the owner asked. Otherwise concrete
classes. Splitting a long function into private helpers is SRP and needs no interface. L: implementations
do not throw new kinds or tighten preconditions. I: small caller-shaped interfaces. D: inner layers own
interfaces, outer layers implement them.

## 4. Errors
- Domain exceptions only; never throw bare `Error`/`Exception`/`RuntimeException`.
- Each carries `errorCode` (UPPER_SNAKE, from one catalog), HTTP status, user message, log context.
- One global handler maps exceptions → envelope. Controllers never try/catch to format errors.
- try/catch only where you really handle (fallback, retry, add context and rethrow). No empty catch,
  no `catch → return null` without logging.
- SDK errors are translated in the adapter; `AxiosError`/`SQLException`/`KafkaJSError` never reach services.

Tree: `AppException` → `ValidationException 400` · `UnauthorizedException 401` · `ForbiddenException 403` ·
`NotFoundException 404` · `ConflictException 409` · `BusinessRuleException 422` · `ExternalServiceException 502/503`.

## 5. Async
One style per codebase (TS async/await; Python async end-to-end, no blocking calls in the loop; Java
blocking or reactive, not both) · run independent work in parallel (`Promise.all`, `asyncio.gather`/
`TaskGroup`, `CompletableFuture.allOf`) · every outbound call has a timeout · retry only idempotent
operations, with backoff and a max.

## 6. Naming
**Files carry a role suffix**; separator follows the language:
| Lang | Style | Examples |
|---|---|---|
| TS | kebab-case | `user-profile.service.ts`, `create-user.dto.ts`, `user.repository.port.ts` |
| Python | snake_case | `user_profile_service.py`, `user_repository_port.py` |
| Java | PascalCase | `UserProfileService.java`, `UserJpaAdapter.java` |

Folders: TS kebab, Python snake, Java lowercase packages; plural for collections (`modules/`, `dto/`).
Identifiers: classes PascalCase; functions/vars camelCase (TS/Java) or snake_case (Python); no `Async` suffix; no `I` prefix on interfaces; Java port
`UserRepository` → adapter `UserRepositoryJpaAdapter`.
Data/contract: tables plural snake_case · FK `<singular>_id` · money columns state unit (`amount_minor`,
`total_vnd`) · time columns `_at` · endpoints plural kebab (`POST /orders/:id/cancel`) · events
`<domain>.<entity>.<action>` · errorCode `USER_NOT_FOUND` · env vars prefixed `DB_URL`, `JWT_SECRET`.
Repository methods read as intent: `findOverdueInvoices()`, `findByIdAndOwner(id, userId)` — not
`findByDueDateLessThanAndStatusNot()`.
