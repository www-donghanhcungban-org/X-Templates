# PLAN — Hardening X-Templates trước 3.37.0

> Duyệt D-643. Mốc `34fdcf0a`. Pha `harden`, quy mô S.

## Mục tiêu

- Khép các phát hiện 🟠 trong [sổ audit](../ops/AUDIT-STATUS.md) theo từng lát. Giữ ID T-5068 và T-5073 từ [PLAN nâng cấp](PLAN-upgrade-2026-11-27.md).
- Đợt D-638 đã qua 12 Gate và 69 lệnh xác minh Blueprint. Không còn MUST mở. `release-check` vẫn NO-GO vì sổ audit và nợ review. Rà delta theo phạm vi máy in và chạy lại xác minh cuối trước khi lập gói ký.
- Giữ PR theo hàng đợi của `main`. Phần thiết lập GitHub do admin và môi trường diễn tập theo T-4007/T-5020 tiếp tục xử lý tại PLAN đang sở hữu chúng.

## Ngân sách

- Số vòng theo `--single-session`. Timeout mỗi Gate 1200 giây. Chi phí dịch vụ ngoài 0.

## Task

- [ ] `T-5097` AUD-HAR-572: khởi động bộ nạp Python của hook với stdlib, kiểm tương thích CLI và đầu ra hook (nguồn: audit:AUD-HAR-572) (files: .claude/hooks/, tests/test_guard_audit1019.py, tests/test_hook_precompact_output.py, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `python3 -m unittest tests.test_guard_audit1019 tests.test_hook_precompact_output tests.test_hooks`
- [x] `T-5073` AUD-HAR-577: gắn hợp đồng duyệt với đường dẫn bằng chứng ổn định và giữ trạng thái chờ cho task phụ thuộc (nguồn: audit:AUD-HAR-577) (files: scripts/xt_design.py, tests/test_design_gate.py, tests/fixtures/autonomy/scope.json, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `python3 -m unittest tests.test_design_gate`
- [x] `T-5102` AUD-HAR-583: giữ CLI cũ chạy được nếu lần nâng cấp lỗi trước khi có đủ mô-đun cho CLI mới. Kiểm đường cài thật với lỗi chép tệp và lượt chạy lại (nguồn: audit:AUD-HAR-583) (files: scripts/install.py, tests/test_install_atomic.py, tests/fixtures/autonomy/scope.json, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `python3 -m unittest tests.test_install_atomic tests.test_install`
- [ ] `T-5098` AUD-HAR-573: áp chính sách đường dẫn được bảo vệ cho cache bytecode của CLI và các gói đi kèm ở repo khung và bản cài. Kiểm đối chứng cache ứng dụng và bố cục cài chưa xác định (nguồn: audit:AUD-HAR-573) (files: .claude/hooks/guard.py, tests/test_hooks.py, tests/fixtures/autonomy/scope.json, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `python3 -m unittest tests.test_hooks tests.test_docs_budget`
- [ ] `T-5068` AUD-HAR-576: áp cùng chính sách bảo vệ thao tác duyệt cho các bộ nạp mô-đun theo tên, giữ ngân sách dòng (nguồn: audit:AUD-HAR-576) (files: .claude/hooks/guard.py, tests/test_stage_agent_approval.py, tests/fixtures/autonomy/guard.json, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `python3 -m unittest tests.test_stage_agent_approval tests.test_guard_corpus tests.test_autonomy_bench tests.test_docs_budget`
- [ ] `T-5096` AUD-HAR-541: dùng tập cú pháp tên/refspec xác định được khi phân loại thao tác tag phát hành (nguồn: audit:AUD-HAR-541) (files: .claude/hooks/guard.py, tests/test_guard_release_oracle.py, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `python3 -m unittest tests.test_guard_release_oracle`
- [ ] `T-5101` AUD-HAR-579: xử lý đối số biến đổi số lượng từ theo cùng chính sách xác định được (nguồn: audit:AUD-HAR-579) (sau: T-5096; files: .claude/hooks/guard.py, tests/test_guard_tag_glob_oracle.py, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `python3 -m unittest tests.test_guard_tag_glob_oracle`

## Cổng ký

- Rà delta và nợ review trên diff tích luỹ sau khi các lát đã merge. Chạy `python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md --strict`, `python3 scripts/xt.py loop verify --all` và `python3 scripts/xt.py release-check --json` trên cây cuối trước khi ký.
