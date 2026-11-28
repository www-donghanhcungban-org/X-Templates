# ADR-0111 — Tách bộ đọc trọng số và chia shard khỏi xt.py

- **Trạng thái:** Đã chấp nhận theo PLAN nâng cấp và D-626.
- **Triển khai:** T-5069.

## Bối cảnh

`xt.py` có 23.668 dòng trên `main` tại `a546e8d6`, bằng trần của repo. T-5075 cần cổng dùng chung cho CLI và steward.

## Yếu tố quyết định

Giữ giao diện CLI và phân hoạch xác định, giảm dòng ở bộ điều phối, giữ Python 3.13 và khả năng chạy với `-I`.

## Phương án

- Giữ hiện trạng. T-5075 phải giải phóng dòng cùng lúc với việc đổi hành vi.
- Tách bộ đọc trọng số và hàm phân hoạch thuần. Test hiện có kiểm được phân hoạch và lỗi đầu vào độc lập với CLI.

## Quyết định

Chuyển phần thuần sang `xt_shard.py`. Giữ phần đọc stdin, ghi kết quả và quản lý tiến trình ở CLI. Giảm trần `xt.py` 42 dòng.

## Hệ quả và xác nhận

Bộ cài và gói phân phối mang theo module mới. Gate T-5069 kiểm phân hoạch, đầu ra CLI, bộ cài và ngân sách dòng.
Đọc lại quyết định khi lớp điều phối shard cần tách thêm. Chính sách bytecode và phạm vi `perf trial` cần bằng chứng riêng trước khi đổi.
