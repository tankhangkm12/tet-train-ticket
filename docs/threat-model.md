# Threat model

> DRAFT v3 · TET-0 · 2026-10-06 (v3: sửa theo review vòng 1 R-3, R-4, R-5, R-6, R-9 — `.aizen/runs/TET-0/plan.md` § v3; v2: quyết định owner áp vào) · STRIDE theo ranh giới và theo luồng tiền/ghế · khả năng/ảnh hưởng là `[inferred]`

## 1. Tài sản và kẻ tấn công

- Tài sản: ghế Tết (khan hiếm, bán lại được giá cao), tiền khách, CCCD (dữ liệu cá nhân — Nghị định 13/2023 về bảo vệ
  DLCN `[unverified]` phạm vi áp dụng), khoá ký QR / IPN / admission token.
- Kẻ tấn công hợp lý: bot đặt chỗ, phe vé (đầu cơ) có nhiều tài khoản và CCCD mượn, người dùng tò mò sửa id, kẻ giả
  IPN, nhân viên lạm quyền.

## 2. Ranh giới tin cậy

```text
 internet ──B1 (ẩn danh, không giới hạn lần thử)──▶ Ingress (TLS, rate limit IP)
    ──B2 (đã đăng nhập: danh tính là claim, kiểm mỗi request)──▶ api / waiting-room
    ──B3 (SQL)──▶ PostgreSQL       ──B4 (Redis, không auth ngoài cluster)──▶ Redis
 cổng thanh toán ──B5 (IPN: chỉ tin chữ ký)──▶ api          worker ──B6──▶ Kafka, SMTP, API cổng
 CI/CD ──B7 (secret lúc build/deploy)──▶ registry, cluster
```

## 3. Mối đe doạ

| THR | Mức | STRIDE · ranh giới | Kịch bản (actor · điều kiện · bước · kết quả) | Kiểm soát |
|---|---|---|---|---|
| THR-01 | Cao | D, S · B1/B2 · queue | Bot mở hàng nghìn phiên vào hàng chờ, chiếm vị trí đầu, đẩy người thật ra sau | CTL-01 đăng nhập + email đã xác minh (`email_verified`, không thì 403 `EMAIL_NOT_VERIFIED`, R-6) trước khi vào hàng + 1 chỗ/tài khoản (BR-10) · CTL-02 CAPTCHA Cloudflare Turnstile khi join (Q-W3 — Quyết định (owner, 2026-10-06)) · CTL-03 bốc thăm pre-queue (không thưởng tốc độ; Q-W1 — Quyết định (owner, 2026-10-06)) · CTL-04 rate limit IP ở ingress (join 5/phút/IP, status 1 req/2 s/tài khoản) |
| THR-02 | Cao | S · B2 · admission | Bot lấy admission token của tài khoản A dùng cho tài khoản B/nhiều máy | CTL-05 token gắn `sub = accountId`, api kiểm `sub == caller`; hạn 20'; 1 token/tài khoản (tải lại trang trả lại đúng token đó, F-3) |
| THR-03 | Cao | E (nghiệp vụ) · luồng hold | Phe vé gom vé bằng nhiều tài khoản, giữ chỗ rồi để hết hạn liên tục để "giam" ghế | CTL-06 hạn mức 4/CCCD + 10/tài khoản (AC-4) tính cả vé đang giữ · CTL-07 vé ghi tên + CCCD, đối chiếu khi lên tàu (BR-09) → bán lại phải đổi tên = trả + mua lại · CTL-08 trả vé không hoàn hạn mức (BR-08) · CTL-09 cảnh báo tài khoản có > 3 đơn hết hạn/đợt (metric, xử lý tay v1) |
| THR-04 | TB | S · B2 · hold | Đầu cơ dùng CCCD bịa (12 số ngẫu nhiên) để vượt 4/CCCD | CTL-10 kiểm định dạng CCCD (mã tỉnh 3 số đầu hợp lệ, giới tính/năm sinh) — không xác minh được với CSDL quốc gia ở v1 (rủi ro owner chấp nhận, Q-S6) · CTL-07 đối chiếu giấy tờ khi lên tàu làm vé CCCD bịa vô dụng |
| THR-05 | Cao | S, T · B5 · IPN | Kẻ tấn công gửi IPN giả "thành công", hoặc phát lại IPN thật cũ để lấy vé cho đơn khác | CTL-11 kiểm HMAC-SHA512 constant-time, secret chỉ trong K8s Secret · CTL-12 `payment_event UNIQUE (provider, event_key)` → phát lại dừng ở bước dedup · CTL-13 `txn_ref` gắn 1 attempt + so số tiền · CTL-14 R1 tra cứu cổng xác nhận chéo |
| THR-06 | Cao | I · B2 · IDOR vé/đơn | Khách đổi `ticketId`/`orderId` trong URL để xem vé (tên, QR, 4 số CCCD) người khác hoặc trả vé của họ | CTL-15 mọi truy vấn khách có `WHERE account_id = :caller` trong repository (không chỉ ở controller) · CTL-16 id là UUID (không đoán được) · CTL-17 trả 404 (không phải 403) cho tài nguyên không thuộc mình · TC-SEC-01 dùng token B gọi mọi endpoint `{orderId}`, `{ticketId}` của A → 404 |
| THR-07 | Cao | T · B2 · giá | Client gửi giá/tổng tiền thấp hơn | CTL-18 giá tính ở server từ `segment_fare`; request không có trường giá (OpenAPI `CreateOrderRequest`) |
| THR-08 | Cao | T · luồng | Huỷ đơn / trả vé 2 lần song song để được hoàn tiền 2 lần | CTL-19 chuyển trạng thái có điều kiện + `refund_once_per_ticket` / `refund_once_per_attempt` unique |
| THR-09 | TB | R, E · B2 · admin | Nhân viên tự hoàn tiền / sửa đối soát không dấu vết; khách tự nâng role | CTL-20 `audit_log` cho mọi thao tác STAFF/ADMIN · CTL-34 nhân viên chỉ hoàn 100% với `reason = TRIP_CANCELLED` cho chuyến đã `CANCELLED` (R-9); xử lý đối soát không chèn vé trực tiếp, `ISSUE_TICKETS` đi qua handler IPN (R-3, payment.md §5) · CTL-21 role chỉ đổi bằng SQL/migration v1, không có trong DTO đăng ký · CTL-22 `/admin/**` kiểm role ở filter + method security |
| THR-10 | Cao | I · B3 · CCCD | Lộ CCCD qua dump DB, log, backup | CTL-23 `cccd_enc` AES-256-GCM, khoá trong Secret (xoay vòng có `key_id` khi cần) · CTL-24 khoá hạn mức là HMAC có pepper, không phải hash thô (12 chữ số → brute-force được) · CTL-25 masking log, API chỉ trả `cccdLast4` |
| THR-11 | Cao | S, T · QR | Làm giả QR / sửa ghế trong QR | CTL-26 QR ký Ed25519, khoá riêng chỉ ở `worker` · CTL-27 soát vé luôn online qua `/staff/tickets:verify` (chữ ký + trạng thái: `REFUNDED` bị từ chối vì ghế-chặng đã bán lại, `USED` chống dùng 2 lần); v1 không soát offline (R-4, payment.md §6) |
| THR-12 | TB | D · B1 · search | Cào search/seatmap ngoài giờ mở bán làm nóng DB; người đã vào gọi dồn vượt năng lực | CTL-28 search không đọc PG (snapshot) · CTL-29 rate limit theo tài khoản ở api (Bucket4j + Redis): search/seatmap 2 req/s, endpoint khác 10 req/s (F-4) · CTL-33 trần tổng theo endpoint = C_x rps, và một trần chung C_other = 600 rps `[inferred]` cho route khách còn lại không cần token (đơn, thanh toán, vé — R-5) → 429 `RATE_LIMITED` + `retryAfterSeconds` (F-4, waiting-room.md §3) |
| THR-13 | TB | S · B2 · phiên | Đánh cắp refresh token | CTL-30 refresh cookie HttpOnly Secure SameSite=Strict, xoay vòng, dùng lại token cũ → thu hồi cả họ · access 15' |
| THR-14 | TB | E · B4 | Pod bị chiếm ghi thẳng Redis (đẩy `served`) | CTL-31 Redis chỉ trong cluster + NetworkPolicy chỉ cho waiting-room/api/worker + mật khẩu ACL |
| THR-15 | TB | T · B7 | Lộ secret qua repo/CI | CTL-32 không secret trong git; gitleaks trong pipeline (`check.py` secrets) · secret qua K8s Secret / sealed |

## 4. Ma trận phân quyền (tóm tắt)

| Endpoint | Ẩn danh | PASSENGER | STAFF | ADMIN | Điều kiện sở hữu |
|---|---|---|---|---|---|
| `/auth/*`, `GET /stations` | ✓ | ✓ | ✓ | ✓ | — |
| `/queue/*`, `/trips/*` | — | ✓ | ✓ | ✓ | token `sub == caller` khi `queue_enabled` |
| `/orders/**`, `/tickets/**` | — | ✓ | — | — | `account_id = caller` (404 nếu khác) |
| `/payments/vnpay/ipn` | chữ ký | — | — | — | chữ ký HMAC hợp lệ |
| `/admin/tickets/*/refund`, `/admin/reconciliation-issues/**`, `/admin/reconciliation-reports`, `/staff/**` | — | — | ✓ | ✓ | audit_log |
| `/admin/stations|routes|trains|trips|sale-waves/**` | — | — | — | ✓ | audit_log |

## 5. Rủi ro owner cần chấp nhận

- R-1 CCCD không xác minh với CSDL quốc gia (THR-04) — giảm bằng đối chiếu khi lên tàu.
- R-2 Một người nhiều tài khoản vẫn vượt 10/tài khoản; chặn cứng là 4/CCCD (thật) — chấp nhận ở v1.

Quyết định (owner, 2026-10-06), Q-S6: chấp nhận R-1 và R-2 ở v1.
