# Module triển khai và thứ tự build

> DRAFT v3 · TET-0 · 2026-10-06 (v3: số test theo review vòng 1 — `.aizen/runs/TET-0/plan.md` § v3; v2: quyết định owner áp vào) · dùng cho các task build sau (TET-1…). Mỗi dòng là một unit `dev`/`devops` với write set
> rời nhau. Base package Java: `vn.tetticket` (BE = `backend/src/main/java/vn/tetticket`).

## 1. Danh sách

| Unit | Kind | Phủ | Write set | Kiểm (green signal) | Sau |
|---|---|---|---|---|---|
| `infra-local` | infra | môi trường dev | `docker-compose.yml`, `deploy/local/**` | `docker compose up` → PG 16, Redis 7, Kafka (KRaft 1 broker), Mailpit healthy | — |
| `db` | db | data-model.md, `ddl.sql` | `backend/src/main/resources/db/migration/**` | Flyway migrate trên PG Testcontainers xanh; EXCLUDE + CHECK có test vi phạm | infra-local |
| `platform` | be | khung app + `shared` + `identity` | `backend/pom.xml`, `backend/src/main/java/vn/tetticket/{TetTicketApplication.java,shared/**,identity/**}`, `backend/src/main/resources/application*.yml`, `backend/src/test/java/vn/tetticket/{shared,identity}/**` | 3 profile `api`/`wr`/`worker` khởi động; problem+json; idempotency filter (TC-IDEM-01..03); JWT + refresh rotation; xác minh email `POST /auth/verify-email` (R-6); AES-GCM/HMAC CCCD | infra-local |
| `catalog` | be | FR-18, FR-19, FR-20 (CRUD đợt), huỷ chuyến (endpoint, F-1) | `…/catalog/**` (+ test) | CRUD + generate trips + cancel đặt `cancelled_at`; service đọc chuyến/đợt cho kiểm trước giữ chỗ | db, platform |
| `waiting-room` | be | AC-3, FR-01..03, FR-21, BR-10, trần rps (F-4) | `…/waitingroom/**` (+ test) | TC-WR-01..11 | db, platform |
| `inventory` | be | AC-1, AC-2 (nhả), AC-4, AC-5, FR-04..08, publish đợt FR-20 (F-13), job trip-cancel (F-1) | `…/inventory/**` (+ test) | TC-INV-01..12; publish gán chuyến + tạo đúng 800 × chuyến hàng; p95 hold/search đo local | catalog |
| `payment` | be | AC-2, FR-09..12, FR-23 | `…/payment/**` (+ test) | TC-PAY-01..14 với cổng giả (WireMock) + 1 lần VNPay sandbox thật (Q-P1) | inventory |
| `ticketing` | be | FR-13..17, FR-22, email (Mailpit, Q-P4) | `…/ticketing/**`, `…/notification/**` (+ test) | TC-TKT-01..02, TC-RF-01..03, TC-SEC-01 | payment |
| `web` | fe | mọi màn hình khách + admin | `web/**` | build xanh; mỗi màn hình × trạng thái (loading, empty, 403 ADMISSION_REQUIRED, 409 SEAT_UNAVAILABLE, 422 QUOTA_*, hết giờ giữ chỗ) | platform (dựng trên mock từ `openapi.yaml`) |
| `k8s` | infra | hld.md §5–7 | `deploy/k8s/**`, `.github/workflows/**` | `helm lint`/`kubeconform`; deploy lên cluster local (kind) | ticketing |
| `loadtest` | — không phải unit dev: tester trong task `k8s` (F-14) | AC-5, AC-3, AC-1 ở quy mô | `loadtest/**` | k6: p95 search < 300 ms, hold < 500 ms ở λ = 105/s; 0 vi phạm I-1; vượt `active_cap` ≤ λ_max × 5 s, 429 khi vượt C_x / C_other (F-4, R-5); kịch bản Redis-down: tải đọc PG trong trần seat-inventory.md §5 (R-8) | k8s |

Hot file một chủ: `backend/pom.xml` và `application*.yml` thuộc `platform` — các unit khác ghi dependency/property cần thêm
trong report (`HANDOFF`). Migration chỉ `db` viết; unit sau cần cột mới → task mới cho `db`.

Thư viện dự kiến (platform khai báo một lần): Spring Boot 3.x (web, security, data-jdbc + SQL tay cho đường nóng — Q-D2 = J1, Quyết định (owner,
2026-10-06), JPA bị loại; validation, actuator), Flyway, PostgreSQL driver, Spring Data Redis (Lettuce), Spring Kafka, Caffeine, Bucket4j, Testcontainers,
WireMock. Crypto dùng JDK 21 (Ed25519, AES-GCM, HMAC) — không thêm thư viện.

## 2. Thứ tự / wave

```text
W1  infra-local
W2  db ‖ platform                      (seam đã chốt: ddl.sql, openapi.yaml)
W3  catalog ‖ waiting-room ‖ web(1: hàng chờ, search, seatmap trên mock)
W4  inventory
W5  payment
W6  ticketing ‖ web(2: thanh toán, vé, trả vé, admin)
W7  k8s (+ loadtest bởi tester của chính task k8s, F-14)
```

Đường găng: db → catalog → inventory → payment → ticketing. `waiting-room` và `web` chạy song song vì chỉ dựa vào hợp
đồng đã chốt.

## 3. A3 các task build sẽ cần (xin duyệt khi lập plan task đó)

| Unit | Hành động A3 |
|---|---|
| infra-local | kéo image `postgres:16`, `redis:7`, `apache/kafka` (KRaft), `axllent/mailpit` |
| platform…ticketing | tải dependency Maven; Testcontainers kéo image như trên |
| payment | tạo tài khoản VNPay sandbox (owner làm — A4 secret, Q-P1), gọi API sandbox; WireMock cho test tự động |
| web | `npm install` (Next.js, generator client từ OpenAPI) |
| k8s | cài `kind`, `helm`, `kubeconform`; operator CloudNativePG (Q-D3 — Quyết định (owner, 2026-10-06)) |
| loadtest (task `k8s`) | cài `k6` |

Rollback chung: mỗi unit = commit trên nhánh `feature/<TASK>-<unit>`; revert commit; migration có `V*__` mới để đảo, không sửa migration đã chạy.
