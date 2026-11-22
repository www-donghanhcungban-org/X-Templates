# PLAN harden X-Templates 2026-11-22 (đợt b) — trả nợ 🟢 có đường tái hiện sau audit delta 22/11

> Duyệt: D-541 (phiên chính tự duyệt) · Blueprint: BLUEPRINT.md · Quy trình: ADR-0080 · Đợt trước: PLAN-harden-2026-11-22 (lập trước khi làm)

## Tóm tắt
- Mục tiêu: trả năm nợ 🟢 của audit delta `98770bc7..ce08f914` mà có đường tái hiện: AUD-DOC-328 (sổ ghi số PR thay "PR sau"), AUD-TEST-148 và AUD-DOC-330 (test hook), AUD-XFEAT-053 và AUD-CODE-067 (`xt_distribution.py`, `xt_ops_setup.py`).
- Ngoài phạm vi, ghi lại không làm: AUD-DOC-327 (chỉnh `updated` và tệp luật cho ba tệp, giá trị thấp, để chạm khi sửa nội dung thật); AUD-DOC-329 (khuôn GO-NO-GO nằm ở bản đã ký, sửa ở lần cắt bản sau); AUD-HAR-474 (chưa biết Claude Code đếm giới hạn 10 000 theo code point hay UTF-16, sửa theo đoán là rủi ro); tách `guard.py` (PLAN-guard-split-2026-11-22). Không cắt bản mới: chỉ sửa hook và tài liệu, không buộc dự án đích làm gì.
- Mỗi lát một PR; review một lần theo ADR-0062 (🔴 sửa, 🟠/🟢 ghi nợ); lát mã chỉ merge sau review sạch ở head.

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí ngoài phiên: 0 · Timeout Gate: 1200 giây · Hạn: 6 giờ.

## Task
### Lát A — sổ
- [x] `T-3991` AUD-DOC-328: thay "(`3a7f952b`, PR sau)" bằng "(#737)" và "(`bd762557`, PR sau)" bằng "(#736)" ở các hàng sổ — Gate: `python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md --strict`
### Lát B — mã và test
- [ ] `T-3992` AUD-TEST-148, AUD-DOC-330: test dòng nối thêm của khối Autopilot, sửa chú thích dòng đầu — Gate: `python3 -m unittest tests.test_hooks.SessionStartUtf8Test` (sau: T-3991)
- [ ] `T-3993` AUD-XFEAT-053, AUD-CODE-067: `URL_TAIL` chỉ miễn khi dòng ghi chú chưa có URL, `about_status` xét từng trường, bỏ cách che chữ `https:/{2}`, gợi ý "chưa đọc được" không ghi đè mô tả — Gate: `python3 -m unittest tests.test_doctor tests.test_ops_setup_edges` (sau: T-3992)
- [ ] `T-3994` CHANGELOG và sổ khớp (bốn hàng `đã sửa`, ghi PR) — Gate: `python3 scripts/xt.py changelog-check` (sau: T-3993)
