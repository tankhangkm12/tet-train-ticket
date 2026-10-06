# Dự phóng tải và năng lực

> DRAFT v3 · TET-0 · 2026-10-06 (v3: sửa theo review vòng 1 R-5, R-10 — `.aizen/runs/TET-0/plan.md` § v3; v2: quyết định owner áp vào) · Mọi số `[projected]` = tính bằng `capacity.py` (aizen-core v25) hoặc script tải
> (phụ lục `.aizen/runs/TET-0/reports/plan.md`); `[inferred]` = giả định, phải đo lại bằng load test (`loadtest` — tester trong task `k8s`, F-14).

## 1. Đầu vào

| Đầu vào | Thấp / dự kiến / cao | Nguồn |
|---|---|---|
| Người đồng thời lúc mở bán | 30k / **50k** / 80k | owner (50k), biên ±  `[inferred]` |
| Thời gian cho hết hàng ban đầu vào | 120 / 60 / 30 phút | `[inferred]` |
| Phiên mua sau khi vào | 8 phút | `[inferred]` |
| Request mỗi phiên | search 6, seatmap 4, hold 1.5, pay 1, xem đơn 3 | `[inferred]` |
| Poll trạng thái hàng chờ | trung bình 15 s (5–30 s) | thiết kế (waiting-room.md §5) |
| Vé / đơn | 2.5 | `[inferred]` |
| Tàu, ga, ghế | 20 chuyến/ngày, 15 ga, 800 ghế | owner |
| Độ dài một đợt | 30 ngày chạy tàu | `[inferred]` — khớp 480k ghế-chuyến ≈ 500k vé/đợt của owner |

## 2. Tải lên backend `[projected]`

Công thức: λ = người / (phút cho vào × 60); người đang mua A = λ × T (Little); rps_x = A × n_x / T = λ × n_x.

| Kịch bản | Cho vào/s | Đang mua | search rps | seatmap rps | hold rps | pay rps | poll hàng chờ rps | vé/s |
|---|---|---|---|---|---|---|---|---|
| thấp | 4.2 | 2,000 | 25 | 17 | 6 | 4 | 2,000 | 10 |
| dự kiến | 13.9 | 6,667 | 83 | 56 | 21 | 14 | 3,333 | 35 |
| cao | 44.4 | 21,333 | 267 | 178 | 67 | 44 | 5,333 | 111 |
| **không có phòng chờ** (dự kiến) | — | 50,000 | ~10,000 search+seatmap | | ~1,250 burst | | — | — |

Nhạy nhất: số người và thời gian cho vào (tuyến tính). Ý nghĩa: phòng chờ cắt tải hold ~60 lần → giữ tồn ghế trên PG.

## 3. Instance `[projected]` (capacity.py throughput, 2 core/pod, 60% CPU)

| Đường | rps (thấp/dự kiến/cao) | CPU ms/req `[inferred]` | DB ms/req `[inferred]` | Pod | Kết nối DB bận |
|---|---|---|---|---|---|
| search (năng lực thiết kế) | 300 / 1,000 / 3,000 | 4 | 0 (cache) | 1 / 4 / 10 | 0 |
| hold (năng lực thiết kế) | 70 / 300 / 600 | 4 | 15 | 1 / 1 / 2 | 1.1 / 4.5 / 9 |
| route khách còn lại C_other (R-5) | 150 / 600 / 1,200 | 4 | 5 | 1 / 2 / 4 | 0.8 / 3 / 6 |
| poll hàng chờ (1 core/pod) | 2,000 / 3,333 / 5,333 | 0.5 | 0 | 2 / 3 / 5 | 0 |

Chọn năng lực thiết kế: **search 1,000 rps, seatmap 600 rps, hold 300 rps** → λ_max = 105 người/s
(waiting-room.md §3) — gấp ~2.4 lần kịch bản cao. Trần chung route khách còn lại (đơn, thanh toán, vé): **C_other 600 rps**
`[inferred]` = λ_max × 4 request/phiên × 1.4 (waiting-room.md §3 a'). Triển khai tối thiểu: `api` 4 pod (HPA 4→10), `waiting-room` 3 pod
(→5), `worker` 2 pod, mỗi deployment ≥ 2 để chịu mất 1 node.

## 4. PostgreSQL `[projected]` (capacity.py connections)

| Kết nối | Tỉ lệ đang chạy | RAM kết nối |
|---|---|---|
| 100 | 0.1 | 240 MB |
| 150 | 0.2 | 990 MB |
| 250 | 0.4 | 8.69 GB |

Pool: 20/pod `api` × 4–10 + 10/pod `worker` × 2 → 100–220. Kịch bản cao (250, 40% chạy) cần ~9 GB → giữ
`max_connections` ≤ 300, `work_mem` nhỏ (4 MB); vượt → PgBouncer transaction mode. Hold chỉ cần ~5–9 kết nối bận (4.5 ở 300 rps).

Tranh chấp ghế nóng (capacity.py contention, cửa sổ khoá 10 ms): 0.1 / 2 / 20 ghi/s trên cùng 1 ghế → 0.1% / 2% /
18% bị 409, trần 100 commit/s/ghế. 409 là đúng nghiệp vụ (ghế đã có người), không thử lại; UX: làm mới sơ đồ và gợi
ý ghế trống liền kề. Không có hàng nóng toàn chuyến (seat-inventory.md §5).

## 5. Dung lượng `[projected]`

| Bảng | Đầu vào | Kết quả |
|---|---|---|
| `seat_inventory` | 52 B/hàng (capacity.py rowsize, chạy lại 2026-10-06; v1 ghi 60 B — F-12), 480k hàng/đợt | ~24 MB heap/đợt chưa tính PK index — giữ lại sau đợt (F-9: FK từ `order_item`) |
| `ticket` 36 tháng | tài khoản 200k/500k/1M × 0.2/0.33/0.5 vé/tài khoản/tháng (500k vé/đợt × ~4 đợt/năm `[inferred]`) | 1.4M / 5.9M / 18M hàng · 0.5 / 2.2 / 8.4 GB · ×3 bản: 1.5 / 6.7 / 25 GB |
| Redis | 50k vị trí + 600 snapshot × ~20 KB | < 50 MB `[inferred]` |

Ngưỡng: dưới 50 GB/bảng → không partition, không read replica cho đọc.

## 6. Băng thông `[projected]` (capacity.py bandwidth)

| Đường | rps | Payload | Mbit/s |
|---|---|---|---|
| seatmap (dự kiến / cao / năng lực) | 56 / 178 / 600 | 32 KB JSON | 14.7 / 46.7 / 157 |
| poll hàng chờ | 2,000 / 3,333 / 5,333 | 0.3 KB | 4.9 / 8.2 / 13.1 |

Bật gzip trên ingress cho seatmap (JSON lặp lại nén tốt `[inferred]`).

## 7. Kiểm chứng bằng đo (`loadtest` — tester trong task `k8s`, F-14)

- k6: kịch bản mở bán 50k người ảo qua hàng chờ → đo p95 search/hold ở λ = 105/s; ghi CPU ms/req và DB ms/req thật
  thay cho số `[inferred]` ở §3.
- Tìm trần hold: tăng rps tới khi p95 > 300 ms → số đó là C_hold thật, và là ngưỡng chuyển phương án B (seat-inventory.md §2).
- `pg_total_relation_size` sau publish đợt mẫu so với ~24 MB heap (+ PK index).
- F-4: đếm số người đang mua vượt `active_cap` (chấp nhận ≤ λ_max × 5 s = 525 `[projected]`) và số 429 `RATE_LIMITED` theo
  endpoint khi bơm vượt C_x.
