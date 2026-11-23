# PLAN cải tiến 2026-11-23 — thực thi nhất quán chính sách tự chủ, đo toàn tuyến, một tuyến production

> Duyệt: D-543 (phiên chính tự duyệt nội dung; chủ dự án merge PR chứa tệp này là chốt kế hoạch) · Blueprint: BLUEPRINT.md
> Nguồn: đề xuất của chủ dự án ngày 2026-11-23 (18 thay đổi, 6 nhóm, 5 đợt) · Đối chiếu với mã: [đánh giá](../../research/2026-11-23-improvement-plan-review.md) ở `main` `9c014bb2`
> **Trạng thái: đã chốt, CHƯA thực thi.** Chỉ `loop init` khi chủ dự án báo thực thi.

- Vấn đề: chính sách tự chủ đã chọn (L3, review không bắt buộc, agent ký) chưa được máy thực thi nhất quán; review và kiểm còn lặp; chưa có nghiệp vụ mới nào đi hết tuyến tới production kèm số đo.
- Người dùng: chủ dự án và các phiên agent làm việc trên khung và dự án đích.
- Một chỉ số: một lát nghiệp vụ mới tới production có đủ chuỗi yêu cầu → task → PR → artefact → deployment trong sổ, và `cost_usd_per_slice`, `ever_conflicted_pr_rate`, `escaped_after_merge` đọc được từ sổ đó (có số, hoặc `null` kèm lý do).
- Không làm: thêm người duyệt mặc định; đặt chỉ tiêu tỷ lệ PR phải review; thêm pack, host hay worker trước khi có bằng chứng; đưa bộ nhớ dài hạn, thu thập hoạt động, điều khiển desktop vào khung.

## Tóm tắt

Giữ nguyên bốn quyết định nền của đề xuất: `merge_autonomy: L3`, `merge_review: optional`, `merge_hard_exceptions: auto`, `release_signoff: agent`. Giữ thứ tự năm đợt theo kết quả. Các chỗ chỉnh so với bản gốc, căn cứ ở bản đánh giá:

1. **Thành task máy kiểm.** Đợt 1 và đợt 2 viết thành 24 task mới có ID, Gate và phạm vi file, cộng `T-3555` giữ ở PLAN gốc. Đợt 3–5 giữ dạng khung có điều kiện vào; mỗi đợt lập PLAN riêng khi tới cửa, vì nội dung phụ thuộc số đo và việc của người.
2. **Không mở việc trùng.** Mục 05, 08, 10, 12, 14, 16 trùng `T-3858`, `T-3863`, `T-3854`, `T-3851`, `T-3852`, `T-3865` đang mở ở [PLAN-factory-e2e](PLAN-factory-e2e.md). Bản này chỉ thêm phần còn thiếu và trỏ về ID cũ.
3. **Mục 04 mở rộng.** Guard cho qua mọi verdict khác `merge` và ca lệch head ở chính sách mặc định, không riêng làn `derived` và PR fork của `AUD-HAR-454`.
4. **Mục 05 sửa mẫu trước khi áp.** `tags.json` hiện có `bypass_actors: []` kèm luật `creation`: áp vào là chặn workflow phát hành. Tra tài liệu GitHub hiện hành, tách ruleset tạo và ruleset sửa/xoá, rồi chủ repo mới áp.
5. **Mục 07 đi hai bước.** Bỏ ngay biến khởi động trình thông dịch (không phá tương thích); allowlist khai tên bật mặc định ở bản MINOR sau khi canary chạy được.
6. **Mục 13 không lặp phần đo** (đã xong ở #746, D-542). Tách sâu `guard.py` (`T-3987`…`T-3990`) lùi về đợt 4 đúng điều kiện đề xuất nêu; `T-3996` (đo, chỉ đọc) làm lúc nào cũng được. Lý do thêm: mục 04 sửa cùng tệp nóng.
7. **Mục 03 bỏ "evidence cache".** Phần CI đã có (`concurrency`, cache theo lockfile, job `quality`). Dùng lại bằng chứng cũ là rủi ro mới mà chưa có số đo cho thấy cần; chỉ sửa `test-select` và đo số run trước.
8. **Thêm hai việc đề xuất bỏ sót:** hạn 2026-12-02 của `T-3555`; bootstrap môi trường (mỗi container mới đang phải dựng tay, cổng cục bộ chạy trên 3.15.0b4 trong khi CI dùng 3.15.2).
9. **Tách việc của người** thành mục riêng bên dưới; agent chuẩn bị phần trong repo rồi `loop defer`.

## Ánh xạ 18 mục

| Mục | Nhà trong PLAN | Đợt |
|---|---|---|
| 01 Chính sách điều phối | `T-3997`, `T-3998`, `T-4002` | 1 |
| 02 Rà diff tích luỹ, dùng lại bằng chứng | `T-4013` | 2 |
| 03 Kiểm trùng, `test-select` | `T-4009` (đo), `T-4011`, `T-4012` | 1–2 |
| 04 Quyết định chặn tới điểm merge | `T-3999`…`T-4001` | 1 |
| 05 Tag và danh tính phát hành | `T-4004`…`T-4006`; phần còn lại của `T-3858` | 1 |
| 06 Tài liệu có khả năng thực thi | `T-4003` | 1 |
| 07 Môi trường lệnh triển khai | `T-4014`, `T-4015` | 2 |
| 08 Archive và receipt đã attest | `T-4016`, `T-4017` | 2 |
| 09 Trạng thái và ứng viên mới | `T-4018`…`T-4020` | 2 |
| 10 Pilot production | `T-3863` (PLAN-factory-e2e), PLAN đợt 3 | 3 |
| 11 Starter theo rủi ro pilot | PLAN đợt 3 | 3 |
| 12 Chi phí và thời gian theo lát | `T-4007`, `T-4008`; tổng hợp ở `T-3854` | 1, 3 |
| 13 Tách lõi sau khi đo | đo: xong (#746); `T-3996`, `T-3987`…`T-3990` (PLAN-guard-split) | 4 |
| 14 Tệp dùng chung, xung đột | `T-3851`, `T-3852` (PLAN-factory-e2e) | 4 |
| 15 Registry có bằng chứng | PLAN đợt 3 | 3 |
| 16 Canary nâng khung | `T-3865` (PLAN-factory-e2e) | 3 |
| 17 Bootstrap, host thật | `T-4010` (bootstrap); kiểm host ở PLAN đợt 4 | 1, 4 |
| 18 Màn trạng thái dùng `xt_flow` | PLAN đợt 4 | 4 |

## Ngân sách

- Số vòng: mặc định `--single-session`, mỗi đợt một lần `loop init` · Chi phí ngoài phiên: 0 tới hết đợt 2 · Timeout Gate: 1200 giây.
- Hạn thật: 2026-12-02 (`T-3555`); 2027-01-21 (xét lại hàng rào guard, các chấp nhận `AUD-HAR-452/453/454`, `AUD-CI-036`). Các đợt không cam kết số ngày.

## Việc của người (agent chuẩn bị phần trong repo, rồi `loop defer`)

| Việc | Cần cho | Agent chuẩn bị |
|---|---|---|
| Áp ruleset tag live và cấp danh tính phát hành (GitHub App hoặc khoá cho `XT_RELEASE_TOKEN`) — quyền admin repo | `T-4006`, cửa đợt 2 | Mẫu ruleset đã sửa, lệnh qua `xt.py admin-plan --script` |
| Secret `XT_STEWARD_TOKEN` | `T-3865`, cửa đợt 3 | RUNBOOK-PR-STEWARD §1 đã có |
| Chọn sản phẩm pilot và **một** yêu cầu từ backlog thật; đích và khoá production; thêm repo sản phẩm vào phiên | cửa đợt 3 | Bảng dữ kiện từng ứng viên (đích triển khai đã xác minh hay chưa) |
| Phiên thật trên host khác (Codex trước) | đợt 4, mục 17 | Kịch bản kiểm: cho phép, chặn, lỗi hook, timeout, trust, resume |

## Điểm dừng bắt buộc về hành động

- Dữ liệu người dùng thật, tiền thật, khoá thật, triển khai production: `- grant:` trong PLAN đợt 3 hoặc `loop defer`.
- Thay đổi hàng rào, workflow, ruleset, khoá chính sách: rà độc lập một lượt ở head trước merge theo ADR của `T-3997`.
- Không ký chồng hồ sơ 3.35.0; ứng viên mới có GO-NO-GO riêng (`T-4020`).

## Thứ tự và lý do

1. Lát 1A trước mọi lát chạm hàng rào: nó định nghĩa khi nào cần rà sớm, các lát sau áp đúng luật đó.
2. Lát 1B trước 1C: máy chỉ cưỡng chế ngoại lệ mới khi quyết định chặn đã giữ được tới điểm merge (điều kiện của đề xuất).
3. Lát 1D, 1E, 1F độc lập file với 1A–1C, làm xen được. `guard.py` và `xt.py` mỗi tệp một đầu mối tại một thời điểm. `T-3555` (ở PLAN gốc của nó) làm sớm trong đợt 1 vì hạn 2026-12-02.
4. Đợt 2 mở khi lát 1A–1C xong. Việc của người ở lát 1D không chặn lát 2A, 2B, 2C, 2E; chỉ lát 2D (`T-4016`) chờ `T-4006`. Ứng viên 3.36.0 (`T-4020`) đứng cuối đợt 2.

## Task

### Lát 1A — một nhà cho chính sách rà sớm (mục 01, phần văn bản)
- [ ] `T-3997` ADR mới "Rà độc lập sớm theo tác động tức thì" (sửa nhịp 1 của ADR-0080, giữ ADR-0079): lớp ngoại lệ gồm đúng những thay đổi có hiệu lực ngay khi merge mà **chính nó là lớp đỡ** — hook và `settings.json` của harness (kể cả bản sinh cho host khác), `.github/workflows/*`, `.github/rulesets/*`, khoá chính sách của `xt.yaml` (`merge_*`, `release_signoff`, `delivery_phase`, `commit_gate`, `ai_attribution`), và nhánh tự triển khai production sau merge do dự án đích khai. Không gồm `scripts/*` nói chung (lớp đỡ còn lại: CI, ruleset, cổng ký), không gồm văn xuôi thuần. Chính sách đọc từ nhánh đích; nhãn hay cấu hình trong chính PR không tự miễn. ADR quyết luôn: PR Dependabot nâng action trong workflow xử lý thế nào; khoá tắt nằm ở đâu và ai được đổi (files: docs/adr/) — Gate: `git grep --untracked -qiE '^# ADR-[0-9]+: .*tác động tức thì' -- docs/adr && python3 scripts/xt.py validate`
- [ ] `T-3998` Đồng bộ một nhà: bảng năm hàng của đề xuất §2 vào `stop-points-and-escalation.md`; `/complete`, `/autopilot`, `/review`, bảng điều phối của `orchestration-and-subagents.md`, mẫu PLAN và `PLAN-guard-split-2026-11-22` chỉ liên kết về đó, bỏ câu "lát mã chỉ merge sau review sạch ở head" làm mặc định; nghi ngờ cụ thể thì xác minh hẹp có đầu vào, kết quả cần kiểm và điểm dừng, không mở lại review toàn PR (sau: T-3997; files: framework/11-autonomous-loop/, .claude/skills/, framework/templates/PLAN.md, docs/autopilot/PLAN-guard-split-2026-11-22.md) — Gate: `python3 -m unittest tests.test_check_links && python3 scripts/check-links.py && python3 scripts/xt.py validate`

### Lát 1B — quyết định chặn giữ tới điểm merge (mục 04; đổi hàng rào, rà sớm theo T-3997)
- [ ] `T-3999` Viết test trước và xem đỏ ở nhánh đích: ma trận verdict (`merge`, `wait`, `human`, `review`, `fix`, `update`, lỗi) × đường vào (`gh pr merge` ghim head, `gh api` REST merge, tool MCP merge) × chính sách (mặc định, `XT_GUARD_POLICY=strict`). Rồi sửa: mã quyết định riêng đặt ở **nơi sinh**, không suy từ câu giải thích — chưa đủ điều kiện, lệch head, chưa xác minh được; chính sách mặc định chặn cả ba, strict giữ hỏi; ca `merge` đúng head vẫn `allow`. Given PR có verdict `wait` vì CI đang chạy, When agent gọi merge ghim đúng head, Then guard chặn kèm mã; ca biên: `merge-check` lỗi mạng, head đổi giữa lúc kiểm và lúc merge (sau: T-3997; topo: review; files: .claude/hooks/guard.py, tests/test_merge_verdict_codes.py) — Gate: `python3 -m unittest tests.test_merge_verdict_codes`
- [ ] `T-4000` Nhất quán giữa các đường vào và không hồi quy: steward và `pr next` chỉ merge khi `merge-check` trả `merge` ở head đã đọc lại ngay trước merge; cập nhật corpus `guard.json`, oracle và `autonomy-bench` cho mã mới (sau: T-3999; files: .claude/hooks/, tests/) — Gate: `python3 -m unittest tests.test_green_gh tests.test_green_shell tests.test_audit_dot4_har && python3 scripts/xt.py autonomy-bench`
- [ ] `T-4001` Văn bản và sổ khớp mã: `AGENTS.md` §5 và `stop-points-and-escalation.md` mô tả đúng nhóm máy chặn; `AUD-HAR-454` chuyển `đã sửa` kèm số PR; CHANGELOG có dòng **Dự án đích** (agent merge khi `merge-check` chưa `merge` nay bị chặn ở chính sách mặc định) (sau: T-4000) — Gate: `python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md --strict && python3 scripts/xt.py changelog-check`

### Lát 1C — máy cưỡng chế rà sớm, phân loại tài liệu chạy được (mục 01 phần máy, mục 06)
- [ ] `T-4002` `merge-check` và `pr next` trả `review` kèm lý do máy đọc cho PR chạm lớp ngoại lệ của T-3997 kể cả khi `merge_review: optional`, theo đường `protected` sẵn có; tập đường dẫn và khoá đọc từ nhánh đích nên PR sửa chính sách được xét theo bản cũ; PR ngoài lớp ngoại lệ không đổi hành vi (bench giữ nguyên) (sau: T-3998, T-4001; topo: review; files: scripts/xt.py, tests/test_immediate_effect_review.py) — Gate: `python3 -m unittest tests.test_immediate_effect_review`
- [ ] `T-4003` Nợ review tính theo **dòng đổi** ở tài liệu có lệnh chạy được: diff chạm dòng `Kiểm:` của `BLUEPRINT.md`, dòng Gate hoặc `- grant:` của `docs/**/PLAN*.md`, lệnh trong skill và mẫu thì tính như mã; sửa mô tả thuần không sinh nợ và không sinh reviewer. Given PR chỉ sửa câu chữ trong `BLUEPRINT.md`, Then `review_debt` không đổi; Given PR đổi một lệnh `Kiểm:`, Then tệp vào nợ (sau: T-4002; files: scripts/xt.py, tests/test_executable_docs.py) — Gate: `python3 -m unittest tests.test_executable_docs`

### Lát 1D — tag và danh tính phát hành (mục 05; phần ruleset của T-3858)
- [ ] `T-4004` `researcher` tra tài liệu GitHub hiện hành, ghi ngày: loại actor vào được `bypass_actors` của ruleset tag, `GITHUB_TOKEN` có vào được không, bypass đặt theo ruleset hay theo luật, hành vi luật `creation` với workflow, và cách lưu asset bất biến theo bản phát hành (dùng cho T-4016) (files: research/) — Gate: `ls research/*-tag-ruleset-release-identity.md && python3 scripts/xt.py validate`
- [ ] `T-4005` Sửa mẫu theo T-4004: quyền tạo tag tách khỏi quyền sửa và xoá (hai ruleset nếu bypass đặt theo ruleset); `install.py --with-github`, `admin-plan` và script cho chủ repo cùng một mẫu, hết mâu thuẫn giữa `bypass_actors: []` đã commit và yêu cầu một actor của script; hàng sổ `AUD-HAR-452/453` ghi rõ ruleset tag đã áp live hay chưa (sau: T-4004; files: .github/rulesets/, scripts/install.py, scripts/xt_ops_setup.py, tests/) — Gate: `python3 -m unittest tests.test_ops_setup_edges tests.test_install tests.test_tag_rulesets`
- [ ] `T-4006` Việc của chủ repo: áp ruleset tag live và cấp danh tính phát hành; kiểm trong phạm vi thử cô lập rằng actor thường bị từ chối tạo, sửa, xoá tag `v*`, workflow chuẩn tạo được tag, `v3.35.0` giữ nguyên (sau: T-4005) — Gate: `python3 scripts/xt.py admin-plan --json`

### Lát 1E — sổ số đo tối thiểu và baseline (mục 12, phần đo của mục 03)
- [ ] `T-4007` SPEC sổ lát: một định danh nối yêu cầu, task, PR, artefact, deployment, sự cố; sự kiện ghi từ lệnh đã có (`loop record`, `pr next`, receipt triển khai, `incident`); mỗi lát một tệp để sổ không thành tệp nóng; thời gian song song không cộng thành lead time, chi phí không đếm trùng, dữ liệu thiếu là `null` kèm lý do, giá quy đổi có nguồn và ngày (files: docs/specs/) — Gate: `test -s docs/specs/SPEC-slice-ledger.md && python3 scripts/xt.py validate`
- [ ] `T-4008` Ghi và đọc sổ theo SPEC; `xt_flow.report()` lấy `cost_usd_per_slice`, `ever_conflicted_pr_rate`, `escaped_after_merge` từ sổ, chưa có nguồn thì `null` kèm lý do máy đọc; lượt reviewer ghi lý do gọi, phát hiện được xác nhận và bị bác (sau: T-4007; files: scripts/xt_flow.py, tests/test_slice_ledger.py, tests/test_factory_metrics.py) — Gate: `python3 -m unittest tests.test_slice_ledger tests.test_factory_metrics`
- [ ] `T-4009` Baseline trước mọi tối ưu, cùng định nghĩa cho lần đo sau: 20 PR merge gần nhất — số run CI, runner-minutes, run bị thay thế, lượt reviewer và kết quả; mỗi con số kèm lệnh và ngày (sau: T-4008; files: research/) — Gate: `ls research/*-delivery-baseline.md && python3 scripts/xt.py validate`

### Lát 1F — hạn cứng và chi phí mỗi phiên
- Việc có hạn 2026-12-02, giữ ở PLAN gốc vì ID task không được trùng giữa các PLAN (`tests.test_green_release`): `T-3555` của [PLAN-harden-2026-10-27-loops](PLAN-harden-2026-10-27-loops.md) — bỏ `pull_request_target` khỏi `pr-review.yml`. Làm trong đợt 1 bằng vòng của PLAN đó; việc đầu là tra lại căn cứ và ngày của hạn từ nguồn GitHub hiện hành.
- [ ] `T-4010` Bootstrap tối thiểu (mục 17): một lệnh dựng CPython 3.15.x bản phát hành và công cụ cổng trên `PATH` cho container hay máy mới; `doctor` cảnh báo khi runtime là bản tiền phát hành hoặc khác bản CI ghim; tách rõ ba mốc cài khung, chạy ứng dụng, đủ điều kiện production trong hướng dẫn (files: scripts/dev-task.sh, tests/test_bootstrap.py) — Gate: `python3 -m unittest tests.test_bootstrap`

**Cửa đợt 1:** không đường merge nào còn mất quyết định chặn; lời gọi reviewer nào cũng có lý do ghi được; mẫu ruleset tag đúng và việc áp live đã giao chủ repo; sổ số đo bắt đầu ghi và có baseline.

### Lát 2A — chọn test không sót (mục 03)
- [ ] `T-4011` `test-select` bắc cầu kế thừa qua tệp test khác (`AUD-TEST-131`: lớp nền `TmpRepoCase`, `SignoffRepo`, `ReleaseCase`); regression cho từng ranh giới đã tìm thấy, không thêm test để tăng số (files: scripts/xt.py, tests/test_select_inherit.py) — Gate: `python3 -m unittest tests.test_select_inherit`
- [ ] `T-4012` Tệp chưa track ở cổng commit (`AUD-HAR-443`; cách làm theo D-518: chỉ loại khi guard xác nhận lệnh là `git commit` đứng một mình; đổi hàng rào nên rà sớm) (sau: T-4011; topo: review; files: .claude/hooks/, tests/test_commit_gate_untracked.py) — Gate: `python3 -m unittest tests.test_commit_gate_untracked`

### Lát 2B — bằng chứng review gắn nội dung (mục 02)
- [ ] `T-4013` Bản ghi và dấu review thêm base, phạm vi (tệp và digest diff) và chính sách hiệu lực ở nhánh đích; dấu `xt-review` bản mới đọc được bản cũ; chỉ tái dùng khi máy chứng minh diff trên phạm vi còn y nguyên, cập nhật base hay giải xung đột thì kiểm lại phần bị chạm; rủi ro chấp nhận có chủ, lý do, bằng chứng giảm thiểu, hạn (topo: review; files: scripts/xt.py, tests/test_review_scope.py) — Gate: `python3 -m unittest tests.test_review_scope`

### Lát 2C — môi trường lệnh triển khai (mục 07)
- [ ] `T-4014` Bước 1, không phá tương thích: lệnh `deploy`, `smoke`, `rollback`, `digest` bỏ biến khởi động trình thông dịch và nạp thư viện (`BASH_ENV`, `ENV`, `LD_PRELOAD`, `PYTHON*`, `NODE_OPTIONS`, …); phép thử script khởi động ngoài checkout không chạy; log không chứa giá trị biến (files: scripts/xt.py, tests/test_deploy_env.py) — Gate: `python3 -m unittest tests.test_deploy_env`
- [ ] `T-4015` Bước 2: allowlist theo mẫu `trial_env` — biến hệ thống cần thiết, `PATH` kiểm soát, cấu hình và khoá cấp **theo tên** khai trong `xt.yaml`; thiếu biến đã khai thì báo lỗi nêu tên biến; mặc định bật ở bản MINOR kế, bản này chỉ `doctor` cảnh báo dự án chưa khai (sau: T-4014; files: scripts/xt.py, tests/test_deploy_env.py) — Gate: `python3 -m unittest tests.test_deploy_env tests.test_deploy_run tests.test_deploy_prod`

### Lát 2D — đúng bytes đã attest (mục 08; đóng AUD-CI-036)
- [ ] `T-4016` Workflow phát hành lưu archive và promotion receipt theo phiên bản bất biến tải được (cách lưu theo T-4004); digest trong nghiệm thu và phân phối là một (sau: T-4004, T-4006; topo: review; files: .github/workflows/release-tag.yml, tests/) — Gate: `python3 -m unittest tests.test_release_contract tests.test_release_assets`
- [ ] `T-4017` `release-verify`, `upgrade`, `install.py` tải đúng bytes đó rồi kiểm digest, nguồn, danh tính ký và liên kết tag, commit; sửa một byte, thay receipt, gắn sai nguồn đều bị từ chối; đường dựng lại giữ một bản làm đường lùi (sau: T-4016; files: scripts/xt_distribution.py, tests/) — Gate: `python3 -m unittest tests.test_distribution_bytes tests.test_green_install`

### Lát 2E — trạng thái rõ và ứng viên mới (mục 09)
- [ ] `T-4018` Tách ba trạng thái trong `release-check`: kiểm kỹ thuật đạt, nội dung đã ký đúng vân tay, đã phân phối; tên trạng thái chờ ký không còn nói "human" khi `release_signoff: agent`; lược đồ tăng số, bên đọc (`xt_release_ops`, workflow dự án đích) nhận cả tên cũ một chu kỳ; consumer dựa vào trạng thái đã chấp thuận, không chỉ exit 0 (topo: review; files: scripts/xt.py, scripts/xt_release_ops.py, tests/test_release_states.py) — Gate: `python3 -m unittest tests.test_release_states tests.test_release_signoff tests.test_release_signoff_scale`
- [ ] `T-4019` README lấy "bản đã gắn tag" từ bản đã phát hành và `xt.py checks` kiểm, không sửa tay mỗi lần cắt bản (files: README.md, scripts/xt.py, tests/) — Gate: `python3 -m unittest tests.test_readme_released_tag && python3 scripts/xt.py checks`
- [ ] `T-4020` Ứng viên 3.36.0 qua `/complete`: audit delta, trả nợ review theo lô trên diff tích luỹ, GO-NO-GO mới cho đúng vân tay; không ký chồng hồ sơ 3.35.0 (sau: T-4012, T-4013, T-4015, T-4017, T-4019) — Gate: `python3 scripts/xt.py release-check`

**Cửa đợt 2:** ứng viên mới đúng vân tay; lệnh triển khai không còn nạp ngầm; artefact tải và xác minh được; bằng chứng review không tái dùng sai.

## Đợt 3–5 (khung; mỗi đợt lập PLAN riêng khi tới cửa)

| Đợt | Phạm vi | Điều kiện vào | Điều kiện đi tiếp |
|---|---|---|---|
| 3 Canary và pilot | 16 (`T-3865`), 10 (`T-3863`), 11, 15, tổng hợp 12 (`T-3854`) | Cửa đợt 2; 3.36.0 đã phát hành; ba việc của người ở trên đã có | Nghiệp vụ mới chạy tại đích; nghiệm thu, quan sát, phục hồi và số đo toàn tuyến đạt |
| 4 Tối ưu theo dữ liệu | 13 (PLAN-guard-split), 14 (`T-3851`, `T-3852`), 18, kiểm host của 17 | Có baseline và số đo của pilot | Cải thiện đo được trên cùng môi trường, hành vi giữ đúng; CLI và UI cùng quyết định |
| 5 Mở rộng có kiểm chứng | Mở rộng 16, thêm host hoặc worker theo nhu cầu | Canary qua khoảng quan sát | Mỗi lần mở rộng có giả thuyết lợi ích, tiêu chí quan sát, đường lùi |

Ghi chú cho PLAN đợt 3: chọn sản phẩm pilot theo đích triển khai đã xác minh (hiện DHCB có bằng chứng SSH và health, Hotel Manager chưa có bằng chứng triển khai); mục 11 chỉ làm những rủi ro mà nghiệp vụ được chọn chạm tới, không đánh dấu cả pack sẵn sàng production từ một smoke; registry lên lược đồ mới thêm giai đoạn, thời điểm quan sát và nguồn từng trường, repo đã ở production được tiếp nhận đúng giai đoạn thật.

## Bảng đo

Giữ sáu chỉ số của đề xuất §10 (chi phí mỗi lát, lead time và thời gian chờ, review có ích, CI và tích hợp, lỗi lọt và phục hồi, chi phí lõi). Nguồn: sổ lát (`T-4008`), baseline (`T-4009`), `xt_guard_profile`. Một pilot cho baseline, chưa đủ để kết luận tiết kiệm theo tỷ lệ.
