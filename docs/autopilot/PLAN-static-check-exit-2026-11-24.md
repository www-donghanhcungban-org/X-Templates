# PLAN X-Templates 2026-11-24 — static-check: lỗi nội bộ của loại thoát mã 2

> Duyệt: D-572 (phiên chính tự duyệt; chủ dự án yêu cầu "hoàn thành tiếp dự án") · Căn cứ: rà Opus #785 (🟢 có từ trước): `main` của `xt.py` chỉ bắt `OSError`/`UnicodeDecodeError` nên lỗi của loại thoát mã 1, trùng "có phát hiện"

## Tóm tắt
- `cmd_static_check` bắt lỗi ngoài dự kiến của loại, in tên lỗi, thoát mã 2; test đỏ trước (ngoại lệ thoát ra), xanh sau.

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí ngoài phiên: 0 · Timeout Gate: 1200 giây · Hạn: 1 giờ.

## Task
- [x] `T-4941` bắt lỗi nội bộ của loại ở `cmd_static_check`, thoát 2 (files: scripts/xt.py, tests/test_static_check.py, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_static_check tests.test_static_check_hardening tests.test_doc_command_drift`
