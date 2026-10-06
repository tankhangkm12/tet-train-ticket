# SRS — Hệ thống bán vé tàu Tết online

> DRAFT v3 · TET-0 · 2026-10-06 (v3: sửa theo review vòng 1 R-5, R-6, R-9 — `.aizen/runs/TET-0/plan.md` § v3; v2: quyết định owner áp vào) · nguồn: `.aizen/runs/TET-0/input.md` (yêu cầu nguyên văn của owner)
> Nhãn: `[owner]` owner nói · `[inferred]` giả định của planner (cần owner xác nhận) · `[projected]` tính bằng capacity.py

## 1. Mục tiêu và phạm vi

Mục tiêu: bán vé tàu Tết theo đợt, chịu được đỉnh 50k người đồng thời lúc mở bán mà không bán trùng ghế,
không lệch vé khi thanh toán, và người dùng thấy rõ vị trí trong hàng chờ. Dự án học, làm như production. `[owner]`

| Trong phạm vi v1 `[owner]` | Ngoài phạm vi v1 `[owner]` |
|---|---|
| tìm chuyến; sơ đồ ghế theo chặng; giữ chỗ 15'; thanh toán 1 cổng sandbox; vé điện tử QR; phòng chờ ảo; đổi/trả cơ bản; admin lịch tàu + đợt mở bán | app mobile, bán tại quầy, khuyến mãi, khách hàng thân thiết, đa ngôn ngữ |

Ngoài phạm vi thêm `[inferred]`: app soát vé tại cửa (chỉ có API verify QR cho nhân viên), SMS OTP, hoá đơn điện tử,
nhiều cổng thanh toán, một vé nối 2 tàu.

## 2. Actor

| Actor | Mô tả | Xác thực |
|---|---|---|
| ACT-1 Hành khách | tài khoản cá nhân, mua ≤ 10 vé/đợt, ≤ 4 vé/CCCD/đợt | email + mật khẩu, JWT |
| ACT-2 Nhân viên (`STAFF`) | trả vé bắt buộc (tàu huỷ), xem đơn, soát QR, xử lý lệch đối soát | như trên + role |
| ACT-3 Quản trị (`ADMIN`) | ga, tuyến, đoàn tàu, giá chặng, chuyến, đợt mở bán, tham số hàng chờ | như trên + role |
| ACT-4 Cổng thanh toán | gọi IPN báo kết quả; được gọi để tra cứu / hoàn tiền | chữ ký HMAC |
| ACT-5 Bot / đầu cơ | kẻ tấn công — xem `threat-model.md` | — |

## 3. Use case

| UC | Actor | Luồng chính | FR |
|---|---|---|---|
| UC-01 Vào hàng chờ | ACT-1 | đăng nhập (email đã xác minh, R-6) → trang đợt → nhận số thứ tự → xem vị trí/ETA → nhận admission token | FR-01..03 |
| UC-02 Tìm chuyến | ACT-1 | ga đi, ga đến, ngày → chuyến + số chỗ trống theo hạng | FR-04 |
| UC-03 Chọn ghế theo chặng | ACT-1 | sơ đồ ghế của chuyến cho chặng (đi→đến) | FR-05 |
| UC-04 Giữ chỗ | ACT-1 | ≤ 4 ghế + tên/CCCD từng khách → đơn `PENDING_PAYMENT`, hết hạn sau 15' | FR-06..08 |
| UC-05 Thanh toán | ACT-1, ACT-4 | tạo lượt thanh toán → cổng → IPN → đơn `PAID` | FR-09..12 |
| UC-06 Nhận vé QR | ACT-1 | xem vé có QR ký số; email xác nhận | FR-13..14 |
| UC-07 Trả vé | ACT-1, ACT-2 | trả theo chính sách → nhả chặng ghế → hoàn tiền | FR-15..16 |
| UC-08 Đổi vé | ACT-1 | v1: trả + mua mới (Q-S4 — Quyết định (owner, 2026-10-06)) | FR-17 |
| UC-09 Lịch tàu | ACT-3 | ga, tuyến (ga có thứ tự), tàu + ghế, giá đoạn, sinh chuyến | FR-18..19 |
| UC-10 Đợt mở bán | ACT-3 | tạo đợt (khoảng ngày chạy tàu) → publish (gán chuyến + tạo tồn ghế) → mở/đóng, chỉnh hàng chờ | FR-20..21 |
| UC-11 Soát vé | ACT-2 | quét QR → chữ ký + trạng thái | FR-22 |
| UC-12 Lệch đối soát | ACT-2 | xem và xử lý bản ghi lệch | FR-23 |

## 4. Yêu cầu chức năng

| FR | Yêu cầu | AC | Thiết kế |
|---|---|---|---|
| FR-01 | Đợt bật `queue_enabled` → API đặt vé của đợt (search, seatmap, `POST /orders`) đòi admission token; tạo thanh toán và xem đơn/vé đã có **không** cần token (F-2 — Quyết định (owner, 2026-10-06)) | AC-3 | waiting-room.md §4 |
| FR-02 | Người dùng thấy vị trí + ETA, cập nhật ≤ 30 s | AC-3 | waiting-room.md §5 |
| FR-03 | Tốc độ cho vào theo công thức năng lực, không vượt `active_cap`; trần rps cứng theo endpoint = C_x, và C_other chung cho route khách còn lại → 429 `RATE_LIMITED` (F-4, R-5) | AC-3 | waiting-room.md §3 |
| FR-04 | Tìm chuyến theo (ga đi, ga đến, ngày): giờ đi/đến, chỗ trống theo hạng cho đúng chặng | AC-5 | seat-inventory.md §5 |
| FR-05 | Sơ đồ ghế (chuyến, chặng): ghế trống khi không giao chặng đã giữ/bán | AC-1 | seat-inventory.md §5 |
| FR-06 | Giữ 1..4 ghế/đơn, tất cả-hoặc-không; giao chặng → `SEAT_UNAVAILABLE`; chuyến không `SCHEDULED` / đợt không `PUBLISHED` / ngoài `[opens_at, closes_at)` → 409 `WAVE_NOT_OPEN` (F-1) | AC-1 | seat-inventory.md §3 |
| FR-07 | Đơn giữ chỗ tự hết hạn sau 15' nếu chưa trả tiền, ghế được nhả | AC-2 | seat-inventory.md §4 |
| FR-08 | Vé gắn tên + CCCD; ≤ 4 vé/CCCD/đợt, ≤ 10 vé/tài khoản/đợt | AC-4 | seat-inventory.md §6 |
| FR-09 | Tạo lượt thanh toán idempotent (`Idempotency-Key`) | AC-2 | payment.md §2 |
| FR-10 | IPN kiểm chữ ký, số tiền, chống trùng | AC-2 | payment.md §3 |
| FR-11 | IPN trễ (đơn `EXPIRED`) → lấy lại ghế nếu còn, không thì hoàn 100% tự động (Q-P2 = L1); đơn khách đã huỷ (`CANCELLED`) → luôn hoàn 100% (F-7, Q-P5) — Quyết định (owner, 2026-10-06) | AC-2 | payment.md §4 |
| FR-12 | Đối soát: tra cứu lượt treo + so file đối soát ngày (CSV nhân viên tải lên, Q-P3 — Quyết định (owner, 2026-10-06)) | AC-2 | payment.md §5 |
| FR-13 | Đơn `PAID` → phát vé (1 vé/order_item, idempotent), QR ký Ed25519 | — | payment.md §6 |
| FR-14 | Email xác nhận vé, không chặn luồng thanh toán | — | hld.md §3 |
| FR-15 | Hành khách trả vé theo BR-07 → nhả chặng ghế → hoàn tiền | — | payment.md §7 |
| FR-16 | Nhân viên trả vé bắt buộc (chỉ khi chuyến đã huỷ, R-9), hoàn 100%; huỷ chuyến → job expire đơn `PENDING_PAYMENT` của chuyến + hoàn 100% mọi vé `VALID` (F-1) | AC-2 | payment.md §7, seat-inventory.md §4 |
| FR-17 | Đổi vé v1 = trả + mua mới (Q-S4 — Quyết định (owner, 2026-10-06)) | — | plan Q-S4 |
| FR-18 | Admin CRUD ga, tuyến, tàu + ghế, giá đoạn × hạng | — | data-model.md |
| FR-19 | Admin sinh chuyến theo tuyến × tàu × khoảng ngày | — | openapi `/admin/trips:generate` |
| FR-20 | Admin tạo đợt (gồm `tripDateFrom..tripDateTo`); publish (cùng tx) gán chuyến chạy trong khoảng đó vào đợt rồi tạo `seat_inventory` (F-10, F-13) | AC-4 | data-model.md §3 |
| FR-21 | Admin chỉnh `admit_rate_per_s`, `active_cap` khi đang bán | AC-3 | waiting-room.md §3 |
| FR-22 | Nhân viên kiểm QR: chữ ký hợp lệ + vé `VALID` | — | openapi `/staff/tickets:verify` |
| FR-23 | Nhân viên xem/xử lý lệch đối soát | AC-2 | payment.md §5 |

## 5. Luật nghiệp vụ

| BR | Luật | Ép ở đâu |
|---|---|---|
| BR-01 | Một ghế của một chuyến không thuộc hai đơn còn hiệu lực có chặng giao nhau | `UPDATE … WHERE occupied_mask & :m = 0` + EXCLUDE `order_item_no_overlap` (Q-I1 = A, Q-I2 = có — Quyết định (owner, 2026-10-06)) |
| BR-02 | Chặng = các đoạn liên tiếp `[from_idx, to_idx)` theo thứ tự ga; `from_idx < to_idx` | CHECK |
| BR-03 | Giữ chỗ 15'; chỉ tạo lượt thanh toán khi còn ≥ 2' `[inferred]` | `expires_at`, sweeper |
| BR-04 | ≤ 4 vé/CCCD/đợt, ≤ 10 vé/tài khoản/đợt; đếm vé đang giữ + đã bán | upsert có điều kiện `quota_usage` |
| BR-05 | Một đơn ≤ 4 vé, cùng chuyến, cùng chặng `[owner]` (Q-S3 — Quyết định (owner, 2026-10-06)) | validation + CHECK |
| BR-06 | Giá = Σ giá đoạn theo hạng ghế; tiền `bigint` VND | `segment_fare` |
| BR-07 | Trả vé ≥ 24 h trước giờ chạy tại ga đi, phí 10%; < 24 h không trả; tàu huỷ hoàn 100% `[owner]` (Q-S5 — Quyết định (owner, 2026-10-06): giữ như docs) | service + test |
| BR-08 | Vé đã trả không hoàn lại hạn mức đợt (chống vòng mua-trả) `[owner]` (Q-S5 — Quyết định (owner, 2026-10-06)) | refund không giảm `quota_usage` |
| BR-09 | Vé in tên + 4 số cuối CCCD; đối chiếu giấy tờ khi lên tàu | QR payload |
| BR-10 | Một tài khoản chỉ có 1 vị trí trong hàng chờ của một đợt | Redis `SET NX` |

## 6. Yêu cầu phi chức năng

| NFR | Yêu cầu | Số | Cơ chế |
|---|---|---|---|
| NFR-01 (AC-5) | p95 tìm chuyến ở tải đỉnh | < 300 ms | snapshot mask trong Redis + cache cục bộ, không đọc PG (seat-inventory.md §5) |
| NFR-02 (AC-5) | p95 giữ ghế ở tải đỉnh | < 500 ms | 1 transaction PG: ≤ 4 UPDATE theo PK + 2 upsert hạn mức, không hot row toàn chuyến |
| NFR-03 (AC-3) | Lưu lượng vào backend | ≤ `active_cap` người đang mua (vượt ≤ λ_max × 5 s chấp nhận, đo trong loadtest) và ≤ C_x rps mỗi endpoint x, ≤ C_other rps cho route khách còn lại (R-5) | waiting-room.md §3 (F-4) |
| NFR-04 | Đỉnh người dùng đồng thời | 50k `[owner]` | capacity.md |
| NFR-05 | Không mất đơn đã trả tiền khi hỏng primary | RPO 0 với commit | PG synchronous replica (hld.md §5) |
| NFR-06 | Khả dụng trong giờ mở bán | 99.9% `[inferred]` | ≥ 2 replica mỗi deployment, PG HA |
| NFR-07 | CCCD | mã hoá khi lưu, không log | AES-GCM + HMAC (threat-model.md) |
| NFR-08 | Quan sát | p95 theo endpoint, độ dài hàng chờ, tốc độ cho vào, số 409 | Micrometer → Prometheus |

## 7. AC → cơ chế

| AC | Cơ chế | Tài liệu |
|---|---|---|
| AC-1 | conditional UPDATE trên bitmask chặng; khoá hàng + đánh giá lại WHERE | seat-inventory.md §3 |
| AC-2 | `expires_at` + sweeper `SKIP LOCKED`; chuyển trạng thái có điều kiện; IPN dedup `UNIQUE`; IPN trễ; đối soát | seat-inventory.md §4, payment.md |
| AC-3 | hàng chờ đánh số (Redis `INCR`), con trỏ cho vào theo công thức, admission token ký HMAC; trần rps theo endpoint (Bucket4j/Redis → 429) | waiting-room.md |
| AC-4 | `quota_usage` upsert có điều kiện trong cùng transaction giữ chỗ; khoá = HMAC(CCCD) | seat-inventory.md §6 |
| AC-5 | search từ snapshot Redis; hold 1 transaction ngắn; số trong capacity.md | capacity.md |
