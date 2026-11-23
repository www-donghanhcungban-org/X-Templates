# PLAN harden X-Templates 2026-11-23 (đợt b) — mốc quét sổ audit lên `bcd1c25a`

> Duyệt: D-555 (phiên chính tự duyệt) · Blueprint: BLUEPRINT.md · Quy trình: ADR-0080 · Đợt trước: PLAN-harden-2026-11-23

## Tóm tắt
- Mục tiêu: `release-check` còn `review_debt` do mốc quét: nhóm DEP ở `6e134c68` trong khi lô B đã rà phụ thuộc (starter, khoá e2e, hash Playwright 1.65.2, Biome 2.6.8), và các tệp PLAN của #757 đổi sau mốc `37399979`. Đưa các nhóm đã rà lên `bcd1c25a`; delta `37399979..bcd1c25a` chỉ đổi PLAN, sổ audit, báo cáo và bản nháp GO-NO-GO.
- Ngoài phạm vi: ký GO-NO-GO (sau khi `release-check` chỉ còn hàng chữ ký); T-4007, T-4010.
- Một lát, một PR; chỉ đổi tài liệu và sổ.

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí ngoài phiên: 0 · Timeout Gate: 1200 giây · Hạn: 2 giờ.

## Task
- [x] `T-4104` sổ: nhóm ARCH, SEC, CODE, TEST, DEP, CI, DOC, XFEAT, HAR lên `bcd1c25a` kèm ghi chú phạm vi — Gate: `python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md --strict && grep -c 'bcd1c25a' docs/ops/AUDIT-STATUS.md`
