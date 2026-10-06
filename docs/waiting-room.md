# Phòng chờ ảo (virtual waiting room)

> DRAFT v3 · TET-0 · 2026-10-06 (v3: sửa theo review vòng 1 R-5, R-6, R-7 — `.aizen/runs/TET-0/plan.md` § v3; v2: quyết định owner áp vào) · phủ: AC-3 · FR-01..03, FR-21 · BR-10 · NFR-03
> Nhãn: `[projected]` capacity.py/loadmix (capacity.md) · `[inferred]` giả định · `[unverified]` chưa kiểm nguồn hôm nay

## 1. Vì sao cần

Không có phòng chờ, 50k người cùng search/seatmap/hold trong phút đầu: ~10,000 rps search+seatmap và burst hold
~1,250 rps `[projected]`. Có phòng chờ, backend chỉ thấy người đã được cho vào: dự kiến 83 rps search, 21 rps hold
`[projected]` (capacity.md §2). Phòng chờ là thứ cho phép giữ tồn ghế trên PG (seat-inventory.md §2).

## 2. So sánh phương án

| Tiêu chí | **A · Hàng chờ đánh số trên Redis (tự làm, deployment riêng)** | B · Hàng chờ ZSET + dequeue tường minh | C · Waiting room ở edge (Cloudflare / Queue-it) |
|---|---|---|---|
| Đúng AC-3 (chặn lưu lượng + thấy vị trí) | có | có | có |
| Độ chính xác vị trí | gần đúng: người bỏ đi vẫn chiếm số (ETA hơi bi quan) | đúng (xoá người bỏ đi) | theo nhà cung cấp |
| Chi phí mỗi lần hỏi trạng thái | 2–3 lệnh Redis O(1) | `ZRANK` O(log n) + dọn dẹp | 0 cho origin |
| Bộ nhớ Redis cho 50k người | ~5 MB `[inferred]` | ~10 MB `[inferred]` | 0 |
| Quy mô làm | 1 module (~4 endpoint, 1 ticker, 1 filter) | như A + job dọn + logic dequeue | cấu hình + verify token của vendor; gói trả phí `[unverified]` |
| Học được (mục tiêu dự án) | cao | cao | thấp |
| Phụ thuộc ngoài | không | không | có, khoá vendor |
| Đảo ngược | dễ | dễ | trung bình |

Bị loại: D · chỉ rate-limit 429 + thử lại — không cho người dùng thấy vị trí (trái AC-3), thưởng cho bot thử lại nhanh.

**Quyết định (owner, 2026-10-06): A** + polling 5/15/30 s (B, C bị loại, giữ trong bảng làm hồ sơ lý do) — đơn giản nhất
mà vẫn đúng AC-3, không phụ thuộc vendor. Chuyển sang C nếu chạy thật trên Internet
và lượt tải trang chờ vượt năng lực ingress (> ~20k rps `[inferred]`).

## 3. Công thức tốc độ cho vào (gắn với năng lực backend)

```text
C_x    = năng lực đo bằng load test của endpoint x ở p95 mục tiêu (rps)        x ∈ {search, seatmap, hold}
n_x    = số request x trung bình mỗi phiên mua (search 6, seatmap 4, hold 1.5)  [inferred — đo lại sau đợt đầu]
u      = hệ số an toàn cho burst đầu phiên = 0.7                                  [inferred]
T      = thời lượng phiên đã vào = 8 phút                                         [inferred]

λ_max  = u × min_x ( C_x / n_x )          -- người/giây được cho vào (Little: tải x = λ × n_x)
A_max  = λ_max × T                        -- số người đang mua tối đa (active_cap)
mỗi tick Δt = 1 s:  k = min( ceil(λ_max × Δt), A_max − active )  ;  served += min(k, seq − served)
```

Với mục tiêu năng lực thiết kế C_search = 1,000, C_seatmap = 600, C_hold = 300 rps `[inferred — mục tiêu, phải đo]`:
λ_max = 0.7 × min(167, 150, 200) = **105 người/s**, A_max = **50,400** `[projected]` → 50k người vào hết trong ~8 phút.
Admin lưu `admit_rate_per_s` và `active_cap` trên `sale_wave` (FR-21) và chỉnh được khi đang bán; mặc định = công
thức trên với số đo load test (`loadtest`, F-14). Không tự động điều chỉnh theo độ trễ ở v1 — admin chỉnh tay (Q-W4 —
Quyết định (owner, 2026-10-06); AIMD bị loại).

**Trần lưu lượng cứng ở `api` (F-4, Q-W6 — Quyết định (owner, 2026-10-06))**. Công thức trên giới hạn *số người*;
để "phía sau chỉ nhận lưu lượng trong ngưỡng" (AC-3) cả khi người đã vào gọi dồn, filter `waitingroom` ở `api` thêm:

- (a) Giới hạn tổng theo endpoint x ∈ {search, seatmap, hold}: C_x rps (1,000 / 600 / 300 `[inferred — mục tiêu, phải đo]`),
  Bucket4j với bucket dùng chung trên Redis → vượt: 429 `RATE_LIMITED` + `retryAfterSeconds`. Redis lỗi → mỗi pod dùng
  bucket cục bộ C_x / số pod `api` `[agent-chosen]` (người đã có token vẫn mua tiếp, §6).
- (a') Một bucket tổng chung cho mọi route khách còn lại không cần token (`GET /orders`, `GET|DELETE /orders/{id}`,
  `POST /orders/{id}/payments`, `GET /tickets/**`, `POST /tickets/{id}/refund`): C_other = 600 rps `[inferred — mục tiêu,
  phải đo]` ≈ λ_max × 4 request/phiên (pay 1 + xem đơn 3) × 1.4 dư = 588 → 600; capacity.py throughput: 2 pod, ~3 kết nối
  DB bận `[projected]` (capacity.md §3). Vượt → 429 `RATE_LIMITED` như (a) (R-5): trại bot N tài khoản × 10 req/s không
  dồn được quá C_other vào PG. IPN (chữ ký, cổng gọi) và `/auth/*` (giới hạn IP ở ingress) không thuộc bucket này.
- (b) Giới hạn theo tài khoản: search và seatmap 2 req/s; endpoint khác giữ 10 req/s (threat-model.md CTL-29).
- (c) `active` chỉ đếm người đã poll nhận token (§4 bước 4): người đã qua `served` nhưng chưa poll, hoặc quay lại muộn,
  chưa bị tính → chấp nhận vượt `active_cap` tối đa λ_max × 5 s (= 525 người với λ_max = 105 `[projected]`); đo trong
  `loadtest`.

## 4. Cơ chế (Redis, đợt `w`)

| Key | Kiểu | Ý nghĩa |
|---|---|---|
| `wr:{w}:seq` | int | `INCR` → số thứ tự của người mới vào hàng |
| `wr:{w}:acct:{accountId}` | string | số của tài khoản, `SET NX` → 1 tài khoản 1 chỗ (BR-10), vào lại trả đúng số cũ |
| `wr:{w}:pre` | set | tài khoản vào trước giờ mở (`opens_at − 30'`..`opens_at`), và sau giờ mở khi `drawn` chưa bật (F-5) |
| `wr:{w}:drawn` | string | cờ: bốc thăm xong (F-5); chưa bật → join vẫn vào `pre` |
| `wr:{w}:tok:{accountId}` | string | admission token đã cấp, TTL = hạn token (F-3) |
| `wr:{w}:served` | int | con trỏ: mọi số ≤ served đã được cho vào |
| `wr:{w}:active` | zset | member = accountId, score = hạn token (ms); `active = ZCOUNT now +inf` |
| `wr:{w}:leader` | string | khoá ticker `SET NX PX 3000` — 1 pod chạy ticker |

1. **Join** (`POST /queue/{waveId}/join`, cần đăng nhập + email đã xác minh — `account.email_verified = true`, không thì
   403 `EMAIL_NOT_VERIFIED` (R-6) — + CAPTCHA Cloudflare Turnstile — Q-W3, Quyết định (owner, 2026-10-06)): một script
   Lua (nguyên tử với bước rút thăm và bật cờ ở 2), theo thứ tự: `acct` đã có → trả lại đúng số đó (R-7, BR-10); `drawn`
   chưa bật (trước giờ mở, hoặc sau giờ mở khi ticker chưa rút xong — F-5) → `SADD pre` (lặp lại vô hại), trạng thái
   `PRE_QUEUE`; `drawn` đã bật → `SET acct NX` với `INCR seq`.
2. **Bốc thăm lúc mở** (Q-W1 — Quyết định (owner, 2026-10-06): pre-queue 30' + bốc thăm; FIFO thuần bị loại): ticker
   từ `opens_at` rút ngẫu nhiên `pre` theo lô, **mỗi lô là một script Lua** `SPOP pre <cỡ lô>` → `INCRBY seq <số rút
   được>` → `SET acct` cho từng tài khoản (R-7): ticker chết giữa chừng thì cả lô chưa xảy ra, không ai bị rút mà mất số;
   khi `pre` rỗng, một script Lua `SCARD pre = 0 → SET drawn 1` (F-5). Trước khi `drawn` bật không ai khác `INCR seq`
   → số 1..P thuộc nhóm bốc thăm, trước mọi người đến sau; vào sớm từng ms không có lợi, bot không thắng nhờ tốc độ.
3. **Ticker** mỗi 1 s (leader): dọn `ZREMRANGEBYSCORE active -inf now`, tính `k` theo §3, `INCRBY served k`.
4. **Status** (`GET /queue/{waveId}/status`): `position = my_no − served`. `≤ 0` → `ADMITTED`: lần đầu cấp admission
   token, `SET tok NX PX <hạn>`, `PEXPIRE acct <hạn>`, `ZADD active exp accountId`; các lần status sau (kể cả tải lại
   trang) trả lại đúng token trong `tok` — không cấp token mới, không `ZADD` lần hai (F-3, Q-W5 — Quyết định (owner,
   2026-10-06)).
5. **Admission token**: JWT HS256 `{sub: accountId, wave, exp = now + 20', jti}` — khoá ký riêng (secret
   `WR_TOKEN_KEY`). Pod `api` kiểm chữ ký + `sub == người gọi` + `wave` khớp, không gọi Redis (rẻ).
   Endpoint bị chặn khi `queue_enabled`: `GET /trips/search`, `GET /trips/{id}/seatmap`, `POST /orders`. Thanh toán và
   xem vé của đơn đã có **không** cần token (người đó đã được cho vào lúc giữ chỗ) — FR-01 đã sửa theo đây (F-2).
6. **Rời sớm**: đơn `PAID` hoặc người dùng bấm "xong" → `ZREM active` → nhả slot cho người sau.
7. **Hết token** (20') → `tok` và `acct` cùng hết hạn → join lại được số mới (cuối hàng). Giữ chỗ đã tạo vẫn còn hạn 15'
   riêng của nó.

## 5. Người dùng thấy vị trí (AC-3)

- Trang chờ là trang tĩnh (Next.js static, cache được) → 50k lượt tải không tạo SSR.
- Polling theo gợi ý server `pollAfterSeconds`: 5 s nếu `position < 1,000`, 15 s nếu `< 10,000`, 30 s còn lại.
  Tải trung bình ~3,333 rps (50k / 15 s) `[projected]` → 3 pod 1 core (capacity.md §3).
- Phản hồi: `{state: PRE_QUEUE|WAITING|ADMITTED, position, etaSeconds, pollAfterSeconds, admissionToken?}`;
  `etaSeconds = position / λ_obs`, λ_obs = trung bình trượt số người được vào/giây trong 60 s.
- Polling thay SSE/WebSocket: 50k kết nối dài vô ích khi số chỉ đổi mỗi giây (Q-W2 — Quyết định (owner, 2026-10-06)).

## 6. Hỏng hóc

- Redis chết → `waiting-room` trả 503 `QUEUE_UNAVAILABLE`, `api` vẫn kiểm token đã cấp (không cần Redis) và từ chối
  người chưa có token → **fail closed**, PG không bị dồn. Redis bật AOF `everysec`: khởi động lại giữ số thứ tự
  (mất tối đa ~1 s ghi `[inferred]`).
- Pod ticker chết → khoá `leader` hết hạn sau 3 s, pod khác nhận.
- Kill switch: admin đặt `admit_rate_per_s = 0` để dừng cho vào (sự cố DB), người đã vào vẫn mua tiếp.
- Redis lỗi khi đang bán → trần rps (§3 a, a') chuyển sang bucket cục bộ mỗi pod; trần tổng vẫn ≤ C_x (và ≤ C_other).

## 7. Test (unit `waiting-room`)

TC-WR-01 join 2 lần cùng tài khoản → cùng số; tài khoản đã được rút số ở lô trước join lại → cùng số đó, không vào lại
`pre` (R-7) · TC-WR-02 ticker không cho `active` vượt `active_cap` · TC-WR-03
`position` giảm đúng `k` mỗi tick · TC-WR-04 pre-queue được cấp số trước người đến sau, thứ tự là hoán vị · TC-WR-05
`POST /orders` thiếu/sai/hết hạn/token của người khác → 403 `ADMISSION_REQUIRED` · TC-WR-06 2 pod ticker → chỉ 1 chạy ·
TC-WR-07 Redis tắt → join 503, gated endpoint từ chối người chưa có token · TC-WR-08 status gọi lại sau `ADMITTED` →
cùng token, `active` không tăng; token hết hạn → join lại nhận số mới (F-3) · TC-WR-09 join sau `opens_at` khi `drawn`
chưa bật → vào `pre`, nhận số ≤ P; join sau khi bật → số > P (F-5); giết ticker giữa các lô → mọi tài khoản hoặc còn
trong `pre` hoặc đã có số, `SCARD pre + số đã gán` không đổi (R-7) · TC-WR-10 vượt C_x rps trên 1 endpoint → 429
`RATE_LIMITED` + `retryAfterSeconds`; 1 tài khoản > 2 req/s search/seatmap → 429 (F-4); tổng route khách còn lại vượt
C_other → 429 (R-5) · TC-WR-11 tài khoản `email_verified = false` join → 403 `EMAIL_NOT_VERIFIED`, không ghi Redis (R-6).
