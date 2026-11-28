# PLAN — Hoàn thiện các phát hiện audit delta X-Templates

> Duyệt D-638. Mốc `60681783`. Bằng chứng và phạm vi nằm ở [báo cáo audit](../ops/AUDIT-REPORT-2026-11-27-delta.md).

## Mục tiêu

- Sửa từng phát hiện đã xác minh bằng ca hồi quy ở luồng thật. Giữ nguyên các ngưỡng chất lượng và lần lượt đưa từng lát qua hàng PR.
- Dùng [PLAN nâng cấp](PLAN-upgrade-2026-11-27.md) cho các việc đã có ID. Sau khi các lát merge, chạy audit delta, `audit check --strict` và `release-check` để quyết định có thể cắt 3.37.0.

## Ngân sách

- Số vòng tính theo `--single-session`. Chi phí dịch vụ ngoài 0. Timeout mỗi Gate 1200 giây. Xử lý các mục reflow có hạn 2026-12-02 trước cổng ký.

## Việc phụ thuộc môi trường

- T-4007 và T-5020 cần quyền cấu hình GitHub, danh tính phát hành và repo diễn tập. T-5081 còn kiểm trên Claude Code thật. T-5082 còn đo workload WSL2 trước khi đổi mặc định theo AUD-HAR-581.

## Task

### Lát 0 — Xác nhận truy vết tiêu chí

- [x] `T-5094` AUD-XFEAT-062: `ac-trace` nhận mã AC trong Markdown hợp lệ và mẫu SPEC nối mã AC với kịch bản S-NNN (nguồn: audit:AUD-XFEAT-062, D-641) (files: scripts/xt_checks/kind_ac_trace.py, framework/templates/SPEC.md, tests/test_check_ac_trace.py, tests/fixtures/autonomy/scope.json, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `python3 -m unittest tests.test_check_ac_trace tests.test_static_check`

### Lát 1 — Bảo toàn cấu hình và giới hạn tài nguyên

- [x] `T-5083` AUD-XFEAT-057: bot nâng cấp giữ lựa chọn ghim model Codex đã bật; bản cài kế thừa và tệp tự sửa giữ chính sách hiện hành (nguồn: audit:AUD-XFEAT-057) (files: scripts/install.py, scripts/xt_distribution.py, tests/test_codex_harness.py, tests/test_upgrade_bot.py, framework/templates/harness/README.md, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `python3 -m unittest tests.test_codex_harness tests.test_upgrade_bot`
- [x] `T-5084` AUD-CODE-068: hạn chờ khay CPU áp cả lúc chờ khoá và lúc cấp lease; hết hạn trả 2, lệnh con chưa chạy và mục chờ được dọn (nguồn: audit:AUD-CODE-068) (files: scripts/xt_cpu_share.py, tests/test_cpu_share.py, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review; exec: deep) — Gate: `python3 -m unittest tests.test_cpu_share`
- [x] `T-5085` AUD-XFEAT-058: kiểm cùng tập đối số ICU trong thân nhánh plural/select, phát hiện khoá phẳng/lồng trùng; giữ cú pháp và selector theo locale (nguồn: audit:AUD-XFEAT-058) (files: scripts/xt_checks/kind_i18n.py, tests/test_check_i18n.py, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `python3 -m unittest tests.test_check_i18n`

### Lát 2 — Cổng nghiệm thu và phát hành

- [x] `T-5086` AUD-HAR-582: phân loại delta theo đường dẫn cho E2E và tài sản UI; thay một tệp thì nhóm phù hợp có trong `rescan` (nguồn: audit:AUD-HAR-582) (files: scripts/xt.py, tests/test_xt_cli.py, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `python3 -m unittest tests.test_xt_cli.PathGroupsTest tests.test_xt_cli.AuditToolsTest tests.test_xt_cli.AuditRescanTest tests.test_docs_budget`
- [x] `T-5087` AUD-A11Y-004: kiểm chữ cắt theo mép cắt thực của khung có viền; kiểm Chromium với ca fit và ca cắt dưới reflow (files: framework/templates/ui-gates/, tests_e2e/verify_render.test.mjs, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `node --test tests_e2e/verify_render.test.mjs`
- [x] `T-5088` AUD-CI-049: cả hai đường kiểm release đã có dùng đúng tên archive/biên nhận theo hợp đồng downstream, đồng thời kiểm VERSION của tag (nguồn: audit:AUD-CI-049) (files: .github/workflows/release-tag.yml, tests/test_ci.py, tests/test_release_assets.py, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `python3 scripts/xt.py ci-check && python3 -m unittest tests.test_ci tests.test_release_assets`
- [x] `T-5089` AUD-DEP-040: required CI kiểm cả lock verify-render và Dependabot theo dõi cùng thư mục (nguồn: audit:AUD-DEP-040) (files: .github/workflows/dep-audit.yml, .github/dependabot.yml, tests/test_ci.py, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `npm audit --package-lock-only --ignore-scripts --audit-level=moderate --prefix tests_e2e/verify-render-deps && python3 -m unittest tests.test_ci`
- [x] `T-5090` AUD-XFEAT-059: preflight, admin-plan và rollout drill dùng cùng điều kiện `deploy_env_pass`; rollout so allowlist ứng viên với nhánh bảo vệ; repo mẫu hợp lệ khai danh sách có thể rỗng (nguồn: audit:AUD-XFEAT-059) (files: scripts/xt_ops_setup.py, scripts/xt_release_ops.py, tests/test_admin_plan.py, tests/test_factory_operations.py, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `python3 -m unittest tests.test_admin_plan tests.test_factory_operations tests.test_deploy_env_allowlist`

### Lát 3 — Phát hiện bổ sung ở `feb86abd` theo D-640

- [x] `T-5092` (nguồn: audit:AUD-CODE-069) Từ chối `--cost ''` trước khi thực thi Gate hoặc ghi dấu review, vẫn chấp nhận bỏ cờ (files: scripts/xt.py, tests/test_cost_flag.py, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `python3 -m unittest tests.test_cost_flag`
- [ ] `T-5093` (nguồn: audit:AUD-XFEAT-061) API thống kê PR dùng cùng repo và host đã xác minh với API danh sách. Giữ khả năng chọn repo của CLI (files: scripts/xt_app/api_pr.py, tests/test_app_pr.py, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `python3 -m unittest tests.test_app_pr.PrsTest tests.test_app_pr.PrStatsTest`

### Lát 4 — Hồ sơ license verify-render theo D-642

- [x] `T-5095` AUD-DEP-041: bổ sung inventory bốn gói npm ghim của verify-render và chứng cứ license trực tiếp/bắc cầu. Kiểm bảng khớp phiên bản trong lock (nguồn: audit:AUD-DEP-041, D-642) (files: docs/ops/DEPENDENCIES.md, tests/test_ci.py, tests/fixtures/autonomy/scope.json, docs/ops/AUDIT-STATUS.md, CHANGELOG.md; topo: review) — Gate: `python3 -m unittest tests.test_ci.SupplyChainArtifactsTest`
