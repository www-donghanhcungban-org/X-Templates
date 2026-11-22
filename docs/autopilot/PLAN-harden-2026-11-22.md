# PLAN harden X-Templates 2026-11-22 — trả nợ 🟢 sau phát hành 3.35.0

> Duyệt: D-539 (phiên chính tự duyệt) · Blueprint: BLUEPRINT.md · Quy trình: ADR-0080 · Đợt trước: PLAN-harden-2026-11-21 (lập sau khi làm; lần này lập TRƯỚC khi làm)

## Tóm tắt
- Mục tiêu: trả nợ 🟢 của audit delta thứ hai 3.35.0 làm được trong repo này: PROGRESS bàn giao lạc hậu và các mục tài liệu (lát A); hook SessionStart AUD-HAR-471 và test/mã nhỏ (lát B).
- Ngoài phạm vi, ghi lại không làm: nâng 3.35.0 vào dự án đích (cần `XT_STEWARD_TOKEN`, repo khác); tách `guard.py` (ADR-0090, nhiều PR nhỏ); AUD-TEST-140 (sinh lại trọng số cần chạy cả bộ test), AUD-ARCH-018, AUD-HAR-464 (đổi lệnh `Kiểm` của blueprint).
- Mỗi task: Gate một lệnh đơn; mỗi lát một PR; review một lần theo ADR-0062 (🔴 sửa, 🟠/🟢 ghi nợ).

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí ngoài phiên: 0 · Timeout Gate: 1200 giây · Hạn: 6 giờ.

## Task
### Lát A — tài liệu và PROGRESS
- [x] `T-3978` PROGRESS.md bàn giao đúng hiện trạng (3.35.0 đã phát hành) — Gate: `python3 scripts/xt.py progress-check`
- [x] `T-3979` AUD-DOC-317/318/319/320/321/322/323, AUD-HAR-463: SPEC admin-plan, chép trùng, DECISIONS D-520/521, nguồn CodeQL, số đo test, macOS, research, đặt nhà Plan Mode — Gate: `python3 scripts/xt.py validate` (sau: T-3978)
- [x] `T-3980` CHANGELOG khớp — Gate: `python3 scripts/xt.py changelog-check` (sau: T-3979)
### Lát B — hook và test
- [x] `T-3981` AUD-HAR-471, AUD-TEST-145: dấu khi cắt 8 KB, cắt `loop status` theo dòng, nhánh dài có dấu, test ghim 9 800 — Gate: `python3 -m unittest tests.test_hooks.SessionStartUtf8Test` (sau: T-3980)
- [x] `T-3982` AUD-TEST-144, AUD-CODE-066, AUD-TEST-143, AUD-TEST-142, AUD-DOC-316: tên test, thông điệp about, trần 1 MiB, keep_mode, ghi chú chuẩn một dòng — Gate: `python3 -m unittest tests.test_ops_setup_edges tests.test_doctor tests.test_install` (sau: T-3981)
- [x] `T-3983` Sổ audit khớp — Gate: `python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md --strict` (sau: T-3982)
