# Tồn ghế theo chặng (seat inventory)

> DRAFT v3 · TET-0 · 2026-10-06 (v3: sửa theo review vòng 1 R-1, R-2, R-8 — `.aizen/runs/TET-0/plan.md` § v3; v2: quyết định owner áp vào) · phủ: AC-1, AC-2 (phần nhả ghế), AC-4, AC-5 · BR-01..05 · FR-04..08
> Nhãn: `[projected]` capacity.py/loadmix · `[inferred]` giả định · `[unverified]` hành vi engine theo hiểu biết, chưa đo/đọc lại docs hôm nay

## 1. Mô hình chặng

Tuyến có `n` ga theo thứ tự `idx = 0..n-1` (`route_station`). Đoạn `i` = ga `i` → ga `i+1`. Chặng của vé
`[from_idx, to_idx)` chiếm các đoạn `from_idx .. to_idx-1`, mã hoá thành bitmask:

```text
mask(from, to) = ((1 << to) - 1) XOR ((1 << from) - 1)        -- bit i bật = đoạn i bị chiếm
ví dụ 15 ga (14 đoạn), vé ga 2 → ga 6:  bits 2,3,4,5  = 0b00000000111100 = 60
hai chặng giao nhau  ⇔  maskA & maskB ≠ 0                     -- [2,6) và [5,9): 60 & 480 = 32 ≠ 0 → giao
                                                               -- [2,6) và [6,9): 60 & 448 = 0   → không giao
```

`occupied_mask bigint` → tối đa 63 đoạn (64 ga) / tuyến; CHECK ở `route_station.idx < 64`. Owner nói ~15 ga → dư.

## 2. So sánh phương án

| Tiêu chí (như nhau cho mọi phương án) | **A · Bitmask trên PG + conditional UPDATE** | B · Redis Lua + đồng bộ PG bất đồng bộ | C · Chỉ EXCLUDE constraint trên `order_item` |
|---|---|---|---|
| Đúng AC-1 khi 2 request đồng thời | có — khoá hàng `(trip, seat)`, WHERE đánh giá lại sau khi tx trước commit | có trong Redis; **failover Redis mất ghi đã ack** (replication bất đồng bộ) → 2 người "giữ" cùng ghế, PG phải chặn lần nữa | có — xung đột chèn chờ tx trước rồi lỗi `23P01` `[unverified]` |
| Nguồn sự thật | PG (mask + `order_item` cùng tx) | Redis cho giữ chỗ, PG cho bán → 2 nguồn | PG, 1 nguồn duy nhất (`order_item`) |
| Độ trễ hold (DB) | ~5–20 ms/tx `[inferred]` | ~1 ms Redis + ghi PG sau `[inferred]` | ~5–25 ms/tx (gist) `[inferred]` |
| Trần thông lượng hold | ~1.5–3k tx/s trên 1 primary 8 vCPU `[inferred — phải đo]` | ~50–100k ops/s/shard `[inferred]` | thấp hơn A (gist insert) `[unverified]` |
| Đọc sơ đồ ghế / search | `SELECT seat_id, occupied_mask … WHERE trip_id=?` 800 hàng theo PK; `RETURNING` cho write-through cache | đọc thẳng Redis | gộp `order_item` của chuyến (≤ 11.2k hàng) |
| Nhả ghế hết hạn | `mask & ~m` trong tx sweeper | TTL Redis + đồng bộ PG | đổi `status`, không cần mask |
| Quy mô làm (scope) | 1 bảng + 1 câu UPDATE + sweeper | Lua script, stream đồng bộ, xử lý lệch Redis↔PG, vẫn cần A hoặc C ở PG | 1 constraint + extension `btree_gist` + sweeper |
| Vận hành / rủi ro | mask lệch `order_item` nếu code nhả sai → job kiểm bất biến (§7) | mất dữ liệu khi failover, lệch 2 nguồn | gist bloat dưới ghi đồng thời `[unverified]` |
| Đảo ngược | dễ (thêm C làm lưới, hoặc lên B sau) | khó (đổi nguồn sự thật) | dễ |
| Hợp ràng buộc owner | PG nguồn sự thật, Redis chỉ cache | Redis thành nguồn giữ chỗ — trái "PG nguồn sự thật" | hợp |

**Quyết định (owner, 2026-10-06): A** (Q-I1), cộng **C làm lưới an toàn** (Q-I2 = có, extension `btree_gist`); B bị loại
(giữ trong bảng làm hồ sơ lý do): A là điểm tuần tự hoá nhanh và cho
`RETURNING occupied_mask` để cập nhật cache ngay; EXCLUDE trên `order_item` đảm bảo AC-1 "không bao giờ" ngay cả khi
code nhả mask có lỗi. Với phòng chờ, nhu cầu hold chỉ 21 rps (dự kiến) / 67 rps (cao) `[projected]` → A còn dư
20–70 lần so với trần `[inferred]`.

**Ngưỡng chuyển sang B**: khi nhu cầu hold cần thiết > **1,500 rps kéo dài** `[inferred]`, hoặc load test cho p95
hold > 300 ms / CPU primary > 70% ở `admit_rate` mong muốn. Chỉ khi đó Redis Lua làm lớp lọc trước, PG (A + C) vẫn là
chốt cuối. Không có phòng chờ thì burst hold là 750–2,000 rps `[projected]` → chính phòng chờ giữ ta ở A.

## 3. Cơ chế nguyên tử giữ chỗ (AC-1, AC-4)

**Kiểm trước tx (F-1, Q-I4 — Quyết định (owner, 2026-10-06))**: service đọc chuyến + đợt từ cache 60 s (service public
của `catalog`) và chỉ mở tx khi đủ 3 điều kiện: `trip.status = 'SCHEDULED'`, `sale_wave.status = 'PUBLISHED'`,
`now() ∈ [opens_at, closes_at)`. Chuyến không tồn tại → 404 `NOT_FOUND`; trái 1 trong 3 điều kiện → 409 `WAVE_NOT_OPEN`,
không ghi gì. Cache có thể cũ ≤ 60 s → đơn sinh trong cửa sổ đó sau khi huỷ chuyến do job trip-cancel (§4) vét.

Một transaction READ COMMITTED. Thứ tự khoá cố định, **chung cho mọi đường ghi** (hold, sweeper, trip-cancel, IPN trễ):
**[đơn, nếu tx khoá đơn] → quota (ACCOUNT, rồi CCCD theo `subject` tăng dần) → ghế (seat_id tăng dần)**, và mỗi tx
khoá đơn chỉ xử lý **một** đơn (R-2) → không có chu trình chờ giữa các đường:

```sql
BEGIN;
-- (1) hạn mức tài khoản: n = số vé trong đơn (1..4). INSERT…SELECT…WHERE chặn cả lần chèn đầu.
INSERT INTO quota_usage (sale_wave_id, kind, subject, used)
SELECT :wave, 'ACCOUNT', :account_key, :n WHERE :n <= :max_per_account
ON CONFLICT (sale_wave_id, kind, subject) DO UPDATE
   SET used = quota_usage.used + EXCLUDED.used
 WHERE quota_usage.used + EXCLUDED.used <= :max_per_account
RETURNING used;                                   -- 0 hàng → 422 QUOTA_ACCOUNT_EXCEEDED, ROLLBACK
-- (2) mỗi CCCD khác nhau trong đơn (sắp theo subject): như trên với kind='CCCD', subject = HMAC(cccd), :max_per_cccd
-- (3) mỗi ghế, seat_id tăng dần:
UPDATE seat_inventory
   SET occupied_mask = occupied_mask | :m
 WHERE trip_id = :trip AND seat_id = :seat
   AND occupied_mask & :m = 0
RETURNING occupied_mask;                          -- 0 hàng → 409 SEAT_UNAVAILABLE {seatIds}, ROLLBACK
-- (4)
INSERT INTO booking_order (…, status, expires_at) VALUES (…, 'PENDING_PAYMENT', now() + interval '15 minutes');
INSERT INTO order_item (…, seg_mask, status) VALUES (…, :m, 'ACTIVE');   -- EXCLUDE (Q-I2) là lưới thứ hai
COMMIT;
-- (5) sau commit, best-effort: HSET inv:{trip} seat_id occupied_mask (Redis) — chỉ cho UX, không cho tính đúng
```

Deadlock vẫn có thể do PG phát hiện (40P01) → service thử lại **1 lần**, rồi 409. Serialization không cần
SERIALIZABLE: tính đúng đến từ khoá hàng + WHERE có điều kiện.

### Kịch bản đua (AC-1) — ghế 12, chuyến T, 15 ga

```text
 thời gian   Tx1: khách X, ga 2→6 (m=60)                     Tx2: khách Y, ga 5→9 (m=480)        occupied_mask(T,12)
 t0          BEGIN                                            BEGIN                                 0
 t1          UPDATE … WHERE mask & 60 = 0  → khoá hàng,                                              0 (bản mới 60, chưa commit)
             mask = 60 (chưa commit)
 t2                                                           UPDATE … WHERE mask & 480 = 0
                                                              → hàng đang bị Tx1 khoá → CHỜ
 t3          INSERT order, order_item; COMMIT                                                       60
 t4                                                           PG đọc lại bản mới nhất (60) và đánh
                                                              giá lại WHERE: 60 & 480 = 32 ≠ 0
                                                              → 0 hàng → ROLLBACK → 409 SEAT_UNAVAILABLE  60
 nếu Tx1 ROLLBACK ở t3 → Tx2 đánh giá lại trên bản 0 → thành công, mask = 480.
 nếu Y chọn ga 6→9 (m=448): 60 & 448 = 0 → cả hai thành công, mask = 508 (chặng không giao — đúng nghiệp vụ).
```

Cơ sở: hành vi UPDATE ở READ COMMITTED — chờ tx đang giữ hàng, rồi đánh giá lại WHERE trên phiên bản đã commit
(PostgreSQL docs "Transaction Isolation — Read Committed") `[unverified — đọc lại khi build; test TC-INV-01 chứng minh]`.

## 4. Hết hạn giữ chỗ 15 phút (AC-2)

- `booking_order.expires_at = now() + 15'` lúc giữ. Ghế vẫn tính là chiếm cho tới khi sweeper nhả → nhả trễ tối đa
  bằng chu kỳ sweeper (15 s, Q-I3 — Quyết định (owner, 2026-10-06); 5 s bị loại): ghế trống lại trong khoảng 15:00–15:15.
- Sweeper (deployment `worker`, mỗi 15 s, nhiều replica an toàn nhờ `SKIP LOCKED`): **mỗi đơn một tx ngắn** (R-2),
  lặp tới khi hết đơn quá hạn hoặc đủ 200 đơn/lượt:

```sql
-- một vòng lặp = một tx; SELECT trả 0 hàng → ROLLBACK, dừng lượt
BEGIN;
SELECT id FROM booking_order
 WHERE status = 'PENDING_PAYMENT' AND expires_at < now()
 ORDER BY expires_at LIMIT 1 FOR UPDATE SKIP LOCKED;
-- thứ tự khoá như §3: order → quota (ACCOUNT, CCCD tăng dần) → ghế (seat_id tăng dần)
UPDATE booking_order SET status = 'EXPIRED', updated_at = now() WHERE id = :id AND status = 'PENDING_PAYMENT';
UPDATE quota_usage SET used = used - :n WHERE sale_wave_id = :w AND kind = :k AND subject = :s;   -- CHECK used >= 0
UPDATE seat_inventory SET occupied_mask = occupied_mask & ~:m WHERE trip_id = :t AND seat_id = :seat;  -- seat_id tăng dần
UPDATE order_item SET status = 'RELEASED' WHERE order_id = :id AND status = 'ACTIVE';
COMMIT;
```

- Vì sao một đơn/tx (R-2): tx gom nhiều đơn giữ khoá ghế của đơn k trong lúc chờ quota của đơn k+1, còn hold giữ quota
  rồi chờ ghế → chu trình → 40P01 và rollback cả lô, nhả ghế trễ (AC-2) đúng lúc 15:00–15:15. Một đơn/tx chỉ chờ khoá
  theo thứ tự §3, khoá ghế giữ trong 1 tx ngắn; 200 tx × ~5 ms ≈ 1 s/lượt/replica `[inferred]` < chu kỳ 15 s.
- Đua **sweeper ↔ IPN thành công**: cả hai đổi `booking_order.status` có điều kiện `= 'PENDING_PAYMENT'` dưới khoá
  hàng → đúng một bên thắng. IPN thua (đơn đã `EXPIRED`) → luồng "IPN trễ" (payment.md §4).
- Đua **khách tự huỷ ↔ sweeper**: cùng điều kiện → một bên thắng, bên kia 0 hàng = không làm gì.
- `& ~m` an toàn vì BR-01 đảm bảo không đơn còn hiệu lực nào khác có bit chung trên cùng ghế.
- **Huỷ chuyến (F-1, Q-I4 — Quyết định (owner, 2026-10-06))**: `POST /admin/trips/{id}:cancel` (`catalog`) đặt
  `trip.status = 'CANCELLED', cancelled_at = now()`. Job `trip-cancel` (`inventory`, `worker`, mỗi 1') xử lý mọi chuyến
  `CANCELLED` **còn việc** — theo điều kiện, không theo thời gian (R-1):
  `EXISTS (SELECT 1 FROM order_item WHERE trip_id = :t AND status = 'ACTIVE')` (chỉ mục gist `order_item_no_overlap`
  có `trip_id` đứng đầu, một phần `ACTIVE`, dùng được cho điều kiện này `[inferred]`). Mỗi lượt: (a) expire mọi đơn
  `PENDING_PAYMENT` của chuyến bằng đúng các câu sweeper ở trên, mỗi đơn một tx (điều kiện `trip_id = :t` thay cho
  `expires_at < now()`); (b) gọi service hoàn vé của `ticketing` cho mọi vé `VALID` của chuyến → refund 100%
  `TRIP_CANCELLED` (như nhân viên trả vé, payment.md §7), mỗi vé một tx. Đơn `PAID` chưa có vé (Kafka/issuer chậm) giữ
  item `ACTIVE` → chuyến vẫn thoả điều kiện → lượt sau hoàn vé ngay khi vé được phát, dù muộn bao lâu. Mỗi bước có điều
  kiện trạng thái + `refund_once_per_ticket` → chạy lặp an toàn; chuyến rời khỏi job khi mọi item đã `RELEASED`/`REFUNDED`.
  Vậy job luôn chạy lại ít nhất tới 16' sau huỷ (= 15' giữ chỗ + 60 s cache điều kiện) như owner chốt, và lâu hơn nếu
  còn việc. Cảnh báo: chuyến `CANCELLED` còn item `ACTIVE` > 30' sau huỷ (hld.md §7). IPN cho đơn của chuyến đã huỷ → hoàn
  100%, cả khi đơn còn `PENDING_PAYMENT` (payment.md §3 bước 6) lẫn khi đã `EXPIRED` (payment.md §4).

## 5. Tìm chuyến và sơ đồ ghế (AC-5)

- Snapshot tồn ghế mỗi chuyến trong Redis: `inv:{trip_id}` (HASH `seat_id → occupied_mask`, ~800 trường).
  Ghi: write-through sau commit hold/nhả/bán; nạp lại toàn bộ từ PG khi thiếu key hoặc mỗi 30 s (sửa lệch) — mỗi pod
  nạp **single-flight** theo chuyến (R-8).
- Cache cục bộ (Caffeine) trên mỗi pod `api` cho snapshot: `refreshAfterWrite` 1 s + `expireAfterWrite` 60 s → mỗi chuyến
  chỉ một lần nạp đang chạy trên một pod, trong lúc nạp vẫn trả bản cũ; 60 s cho danh sách chuyến theo (ngày, ga đi, ga
  đến) và sơ đồ toa/ghế (tĩnh theo tàu).
- **Redis lỗi** (R-8): snapshot nạp thẳng từ PG (`SELECT seat_id, occupied_mask … WHERE trip_id = ?`, 800 hàng theo PK)
  qua cùng cache Caffeine, single-flight theo chuyến, chu kỳ nạp nâng lên 5 s khi circuit Redis mở (sơ đồ ghế cũ ≤ 5 s,
  hold vẫn là phán quyết cuối). Tải PG bị chặn ở ≤ min(số pod `api` × số chuyến đang được hỏi / 5 s, C_search + C_seatmap
  = 1,600) lần đọc/s — ví dụ 10 pod × 100 chuyến nóng / 5 s = 200 đọc/s, ~1–2 ms mỗi lần `[inferred]`; đo trong `loadtest`
  (kịch bản Redis-down).
- Search = danh sách chuyến (≤ 20/ngày) × đếm `mask & m = 0` theo hạng trên snapshot: 16,000 phép AND/truy vấn,
  snapshot 6.4 KB/chuyến `[projected]` → CPU vài ms, không đụng PG.
- Seatmap: cùng snapshot, trả `available` cho từng ghế. Có thể cũ ≤ 1 s → hold là phán quyết cuối (409 → refresh).
- **Không** có cột đếm "còn X chỗ" theo chuyến trong PG: một hàng như vậy là hot row mà mọi hold phải ghi.

## 6. Hạn mức (AC-4)

- `quota_usage (sale_wave_id, kind ∈ {ACCOUNT, CCCD}, subject bytea)` PK; `used int CHECK (used >= 0)`.
- `subject` = `account_id` (16 byte) hoặc `HMAC-SHA256(pepper, cccd chuẩn hoá)` — không lưu CCCD thô làm khoá.
- Tăng trong tx giữ chỗ (§3 bước 1–2), giảm khi hết hạn / huỷ giữ chỗ. Vé đã trả **không** giảm (BR-08, Q-S5).
- Đúng khi đồng thời: upsert có điều kiện khoá hàng `(wave, kind, subject)` → 2 đơn cùng CCCD đến cùng lúc được
  tuần tự hoá; đơn thứ hai thấy `used` mới. Tranh chấp chỉ trong phạm vi 1 tài khoản/1 CCCD → không hot row.

## 7. Bất biến và kiểm tra

- Bất biến I-1: với mọi `(trip, seat)`: `occupied_mask = bit_or(seg_mask)` của `order_item.status = 'ACTIVE'`.
  Truy vấn kiểm (job `worker` mỗi 10', báo động nếu ≠ 0 hàng):
  `SELECT … FROM seat_inventory s LEFT JOIN (SELECT trip_id, seat_id, bit_or(seg_mask) m FROM order_item WHERE status='ACTIVE' GROUP BY 1,2) a USING (trip_id, seat_id) WHERE s.occupied_mask <> coalesce(a.m, 0)`.
- Test (unit `inventory`): TC-INV-01 hai tx đồng thời chặng giao → đúng 1 thành công (Testcontainers PG, 2 luồng,
  barrier); TC-INV-02 chặng kề nhau → cả 2 thành công; TC-INV-03 đơn 3 ghế, ghế thứ 3 bận → không ghế nào bị giữ;
  TC-INV-04 sweeper nhả đúng mask + quota; TC-INV-05 sweeper ↔ IPN đua → 1 thắng; TC-INV-06 CCCD thứ 5 → 422;
  TC-INV-07 tài khoản vé thứ 11 → 422; TC-INV-08 200 luồng tranh 1 ghế → 1 thành công, I-1 giữ; TC-INV-09 giữ chỗ khi
  chuyến `CANCELLED` / đợt chưa `PUBLISHED` / ngoài giờ mở → 409 `WAVE_NOT_OPEN`, không hàng nào đổi (F-1);
  TC-INV-10 huỷ chuyến → đơn `PENDING_PAYMENT` thành `EXPIRED` + nhả mask/quota, vé `VALID` có refund 100%; đơn tạo
  trong cửa sổ cache 60 s được lần chạy sau vét; chạy job 2 lần → không refund thứ hai (F-1); đơn `PAID` lúc huỷ, issuer
  dừng > 17' rồi mới phát vé → lượt kế tiếp vẫn hoàn 100%; chuyến hết item `ACTIVE` → job bỏ qua (R-1);
  TC-INV-11 sweeper hết hạn đơn cùng lúc hold tranh quota/ghế chung (2 replica sweeper + hold song song) → không 40P01,
  I-1 giữ (R-2); TC-INV-12 Redis tắt → search/seatmap vẫn trả, số lần đọc PG/chuyến/pod ≤ 1 mỗi 5 s (R-8).
