# PLAN X-Templates 2026-11-24 — nâng trần sau báo cáo đánh giá ngoài (bằng chứng, số đo, UI/UX)

> Duyệt: D-573 (kế thừa quyết định D-571 chưa merge của nhánh; giữ nguyên D-571/D-572 đã có trên `main`) · Chủ dự án yêu cầu "phân tích đánh giá lại nhận định này, lên kế hoạch nâng trần hoàn thiện dự án", sau đó tiếp quản nhánh và merge · Căn cứ: [đối chiếu báo cáo](../../research/2026-11-24-external-review-reassessment.md) — các phát hiện đã tái hiện ở `b82e369`, rà lại kế hoạch trên `7a1cf1d`

## Tóm tắt
- Thứ tự: bằng chứng đúng → ranh giới thực thi → số đo thật → UI/UX có pilot → lan truyền và nợ lõi. Pilot chạy trên bộ kiểm báo sạch sai hoặc sổ thiếu sự kiện thì số đo không dùng được, nên hai đợt đầu đi trước.
- Mảng UI/UX không thêm luật MUST. Việc là nối cổng có sẵn vào starter và sản phẩm, thêm đường thiết kế (brief, phương án, lý do chọn) và thử tác vụ với người thật.
- Mỗi task "nối luồng" có Gate đi qua lệnh thật trong repo tạm; không nhận Gate chỉ đưa dữ liệu giả vào bộ tính (bài học `T-4009`).
- Trạng thái: PR này hoàn thiện kế hoạch, chưa triển khai 20 task bên dưới. Tệp kiểm thử/bộ kiểm mới ghi trong Gate là đầu ra phải tạo ở task tương ứng; không coi lệnh dự kiến là bằng chứng đã chạy.
- Không làm: đổi cấu hình tự chủ (L3, review optional, agent ký) — báo cáo không yêu cầu; thêm người duyệt mọi PR; design system lớn trước khi có một luồng đạt.

## Ngân sách
- Số vòng: mặc định `--single-session` mỗi đợt · Chi phí ngoài phiên: 0 cho đợt 1–3 và 5; đợt 4 cần môi trường production của dự án đích · Timeout Gate: 1200 giây · Mỗi task một PR (`LOOP-DESIGN-029`).

## Việc của người (không chặn các task tự động của đợt 1–3)

| Việc | Chặn task | Ghi chú |
|---|---|---|
| Áp ruleset tag `v*` live và cấp danh tính phát hành | `T-4007` ở PLAN-improve, `T-5020` | Lệnh qua `xt.py admin-plan --script`; quyền admin repo. Chưa có quyền thì defer `T-5020`, vẫn làm `T-5008` |
| Cấp `XT_STEWARD_TOKEN` | `T-5018` | RUNBOOK-PR-STEWARD §1 |
| Mời 3–5 người đúng vai trò thử tác vụ; cấp môi trường production và khoá của Hotel Manager | `T-5017` | Mẫu nhỏ, nghiên cứu hình thành |

## Mốc "đã nâng trần" (đo được)

| Mốc | Điều kiện |
|---|---|
| Bằng chứng | Mọi loại `static-check` đỏ hoặc không kết luận khi container sai kiểu; kết quả kèm số mục đã kiểm |
| Số đo | Test tích hợp diễn tập đủ 9 đường ghi bằng lệnh thật; pilot chỉ ghi sự kiện thực, báo rõ nguồn đã nối và `no_events`/`window_open`; báo cáo có tỷ lệ bao phủ, chi phí gồm lượt đỏ |
| Ranh giới | Ruleset tag live có biên bản diễn tập; adapter production chạy với allowlist khai rõ |
| UI/UX | Starter xanh với ma trận viewport, bàn phím, axe, contrast trong CI mặc định; một pilot có brief, phương án, số thử tác vụ, receipt production và rollback |
| Lõi | `xt.py` và `guard.py` không tăng dòng; một module guard tách có parity |

## Task

### Đợt 1 — bằng chứng đúng
- [ ] `T-5001` `sbom`/`vex`: container sai kiểu (`components`, `dependencies`, `statements`, `products`…) sinh phát hiện cấu trúc thay vì thành danh sách rỗng; JSON thêm số mục đã kiểm; sửa các test đang khẳng định hành vi cũ (files: scripts/xt_checks/kind_sbom.py, scripts/xt_checks/kind_vex.py, scripts/xt_checks/__init__.py, tests/test_check_sbom.py, tests/test_check_vex.py, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_check_sbom tests.test_check_vex tests.test_static_check`
- [ ] `T-5002` test tính chất cho mọi loại `static-check`: với mỗi khoá container theo hợp đồng đầu vào, thay bằng kiểu không hợp lệ (chuỗi/số/`null` khi schema không cho phép) thì kết quả không được sạch; giữ ca đối chứng cho container rỗng hoặc `null` hợp lệ và loại đầu vào văn bản; sửa các loại rơi (sau: T-5001; files: tests/test_static_check_shape.py, scripts/xt_checks/) — Gate: `python3 -m unittest tests.test_static_check_shape`
- [ ] `T-5003` `xt_pack --strict` đòi đủ `PACKAGES` (thư mục có và có `__init__.py`); `verify` chạy một lệnh của từng gói từ chính `.pyz` (files: scripts/xt_pack.py, tests/test_pack.py, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_pack`
- [ ] `T-5004` bộ dò đổi lệnh trong tài liệu thực thi dùng chính parser chạy lệnh và giữ cặp ID–lệnh; đóng AUD-HAR-478 trước hạn (files: scripts/xt.py, tests/test_executable_docs.py, docs/ops/AUDIT-STATUS.md, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_executable_docs`
- [ ] `T-5005` sửa `UX-VISUAL-009`: tách ảnh nét ở DPR cao, reflow ở 320 CSS px và phóng chữ 200 %; không dùng `deviceScaleFactor` làm zoom; cập nhật bảng công cụ cùng tệp và skill `ui-verify` nếu lặp lại (files: framework/06-design-ux/motion-and-visual-quality.md, .claude/skills/ui-verify/SKILL.md, CHANGELOG.md) — Gate: `python3 scripts/xt.py validate`
- [ ] `T-5006` quy ước Gate cho task nối luồng: `LOOP-DESIGN` thêm một mục SHOULD "Gate của task nối luồng chạy lệnh thật, không chỉ bộ tính trên dữ liệu giả"; ghi đính chính `T-4009` ở PLAN-improve (không bỏ tick, thêm dòng trỏ `T-5009`) (files: framework/11-autonomous-loop/loop-design.md, docs/autopilot/PLAN-improve-2026-11-23.md, CHANGELOG.md) — Gate: `python3 scripts/xt.py validate`

### Đợt 2 — ranh giới thực thi
- [ ] `T-5007` adapter triển khai: bỏ `GIT_CONFIG_*`, `GIT_SSH_COMMAND`, `GIT_EXEC_PATH` và họ biến cấu hình Git khỏi môi trường mặc định; `deploy_env_pass:` khai rỗng nghĩa là allowlist rỗng, khác với không khai; môi trường production đòi allowlist đã khai (sau: T-5001; files: scripts/xt.py, tests/test_deploy_env.py, tests/test_deploy_env_allowlist.py, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_deploy_env tests.test_deploy_env_allowlist tests.test_deploy_prod`
- [ ] `T-5008` ADR "merge intent": một bản ghi host, repo, PR, expected_head do `pr next` sinh và executor thực hiện đúng; guard chặn `gh pr merge` thiếu pin HEAD trong phiên tự hành và xử `GH_REPO`/`GH_HOST` như `--repo`; đóng AUD-HAR-492 (sau: T-5007; files: docs/adr/, .claude/hooks/guard.py, scripts/xt.py, tests/test_merge_verdict_corpus.py, tests/fixtures/autonomy/, docs/ops/AUDIT-STATUS.md, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_merge_verdict_corpus tests.test_merge_verdict_codes tests.test_merge`
- [ ] `T-5020` sau khi chủ repo xong `T-4007`: diễn tập theo phạm vi admin đã duyệt, lưu báo cáo và JSON bằng chứng ruleset/release; tạo bộ kiểm đọc bằng chứng thật (repo, ref/digest, danh tính/quyền, thời điểm, lệnh và mã thoát, kết quả mong đợi/quan sát cho tạo/sửa/xoá tag và asset), đối chiếu trạng thái live qua API chỉ đọc; thiếu/bỏ qua/sai kết quả thì đỏ, không thao tác phá huỷ bản phát hành đang dùng (việc của người mở khoá; files: docs/ops/TAG-RULESET-DRILL.md, docs/ops/TAG-RULESET-DRILL.json, tests_e2e/verify_ceiling_evidence.py, tests/test_ceiling_evidence.py) — Gate: `python3 -m unittest tests.test_ceiling_evidence && python3 tests_e2e/verify_ceiling_evidence.py tag-drill docs/ops/TAG-RULESET-DRILL.json`

### Đợt 3 — số đo thật
- [ ] `T-5009` nối sáu nguồn còn thiếu của sổ lát theo bảng SPEC-slice-ledger: `requirement` (`loop init`), `pr` và `merged` (`pr next`), `artefact` và `deployed` (receipt `deploy`), `incident` (`incident check`); test tích hợp chạy các lệnh thật trong repo tạm rồi đọc đủ 9 loại (sau: T-5006; files: scripts/xt.py, scripts/xt_flow.py, tests/test_slice_ledger_e2e.py, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_slice_ledger_e2e tests.test_slice_ledger tests.test_flow`
- [ ] `T-5010` `xt_flow.report()` thêm tỷ lệ bao phủ dữ liệu mỗi lát (loại sự kiện có và thiếu); chỉ số thiếu nguồn giữ `null` kèm lý do; `loop record --cost` ghi cả lượt Gate đỏ (sau: T-5009; files: scripts/xt.py, scripts/xt_flow.py, tests/test_flow.py, tests/test_slice_ledger.py, docs/specs/SPEC-slice-ledger.md, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_flow tests.test_slice_ledger`
- [ ] `T-5011` xuất sổ lát thành lịch sử bền qua worktree và phiên (lệnh xuất gộp, có nguồn gốc commit; CI lưu làm artefact); test tích hợp chạy lệnh xuất thật từ hai worktree, đọc lại ở phiên mới, kiểm chống đếm trùng và nguồn gốc (sau: T-5010; files: scripts/xt.py, scripts/xt_flow.py, tests/test_flow.py, tests/test_slice_export_e2e.py, .github/workflows/, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_slice_export_e2e tests.test_flow`

### Đợt 4 — UI/UX có kết quả kiểm chứng
- [ ] `T-5012` starter `web-api-ts`: màu về token ngữ nghĩa có cặp contrast khai rõ; `pack_preview` thêm ma trận 1280/390/320 px, đi bàn phím toàn luồng, axe, ảnh từng trạng thái (loading, rỗng, lỗi, thành công); tạo runner dựng starter tạm và chạy trình duyệt thật với ca tốt/xấu, nối cùng runner vào `pack-web-api.yml`, ghim phụ thuộc và bootstrap trình duyệt (sau: T-5005; files: framework/templates/packs/web-api-ts/starter/, tests_e2e/pack_ui.py, tests/test_pack_ui.py, .github/workflows/pack-web-api.yml, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_pack_ui tests.test_packs && python3 tests_e2e/pack_ui.py`
- [ ] `T-5013` `verify-render`: chạy lại axe ở viewport hẹp; báo cáo ghi viewport, theme, trạng thái, số phần tử đã đo và không đo được; dùng `--strict` đã có cho cổng phát hành, thêm ngoại lệ có phạm vi/lý do/bằng chứng/hạn, không miễn vi phạm đã đo; test chạy chính script trên trang mẫu qua Chromium (ca đạt, lỗi chỉ xuất hiện ở viewport hẹp, `UNMEASURED` có/không ngoại lệ), nối vào CI và ghim phụ thuộc (sau: T-5012; files: framework/templates/ui-gates/verify-render.mjs, framework/templates/ui-gates/README.md, tests_e2e/verify_render.test.mjs, .github/workflows/pack-web-api.yml, CHANGELOG.md) — Gate: `node --test tests_e2e/verify_render.test.mjs && python3 scripts/xt.py validate`
- [ ] `T-5014` đường thiết kế: mẫu `DESIGN-BRIEF.md` (người dùng chính, một tác vụ, thiết bị, dữ liệu dài/rỗng, tiêu chí thành công), mẫu ghi 2–3 phương án và lý do chọn, mẫu biên bản thử tác vụ (số người hoàn thành, thời gian, lỗi thao tác, chỗ cần trợ giúp); skill `ui-verify` thêm bước rà hình ảnh toàn luồng; không thêm MUST (sau: T-5013; files: framework/templates/, .claude/skills/ui-verify/SKILL.md, framework/06-design-ux/README.md, CHANGELOG.md) — Gate: `python3 scripts/xt.py validate`
- [ ] `T-5015` máy kiểm cấu trúc gói bằng chứng thiết kế dưới dạng loại `static-check design-evidence`: brief đủ trường, ≥ 2 phương án, biên bản thử tác vụ hoặc trạng thái "chưa thử" có cấu trúc; hợp đồng `--opt mode=pilot` đòi kết quả thử thật (số người, hoàn thành, thời gian, lỗi, trợ giúp), từ chối "chưa thử"; test CLI tốt/xấu/sai kiểu và số mục đã kiểm; viết SPEC mới, không sửa ADR cũ (sau: T-5014, T-5002; files: scripts/xt_checks/, tests/test_check_design_evidence.py, tests/test_static_check_shape.py, docs/specs/SPEC-design-evidence.md, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_check_design_evidence tests.test_static_check tests.test_static_check_shape`
- [ ] `T-5017` pilot nghiệp vụ mới có UI trên Hotel Manager, đo từ trước phân tích yêu cầu tới kiểm bản tại đích: brief → phương án → prototype dữ liệu thật → cổng UI trong CI sản phẩm → thử tác vụ → production và rollback có receipt → theo dõi lỗi; sổ ghi mọi sự kiện thực, nguồn chưa có sự kiện báo `no_events`, cửa sổ chưa đóng báo `window_open`, không tạo incident giả; mở rộng bộ kiểm bằng chứng để đối chiếu repo/head/digest của CI, thử trình duyệt, receipt production/rollback và sổ lát, lỗi/mất nguồn thì đỏ; người thử dùng mã ẩn danh (việc của người mở khoá; sau: T-5007, T-5008, T-5011, T-5015, T-5020; files: research/, docs/ops/HOTEL-UI-PILOT.json, tests_e2e/verify_ceiling_evidence.py, tests/test_ceiling_evidence.py) — Gate: `python3 scripts/xt.py static-check design-evidence docs/ops/HOTEL-UI-PILOT.json --opt mode=pilot && python3 -m unittest tests.test_ceiling_evidence && python3 tests_e2e/verify_ceiling_evidence.py pilot docs/ops/HOTEL-UI-PILOT.json`

### Đợt 5 — lan truyền và nợ lõi
- [ ] `T-5016` trần dòng cho `scripts/xt.py` và `.claude/hooks/guard.py` trong test ngân sách: không vượt số dòng hiện tại, nới chỉ bằng ADR (ADR-0092); logic mới vào module riêng (files: tests/test_docs_budget.py, scripts/AGENTS.md, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_docs_budget`
- [ ] `T-5018` cắt bản chứa đợt 1–3 rồi nâng năm dự án đích lên bản đó; registry bổ sung `type`, `risk`, `pack`, môi trường, release, SLO; mở rộng bộ kiểm bằng chứng để đối chiếu release/tag/artifact đã phát hành và đúng năm repo trong registry với PR nâng cấp đã merge, CI xanh ở head đó, manifest phiên bản/hash khớp; thiếu một repo thì chưa tick (việc của người mở khoá; sau: T-5002, T-5003, T-5004, T-5005, T-5008, T-5011, T-5020; files: VERSION, CHANGELOG.md, docs/ops/registry.json, docs/ops/CEILING-ROLLOUT.json, tests_e2e/verify_ceiling_evidence.py, tests/test_ceiling_evidence.py) — Gate: `python3 scripts/xt.py release-check && python3 -m unittest tests.test_ceiling_evidence && python3 tests_e2e/verify_ceiling_evidence.py rollout docs/ops/CEILING-ROLLOUT.json`
- [ ] `T-5019` tách lát đầu của guard theo PLAN-guard-split (phân tích lệnh) có parity trên corpus autonomy; đo lại thời gian hook trong cùng container trước và sau (sau: T-5008, T-5016; files: .claude/hooks/, tests/, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_merge_verdict_corpus tests.test_guard_exec_class`

## Thứ tự và cửa
1. Đợt 1 làm ngay, sáu PR nhỏ độc lập trừ `T-5002` sau `T-5001`. `T-5016` có thể làm cùng đợt 1 vì rẻ và chặn nợ tăng.
2. Đợt 2 và 3 chạy song song được (khác tệp trừ `scripts/xt.py`: một executor cho tệp nóng, tuần tự).
3. Đợt 4: `T-5012`…`T-5015` không cần người; `T-5017` mở khi quyền và môi trường cho pilot đã có cùng mọi task trong `sau:`. `XT_STEWARD_TOKEN` chỉ chặn `T-5018`, không tự biến thành điều kiện của pilot.
4. Hạn có sẵn giữ nguyên và đi trước: 2026-12-02 bỏ `pull_request_target` khỏi `pr-review.yml`.
