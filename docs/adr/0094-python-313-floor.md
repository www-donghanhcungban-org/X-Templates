# ADR-0094: Công cụ X-Templates chạy trên CPython 3.13 trở lên

- **Trạng thái:** Đã chấp nhận ngày 2026-11-23 (D-545; chủ dự án: "hỗ trợ từ 3.13 trở lên đi, tôi duyệt triển khai luôn").
- **Sửa:** ADR-0078 (bỏ ràng buộc "chỉ dòng 3.15"; giữ 3.15.2 làm bản CI chính). Không đổi các phần khác của ADR-0078.
- **Trạng thái triển khai:** Mã và test ở PR cùng ngày; CI thêm job `compat-py313`.

## Bối cảnh

ADR-0078 chọn một dòng 3.15 để khỏi xác minh nhiều phiên bản. Chi phí thật lộ ra khi dựng môi trường: container và máy
dev phổ biến chỉ có 3.12–3.13, `uv` cấp 3.15.0b4 (bản tiền phát hành, khác bản CI 3.15.2), và mọi lệnh của khung
(`xt.py`, `install.py`, hook, `dev-task.sh`) từ chối chạy trên phiên bản khác — hook từ chối nghĩa là Bash bị chặn.
Đo ngày 2026-11-23 ở `main` `dfc4a8cb`: `py_compile` bằng 3.13 chỉ vấp sáu dòng `except A, B:` không ngoặc (cú pháp 3.14,
PEP 758) ở ba module (`xt_distribution.py`, `xt_ops_setup.py`, `xt_release_ops.py`); `mypy --strict --python-version 3.13`
sạch; ruff đã nhắm `py313` từ trước.

## Phương án đã cân nhắc

1. Giữ 3.15.x. Không đổi mã; mỗi máy phải cài 3.15 trước khi dùng khung.
2. Sàn 3.13, mọi phiên bản mới hơn đều chạy; CI chính giữ 3.15.2 và thêm một job chạy bộ test trên 3.13 (chọn).
3. Sàn 3.11 như trước ADR-0078. Hết ý nghĩa: 3.11 thiếu nhiều tính năng mà mã đang dùng và tăng chi phí kiểm.

## Quyết định

- Sàn runtime là CPython 3.13 (`MIN_PYTHON` ở `scripts/xt.py`); 3.13, 3.14, 3.15 đều chạy. Chỉ CPython, như trước.
- Mã của khung không dùng cú pháp hay API chỉ có từ 3.14 trở lên. Cú pháp nhóm ngoại lệ luôn có ngoặc. Test thêm: mọi
  tệp `.py` của khung biên dịch được bằng cú pháp 3.13.
- `mypy --strict --python-version 3.13`; ruff giữ `py313`. Muốn dùng tính năng mới hơn thì nâng sàn bằng ADR.
- CI giữ 3.15.2 cho các job hiện có (coverage 100 % ở đây); job `compat-py313` chạy toàn bộ lớp test trên 3.13 bản
  mới nhất của `actions/setup-python`, không đo coverage. Ruleset `main` không đổi (vẫn năm check bắt buộc); job này nằm
  trong `quality` nên đỏ là chặn merge.
- `dev-task.sh` bắt tay runtime bằng một dấu duy nhất `xt-cpython-ok` (CPython và ≥ 3.13) thay cho dấu theo từng
  phiên bản; lỗi runtime vẫn là exit 126 ở hook và 2 ở lệnh khác.
- Dự án đích: cài khung được trên máy có Python ≥ 3.13; workflow mẫu và steward vẫn ghim 3.15.2 cho CI của chúng,
  dự án đích có thể hạ ghim xuống 3.13 mà không đổi gì khác.

## Hệ quả

- Hết lý do đòi cài Python riêng cho khung ở máy phổ biến; `T-4011` (bootstrap) chỉ còn cần cho máy không có Python ≥ 3.13.
- Mất khả năng dùng cú pháp 3.14/3.15 trong khung tới khi nâng sàn.
- Thêm một job CI (~ bằng một shard test).
- Giữ bản ghim CI 3.15.2 nên lỗi chỉ lộ ở bản mới (ví dụ API bị gỡ) vẫn được bắt.

Đường lùi: revert PR này; ADR-0078 có hiệu lực lại.
