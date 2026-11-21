# PLAN harden X-Templates 2026-11-21 — cổng ký 3.35.0 (audit delta thứ hai)

> Duyệt: D-538 (phiên chính tự duyệt) · Blueprint: BLUEPRINT.md · Quy trình: ADR-0080 · Đợt trước: PLAN-harden-2026-11-17
> **Lập sau khi làm** (ghi thẳng để không ai hiểu nhầm): các lát #727–#731 chạy ngoài vòng `loop` vì phiên bỏ Bước 3–4 của `/complete`. PLAN này khai lại đúng các lát đó để `loop verify` chạy lại từng Gate trên cây hiện tại và để `release-sign` biết không còn `loop defer`. Bằng chứng của task là lần chạy lại hôm nay, không phải lời khai.

## Tóm tắt
- Mục tiêu: đóng 2 🔴 (AUD-HAR-461, AUD-CI-040) và 12 🟠 của audit delta thứ hai #716–#726 cùng nợ review #727–#729; nâng trần ADR-0092; sổ audit khớp. Còn 🟢 mở ghi trong sổ (AUD-HAR-471, AUD-TEST-137…145…).
- Quyết định: D-536 (hook về 8 KB, ngân sách ký tự), D-537 (nâng trần theo giới hạn kênh), D-538 (duyệt PLAN này).
- Không có việc cần người ngoài chữ ký §5 của GO-NO-GO (do agent ký theo `release_signoff: agent`, ADR-0074).

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí ngoài phiên: 0 · Timeout Gate: 1200 giây · Hạn: 4 giờ.

## Task
### Lát A — hook và công cụ (🔴)
- [x] `T-3971` 🔴 AUD-HAR-461/465/466/467/468: hook SessionStart giữ tổng additionalContext ≤ 9 800 ký tự, cắt giữa `loop status`, đo bằng ký tự, cắt PROGRESS có dấu — Gate: `python3 -m unittest tests.test_hooks.SessionStartUtf8Test`
- [x] `T-3972` 🔴 AUD-CI-040: hàng `field-workflow` của `admin-plan` không đòi quyền tạo PR của Actions — Gate: `python3 -m unittest tests.test_ops_setup_edges tests.test_admin_plan` (sau: T-3971)
### Lát B — ADR, trần, tài liệu (🟠)
- [x] `T-3973` 🟠 AUD-ARCH-016/017, AUD-DOC-311…315, AUD-TEST-136: ADR-0091/0092, `LOOP-CTX-001`, AGENTS, WF-SDD-018 — Gate: `python3 scripts/xt.py validate` (sau: T-3972)
- [x] `T-3977` 🟠 CHANGELOG `[3.35.0]` khớp VERSION, mục "Dự án đích" — Gate: `python3 scripts/xt.py changelog-check` (sau: T-3973)
- [x] `T-3974` AUD-HAR-462: trần `CAPS`/`DIR_CAPS`/`MARK_FACTOR` theo giới hạn kênh (ADR-0092) — Gate: `python3 -m unittest tests.test_docs_budget` (sau: T-3977)
### Lát C — sổ và bench
- [x] `T-3975` Sổ audit khớp, không 🔴/🟠 mở — Gate: `python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md --strict` (sau: T-3974)
- [x] `T-3976` Bench tự hành phủ mọi 🔴/🟠 `đã sửa` — Gate: `python3 -m unittest tests.test_autonomy_bench` (sau: T-3975)
