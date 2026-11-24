# PLAN X-Templates 2026-11-24 — lô ID yêu cầu mới từ catalog stored

> Duyệt: D-567 (phiên chính tự duyệt; chủ dự án yêu cầu "nâng trần tất cả skill, lô ID… mọi thứ từ stored") · Căn cứ: bốn báo cáo rà PLAYBOOK §5–§7 của catalog stored (nhãn KHUNG: có ý nhưng thiếu ID); mỗi ý lọc theo luật mức ở D-567

## Tóm tắt
- 18 ID mới ở 14 tệp thuộc 11 module, bốn executor viết song song theo khuôn có sẵn; phiên chính kiểm bằng máy (khuôn, mức, `Kiểm` và `Nguồn`, mọi ID viện dẫn có thật) rồi đọc nguyên văn các ID rủi ro nhất.
- Không có MUST. SHOULD chỉ khi bổ sung trực tiếp cho một ID có sẵn; ý chỉ có nguồn là đề xuất của catalog stored để MAY (hạ `WF-CI-029` từ SHOULD xuống MAY vì không bổ sung ID nào).
- Chưa làm: ID cho các ý cần công cụ ngoài hoặc chưa có nguồn nào ngoài catalog mà không bổ sung ID có sẵn; mốc EU AI Act sau Omnibus (chưa xác minh).

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí ngoài phiên: 0 · Timeout Gate: 1200 giây · Hạn: 2 giờ.

## Task
- [x] `T-4801` thêm 18 ID mới vào `framework/` (không MUST), ghi CHANGELOG (files: framework/06-design-ux/ai-ux.md, framework/06-design-ux/motion-and-visual-quality.md, framework/03-industries/media-content.md, framework/12-security/ai-security.md, framework/12-security/secrets-management.md, framework/13-ai-engineering/evaluation.md, framework/13-ai-engineering/agentic-systems.md, framework/13-ai-engineering/protocols-mcp-a2a.md, framework/08-backend/background-jobs-and-queues.md, framework/08-backend/files-and-media.md, framework/15-operations/deployment-strategies.md, framework/18-cross-cutting/i18n-and-l10n.md, framework/10-workflow/ci-cd-pipeline.md, framework/17-product-project/risk-and-assumptions.md, CHANGELOG.md) — Gate: `python3 scripts/xt.py validate && python3 scripts/check-links.py && python3 scripts/xt.py changelog-check && python3 -m unittest tests.test_docs_budget tests.test_content_facts`
