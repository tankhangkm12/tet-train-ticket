# Order Service — SRS (rút gọn)

## Mục tiêu
Dịch vụ quản lý đơn hàng cho hệ thống bán lẻ nội bộ.

## Kiến trúc
- Ngôn ngữ: TypeScript, framework NestJS 10, Node 20.
- Kiến trúc phân lớp: controller → service → repository.
- REST JSON, prefix `/api/v1`.

## Hạ tầng
- PostgreSQL 16 (dữ liệu đơn hàng).
- Redis 7 (cache danh mục sản phẩm).
- Logger: pino, log JSON.

## Bảo mật
- Có đăng nhập cho nhân viên; cơ chế xác thực và phân quyền: chưa chốt.

## Quy ước
- Tên biến camelCase, file kebab-case.
- Lỗi trả về dạng `{ "error": { "code", "message" } }`.
