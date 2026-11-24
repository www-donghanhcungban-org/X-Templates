# PLAN X-Templates 2026-11-24 — nâng skill ui-verify và adr từ ý skill của catalog stored

> Duyệt: D-568 (phiên chính tự duyệt; chủ dự án yêu cầu "nâng trần tất cả skill… mọi thứ từ stored", "còn gì làm tiếp trước đi") · Căn cứ: PLAYBOOK §5.3/§5.5 của stored đối chiếu với skill hiện có: phần lớn ý đã có ở `ui-verify` hoặc ID `UX-*`; chỗ thiếu là tuỳ chọn người dùng, quét tĩnh nguồn và báo cáo bốn trạng thái. Skill `adr` lệch mẫu MADR của chính khung (thiếu Yếu tố quyết định, Xác nhận, Điều kiện đọc lại)

## Tóm tắt
- Nâng chứ không thêm skill mới: khung có 17 skill và test định tuyến (`XC-DOCAI-025`) đòi mỗi skill mới có ≥ 2 câu mẫu và không trùng `description`; thêm skill chỉ khi đo được lợi.
- Không làm: skill cần chạy model để chấm (`evaluating-ux-skills`), tổng hợp nghiên cứu người dùng (`synthesizing-user-research`) — ngoài phạm vi khung và không tất định.
- `description` giữ nguyên để không đổi định tuyến.

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí ngoài phiên: 0 · Timeout Gate: 1200 giây · Hạn: 1 giờ.

## Task
- [x] `T-4901` nâng `ui-verify` (tuỳ chọn người dùng, axe `wcag22aa`, quét tĩnh `static-check`, báo cáo bốn trạng thái + gói bằng chứng) và `adr` (mục MADR còn thiếu), sinh lại gương Codex (files: .claude/skills/ui-verify/SKILL.md, .claude/skills/adr/SKILL.md, .agents/skills/ui-verify/SKILL.md, .agents/skills/adr/SKILL.md, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_skill_routing tests.test_codex_harness tests.test_doc_command_drift tests.test_docs_budget tests.test_content_facts tests.test_skill_factory`
