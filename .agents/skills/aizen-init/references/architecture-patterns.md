# Architecture patterns (stack-agnostic)

Read at steps 2, 5, 6, 7. Use the stack's idiom for each idea (NestJS interceptor, Spring aspect, Go/Express
middleware, FastAPI dependency); the docs' own conventions win over this file.

## Layout (adapt names to the stack)

```text
src/
  config/          # the single config module: load + validate env once
  core/            # interfaces the app owns: Logger, Cache, Repo..., Clock
  infrastructure/  # implementations of core interfaces (pino/zap logger, pg, redis…)
  common/          # cross-cutting: request-id, logging, errors, validation, timing, auth guards
  modules/health/  # /health and /health/ready
  modules/auth/    # login/refresh/me if the plan includes them
  main / app       # composition root: build config → connect infra → wire → listen
tests/
```

## Fail-fast startup (step 5)

```text
main():
  cfg = config.load()                 # missing var → error naming it → exit 1
  for dep in [db, cache, ...]:
      dep.connect(timeout=cfg.X)      # bounded timeout, a few retries at most
      on error: log.error("connect failed", dep=name, err) ; exit 1
  app.listen(cfg.port)
```

`/health` = process alive, no I/O. `/health/ready` = ping each dependency → `{"status":"up|down","checks":{"db":"up",...}}`,
HTTP 503 if any is down. Compose healthcheck uses `/health`.

## Adapters (step 6)

One interface per external tool, owned by `core/`; one implementation in `infrastructure/`; business code and
modules import the interface only; wiring happens only in the composition root. Example:

```ts
interface Logger { info(msg: string, f?: object): void; error(msg: string, f?: object): void; child(f: object): Logger }
class PinoLogger implements Logger { ... }      // only file that imports pino
```

The interface exposes only what the project uses now — no speculative methods.

## Request-id + AOP (step 7)

- **Request-id middleware** (first in chain): `id = header["X-Request-Id"] || uuid()`; store in request context
  (AsyncLocalStorage / contextvars / context.Context / MDC); set response header `X-Request-Id`.
- **Logger** reads the id from context and adds `requestId` to every line by default — callers never pass it.
- **AOP layers** in order: request-id → logging (method, path, status, duration) → auth → validation → handler;
  central error handler maps errors to one JSON shape `{"error":{"code","message","requestId"}}` and never leaks
  stack traces outside dev.
- **Auth**: authentication (verify token → principal in context) separate from authorization (role/permission
  guard per route). Secrets and token TTLs come from config.
