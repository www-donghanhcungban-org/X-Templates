# PLAN harden X-Templates 2026-11-23 — audit delta #746–#755 và hồ sơ cắt bản 3.36.0

> Duyệt: phiên chính tự duyệt, ghi `loop decide` (ADR-0008) · Blueprint: BLUEPRINT.md · Quy trình: ADR-0080 · Nguồn: `release-check` ở `75ead1ac460a` (blueprint, verify, review_debt, go_no_go)

## Tóm tắt
- Mục tiêu: trả nợ review của `release-check` (70 file đổi sau SHA quét `27d70c0c`): audit delta cho #746–#755 trên diff tích luỹ `27d70c0c..fae1ca30` (phần #756 đã qua ba lô rà và hai lượt rà hẹp), ghi sổ, chuẩn bị GO-NO-GO 3.36.0 chờ ký.
- Ngoài phạm vi: ký GO-NO-GO và cắt bản (BASE-DEP-003 chỉ xanh ở môi trường CPython 3.15.2); T-4007 và T-4010 (chờ người); tách sâu `guard.py`.
- Mỗi lát một PR; 🔴 sửa, 🟠/🟢 ghi nợ có chủ và hạn (ADR-0062).

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí ngoài phiên: 0 · Timeout Gate: 1200 giây · Hạn: 6 giờ.

## Task
- [x] `T-4101` audit delta lô A (guard, hồ sơ guard, quyết định merge: `scripts/xt_guard_profile.py`, `.claude/hooks/guard.py`, tests guard/merge) bằng `reviewer-alt`, báo cáo ở `docs/ops/AUDIT-REPORT-2026-11-23-delta.md` — Gate: `test -s docs/ops/AUDIT-REPORT-2026-11-23-delta.md`
- [x] `T-4102` audit delta lô B (ops/CI/release/sàn Python: `xt_ops_setup.py`, workflow, ruleset tag, `dev-task.sh`, `install.py`, tài liệu ADR-0093…0095) bằng `reviewer-alt` (sau: T-4101)  — Gate: `grep -q "Lô B" docs/ops/AUDIT-REPORT-2026-11-23-delta.md`
- [x] `T-4103` sổ: nhóm quét lên SHA mới, hàng phát hiện, D-NNN cho AUD-HAR-487 và AUD-CI-042, sửa chữ "PR một tệp + `tests/test_x.py`" — Gate: `python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md --strict` (sau: T-4102)
