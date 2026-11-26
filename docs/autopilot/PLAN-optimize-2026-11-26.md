# PLAN X-Templates 2026-11-26 — tối ưu khung đợt 1 và nâng dự án đích

> Duyệt: D-608 (phiên chính tự duyệt; chủ dự án yêu cầu "nghiên cứu thêm, tối ưu toàn bộ khung và áp dụng khung cho dự án đích") · Căn cứ: [nghiên cứu tối ưu](../../research/2026-11-26-framework-optimization.md) (10 hướng đo, mỗi hướng một lượt phản biện) · Dự án đích: D-609, D-610

## Tóm tắt
- Nghiên cứu cho 31 lát; đợt này làm các lát không chạm tệp nóng (`guard.py`, `xt.py`, `settings.json`) cùng lát đầu chuỗi `CHANGELOG`. Lát còn lại xếp ở mục "Đợt sau" của nghiên cứu, mở PLAN riêng khi đợt này merge.
- Mỗi lát một nhánh từ `origin/main`, một worktree, một PR; `files:` không giao nhau nên chạy song song (`LOOP-ORCH-007`).
- Dự án đích: chưa nâng (D-610); tối ưu đi vào mã khung và mẫu cài, đích nhận khi cắt bản kế. X-Scanner giữ 3.29.0 có hạn (D-609); X-Agents loại khỏi danh sách đích (D-610).
- Không nới cổng: coverage 100 %, `mypy --strict`, C901 ≤ 10, trần byte và trần dòng giữ nguyên.

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí dịch vụ ngoài: 0 · Timeout Gate: 1200 giây · Hạn: phiên hiện hành.

## Task

### Lát 1 — sổ đo và kế hoạch
- [ ] `T-5032` ghi số đo 10 hướng, kế hoạch 31 lát, đề xuất bị bác và việc cần người vào `research/`; mở hàng sổ audit cho phát hiện chưa có nhà (files: research/2026-11-26-framework-optimization.md, docs/autopilot/PLAN-optimize-2026-11-26.md, docs/autopilot/DECISIONS.md, docs/ops/AUDIT-STATUS.md, tests/fixtures/autonomy/scope.json, PROGRESS.md) — Gate: `python3 scripts/xt.py validate && python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md && python3 scripts/check-links.py && python3 -m unittest tests.test_docs_budget tests.test_plan_files`

### Lát 2 — CI và cổng cục bộ nhanh hơn, không đổi độ phủ
- [ ] `T-5033` tách lưới fuzz thường của `GuardFuzzTest` thành 4 phần `variants[p::4]` và `GuardLayersNoNetworkTest` theo từng lớp mạng; giữ tên lớp `GuardFuzzTest`; test phân hoạch chứng minh hợp các phần bằng tập gốc, không trùng; đặt trọng số lớp mới (files: tests/test_guard_fuzz.py, tests/test_signoff3_isolation.py, tests/shard-weights.json; topo: parallel) — Gate: `python3 -m unittest tests.test_guard_fuzz tests.test_signoff3_isolation tests.test_ci_shard`
- [ ] `T-5034` test nêu đích danh `verify-render.mjs` và bài test e2e của nó, khẳng định workflow gói web phủ hai tệp và README liệt kê đủ cờ, để `test-select` không rơi về cả suite (files: tests/test_verify_render.py; topo: parallel) — Gate: `test "$(python3 scripts/xt.py test-select --unittest framework/templates/ui-gates/verify-render.mjs tests_e2e/verify_render.test.mjs | wc -l)" -lt 10 && python3 -m unittest tests.test_verify_render tests.test_select_inherit tests.test_commit_gate`
- [ ] `T-5035` test kiểm kiểu các khoá đã biết của `.claude/settings.json` (giá trị `env` là chuỗi, `timeout` là số, `onFailure` thuộc tập cho phép, `autoCompactWindow` nguyên ≥ 100000); khoá lạ không đỏ (files: tests/test_settings_types.py; topo: parallel) — Gate: `python3 -m unittest tests.test_settings_types`
- [ ] `T-5037` `check-links` bỏ đúng tiền tố `.claude/worktrees` bằng `os.walk` có tỉa; bộ dò lệnh tài liệu loại cùng đường; test tự dựng worktree giả có link hỏng (files: scripts/check-links.py, tests/test_check_links.py, tests/test_doc_command_drift.py, CHANGELOG.md; topo: parallel) — Gate: `python3 -m unittest tests.test_check_links tests.test_doc_command_drift && python3 scripts/check-links.py && python3 scripts/xt.py autonomy-bench`

### Lát 3 — dự án đích
- [ ] `T-5036` registry và TARGETS ghi ngoại lệ có hạn 2027-01-21 cho X-Scanner (trần 1 MiB mỗi tệp của đích) kèm ba điều kiện mở; loại X-Agents khỏi danh sách đích (D-610) (files: docs/ops/registry.json, docs/ops/TARGETS.md; topo: parallel) — Gate: `python3 scripts/xt.py registry --json >/dev/null && python3 -m unittest tests.test_registry`
- [~] `T-5038` X-Company canary: PR nâng `.xtemplates/` lên v3.36.0 ở repo đích — Bỏ: chủ dự án hoãn mọi PR nâng ở dự án đích (D-610); dừng trước khi đẩy nhánh, repo đích không đổi
