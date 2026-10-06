# Data model

> DRAFT v3 · TET-0 · 2026-10-06 (v3: review vòng 1 R-3 — `.aizen/runs/TET-0/plan.md` § v3; v2: quyết định owner áp vào) · DDL: `ddl.sql` (PostgreSQL 16, chưa chạy thử — `[unverified]` cú pháp tới khi unit `db` áp lên PG thật)
> PostgreSQL là nguồn sự thật cho mọi thứ trừ hàng chờ (Redis) và snapshot cache (Redis, dựng lại được từ PG).

## 1. ERD (ASCII)

```text
 station ─< route_station >─ route ─< segment_fare
                               │
 train ─< seat                 │
   │        │                  │
   └──────< trip >─────────────┘        sale_wave ─< trip
             │                              │
             └─< seat_inventory >─ seat     ├─< quota_usage
                       │                    │
 account ─< booking_order >─────────────────┘
               │      │
               │      └─< payment_attempt ─< payment_event
               │                 │
               └─< order_item ───┼─< refund
                       │         │
                       └── ticket (1:1 order_item) ─< refund (≤ 1 refund/vé, FK F-11)

 plumbing: idempotency_record · outbox_event · notification_sent · reconciliation_issue · audit_log
```

## 2. Bảng và thao tác dùng chúng

| Bảng | Ghi bởi (thao tác) | Đọc bởi |
|---|---|---|
| `station`, `route`, `route_station`, `segment_fare`, `train`, `seat` | admin CRUD (FR-18) | search, seatmap, tính giá (cache 60 s) |
| `trip` | admin sinh chuyến (FR-19), huỷ chuyến (`cancelled_at`, F-1), publish đợt gán `sale_wave_id` (F-10) | search, kiểm trước giữ chỗ (F-1), job trip-cancel |
| `sale_wave` | admin (FR-20, FR-21) | hold (hạn mức), waiting-room (tham số) |
| `seat_inventory` | publish đợt (tạo 480k hàng/đợt, module `inventory` — F-13), hold, sweeper, IPN trễ, trả vé | snapshot loader |
| `quota_usage` | hold (+n), sweeper/huỷ (−n), IPN trễ (+n) | — |
| `booking_order`, `order_item` | hold, sweeper, huỷ, IPN, trả vé, job trip-cancel (F-1) | khách xem đơn, ticket-issuer |
| `payment_attempt`, `payment_event` | tạo thanh toán, IPN, R1 | đối soát |
| `refund` | IPN (trễ/trùng/chuyến huỷ), trả vé, xử lý đối soát `REFUND` (R-3) | R3, nhân viên |
| `ticket` | ticket-issuer, trả vé, soát vé (`USED`) | khách, soát vé |
| `idempotency_record` | mọi POST có `Idempotency-Key` | như trên |
| `outbox_event` | mọi tx đổi trạng thái cần sự kiện | relay |

`order_item` lặp `trip_id/from_idx/to_idx` của đơn vì EXCLUDE constraint chỉ nhìn được cột trong cùng bảng.

## 3. Publish đợt

`POST /admin/sale-waves/{id}:publish` (module `inventory`, F-13 — Quyết định (owner, 2026-10-06)), một tx (F-10, Q-D5 —
Quyết định (owner, 2026-10-06)):

```sql
UPDATE trip SET sale_wave_id = :w
 WHERE departure_date BETWEEN :trip_date_from AND :trip_date_to      -- cột của sale_wave (F-10)
   AND sale_wave_id IS NULL AND status = 'SCHEDULED';
INSERT INTO seat_inventory (trip_id, seat_id)
SELECT t.id, s.id FROM trip t JOIN seat s ON s.train_id = t.train_id
 WHERE t.sale_wave_id = :w
ON CONFLICT DO NOTHING;                                              -- trip đã có hàng thì bỏ qua
UPDATE sale_wave SET status = 'PUBLISHED' WHERE id = :w AND status = 'DRAFT';
```

~480k hàng, ~24 MB heap chưa tính PK index `[projected]` (capacity.md §5, F-12). Không cho publish khi đã quá `opens_at`.

## 4. Luật → ràng buộc (truy vết LLD ↔ DB)

| Luật | Ràng buộc |
|---|---|
| BR-01 không bán trùng ghế-chặng | `UPDATE … WHERE occupied_mask & :m = 0` + `order_item_no_overlap` EXCLUDE (Q-I2) |
| BR-02 `from < to`, ≤ 64 ga | `CHECK (from_idx < to_idx)`, `CHECK (idx BETWEEN 0 AND 63)` |
| BR-04 hạn mức không âm | `quota_usage.used CHECK (used >= 0)`; trần ép bằng upsert có điều kiện |
| 1 hành khách/ghế trong đơn | `UNIQUE (order_id, seat_id)`, `UNIQUE (order_id, cccd_hmac)` |
| 1 vé / order_item | `ticket.order_item_id UNIQUE` |
| refund theo vé trỏ tới vé có thật | FK `refund_ticket_fk` `refund.ticket_id → ticket` (F-11) |
| đợt có khoảng ngày chạy tàu hợp lệ | `sale_wave CHECK (trip_date_to >= trip_date_from)` (F-10) |
| chuyến huỷ ⇔ có `cancelled_at` | `CHECK ((status = 'CANCELLED') = (cancelled_at IS NOT NULL))` (F-1) |
| 1 lượt thanh toán treo / đơn | `payment_attempt_one_pending` unique một phần |
| IPN không xử lý 2 lần | `payment_event UNIQUE (provider, event_key)` |
| 1 refund / vé, 1 refund toàn phần / lượt | `refund_once_per_ticket`, `refund_once_per_attempt` |
| `PAID` ⇔ có `paid_at` | `CHECK ((status = 'PAID') = (paid_at IS NOT NULL))` |
| request lặp không nhân đôi hiệu ứng | `idempotency_record PK (account_id, idem_key)` |

## 5. Kích thước và tăng trưởng `[projected]` (capacity.md §5)

| Bảng | Hàng | Kích thước | Ghi chú |
|---|---|---|---|
| `seat_inventory` | 480k/đợt | 52 B/hàng → ~24 MB heap/đợt chưa tính PK index (F-12) | **giữ lại** sau đợt — FK `order_item → seat_inventory` cần hàng (F-9, Q-D4 — Quyết định (owner, 2026-10-06)); ~4 đợt/năm `[inferred]` |
| `ticket` (36 tháng) | 1.4M / 5.9M / 18M | 0.5 / 2.2 / 8.4 GB (× bloat), 1.5 / 6.7 / 25 GB × 3 bản | dưới 50 GB → **chưa partition** |

Ngưỡng xem lại: bảng nào > 50 GB hoặc `seat_inventory` > 5M hàng → partition theo `sale_wave_id`/tháng.

## 6. Chỉ mục nóng

- `seat_inventory` PK `(trip_id, seat_id)`: hold (điểm), snapshot (range theo `trip_id`).
- `booking_order_expiry` một phần trên `PENDING_PAYMENT`: sweeper quét nhỏ, không bị hàng `PAID` làm phình.
- `outbox_unpublished`, `payment_attempt_pending_age`: một phần, chỉ chứa việc đang chờ.
