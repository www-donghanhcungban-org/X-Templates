# PLAN cải tiến 2026-11-23 — thực thi nhất quán chính sách tự chủ, đo toàn tuyến, một tuyến production

> Duyệt: D-544 (phiên chính tự duyệt sau một lượt rà độc lập; đính chính D-543; chủ dự án merge PR chứa tệp này là chốt kế hoạch) · Blueprint: BLUEPRINT.md
> Nguồn: đề xuất của chủ dự án ngày 2026-11-23 (18 thay đổi, 6 nhóm, 5 đợt) · Đối chiếu với mã: [đánh giá](../../research/2026-11-23-improvement-plan-review.md) ở `main` `9c014bb2`
> **Trạng thái: đang thực thi theo yêu cầu chủ dự án ngày 2026-11-23.** Lát 1A đã merge (#753); lát 1B ghi quyết định D-547 và bằng chứng qua `loop record`.

- Vấn đề: chính sách tự chủ đã chọn (L3, review không bắt buộc, agent ký) chưa được máy thực thi nhất quán; review và kiểm còn lặp; chưa có nghiệp vụ mới nào đi hết tuyến tới production kèm số đo.
- Người dùng: chủ dự án và các phiên agent làm việc trên khung và dự án đích.
- Một chỉ số: một lát nghiệp vụ mới tới production có đủ chuỗi yêu cầu → task → PR → artefact → deployment trong sổ, và `cost_usd_per_slice`, `ever_conflicted_pr_rate`, `escaped_after_merge` đọc được từ sổ đó (có số, hoặc `null` kèm lý do).
- Không làm: thêm người duyệt mặc định; đặt chỉ tiêu tỷ lệ PR phải review; thêm pack, host hay worker trước khi có bằng chứng; đưa bộ nhớ dài hạn, thu thập hoạt động, điều khiển desktop vào khung.

## Tóm tắt

Giữ nguyên bốn quyết định nền của đề xuất: `merge_autonomy: L3`, `merge_review: optional`, `merge_hard_exceptions: auto`, `release_signoff: agent`. Giữ thứ tự năm đợt theo kết quả. Các chỗ chỉnh so với bản gốc, căn cứ ở bản đánh giá:

1. **Thành task máy kiểm.** Đợt 1 và đợt 2 viết thành 25 task mới có ID, Gate và phạm vi file; `T-3555` giữ ở PLAN gốc. Đợt 3–5 giữ dạng khung có điều kiện vào; mỗi đợt lập PLAN riêng khi tới cửa, vì nội dung phụ thuộc số đo và việc của người.
2. **Không mở việc trùng.** Mục 05 và 16 trùng `T-3858`, `T-3865`; mục 14 trùng `T-3851`, `T-3852` đang mở ở [PLAN-factory-e2e](PLAN-factory-e2e.md). Bản này chỉ thêm phần còn thiếu và trỏ về ID cũ; các cạnh `sau:` của PLAN đó giữ nguyên.
3. **Mục 04 là đổi chính sách, không phải sửa lỗi.** `LOOP-STOP-002` chủ ý để merge chưa đủ điều kiện "cho chạy" ở chính sách mặc định với lớp đỡ là CI, ruleset và review. Guard đã chặn verdict `review`, ngoại lệ cứng và ca `merge-check` lỗi; còn đi qua là `wait`, `fix`, `update`, `human` không cứng, `closed` và lệch head. Chặn nốt các ca đó cần ADR sửa ADR-0018/0019 và D-534.
4. **Mục 01 phần máy thu hẹp ADR-0079.** Bắt rà sớm một lớp thay đổi dù `merge_review: optional` là phương án D-533 từng loại; ADR mới phải ghi rõ nó sửa ADR-0079 và vì sao nay chọn khác.
5. **Mục 05 sửa mẫu trước khi áp.** `tags.json` hiện có `bypass_actors: []` kèm luật `creation`: áp vào là chặn workflow phát hành. Ruleset tag **chưa có ở live** (`admin-plan` ngày 2026-11-23: hàng `ruleset` thiếu), nên lý do chấp nhận `AUD-HAR-452/453` hiện chưa có hàng rào thật.
6. **Mục 07 đi hai bước.** Bỏ ngay biến khởi động trình thông dịch (không phá tương thích); allowlist khai tên bật mặc định ở bản MINOR sau khi canary chạy được.
7. **Mục 13 không lặp phần đo** (đã xong ở #746, D-542). Tách sâu `guard.py` (`T-3987`…`T-3990`) lùi về đợt 4 đúng điều kiện đề xuất nêu, thay ý "3.36.0 cùng việc tách guard" của D-541; `T-3996` (đo, chỉ đọc) làm lúc nào cũng được. Lý do thêm: mục 04 sửa cùng tệp nóng.
8. **Mục 03 bỏ "evidence cache".** Phần CI đã có (`concurrency`, cache theo lockfile, job `quality`). Dùng lại bằng chứng cũ là rủi ro mới mà chưa có số đo cho thấy cần; chỉ sửa `test-select` và đo số run trước.
9. **Thêm hai việc đề xuất bỏ sót:** hạn 2026-12-02 của `T-3555`; bootstrap môi trường (mỗi container mới đang phải dựng tay, cổng cục bộ chạy trên 3.15.0b4 trong khi CI dùng 3.15.2).
10. **Tách việc của người** thành mục riêng bên dưới; agent chuẩn bị phần trong repo rồi `loop defer`.

## Ánh xạ 18 mục

| Mục | Nhà trong PLAN | Đợt |
|---|---|---|
| 01 Chính sách điều phối | `T-3997`, `T-3998`, `T-4003` | 1 |
| 02 Rà diff tích luỹ, dùng lại bằng chứng | `T-4014` | 2 |
| 03 Kiểm trùng, `test-select` | `T-4010` (đo), `T-4012`, `T-4013` | 1–2 |
| 04 Quyết định chặn tới điểm merge | `T-3999`…`T-4002` (đóng `AUD-HAR-454`) | 1 |
| 05 Tag và danh tính phát hành | `T-4005`…`T-4007`; rồi tick `T-3858` ở PLAN-factory-e2e | 1 |
| 06 Tài liệu có khả năng thực thi | `T-4004` (đóng `AUD-HAR-460`) | 1 |
| 07 Môi trường lệnh triển khai | `T-4015`, `T-4016`; quyền runner ở PLAN đợt 3 | 2 |
| 08 Archive và receipt đã attest | `T-4017`, `T-4018` (đóng `AUD-CI-036`) | 2 |
| 09 Trạng thái và ứng viên mới | `T-4019`…`T-4021` | 2 |
| 10 Pilot production | PLAN đợt 3 (pilot trên sản phẩm có sẵn); `T-3863` giữ nguyên, xét lại sau pilot | 3 |
| 11 Starter theo rủi ro pilot | PLAN đợt 3 | 3 |
| 12 Chi phí và thời gian theo lát | `T-4008`, `T-4009`; phần so song song với tuần tự ở `T-3854` | 1, 4 |
| 13 Tách lõi sau khi đo | đo: xong (#746); `T-3996`, `T-3987`…`T-3990` (PLAN-guard-split) | 4 |
| 14 Tệp dùng chung, xung đột | `T-3851`, `T-3852` (PLAN-factory-e2e) | 4 |
| 15 Registry có bằng chứng | PLAN đợt 3 | 3 |
| 16 Canary nâng khung | `T-3865` (PLAN-factory-e2e, sau `T-3858`) | 3 |
| 17 Bootstrap, host thật | `T-4011` (bootstrap Python); Node, pnpm, Docker theo pack ở PLAN đợt 3; kiểm host ở PLAN đợt 4 | 1, 3, 4 |
| 18 Màn trạng thái dùng `xt_flow` | PLAN đợt 4 | 4 |

## Ngân sách

- Số vòng: mặc định `--single-session`, mỗi đợt một lần `loop init` · Chi phí ngoài phiên: 0 tới hết đợt 2 · Timeout Gate: 1200 giây.
- Hạn thật: 2026-12-02 (`T-3555`); 2027-01-21 (xét lại hàng rào guard, các chấp nhận `AUD-HAR-452/453/454/460`, `AUD-CI-036`). Các đợt không cam kết số ngày.

## Việc của người (agent chuẩn bị phần trong repo, rồi `loop defer`)

| Việc | Cần cho | Agent chuẩn bị |
|---|---|---|
| Áp ruleset tag live và cấp danh tính phát hành (GitHub App hoặc khoá cho `XT_RELEASE_TOKEN`) — quyền admin repo | `T-4007`, cửa đợt 3 | Mẫu ruleset đã sửa, lệnh qua `xt.py admin-plan --script` |
| Secret `XT_STEWARD_TOKEN` | `T-3865`, cửa đợt 3 | RUNBOOK-PR-STEWARD §1 đã có |
| Chọn sản phẩm pilot và **một** yêu cầu từ backlog thật; đích và khoá production; thêm repo sản phẩm vào phiên | cửa đợt 3 | Bảng dữ kiện từng ứng viên (đích triển khai đã xác minh hay chưa) |
| Phiên thật trên host khác (Codex trước) | đợt 4, mục 17 | Kịch bản kiểm: cho phép, chặn, lỗi hook, timeout, trust, resume |

## Điểm dừng bắt buộc về hành động

- Dữ liệu người dùng thật, tiền thật, khoá thật, triển khai production: `- grant:` trong PLAN đợt 3 hoặc `loop defer`.
- Thay đổi hàng rào, workflow, ruleset, khoá chính sách: rà độc lập một lượt ở head trước merge theo ADR của `T-3997`.
- Không ký chồng hồ sơ 3.35.0; ứng viên mới có GO-NO-GO riêng. `release-check` chạy ở cổng ký sau `loop verify --all`, không nằm trong Gate của task (hàng `verify` tự tham chiếu).

## Thứ tự và lý do

1. Lát 1A trước mọi lát chạm hàng rào: nó định nghĩa khi nào cần rà sớm, các lát sau áp đúng luật đó.
2. Lát 1B trước 1C: máy chỉ cưỡng chế ngoại lệ mới khi quyết định chặn đã giữ được tới điểm merge (điều kiện của đề xuất).
3. Lát 1D, 1E, 1F không chờ 1A–1C. `guard.py` và `xt.py` mỗi tệp một đầu mối tại một thời điểm (đã khai ở `files:`). `T-3555` (ở PLAN gốc của nó) làm sớm trong đợt 1 vì hạn 2026-12-02.
4. Đợt 2 mở khi lát 1C xong (`sau: T-4004` ở task đầu mỗi lát). Việc của người ở `T-4007` không chặn đợt 2 và không chặn ứng viên 3.36.0; nó là điều kiện vào đợt 3.

## Task

### Lát 1A — một nhà cho chính sách rà sớm (mục 01, phần văn bản)
- [x] `T-3997` ADR mới "Rà độc lập sớm theo tác động tức thì". Mục Sửa: ADR-0079 (thu hẹp — lớp ngoại lệ vẫn cần một lượt rà ở head dù `merge_review: optional`; dẫn D-533 đã loại phương án này và nêu căn cứ nay chọn khác: đề xuất của chủ dự án §2) và nhịp 1 của ADR-0080. Lớp ngoại lệ gồm đúng những thay đổi có hiệu lực ngay khi merge mà **chính nó là lớp đỡ**: hook và `settings.json` của harness (kể cả bản sinh cho host khác), `.github/workflows/*`, `.github/rulesets/*`, khoá chính sách của `xt.yaml` (`merge_*`, `release_signoff`, `delivery_phase`, `commit_gate`, `ai_attribution`), nhánh tự triển khai production sau merge do dự án đích khai. Không gồm `scripts/*` nói chung (lớp đỡ còn lại: CI, ruleset, cổng ký), không gồm văn xuôi thuần. Chính sách đọc từ nhánh đích; nhãn hay cấu hình trong chính PR không tự miễn. ADR quyết luôn: PR Dependabot nâng action trong workflow xử lý thế nào; khoá tắt nằm ở đâu và ai được đổi (files: docs/adr/) — Gate: `git grep --untracked -qiE '^# ADR-[0-9]+: .*tác động tức thì' -- docs/adr && python3 scripts/xt.py validate`
- [x] `T-3998` Đồng bộ một nhà: bảng năm hàng của đề xuất §2 vào `stop-points-and-escalation.md`; `/complete`, bảng điều phối của `orchestration-and-subagents.md` và `PLAN-guard-split-2026-11-22` chỉ liên kết về đó, bỏ câu đòi review ở head cho mọi lát mã làm mặc định; nghi ngờ cụ thể thì xác minh hẹp có đầu vào, kết quả cần kiểm và điểm dừng, không mở lại review toàn PR (sau: T-3997; files: framework/11-autonomous-loop/, .claude/skills/, docs/autopilot/PLAN-guard-split-2026-11-22.md) — Gate: `grep -q 'tác động tức thì' framework/11-autonomous-loop/stop-points-and-escalation.md && grep -q 'tác động tức thì' .claude/skills/complete/SKILL.md && grep -q 'tác động tức thì' docs/autopilot/PLAN-guard-split-2026-11-22.md && python3 -m unittest tests.test_check_links && python3 scripts/check-links.py && python3 scripts/xt.py validate`

### Lát 1B — quyết định chặn giữ tới điểm merge (mục 04; đổi hàng rào, rà sớm theo T-3997)
- [x] `T-3999` ADR mới "Guard chặn lệnh merge khi PR chưa đủ điều kiện merge". Mục Sửa: ADR-0018/0019, câu "còn lại mặc định cho chạy" của `LOOP-STOP-002`, D-534. Bảng từng verdict của `merge-check`: đang chặn giữ nguyên (`review`, ngoại lệ cứng, `merge-check` lỗi); xét chặn thêm `wait`, `fix`, `update`, `human` không cứng, `closed`, lệch head — với mỗi ca ghi lớp đỡ phía máy chủ đang có hay không (dự án đích có thể chưa áp ruleset) và cách người merge ở L1/L2 khi cần; `XT_GUARD_POLICY=strict` giữ hỏi (sau: T-3997; files: docs/adr/) — Gate: `git grep --untracked -qiE '^# ADR-[0-9]+: .*chưa đủ điều kiện merge' -- docs/adr && python3 scripts/xt.py validate`
- [x] `T-4000` Viết test trước theo bảng của T-3999 và xem đỏ ở nhánh đích cho các ô đổi quyết định; ô đang chặn là ô ghim hồi quy. Ma trận verdict × đường vào (`gh pr merge` ghim head, `gh api` REST merge, tool MCP merge, adapter của host khác) × chính sách (mặc định, strict). Sửa: mã quyết định riêng đặt ở **nơi sinh**, không suy từ câu giải thích; không dùng lại `UNVERIFIED` cho nghĩa khác; ca `merge` đúng head vẫn `allow`. Given PR có verdict `wait` vì CI đang chạy, When agent gọi merge ghim đúng head, Then guard chặn kèm mã; ca biên: head đổi giữa lúc kiểm và lúc merge (sau: T-3999; topo: review; files: .claude/hooks/guard.py, tests/test_merge_verdict_codes.py) — Gate: `python3 -m unittest tests.test_merge_verdict_codes`
- [x] `T-4001` Không hồi quy và corpus phủ ca mới: `guard.json`, oracle và `autonomy-bench` có ca cho từng verdict vừa chặn ở từng đường vào (test mới khẳng định điều đó); steward và `pr next` chỉ merge khi `merge-check` trả `merge` ở head đọc lại ngay trước merge (sau: T-4000; files: .claude/hooks/, tests/) — Gate: `python3 -m unittest tests.test_merge_verdict_corpus tests.test_green_gh tests.test_green_shell tests.test_signoff2_scripts tests.test_audit_dot4_har && python3 scripts/xt.py autonomy-bench`
- [x] `T-4002` Văn bản và sổ khớp mã: `LOOP-STOP-002`, `AGENTS.md` §5 và `stop-points-and-escalation.md` mô tả đúng nhóm máy chặn; `AUD-HAR-454` chuyển `đã sửa` kèm số PR; CHANGELOG có dòng **Dự án đích** (sau: T-4001; files: framework/11-autonomous-loop/, AGENTS.md, docs/ops/AUDIT-STATUS.md, CHANGELOG.md) — Gate: `grep -qE '^\| AUD-HAR-454 \| [^|]+ \| đã sửa \|' docs/ops/AUDIT-STATUS.md && python3 scripts/xt.py audit check docs/ops/AUDIT-STATUS.md --strict && python3 scripts/xt.py changelog-check && python3 scripts/xt.py autonomy-bench`

### Lát 1C — máy cưỡng chế rà sớm, phân loại tài liệu chạy được (mục 01 phần máy, mục 06)
- [x] `T-4003` `merge-check` và `pr next` trả `review` kèm lý do máy đọc cho PR chạm lớp ngoại lệ của T-3997 kể cả khi `merge_review: optional`, theo đường `protected` sẵn có; tập đường dẫn và khoá đọc từ nhánh đích nên PR sửa chính sách được xét theo bản cũ; PR ngoài lớp ngoại lệ không đổi hành vi (bench giữ nguyên) (sau: T-3998, T-4002; topo: review; files: scripts/xt.py, tests/test_immediate_effect_review.py) — Gate: `python3 -m unittest tests.test_immediate_effect_review`
- [x] `T-4004` Nợ review tính theo **dòng đổi** ở tài liệu có lệnh chạy được (`AUD-HAR-460`, D-535): diff chạm dòng `Kiểm:` của `BLUEPRINT.md`, dòng Gate hoặc `- grant:` của `docs/**/PLAN*.md`, lệnh trong mẫu thì tính như mã; sửa mô tả thuần không sinh nợ và không sinh reviewer. Given PR chỉ sửa câu chữ trong `BLUEPRINT.md`, Then `review_debt` không đổi; Given PR đổi một lệnh `Kiểm:`, Then tệp vào nợ. Hàng sổ `AUD-HAR-460` chuyển `đã sửa` (sau: T-4003; files: scripts/xt.py, tests/test_executable_docs.py, docs/ops/AUDIT-STATUS.md) — Gate: `python3 -m unittest tests.test_executable_docs && grep -qE '^\| AUD-HAR-460 \| [^|]+ \| đã sửa \|' docs/ops/AUDIT-STATUS.md`

### Lát 1D — tag và danh tính phát hành (mục 05; phần ruleset của T-3858)
- [x] `T-4005` `researcher` tra tài liệu GitHub hiện hành, ghi ngày: loại actor vào được `bypass_actors` của ruleset tag, `GITHUB_TOKEN` có vào được không, bypass đặt theo ruleset hay theo luật, hành vi luật `creation` với workflow, và cách lưu asset bất biến theo bản phát hành (dùng cho T-4017) (files: research/) — Gate: `grep -l 'bypass_actors' research/*-tag-ruleset-release-identity.md && python3 scripts/xt.py validate`
- [x] `T-4006` Sửa mẫu theo T-4005: quyền tạo tag tách khỏi quyền sửa và xoá (hai ruleset nếu bypass đặt theo ruleset); `install.py --with-github`, `admin-plan` và script cho chủ repo cùng một mẫu, hết mâu thuẫn giữa `bypass_actors: []` đã commit và yêu cầu một actor của script; `admin-plan --only <hàng>` thoát theo đúng một hàng; hàng sổ `AUD-HAR-452/453` ghi rõ ruleset tag chưa áp live tính đến ngày kiểm (sau: T-4005; files: .github/rulesets/, scripts/install.py, scripts/xt_ops_setup.py, tests/test_tag_rulesets.py, docs/ops/AUDIT-STATUS.md) — Gate: `python3 -m unittest tests.test_ops_setup_edges tests.test_install tests.test_tag_rulesets`
- [ ] `T-4007` Việc của chủ repo: áp ruleset tag live và cấp danh tính phát hành; ghi phép thử trong phạm vi cô lập vào `docs/ops/TAG-RULESET-DRILL.md` — actor thường bị từ chối tạo, sửa, xoá tag `v*`, workflow chuẩn tạo được tag, `v3.35.0` giữ nguyên. Xong thì chạy Gate của `T-3858` ở PLAN-factory-e2e và tick ở đó (sau: T-4006) — Gate: `python3 scripts/xt.py admin-plan --only ruleset && test -s docs/ops/TAG-RULESET-DRILL.md`

### Lát 1E — sổ số đo tối thiểu và baseline (mục 12, phần đo của mục 03)
- [x] `T-4008` SPEC sổ lát: một định danh nối yêu cầu, task, PR, artefact, deployment, sự cố; sự kiện ghi từ lệnh đã có (`loop record`, `pr next`, `pr reviewed`, receipt triển khai, `incident`); mỗi lát một tệp để sổ không thành tệp nóng; thời gian song song không cộng thành lead time, chi phí không đếm trùng, dữ liệu thiếu là `null` kèm lý do, giá quy đổi có nguồn và ngày, lỗi lọt có cửa sổ quan sát và mức độ (files: docs/specs/) — Gate: `grep -q 'cost_usd_per_slice' docs/specs/SPEC-slice-ledger.md && grep -q 'escaped_after_merge' docs/specs/SPEC-slice-ledger.md && python3 scripts/xt.py validate`
- [x] `T-4009` Ghi và đọc sổ theo SPEC; `xt_flow.report()` lấy `cost_usd_per_slice`, `ever_conflicted_pr_rate`, `escaped_after_merge` từ sổ, chưa có nguồn thì `null` kèm lý do máy đọc; lượt reviewer ghi lý do gọi, phát hiện được xác nhận và bị bác (sau: T-4008; files: scripts/xt.py, scripts/xt_flow.py, tests/test_slice_ledger.py, tests/test_factory_metrics.py) — Gate: `python3 -m unittest tests.test_slice_ledger tests.test_factory_metrics`
- [ ] `T-4010` Baseline trước mọi tối ưu, cùng định nghĩa cho lần đo sau: 20 PR merge gần nhất — số run CI, runner-minutes, run bị thay thế, lượt reviewer và kết quả; mỗi con số kèm lệnh và ngày (sau: T-4009; files: research/) — Gate: `grep -l 'runner-minutes' research/*-delivery-baseline.md && python3 scripts/xt.py validate`

### Lát 1F — hạn cứng và chi phí mỗi phiên
- Việc có hạn 2026-12-02, giữ ở PLAN gốc vì ID task không được trùng giữa các PLAN (`tests.test_green_release`): `T-3555` của [PLAN-harden-2026-10-27-loops](PLAN-harden-2026-10-27-loops.md) — bỏ `pull_request_target` khỏi `pr-review.yml`. Làm trong đợt 1 bằng vòng của PLAN đó; việc đầu là tra lại căn cứ và ngày của hạn từ nguồn GitHub hiện hành.
- [x] `T-4011` Bootstrap tối thiểu (mục 17, phần Python): một lệnh dựng CPython ≥ 3.13 (sàn mới, ADR-0094 — máy đã có Python ≥ 3.13 không cần bước này) và công cụ cổng trên `PATH` cho container hay máy chưa có; `doctor` cảnh báo khi runtime là bản tiền phát hành; hướng dẫn tách ba mốc cài khung, chạy ứng dụng, đủ điều kiện production và chỉ công bố hệ điều hành đã kiểm (files: scripts/dev-task.sh, scripts/xt.py, tests/test_bootstrap.py) — Gate: `python3 -m unittest tests.test_bootstrap`

**Cửa đợt 1:** quyết định chặn giữ được tới điểm merge theo bảng của `T-3999`; lời gọi reviewer nào cũng có lý do ghi được; mẫu ruleset tag đúng và việc áp live đã giao chủ repo; sổ số đo bắt đầu ghi và có baseline.

### Lát 2A — chọn test không sót (mục 03)
- [x] `T-4012` `test-select` bắc cầu kế thừa qua tệp test khác (`AUD-TEST-131`: lớp nền `TmpRepoCase`, `SignoffRepo`, `ReleaseCase`); regression cho từng ranh giới đã tìm thấy, không thêm test để tăng số (sau: T-4004; files: scripts/xt.py, tests/test_select_inherit.py) — Gate: `python3 -m unittest tests.test_select_inherit`
- [x] `T-4013` Tệp chưa track ở cổng commit (`AUD-HAR-443`; cách làm theo D-518: chỉ loại khi guard xác nhận lệnh là `git commit` đứng một mình; đổi hàng rào nên rà sớm) (sau: T-4012; topo: review; files: .claude/hooks/, tests/test_commit_gate_untracked.py) — Gate: `python3 -m unittest tests.test_commit_gate_untracked`

### Lát 2B — bằng chứng review gắn nội dung (mục 02)
- [x] `T-4014` Bản ghi và dấu review thêm base, phạm vi (tệp và digest diff) và chính sách hiệu lực ở nhánh đích; dấu `xt-review` bản mới đọc được bản cũ, và guard (`REVIEW_MARK_RE`) cùng bộ lọc của `pr-steward.yml` nhận cả hai để dấu mới không lọt luật chống đăng tay; chỉ tái dùng khi máy chứng minh diff trên phạm vi còn y nguyên, cập nhật base hay giải xung đột thì kiểm lại phần bị chạm; rủi ro chấp nhận có chủ, lý do, bằng chứng giảm thiểu, hạn (sau: T-4004; topo: review; files: scripts/xt.py, .claude/hooks/guard.py, .github/workflows/pr-steward.yml, tests/test_review_scope.py) — Gate: `python3 -m unittest tests.test_review_scope`

### Lát 2C — môi trường lệnh triển khai (mục 07)
- [x] `T-4015` Bước 1, không phá tương thích: lệnh `deploy`, `smoke`, `rollback`, `digest` bỏ biến khởi động trình thông dịch và nạp thư viện (`BASH_ENV`, `ENV`, `LD_PRELOAD`, `PYTHON*`, `NODE_OPTIONS`, …); phép thử script khởi động ngoài checkout không chạy; log không chứa giá trị biến (sau: T-4004; files: scripts/xt.py, tests/test_deploy_env.py) — Gate: `python3 -m unittest tests.test_deploy_env`
- [x] `T-4016` Bước 2: allowlist theo mẫu `trial_env` — biến hệ thống cần thiết, `PATH` kiểm soát, cấu hình và khoá cấp **theo tên** khai trong `xt.yaml`; thiếu biến đã khai thì báo lỗi nêu tên biến, không tự lấy khoá rộng từ host; mặc định bật ở bản MINOR kế, bản này chỉ `doctor` cảnh báo dự án chưa khai (sau: T-4015; files: scripts/xt.py, tests/test_deploy_env_allowlist.py) — Gate: `python3 -m unittest tests.test_deploy_env_allowlist tests.test_deploy_run tests.test_deploy_prod`

### Lát 2D — đúng bytes đã attest (mục 08; đóng AUD-CI-036)
- [x] `T-4017` Workflow phát hành lưu archive và promotion receipt theo phiên bản bất biến tải được (cách lưu theo T-4005); digest trong nghiệm thu và phân phối là một; đổi workflow nên rà sớm (sau: T-4005, T-4004; topo: review; files: .github/workflows/release-tag.yml, tests/test_release_assets.py) — Gate: `python3 -m unittest tests.test_release_contract tests.test_release_assets`
- [x] `T-4018` `release-verify`, `upgrade`, `install.py` tải đúng bytes đó rồi kiểm digest, nguồn, danh tính ký và liên kết tag, commit; sửa một byte, thay receipt, gắn sai nguồn đều bị từ chối; đường dựng lại giữ một bản làm đường lùi; hàng sổ `AUD-CI-036` chuyển `đã sửa` (sau: T-4017; files: scripts/xt_distribution.py, scripts/install.py, tests/test_distribution_bytes.py, docs/ops/AUDIT-STATUS.md) — Gate: `python3 -m unittest tests.test_distribution_bytes tests.test_green_install`

### Lát 2E — trạng thái rõ và ứng viên mới (mục 09)
- [x] `T-4019` Tách ba trạng thái trong `release-check`: kiểm kỹ thuật đạt, nội dung đã ký đúng vân tay, đã phân phối; tên trạng thái chờ ký không còn nói "human" khi `release_signoff: agent`; lược đồ tăng số, bên đọc (`xt_release_ops`, workflow dự án đích) nhận cả tên cũ một chu kỳ; consumer dựa vào trạng thái đã chấp thuận, không chỉ exit 0 (sau: T-4004; topo: review; files: scripts/xt.py, scripts/xt_release_ops.py, tests/test_release_states.py) — Gate: `python3 -m unittest tests.test_release_states tests.test_release_signoff tests.test_release_signoff_scale`
- [x] `T-4020` README lấy "bản đã gắn tag" từ bản đã phát hành và `xt.py checks` kiểm, không sửa tay mỗi lần cắt bản (sau: T-4019; files: README.md, scripts/xt.py, tests/test_readme_released_tag.py) — Gate: `python3 -m unittest tests.test_readme_released_tag && python3 scripts/xt.py checks`
- [x] `T-4021` Cắt ứng viên 3.36.0: `VERSION`, CHANGELOG có mục **Dự án đích**, GO-NO-GO mới phần máy cho đúng vân tay; sau đó `/complete` chạy cổng ký (audit delta, nợ review theo lô, `release-check`, chữ ký) ngoài Gate này (sau: T-4013, T-4014, T-4016, T-4018, T-4019, T-4020) — Gate: `python3 scripts/xt.py changelog-check && grep -qx '3.36.0' VERSION && python3 scripts/xt.py progress-check`

**Cửa đợt 2:** ứng viên mới đúng vân tay và `release-check` không FAIL ở cổng ký; lệnh triển khai không còn nạp ngầm; artefact tải và xác minh được; bằng chứng review không tái dùng sai.

## Đợt 3–5 (khung; mỗi đợt lập PLAN riêng khi tới cửa)

| Đợt | Phạm vi | Điều kiện vào | Điều kiện đi tiếp |
|---|---|---|---|
| 3 Canary và pilot | 16 (`T-3865`), 10 (pilot trên sản phẩm có sẵn), 11, 15, quyền runner của 07 | Cửa đợt 2; 3.36.0 đã phát hành; `T-4007` và `T-3858` đã tick; ba việc của người ở trên đã có | Nghiệp vụ mới chạy tại đích; nghiệm thu, quan sát, phục hồi và số đo toàn tuyến đạt; canary qua khoảng quan sát đã đặt và quay lui được |
| 4 Tối ưu theo dữ liệu | 13 (PLAN-guard-split), 14 (`T-3851`, `T-3852`, rồi `T-3854`), 18, kiểm host của 17 | Có baseline và số đo của pilot | Cải thiện đo được trên cùng môi trường, hành vi giữ đúng; CLI và UI cùng quyết định |
| 5 Mở rộng có kiểm chứng | Mở rộng 16, thêm host hoặc worker theo nhu cầu | Canary qua khoảng quan sát | Mỗi lần mở rộng có giả thuyết lợi ích, tiêu chí quan sát, đường lùi |

Ghi chú cho PLAN đợt 3: chọn sản phẩm pilot theo đích triển khai đã xác minh (hiện DHCB có bằng chứng SSH và health, Hotel Manager chưa có bằng chứng triển khai); mục 11 chỉ làm những rủi ro mà nghiệp vụ được chọn chạm tới, không đánh dấu cả pack sẵn sàng production từ một smoke; quyền filesystem, mạng và khoá của runner cấp theo tác vụ; registry lên lược đồ mới thêm giai đoạn, thời điểm quan sát và nguồn từng trường, repo đã ở production được tiếp nhận đúng giai đoạn thật; pilot xong thì quyết `T-3863` còn cần hay đã được thay.

## Bảng đo

Giữ sáu chỉ số của đề xuất §10 (chi phí mỗi lát, lead time và thời gian chờ, review có ích, CI và tích hợp, lỗi lọt và phục hồi, chi phí lõi). Nguồn: sổ lát (`T-4009`), baseline (`T-4010`), `xt_guard_profile`. Một pilot cho baseline, chưa đủ để kết luận tiết kiệm theo tỷ lệ.
