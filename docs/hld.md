# HLD — kiến trúc tổng thể

> DRAFT v3 · TET-0 · 2026-10-06 (v3: sửa theo review vòng 1 R-1, R-8, R-10, R-11 — `.aizen/runs/TET-0/plan.md` § v3; v2: quyết định owner áp vào) · stack theo ràng buộc owner: Spring Boot (Java 21), Next.js, PostgreSQL, Redis, Kafka, Docker + Kubernetes

## 1. Phương án kiến trúc

| Tiêu chí | **A · Modular monolith, 1 codebase, 3 deployment (api / waiting-room / worker)** | B · Microservices (catalog, inventory, booking, payment, ticketing, queue) | C · Monolith 1 deployment |
|---|---|---|---|
| Đúng AC | có — tx giữ chỗ + hạn mức + đơn trong 1 DB tx | khó: hold + quota + order qua nhiều service → saga, bù trừ | có |
| Cô lập tải | có — hàng chờ (3.3k rps poll `[projected]`, capacity.md §2) và job nền tách pod khỏi `api` | có | không — poll hàng chờ ăn CPU của hold |
| Quy mô làm | 1 repo backend, 8 package module, 3 profile | ≥ 6 service, 6 pipeline, contract giữa service | ít nhất |
| Vận hành | 3 Deployment + HPA | 6+ Deployment, tracing phân tán bắt buộc | 1 |
| Đảo ngược | tách module thành service sau được (ranh giới package) | khó gộp lại | dễ lên A |

**Quyết định (owner, 2026-10-06): A** (Q-S1; B và C bị loại, giữ trong bảng làm hồ sơ lý do): giữ được transaction đơn cho AC-1/AC-4 và vẫn tách tải hàng chờ. Lên B chỉ khi một module cần
scale/deploy độc lập mà profile riêng không đủ.

## 2. Sơ đồ thành phần

```text
 Browser (Next.js)                         Cổng thanh toán (VNPay sandbox)
     │ HTTPS                                   │ IPN (GET, ký HMAC)      ▲ query / refund API
     ▼                                         ▼                         │
 ┌───────────────────── Ingress (NGINX) — TLS, rate limit/IP, route theo path ─────────────────────┐
 │  /            → web (Next.js, trang tĩnh + SSR nhẹ)                                               │
 │  /api/v1/queue/** → waiting-room                                                                  │
 │  /api/v1/**   → api                                                                               │
 └──────────────────────────────────────────────────────────────────────────────────────────────────┘
        │                      │                                   │
        ▼                      ▼                                   ▼
 ┌─────────────┐   ┌──────────────────────┐            ┌──────────────────────────┐
 │ web (2+)    │   │ waiting-room (3+)    │            │ api (4+, HPA theo CPU)   │
 │ Next.js     │   │ Spring Boot profile  │            │ Spring Boot profile api  │
 └─────────────┘   │ wr: join/status,     │            │ identity, catalog,       │
                   │ ticker (leader lock) │            │ inventory, booking,      │
                   └─────────┬────────────┘            │ payment(IPN), ticketing  │
                             │                         │ (đọc), admin             │
                             ▼                         └──────┬─────────┬─────────┘
                   ┌──────────────────────┐                   │ JDBC    │ Redis (snapshot, cache)
                   │ Redis (primary +     │◀──────────────────┼─────────┘
                   │ replica, Sentinel)   │                   ▼
                   │ queue · inv snapshot │        ┌──────────────────────────┐
                   └──────────────────────┘        │ PostgreSQL 16            │
                             ▲                     │ primary + 1 sync replica │
                             │                     └──────────┬───────────────┘
                   ┌─────────┴────────────┐                   │ outbox (poll SKIP LOCKED)
                   │ worker (2+)          │◀──────────────────┘
                   │ sweeper, outbox relay│──────▶ Kafka (3 broker, KRaft) ──▶ worker consumers:
                   │ R1/R2/R3, invariant  │         topic order-events           ticket-issuer, notifier, refunder
                   └──────────────────────┘                                      └──▶ SMTP (Mailpit local, Q-P4)
```

## 3. Luồng chính

```text
UC-01..04 (mở bán)
 web ──join──▶ waiting-room ──INCR/SET NX──▶ Redis
 web ──status (poll 5–30 s)──▶ waiting-room ──▶ ADMITTED + admission token (JWT HS256, 20')
 web ──search/seatmap + token──▶ api ──▶ cache cục bộ 1 s ──▶ Redis inv:{trip} (miss / Redis lỗi → PG, single-flight, seat-inventory.md §5)
 web ──POST /orders + token + Idempotency-Key──▶ api ──1 tx: quota → seats → order──▶ PG ──▶ HSET snapshot

UC-05..06 (thanh toán)
 web ──POST /orders/{id}/payments──▶ api ──▶ PG (attempt) ──▶ redirectUrl ──▶ cổng
 cổng ──IPN──▶ api ──1 tx: verify, dedup, attempt+order+outbox──▶ PG
 worker relay ──▶ Kafka order-events ──▶ ticket-issuer (INSERT ticket ON CONFLICT DO NOTHING) ──▶ outbox TicketsIssued ──▶ notifier (email)

Nền
 worker sweeper 15 s: đơn quá hạn → EXPIRED, nhả mask + quota
 worker trip-cancel mỗi 1': chuyến CANCELLED còn order_item ACTIVE → expire đơn PENDING + hoàn 100% vé VALID (F-1, R-1, seat-inventory.md §4)
 worker R1 5' / R2 khi nhân viên tải CSV / R3: tra cứu, so khớp, hoàn tiền · invariant I-1 mỗi 10'
```

## 4. Module trong codebase backend (ranh giới package)

| Module | Trách nhiệm | Deployment |
|---|---|---|
| `identity` | đăng ký, đăng nhập, JWT, refresh rotation, role | api |
| `catalog` | ga, tuyến, tàu, ghế, giá, chuyến (sinh, huỷ), đợt (CRUD, tham số hàng chờ) | api |
| `inventory` | publish đợt (gán chuyến + tạo `seat_inventory`, F-13), snapshot, search, seatmap, hold (+ kiểm trước F-1), quota, sweeper, job trip-cancel (F-1), invariant | api + worker |
| `waitingroom` | join, status, ticker, cấp token; filter kiểm token + rate limit theo endpoint/tài khoản (F-4) (dùng ở api) | waiting-room (+ filter ở api) |
| `payment` | tạo attempt, IPN, R1/R2 (CSV)/R3, adapter VNPay | api + worker |
| `ticketing` | ticket-issuer, QR Ed25519, trả vé, verify | api + worker |
| `notification` | email (Mailpit local ở v1, Q-P4) | worker |
| `shared` | idempotency filter, outbox, problem+json, crypto CCCD | tất cả |

Một module chỉ gọi module khác qua service public của nó; không truy cập bảng của module khác trừ trong tx giữ chỗ
(`inventory` sở hữu `seat_inventory`, `quota_usage`, `booking_order`, `order_item`) và tx publish đợt (`inventory`
ghi `trip.sale_wave_id`, `sale_wave.status` của `catalog` trong cùng tx tạo `seat_inventory` — F-10, F-13 —
Quyết định (owner, 2026-10-06)). Job trip-cancel (`inventory`) gọi service hoàn vé của `ticketing`, không ghi bảng `ticket`.

## 5. Dữ liệu, HA, sao lưu

- PostgreSQL 16: 1 primary + 1 replica **đồng bộ** (`synchronous_commit = on`) → RPO 0 cho đơn đã commit (NFR-05).
  Trên K8s: operator CloudNativePG (Q-D3 — Quyết định (owner, 2026-10-06); StatefulSet tự dựng / PG ngoài cluster bị loại) — failover tự động. Backup: base backup ngày + WAL archive (PITR 7 ngày).
- Pool: HikariCP 20/pod `api` × 4–10 pod + 10/pod `worker` × 2 → 100–220 kết nối, RAM ~1–9 GB tuỳ `work_mem`
  `[projected]` (capacity.md §4) → thêm PgBouncer chỉ khi > 300 kết nối.
- Redis 7: primary + replica + Sentinel, AOF `everysec`. Mất Redis → fail closed (waiting-room.md §6); snapshot dựng lại từ PG.
- Kafka: 3 broker KRaft, `min.insync.replicas = 2`, topic `order-events` RF 3.

## 6. Hiệu năng (AC-5) — ngân sách

| Đường | Ngân sách p95 | Thành phần |
|---|---|---|
| search | < 300 ms (mục tiêu nội bộ 100 ms) | ingress ~5 ms + JWT/token ~1 ms + Bucket4j Redis (trần endpoint + tài khoản) ~1–2 ms + cache cục bộ/Redis 1–5 ms + tính mask ~1 ms + JSON `[inferred]` |
| hold | < 500 ms (mục tiêu nội bộ 150 ms) | ingress ~5 ms + token ~1 ms + Bucket4j Redis ~1–2 ms + 1 tx PG ~5–20 ms (gồm insert `idempotency_record` ~1 ms, 2–5 upsert quota, ≤ 4 UPDATE ghế, insert đơn + kiểm EXCLUDE gist ~1–3 ms) + commit chờ replica đồng bộ ~1–3 ms cùng vùng + chờ khoá hàng ghế nóng (bên thua nhận 409 sau khi tx thắng commit — chờ ≤ thời gian tx đó) `[inferred]` |

Đo bằng Micrometer histogram theo endpoint (NFR-08); kiểm bằng k6 ở bước `loadtest` (tester trong task `k8s`, F-14).

## 7. Quan sát và vận hành

- Metrics: p50/p95/p99 theo endpoint, 409/422/429 theo mã, độ dài hàng chờ, `served`, `active`, λ_obs, outbox lag,
  số đơn PENDING quá hạn chưa sweep, số `reconciliation_issue` mở. Dashboard Grafana; cảnh báo: outbox lag > 30 s,
  invariant I-1 ≠ 0, IPN chữ ký sai > 10/phút, chuyến `CANCELLED` còn `order_item` `ACTIVE` > 30' sau huỷ (R-1).
- Log JSON có `requestId`; **không log CCCD, token, chữ ký** (masking ở layout).
- Runbook mở bán: scale `api`/`waiting-room` trước 30', bật `queue_enabled`, đặt `admit_rate_per_s` từ load test,
  kill switch = `admit_rate_per_s = 0`.
