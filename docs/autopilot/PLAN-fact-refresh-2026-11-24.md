# PLAN X-Templates 2026-11-24 — cập nhật dữ kiện lỗi thời từ nghiên cứu nguồn sống

> Duyệt: D-566 (phiên chính tự duyệt; chủ dự án yêu cầu "nâng kịch trần mọi thứ từ stored + nghiên cứu cho dự án khung này") · Căn cứ: bốn báo cáo đối chiếu khung với nguồn sống ngày 2026-11-24 (AI/agent, chuỗi cung ứng/CI, UI/UX/frontend, backend/dữ liệu/vận hành), mỗi số trọng yếu tra lại từ nguồn gốc rồi mới ghi (luật P2)

## Tóm tắt
- Ba executor sửa song song theo thư mục (backend/DB/vận hành/test; frontend/UX/i18n/profiles; bảo mật/CI/chuẩn AI); phiên chính đọc diff, bắt hai lỗi (`scorecard-action` lẫn dãy số với Scorecard CLI; hồ sơ `api-service.md` chưa theo Python 3.15.2 trong khi dòng backend đã viết vậy) và tra thêm `checkov` ngoài bảng.
- Không làm vì chưa xác minh từ nguồn gốc: mốc EU AI Act sau Omnibus (EUR-Lex không đọc được qua công cụ), hạ `CMP-AI-012`, ISO/IEC 42005, NIST AI 100-2, nâng `SEC-SUPPLY-024`, số bản OSPS Baseline (hai lượt tra lệch nhau).
- Đổi mức: chỉ `UX-A11Y-026` và `UX-DS-017` (MAY → SHOULD) có nguồn WebStatus.

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí ngoài phiên: 0 · Timeout Gate: 1200 giây · Hạn: 2 giờ.

## Task
- [x] `T-4701` sửa dữ kiện lỗi thời ở `framework/` (49 tệp + hồ sơ `api-service.md`), ghi nguồn và ngày xác minh tại chỗ; đổi mức hai ID `prefers-contrast` (files: framework/**, CHANGELOG.md) — Gate: `python3 scripts/xt.py validate && python3 scripts/check-links.py && python3 scripts/xt.py changelog-check && python3 -m unittest tests.test_docs_budget tests.test_content_facts`
