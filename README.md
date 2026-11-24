# X-Templates — khung tham chiếu phát triển phần mềm

> Thư viện **yêu cầu có ID** cho mọi loại phần mềm và ngành nghề, kèm công cụ ghép thành checklist dự án, kiểm "xong" bằng máy,
> và harness để AI agent **tự làm đến khi hoàn thành** mà vẫn dừng đúng chỗ cần người.
> Nội dung tiếng Việt; phiên bản, chuẩn và luật có nguồn và ngày kiểm tra theo từng mục. Mục ghi **chưa xác minh** cần đối chiếu trước khi áp dụng.
>
> Mã mở [MIT](LICENSE), miễn phí. Thấy hữu ích? [Ủng hộ tác giả](#ủng-hộ-và-liên-hệ) ☕

Bản đã gắn tag: xem [danh sách tag](https://github.com/www-donghanhcungban-org/X-Templates/tags) hoặc chạy `git describe --tags --abbrev=0` (số bản không ghi ở đây để khỏi lệch mỗi lần cắt bản; `xt.py validate` kiểm). [CHANGELOG](CHANGELOG.md) ghi thay đổi trên `main` theo từng bản. [PROGRESS](PROGRESS.md) ghi việc đang làm và mốc bàn giao.

## Vì sao dùng X-Templates

| Bạn gặp | X-Templates giúp |
|---|---|
| Không biết dự án còn thiếu gì: bảo mật, log, backup, pháp lý… | ~2.850 yêu cầu có ID (1.545 MUST) cho 14 loại phần mềm và 8 ngành, mỗi mục có cách kiểm và nguồn kèm ngày xác minh |
| Checklist quá dài so với quy mô thật | Ghép theo loại phần mềm + ngành + quy mô S/M/L: `web-app` có 70 MUST ở bản prototype, 473 ở production |
| "Xong" chỉ là lời nói | `blueprint-status --strict --run` chạy lệnh kiểm của từng mục; `release-check` ra GO/NO-GO cho phát hành |
| AI agent làm nhanh nhưng dễ phá hoặc khai "xong" sai | `/autopilot` trong Claude Code: mỗi task có bằng chứng máy, mỗi lát một PR, hook chặn thao tác không đảo ngược và lộ bí mật, dừng đúng chỗ cần người |
| Tuân thủ luật Việt Nam khó tra | Gói ngành dẫn Luật Bảo vệ dữ liệu cá nhân 91/2025, NĐ 356/2025, Luật An ninh mạng 116/2025, cùng chuẩn quốc tế (OWASP, EU AI Act) |
| Ngại cài thêm công cụ | Một lệnh `install.py`; CLI chỉ dùng thư viện chuẩn Python; app cục bộ 7 màn xem tiến độ, kế hoạch, PR |

Phù hợp cho lập trình viên và nhóm nhỏ muốn làm phần mềm đúng chuẩn production, tech lead cần checklist audit trước
phát hành, và người dùng AI agent muốn giao việc dài mà vẫn kiểm soát được chất lượng.

## Có gì trong khung

| Mảng | Nội dung | Số file |
|---|---|---|
| [`00-method`](framework/00-method/README.md) | Nguyên tắc P1–P12, vòng đời G0–G8, quy ước module, cách ghép blueprint, luật bằng chứng, audit | 6 |
| [`01-baseline`](framework/01-baseline/README.md) | Thứ **mọi** phần mềm đều cần: repo, cổng chất lượng, bảo mật tối thiểu, lỗi/log, cấu hình, tài liệu, đúng dữ liệu, phụ thuộc | 8 |
| [`02-profiles`](framework/02-profiles/README.md) | 14 hồ sơ loại phần mềm: web, mobile, desktop, site tĩnh, API, CLI, thư viện, data/ML, **AI agent**, **hệ agentic**, game, blockchain, IoT, monorepo | 14 |
| [`03-industries`](framework/03-industries/README.md) | 8 gói ngành có khung pháp lý Việt Nam + quốc tế: fintech, y tế, giáo dục, TMĐT, chính phủ, SaaS đa tenant, truyền thông, logistics | 8 |
| [`04-standards`](framework/04-standards/README.md) | Tiêu chuẩn: bảo mật, tiếp cận, API/web, dữ liệu, quy trình, AI — phiên bản hiện hành và cách chứng minh | 6 |
| [`05`](framework/05-architecture/README.md)–[`09`](framework/09-database/README.md) | Kiến trúc · Thiết kế & UI/UX · Frontend · Backend · Cơ sở dữ liệu | 36 |
| [`10-workflow`](framework/10-workflow/README.md) | Git, review, CI/CD, phát hành, môi trường, spec-driven, tài liệu, đội & WIP | 8 |
| [`11-autonomous-loop`](framework/11-autonomous-loop/README.md) | Vòng lặp tự động: 4 con số, bằng chứng, điểm dừng, điều phối subagent, tự sửa CI, ngân sách context, phản hồi từ dự án đích, vòng tối ưu hiệu năng | 8 |
| [`12-security`](framework/12-security/README.md) | Threat model, AppSec, bí mật, chuỗi cung ứng, hạ tầng, bảo mật AI, log & audit | 7 |
| [`13-ai-engineering`](framework/13-ai-engineering/README.md) | LLM app, RAG, agent & tool, hệ agentic, eval, guardrail, MCP/A2A, quan sát & chi phí, dữ liệu | 9 |
| [`14`](framework/14-testing-quality/README.md)–[`18`](framework/18-cross-cutting/README.md) | Kiểm thử · Vận hành · Tuân thủ & quyền riêng tư · Sản phẩm & dự án · Xuyên suốt (i18n, hiệu năng, DX, tài liệu cho AI, đơn vị/tiền/thời gian, bền vững, OSS) | 37 |
| [`templates`](framework/templates/README.md) | PROJECT, PLAN, PROGRESS, SPEC, ADR, THREAT-MODEL, RUNBOOK, POST-MORTEM, DPIA, GO-NO-GO, RELEASE-NOTES, API-CONTRACT, AGENTS, CLAUDE, xt.yaml, AUDIT-STATUS, AUDIT-REPORT, PULL-REQUEST, dependabot.yml, ui-gates/ | 20 |

Mỗi yêu cầu là một dòng có **ID ổn định**, mức **MUST/SHOULD/MAY**, cách **Kiểm** bằng máy và **Nguồn**:

```markdown
- [ ] `BE-AUTH-003` **MUST** Băm mật khẩu bằng Argon2id với tham số OWASP. → Kiểm: test đọc hash có tiền tố `$argon2id$`. · Nguồn: ASVS 5.0 V6
```

Chỉ mục đầy đủ theo vai đọc: [`framework/README.md`](framework/README.md).

## Dùng cho một dự án

Trong Claude Code, dùng `/factory "Sổ ghi chú cho nhóm, cho tôi thử MVP trước"` để nhận bản dev chạy được
và một lượt duyệt với cách thử. Để giao cả vòng đời, dùng
`/factory "Làm sổ ghi chú cho nhóm, tối ưu thời gian tạo ghi chú trước khi phát hành và đo mức sử dụng"`. Trong Codex, gọi cùng quy trình bằng `$factory`.
Agent có thể bắt đầu từ ý tưởng hoặc tiếp tục repo hiện có theo sổ giai đoạn, PLAN và bằng chứng phát hành.
Mặc định audit và diễn tập ở giai đoạn 2, tối ưu và thử lại ở giai đoạn 3 trước lần phát hành production đầu tiên, rồi vận hành và thử nghiệm tăng trưởng. Sản phẩm đang chạy có thể dùng số liệu vận hành làm mốc.
Xem [quy trình factory](.claude/skills/factory/SKILL.md) và [gói web-api-ts](framework/templates/packs/web-api-ts/README.md).

Để tự tạo repo khởi đầu với cùng gói, dùng CPython 3.13 trở lên và thay `/đường/dẫn/dự-án` bằng thư mục mới hoặc rỗng.

```bash
git clone https://github.com/www-donghanhcungban-org/X-Templates /tmp/x-templates
python3 /tmp/x-templates/scripts/install.py /đường/dẫn/dự-án --new --name so-ghi-chu --pack web-api-ts --idea "Sổ ghi chú cho nhóm"
cd /đường/dẫn/dự-án
python3 .xtemplates/scripts/xt.py stage status
python3 .xtemplates/scripts/xt.py blueprint-status BLUEPRINT.md
```

`--new` tạo repo git, starter, blueprint quy mô S và sổ giai đoạn 1 (MVP). `PROJECT.md` lưu ý tưởng và
dành bốn dòng Khung cho bước xác định MVP. Lệnh hoàn tất sau `doctor --offline`. Để chạy bản dev cần cài phụ
thuộc của gói và có Docker Compose. Khi phát hành, kiểm các mục MUST bằng `blueprint-status BLUEPRINT.md --strict --run`.
Với Codex, thêm `--harness codex` vào lệnh `--new`; skill và hook nằm ngay trong commit đầu. Repo đã có mã dùng `install.py <đích> --harness codex` để bổ sung chúng. Tại gốc sản phẩm, `python3 .xtemplates/scripts/xt_flow.py --json` đọc bằng chứng hiện có
và cho biết bước tiếp theo thuộc về agent hay người duyệt.

**Repo đã có mã.** Chạy `python3 /tmp/x-templates/scripts/install.py /đường/dẫn/dự-án --with-github`. Với bản ≤ 2.x,
installer chuyển sang `.xtemplates/`, `xt.py`, `xt.yaml` và liệt kê tên cũ cần sửa
([ADR-0007](docs/adr/0007-rename-technical-identifiers-to-xtemplates.md)). Ở lần cài thông thường, thêm `--stage-init`
để khởi tạo giai đoạn 1 nếu chưa có sổ. Với sản phẩm đang ở giai đoạn 2 hoặc 3, chủ dự án dùng
`xt.py stage init --adopt 2|3 --evidence …` ([ADR-0058](docs/adr/0058-product-stages-machine-lock.md)).

Khi cài vào repo có sẵn và tạo `xt.yaml` lần đầu, `--preset safe` chọn `L1` / `human` / `harden`,
`--preset autonomous` chọn `L3` / `auto` / `build`. Cài lại giữ chính sách đã chọn. Xem trước bằng
`install.py <dự-án> --preset safe --plan`. Sau cài đặt, khai lệnh thật ở `xt.yaml`, chạy `doctor` rồi kiểm Gate
([ADR-0055](docs/adr/0055-optional-install-policy-presets.md)).

Quy mô quyết định khối lượng: `web-app` có 70 MUST ở **S** (prototype), 473 ở **M** (production), 1.154 ở **L** (đo 2026-11-20).
`--out BLUEPRINT.md` ghi file chính chỉ chứa MUST theo quy mô (web-app + ecommerce: 41 KB ở S thay vì ~690 KB) và
`BLUEPRINT-BACKLOG.md` chứa SHOULD/MAY ([ADR-0012](docs/adr/0012-blueprint-by-scale-and-task-iteration-cap.md)).
Ghép thêm module ngoài hồ sơ bằng `--add`, ví dụ web app có tính năng AI: `--add "13-ai-engineering/*"`.

Để giảm ngữ cảnh mỗi task, dùng `xt.py context --task T-NNN --plan <PLAN>` thay vì nạp toàn bộ blueprint; chọn
quy mô theo rủi ro thật và giải trình mục không áp dụng. Thư viện dùng được qua nhiều công cụ; harness tự động
hiện tập trung vào Claude Code + Bash + GitHub. Bộ cài và CLI dùng CPython 3.13 trở lên (CI chính ghim 3.15.2, thêm job kiểm trên 3.13) trên môi trường POSIX (Linux; macOS chưa được CI kiểm — mọi workflow chạy `ubuntu-latest`;
trên Windows cần chạy qua WSL2 hoặc DevContainer/Docker vì hook Bash và bộ cập nhật state cần đường dẫn POSIX, `fcntl` và
filesystem hỗ trợ `flock` — thiếu `fcntl` lệnh ghi state thoát 2). CI trên Linux dùng bản ghim ở `.python-version`. Môi trường local
và runner cần chọn `python3` là CPython 3.13 trở lên. Sàn runtime: [ADR-0094](docs/adr/0094-python-313-floor.md); cách chuyển workflow đã cài: [ADR-0078](docs/adr/0078-python-315-runtime.md).
Tài liệu ngành là đầu vào rà soát; yêu cầu pháp lý chưa xác minh cần người có chuyên môn xác nhận.

## Chạy tự động đến khi xong

Trong Claude Code, sau khi cài khung, gõ `/autopilot <mô tả yêu cầu>`:

1. Agent lập kế hoạch gọn G0–G4 (pha build dùng đầu ra mức S — ADR-0046): đọc repo, `BLUEPRINT.md`, `PLAN.md` có task, lệnh kiểm và Given/When/Then ngắn; nghiên cứu/spec riêng chỉ khi thêm phụ thuộc hay nghiệp vụ không tầm thường.
2. Phiên chính tự duyệt kế hoạch theo tiêu chí chất lượng cuối và ghi `D-NNN` (ADR-0008); bạn can thiệp lúc nào cũng được.
3. Vòng lặp chạy: làm task, `xt.py loop record` ghi bằng chứng, commit, mỗi lát một PR, máy merge ghim head khi `merge-check` = `merge` ở đúng head (ADR-0036; review theo chính sách nhánh đích — ADR-0079), trừ ngoại lệ cứng auth/tiền/dữ liệu thật/mật mã khi `merge_hard_exceptions: human` (ADR-0016, ADR-0020). Stop hook đọc bằng chứng trên đĩa để quyết làm tiếp.
4. Mỗi đợt **build xong** (mọi task có bằng chứng xanh, `loop verify --all`; MUST blueprint còn mở ghi số, không chặn ở pha build) → `/audit delta` → sửa/đợt kế, lặp tới khi **hết việc** (PLAN hết task, 0 MUST mở ngoài việc chờ người, audit toàn diện 0 🔴/🟠) rồi **đề xuất** `/complete` (ADR-0047). Dừng khi chạm ngân sách, khi cùng một lỗi lặp 3 lần, hoặc ở **điểm dừng bắt buộc**:
   thao tác không đảo ngược (máy chặn), tiền thật, dữ liệu người dùng thật, đăng ký dịch vụ trả phí/nhập khoá thật
   (`loop defer`, gom cho người). Deploy/publish và đổi cấu hình cổng kèm lý do **cho chạy** (ADR-0018, D-023 — lớp đỡ
   là CI/ruleset nhánh/review); mâu thuẫn spec không còn là điểm dừng: phiên chính tự quyết, ghi `D-NNN`.
5. Hoàn thiện và phát hành bằng `/complete` (pha harden, ADR-0046): PR đặt `delivery_phase: harden` → `/audit` → trả nợ
   review theo PR/lát → `PLAN-harden` (🔴/🟠, MUST còn mở, sàn Gate M/L, thiết kế đầy đủ, refactor, hiệu năng) chạy cùng vòng
   lặp với luật harden → `xt.py release-check` → `GO-NO-GO.md`. Người ký theo mặc định. Dự án bật ký tự động dùng
   `xt.py release-sign` khi đủ điều kiện của [ADR-0074](docs/adr/0074-agent-release-signoff.md). Lặp lại mỗi bản phát hành.

Hook trong [`.claude/`](.claude/settings.json) chặn thao tác nguy hiểm/không đảo ngược (lệnh phá huỷ, `curl | sh`, push nhánh chính…) mà không hỏi người (ADR-0018),
chạy cổng chất lượng trước mỗi commit. Luật cho mọi harness ở [`AGENTS.md`](AGENTS.md). Giao thức đầy đủ:
[`framework/11-autonomous-loop/README.md`](framework/11-autonomous-loop/README.md).

## Ứng dụng cục bộ

```bash
python3 scripts/xt.py app                 # repo khung
python3 .xtemplates/scripts/xt.py app     # dự án đích (sau install.py)
```

Lệnh in một URL `http://127.0.0.1:<cổng>/#t=<token>` và mở trình duyệt. Có 7 màn: Tổng quan · Thư viện yêu cầu ·
Ghép blueprint · Tiến độ blueprint · Kế hoạch và phân chia việc (cùng kết quả `xt.py plan waves`) · Vòng tự động, việc
chờ người, quyết định và ADR · PR (cần `gh` đã đăng nhập; thiếu thì màn báo lý do, các màn khác vẫn chạy).

App **không chạy lệnh**: không Gate, merge, push hay defer — mỗi màn chỉ hiện lệnh để chép sang terminal, nơi guard
kiểm. Ngoại lệ duy nhất là nút "Ghi BLUEPRINT.md", đi đúng đường của `compose --out` (giữ tick theo ID). Máy chủ chỉ
nghe 127.0.0.1, đòi token mỗi lần chạy, kiểm `Host`/`Origin` và đặt CSP chặt — mô hình đầy đủ ở
[ADR-0038](docs/adr/0038-local-app-on-xt.md), hợp đồng API ở [`SPEC-app.md`](docs/specs/SPEC-app.md).
`xt.py app --smoke` gọi mọi API rồi thoát (exit 1 khi có route lỗi) — dùng để kiểm bản cài.

## Công cụ

| Lệnh | Việc |
|---|---|
| `python3 scripts/xt.py validate` · `python3 scripts/xt.py list profiles` | Kiểm quy ước toàn khung: frontmatter, ID duy nhất, MUST có cách kiểm, liên kết, ID được nhắc phải có mục định nghĩa; `validate --stale N [--today YYYY-MM-DD]` liệt kê dòng "xác minh YYYY-MM-DD" cũ hơn N ngày |
| `python3 scripts/xt.py compose ...` | Ghép blueprint theo hồ sơ, ngành, quy mô; ghép lại vào file có sẵn thì giữ trạng thái theo ID |
| `python3 scripts/xt.py blueprint-status FILE --strict [--run] [--json]` | Đếm đạt/miễn/chưa (+ `unchecked_must_ratio` trong `--json`); dòng mục sai định dạng, mục MUST ít hơn bảng đầu trang hay miễn trừ thiếu lý do ở phần ghi chú = lỗi; `--run` chạy lại lệnh `— Kiểm: \`…\`` của mục đã tick trong thư mục chứa FILE, đỏ = chưa đạt (`LOOP-DESIGN-023`); cổng phát hành; `FILE` là `-` thì đọc stdin (không `--run`) |
| `python3 scripts/xt.py floor [--run] [--skip KEY]… [--strict] [--json]` | Sàn Gate M/L (`LOOP-HARNESS-023`: `format_check`, `coverage`, kiểm kiểu theo stack, `e2e`): liệt kê khoá đã khai/thiếu; `--run` chạy lệnh đã khai qua guard (bỏ lệnh trùng `gate`), đỏ → exit 1; thiếu khoá chỉ cảnh báo trừ `--strict`; quy mô S → không áp. CI mẫu chạy `floor --run --skip e2e` sau `gate-par` (AUD-XFEAT-020) |
| `python3 scripts/xt.py doctor [--fix] [--json] [--offline]` | Audit khung đã cài trước `/autopilot`: Python/git/bash, hook + file hook + cú pháp, skill/subagent, `*.xtemplates-new` chưa gộp, Agent Teams bật không ADR và agent ngoài ghim model (`LOOP-ORCH-021/022`), cấu hình harness rò/mở quyền (`LOOP-HARNESS-032`: `enableAllProjectMcpServers`, `settings.local.json` không có trong `.gitignore` hoặc đã bị track), `AGENTS.md`/`CLAUDE.md`, `xt.yaml`, `.gitignore`, state, khung `validate`, `PROGRESS.md`; `--fix` sửa phần an toàn (không đụng hook/settings); `--offline` giữ mọi kiểm cục bộ, không tra phiên bản mới qua mạng; exit 1 khi còn lỗi |
| `python3 scripts/xt.py loop init/status/next/next-step/record/block/defer/decide/decide-prod/checkpoint/resume/attach/resolve/unblock/stop` | Vòng lặp autopilot có bằng chứng, chạy một phiên đến khi xong (ADR-0009); `next` chọn task sẵn sàng theo `sau:`/`files:`; `next-step` bước kế của mục tiêu, chỉ đọc (ADR-0052 §5; `--objective harden-to-signoff` gom việc harden nháp ID ổn định, `--release`/`--package` dựng và kiểm gói nghiệm thu nháp); `decide` ghi quyết định tự duyệt D-NNN (ADR-0008); `decide-prod --ref D-NNN --choice …` thêm mục ghi quyết định của chủ dự án cho một đề xuất "Khi chạy thật" (D-399); `attach` gắn phiên mới (sau `/clear`) giữ việc chờ/đếm lỗi · `resolve --task ID --reason` gỡ một việc chờ · `unblock --reason` mở vòng bị chặn/đã dừng, giữ việc chờ (ADR-0051); `resume` = lệnh cũ làm cả bốn việc, in cảnh báo |
| `python3 scripts/xt.py loop ci-triage/triage-local/stats/verify/hook-stop` | `ci-triage` phân loại lỗi một run CI và trừ ngân sách sửa (AUTO-04; exit 1 = block/defer) · `triage-local` đọc JSON hook `PostToolUseFailure` từ stdin, lệnh Bash cổng/Gate đỏ → ≤ 20 dòng lỗi đã che bí mật, phân loại như `ci-triage`, không trừ ngân sách; luôn exit 0 (fail-open) · `stats` số đo vòng từ `.autopilot/runs.jsonl` · `verify` kiểm lại cuối: chạy lại Gate có đầu vào đổi · `hook-stop` dùng bởi Stop hook |
| `python3 scripts/xt.py loop run --agent claude\|codex\|gemini\|cursor\|copilot\|grok\|opencode [--agent-args S] [--max-turns N] [--timeout S] [--dry-run]` | Vòng lặp ngoài cho mọi công cụ agent (ADR-0064 lát D): mỗi lượt đọc `loop_verdict` từ bằng chứng trên đĩa, gọi agent headless cho đúng task máy chọn, dừng khi máy báo xong/BLOCKED hoặc hết lượt/giờ; tiến triển chỉ tính theo `loop record` |
| `python3 scripts/xt.py pr next/reviewed/debt/rethink/steward/title-check/stats` | Merge theo làn (ADR-0024/0027): `next` in MỘT hành động kế tiếp cho PR · `reviewed --pr N --head SHA --clean\|--blocking\|--inconclusive` ghi sổ review và đăng lên PR · `debt --pr N [--findings AUD-…] [--fixed AUD-…]` khi `next` trả `debt` (review 1 lần — ADR-0062: 🟠/🟢 ghi `nợ-review: #N` ở sổ audit, 🔴 sửa trong một commit và ghi `đã sửa` rồi khai `--fixed` — không rà lại; sau review chỉ sổ hoặc bản sửa 🔴 đổi; nợ trả cuối pha) · `rethink --pr N --decision D-NNN` mở thêm một lần sửa khi `next` trả `rethink` (PR cắt bản, `review_identity`) — D-NNN mới, câu hỏi nhắc `#N` (ADR-0053); tối đa `max_rethink` lần/PR (xt.yaml, mặc định 1; 0 = không trần; PR cắt bản miễn), hết → `next` trả `split-or-close` (ADR-0061) · `steward [--apply]` chạy `pr next` cho mọi PR mở (workflow `pr-steward`) · `title-check [TITLE]` kiểm tiêu đề TRƯỚC `gh pr create` bằng đúng luật bước CI `checks`/`merge-check` (Conventional Commits, ≤ 100 ký tự — D-056): 0 hợp lệ · 1 sai kèm gợi ý · 2 không có TITLE và không đọc được PR mở của nhánh · `stats [--days 30] [--repo R] [--json]` số đo PR đã merge trong N ngày chỉ qua REST: lead time mở → merge (trung vị, P95), run CI `pull_request` mỗi PR (theo `head_branch` + `head_sha`), tỉ lệ run `failure`/`cancelled`, PR nhãn `xt-standard-lane`, PR revert, `pushes` (head SHA riêng biệt mỗi PR), `first_push_green` (PR xanh ngay run đầu của push đầu), `cancelled_same_sha` (run huỷ mà cùng SHA còn run khác — vết `edited`); run đọc theo workflow CI (`XT_CI_WORKFLOW`) từng ngày để vượt trần 1.000 của listing, ngày vẫn chạm trần → `runs_truncated: true` + cảnh báo — bảng Markdown `/handover` dán vào `PROGRESS.md` (run CI hết hạn sau retention 90 ngày) |
| `python3 scripts/xt.py grant-check GROUP [KHOÁ=GIÁ_TRỊ …]` | Việc production có nằm trong mục Ủy quyền production của PLAN.md không: exit 0 làm, 1 `loop defer` (ADR-0022) |
| `python3 scripts/xt.py guard-check -- <lệnh>` | exit 126 nếu guard cấm lệnh, lỗi nạp hoặc fallback cũng hỏng (ADR-0054); `dev-task.sh`, Gate/`Kiểm:` qua cùng kiểm (LOOP-STOP-027). Dự án chưa cài harness giữ tương thích |
| `python3 scripts/xt.py harness-check` | lệnh kiểm chỉ đọc cho mục hàng rào (`LOOP-ORCH-003`, `LOOP-STOP-001/002`): guard của dự án chặn bộ lệnh mẫu, `permissions.ask` rỗng, agent khai `tools:` tường minh, không `permissionMode`, không `Agent`/`Task`, `reviewer*` không `Edit`/`Write`; exit 1 nếu hàng nào hỏng |
| `python3 scripts/xt.py release-check [--blueprint F] [--status F] [--unchecked-must {warn,fail}] [--json]` | Cổng G7 máy đọc (ADR-0029): gom `blueprint-status --strict --run`, `audit check --strict`, kiểm lại cuối khớp cây, cây git sạch + HEAD, đề xuất "Khi chạy thật" chờ người, pha `harden`, giai đoạn sản phẩm (`stage`: MVP chưa mở Production — ADR-0058) và nợ review sau SHA quét (ADR-0031; file chỉ đổi bởi PR đã merge có review sạch ở head được phủ — ADR-0057), lệnh `attack`/`perf` và cổng production `migration_check`/`acceptance`/`rollback` của xt.yaml (ADR-0042, ADR-0062), `go_no_go` (`GO-NO-GO*.md` nhắc `v<VERSION>` ở `docs/ops/`, `docs/`, gốc có chữ ký §5 — thiếu/chưa ký = BLOCKER chờ người ở mọi quy mô; AUD-HAR-197), số + tỉ lệ MUST tick không có lệnh kiểm (`unchecked_must`: `warn` mặc định, `fail` = NO-GO) → PASS/WARN/FAIL/N-A có bằng chứng, `verdict` GO / GO (chờ người) / NO-GO; exit 1 khi NO-GO — phần máy của `GO-NO-GO.md` |
| `python3 scripts/xt.py deploy run --env E [--json]` | Ở dev, triển khai gói trên loopback, thử luồng trình duyệt và xác minh digest. Với môi trường cấu hình riêng, dự án cung cấp adapter và grant đúng đích. Production cần ứng viên đã ký trên nhánh mặc định của remote và digest đọc lại tại đích. |
| `python3 scripts/xt.py deploy rollback --env E [--json]` | Khôi phục artifact trước, đối chiếu digest tại đích rồi cập nhật receipt. Môi trường cấu hình riêng cần quyền triển khai tương ứng. |
| `python3 scripts/xt.py deploy status [--env E] [--json]` | Đọc bản triển khai gần nhất được xác nhận theo ADR-0077. JSON gồm sổ và `metrics` theo môi trường, tính trên các sự kiện còn lưu (`runs`, `rollback_rate` từ 0 đến 1, `durations_seconds` theo thứ tự sự kiện). Exit 2 nếu cấu hình môi trường hoặc sổ hỏng. |
| `python3 scripts/xt.py admin-plan [--json\|--script] [--only ITEM] [--out MARKDOWN]` | Sau bản dev, kiểm thiết lập và gom việc còn thiếu cho chủ dự án. `--only ruleset` chỉ kiểm và trả mã thoát theo hàng ruleset, không phụ thuộc các thiết lập khác. `--script` in lệnh để rà trước khi áp dụng; quyền tạo tag ở `tags-create.json` cần đúng một App phát hành, còn `tags.json` chặn sửa/xoá không có bypass. |
| `python3 scripts/xt.py rollout-drill --env ENV [--release FILE] [--require-ready] [--json]` | Diễn tập trước production, kiểm artifact, receipt và digest đang phục vụ ở dev. `--require-ready` yêu cầu cả các điều kiện sẵn sàng để phát hành. Thao tác triển khai thật theo runbook của dự án. |
| `python3 scripts/xt.py ops-check --env ENV --field FILE --max-p95-ms MS --max-error-pct PCT [--max-age-hours H] [--json]` | Đối chiếu số đo field với môi trường, digest, khoảng đo và hai ngưỡng SLO. File do người vận hành/CI cung cấp cần `source` và `exported_at` UTC. Dùng `--max-age-hours` khi cần chặn số đo cũ. Nguồn là nhãn do bên xuất khai. [Runbook và mẫu số liệu](framework/templates/RUNBOOK-FACTORY-ROLLOUT.md). |
| `python3 scripts/xt_flow.py [--project DIR] [--prs FILE] [--release FILE] [--merged-prs FILE] [--json\|--github-summary]` | Đọc giai đoạn, bằng chứng và số đo để xác định hành động và người phụ trách tiếp theo. `--prs` nhận kết quả `pr next --json`, `--merged-prs` nhận danh sách pull request từ REST để so thời gian các nhóm. |
| `python3 scripts/xt.py acceptance lock/check/amend` | Khoá SPEC và bộ test độc lập trước khi viết mã. `check --json` đối chiếu digest. Sửa bộ test đã khoá cần quyết định mới, lý do và reviewer độc lập. |
| `python3 <khung>/scripts/xt_acceptance.py check --base SHA --project DIR` | Chạy từ checkout khung riêng đã ghim phiên bản tin cậy. Đối chiếu repo sản phẩm DIR với SHA nghiệm thu đã duyệt trước khi viết mã. Phạm vi mặc định ở `docs/autopilot/ACCEPTANCE.paths` của mốc. Exit 0 khi khớp, 1 khi đổi, 2 khi đầu vào lỗi. Bài kiểm nghiệp vụ chạy riêng. |
| `python3 scripts/xt_guard_profile.py [--path F] [--repeat N] [--top N] [--json] [--closure HẠT_GIỐNG…]` | Chỉ đọc, chỉ ở repo khung. `--closure` thay đo tổng quát bằng bao đóng phụ thuộc ở mức hàm của các hạt giống (tên hàm hoặc `family:<họ>`): hàng kèm theo, hằng đi kèm và điểm vào từ ngoài. Đo thời gian compile của `.claude/hooks/guard.py` (hoặc tệp chỉ định), họ hàm theo tiền tố với số dòng, cạnh gọi giữa các họ và hằng dùng chung nhiều họ; số đo cho việc tách guard ([ADR-0090](docs/adr/0090-split-guard-and-xt-monoliths.md), [ADR-0091](docs/adr/0091-progress-hook-cap-and-split-constraints.md)). Cạnh gọi xấp xỉ theo tên. Exit 0 khi đo được, 2 khi đầu vào lỗi. |
| `python3 scripts/xt_pack.py build --out DIST/xt.pyz [--strict]` · `verify DIST/xt.pyz [--sha256 HEX]` | Chỉ ở repo khung (ADR-0097, pha P1): dựng artefact `.pyz` tất định (`ZIP_STORED`, mục sắp theo tên, `mtime` cố định; cùng nguồn cho cùng `sha256`) chứa `xt.py`, `xt_*.py`, `xt_app` và `VERSION`; `--strict` đòi đủ module; `verify` so từng byte với bản dựng từ nguồn và với ghim 64 hex. Mã thoát 0 đạt · 1 lệch · 2 dùng sai. Chưa dùng để cài: `install.py` vẫn chép mã (pha P5). |
| `python3 scripts/xt.py release-sign --note TEXT [--file F]` | Ký §5 GO-NO-GO cho đúng phiên bản và subject khi G7 cho phép. Quyền `release_signoff: agent` và trần `release_signoff_scale` phải có hiệu lực ở cây làm việc và nhánh mặc định của remote. M/L cần nghiệm thu độc lập, giao đúng artifact và bằng chứng rollback. L cần đo 0 lỗi lọt trong 14 ngày. [ADR-0074](docs/adr/0074-agent-release-signoff.md) |
| `python3 scripts/xt.py stage status/init/submit/reopen/approve/new-cycle` | Sổ giai đoạn ở `docs/autopilot/STAGE.json`. Trình HEAD sạch bằng `submit --evidence`; người duyệt bằng `approve --sha --note`. Agent được duyệt trong trần `stage_approval_max` khi có `stage_approval: agent`. Giai đoạn 2/3 đối chiếu quyền remote, nghiệm thu đã khoá và receipt dev; giai đoạn 3 cần thêm perf PASS. Người phụ trách `init --adopt` cho dự án đã chạy. [ADR-0069](docs/adr/0069-agent-stage-approval.md) |
| `python3 scripts/xt.py autonomy-bench [--corpus DIR] [--json]` | Corpus PR/rollup/review/guard/log CI ở `tests/fixtures/autonomy/` chạy qua hàm thật (merge-check, `_ci_blocker`, `pr next`, guard + chính sách): exit 1 khi false-green > 0 (máy cho merge/chạy/tính xanh ở ca phải chặn), khi có ca lệch (kể cả `code` khác mong đợi) hoặc ID bắt buộc chưa có ca; 2 khi corpus hỏng/ca không chạy được; báo chặn oan và độ phủ REC §2 + 🔴/🟠 đã sửa; job CI `checks` chạy (tổng hợp vào `quality`) (AUTO-07, [baseline](docs/ops/AUTONOMY-BASELINE.md)) |
| `python3 scripts/xt.py mutate-guard [--functions …] [--tests …] [--jobs N] [--timeout S] [--list] [--json]` | Đột biến chính sách guard (`decide`/`policy_action`/`apply_policy`/`_strict_why`) bằng stdlib, mỗi mutant chạy bộ test guard: exit 1 khi còn mutant sống, 2 khi test đỏ lúc chưa đột biến (AUD-TEST-051; workflow `mutation.yml` hằng tuần) |
| `python3 scripts/xt.py app [--port N] [--no-open] [--smoke]` | App web cục bộ (ADR-0038): máy chủ 127.0.0.1 cổng ngẫu nhiên, in URL kèm token rồi mở trình duyệt; chỉ đọc (trừ ghi `BLUEPRINT.md` như `compose --out`), không chạy lệnh; `--smoke` gọi mọi `GET /api/*` rồi thoát, exit 1 khi có route khác 200 |
| `python3 scripts/xt.py plan waves [--plan F] [--max N] [--json\|--handoff]` | Xếp task mở của PLAN thành đợt chạy song song (ADR-0038): mỗi đợt `sau:` đã thoả, `files:` không giao, ≤ N task (mặc định 4 — ADR-0061; trần 5 `LOOP-ORCH-008`); chu trình, ghi chú hỏng, task defer → bị chặn kèm lý do; không cần vòng đang chạy. `--handoff` xuất ngữ cảnh đợt đầu cho giai đoạn đang mở. |
| `python3 scripts/xt.py context --task T-NNNN [--json] [--plan F]` | Gói ngữ cảnh một task của PLAN (REC-11): ID yêu cầu, đoạn spec, Gate, `files:`, file thiếu, số byte — đưa cho executor thay vì cả PLAN |
| `python3 scripts/xt.py merge-watch [--pr N] [--interval 30]` | Chạy nền sau khi mở PR: gọi `merge-check` mỗi 30 giây tới khi PR đã merge hoặc cần hành động (ADR-0021) |
| `python3 scripts/xt.py pr title-check --range BASE..HEAD` | Kiểm subject của mọi commit trong dải bằng một lần đọc Git. Miễn tác giả có đuôi `[bot]`, bỏ đuôi squash ` (#N)` trước khi kiểm. |
| `python3 scripts/xt.py merge-check [--pr N] [--json]` | Máy quyết khi nào merge PR đã mở: `merge` · `review` (chưa đủ review sạch ở head, exit 1, không in lệnh merge — ADR-0032) · `wait` · `update` · `fix` · `human` · `closed`; `merge_autonomy`: L3 (mặc định) máy merge ghim head mọi làn (làn nhanh khi CI xanh, làn chuẩn khi CI xanh, thêm review sạch ở head nếu `merge_review: required` — ADR-0079, ADR-0036; không bật auto-merge của GitHub) trừ ngoại lệ cứng (`merge_hard_exceptions: auto` thì cả ngoại lệ cứng — ADR-0020), L2 chỉ làn nhanh, L1 người merge (ADR-0013, ADR-0015, ADR-0016) |
| `python3 scripts/xt.py feedback add/collect/list/aggregate` | Phản hồi lỗi do khung + cách khắc phục từ dự án đích (`docs/xtemplates-feedback/FB-NNN.md`, qua `redact`); repo khung gộp theo (loại, ID) — ADR-0010 |
| `python3 scripts/xt.py feedback routine-check --from CHECKOUTS [--days 8]` | So các tệp phản hồi đã commit ở nhánh mặc định của từng dự án với SHA trong PR báo cáo. Trả 1 khi có mục mới và báo cáo quá hạn, 2 khi thiếu nguồn Git, 3 khi thiếu bằng chứng GitHub. |
| `python3 scripts/xt.py perf field-check --file FILE --json` · `python3 scripts/xt.py perf field-export` | Kiểm mẫu telemetry của bản đang phục vụ, đúng schema FIELD và ngưỡng của sản phẩm. Workflow `xt-field.yml` của dự án dùng nguồn đã cấu hình. [Quy trình đo](framework/11-autonomous-loop/optimization-loop.md) |
| `python3 scripts/xt.py incident check FILE --json` | Đối chiếu bằng chứng hành động khắc phục được ghi trong post-mortem. |
| `python3 scripts/xt.py release-verify --tag vX.Y.Z [--repo owner/repo]` | Xác minh archive của tag bằng Git và GitHub CLI có `gh attestation verify`. Exit 0 khi đúng nguồn và chữ ký, 1 khi sai, 3 khi chưa kiểm được. |
| `python3 .xtemplates/scripts/xt.py upgrade check\|open-pr` | Dự án đích chọn tag, kiểm cả attestation archive và biên nhận promotion trước khi cài vào PR. Canary nhận ngay. Đợt mặc định chờ 3 ngày. Chọn `--with-github` khi cài để nhận workflow. |
| `python3 scripts/install.py DỰ_ÁN [--with-github] [--preset safe\|autonomous] [--stage-init] [--pack ID] [--harness codex,…] [--plan]` | Cài khung + harness; preset chỉ chọn chính sách cho `xt.yaml` mới, cài lại giữ lựa chọn; `--stage-init` tạo sổ giai đoạn 1 khi chưa có; `--pack` cài gói sản phẩm ([`packs/`](framework/templates/packs/README.md): starter chỉ repo sạch, managed theo hash); `--harness` thêm adapter hook cho công cụ khác — `codex` còn sinh skill `.agents/skills/` và agent `.codex/agents/` từ `.claude/` — tệp sinh đi theo `.claude/` ở lần cài sau (kể cả `--force-harness`), tệp dự án sửa khác bản đã ghi nhận được giữ kèm `.xtemplates-new` ([`harness/`](framework/templates/harness/README.md), ADR-0082); `--plan` xem trước. `--with-github` cài 13 tệp `.github/` (ruleset `main.json`/`tags.json`/`tags-create.json`, mẫu PR, Dependabot, workflow CI, quét bí mật, kiểm tiêu đề PR, steward, `release-tag.yml`, `xt-field.yml`, `xt-upgrade.yml`, stub `merge-gate.yml`); điều kiện chạy của `xt-upgrade.yml`/`xt-field.yml` (secret, environment) ở [`framework/templates/README.md`](framework/templates/README.md) |
| `python3 scripts/install.py . --sync-codex` | Chỉ ở repo khung: sinh lại `.agents/skills/`, `.codex/agents/`, `.codex/hooks.json` từ `.claude/` sau khi sửa skill/agent (ADR-0082); tệp đã track dưới `.agents/`, `.codex/` phải do bộ sinh tạo — thừa thì báo, exit 1 (tệp chưa track chỉ cảnh báo), không tự xoá; `tests.test_codex_harness` đỏ khi tệp đã commit lệch |
| `python3 scripts/install.py DỰ_ÁN --new --pack ID --idea TEXT [--name N] [--scale S\|M\|L]` | Tạo repo sản phẩm mới từ thư mục trống, không cần mạng (F-111): khung + gói + `PROJECT.md` (ý tưởng là dữ liệu, 1…4000 ký tự) + blueprint theo quy mô (mặc định S), rồi chạy `doctor --offline` |
| `python3 scripts/xt.py registry [--file F] [--json] [--today D] [--strict]` | Registry sản phẩm đích (`docs/ops/registry.json`, schema 1 — ADR-0068 lát E): schema sai → exit 2; lệch core/gói so với `VERSION` (current/patch/minor/major/ahead/unknown); ngoại lệ hết hạn (`until` < hôm nay); `--strict` → exit 1 khi còn lệch/hết hạn; màn Registry ở `xt.py app` |
| `python3 scripts/xt.py derived check/list [--pr N \| TỆP…] [--json]` | Chỉ ở repo khung: kiểm bản ghi dự án phái sinh `docs/derived/<owner>--<repo>.json` (schema 1). `check --pr` kiểm như làn `derived` của `merge-check`. Exit 0 hợp lệ, 1 trái luật, 2 lỗi đọc ([hướng dẫn](docs/derived/README.md), ADR-0087). |
| `python3 scripts/xt.py registry pull --from DIR [--file F]` | Cập nhật registry từ sổ triển khai của các clone cục bộ có GitHub origin khớp repo đã khai. Ghi các môi trường có receipt hiện tại và thông tin bản production theo schema của registry. |
| `python3 scripts/xt.py progress-check [FILE]` | `PROGRESS.md` ≤ 8 KB, đúng 4 mục, SHA ở Bàn giao phiên là tổ tiên HEAD và có trên nhánh chính (`XT_PROGRESS_BASE`, mặc định `origin/HEAD` → `origin/main` → `origin/master`; CI cần `fetch-depth: 0`) |
| `python3 scripts/xt.py changelog-check [FILE]` | `CHANGELOG.md` theo Keep a Changelog 1.1.0: `## [Unreleased]` đầu tiên, bản `## [X.Y.Z] - YYYY-MM-DD` giảm dần, nhóm chuẩn, không trùng nhóm trong Unreleased; bản mới nhất == `VERSION` cùng thư mục (nếu có) |
| `python3 scripts/xt.py license-check [--requirements F]… [--allow F] [--today D]` | License (`importlib.metadata`) của mọi gói ghim `==` trong `requirements-dev.txt` (hoặc file chỉ định) đối chiếu allowlist SPDX của `license-allow.json`; ngoại lệ cần `approved_by` + `expires`, chỉ khớp đúng license đã duyệt; vi phạm, gói ghim chưa cài hoặc ngoại lệ quá hạn → exit 1 (BASE-DEP-005); chạy trong `lint` |
| `python3 scripts/xt.py ci-check [DIR]` | Fitness function cho workflow CI: `permissions:` cấp workflow, không `write-all`, `uses:` ghim SHA 40 ký tự (`docker://` ghim `@sha256:`), job có `timeout-minutes`, không `continue-on-error`, workflow có `pull_request` thì job không `environment:` không chạm `secrets.*` ngoài `GITHUB_TOKEN` (`WF-CI-023`; ngoại lệ `# ci-check-allow: <lý do>`) |
| `python3 scripts/xt.py checks` | Một tiến trình chạy lần lượt `validate` · `progress-check` · `changelog-check` · `ci-check` · `license-check` với đối số mặc định (đúng việc năm lệnh đó, không đổi hành vi); `lint` của `xt.yaml` dùng lệnh này — 5 lần khởi động `xt.py` (~250 ms mỗi lần) thành 1. Mục xanh một dòng `✓ tên: exit 0`; mục đỏ kèm chi tiết của chính lệnh đó và không chặn mục sau; dòng cuối tổng kết; exit 1 khi bất kỳ mục nào ≠ 0 (mã riêng từng mục ở dòng của nó, thiếu file → mục đó exit 2) |
| `python3 scripts/xt.py contrast FILE.css… [--pairs F] [--require-on a,b] [--json]` | Tương phản WCAG của cặp token màu trong CSS ở mọi theme (`:root`, `.dark`, `[data-theme=dark]`, `prefers-color-scheme`): tự suy cặp `--X-foreground`/`--on-X` trên `--X`, `--foreground` trên `--background`, `--ring` ≥ 3:1; cặp khác khai ở `--pairs` (`FG on BG [min N]`); chữ < 4,5:1 hoặc phi văn bản < 3:1 → exit 1; `--primary`/`--destructive` thiếu token chữ cũng đỏ (`UX-DS-003/020`) |
| `python3 scripts/xt.py static-check KIND [PATH…] [--opt K=V]… [--json]` | Kiểm tĩnh theo loại cho tệp của dự án (gói `xt_checks`, [ADR-0099](docs/adr/0099-static-check-kinds.md)): mười một loại: `nfc` (văn bản tiếng Việt phải NFC), `credits` (sổ bản quyền asset), `tokens` (token thiết kế, màu hard-code), `motion` (`prefers-reduced-motion`, chớp), `trace` (OTLP: span mồ côi, thiếu `gen_ai.*`), `ac-trace` (tiêu chí `AC-xx` ↔ test), `sbom` (CycloneDX), `vex` (OpenVEX), `pii-vn` (CCCD, số điện thoại, email, cột nhạy cảm), `i18n` (catalog dịch), `dedup-leak` (train ∩ eval); bảng yêu cầu và mã ở ADR-0099; thêm loại là thêm một module, không đổi hợp đồng. Chỉ đọc, chỉ stdlib; 0 sạch, 1 có phát hiện, 2 dùng sai |
| `python3 scripts/xt.py prompt-assets-scan [PATH…] [--exempt F] [--patterns F] [--today D] [--json]` | Cổng tài sản prompt (`SEC-AI-018` ≥ 6 luật, `SEC-AI-028`, `CMP-LIC-024`): injection (`--patterns` dùng chung file với bộ lọc runtime), ký tự ẩn/không UTF-8, lệnh nguy hiểm, bí mật, lời bỏ hàng rào, gói/URL không ghim, system prompt rò rỉ; miễn trừ JSON có `path` + `rule` bắt buộc (id luật, `"*"` = mọi luật) + `reason` + `expires` — `path` khớp theo đoạn: `dir/*` không phủ thư mục con, dùng `dir/**`; đích vắng thuộc danh sách mặc định bỏ qua, đích khác vắng → exit 2; vi phạm → exit 1 |
| `python3 scripts/xt.py vendor-check [--dirs a,b] [--allow X] [--strict] [--json]` | Mã UI vendor: thư mục `vendor`/`third_party`/… có `LICENSE`/`NOTICE`/`SOURCE`, không điều khoản hạn chế (Commons Clause, phi thương mại, Fair Use, BUSL, SSPL); dò danh sách theo dõi `ui-vendor-watchlist.json` (Preline, magic-portfolio, React Bits, Tailwind Plus) trong `package.json`/ghi nguồn; cảnh báo chỉ đỏ khi `--strict` (`CMP-LIC-022`) |
| `python3 scripts/xt.py perf sample --out F [--runs N --warmup W] [--harness GLOB…] -- <lệnh>` | Chạy lệnh nhiều lần, ghi mẫu v2: thời gian tường + `head`/`dirty`/vân tay cây + hash bộ đo + môi trường (vòng tối ưu, `LOOP-OPT-*`) |
| `python3 scripts/xt.py perf compare TRƯỚC SAU [--base REF] [--exact] [--no-regress] [--json]` | So hai bộ mẫu bằng Mann-Whitney U + sàn nhiễu: `improved`/`regressed`/`neutral`/`insufficient` (exit 0 = `improved`); exit 2 khi mẫu không so được (lệch đơn vị/lệnh/bộ đo/nền tảng, baseline bẩn hoặc khác `--base`) |
| `python3 scripts/xt.py perf trial start/prepare/finish/status/abort/log` | Máy quản lý một lần thử tối ưu (ADR-0071; skill `/optimize` gọi): gốc = đầu nhánh mặc định do máy chủ báo (D-366), cấu hình `perf/trial.json` và `xt.py` lấy từ commit gốc (byte khác → `exec` bản gốc), sổ `.autopilot/perf-trials.jsonl`; `start` đòi cây sạch, giả thuyết + falsifier, exit 3 khi đường điểm nóng đã 3 lần không giữ hoặc hết `budget`; `prepare` dựng ba cây đo (`clone --shared`), chạy `setup` với môi trường allowlist, exit 2 khi đường phân giải ra ngoài cây đo; `finish` đo gốc/`start_head`/candidate xen kẽ ở ba cây dựng lại (môi trường mới mỗi lần chạy), quyết theo chỉ số chính + phụ + `equiv` + held-out (hạt giống mới mỗi lượt) + falsifier, giữ (exit 0) hoặc thu hồi vào stash (exit 1; 4 khi cây chưa về vân tay); `finish --resume` sau lượt chết: đo lại một lần khi cây = candidate đã đóng băng, không thì `incomplete` + thu hồi; pha `decided` làm nốt giữ/thu hồi; `finish --no-apply` quyết + ghi sổ, in lệnh thu hồi, không giữ/thu hồi; SIGTERM/SIGINT giữa lượt → dòng `interrupt`, exit 2; `abort` thu hồi đúng file vào stash (tính vào ba lần; exit 4 như trên); `status` pha + lệnh kế, `status --check` = Gate của task tối ưu: `HEAD^{tree}` = cây giữ gần nhất và cây sạch — đều trừ file sổ sách thường `docs/autopilot/PLAN*.md`, `DECISIONS*.md`, PERF-LOG, `PROGRESS.md` (D-371, thu hẹp ở D-372: symlink/dòng nhắc vùng sổ sách → `tampered`/1; squash-merge PR mở vòng mới thì nhận lần giữ của vòng trước khi cây không đổi và nhánh mặc định không đổi mã), lần giữ đạt `target` — chỉ số chính, cả held-out gộp khi khai (exit 0; 1 chưa đạt/commit lạ; 3 chưa đạt và hết `budget`/mọi đường cạn); `log` dựng khối PERF-LOG từ sổ |
| `python3 scripts/xt.py perf guard --base REF [--locked GLOB…] [--strict]` | Worktree (cả file chưa theo dõi) không được đụng/xoá bộ đo, test tương đương; báo dòng đáng ngờ (cache/memoize, `sleep`, đổi đồng hồ, soi stack) |
| `python3 scripts/xt.py audit plan [--blueprint F] [--status F] [--json]` | Dò stack → nhóm audit áp dụng/rút gọn/N/A kèm lý do, công cụ có/thiếu, bằng chứng blueprint trỏ file đã đổi sau khi ghi, nhóm cần quét lại theo `docs/ops/AUDIT-STATUS.md` |
| `python3 scripts/xt.py audit check STATUS [--strict]` | Kiểm sổ audit (schema phát hiện, SHA quét là tổ tiên HEAD và có trên nhánh chính như `progress-check`, chấp nhận rủi ro có chủ + hạn); `--strict` = Definition of Complete |
| `python3 scripts/xt.py stats` | Đếm file theo loại và mục theo mức |
| `python3 scripts/xt.py --version` · `--help` | Phiên bản khung (file `VERSION`) · ví dụ và mã thoát (0 ổn · 1 chưa đạt · 2 sai cách dùng · 3 lỗi GitHub/hết giờ · 126 guard cấm lệnh) |
| `python3 scripts/check-links.py` | Kiểm liên kết Markdown toàn repo |
| `scripts/dev-task.sh gate` | Cổng đầy đủ: chạy lệnh trong `xt.yaml` (build · typecheck · lint · test), CI chạy đúng lệnh này và là cổng đầy đủ; cục bộ trước cắt bản (ADR-0056) |
| `scripts/dev-task.sh gate-fast` | Cổng commit nhanh (hook chạy khi `xt.yaml` `commit_gate: fast`; vắng = `full` = `gate`): `format_check` · lint · typecheck · `test_fast` với `XT_CHANGED_FILES` (file đổi so với HEAD + file mới); `test_fast` trống hoặc không biết file đổi → `test`; không build, không ngưỡng coverage |
| `python3 scripts/xt.py test-select [FILE…] [--tests DIR] [--unittest]` | Test liên quan file đổi (đối số hoặc `XT_CHANGED_FILES`), chọn theo lớp: lớp nhắc tên file hoặc có glob khớp tên (`*.md`, `GO-NO-GO*.md`), lớp cùng file nhắc tên lớp đã chọn (lớp con, lớp dùng lớp phụ trợ); cả file khi chính file test, `test_<tên>.py`, import module đổi hoặc phần ngoài lớp khớp/nhắc lớp đã chọn; lọc ra 0 lớp → không lọc; file không ánh xạ được → cả suite; `--unittest` in id lớp (`tests.test_x.Lop`), module lỗi import → exit 1 |
| `python3 scripts/xt.py commit-gate` | In `fast`\|`full`: cổng trước commit theo `commit_gate` của `xt.yaml` (đọc như `doctor`; vắng/lạ → `full`) — hook `pre-bash-guard.sh` gọi |
| `scripts/dev-task.sh test-shard I N [DIR]` · `test-combine DIR` · `python3 scripts/xt.py test-shard-plan I N --weights FILE` | Chia test cho job CI song song (`test_list`/`test_unit`/`test_combine` của `xt.yaml`); có `test_weights` → chia theo trọng số qua `test-shard-plan` (id từ stdin; tham lam LPT: nặng trước, vào shard nhẹ nhất; id lạ lấy trung vị; JSON hỏng → exit 2), không khai → id thứ k vào shard k mod N |
| `scripts/dev-task.sh bootstrap` | Mốc 1/3 cài khung (T-4011): CPython ≥ 3.13 (dùng `uv python install` theo `.python-version` khi máy chưa có hoặc chỉ có bản tiền phát hành) và công cụ cổng từ `requirements-dev.txt` (ghim hash) vào `.venv`; từ chối `.venv` dưới sàn Python; in dòng `PATH` cho hook. Không chạm `setup` (chạy ứng dụng) hay G7 (production). Đã kiểm trên Linux. `XT_PYTHON` chọn trình thông dịch thử trước |
| `scripts/dev-task.sh test-mode` · `e2e-mode` · `e2e [I N]` | Task của CI mẫu dự án đích (D-115): `shard`/`whole` cho job `test`; `off`/`shard`/`whole` cho job `e2e`; `e2e_setup` rồi `e2e` với `XT_SHARD=I/N` (mặc định `1/1`) |
| `scripts/dev-task.sh test-weights` · `python3 scripts/xt.py test-weights --unit CMD --out FILE` | Đo lại file `test_weights` (id từ stdin, chạy lần lượt, giây làm tròn 0.1, JSON khoá sắp xếp; id đỏ → exit 1, không ghi). Chạy tay rồi commit; CI không chạy |

Biến môi trường (đều tuỳ chọn): `XT_FRAMEWORK` (thư mục khung, mặc định cạnh `scripts/`) · `XT_FRAMEWORK_LINK` (gốc liên kết
trong blueprint, mặc định `.xtemplates/framework`; ghép lại `BLUEPRINT.md` của chính repo khung: đặt `framework`, nếu không mục đã tick bị coi đổi chữ — AUD-HAR-113) · `XT_RECORD_TIMEOUT` (giây, mặc định 1800) · `XT_DEPLOY_TIMEOUT` (số giây cho mỗi bước của adapter dev, mặc định 1200, phạm vi 1–99999) · `XT_PYTHON` (trình thông dịch `dev-task.sh bootstrap` thử trước, mặc định `python3`) · `XT_CHANGED_TRACKED_ONLY=1` (hook cổng commit đặt khi guard khẳng định lệnh là `git commit` đứng một mình: `gate-fast` bỏ tệp chưa track; không đặt tay) · `XT_PROGRESS_BASE` (nhánh chính cho `progress-check` và `audit check`, mặc định `origin/HEAD` → `origin/main` → `origin/master`; rỗng = tắt) · `CLAUDE_PROJECT_DIR` (gốc dự án cho
`loop`; không đặt thì: bản cài `.xtemplates/scripts/xt.py` → cha của `.xtemplates`; nếu không, thư mục cha gần nhất có
`.autopilot`/`xt.yaml`/`.xtemplates`, rồi gần nhất có `.git` — thư mục cha là repo khác (vd `$HOME` dotfiles) sẽ thắng; không thấy thì cwd) · `CLAUDE_CONFIG_DIR` (thư mục cấu hình người dùng của Claude Code mà `doctor`/`loop init` đọc; mặc định `~/.claude` + `~/.claude.json`) · `XT_DEBUG=1` (in traceback khi lỗi) · `XT_GUARD_POLICY=strict` (hook hỏi người như trước ADR-0018; mặc định không hỏi) · `XT_FRAMEWORK_REPO` (repo GitHub để `doctor` so bản phát hành mới nhất, mặc định `www-donghanhcungban-org/X-Templates`) · `XT_STEWARD_UPDATE=off` (`pr steward` không tự cập nhật nhánh tụt base — workflow chạy bằng `GITHUB_TOKEN`) · `XT_CHANGED_FILES` (mỗi dòng một file đổi; `dev-task.sh gate-fast` đặt, `test-select` đọc để chọn lớp test liên quan; không đặt = chạy cả suite) · `XT_MIN_TESTS` (số lớp test tối thiểu `dev-task.sh test-shard` đòi, mặc định 1; liệt kê hỏng không được xanh) · `XT_JOBS` (số tiến trình pytest-xdist cho lệnh `test` tự dò của `dev-task.sh`: nguyên dương, trần 4×số nhân; `1` = `pytest -q` tuần tự; không đặt/rác = `auto`) · `XT_FRAMEWORK_PYTHON` (đường dẫn Python để `dev-task.sh` chạy CLI của khung, CI mẫu đặt tự động) · `XT_COV_DIR` (thư mục dữ liệu coverage `dev-task.sh test-shard`/`test-combine` dùng, đặt bởi chính script) · `XT_SHARD`, `XT_GATE_ALL_TESTS` (cổng test của `dev-task.sh`, tự đặt) · `XT_CI_WORKFLOW` (tên workflow CI khi khác `ci.yml`) · `XT_GUARD_PHASE=harden` (ép guard vào pha harden, ADR-0040) · `CLAUDE_CODE_SESSION_ID` (id phiên, do Claude Code đặt; chỉ đọc).

Kiểm tra trước khi đóng góp với CPython 3.13 trở lên (CI chính dùng 3.15.2) và công cụ ghim kèm hash trong `requirements-dev.txt`.

```bash
pip install --require-hashes -r requirements-dev.txt
scripts/dev-task.sh gate                 # build · typecheck · lint · test — CI chạy song song từng task, job quality tổng hợp
python3 -m unittest discover -s tests    # chỉ test (cổng test còn đòi coverage dòng + nhánh 100%, xem xt.yaml)
```

## Quyết định thiết kế

- [ADR-0001](docs/adr/0001-framework-as-id-library-with-machine-composition.md): khung là thư viện ID, máy ghép và máy kiểm "xong".
- [ADR-0002](docs/adr/0002-harness-stop-points-and-evidence-hooks.md): hook chặn hành động nguy hiểm, Stop hook đọc bằng chứng.
- [ADR-0003](docs/adr/0003-scale-s-floor-only.md): ở quy mô S chỉ sàn (baseline, hồ sơ, ngành) là MUST.
- [ADR-0004](docs/adr/0004-scale-m-module-must-cap.md): ở quy mô M mỗi module tối đa 4 MUST, phần vượt là `MUST@L`.
- [ADR-0005](docs/adr/0005-audit-with-machine-support.md): audit có máy đỡ — sổ máy đọc, `xt.py audit plan/check`.
- [ADR-0007](docs/adr/0007-rename-technical-identifiers-to-xtemplates.md): định danh kỹ thuật theo tên X-Templates
  (`.xtemplates/`, `xt.py`, `xt.yaml`, `XT_*`); `install.py` tự chuyển dự án đã cài bản ≤ 2.x. Thay ADR-0006.
- [ADR-0008](docs/adr/0008-main-session-self-approves-decisions.md): phiên chính tự duyệt điểm quyết định chuyên môn
  theo tiêu chí chất lượng cuối, ghi `D-NNN`; điểm dừng về hành động không tự duyệt (cơ chế sau: ADR-0018).
- [ADR-0009](docs/adr/0009-single-session-autopilot.md): autopilot chạy một phiên đến khi xong (compaction có checkpoint),
  việc cần người `loop defer` gom cuối phiên.
- [ADR-0010](docs/adr/0010-feedback-from-target-projects.md): phản hồi từ dự án đích về khung qua `FB-NNN` + Routine gộp
  → PR nháp, người duyệt trước khi công khai.
- [ADR-0011](docs/adr/0011-gate-fail-closed-in-autopilot.md): trong vòng autopilot, `lint`/`test` rỗng hoặc no-op làm cổng đỏ.
- [ADR-0012](docs/adr/0012-blueprint-by-scale-and-task-iteration-cap.md): `BLUEPRINT.md` chỉ chứa MUST theo quy mô,
  SHOULD/MAY ở `BLUEPRINT-BACKLOG.md`; trần vòng một phiên chỉ đếm task.
- [ADR-0013](docs/adr/0013-machine-decides-when-to-merge.md): `xt.py merge-check` quyết khi nào merge PR; tự merge chỉ
  bằng lệnh ghim head (mức tự chủ: ADR-0015/0024).
- [ADR-0015](docs/adr/0015-auto-merge-on-open-l3.md): mức `merge_autonomy: L3` (mặc định, chủ repo yêu cầu) — máy merge
  mọi làn trừ ngoại lệ cứng (chính sách review hiện hành xem ADR-0079); cơ chế auto-merge thay bởi ADR-0036 (merge ghim head).
- [ADR-0014](docs/adr/0014-pr-per-slice-and-machine-merge.md): mỗi lát code một PR; máy tự merge khi `merge-check` cho
  phép bằng lệnh ghim head (`gh pr merge`, REST `PUT …/merge` có `sha`, MCP `merge_pull_request` có `expectedHeadSha`).
- [ADR-0016](docs/adr/0016-l3-keeps-hard-exceptions.md): ở L3 PR chạm tiền/dữ liệu người dùng thật/auth/mật mã/bí mật
  vẫn người merge (`merge-check` trả `hard`, guard chặn merge) — tắt được bằng ADR-0020.
- [ADR-0017](docs/adr/0017-allow-all-bash-behind-fences.md): `permissions.allow` gồm `Bash` — mọi lệnh Bash không hỏi;
  hàng rào là `deny`/`ask` của settings và hook guard.
- [ADR-0018](docs/adr/0018-deny-dangerous-allow-rest.md): guard không hỏi người — lệnh nguy hiểm/không đảo ngược bị
  chặn, còn lại cho chạy; `XT_GUARD_POLICY=strict` giữ hành vi hỏi cũ.
- [ADR-0019](docs/adr/0019-hard-exceptions-denied-under-no-ask.md): dưới chính sách không hỏi, merge PR ngoại lệ cứng
  (`hard`) bị chặn — người merge (bật auto-merge bị chặn phẳng ở mọi PR — ADR-0036).
- [ADR-0020](docs/adr/0020-hard-exceptions-owner-opt-out.md): chủ dự án tắt được chốt người của ngoại lệ cứng
  (`xt.yaml` `merge_hard_exceptions: auto` đã commit ở nhánh đích; thiếu khoá = `human`; PR đổi khoá luôn người merge);
  repo khung `auto`; mẫu dự án đích `auto` từ 3.24.0 (chủ repo 2026-10-25, D-176; trước đó `human`).
- [ADR-0021](docs/adr/0021-merge-watch-after-opening-pr.md): mở PR xong chạy nền `xt.py merge-watch` (30 giây/lần, gọi lại
  `merge-check`) tới khi PR đã merge hoặc cần hành động.
- [ADR-0022](docs/adr/0022-production-grants-in-plan.md): duyệt kế hoạch = một lần người duyệt mục Ủy quyền production
  (`- grant:` trong PLAN.md, máy kiểm `xt.py grant-check`); PR đổi grant/khoá luôn người merge; hạn mức autopilot mặc định x2.
- [ADR-0023](docs/adr/0023-merge-gate-required-check.md): required check `merge-gate` (`pull_request_target`) đỏ khi
  `merge-check` báo `hard` mà PR đang bật auto-merge — bỏ bởi ADR-0036 (stub xanh tới khi chủ repo gỡ khỏi ruleset).
- [ADR-0024](docs/adr/0024-auto-merge-after-clean-review.md): merge theo làn — PR quan trọng (làn chuẩn) `reviewer` rà sạch
  mới merge, PR làn nhanh merge khi CI xanh — luôn bằng lệnh ghim head (cơ chế: ADR-0036).
- [ADR-0025](docs/adr/0025-merge-by-lane-state-machine-in-code.md): luật merge theo làn nằm trong code — `xt.py pr next`
  trả một hành động kế tiếp, `pr reviewed` ghi kết quả review ở đúng head.
- [ADR-0026](docs/adr/0026-autopilot-evidence-write-denied.md): ghi/xoá tay `.autopilot/` (bằng chứng, trạng thái vòng,
  sổ review) bị chặn, không chỉ hỏi.
- [ADR-0027](docs/adr/0027-pr-steward-on-github.md): workflow `pr-steward` trên GitHub merge ghim head PR đủ
  tiêu chuẩn khi CI xanh và không còn phiên agent (tắt auto-merge do người bật — ADR-0036); `pr reviewed` đăng kết quả review lên PR.
- [ADR-0028](docs/adr/0028-single-merge-eligibility.md): một điều kiện "được merge" (`merge_eligibility`) cho
  `merge-check`, `pr next`, guard và steward khi `merge_review: required` (ADR-0079).
- [ADR-0029](docs/adr/0029-two-executor-tiers-milestone-audit-release-check.md): hai tầng executor (`executor-deep`) có
  chuyển cấp sau 2 lần đỏ, mốc PLAN → audit delta, `pr reviewed --inconclusive`, `release-check` (G7 máy đọc).
- [ADR-0030](docs/adr/0030-essential-items-not-capped-at-m.md): mục `essential` không bị trần MUST ở M khi fact bật
  (`compose --feature`), thí điểm `08-backend/authn-authz.md`.
- [ADR-0031](docs/adr/0031-delivery-phase-build-harden.md): `delivery_phase: build|harden` — pha build merge PR làn chuẩn
  ngoài ngoại lệ cứng khi CI xanh, review ghi nợ; `release-check` đòi `harden` và hết nợ review trước G7.
- [ADR-0032](docs/adr/0032-merge-check-review-verdict.md): `merge-check` trả verdict `review` (exit 1, không gợi lệnh
  merge) khi CI/làn cho merge mà review ở head chưa hợp lệ — thay ADR-0028 §2.
- [ADR-0033](docs/adr/0033-build-phase-lean-autopilot.md): pha build tối giản autopilot — audit delta theo mốc gom về
  trước G7, reviewer chỉ khi `pr next` trả `review`, `PROGRESS.md` cập nhật theo lát.
- [ADR-0034](docs/adr/0034-target-ci-ruleset-minimal-max-parallel.md): CI, E2E và ruleset dự án đích tối thiểu khi triển
  khai ban đầu, song song tối đa — matrix tĩnh không job lập kế hoạch, job `e2e`, ruleset không strict (nay 2 check `quality`, `gitleaks` — ADR-0036); không CD.
- [ADR-0035](docs/adr/0035-merge-gate-workflow-run-check-run.md): `merge-gate` qua `workflow_run` + check-run REST — bỏ
  bởi ADR-0036, không triển khai.
- [ADR-0036](docs/adr/0036-pinned-merge-no-auto-merge-drop-merge-gate.md): máy không bao giờ bật auto-merge của GitHub
  (guard `deny`, mã `AUTO_MERGE_ENABLE`); mọi đường merge của máy (phiên qua `pr next`, steward `--apply`) ghim head sau
  `merge-check` = `merge` ở đúng head, CI chưa xong → `wait`; bỏ required check `merge-gate` (thay ADR-0023, ADR-0035).
- [ADR-0037](docs/adr/0037-reviewers-only-in-harden.md): reviewer chỉ ở pha `harden`; chuyển `harden` chỉ khi lên production (một chiều).
- [ADR-0038](docs/adr/0038-local-app-on-xt.md): app web cục bộ `xt.py app` chỉ đọc, không chạy lệnh.
- [ADR-0039](docs/adr/0039-minimal-target-ci-jobs.md): CI mẫu dự án đích 3 job: `gate` ∥ `e2e` → `quality`.
- [ADR-0040](docs/adr/0040-build-phase-local-actions-allowed.md): pha `build` guard cho chạy mọi hành động chỉ tác động trong dự án/thư mục tạm.
- [ADR-0041](docs/adr/0041-build-phase-minimal-gates.md): pha `build` không áp sàn Gate M/L, không `dev-task.sh gate` trước push (cổng commit vẫn chạy), không trần 150 dòng.
- [ADR-0042](docs/adr/0042-release-check-attack-and-perf.md): `release-check` chạy `attack`/`perf` của `xt.yaml` trước phát hành.
- [ADR-0043](docs/adr/0043-size-budget.md): trần byte đóng băng bề mặt 3.x (file hướng dẫn, thư mục mã/hook/mảng 11).
- [ADR-0044](docs/adr/0044-reviewer-higher-capability.md): reviewer năng lực cao hơn người viết (bậc model, hoặc cùng họ effort cao hơn) thay "khác họ".
- [ADR-0045](docs/adr/0045-split-by-context-measure-before-fold.md): tách agent con chỉ vì context; đổi kiến trúc agent qua eval so sánh; đo trước khi đổi mặc định giao việc.
- [ADR-0046](docs/adr/0046-autopilot-build-complete-harden.md): `/autopilot` = pha build, `done` không đòi hết MUST blueprint; `/complete` = pha harden (audit, nợ review, hoàn thiện, `release-check`, GO-NO-GO); sàn an toàn không đổi.
- [ADR-0047](docs/adr/0047-build-loop-until-audit-clean.md): pha build không chờ người — mẫu dự án đích `merge_hard_exceptions: auto`; `/autopilot` lặp đợt build → `/audit delta` → đợt kế tới khi hết việc và audit toàn diện sạch, rồi **đề xuất** `/complete` (không tự chạy); `loop init` đợt kế (sau `loop verify --all` trên cây có PLAN mới) không bị vòng `done` chặn và mang việc chờ người cùng ID; workflow gắn tag sau khi ứng viên trên `main` có kết quả GO và phê duyệt khớp nội dung.
- [ADR-0048](docs/adr/0048-optimize-skill-and-field-loop.md): `/optimize` chỉ cho ngân sách đang đỏ có số (`release-check` hàng `perf`, `docs/ops/FIELD-<ngày>.json` do người xuất — agent không cầm khoá production; giai đoạn sản phẩm 3 thêm mục tiêu chưa đỏ, `LOOP-OPT-017`); người xác nhận spec/UX/bảo mật **một lần** ở `GO-NO-GO.md`; bản chỉ tối ưu nghiệm thu delta; `LOOP-OPT-005` MUST@M.
- [ADR-0049](docs/adr/0049-workflow-in-fanout-skills.md): `/audit` và `/research` nhiều mục dùng tool Workflow khi người gõ trực tiếp và có tool (cùng luật nhánh subagent: agent chỉ đọc, lô ≤ 5, phiên chính gộp và quyết; gọi từ `/autopilot`/`/complete` → subagent); không bật `ultracode` mặc định.
- [ADR-0050](docs/adr/0050-raise-dir-size-caps.md): trần tổng byte thư mục (`scripts/`, `.claude/hooks/`, `framework/11-autonomous-loop/`) nâng thêm 1 MiB mỗi nhóm theo chủ repo; trần từng file nạp đầu phiên giữ nguyên.
- [ADR-0051](docs/adr/0051-split-session-attach-from-resume.md): tách "gắn phiên mới" khỏi "giải quyết việc chờ / mở block" — `loop attach`, `loop resolve`, `loop unblock`; `loop resume` giữ nghĩa cũ và in cảnh báo (D-201; lát 1 của nghiên cứu ba vòng, chưa triển khai).
- [ADR-0052](docs/adr/0052-loop-state-rev-progress-perf-v2-next-step.md): state có `rev`, chặn không-tiến-triển theo task, mẫu perf v2, `loop next-step` chỉ đọc — lát 0–2 của nghiên cứu ba vòng; `perf trial` hoãn sang ADR riêng (D-202, D-203; lát 0–1 ở 3.28.0, lát 2 đang làm).
- [ADR-0053](docs/adr/0053-review-round-budget-per-pr.md): ngân sách review mỗi PR — hai lượt chưa sạch rồi `pr next` trả `rethink`, thêm lượt qua `pr rethink --decision D-NNN`; review trước PR dùng cho đúng head (D-209; phần duyệt của PLAN-phase-gated-review). Quyết định 2 thay bởi ADR-0059.
- [ADR-0054](docs/adr/0054-fail-closed-unavailable-state-lock-and-guard-loader.md): không ghi state khi thiếu khoá, không thực thi khi guard lỗi nạp (fail-closed).
- [ADR-0055](docs/adr/0055-optional-install-policy-presets.md): preset chính sách cài đặt tuỳ chọn (`install.py --preset`).
- [ADR-0056](docs/adr/0056-delivery-speed-review-scope-ci-gate-ids.md): tốc độ giao hàng — lỗi có từ trước không chặn PR (sổ audit chặn phát hành), CI là cổng đầy đủ mọi pha, `loop decide` đánh số qua nhánh remote (D-221).
- [ADR-0057](docs/adr/0057-merged-review-covers-release-debt.md): `release-check` coi nợ review là đã phủ khi mọi commit chạm file là squash của PR có review sạch ở head (dấu `xt-review` trên GitHub) — bớt PR sổ chỉ để dời SHA sau squash-merge (D-222).
- [ADR-0058](docs/adr/0058-product-stages-machine-lock.md): ba giai đoạn sản phẩm MVP → hoàn thiện → tối ưu khoá bằng máy (`xt.py stage`, sổ `docs/autopilot/STAGE.json`); người duyệt mặc định (`stage approve`), ngoại lệ MVP theo ADR-0069; PLAN khai giai đoạn, `release-check` hàng `stage` (D-239).
- [ADR-0059](docs/adr/0059-review-twice-fix-once-debt.md) (§1–2 thay bởi ADR-0062): review 2 lần, sửa 1 lần — hết lượt thì `pr next` trả `debt`, phát hiện 🟠/🟢 còn lại ghi nợ ở sổ audit (`nợ-review: #N`, `pr debt`) rồi tiếp tục, 🔴 vẫn `pr rethink`; nợ trả cuối pha (`audit check --strict`) (luật chủ dự án 2026-10-30, D-257).
- [ADR-0060](docs/adr/0060-task-skills.md): sáu skill theo tác vụ phát triển (`/debug`, `/tdd`, `/ui-verify`, `/upgrade`, `/migrate-db`, `/incident`), tuỳ chọn cho dự án đích.
- [ADR-0061](docs/adr/0061-adaptive-agent-topology.md): cấu hình agent theo loại việc — mặc định một agent chính tự làm (`topo: self`), `review`/`parallel`/`audit` theo độ độc lập; đợt song song ≤ 4; `rethink` ≤ 1/PR; KPI thời gian trong `loop stats` (nhận định chủ dự án 2026-11-01).
- [ADR-0062](docs/adr/0062-review-once-risk-tiers.md): review 1 lần theo ba mức rủi ro — thấp = làn nhanh (CI + tự rà diff, máy merge ghim head), trung bình = một review logic/phạm vi/test, cao (ngoại lệ cứng kể cả đã miễn, schema/migration) = một review độc lập bắt buộc cả ở pha build; 🔴 sửa rồi `pr debt --fixed`, 🟠/🟢 ghi nợ rồi merge; `release-check` thêm migration/rollback/nghiệm thu (cấu hình chủ dự án 2026-11-01, D-295).
- [ADR-0063](docs/adr/0063-guard-canonical-subset.md): guard chỉ cho chạy tập con bash nó đọc chắc (backtick, nháy/ngoặc không đóng, `$IFS`, `~N`, brace bung `#`, mã động, đăng dấu review…) — ngoài tập con thì chặn (`BUDGET`) thay vì vá từng ca lách (D-299).
- [ADR-0064](docs/adr/0064-multi-provider-harness.md) (D-303): harness đa nhà cung cấp — một lõi chính sách trung lập, adapter mỏng theo công cụ (Codex, Gemini CLI, Cursor, Copilot CLI, Grok Build, OpenCode), sàn chung bằng git hook, vòng lặp ngoài `loop run --agent`, sandbox kiểm bằng `doctor`; nghiên cứu `research/2026-11-02-multi-provider-harness.md`.
- [ADR-0065](docs/adr/0065-guard-allowlist-dynamic-expansion.md) (D-322): guard xét mở rộng động theo danh sách trắng — từ lệnh dựng lúc chạy, tách/gán theo tên động (`IFS`), heredoc đọc lại, dữ liệu thành mã (`mapfile -C`, `${x@P}`) → `BUDGET`; không suy cấu trúc lệnh để miễn.
- [ADR-0066](docs/adr/0066-guard-written-file-reuse.md) (D-327): tệp do chính lệnh ghi mà tên được nhắc lại ở chỗ khác của lệnh (trừ lệnh chỉ đọc trong danh sách trắng) → `BUDGET` — không liệt kê trình chạy (AUD-SEC-406).
- [ADR-0067](docs/adr/0067-guard-static-limit-layered-defense.md) (D-331/D-332): tên tệp/mô-đun dựng lúc chạy trong lệnh tự ghi tệp — giới hạn phân tích tĩnh, chấp nhận có hạn 2027-01-21 (thay một phần ADR-0065); dạng nguyên văn vẫn phải chặn.
- [ADR-0068](docs/adr/0068-software-factory-direction.md) (D-353): định hướng xưởng phần mềm — lõi hiện có + gói sản phẩm có phiên bản (`framework/templates/packs/<stack>/`, stack hotel-manager) + hợp đồng bằng chứng/phát hành có kiểu (evidence v3 thêm trường, `release-check` thêm `promotion`) + registry file; năm lát A–E, mỗi lát một PLAN/PR riêng.
- [ADR-0069](docs/adr/0069-agent-stage-approval.md) (D-352): agent tự nghiệm thu giai đoạn sản phẩm khi `xt.yaml` (cây và bản đã commit ở nhánh chính) khai `stage_approval: agent` — duyệt bản trình còn nguyên, `next-step` trả `stage-approve`; `init --adopt`, dạng mờ vẫn chỉ người (thay một phần ADR-0058).
- [ADR-0070](docs/adr/0070-archive-repo-history.md) (D-354): lịch sử của chính repo khung (PLAN đã đóng, báo cáo audit, GO-NO-GO và ghi chép đo cũ) vào [`docs/archive/`](docs/archive/README.md) — `framework/` giữ nguyên (ID "Ngừng dùng", Nguồn + ngày); số task không tái sử dụng (`xt.py` quét cả kho); `.ignore` để tìm kiếm mặc định bỏ qua kho.
- [ADR-0071](docs/adr/0071-perf-trial.md) (D-356, D-360, D-366, D-368, D-370, D-371, D-372): `perf trial` — máy quản lý trọn một lần thử tối ưu: baseline = đầu nhánh mặc định do máy chủ báo, đo xen kẽ base/`start_head`/candidate ở cây dựng lại từ tree object, cấu hình và công cụ chấm từ commit gốc, held-out lúc finish, falsifier ghi trước, giữ/thu hồi tự động, sổ bền `.autopilot/` dựng PERF-LOG; lát 3 của ADR-0052, triển khai T-3700…T-3707.
- [ADR-0072](docs/adr/0072-review-dir-caps-after-2x.md) (D-373): `.claude/hooks/` vượt 2× mốc 2026-10-26 do bản vá guard #433–#442 — giữ trần `DIR_CAPS`, mốc mới 2026-11-05 cho hooks, cổng máy `SIZE_MARKS` (mỗi nhóm ≤ 2× mốc gần nhất); T-3709 đo chi phí compile `guard.py`.
- [ADR-0073](docs/adr/0073-own-permissions-hook-form.md) (D-383): `harness_permissions: own` giữ dạng lệnh hook sẵn có của dự án — có lệnh khung dạng `${CLAUDE_PROJECT_DIR}` thì giữ tuyệt đối, không có thì tương đối (AUD-HAR-301).
- [ADR-0074](docs/adr/0074-agent-release-signoff.md) (D-401): chủ repo cho agent ký §5 GO-NO-GO — khoá `release_signoff: agent` (cây + nhánh chính, chỉ người đổi), `xt.py release-sign` chỉ ký khi `release-check` không FAIL và chỉ còn chữ ký, ô tên ghi `agent`; mẫu dự án đích để trống.
- [ADR-0075](docs/adr/0075-end-to-end-factory.md) (D-419): xưởng đầu-cuối theo chủ dự án 2026-11-11 — ý tưởng tới bản dev có receipt không hỏi người; song song khi `files:` không giao và diff nằm trong `files:`; agent ký/duyệt ở mọi quy mô qua khoá chỉ người bật; việc người gom một checklist sau bản dev; cơ chế chất lượng bù merge trước phần nới. Việc: [PLAN-factory-e2e](docs/autopilot/PLAN-factory-e2e.md); đặc tả: `docs/specs/SPEC-factory-*.md` (D-422…D-424).

Nghiên cứu nền ngày 2026-10-13 ở [`research/`](research/): phân tích khung cũ, trích xuất catalog `www-donghanhcungban-org/stored`,
AI agent và giao thức, cơ chế Claude Code. Khung cũ khôi phục được bằng `git archive 1b80fe4`.

Định hướng [xưởng phần mềm từ 34 mục stored](research/2026-11-04-software-factory-direction.md) (4/11/2026, chấp nhận qua
[ADR-0068](docs/adr/0068-software-factory-direction.md), D-353): gói sản phẩm có phiên bản, bằng chứng phát hành có kiểu, lộ trình
nghiệm thu A–E; lát A–E đã làm, gộp một PR (#451) theo quyết định chủ dự án (D-358/D-359) thay vì mỗi lát một PR.

## Ủng hộ và liên hệ

X-Templates miễn phí và sẽ luôn mở mã. Nếu khung giúp bạn tiết kiệm thời gian hoặc tránh được sự cố, bạn có thể ủng
hộ để tác giả duy trì và cập nhật nội dung (chuẩn, luật, phiên bản công cụ thay đổi liên tục):

<img src="docs/assets/donate-vietqr-techcombank.png" alt="Mã VietQR ủng hộ: Techcombank, số tài khoản 890977819110" width="260">

- Quét mã VietQR bằng ứng dụng ngân hàng bất kỳ, hoặc chuyển khoản **Techcombank — số tài khoản `890977819110`**.
- Liên hệ, góp ý, hợp tác: điện thoại / Zalo **[+84 977 819 110](https://zalo.me/0977819110)** ·
  email **admin@donghanhcungban.org**. Lỗi và đề xuất tính năng xin mở [issue](https://github.com/www-donghanhcungban-org/X-Templates/issues).
- **Hỗ trợ triển khai:** tác giả hỗ trợ cài đặt và áp dụng X-Templates cho dự án của bạn — **trực tiếp tại TP. Hồ Chí
  Minh** hoặc **online** ở bất kỳ đâu. Liên hệ qua điện thoại/Zalo hoặc email ở trên để trao đổi nhu cầu.

Ủng hộ là tự nguyện, không kèm quyền lợi riêng; hỗ trợ triển khai thoả thuận riêng theo từng dự án. Báo lỗ hổng bảo
mật theo [`SECURITY.md`](SECURITY.md).

## Đóng góp

Xem [`CONTRIBUTING.md`](CONTRIBUTING.md) và [`framework/00-method/conventions.md`](framework/00-method/conventions.md).
Bản đề xuất [khắc phục và nâng cấp tự động hóa ngày 2026-10-19](docs/ops/REMEDIATION-PLAN-2026-10-19.md)
gồm tái hiện, nghiên cứu nguồn sống, thang tự chủ theo loại PR, tiêu chí nghiệm thu và kế hoạch máy đọc
[`PLAN-3.9-automation.md`](docs/archive/autopilot/PLAN-3.9-automation.md) cho đợt sau 3.8.0.
Vận hành: [runbook `pr-steward`](docs/ops/RUNBOOK-PR-STEWARD.md) · [phụ thuộc và license](docs/ops/DEPENDENCIES.md).
Báo lỗ hổng: [`SECURITY.md`](SECURITY.md). Giấy phép: [MIT](LICENSE) cho toàn repo (mã và tài liệu), trừ thành phần
bên thứ ba và nhãn hiệu ghi ở [`NOTICE`](NOTICE); X-Templates không liên kết với các tổ chức có sản phẩm được nhắc tên.
