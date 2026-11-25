# PLAN X-Templates 2026-11-24 — quy tắc làm lát kế trên nhánh cục bộ khi PR đáy chờ merge

> Duyệt: D-570 (phiên chính tự duyệt; chủ dự án yêu cầu "cứ tiếp tục, làm trên nhánh riêng chờ merge xong rồi thì tạo PR, cứ tiếp tục như vậy… mô tả lại cho chuẩn rồi ghi nhớ cho cả dự án khung và dự án đích") · Căn cứ: `LOOP-DESIGN-020` chỉ mô tả PR chồng; phiên chỉ được đẩy một nhánh (cloud) cần cách làm khác

## Tóm tắt
- Thêm `LOOP-DESIGN-029` (SHOULD) và dòng nối ở README vòng lặp, `AGENTS.md` của khung, `framework/templates/AGENTS.md` cho dự án đích.
- Không đổi công cụ hay hợp đồng.

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí ngoài phiên: 0 · Timeout Gate: 1200 giây · Hạn: 1 giờ.

## Task
- [x] `T-4921` ghi `LOOP-DESIGN-029` và các dòng nối, changelog (files: framework/11-autonomous-loop/loop-design.md, framework/11-autonomous-loop/README.md, framework/templates/AGENTS.md, AGENTS.md, CHANGELOG.md) — Gate: `python3 scripts/xt.py validate && python3 scripts/check-links.py && python3 scripts/xt.py changelog-check && python3 -m unittest tests.test_docs_budget tests.test_content_facts tests.test_doc_command_drift`
