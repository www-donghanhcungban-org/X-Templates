# PLAN X-Templates 2026-11-24 — nâng trần sau báo cáo đánh giá ngoài (bằng chứng, số đo, UI/UX)

> Duyệt: D-571 (phiên chính tự duyệt; chủ dự án yêu cầu "phân tích đánh giá lại nhận định này, lên kế hoạch nâng trần hoàn thiện dự án") · Căn cứ: [đối chiếu báo cáo](../../research/2026-11-24-external-review-reassessment.md) — các phát hiện đã tái hiện ở `b82e369`

## Tóm tắt
- Thứ tự: bằng chứng đúng → ranh giới thực thi → số đo thật → UI/UX có pilot → lan truyền và nợ lõi. Pilot chạy trên bộ kiểm báo sạch sai hoặc sổ thiếu sự kiện thì số đo không dùng được, nên hai đợt đầu đi trước.
- Mảng UI/UX không thêm luật MUST. Việc là nối cổng có sẵn vào starter và sản phẩm, thêm đường thiết kế (brief, phương án, lý do chọn) và thử tác vụ với người thật.
- Mỗi task "nối luồng" có Gate đi qua lệnh thật trong repo tạm; không nhận Gate chỉ đưa dữ liệu giả vào bộ tính (bài học `T-4009`).
- Không làm: đổi cấu hình tự chủ (L3, review optional, agent ký) — báo cáo không yêu cầu; thêm người duyệt mọi PR; design system lớn trước khi có một luồng đạt.

## Ngân sách
- Số vòng: mặc định `--single-session` mỗi đợt · Chi phí ngoài phiên: 0 cho đợt 1–3 và 5; đợt 4 cần môi trường production của dự án đích · Timeout Gate: 1200 giây · Mỗi task một PR (`LOOP-DESIGN-029`).

## Việc của người (không chặn đợt 1–3)

| Việc | Chặn task | Ghi chú |
|---|---|---|
| Áp ruleset tag `v*` live và cấp danh tính phát hành | `T-4007` ở PLAN-improve, `T-5008` | Lệnh qua `xt.py admin-plan --script`; quyền admin repo |
| Cấp `XT_STEWARD_TOKEN` | `T-5018` | RUNBOOK-PR-STEWARD §1 |
| Mời 3–5 người đúng vai trò thử tác vụ; cấp môi trường production và khoá của Hotel Manager | `T-5017` | Mẫu nhỏ, nghiên cứu hình thành |

## Mốc "đã nâng trần" (đo được)

| Mốc | Điều kiện |
|---|---|
| Bằng chứng | Mọi loại `static-check` đỏ hoặc không kết luận khi container sai kiểu; kết quả kèm số mục đã kiểm |
| Số đo | Một lát đi qua lệnh thật sinh đủ 9 loại sự kiện; báo cáo có tỷ lệ bao phủ; chi phí gồm lượt đỏ |
| Ranh giới | Ruleset tag live có biên bản diễn tập; adapter production chạy với allowlist khai rõ |
| UI/UX | Starter xanh với ma trận viewport, bàn phím, axe, contrast trong CI mặc định; một pilot có brief, phương án, số thử tác vụ, receipt production và rollback |
| Lõi | `xt.py` và `guard.py` không tăng dòng; một module guard tách có parity |

## Task

### Đợt 1 — bằng chứng đúng
- [ ] `T-5001` `sbom`/`vex`: container sai kiểu (`components`, `dependencies`, `statements`, `products`…) sinh phát hiện cấu trúc thay vì thành danh sách rỗng; JSON thêm số mục đã kiểm; sửa các test đang khẳng định hành vi cũ (files: scripts/xt_checks/kind_sbom.py, scripts/xt_checks/kind_vex.py, scripts/xt_checks/__init__.py, tests/test_check_sbom.py, tests/test_check_vex.py, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_check_sbom tests.test_check_vex tests.test_static_check`
- [ ] `T-5002` test tính chất cho mọi loại `static-check`: với mỗi khoá container của đầu vào, thay bằng chuỗi/số/`null` thì kết quả không được sạch; sửa các loại rơi (sau: T-5001; files: tests/test_static_check_shape.py, scripts/xt_checks/) — Gate: `python3 -m unittest tests.test_static_check_shape`
- [ ] `T-5003` `xt_pack --strict` đòi đủ `PACKAGES` (thư mục có và có `__init__.py`); `verify` chạy một lệnh của từng gói từ chính `.pyz` (files: scripts/xt_pack.py, tests/test_pack.py, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_pack`
- [ ] `T-5004` bộ dò đổi lệnh trong tài liệu thực thi dùng chính parser chạy lệnh và giữ cặp ID–lệnh; đóng AUD-HAR-478 trước hạn (files: scripts/xt.py, tests/test_executable_docs.py, docs/ops/AUDIT-STATUS.md, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_executable_docs`
- [ ] `T-5005` sửa `UX-VISUAL-009`: tách ảnh nét ở DPR cao, reflow ở 320 CSS px và phóng chữ 200 %; không dùng `deviceScaleFactor` làm zoom; cập nhật bảng công cụ cùng tệp và skill `ui-verify` nếu lặp lại (files: framework/06-design-ux/motion-and-visual-quality.md, .claude/skills/ui-verify/SKILL.md, CHANGELOG.md) — Gate: `python3 scripts/xt.py validate`
- [ ] `T-5006` quy ước Gate cho task nối luồng: `LOOP-DESIGN` thêm một mục SHOULD "Gate của task nối luồng chạy lệnh thật, không chỉ bộ tính trên dữ liệu giả"; ghi đính chính `T-4009` ở PLAN-improve (không bỏ tick, thêm dòng trỏ `T-5009`) (files: framework/11-autonomous-loop/loop-design.md, docs/autopilot/PLAN-improve-2026-11-23.md, CHANGELOG.md) — Gate: `python3 scripts/xt.py validate`

### Đợt 2 — ranh giới thực thi
- [ ] `T-5007` adapter triển khai: bỏ `GIT_CONFIG_*`, `GIT_SSH_COMMAND`, `GIT_EXEC_PATH` và họ biến cấu hình Git khỏi môi trường mặc định; `deploy_env_pass:` khai rỗng nghĩa là allowlist rỗng, khác với không khai; môi trường production đòi allowlist đã khai (sau: T-5001; files: scripts/xt.py, tests/test_deploy_env.py, tests/test_deploy_env_allowlist.py, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_deploy_env tests.test_deploy_env_allowlist tests.test_deploy_prod`
- [ ] `T-5008` ADR "merge intent": một bản ghi host, repo, PR, expected_head do `pr next` sinh và executor thực hiện đúng; guard chặn `gh pr merge` thiếu pin HEAD trong phiên tự hành và xử `GH_REPO`/`GH_HOST` như `--repo`; đóng AUD-HAR-492 (sau: T-5007; files: docs/adr/, .claude/hooks/guard.py, scripts/xt.py, tests/test_merge_verdict_corpus.py, tests/fixtures/autonomy/, docs/ops/AUDIT-STATUS.md, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_merge_verdict_corpus tests.test_merge_verdict_codes tests.test_merge`
- [ ] `T-5020` sau khi chủ repo xong `T-4007`: ghi phép thử ruleset tag và kiểm quyền sửa/xoá asset của release vào `docs/ops/TAG-RULESET-DRILL.md` (việc của người mở khoá; files: docs/ops/TAG-RULESET-DRILL.md) — Gate: `test -s docs/ops/TAG-RULESET-DRILL.md && python3 scripts/xt.py validate`

### Đợt 3 — số đo thật
- [ ] `T-5009` nối sáu nguồn còn thiếu của sổ lát theo bảng SPEC-slice-ledger: `requirement` (`loop init`), `pr` và `merged` (`pr next`), `artefact` và `deployed` (receipt `deploy`), `incident` (`incident check`); test tích hợp chạy các lệnh thật trong repo tạm rồi đọc đủ 9 loại (sau: T-5006; files: scripts/xt.py, scripts/xt_flow.py, tests/test_slice_ledger_e2e.py, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_slice_ledger_e2e tests.test_slice_ledger tests.test_flow`
- [ ] `T-5010` `xt_flow.report()` thêm tỷ lệ bao phủ dữ liệu mỗi lát (loại sự kiện có và thiếu); chỉ số thiếu nguồn giữ `null` kèm lý do; `loop record --cost` ghi cả lượt Gate đỏ (sau: T-5009; files: scripts/xt.py, scripts/xt_flow.py, tests/test_flow.py, tests/test_slice_ledger.py, docs/specs/SPEC-slice-ledger.md, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_flow tests.test_slice_ledger`
- [ ] `T-5011` xuất sổ lát thành lịch sử bền qua worktree và phiên (lệnh xuất gộp, có nguồn gốc commit; CI lưu làm artefact) (sau: T-5010; files: scripts/xt_flow.py, tests/test_flow.py, .github/workflows/, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_flow`

### Đợt 4 — UI/UX có kết quả kiểm chứng
- [ ] `T-5012` starter `web-api-ts`: màu về token ngữ nghĩa có cặp contrast khai rõ; `pack_preview` thêm ma trận 1280/390/320 px, đi bàn phím toàn luồng, axe, ảnh từng trạng thái (loading, rỗng, lỗi, thành công); nối vào `pack-web-api.yml` (sau: T-5005; files: framework/templates/packs/web-api-ts/starter/, tests_e2e/, tests/test_pack_ui.py, .github/workflows/pack-web-api.yml, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_pack_ui tests.test_packs`
- [ ] `T-5013` `verify-render`: chạy lại axe ở viewport hẹp; báo cáo ghi viewport, theme, trạng thái, số phần tử đã đo và không đo được; có chế độ cổng phát hành mà `UNMEASURED` làm đỏ trừ ngoại lệ có ghi (sau: T-5012; files: framework/templates/ui-gates/verify-render.mjs, framework/templates/ui-gates/README.md, tests/, CHANGELOG.md) — Gate: `python3 scripts/xt.py validate`
- [ ] `T-5014` đường thiết kế: mẫu `DESIGN-BRIEF.md` (người dùng chính, một tác vụ, thiết bị, dữ liệu dài/rỗng, tiêu chí thành công), mẫu ghi 2–3 phương án và lý do chọn, mẫu biên bản thử tác vụ (số người hoàn thành, thời gian, lỗi thao tác, chỗ cần trợ giúp); skill `ui-verify` thêm bước rà hình ảnh toàn luồng; không thêm MUST (sau: T-5013; files: framework/templates/, .claude/skills/ui-verify/SKILL.md, framework/06-design-ux/README.md, CHANGELOG.md) — Gate: `python3 scripts/xt.py validate`
- [ ] `T-5015` máy kiểm cấu trúc gói bằng chứng thiết kế (brief có đủ trường, có ≥ 2 phương án, có biên bản thử tác vụ hoặc ghi "chưa thử") dưới dạng một loại `static-check` (sau: T-5014, T-5002; files: scripts/xt_checks/, tests/, docs/adr/0099-static-check-kinds.md, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_static_check tests.test_static_check_shape`
- [ ] `T-5017` pilot nghiệp vụ mới có UI trên Hotel Manager, đo từ trước phân tích yêu cầu tới kiểm bản tại đích: brief → phương án → prototype dữ liệu thật → cổng UI trong CI sản phẩm → thử tác vụ → production và rollback có receipt → theo dõi lỗi; sổ lát đủ 9 loại sự kiện (việc của người mở khoá; sau: T-5011, T-5015, T-5020; files: research/, docs/ops/) — Gate: `grep -l 'thử tác vụ' research/*-ui-pilot.md && python3 scripts/xt.py validate`

### Đợt 5 — lan truyền và nợ lõi
- [ ] `T-5016` trần dòng cho `scripts/xt.py` và `.claude/hooks/guard.py` trong test ngân sách: không vượt số dòng hiện tại, nới chỉ bằng ADR (ADR-0092); logic mới vào module riêng (files: tests/test_docs_budget.py, scripts/AGENTS.md, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_docs_budget`
- [ ] `T-5018` cắt bản chứa đợt 1–3 rồi nâng năm dự án đích lên bản đó; registry bổ sung `type`, `risk`, `pack`, môi trường, release, SLO (việc của người mở khoá; sau: T-5011; files: VERSION, CHANGELOG.md, docs/ops/registry.json) — Gate: `python3 scripts/xt.py release-check`
- [ ] `T-5019` tách lát đầu của guard theo PLAN-guard-split (phân tích lệnh) có parity trên corpus autonomy; đo lại thời gian hook trong cùng container trước và sau (sau: T-5008, T-5016; files: .claude/hooks/, tests/, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_merge_verdict_corpus tests.test_guard_exec_class`

## Thứ tự và cửa
1. Đợt 1 làm ngay, sáu PR nhỏ độc lập trừ `T-5002` sau `T-5001`. `T-5016` có thể làm cùng đợt 1 vì rẻ và chặn nợ tăng.
2. Đợt 2 và 3 chạy song song được (khác tệp trừ `scripts/xt.py`: một executor cho tệp nóng, tuần tự).
3. Đợt 4: `T-5012`…`T-5015` không cần người; `T-5017` mở khi ba việc của người đã có và đợt 3 xong.
4. Hạn có sẵn giữ nguyên và đi trước: 2026-12-02 bỏ `pull_request_target` khỏi `pr-review.yml`.
