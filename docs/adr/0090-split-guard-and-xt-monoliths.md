# ADR-0090: Lộ trình tách module cho `.claude/hooks/guard.py` và `scripts/xt.py`

- **Trạng thái:** Đề xuất được chấp nhận ngày 2026-11-21 (mục tiêu trước hạn xét lại 2027-01-21).
- **Trạng thái triển khai:** Đã thống nhất ranh giới và cổng; tách từng lát nhỏ theo PR riêng.
- **Bổ sung:** [ADR-0091](0091-progress-hook-cap-and-split-constraints.md) (bất biến nạp guard, `perf trial`, trình tự đo T-3709).
- **Liên quan:** [ADR-0001](0001-framework-as-id-library-with-machine-composition.md), [ADR-0018](0018-deny-dangerous-allow-rest.md), [ADR-0089](0089-raise-file-and-dir-caps-5x.md), [scripts/AGENTS.md](../../scripts/AGENTS.md), [tests/AGENTS.md](../../tests/AGENTS.md).

## Bối cảnh

Đo tại commit `bb1d11df` ngày 2026-11-21 cho thấy hai tệp Python lõi đang gánh phần lớn mã điều phối và bảo vệ của khung:

| Tệp | Số dòng | Kích thước | Giới hạn nhóm (ADR-0089) |
|---|---:|---:|---:|
| `.claude/hooks/guard.py` | 24 423 | 1 379 538 B | 7 089 845 B (`.claude/hooks/`) |
| `scripts/xt.py` | 22 855 | 1 232 063 B | 8 802 155 B (`scripts/*.py`) |

Việc dồn toàn bộ bộ phân tích shell, luật git/gh, kiểm đường dẫn, vòng lặp, phát hành và merge-check vào hai tệp khiến độ trễ đọc hiểu, phạm vi xung đột PR và gánh nặng kiểm kiểu tĩnh tăng cao. Trước đây một số phần của `scripts/` đã tách thành công (`xt_ops_setup.py`, `xt_release_ops.py`, `xt_deploy.py`, `xt_derived.py`, `xt_distribution.py`, `xt_acceptance.py`), và PR `#719` đã khóa giao diện phụ thuộc bằng `Core(Protocol)` kiểm chứng qua AST.

## Quyết định

1. **Ranh giới tách `scripts/xt.py` theo miền lệnh:**
   - Tách từng cụm subcommand độc lập sang module `scripts/xt_<miền>.py` (ưu tiên `xt_loop.py`, `xt_pr.py`, `xt_doctor.py`, `xt_shard.py`), giữ `scripts/xt.py` làm điểm vào CLI, hàm lõi dùng chung và đăng ký subcommand.
   - Mọi module tách ra giao tiếp ngược với `xt.py` qua `Core(Protocol)` (theo mẫu `xt_ops_setup.py`, `xt_release_ops.py`, `xt_deploy.py`) và phải có test AST kiểm khớp thuộc tính trên `xt` (`test_core_protocol_covers_every_referenced_attribute_on_xt`).
   - Mỗi module `.py` mới phải được thêm vào lệnh `typecheck` trong `xt.yaml` (`mypy --strict --python-version 3.15`) và danh sách cài đặt trong `scripts/install.py` nếu dự án đích cần gọi.

2. **Ranh giới tách `.claude/hooks/guard.py` theo tầng xử lý:**
   - Tách dần theo ba lớp: (a) bộ tách token/chuỗi/biến Bash (`guard_bash.py`), (b) luật git/gh/network (`guard_remote.py`), (c) luật đường dẫn/bí mật/cổng (`guard_paths.py`), giữ `.claude/hooks/guard.py` làm choke point duy nhất (`PreToolUse`, ADR-0018) và điểm nạp tương thích ngược cho bộ test hiện có.
   - Khi cài sang dự án đích, `scripts/install.py` phải đồng bộ danh sách tệp companion dưới `.claude/hooks/` và giữ nguyên chế độ fail-open khi chạy ngoài dự án nếu thiếu cấu hình.

3. **Điều kiện bắt buộc cho mỗi PR tách module:**
   - Một PR chỉ tách một cụm nhỏ, không đổi hành vi CLI/hook; đối với `guard.py` bắt buộc qua toàn bộ `autonomy-bench`, `test_guard_fuzz`, `test_green_shell`, `test_green_gh`, và so quyết định thô base ↔ nhánh là tập cha không lọt (`tests/AGENTS.md`).
   - Giữ coverage dòng + nhánh 100 % trên CI, chỉ dùng stdlib CPython 3.15.x (ADR-0001).

## Hệ quả và đường lùi

- Cho phép chia nhỏ PR bảo trì an toàn mà vẫn giữ một cổng kiểm kiểu tĩnh và không phá vỡ import cũ (`import xt`, `import guard`).
- Đường lùi: mỗi lát tách là một PR độc lập nên có thể revert từng PR nếu phát sinh hồi quy ở dự án đích hoặc test parity.
