# Thanh toán, phát vé, trả vé

> DRAFT v3 · TET-0 · 2026-10-06 (v3: sửa theo review vòng 1 R-1, R-3, R-4, R-9 — `.aizen/runs/TET-0/plan.md` § v3; v2: quyết định owner áp vào) · phủ: AC-2 · FR-09..17, FR-23 · BR-03, BR-07, BR-08
> Cổng: VNPay sandbox — Quyết định (owner, 2026-10-06), Q-P1: owner tự tạo tài khoản sandbox (secret là A4); test tự động
> bằng cổng giả WireMock, 1 lần chạy thật trên sandbox. Chi tiết giao thức VNPay (tên tham số, mã `RspCode`, HMAC-SHA512, IPN dạng GET,
> API tra cứu/hoàn tiền) là `[unverified]` — kiểm lại tài liệu sandbox của cổng khi build unit `payment`.

## 1. Trạng thái

```text
booking_order:   PENDING_PAYMENT ──IPN ok──▶ PAID
                       │ sweeper/khách huỷ/chuyến huỷ ▲ IPN trễ + lấy lại được ghế (chỉ từ EXPIRED, Q-P2 = L1)
                       ▼                              │
                  EXPIRED | CANCELLED ────────────────┘   (EXPIRED không lấy lại được, hoặc CANCELLED → refund 100%,
                                                           đơn giữ nguyên trạng thái — F-7)
payment_attempt: PENDING ─▶ SUCCEEDED ─▶ REFUNDED | PARTIALLY_REFUNDED
                        └─▶ FAILED | EXPIRED ─▶ SUCCEEDED   (kết quả thành công đến sau, F-6)
order_item:      ACTIVE (đang giữ hoặc đã bán — theo trạng thái đơn) ─▶ RELEASED | REFUNDED
ticket:          VALID ─▶ REFUNDED | USED
refund:          REQUESTED ─▶ SUCCEEDED | FAILED (sau 5 lần thử → reconciliation_issue)
```

Mọi chuyển trạng thái là `UPDATE … SET status = :new WHERE id = :id AND status = :expected` (hoặc `status IN (…)`,
vd. F-6) — 0 hàng = bên khác đã thắng, không làm gì thêm.

## 2. Tạo lượt thanh toán — idempotent (FR-09)

`POST /api/v1/orders/{orderId}/payments` + header `Idempotency-Key` (UUID do client sinh, mỗi lần bấm "Thanh toán").

1. Idempotency chung cho `POST /orders`, `POST /orders/{id}/payments`, `POST /tickets/{id}/refund`: trong cùng tx
   nghiệp vụ, đầu tiên `INSERT INTO idempotency_record (account_id, idem_key, request_hash) …` (PK
   `(account_id, idem_key)`). Request trùng đồng thời chờ trên PK; tx đầu commit → request sau đọc `response_*` đã lưu
   và trả lại y nguyên; tx đầu rollback → request sau làm lại từ đầu. Cùng key khác `request_hash` → 422
   `IDEMPOTENCY_KEY_REUSED`. Dọn bản ghi > 24 h.
2. Điều kiện: đơn của người gọi, `PENDING_PAYMENT`, `expires_at − now() ≥ 2'` (BR-03) — không thì 409
   `ORDER_NOT_PAYABLE`.
3. Một lượt `PENDING` mỗi đơn: unique index một phần `payment_attempt (order_id) WHERE status = 'PENDING'`; đã có →
   trả lại `redirectUrl` cũ.
4. `txn_ref` = mã ngắn duy nhất (`UNIQUE (provider, txn_ref)`), số tiền = `booking_order.total_amount`, hạn thanh
   toán gửi cổng = `expires_at` của đơn → cổng tự chặn trả tiền sau khi giữ chỗ hết hạn (giảm IPN trễ).

## 3. IPN (webhook) — chữ ký + chống trùng (FR-10)

`GET /api/v1/payments/vnpay/ipn?…` (cổng gọi server-to-server). Một transaction:

```text
1. Kiểm chữ ký: HMAC-SHA512(secret, các tham số sắp xếp, bỏ chữ ký) so sánh constant-time → sai: RspCode 97, ghi log an ninh
2. INSERT payment_event (provider, event_key = txn_ref || ':' || provider_txn_no || ':' || response_code, payload)   -- F-8
     ON CONFLICT (provider, event_key) DO NOTHING
   → 0 hàng = đã xử lý (replay/trùng) → RspCode 02, KHÔNG làm gì thêm
3. SELECT payment_attempt WHERE provider = 'VNPAY' AND txn_ref = :ref FOR UPDATE → không có: RspCode 01
4. amount ≠ attempt.amount → RspCode 04 + reconciliation_issue(AMOUNT_MISMATCH)
5. response_code thất bại → attempt PENDING→FAILED; RspCode 00
6. thành công → attempt `status IN ('PENDING','FAILED','EXPIRED')` → SUCCEEDED (F-6: kết quả thành công đến sau khi
   bước 5 đặt FAILED hoặc R1 đặt EXPIRED vẫn được nhận), rồi theo trạng thái đơn (khoá hàng đơn):
     PENDING_PAYMENT → đọc trip.status trong tx (R-1):
         SCHEDULED → PAID, outbox OrderPaid                                     (đường bình thường)
         CANCELLED → expire đơn bằng đúng các câu sweeper (nhả quota + mask, item RELEASED; seat-inventory.md §4),
                     refund 100% lượt này LATE_PAYMENT_UNFULFILLED, outbox RefundRequested (F-1)
     EXPIRED → §4 (IPN trễ, Q-P2 = L1)
     CANCELLED (khách đã tự huỷ) → refund 100% lượt này, đơn giữ CANCELLED, outbox RefundRequested (F-7, Q-P5)
     PAID (lượt khác đã thành công — trả tiền 2 lần) → refund 100% lượt này, outbox RefundRequested
7. COMMIT → RspCode 00. Sau commit: ZREM khỏi wr:{w}:active, HSET snapshot nếu đổi mask.
```

Bước 2 cùng tx với bước 6: nếu xử lý lỗi và rollback thì `payment_event` cũng không được lưu → cổng gọi lại sẽ được xử
lý lại. Replay một IPN hợp lệ cũ chỉ chạm bước 2 và dừng (THR-05). `return URL` (trình duyệt quay về) **không bao giờ**
đổi trạng thái — chỉ hiển thị; frontend đọc `GET /orders/{id}`.

## 4. IPN trễ / trùng sau khi giữ chỗ hết hạn (AC-2, FR-11)

Đơn đã `EXPIRED` (sweeper thắng) nhưng tiền đã trừ. Trong cùng tx IPN, thứ tự khoá order → quota → ghế:

1. Chuyến còn `SCHEDULED` (đọc trong tx; chuyến đã huỷ → đi thẳng bước 3, F-1). Lấy lại hạn mức (như
   seat-inventory.md §3 bước 1–2) và ghế (bước 3, cùng `seg_mask` của `order_item`).
2. Tất cả thành công → `EXPIRED → PAID`, `order_item` `RELEASED → ACTIVE`, outbox `OrderPaid`. Khách vẫn có vé.
3. Có ghế đã bị người khác giữ, hoặc vượt hạn mức → rollback savepoint phần lấy lại, giữ `EXPIRED`, tạo
   `refund(amount = total, reason = LATE_PAYMENT_UNFULFILLED)` + outbox `RefundRequested` + email báo hoàn tiền.

Không bao giờ có hai vé cho một ghế-chặng (AC-1 giữ nguyên vì dùng lại đúng câu UPDATE có điều kiện), không bao giờ
mất tiền khách (hoặc có vé, hoặc có refund). IPN trùng của cùng giao dịch dừng ở §3 bước 2.

Quyết định (owner, 2026-10-06), Q-P2 = **L1** (lấy lại ghế nếu còn, không thì hoàn 100%; L2 "luôn hoàn 100%" bị loại —
bảng so sánh trong `.aizen/runs/TET-0/plan.md`). Nhánh lấy lại **chỉ** cho đơn `EXPIRED`: đơn `CANCELLED` (khách tự
huỷ) mà tiền về sau → luôn hoàn 100% `LATE_PAYMENT_UNFULFILLED`, không lấy lại ghế, không vé (F-7, Q-P5 — Quyết định
(owner, 2026-10-06)).

## 5. Đối soát (FR-12, FR-23)

| Job (`worker`) | Lịch | Làm gì |
|---|---|---|
| R1 tra cứu lượt treo | mỗi 5' | `payment_attempt` `PENDING` tạo > 10' trước → gọi API tra cứu của cổng → đưa kết quả vào **cùng handler §3 từ bước 2** (cùng `event_key` nên IPN đến sau bị chặn trùng). Cổng báo không có giao dịch và đã quá `expires_at + 30'` → `EXPIRED`. |
| R2 so khớp ngày | khi nhân viên tải CSV lên | nhân viên tải CSV báo cáo giao dịch ngày của cổng (`POST /api/v1/admin/reconciliation-reports`, Q-P3 — Quyết định (owner, 2026-10-06); API báo cáo của cổng bị loại vì chưa kiểm) → so với `SUCCEEDED` của ngày đó → lệch thành `reconciliation_issue` (`MISSING_LOCAL`, `MISSING_GATEWAY`, `AMOUNT_MISMATCH`); tải lại cùng ngày chỉ tạo issue chưa có (kind + `txn_ref`) |
| R3 hoàn tiền | consumer `RefundRequested` + quét lại mỗi 5' | gọi API hoàn tiền với `refund.id` làm mã tham chiếu (idempotent phía cổng `[unverified]`); lỗi → thử lại lùi dần, 5 lần → `FAILED` + issue |

Nhân viên xem/xử lý `reconciliation_issue` (`GET/POST /api/v1/admin/reconciliation-issues…`), mọi thao tác vào `audit_log`.
`POST …/{id}:resolve` có 3 `action` (R-3); không action nào chèn `ticket` hay đổi `occupied_mask` trực tiếp:

- `ISSUE_TICKETS` (chỉ issue `MISSING_LOCAL`): đưa giao dịch của cổng (dòng CSV: `txn_ref`, `provider_txn_no`, số tiền,
  mã thành công) vào **cùng handler §3 từ bước 2**, `source = QUERY` → kết quả theo §3/§4: đơn `PENDING_PAYMENT` → `PAID`,
  vé qua outbox; đơn `EXPIRED` → L1 lấy lại ghế hoặc hoàn 100%; đơn `CANCELLED` / chuyến huỷ → hoàn 100%. Ghế đã bán cho
  người khác thì L1 thất bại và hoàn tiền — không bao giờ 2 vé cho một ghế-chặng. Handler trả 01 / 02 / 04 → 409, issue
  vẫn `OPEN`.
- `REFUND` (chỉ issue `MISSING_LOCAL` có `payment_attempt`): attempt → `SUCCEEDED` (tiền đã ở cổng) + `refund` 100% lượt
  đó (`LATE_PAYMENT_UNFULFILLED`, `refund_once_per_attempt`) + outbox `RefundRequested`; đơn giữ nguyên trạng thái.
- `NO_ACTION`: đóng issue kèm `note` (vd. `MISSING_GATEWAY` đã xác minh với cổng).

## 6. Phát vé QR (FR-13, FR-14)

- Outbox: `outbox_event` ghi trong cùng tx đổi trạng thái. Relay (`worker`, mỗi 200 ms): `SELECT … WHERE
  published_at IS NULL ORDER BY id LIMIT 500 FOR UPDATE SKIP LOCKED` → Kafka (`acks=all`, producer idempotent) →
  `published_at = now()`. At-least-once → mọi consumer idempotent.
- Topic `order-events` (key = `order_id`, 12 partition `[inferred]`): `OrderPaid`, `TicketsIssued`, `RefundRequested`.
- Consumer `ticket-issuer`: mỗi `order_item` → `INSERT INTO ticket … ON CONFLICT (order_item_id) DO NOTHING`; QR =
  `base64url(payload) "." base64url(Ed25519(payload))`, payload `{tid, trip, coach, seat, from, to, dep, name, cccd4}`
  — không chứa CCCD đầy đủ. Xong → outbox `TicketsIssued`.
- Soát vé lên tàu **luôn online** qua `POST /staff/tickets:verify` (chữ ký + trạng thái `VALID`, `markUsed`): vé đã trả
  vẫn mang chữ ký hợp lệ và ghế-chặng của nó được bán lại ngay (§7), nên chữ ký một mình không đủ (R-4, CTL-27). Chữ ký
  Ed25519 chỉ chống làm giả/sửa QR; v1 không có soát vé offline (app soát vé ngoài phạm vi, srs.md §1).
- Consumer `notifier`: `TicketsIssued` / refund → email (Mailpit local, không gửi thật — Q-P4, Quyết định (owner,
  2026-10-06); SMTP sandbox ngoài bị loại); chống gửi trùng bằng
  `notification_sent (event_id PK)`.
- Quyết định (owner, 2026-10-06), Q-S2 = **K1** outbox → Kafka → ticket-issuer. Phương án bị loại K2: phát vé ngay
  trong tx IPN (bỏ Kafka khỏi đường phát vé) — đơn giản hơn nhưng trái ràng buộc owner và làm IPN dài hơn; bảng so
  sánh ở plan `## Module scope`.

## 7. Trả vé / đổi vé (FR-15..17)

- `POST /api/v1/tickets/{ticketId}/refund` (`Idempotency-Key`): vé của người gọi, `VALID`, BR-07 (≥ 24 h trước giờ
  chạy tại ga đi) → một tx: ticket `REFUNDED`, `order_item` `REFUNDED`, `seat_inventory.occupied_mask & ~m` (ghế-chặng
  bán lại được ngay), `refund(amount = price × 90%)`, outbox `RefundRequested`. **Không** giảm `quota_usage` (BR-08).
- Nhân viên `POST /api/v1/admin/tickets/{ticketId}/refund` `{reason: TRIP_CANCELLED}` → 100%, bỏ qua BR-07 — chỉ nhận
  `TRIP_CANCELLED` và chỉ khi chuyến đã `CANCELLED`, không thì 409 `REFUND_NOT_ALLOWED` (R-9); khách muốn trả thì tự trả
  theo BR-07 ở dòng trên.
- Huỷ chuyến: job `trip-cancel` gọi đúng service hoàn vé này cho mọi vé `VALID` của chuyến (F-1, seat-inventory.md §4).
- Chính sách trả giữ như trên (Q-S5); đổi vé v1 = trả + mua mới (Q-S4) — Quyết định (owner, 2026-10-06).

## 8. Test (unit `payment`, `ticketing`)

TC-PAY-01 chữ ký sai → 97, không đổi gì · TC-PAY-02 cùng IPN gửi 2 lần (tuần tự và đồng thời) → 1 lần PAID, 1 outbox ·
TC-PAY-03 số tiền lệch → 04 + issue · TC-PAY-04 IPN sau khi EXPIRED, ghế còn → PAID · TC-PAY-05 IPN sau khi EXPIRED,
ghế đã bị giữ → EXPIRED + refund 100% · TC-PAY-06 trả tiền 2 lượt → lượt 2 refund · TC-PAY-07 `POST /payments` cùng
key 2 lần → cùng `redirectUrl`, 1 attempt · TC-PAY-08 R1 thấy thành công trước IPN → PAID; IPN đến sau → 02 ·
TC-PAY-09 attempt đã `FAILED` (bước 5) hoặc `EXPIRED` (R1), sau đó kết quả thành công (`response_code` khác) → attempt
`SUCCEEDED`, đơn `PAID` (hoặc §4 / refund) — không bao giờ tiền trừ mà không vé, không refund (F-6) · TC-PAY-10 đơn
`CANCELLED` rồi tiền về → refund 100%, đơn giữ `CANCELLED`, không vé (F-7) · TC-PAY-11 2 lượt thất bại khác `txn_ref`,
`provider_txn_no` rỗng, cùng `response_code` → 2 `payment_event`, không cái nào bị coi là trùng (F-8) · TC-PAY-12 IPN
trễ cho đơn `EXPIRED` của chuyến đã huỷ → refund 100%, không lấy lại ghế (F-1) · TC-PAY-13 IPN thành công cho đơn
`PENDING_PAYMENT` của chuyến đã huỷ → đơn `EXPIRED`, mask/quota nhả, refund 100%, không `OrderPaid` (R-1) · TC-PAY-14
`ISSUE_TICKETS` cho issue `MISSING_LOCAL` mà ghế đã bán lại → refund 100%, không vé thứ hai; ghế còn → `PAID` + vé qua
outbox (R-3) ·
TC-TKT-01 `OrderPaid` giao 2 lần → 1 vé/item · TC-TKT-02 QR sửa 1 byte → verify sai · TC-RF-01 trả vé < 24 h → 409
`REFUND_NOT_ALLOWED` · TC-RF-02 trả vé → ghế-chặng trống lại, quota không giảm · TC-RF-03 nhân viên trả vé của chuyến
chưa huỷ → 409 `REFUND_NOT_ALLOWED`; `reason` khác `TRIP_CANCELLED` → 400 (R-9).
