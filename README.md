# tet-train-ticket

Hệ thống bán vé tàu Tết trực tuyến giải quyết bài toán nghẽn mạng cao điểm bằng phòng chờ ảo (virtual waiting room), xử lý giữ chỗ đồng thời và thanh toán tích hợp.

## Tech stack
| Thành phần | Lựa chọn | Phiên bản | Ghi chú |
|---|---|---|---|
| Ngôn ngữ | Java | 21 (LTS) | Maven compiler release 21 |
| Framework | Spring Boot | 4.1.1 (GA) | Spring Framework 7, Jackson 3 |
| Cơ sở dữ liệu | PostgreSQL | 16-alpine | Nguồn sự thật, Flyway migrations |
| Cache & Queue | Redis | 7-alpine | Lettuce client, waiting room tokens |
| Message Broker | Apache Kafka | 4.2.1 | KRaft mode (không ZooKeeper) |
| Dev Mailer | Mailpit | v1.21.0 | Local SMTP (1025) & Web UI (8025) |
| Architecture Test | ArchUnit | 1.4.1 | Enforce ranh giới package modular monolith |

## Project structure
```text
tet-train-ticket/
├── .aizen/                      # Quản lý vòng đời dự án và kiểm định chất lượng Aizen
├── backend/                     # Mã nguồn Spring Boot backend
│   ├── src/main/java/vn/tetticket/
│   │   ├── catalog/             # Module danh mục tàu, toa, ga, lịch trình
│   │   ├── identity/            # Module tài khoản, xác thực, phân quyền RBAC
│   │   ├── inventory/           # Module tồn kho chỗ ngồi và sơ đồ tàu
│   │   ├── notification/        # Module thông báo vé và trạng thái
│   │   ├── payment/             # Module thanh toán (VNPay / VietQR)
│   │   ├── shared/              # Thành phần dùng chung (config, security, health, adapters, error)
│   │   ├── ticketing/           # Module đặt chỗ và phát hành vé
│   │   └── waitingroom/         # Module phòng chờ ảo điều tiết lưu lượng
│   └── src/main/resources/
│       ├── db/migration/        # Flyway SQL migrations (V1__initial_schema.sql)
│       └── application.yml      # Cấu hình trung tâm Spring Boot
├── docs/                        # Tài liệu đặc tả yêu cầu (SRS, HLD, OpenAPI, DDL)
├── docker-compose.yml           # Khởi chạy toàn bộ hạ tầng cục bộ
├── Dockerfile                   # Multi-stage Docker build (eclipse-temurin:21)
├── .env.example                 # Mẫu khai báo biến môi trường chuẩn
└── README.md                    # Hướng dẫn chi tiết dự án
```

## Architecture
Kiến trúc Modular Monolith tuân thủ quy tắc DDD / Hexagonal Architecture (Ports & Adapters):
- **Luồng xử lý Request**: `RequestIdFilter` (gán/lan truyền `X-Request-Id` và SLF4J MDC) → `RequestLoggingFilter` (ghi log vào/ra kèm thời gian thực thi) → `JwtAuthenticationFilter` (xác thực token Ed25519) → Security Authorization (RBAC) → Controller Handler → `GlobalExceptionHandler` (RFC 7807 Problem Detail).
- **Adapters behind interfaces**: Tất cả công cụ ngoại vi (`AppLogger`, `CacheClient`, `EventPublisher`, `EmailSender`, `AdminClient`) đều đặt sau Interface và được wire tập trung tại Composition Root [`AdapterConfig.java`](backend/src/main/java/vn/tetticket/shared/adapter/config/AdapterConfig.java).
- **Ranh giới module**: ArchUnit tests (`ModularArchitectureTest`) tự động kiểm tra và chặn các vi phạm phụ thuộc trái phép giữa các module.

## Resources / infrastructure
| Service | Image:tag | Port | Used for | Health check |
|---|---|---|---|---|
| PostgreSQL | `postgres:16-alpine` | 5432 | Lưu trữ dữ liệu quan hệ, giao dịch vé | `pg_isready -U postgres -d tet_ticket` |
| Redis | `redis:7-alpine` | 6379 | Token phòng chờ ảo, cache dữ liệu | `redis-cli ping` |
| Kafka | `apache/kafka:4.2.1` | 9092 | Outbox relay cho order-events | `/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list` |
| Mailpit | `axllent/mailpit:v1.21.0` | 1025 / 8025 | Giả lập gửi nhận email môi trường dev | `wget -q --spider http://localhost:8025/api/v1/info` |
| App Backend | `tet-train-ticket-app:latest` | 8080 | REST API core application | `wget -q --spider http://localhost:8080/health` |

## Environment variables
| Biến môi trường | Bắt buộc | Mặc định / Ví dụ | Mô tả |
|---|---|---|---|
| `SERVER_PORT` | Không | `8080` | Cổng HTTP của ứng dụng backend |
| `SPRING_PROFILES_ACTIVE` | Không | `api` | Spring profile kích hoạt (`api`, `wr`, `worker`) |
| `POSTGRES_HOST` | Có | `localhost` (hoặc `postgres` trong Docker) | Địa chỉ máy chủ PostgreSQL |
| `POSTGRES_PORT` | Không | `5432` | Cổng kết nối PostgreSQL |
| `POSTGRES_DB` | Có | `tet_ticket` | Tên cơ sở dữ liệu PostgreSQL |
| `POSTGRES_USER` | Có | `postgres` | Tài khoản kết nối cơ sở dữ liệu |
| `POSTGRES_PASSWORD` | Có | `postgrespassword` | Mật khẩu tài khoản cơ sở dữ liệu |
| `REDIS_HOST` | Có | `localhost` (hoặc `redis` trong Docker) | Địa chỉ máy chủ Redis |
| `REDIS_PORT` | Không | `6379` | Cổng kết nối Redis |
| `KAFKA_BOOTSTRAP_SERVERS` | Có | `localhost:9092` (hoặc `kafka:9092`) | Danh sách địa chỉ broker Apache Kafka |
| `MAIL_HOST` | Không | `localhost` (hoặc `mailpit` trong Docker) | Địa chỉ SMTP server gửi email |
| `MAIL_PORT` | Không | `1025` | Cổng SMTP server gửi email |
| `JWT_PUBLIC_KEY` | Có | `MCowBQYDK2VwAyEAVmTvQ8njvYoQ1WBKOvbcsrqi9Nvaery5qD2LHTyII+0=` | Ed25519 Public Key (Base64) để verify token |
| `JWT_PRIVATE_KEY` | Chỉ Identity | `MC4CAQAwBQYDK2VwBCIEICyou5y8vnEP0V3Kl61JGlfmho3Hhd6pCWNsqF318zTP` | Ed25519 Private Key (Base64) để ký token |
| `APP_QUEUE_ADMIT_RATE` | Không | `100` | Số lượng người dùng được duyệt qua phòng chờ mỗi giây |

## Sinh cặp khoá Ed25519 cho JWT (JWT_PUBLIC_KEY / JWT_PRIVATE_KEY)
Hệ thống sử dụng chữ ký bất đối xứng EdDSA (Ed25519) định dạng PKCS#8 (Private Key) và X.509 (Public Key) được mã hóa Base64 một dòng. Bạn có thể tự sinh cặp khoá mới bằng các lệnh sau:

### Cách 1: Sử dụng Java / JShell (Khuyên dùng — Chạy trực tiếp trên mọi máy có JDK 21)
**Trên Windows (PowerShell):**
```powershell
"var kp = java.security.KeyPairGenerator.getInstance(`"Ed25519`").generateKeyPair(); System.out.println(`"JWT_PRIVATE_KEY=`" + java.util.Base64.getEncoder().encodeToString(kp.getPrivate().getEncoded())); System.out.println(`"JWT_PUBLIC_KEY=`" + java.util.Base64.getEncoder().encodeToString(kp.getPublic().getEncoded()));`n/exit" | jshell -s -
```

**Trên Linux / macOS (Bash):**
```bash
echo 'var kp = java.security.KeyPairGenerator.getInstance("Ed25519").generateKeyPair(); System.out.println("JWT_PRIVATE_KEY=" + java.util.Base64.getEncoder().encodeToString(kp.getPrivate().getEncoded())); System.out.println("JWT_PUBLIC_KEY=" + java.util.Base64.getEncoder().encodeToString(kp.getPublic().getEncoded()));' | jshell -s -
```

### Cách 2: Sử dụng OpenSSL
**Trên Linux / WSL / Git Bash:**
```bash
# 1. Sinh private key (PKCS#8 Base64)
openssl genpkey -algorithm Ed25519 -out ed25519.pem
grep -v -- "-----" ed25519.pem | tr -d '\n'
echo ""

# 2. Trích xuất public key (X.509 Base64)
openssl pkey -in ed25519.pem -pubout -out ed25519.pub
grep -v -- "-----" ed25519.pub | tr -d '\n'
echo ""
```
Dán giá trị sinh ra vào `.env`:
```env
JWT_PUBLIC_KEY=<chuỗi_public_key>
JWT_PRIVATE_KEY=<chuỗi_private_key>
```

## Configuration
- Cấu hình trung tâm được quản lý bởi [`AppProperties.java`](backend/src/main/java/vn/tetticket/shared/config/AppProperties.java) (`@ConfigurationProperties(prefix = "app")`).
- Tự động nạp file `.env` qua cơ chế SPI `DotenvEnvironmentPostProcessor`.
- Fail-fast khi khởi động: Nếu thiếu biến môi trường bắt buộc (như `JWT_PUBLIC_KEY`), ứng dụng sẽ dừng ngay lập tức và in rõ tên biến vi phạm kèm hướng dẫn khắc phục.

## Run locally
1. Chuẩn bị file môi trường:
```bash
cp .env.example .env
```
2. Khởi chạy toàn bộ hệ thống bằng Docker Compose:
```bash
docker compose up -d
```
3. Kiểm tra trạng thái sẵn sàng của hạ tầng:
```bash
curl http://localhost:8080/health/ready
```

## API
| Method | Path | Auth | Mô tả |
|---|---|---|---|
| `GET` | `/health` | Public | Liveness probe kiểm tra tiến trình ứng dụng |
| `GET` | `/health/ready` | Public | Readiness probe kiểm tra kết nối song song tới PG, Redis, Kafka (<1.5s) |
| `GET` | `/api/v1/profile` | Authenticated | Test slice: Lấy thông tin tài khoản hiện tại |
| `GET` | `/api/v1/admin/dashboard` | `ADMIN` | Test slice: Endpoint yêu cầu quyền Quản trị viên (403 nếu quyền khác) |
| `GET` | `/api/v1/staff/check-in` | `STAFF`, `ADMIN` | Test slice: Endpoint yêu cầu quyền Nhân viên kiểm soát vé |

## Authentication & authorization
- Thuật toán khóa bất đối xứng EdDSA (`Ed25519`): Khóa private chỉ lưu trữ tại module `identity`, các module khác xác thực stateless hoàn toàn qua khóa public.
- Phân quyền theo vai trò (RBAC): `CUSTOMER`, `STAFF`, `ADMIN`.
- Khi chưa đăng nhập: Trả về HTTP 401 Problem Detail (`application/problem+json`).
- Khi không đủ quyền: Trả về HTTP 403 Problem Detail (`application/problem+json`).

## Logging & request-id
- Tự động đọc hoặc sinh UUID mới cho header `X-Request-Id`, phản hồi lại client qua header và đưa vào MDC.
- Format console log chuẩn hóa chứa `[%X{requestId}]`:
```text
2026-10-06T17:37:05.606Z INFO [http-nio-8080-exec-7] [503e1c20-d814-48d2-b97d-4353e965ec48] v.t.shared.logging.RequestLoggingFilter : --> GET /api/v1/admin/dashboard
2026-10-06T17:37:05.615Z INFO [http-nio-8080-exec-7] [503e1c20-d814-48d2-b97d-4353e965ec48] v.t.shared.logging.RequestLoggingFilter : <-- GET /api/v1/admin/dashboard 403 (9ms)
```

## Testing
- Chạy toàn bộ test suite bằng Maven Wrapper:
```bash
cd backend
./mvnw test
```
- Độ bao phủ: Unit tests cho adapters, security filters, JWT signer/verifier, parallel readiness probe, bean validation fail-fast, và ArchUnit modular boundary tests.

## Git workflow
- Mô hình Git Flow: Nhánh chính `main`, nhánh phát triển tích hợp `develop`.
- Mọi tính năng phát triển trên các nhánh `feature/*` tách từ `develop` và merge với cờ `--no-ff`.
- Quy chuẩn commit tuân thủ Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`).

## Troubleshooting
- Ứng dụng thoát khi khởi động: Kiểm tra biến môi trường bắt buộc trong `.env` (`JWT_PUBLIC_KEY`).
- `/health/ready` trả về HTTP 503: Kiểm tra trạng thái các container hạ tầng qua `docker compose ps` hoặc `docker compose logs <service>`.
