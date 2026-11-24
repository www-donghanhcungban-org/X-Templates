# PLAN X-Templates 2026-11-24 — chung sống với Claude Ship (ADR-0100)

> Duyệt: D-565 (phiên chính tự duyệt; chủ dự án hỏi "Claude Ship thế nào, áp dụng vào dự án hiệu quả không", rồi "chọn hướng tốt nhất", "tôi muốn tự động nhiều nhất có thể") · Căn cứ: [nghiên cứu Claude Ship](../../research/2026-11-24-claude-ship.md) — hai lượt đọc tài liệu chính thức, lượt sau trích nguyên văn tám điểm then chốt

## Tóm tắt
- Claude Ship (ra mắt 2026-11-23): Code Review (GA), PR Steward và Claude Approvals (public beta), `/ship` và `/steward`. Tài liệu tự nêu hook của dự án không áp dụng cho `gh`/`git` do `/ship` chạy và không có xác nhận thật → lệch với guard của khung.
- Chọn mức tự động theo bậc (D-565): A mặc định (autopilot của khung), B khi chủ tổ chức bật Code Review với trần chi phí, C chỉ sau số đo từ B; không bao giờ merge mà không người duyệt.
- Việc của người (không tự làm): bật Code Review ở cấp tổ chức, đặt trần chi phí; số đo hiệu quả thật chưa có.

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí ngoài phiên: 0 · Timeout Gate: 1200 giây · Hạn: 2 giờ.

## Task
- [x] `T-4601` ADR-0100 và bản nghiên cứu Claude Ship (trích nguyên văn, mức bằng chứng từng dòng) (files: docs/adr/0100-claude-ship-coexistence.md, research/2026-11-24-claude-ship.md) — Gate: `test -s docs/adr/0100-claude-ship-coexistence.md && test -s research/2026-11-24-claude-ship.md && python3 scripts/check-links.py`
- [x] `T-4602` yêu cầu `WF-REVIEW-022` cho dự án đích: công cụ AI ngoài tự commit/duyệt/merge không là đường merge (files: framework/10-workflow/code-review.md, CHANGELOG.md) — Gate: `python3 scripts/xt.py validate && python3 scripts/xt.py changelog-check && python3 -m unittest tests.test_docs_budget tests.test_content_facts`
