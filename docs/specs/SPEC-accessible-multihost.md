# SPEC-accessible-multihost — Đặc tả triển khai: dễ tiếp cận, skill tới nhiều host, mức tự chủ có bằng chứng

| Trường | Giá trị |
|---|---|
| Task | `T-5111`…`T-5120` của [PLAN-approach-2026-11-28](../autopilot/PLAN-approach-2026-11-28.md) |
| Trạng thái | Approved for implementation (phiên chính tự duyệt, ADR-0008; D-650, D-651, D-652) |
| Phiên bản | 1 · 2026-11-28 · đường cơ sở `main` `44ee1f8` |
| Căn cứ | [Đối chiếu bản nhận định ngoài](../../research/2026-11-28-external-roadmap-assessment.md) (dữ kiện nguồn sống, mức bằng chứng a/b/c) |
| Luật sẵn có (không chép lại) | `framework/00-method/conventions.md`, `scripts/AGENTS.md`, `tests/AGENTS.md`, [SPEC-slice-ledger](SPEC-slice-ledger.md), thang L0–L4 ở `framework/11-autonomous-loop/stop-points-and-escalation.md` |

Mỗi phần dưới đây là hợp đồng của một task: hành vi hiện có (kèm `tệp:dòng` ở đường cơ sở), giao ước mới, thay đổi theo tệp,
ca nghiệm thu có ID và điều không làm. Ca nghiệm thu là test phải viết, không phải gợi ý. Số dòng trong mã có thể trôi khi
`main` đổi; người làm tìm lại theo tên hàm.

## 0. Ràng buộc chung cho mọi task

- Mỗi task một nhánh từ `origin/main`, một PR nháp; Gate của task ghi trong PLAN, cộng `scripts/dev-task.sh gate-fast`.
- Không nới cổng: coverage dòng + nhánh 100 %, `mypy --strict --python-version 3.13`, C901 ≤ 10, trần byte và trần dòng
  (`tests/test_docs_budget.py`). `scripts/xt.py` đang 23 624/23 626 dòng: mọi logic mới đặt ở module riêng; `T-5120` được
  sửa `xt.py` với 0 dòng ròng.
- Mã chỉ dùng thư viện chuẩn, không API 3.14+ (ADR-0094). Tệp `.py` mới thêm vào lệnh `typecheck` của `xt.yaml`.
- Lớp test mới thêm trọng số vào `tests/shard-weights.json` (`scripts/dev-task.sh test-weights`).
- Đổi hành vi dự án đích nhận được (T-5111, T-5114, T-5119, T-5120) → dòng `CHANGELOG.md` mục "Chưa phát hành"; cắt bản là
  việc riêng, không nằm trong task.
- Văn bản sinh ra cho dự án đích viết tiếng Việt như các tệp sinh hiện có; giá trị lấy từ tệp cấu hình là dữ liệu, không
  được chèn nguyên văn khi chứa ký tự xuống dòng hay dấu backtick (xem ACC-111-6).

## 1. `T-5111` — người mới biết làm gì sau `install.py --new`

### 1.1 Hành vi hiện có
- `new_project_readme()` (`scripts/install.py:3103`) ghi README 5 phần: tiêu đề, ý tưởng trích dẫn, một dòng liên kết
  `PROJECT.md` · `PROGRESS.md`, đường kẻ, chân trang nguồn. README đã có thì không đụng (copy-if-absent).
- `new_bootstrap()` (`scripts/install.py:3116`) gọi `install(...)`; hàm này in ở cuối (`scripts/install.py:2981`):
  "Xong. Bước tiếp: `xt.py doctor` …, điền xt.yaml, rồi `xt.py list profiles` → compose BLUEPRINT.md." Với `--new` câu này
  **sai**: `new_bootstrap` còn chạy `stage init`, ghi PROJECT/README, `compose` và commit đầu *sau* câu đó, nên người mới
  được bảo đi compose một blueprint đã có. Sau `doctor --offline` cuối, lệnh không in thêm gì.
- Gói `web-api-ts` khai sẵn các khoá cần cho bước kế trong `pack.json` → `xt_yaml`: `setup`, `dev`, `preview`.

### 1.2 Giao ước
- Hàm mới `new_next_steps(name: str, pack: dict[str, Any]) -> list[str]` trả các bước theo thứ tự, mỗi bước một chuỗi
  Markdown một dòng. Thứ tự và điều kiện:

| # | Bước | Điều kiện có mặt |
|---|---|---|
| 1 | `cd <name>` | luôn |
| 2 | Cài phụ thuộc: `` `<xt_yaml.setup>` `` | khoá có, là chuỗi an toàn |
| 3 | Chạy bản dev: `` `<xt_yaml.dev>` ``, mở `<xt_yaml.preview>` | `dev` an toàn; phần "mở …" chỉ khi `preview` an toàn |
| 4 | Mở agent trong thư mục dự án và gọi `/factory` (Claude Code); host khác đọc `AGENTS.md` | luôn |
| 5 | Xem tiến độ trên trình duyệt: `` `python3 .xtemplates/scripts/xt.py app` `` | luôn |
| 6 | Luật và quyết định: `AGENTS.md`, `PROJECT.md`, `BLUEPRINT.md` | luôn |

- "Chuỗi an toàn" = `str`, 1…200 ký tự, không chứa `\n`, `\r`, `` ` `` hay ký tự điều khiển. Không an toàn → bỏ bước (hoặc
  bỏ phần "mở …"), không đoán, không thoát ký tự.
- README do `new_project_readme` sinh thêm mục `## Bắt đầu` ngay sau dòng liên kết: danh sách đánh số từ `new_next_steps`.
  `new_project_readme` nhận thêm tham số `pack`. README đã có → không đụng như cũ.
- `install()` nhận tham số khoá `done_hint: bool = True`; `new_bootstrap` truyền `False` → không in câu "Xong. Bước tiếp …"
  ở giữa. `new_bootstrap` in khối cuối, sau `doctor --offline` thành công, đúng một lần:
  `[install] Xong. Dự án <name> đã sẵn sàng. Bước kế:` rồi từng bước, mỗi dòng `[install]   <số>. <bước>`.
- `doctor --offline` đỏ → không in khối bước kế (mã thoát giữ hành vi hiện có).

### 1.3 Thay đổi theo tệp
`scripts/install.py` (hàm mới + hai tham số), `tests/test_install_new.py`, `CHANGELOG.md`. Không đổi `pack.json`.

### 1.4 Ca nghiệm thu
- **ACC-111-1** Given thư mục rỗng và gói `web-api-ts`, When `--new --pack web-api-ts --idea …`, Then README có `## Bắt đầu`
  với 6 bước, bước 2 chứa `pnpm install --frozen-lockfile`, bước 3 chứa `pnpm dev` và `http://127.0.0.1:4317`.
- **ACC-111-2** Cùng lệnh, Then stdout kết thúc bằng khối "Bước kế" khớp từng bước của README (cùng nguồn `new_next_steps`).
- **ACC-111-3** Cùng lệnh, Then stdout **không** chứa `list profiles` (câu "Xong" của `install()` đã tắt ở `--new`).
- **ACC-111-4** Given cài thường (không `--new`), Then câu "Xong. Bước tiếp … list profiles" vẫn in như cũ.
- **ACC-111-5** Given gói giả không có `setup`/`dev`/`preview`, Then README có 4 bước (1, 4, 5, 6), không dòng rỗng.
- **ACC-111-6** Given `dev` = `` "a`b" `` hoặc chứa `\n`, Then bước 3 vắng mặt; README không có backtick lẻ.
- **ACC-111-7** Given README đã có trong thư mục đích trước bootstrap (ca hiện có), Then README giữ nguyên byte.

### 1.5 Không làm
Không dịch README sinh ra; không thêm lệnh `xt.py init --demo` (đường `--new` đã là lệnh tạo dự án, D-650); không chạy
`setup`/`dev` hộ người dùng (bộ cài không cần mạng, ADR-0068).

## 2. `T-5112` — trang chọn đường theo cỡ việc

### 2.1 Hành vi hiện có
`framework/00-method/lifecycle.md` có "Quy mô S/M/L — làm nhẹ đi chứ không bỏ" (quy mô **dự án**) và "Ánh xạ sang chế độ tự
động"; chưa có chỗ nói **một việc** cỡ nào thì đi đường nào. BMAD có bốn đường Trivial/One-session/Epic/Project
(research §4.5); người mới của khung không có tương đương nên dễ tưởng việc nào cũng phải `/autopilot`.

### 2.2 Giao ước
- Thêm mục `## Chọn đường theo cỡ việc` vào `lifecycle.md`, sau mục quy mô S/M/L. Một bảng bốn hàng, năm cột:

| Đường | Dùng khi (cả hai điều kiện) | Cách chạy | Được bỏ | Không bao giờ bỏ |
|---|---|---|---|---|
| Sửa thẳng | Một lát nhỏ không đổi giao ước công khai; không chạm nhóm rủi ro của làn nhanh | Sửa → cổng commit → PR nháp | PLAN, SPEC, ADR | Gate, PR nháp, review khi `pr next` đòi, CHANGELOG khi đổi ID/công cụ, không bí mật |
| Một phiên có PLAN ngắn | Một mục tiêu, vài task độc lập, xong trong một phiên | PLAN 1–5 task, `loop` | SPEC dài, audit delta | Như trên + `loop record` cho mỗi task |
| Đợt `/autopilot` | Nhiều lát có phụ thuộc hoặc nhiều PR | `/autopilot` | — | Như trên + audit delta cuối đợt |
| Vòng đời `/factory` | Từ ý tưởng tới phát hành, xuyên giai đoạn sản phẩm | `/factory` | — | Toàn bộ cổng G0–G8 theo quy mô dự án |

- Cột "Không bao giờ bỏ" chỉ **liên kết** tới luật nhà (ID hoặc mục), không chép nguyên văn. "Nhóm rủi ro của làn nhanh"
  liên kết tới vị từ làn nhanh ở `stop-points-and-escalation.md`.
- Không thêm ID checklist mới. Nếu người rà thấy cần một mục bắt buộc, thêm `SHOULD` theo `conventions.md` trong PR riêng.
- `framework/templates/AGENTS.md` thêm **một dòng** trỏ tới mục mới (trần 28 672 byte vẫn giữ); `README.md` thêm một dòng ở
  phần bắt đầu, cả bản tiếng Anh và tiếng Việt.

### 2.3 Ca nghiệm thu
- **ACC-112-1** `xt.py validate` và `check-links.py` exit 0; `tests.test_docs_budget` xanh (trần AGENTS mẫu không đổi).
- **ACC-112-2** `grep -c "Chọn đường theo cỡ việc"` ở `framework/templates/AGENTS.md` và `README.md` đều ≥ 1, và liên kết
  trỏ đúng neo của `lifecycle.md`.
- **ACC-112-3** Mục mới không chứa câu luật trùng nguyên văn với tệp nhà (người rà kiểm, ghi trong PR).

## 3. `T-5113` — khung tự kiểm skill theo chuẩn Agent Skills

### 3.1 Hành vi hiện có (đo 2026-11-28)
17 skill ở `.claude/skills`, gương byte-trùng ở `.agents/skills`. Khoá frontmatter: `name` (17), `description` (17),
`argument-hint` (15). Mô tả dài nhất 553 ký tự (`audit`), nhiều dòng nhất 57 (`audit`). Không test nào ghim giới hạn của
chuẩn. `argument-hint` là khoá Claude Code; claude.ai upload và Skills API chỉ nhận sáu trường chuẩn (research §4.1, mức b).

### 3.2 Giao ước
- Tệp mới `tests/test_skills_spec.py`, stdlib, đọc frontmatter giữa hai dòng `---` đầu tệp bằng parser dòng `khoá: giá trị`
  (không PyYAML). Khoá có giá trị nhiều dòng (`|`, `>`) → fail với lý do "parser của test chỉ đọc giá trị một dòng".
- Hằng khai trong test, kèm nguồn và ngày đọc:
  - `SPEC_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}` (agentskills.io/specification).
  - `CLAUDE_CODE_KEYS = {"argument-hint", …}` chỉ gồm khoá đang dùng hoặc có lý do ghi trong chú thích
    (code.claude.com/docs/en/skills).
- Luật kiểm cho mọi `SKILL.md` ở `.claude/skills/*/` và `.agents/skills/*/`:
  1. `name` khớp `^[a-z0-9]+(-[a-z0-9]+)*$`, dài 1–64, bằng tên thư mục.
  2. `description` dài 1–1024 ký tự sau khi bỏ khoảng trắng hai đầu.
  3. `compatibility` (nếu có) ≤ 500 ký tự.
  4. Tệp < 500 dòng.
  5. Mọi khoá thuộc `SPEC_KEYS ∪ CLAUDE_CODE_KEYS`; khoá lạ → fail, thông báo nêu tên skill và khoá.
  6. Mỗi skill ở `.claude/skills` có gương byte-trùng ở `.agents/skills` và ngược lại (nếu `test_codex_harness` đã ghim
     điều này, test mới gọi lại kiểm đó thay vì viết lần hai).
- `framework/18-cross-cutting/docs-for-ai-agents.md`: thêm một đoạn ngắn: chuẩn Agent Skills (sáu trường), `skills-ref` là
  bản minh hoạ "không dùng cho production" nên khung tự kiểm bằng test stdlib; khoá ngoài chuẩn làm skill không tải lên được
  claude.ai/Skills API.

### 3.3 Ca nghiệm thu
- **ACC-113-1** Trên cây hiện tại test xanh (17 skill đều đạt).
- **ACC-113-2** Mỗi luật 1–5 có một ca đỏ dựng trong thư mục tạm (tên hoa, tên khác thư mục, mô tả 1025 ký tự, 500 dòng,
  khoá `foo:`), test gọi cùng hàm kiểm và khẳng định thông báo lỗi nêu đúng skill và luật.
- **ACC-113-3** Ca đối chứng: skill tạm có `license` và `compatibility` 500 ký tự → đạt.

### 3.4 Không làm
Không bỏ `argument-hint` (Claude Code dùng nó để gợi ý đối số; chỉ đường tải lên claude.ai bị ảnh hưởng, ngoài phạm vi
khung). Không chạy `skills-ref` trong CI.

## 4. `T-5114` — `--harness gemini` sinh gương `.agents/skills`

### 4.1 Hành vi hiện có
- Gương skill sinh bởi bộ sinh của ADR-0082: `codex_jobs()` tạo việc cho skill
  (`.claude/skills/<n>/SKILL.md` → `.agents/skills/<n>/SKILL.md`, `render_skill` sao byte) và agent (→ `.codex/agents/*.toml`) —
  hàm ở `scripts/install.py:1719`;
  `install_codex_harness()` (`scripts/install.py:1808`) chỉ chạy khi `"codex" in hosts`, hash ghi vào map `codex_files` của
  manifest, luật `copied/kept/updated/kept-own/updated-new/skipped-source`, không xuyên symlink (`read_regular`).
- Adapter Gemini (`scripts/install.py:1442`) chỉ ghi `.gemini/settings.json`. Gemini CLI đọc skill ở `.gemini/skills` hoặc bí
  danh `.agents/skills`, không đọc `.claude/skills` (research §4.2, mức b). Kết quả: trong sáu host có adapter, Gemini là host
  duy nhất không nhận skill nào của khung.

### 4.2 Giao ước
- Đổi điều kiện: phần **skill** của bộ sinh chạy khi `hosts ∩ {"codex", "gemini"}` khác rỗng; phần **agent** và
  `.codex/hooks.json` vẫn chỉ khi có `codex`. Tách `codex_jobs` thành hai hàm (`skill_mirror_jobs`, `codex_agent_jobs`) hoặc
  thêm tham số `agents: bool`; giữ hàm cũ làm vỏ nếu test hiện có gọi trực tiếp.
- Map manifest giữ tên `codex_files` cho mọi tệp `.agents/skills/*` dù host nào sinh (một chủ cho một đường dẫn; đổi tên map
  làm hỏng nâng cấp của dự án đã cài). ADR mới ghi rõ tên map là lịch sử.
- `--plan --harness gemini` liệt kê các tệp `.agents/skills/*` với cùng hành động mà lần cài thật sẽ làm.
- Dòng log: `✓ skill mirror (.agents/skills) cho <host,…>: <thống kê>`; khi có `codex` giữ nguyên dòng log cũ của Codex.
- Trước khi viết mã, người làm đọc nguyên văn geminicli.com/docs/cli/skills (ghi ngày vào ADR): nếu Gemini cần bật skill
  bằng cấu hình, **không** sửa `settings.json` của người dùng ngoài khoá khung đã quản; ghi hướng dẫn vào README adapter.
- ADR mới (số kế tiếp trên `origin/main` lúc làm; 2026-11-28 đã có tới 0118): phạm vi (`gemini` dùng gương có sẵn), lý do không sinh cho Cursor/Copilot/OpenCode
  (đọc thẳng `.claude/skills`), đường lùi (bỏ `gemini` khỏi điều kiện).

### 4.3 Ca nghiệm thu
- **ACC-114-1** `--harness gemini` trên dự án sạch → có `.agents/skills/<n>/SKILL.md` cho mọi skill không bị che, byte-trùng
  nguồn; **không** có `.codex/agents/` hay `.codex/hooks.json`.
- **ACC-114-2** `--harness codex,gemini` → mỗi tệp gương sinh đúng một lần; kết quả byte-trùng ca chỉ `codex`.
- **ACC-114-3** Cài `gemini` rồi cài lại thêm `codex` → gương `kept`, agent `copied`.
- **ACC-114-4** Dự án tự sửa một gương rồi nâng bản khung có skill đổi → `.xtemplates-new`, giữ tệp của dự án (luật cũ).
- **ACC-114-5** Gương là symlink hoặc nằm dưới thư mục symlink → không đi theo, giữ nguyên (luật cũ áp cho host mới).
- **ACC-114-6** Bỏ `gemini` khỏi `--harness` ở lần cài sau → hành vi giống bỏ `codex` hiện nay; nếu chưa có test ghim hành
  vi đó, viết test ghim hành vi hiện tại **trước** khi đổi mã.
- **ACC-114-7** `--plan --harness gemini` liệt kê đúng tập tệp ACC-114-1, không ghi gì lên đĩa.

## 5. `T-5115`/`T-5116` — mức tự chủ đọc từ bằng chứng

Phần này là SPEC mà `T-5115` yêu cầu; `T-5116` triển khai nó.

### 5.1 Hành vi hiện có
- Thang L0–L4 (`stop-points-and-escalation.md` §"Mức tự chủ L0–L4") có cột "Điều kiện lên mức" và "Đường lùi tự động", nhưng
  không lệnh nào đọc các điều kiện đó. `merge_autonomy` trong `xt.yaml` do chủ dự án chọn thẳng; `merge_autonomy_level()`
  (`scripts/xt.py:7360`) đọc nó ở ref đã commit.
- `xt_flow.report()` đã có các số đo nguồn: `first_pass_rate`, `tasks_observed`, `resolved_interventions` (từ
  `.autopilot/runs.jsonl` và state), `escaped_after_merge`, `ever_conflicted_pr_rate` (sổ lát), `deploy_by_env` (sổ triển khai).
  Các số này tính trên toàn bộ dữ liệu, không theo cửa sổ thời gian.
- Sổ lát chưa ghi **làn** của PR (sự kiện `pr` có `verdict`, `head`, `mergeable`), nên điều kiện L2 "200 merge làn nhanh"
  chưa có nguồn.

### 5.2 Giao ước: khối `autonomy` trong `xt_flow.py --json`
Thêm khoá cấp cao `autonomy` (cạnh `metrics`, `coverage`). Chỉ tư vấn: không lệnh nào ghi `merge_autonomy`, không cổng nào
đọc khối này để quyết merge.

```json
"autonomy": {
  "schema": 1,
  "advisory": true,
  "declared": "L3",
  "eligible": "L0",
  "as_of": "2026-11-28T10:00:00+00:00",
  "checks": [
    {"level": "L1", "id": "baseline_days", "value": 12.5, "op": ">=", "threshold": 56, "ok": false, "reason": null},
    {"level": "L1", "id": "first_pass_rate_28d", "value": 0.81, "op": ">=", "threshold": 0.70, "ok": true, "reason": null},
    {"level": "L1", "id": "escaped_vs_baseline", "value": null, "op": "<=", "threshold": null, "ok": null, "reason": "window_short"},
    {"level": "L2", "id": "fast_lane_clean_merges", "value": null, "op": ">=", "threshold": 200, "ok": null, "reason": "no_source"}
  ],
  "rollback": {"triggered": null, "checks": []},
  "missing": ["fast_lane_clean_merges: sổ lát chưa ghi làn của PR"]
}
```

- `declared`: `"L<n>"` từ `merge_autonomy_level(base, None)`; đọc lỗi → `null` và lý do vào `missing`.
- `eligible`: mức cao nhất mà **mọi** check của nó và của các mức dưới có `ok: true`. Check có `ok: null` chặn mức đó (thiếu
  dữ liệu không được tính là đạt). Không mức nào đạt → `"L0"`.
- `reason` khi `value` là `null`: `no_source` (chưa có lệnh nào ghi dữ liệu cần), `no_events` (có nguồn, chưa có sự kiện),
  `window_short` (dữ liệu chưa phủ đủ cửa sổ), `human_only` (điều kiện là phê duyệt của người, máy không đo).

### 5.3 Ánh xạ điều kiện → check

| Mức | Điều kiện ở thang | `id` | Cách tính | Nguồn |
|---|---|---|---|---|
| L1 | Có baseline 8 tuần | `baseline_days` | Ngày giữa `started` sớm nhất và `finished` muộn nhất trong `runs.jsonl` (mọi vòng) | runs.jsonl |
| L1 | `first_pass_gate_rate ≥ 70 %` trong 4 tuần | `first_pass_rate_28d` | Như `loop_stats` nhưng chỉ task có lượt Gate đầu trong 28 ngày trước `as_of`; < 28 ngày dữ liệu → `window_short` | runs.jsonl |
| L1 | Lỗi lọt ≤ baseline | `escaped_vs_baseline` | `escaped_after_merge` (tổng mọi severity) của PR merge trong 28 ngày gần nhất ≤ trung bình mỗi 28 ngày của 56 ngày trước đó; cửa sổ 14 ngày của PR chưa đóng → `window_short` | sổ lát |
| L2 | 200 merge làn nhanh liên tiếp không lỗi nghiêm trọng (đội 1 người: 60) | `fast_lane_clean_merges` | `null` + `no_source` cho tới khi sổ lát ghi làn (task sau, mục 5.6); ngưỡng 60 khi chạy với `--solo` | — |
| L3 | 8 tuần ở L2 | `weeks_at_l2` | `null` + `no_source` (không có lịch sử mức đã khai) | — |
| L3 | `change_failure_rate ≤ baseline` | `change_failure_vs_baseline` | `rollback_rate` của môi trường production trong 28 ngày ≤ của 56 ngày trước đó; không có môi trường `production` → `no_events` | sổ triển khai |
| L3 | Can thiệp ≤ 15 % | `intervention_rate` | `resolved_interventions / tasks_observed` trong 28 ngày; `tasks_observed` = 0 → `no_events` | state + runs.jsonl |
| L4 | Hệ rủi ro thấp, có phê duyệt quản trị | `governance_approval` | Luôn `null` + `human_only` | — |

Đường lùi (`rollback.checks`): `escaped_two_weeks` = hai tuần lịch liên tiếp gần nhất đều có lỗi lọt cao hơn trung bình tuần
của baseline; `privilege_violation` luôn `null` + `no_source`. `triggered` = `true` nếu có check `true`; `null` nếu mọi check
`null`; còn lại `false`. Khi `triggered` là `true`, `eligible` hạ một mức so với kết quả tính ở trên (sàn L0).

### 5.4 Đầu ra chữ và CLI
- `xt_flow.py` (không `--json`) in thêm một dòng: `Tự chủ (tư vấn): khai L3 · đủ bằng chứng cho L0 · thiếu: <id>, <id>`.
- `--github-summary` thêm một dòng cùng nội dung.
- Cờ mới `--solo`: ngưỡng `fast_lane_clean_merges` = 60. Không cờ nào khác.
- `stop-points-and-escalation.md`: dưới bảng L0–L4 thêm một câu trỏ tới `xt_flow.py --json` khoá `autonomy`, nói rõ là tư vấn.

### 5.5 Ca nghiệm thu (Given/When/Then)
Dữ liệu dựng bằng lệnh thật của khung trong repo tạm (`loop init`, `loop record`, `deploy` receipt, `incident check`), dịch
đồng hồ bằng cơ chế thời gian giả mà test hiện có của `xt_flow` đang dùng; không chèn sự kiện tay vào bộ tính.
- **ACC-116-1** Given repo không có `.autopilot/`, When `--json`, Then `autonomy.eligible` = `"L0"`, mọi check L1 có
  `ok: null` và `reason` ∈ {`no_source`, `no_events`}; mã thoát 0.
- **ACC-116-2** Given 10 ngày dữ liệu Gate, tỉ lệ xanh lần đầu 90 %, Then `baseline_days` < 56, `ok: false`;
  `first_pass_rate_28d` có `reason: "window_short"`; `eligible` = `"L0"`.
- **ACC-116-3** Given 60 ngày dữ liệu, xanh lần đầu 75 % trong 28 ngày cuối, không PR nào trong cửa sổ lỗi lọt, mọi PR đã qua
  14 ngày, Then ba check L1 `ok: true`, `eligible` = `"L1"` (L2 chặn bởi `no_source`).
- **ACC-116-4** Như ACC-116-3 nhưng xanh lần đầu 69 %, Then `first_pass_rate_28d.ok` = `false`, `eligible` = `"L0"`.
- **ACC-116-5** Given `xt.yaml` có `merge_autonomy: L3` và chỉ đủ L1, Then `declared` = `"L3"`, `eligible` = `"L1"`; không tệp
  nào trong repo đổi (so `git status --porcelain` trước và sau).
- **ACC-116-6** Given hai tuần liên tiếp có lỗi lọt cao hơn baseline, Then `rollback.triggered` = `true` và `eligible` hạ một mức.
- **ACC-116-7** Given `--solo`, Then threshold của `fast_lane_clean_merges` là 60; không `--solo` là 200.
- **ACC-116-8** Given `runs.jsonl` có dòng hỏng, Then check vẫn tính trên dòng hợp lệ (luật đọc hiện có), không ném lỗi.
- **ACC-116-9** Đầu ra chữ và `--github-summary` chứa đúng một dòng "Tự chủ (tư vấn)".

### 5.6 Không làm (và task nên mở sau)
Không tự đổi `merge_autonomy`; không gắn khối này vào `pr next`, `merge-check` hay `release-check`. Ghi `lane` vào sự kiện
`pr` của sổ lát chạm `xt.py` (đang sát trần dòng) và đổi SPEC-slice-ledger: mở task riêng khi có nhu cầu đo L2, không gộp vào
đây.

## 6. `T-5117` — mẫu issue song ngữ, đoạn tiếng Anh ở CONTRIBUTING

### 6.1 Hành vi hiện có
`.github/ISSUE_TEMPLATE/` chỉ có `feedback-du-an-dich.yml` (phản hồi của dự án đích, tiếng Việt). Có `SECURITY.md`. README đã
song ngữ; `CONTRIBUTING.md` chỉ tiếng Việt.

### 6.2 Giao ước
- `bug-report.yml` và `feature-request.yml` (GitHub issue forms). Nhãn mỗi trường dạng `Tiếng Việt / English`. Trường bắt buộc:
  - Báo lỗi: phiên bản khung (`VERSION` hoặc tag), host agent và phiên bản, lệnh đã chạy, kết quả mong đợi, kết quả thật, log.
  - Đề xuất: vấn đề đang gặp, đề xuất, phương án đã cân nhắc, mục/ID liên quan (không bắt buộc).
- Ô mô tả đầu mỗi mẫu nhắc: không dán bí mật hay dữ liệu người dùng thật; lỗ hổng bảo mật báo theo `SECURITY.md`.
- `config.yml`: giữ `blank_issues_enabled: true` (không chặn người ngoài), thêm `contact_links` tới `SECURITY.md`.
- `CONTRIBUTING.md`: đoạn "In English" 5–8 dòng ở đầu: repo viết tiếng Việt, issue/PR bằng tiếng Anh được nhận, liên kết luật
  hiện có (conventional commit, mỗi lát một PR, không nới cổng). Không chép luật.
- Mẫu `feedback-du-an-dich.yml` giữ nguyên.

### 6.3 Ca nghiệm thu
- **ACC-117-1** `xt.py checks` và `check-links.py` exit 0.
- **ACC-117-2** Hai tệp YAML mới đọc được bằng parser của test hiện có cho workflow/YAML (nếu có) hoặc kiểm dạng bằng test mới
  tối thiểu: có `name`, `description`, `body`, mỗi phần tử `body` có `type`.
- **ACC-117-3** Mẫu không có trường thu email, số điện thoại hay token.

## 7. `T-5118` — README adapter theo ma trận host

### 7.1 Giao ước
`framework/templates/harness/README.md` có một bảng cập nhật từ research §4.2, mỗi hàng: host, phiên bản đã đọc và ngày đọc,
sự kiện chặn trước tool, host đọc gì của `.claude/`, nơi đọc skill, trạng thái adapter (`thử nghiệm` cho tới khi có payload
thật — ADR-0064). Ghi rõ:
- Cursor, Copilot, OpenCode đọc thẳng `.claude/skills`; Codex đọc gương `.agents/skills`; Gemini đọc gương sau `T-5114`.
- Mẫu `opencode-xt.ts` theo API plugin dòng 1.x; dòng 2.x xem `T-5119`.
- Gemini CLI: README của dự án nói dành cho Gemini Code Assist doanh nghiệp; gói cá nhân sang Antigravity CLI (chưa có adapter).
- Copilot cloud agent chỉ đọc `.github/hooks/*.json` và coi `ask` là `deny`.
- Câu hỏi còn mở: hook có chạy ở chế độ không người (`-p`, `exec`, `run`) không — tài liệu chưa nói.

### 7.2 Ca nghiệm thu
- **ACC-118-1** `xt.py validate`, `check-links.py` exit 0.
- **ACC-118-2** Mỗi hàng có ngày đọc dạng `YYYY-MM-DD`; không hàng nào ghi "hỗ trợ" khi chưa có payload thật.

## 8. `T-5119` — adapter OpenCode dòng 2.x

### 8.1 Hành vi hiện có
`framework/templates/harness/opencode-xt.ts` dùng hook V1 `"tool.execute.before"`. Theo research §4.2 (mức b, chưa đọc
nguyên văn tài liệu plugin 2.x): dòng 2.x dùng `ctx.tool.hook("execute.before", …)` trong `Plugin.define`, và plugin V1 không
chạy ở V2. Dự án dùng OpenCode 2.x hiện **không** có guard qua adapter này.

### 8.2 Giao ước
1. **Nghiên cứu trước** (`/research`): đọc nguyên văn tài liệu plugin 2.x và mã nguồn tag mới nhất; ghi vào
   `research/<ngày>-opencode-v2-plugin.md`: chữ ký hook, đường dẫn nạp plugin, cách chặn (ném lỗi hay trả giá trị), cách đọc
   đối số tool, có chạy ở `opencode run` không. Không xác minh được chữ ký hook → `loop defer --task T-5119` kèm lý do, không
   đoán API.
2. Mẫu mới `framework/templates/harness/opencode-v2-xt.ts`, cùng hợp đồng với mẫu 1.x: gửi payload cho `xt_adapter.py`, chặn
   khi adapter trả `deny`, **fail-closed** khi adapter lỗi với tool ghi/chạy lệnh (theo cách mẫu 1.x đang làm).
3. Host id mới `opencode2` trong bảng adapter của `install.py`; chọn bằng `--harness opencode2`. Bộ cài **không** dò phiên bản
   OpenCode. Cài cả `opencode` và `opencode2` cùng lúc → lỗi rõ ràng, mã thoát 2.
4. `xt_adapter.py`: `parse`/`to_core` nhận `opencode2` nếu payload khác 1.x; giống thì ánh xạ về cùng nhánh.

### 8.3 Ca nghiệm thu
- **ACC-119-1** Payload mẫu 2.x (lấy từ tài liệu đã đọc, lưu ở `tests/fixtures/`) cho lệnh `git push --force` → adapter trả
  quyết định chặn với lý do của guard.
- **ACC-119-2** Payload lệnh vô hại → cho qua.
- **ACC-119-3** `--harness opencode,opencode2` → mã thoát 2, không ghi tệp nào.
- **ACC-119-4** `--harness opencode` vẫn cài mẫu 1.x như cũ (byte-trùng).
- **ACC-119-5** Nhãn trong README adapter là `thử nghiệm`.

## 9. `T-5120` — PROGRESS rộng hơn mà không mất phần cuối

### 9.1 Hành vi hiện có (đo 2026-11-28)
- Hook `.claude/hooks/session-start.sh` dựng phần còn lại trước (khối Autopilot ≤ 2 400 ký tự, Git: nhánh/repo ≤ 200 byte
  mỗi thứ, log ≤ 1 200 byte, dòng luật), rồi cho PROGRESS phần ngân sách `9800 − len(rest) − len(head) − 2` ký tự. PROGRESS
  bị cắt **từ cuối**: cắt byte ở `PROGRESS_LIMIT=8192` trước, rồi cắt ký tự theo ngân sách. Awk chỉ giữ dòng 1 và bốn mục.
- `progress-check` (`scripts/xt.py:4048`) kiểm `len(raw) > PROGRESS_MAX_BYTES` (8 192). `tests/test_hooks.py:858` ghim hai
  số bằng nhau.
- PROGRESS hiện 8 187 byte ≈ 7 294 ký tự (1,12 byte/ký tự): dòng 1 34 · Đang làm 1 746 · Tiếp theo 2 125 · Quyết định
  2 303 · Bàn giao phiên 980 (đo bằng `len()` theo mục). Khi Autopilot tắt, phần còn lại ~752 ký tự: vừa. Khi khối Autopilot
  đầy, ngân sách PROGRESS ~6 600 ký tự < 7 294: mục cuối (**Bàn giao phiên** — mục quan trọng nhất để "tiếp tục") bị cắt
  trước, mục **Quyết định** (đã có nhà ở ADR và DECISIONS.md) lại còn nguyên. Số 6 600 tính từ mã, chưa tái hiện.
- Ca xấu nhất (Autopilot 2 400, nhánh và repo đúng 200 byte nên dòng gợi ý tên phiên lặp lại cả hai, log 1 200 byte): phần
  còn lại ≈ 4 700 ký tự, ngân sách PROGRESS ≈ 5 030 ký tự (ước từ mã, chưa đo).
- Trần kênh: `additionalContext` của hook tối đa 10 000 ký tự; vượt thì chỉ còn đường dẫn tệp và 2 000 ký tự đầu, không cấu
  hình nào nâng (code.claude.com/docs/en/hooks, đọc 2026-11-28).

### 9.2 Giao ước
- **Thứ tự ưu tiên khi thiếu chỗ** (hook): dòng 1, `## Đang làm`, `## Tiếp theo`, `## Bàn giao phiên` là phần ưu tiên. Nếu
  toàn bộ PROGRESS vượt ngân sách, thay thân mục `## Quyết định` bằng đúng một dòng
  `[mục Quyết định không nạp vì thiếu chỗ — đọc PROGRESS.md]`. Nếu vẫn vượt, cắt từ cuối **mục Tiếp theo** (giữ nguyên Đang
  làm và Bàn giao), kèm dấu cắt hiện có. Đầu ra giữ thứ tự mục như trong tệp.
- **Đo bằng ký tự**: hook bỏ bước cắt byte; `progress-check` đổi kiểm byte thành kiểm ký tự với hai trần:
  - `PROGRESS_PRIORITY_MAX_CHARS` cho dòng 1 + ba mục ưu tiên = ngân sách PROGRESS ở ca xấu nhất (mục 9.1) trừ dòng thay
    thế mục Quyết định, làm tròn xuống bội số 100. Dự kiến ≈ 4 900 ký tự; PROGRESS của repo khung hôm nay là 4 885, tức
    sát trần. Đây là bảo đảm cứng: phần ưu tiên ≤ trần thì không bao giờ bị cắt.
  - `PROGRESS_MAX_CHARS` cho cả tệp = ngân sách PROGRESS khi Autopilot tắt với phần Git tham chiếu (nhánh và repo 40 ký tự,
    log 3 dòng 300 ký tự, dòng luật hiện tại), làm tròn xuống bội số 100, và **không nhỏ hơn 8 192** để PROGRESS cũ ≤ 8 192
    byte không đỏ khi nâng bản. Dự kiến ≈ 8 900 ký tự (hôm nay 7 294). Phần vượt ngân sách thực tế của một phiên chỉ làm
    mục Quyết định bị thay bằng dòng trỏ tệp; ba mục ưu tiên không bị ảnh hưởng.
  - Người làm tính hai số từ mã hook, ghi phép tính vào ADR và để test ACC-120-1/2 đo lại.
  - Vượt `PROGRESS_MAX_CHARS` → `progress-check` **đỏ** (như trần byte hôm nay). Vượt `PROGRESS_PRIORITY_MAX_CHARS` →
    **cảnh báo**, exit 0, nêu số ký tự từng mục và gợi ý chuyển việc ở Tiếp theo sang PLAN. Lý do: luật mới không được làm dự
    án đích đỏ ngay khi nâng bản (giữ đường lùi); hook vẫn xử lý phần vượt bằng cách cắt đuôi Tiếp theo. Nâng thành lỗi là
    quyết định ADR sau một bản phát hành.
  - Hai trần là hằng ở **một** nơi mà cả hook và `xt.py` đọc được: hook đọc từ dòng `PROGRESS_LIMIT_CHARS=` và
    `PROGRESS_PRIORITY_CHARS=` của chính nó; test ghim bằng nhau với hằng của `xt.py` như cách đang ghim `PROGRESS_LIMIT`.
- `scripts/xt.py`: 0 dòng ròng (thay hằng và phép so sánh tại chỗ; logic tách mục dùng `progress_sections` sẵn có). Nếu không
  đủ, đặt hàm đếm ký tự theo mục ở module mới (ví dụ `scripts/xt_progress.py`) và gọi từ `xt.py`.
- ADR mới thay một phần ADR-0091: trần đo bằng ký tự, thứ tự ưu tiên mục, phép tính hai trần, đường lùi (đặt lại cắt từ cuối).
- `framework/11-autonomous-loop/harness-files.md` và mẫu `framework/templates/PROGRESS.md` cập nhật câu nói trần (chỉ câu đó).
- Dự án đích: dòng CHANGELOG nói rõ `progress-check` đổi đơn vị và có cảnh báo mới; PROGRESS cũ ≤ 8 192 byte có ≤ 8 192 ký
  tự nên không đỏ khi nâng bản (có thể nhận cảnh báo phần ưu tiên).

### 9.3 Ca nghiệm thu
- **ACC-120-1** Given khối Autopilot 2 400 ký tự, nhánh và repo 200 byte, log 1 200 byte, PROGRESS có ba mục ưu tiên đúng
  `PROGRESS_PRIORITY_MAX_CHARS` và mục Quyết định 3 000 ký tự, When chạy hook, Then `additionalContext` ≤ 10 000 ký tự, ba mục
  ưu tiên còn nguyên từng ký tự, mục Quyết định là dòng thay thế.
- **ACC-120-2** Given Autopilot tắt, PROGRESS đúng `PROGRESS_MAX_CHARS`, Then không cắt gì, không dòng thay thế.
- **ACC-120-3** Given ba mục ưu tiên vượt trần ưu tiên 500 ký tự (`progress-check` chỉ cảnh báo), Then Đang làm và Bàn giao
  còn nguyên, Tiếp theo bị cắt đuôi kèm dấu cắt, tổng ≤ 10 000.
- **ACC-120-4** `progress-check` đỏ khi tệp > `PROGRESS_MAX_CHARS` ký tự; phần ưu tiên > `PROGRESS_PRIORITY_MAX_CHARS` →
  exit 0 kèm cảnh báo nêu số ký tự từng mục ưu tiên.
- **ACC-120-5** Tệp ASCII 8 192 byte (8 192 ký tự) → không đỏ; tệp `PROGRESS_MAX_CHARS + 1` ký tự → đỏ; tệp tiếng Việt
  9 500 byte nhưng ≤ `PROGRESS_MAX_CHARS` ký tự → không đỏ (trước đây đỏ vì đo byte).
- **ACC-120-6** Test ghim hằng của hook và `xt.py` bằng nhau; `tests.test_docs_budget` xanh (trần dòng `xt.py` không đổi).
- **ACC-120-7** `xt.py autonomy-bench` xanh (hook vẫn fail-open: thiếu `python3` thì không in gì như hiện nay).

### 9.4 Không làm
Không nâng 100 kB (trần kênh 10 000 ký tự; ADR-0089 đã thử 40 960 byte và gây AUD-HAR-461). Không nạp PROGRESS qua kênh khác
(ví dụ đọc tệp bằng tool ở đầu phiên): đó là đổi giao thức phiên, cần ADR riêng.

## 10. Thứ tự, phụ thuộc và rủi ro

- Thứ tự theo PLAN (`xt.py plan waves`: 9 task mở, 7 đợt; đợt 1 là `T-5111`, `T-5113`, `T-5117`). `T-5111` → `T-5114` → `T-5118` → `T-5119` nối tiếp vì cùng sửa
  `install.py` hoặc README adapter. `T-5115` (tệp này) → `T-5116`. `T-5112`, `T-5113`, `T-5117`, `T-5120` độc lập.
- Rủi ro chính và cách giữ:
  - `T-5114` đổi điều kiện bộ sinh dùng chung với Codex → ACC-114-2/3 ghim byte-trùng ca Codex.
  - `T-5116` có thể bị đọc như "máy cho phép lên mức" → `advisory: true`, ACC-116-5 ghim không tệp nào đổi, tài liệu ghi rõ.
  - `T-5119` dựa vào API chưa đọc nguyên văn → bước nghiên cứu là điều kiện vào; không xác minh được thì hoãn.
  - `T-5120` chạm hook nạp đầu phiên của mọi dự án đích → hook vẫn fail-open, ACC-120-1…3 ghim trần 10 000 ký tự.
- Đường lùi: mỗi task một PR squash, revert một commit là về hành vi cũ; không task nào đổi dữ liệu đã ghi của dự án đích
  (manifest giữ tên map, sổ lát giữ schema).

## 11. Chưa xác minh
- Gemini CLI có cần bật cấu hình để đọc `.agents/skills` không (T-5114 đọc trước khi làm).
- Chữ ký hook plugin OpenCode 2.x (T-5119 đọc trước khi làm).
- Ngân sách PROGRESS ~6 600 ký tự khi khối Autopilot đầy và ~5 030 ở ca xấu nhất: tính từ mã, chưa tái hiện; ACC-120-1
  sẽ đo. Hai trần dự kiến (≈ 4 900 và ≈ 8 900) chỉ là ước lượng cho tới khi ADR của `T-5120` ghi phép tính.
