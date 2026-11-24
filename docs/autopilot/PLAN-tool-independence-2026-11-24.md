# PLAN X-Templates 2026-11-24 — tách khung khỏi dự án đích (ADR-0097, đợt P0–P1)

> Duyệt: D-557 (phiên chính tự duyệt, chủ dự án yêu cầu "chọn phương án tốt nhất rồi triển khai") · Blueprint: BLUEPRINT.md · Căn cứ: [báo cáo tách khung](../../research/2026-11-24-framework-target-independence.md), [khảo sát 26 dự án](../../research/2026-11-24-similar-projects-survey.md)

## Tóm tắt
- Mục tiêu: dự án đích không dùng chung mã của khung và tự đặt tên công cụ. Quyết định: artefact `.pyz` ghim digest + launcher mang tên đích + hợp đồng có schema (phương án B kèm B1–B7); mặc định giữ `xt`/`.xtemplates`, nên dự án đã cài không đổi.
- Số đo P0 (2026-11-24, thô ở `research/evidence/2026-11-24-zip-load-bench.txt`): nạp `guard.py` từ zip `ZIP_STORED` trong ±3 % so với tệp rời (3.15.2: 431 so với 428 ms; 3.13.18: 318 so với 325 ms); deflate chậm hơn +4 %.
- Lượt rà đầu của PR (🔴) phát hiện `xt.py` chỉ nhận ra module anh em là tệp trên đĩa nên zip thiếu 7 lệnh con (`upgrade`, `release-verify`, `acceptance`…) và `--version` báo "unknown" — khẳng định "chạy nguyên trạng từ zip" ở bản đầu là sai (mới thử ba lệnh). Đã sửa bằng `sibling_exists`/`artifact_member` và test đòi zip có đủ lệnh con của hợp đồng.
- Đợt này làm P0 (ADR, số đo, đóng băng hợp đồng) và P1 (bộ dựng tất định, `xt.py` nhận ra mã trong zip). Chưa đổi cách cài.
- Đợt sau, mỗi pha một PR đảo ngược được: P2 `tool.json` + bộ phân giải (thư mục, tên tệp cấu hình, tiền tố biến) thay các chỗ cứng; P3 `install.py --tool-name`, launcher, render `<XT>`; P4 `release-tag.yml` dựng và attest `.pyz`, `release-verify` kiểm thêm; P5 `install.py --layout artifact` và lệnh `hook <event>`; P6 reusable workflow ghim SHA và bản MAJOR kế.
- Ngoài phạm vi: đổi tên secret GitHub, bỏ `framework/**` khỏi đích (agent đọc bằng Read), plugin host.
- Mỗi lát một PR; chạm `xt.yaml`/hook/workflow cần một lượt review ở head (ADR-0095); 🔴 sửa, 🟠/🟢 ghi nợ (ADR-0062).

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí ngoài phiên: 0 · Timeout Gate: 1200 giây · Hạn: 4 giờ.

## Task
- [x] `T-4205` ADR-0097 pha P2a: module `scripts/xt_toolcfg.py` (bộ phân giải `tool.json`: gốc, tên tệp cấu hình, tiền tố biến, `contract`/`min_contract`; thiếu tệp → mặc định, sai → lỗi rõ, `min_contract` cao hơn artefact → từ chối), vào `.pyz` và `install.py`; chưa nối vào `xt.py` (files: scripts/xt_toolcfg.py, scripts/xt_pack.py, scripts/install.py, xt.yaml, tests/test_toolcfg.py, tests/test_install.py, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_toolcfg tests.test_pack tests.test_install`
- [x] `T-4204` trả nợ review #768 (nợ-review: #768, đặt ở sổ audit): mục zip hỏng coi như thiếu và không rơi về đọc đĩa, `perf trial` và `mutate-guard` chạy từ zip, từ chối thư mục gói là liên kết tượng trưng, tệp tạm của `build`, `--strict` đòi `VERSION`, hợp đồng thêm `test-weights`, `perf trial`, `STAGE_SCHEMA` và dấu review `debt`, sửa ADR-0097 và số đo (sau: T-4203; files: scripts/xt.py, scripts/xt_pack.py, tests/test_pack.py, tests/test_contract_surface.py, tests/fixtures/contract-surface.json, docs/adr/0097-versioned-tool-artifact-and-target-naming.md) — Gate: `python3 -m unittest tests.test_pack tests.test_contract_surface tests.test_docs_budget`
- [x] `T-4201` ADR-0097 và đính chính con trỏ "`xt.pyz` (ADR-0010)" ở PROGRESS (files: docs/adr/0097-versioned-tool-artifact-and-target-naming.md, PROGRESS.md, CHANGELOG.md) — Gate: `test -s docs/adr/0097-versioned-tool-artifact-and-target-naming.md && python3 -m unittest tests.test_docs_budget`
- [x] `T-4202` đóng băng bề mặt hợp đồng: lệnh con, khoá `xt.yaml` của mẫu, số schema, dấu review `v1`/`v2` (files: tests/test_contract_surface.py, tests/fixtures/contract-surface.json) — Gate: `python3 -m unittest tests.test_contract_surface`
- [x] `T-4203` bộ dựng artefact tất định `scripts/xt_pack.py`: `ZIP_STORED`, mục sắp theo tên, `mtime` và quyền cố định, hai lần dựng cùng `sha256`, kiểm sửa một byte, zip có đủ lệnh con của hợp đồng và đúng `--version` (sau: T-4202; files: scripts/xt_pack.py, scripts/xt.py, tests/test_pack.py, xt.yaml) — Gate: `python3 -m unittest tests.test_pack tests.test_contract_surface`
