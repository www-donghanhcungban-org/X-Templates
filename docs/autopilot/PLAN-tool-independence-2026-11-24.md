# PLAN X-Templates 2026-11-24 — tách khung khỏi dự án đích (ADR-0097, đợt P0–P1)

> Duyệt: D-557 (phiên chính tự duyệt, chủ dự án yêu cầu "chọn phương án tốt nhất rồi triển khai") · Blueprint: BLUEPRINT.md · Căn cứ: [báo cáo tách khung](../../research/2026-11-24-framework-target-independence.md), [khảo sát 26 dự án](../../research/2026-11-24-similar-projects-survey.md)

## Tóm tắt
- Mục tiêu: dự án đích không dùng chung mã của khung và tự đặt tên công cụ. Quyết định: artefact `.pyz` ghim digest + launcher mang tên đích + hợp đồng có schema (phương án B kèm B1–B7); mặc định giữ `xt`/`.xtemplates`, nên dự án đã cài không đổi.
- Số đo P0 (2026-11-24): nạp `guard.py` từ zip `ZIP_STORED` chậm hơn tệp rời ≤ 2,5 % (3.15.2: 459 so với 463 ms; 3.13.18: 370 so với 361 ms); deflate chậm hơn. `xt.py` chạy nguyên trạng từ zip (`doctor`, `loop status`).
- Đợt này làm P0 (ADR, số đo, đóng băng hợp đồng) và P1 (bộ dựng tất định). Chưa đổi cách cài.
- Đợt sau, mỗi pha một PR đảo ngược được: P2 `tool.json` + bộ phân giải (thư mục, tên tệp cấu hình, tiền tố biến) thay các chỗ cứng; P3 `install.py --tool-name`, launcher, render `<XT>`; P4 `release-tag.yml` dựng và attest `.pyz`, `release-verify` kiểm thêm; P5 `install.py --layout artifact` và lệnh `hook <event>`; P6 reusable workflow ghim SHA và bản MAJOR kế.
- Ngoài phạm vi: đổi tên secret GitHub, bỏ `framework/**` khỏi đích (agent đọc bằng Read), plugin host.
- Mỗi lát một PR; chạm `xt.yaml`/hook/workflow cần một lượt review ở head (ADR-0095); 🔴 sửa, 🟠/🟢 ghi nợ (ADR-0062).

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí ngoài phiên: 0 · Timeout Gate: 1200 giây · Hạn: 4 giờ.

## Task
- [x] `T-4201` ADR-0097 và đính chính con trỏ "`xt.pyz` (ADR-0010)" ở PROGRESS (files: docs/adr/0097-versioned-tool-artifact-and-target-naming.md, PROGRESS.md, CHANGELOG.md) — Gate: `test -s docs/adr/0097-versioned-tool-artifact-and-target-naming.md && python3 -m unittest tests.test_docs_budget`
- [x] `T-4202` đóng băng bề mặt hợp đồng: lệnh con, khoá `xt.yaml` của mẫu, số schema, dấu review `v1`/`v2` (files: tests/test_contract_surface.py, tests/fixtures/contract-surface.json) — Gate: `python3 -m unittest tests.test_contract_surface`
- [x] `T-4203` bộ dựng artefact tất định `scripts/xt_pack.py`: `ZIP_STORED`, mục sắp theo tên, `mtime` và quyền cố định, hai lần dựng cùng `sha256`, kiểm sửa một byte, chạy được từ zip (sau: T-4202; files: scripts/xt_pack.py, tests/test_pack.py, xt.yaml) — Gate: `python3 -m unittest tests.test_pack tests.test_contract_surface`
