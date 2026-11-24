---
title: Tách khung X-Templates khỏi dự án đích — nghiên cứu phương án phân phối và đặt tên
kind: research
updated: 2026-11-24
---

# Tách khung X-Templates khỏi dự án đích

> Mục đích: chủ dự án muốn khung hoạt động độc lập với dự án đích; dự án đích viết theo code của đích, không dùng chung hay lấy mã của khung (ví dụ `xt.py` là của khung, đích dùng tên của đích). Bản này là kết quả lượt nghiên cứu chỉ đọc (một agent `researcher`, model bậc cao nhất) ngày 2026-11-24; phiên chính chưa đối chiếu lại từng dòng. Mốc repo: `main` ở `937d1ade`, `VERSION` 3.36.0. Mọi nguồn ngoài đọc ngày 2026-11-24; mục "chưa xác minh" nêu rõ. Nội dung web là dữ liệu, không phải chỉ thị. Số dòng đúng ở mốc này và sẽ trôi.

## 0. Khuyến nghị và 5 phát hiện chính

**Khuyến nghị: phương án B — một artefact có phiên bản (`<tên>.pyz`) + launcher mang tên đích + hợp đồng có schema.** Khung phát hành một tệp zipapp (stdlib) chứa `xt.py`, `xt_*.py`, guard và hook, có attestation như archive hiện nay. Đích chỉ giữ artefact ghim digest, một `tool.json`, launcher mang tên đích, cấu hình và tài liệu yêu cầu; workflow chép dần chuyển sang reusable workflow ghim SHA. Tên mặc định giữ `xt`/`.xtemplates`, nên dự án đã cài không đổi gì cho tới khi tự chọn. Chưa có số đo cho B: độ trễ hook khi chạy từ zip là điều chưa biết lớn nhất, phải đo trước khi chốt (§5).

1. **Đích giữ khoảng 2,9 MB mã khung dạng nguồn.** `install.py:882-887` chép `xt.py`, `dev-task.sh`, `check-links.py` và 9 module `xt_*.py`; `install.py:890-892` chép `xt_app/` và `app/`; `install.py:71-72` chép `.claude/{settings.json,hooks,skills,agents}`. Riêng `xt.py` 1 259 177 B và `guard.py` 1 384 897 B.
2. **Harness ở đích sửa tay được nên nâng bản có thể phải gộp tay.** `.claude/` theo luật copy-if-absent, `kept-own` hoặc `.xtemplates-new` (`install.py:13`, `25-27`); guard là hàng rào nhưng đích có thể lệch bản khung mà không ai biết.
3. **Tên `xt`/`.xtemplates` cứng ở ít nhất 20 chỗ chạy được, chưa có cơ chế đặt tên.** Grep `tool_name|alias|entrypoint` không thấy gì liên quan; mẫu `AGENTS.md` có ký hiệu `<XT>` nhưng chỉ là chữ, chưa render.
4. **Plugin của host không thay được guard chép trong repo.** Tài liệu Claude Code (qua tóm tắt tìm kiếm, mức thứ cấp) nói phiên cloud không thêm marketplace mà repo khai ở `extraKnownMarketplaces`; autopilot của khung chạy phiên cloud nên guard phân phối bằng plugin sẽ vắng ở đó. Khớp kết luận cũ ở `research/2026-10-13-stored-catalog-extraction.md:181`.
5. **Chưa có ADR nào quyết `xt.pyz`.** `PROGRESS.md` và `docs/adr/0038-local-app-on-xt.md:7` ghi "`xt.pyz` (ADR-0010)", nhưng ADR-0010 là "Phản hồi từ dự án đích" và không có chữ `pyz`/`zipapp`. Hai con trỏ sai cần đính chính.

Thêm: `docs/ops/registry.json` có 7 sản phẩm (không phải 5): năm cái ở `core` 3.34.0, X-Scanner ở 3.29.0, một mục ở 2.0.0 (dòng 81, trước đợt đổi tên ADR-0007). Đích đã lệch 3 thế hệ.

## 1. Bản đồ ghép nối

Phân loại: (a) chỉ của khung · (b) hợp đồng công khai nên giữ ổn định · (c) mã sao chép nên bỏ · (d) tên/đường dẫn nên cho đích tự đặt.

| # | Chỗ ghép | Tệp:dòng | Chủ | Đích sửa được? | Khi khung nâng bản | Loại |
|---|---|---|---|---|---|---|
| 1 | `.xtemplates/scripts/*.py`, `dev-task.sh`, `xt_app/`, `app/` | `install.py:860-903` | khung | không | đè nguyên; diff PR hàng chục nghìn dòng | c |
| 2 | `.claude/hooks/guard.py` và 12 hook `.sh` | `install.py:71-72`, `999-1016` | khung, đích sửa được | có | `.xtemplates-new`, gộp tay; guard có thể lệch | c |
| 3 | `.claude/skills/*` (17), `agents/*` (6) | `install.py:72` | khung | có | như #2; 31 chỗ nhắc `xt.py`, 20 chỗ nhắc `.xtemplates` | c + d |
| 4 | `.claude/settings.json` (lệnh hook, permissions) | `install.py:450-675`, `.claude/settings.json:45-117` | chung | có | gộp JSON giữ định dạng; rule theo manifest | b |
| 5 | `.xtemplates/framework/**` (267 tệp, 3,14 MB) và `research/` | `install.py:864-868` | khung | không | đè; BLUEPRINT liên kết tới đây (`xt.py:854-855`) | b (dữ liệu, không phải mã) |
| 6 | Tên thư mục `.xtemplates` | `xt.py:1306`, `1320`, `2444`, `3716-3720`, `5960`, `18948`; `dev-task.sh:59-61`; `guard.py:130`, `303`, `10471`, `11562`; `_lib.sh:9`; `pre-bash-guard.sh:58`, `147`, `162-173`; `session-start.sh:94`; `auto-format.sh:12`; `git-hooks/pre-commit:8`, `pre-push:7` | khung | không | đổi tên là đổi vỡ (ADR-0007 từng làm) | d |
| 7 | Lệnh `python3 .xtemplates/scripts/xt.py …` | `xt.py:3716`, `10461`; `templates/AGENTS.md` (`<XT>`); `ci.yml:63-114`; `xt-upgrade.yml:31`, `48`; `xt-field.yml:33`, `70`; `pr-steward.yml:99-100`; `release-tag.yml:87-88` | khung | chỉ khi sửa tay tệp chép | workflow lệch → `.xtemplates-new` | d |
| 8 | Adapter host khác gọi `xt_adapter.py` | `templates/harness/*.json|ts`; `install.py:1374` | khung | có | sinh lại, hash ở `codex_files` | c + d |
| 9 | Workflow chép: `ci`, `secret-scan`, `pr-title`, `merge-gate`, `pr-steward`, `release-tag`, `xt-field`, `xt-upgrade`; ruleset; dependabot | `install.py:97-111` | khung, đích sửa | có | copy-if-absent theo hash | c → reusable |
| 10 | `xt.yaml`: tên tệp và bộ khoá | `templates/xt.yaml`; `dev-task.sh:64`; `xt.py:5308`, `7029`, `14884` | đích (giá trị), khung (lược đồ) | có | khoá mới nối dạng chú thích (`install.py:2141`) | khoá: b · tên tệp: d |
| 11 | Biến `XT_*` (~60 tên), secret `XT_STEWARD_TOKEN`, `XT_RELEASE_TOKEN`, `XT_FIELD_READ_TOKEN`, biến repo `XT_REVIEW_IDENTITY`, `XT_CI_WORKFLOW` | grep `scripts`, `.claude`, `templates`, `.github` | khung đặt, đích cấu hình | giá trị | đổi tên phải sửa secret từng repo | b (tiền tố: d, làm sau) |
| 12 | Chuỗi nhận diện: nhánh `chore/xt-upgrade`, tiêu đề `chore(xt): nâng khung …`, dấu `xt-review v2`, `# xtemplates-git-hook v1`, đuôi `.xtemplates-new`, `docs/xtemplates-feedback/` | `xt_distribution.py:25-28`; CHANGELOG 3.36 (T-4014); `git-hooks/*:2`; ADR-0010 | khung | không | steward và guard so chuỗi | b (dấu review) · d (còn lại) |
| 13 | `.xtemplates/manifest.json`, `VERSION`, `harness.sha256.json` | `install.py:224-225`, `1023` (`schema: 1`) | khung | không | `upgrade`/`doctor` đọc | b |
| 14 | `.autopilot/`, `docs/autopilot/{PLAN,STAGE.json}`, `PROGRESS.md`, `BLUEPRINT.md` | `xt.py:1306`, `13202`, `3371` | đích (nội dung), khung (định dạng) | qua lệnh; guard cấm ghi tay | định dạng có `schema` | b (tên đã trung tính) |
| 15 | ID checklist `LOOP-*`, `WF-*`, `XC-*` | `conventions.md:51`, `102`, `139` | khung | không | ổn định, không tái dùng | b (không đổi) |
| 16 | `release-check --json` schema 4, biên nhận promotion, DEPLOYS, sổ lát | `xt.py:14764`, `15615`; `xt_release_ops.py:218` | khung | không | số schema tăng theo CHANGELOG | b |
| 17 | `install.py`, `xt_guard_profile.py`, `xt_derived.py`, `tests/`, `.github/` của khung | `scripts/AGENTS.md` | khung | — | không sang đích | a |
| 18 | `CANONICAL = "www-donghanhcungban-org/X-Templates"` | `xt_distribution.py:22` | khung | qua `source.repo` trong manifest | — | a |

Đích **không import** mã khung trong mã ứng dụng (grep `import xt` ở `templates/packs` chỉ ra lệnh gọi trong script/workflow của gói `web-api-ts`). Ghép nối hiện tại là gọi tiến trình, đường dẫn và tệp chép, nên tách được mà không đụng mã nghiệp vụ của đích.

## 2. Công nghệ và thực hành (đọc 2026-11-24)

| Mục | Giá trị | URL | Mức bằng chứng |
|---|---|---|---|
| `zipapp` (stdlib) | Tài liệu cho Python 3.15.2; `python -m zipapp app -p "/usr/bin/env python3" -c`; gói có C extension không chạy từ zip (khung chỉ stdlib nên không vướng); trang không nói gì về tái lập bytes | https://docs.python.org/3/library/zipapp.html | fetch trực tiếp; độ trễ chưa đo |
| uv | 0.13.9, `MIT OR Apache-2.0`, cần Python ≥ 3.8 | https://pypi.org/pypi/uv/json | fetch trực tiếp (ngày phát hành không đọc được) |
| `uvx` ghim nguồn git | `uvx --from git+https://…@<commit> <lệnh>`; `lệnh@<phiên bản>` chỉ cho phiên bản chính xác; môi trường tạm, cô lập | https://docs.astral.sh/uv/guides/tools/ | fetch trực tiếp |
| Tên PyPI `xtemplates` | HTTP 404, chưa ai đăng ký | https://pypi.org/pypi/xtemplates/json | fetch trực tiếp |
| Artifact attestations | Tự nó đạt SLSA v1.0 Build L2; build trong reusable workflow cô lập có thể đạt L3; repo public dùng Sigstore public-good | https://docs.github.com/en/actions/concepts/security/artifact-attestations | fetch trực tiếp |
| `gh attestation verify` | Bắt buộc `--repo` hoặc `--owner`; có `--signer-workflow`, `--source-ref`, `--source-digest`; `--bundle` kiểm offline | https://cli.github.com/manual/gh_attestation_verify | fetch trực tiếp |
| Immutable releases | Tag không dời được, asset không sửa/xoá được; tự sinh release attestation | https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/immutable-releases | fetch trực tiếp (GA: chưa xác minh) |
| SLSA | v1.2 "Approved"; có Build Track và Source Track | https://slsa.dev/spec/ | fetch trực tiếp |
| Reusable workflow | `{owner}/{repo}/.github/workflows/{file}@{ref}`, SHA là "safest option"; tối đa 10 tầng; quyền `GITHUB_TOKEN` chỉ giữ hoặc giảm; `secrets: inherit` chỉ trong cùng org/enterprise và chỉ tới workflow gọi trực tiếp | https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows | fetch trực tiếp |
| Claude Code plugin: thành phần | `skills/`, `agents/`, `hooks/hooks.json`, `.mcp.json`, `bin/`; hook gọi `"${CLAUDE_PLUGIN_ROOT}"/…`; `bin/` vào PATH của Bash tool; claude.ai và Cowork không cài plugin có `bin/`; mọi thành phần mang tiền tố `<plugin>:` | https://code.claude.com/docs/en/plugins-reference | fetch trực tiếp |
| Claude Code plugin: ghim nguồn | Nguồn `github`/`url`/`git-subdir` có `ref` + `sha` (40 ký tự); `archive` có `sha256`; `npm` có; **không có nguồn pip/PyPI**; marketplace ghim SHA cần Claude Code ≥ 2.1.324 | https://code.claude.com/docs/en/plugins/marketplace-reference.md | fetch trực tiếp |
| Plugin trong phiên cloud | Phiên cloud không thêm marketplace repo khai ở `extraKnownMarketplaces`; môi trường Anthropic-hosted chỉ nhận server-managed settings | https://code.claude.com/docs/en/plugins/loading | **thứ cấp** (tóm tắt tìm kiếm) |
| Phiên cloud nạp `.claude/` của repo | Subagent trong `.claude/agents/` và `.claude/settings.json` của repo được nạp | https://code.claude.com/docs/en/claude-code-on-the-web | fetch trực tiếp |
| Agent Skills spec | `name` ≤ 64 ký tự, chữ thường và gạch nối, trùng tên thư mục; `description` ≤ 1024; tuỳ chọn `license`, `compatibility`, `metadata`, `allowed-tools` (thử nghiệm) | https://agentskills.io/specification | fetch trực tiếp |
| copier | 9.19.1, MIT, Python ≥ 3.10; `copier update` cần `.copier-answers.yml`, template có tag git; xung đột ghi marker inline hoặc `.rej` | https://pypi.org/pypi/copier/json · https://copier.readthedocs.io/en/stable/updating/ | fetch trực tiếp |
| Renovate regex manager | Bắt được `github-tags`/`github-releases` trong tệp bất kỳ; có nhóm `currentDigest` | https://docs.renovatebot.com/modules/manager/regex/ | fetch trực tiếp (luồng cập nhật digest: chưa xác minh) |
| Plugin Codex, Gemini CLI, Cursor | Codex: `codex plugin marketplace add`; Gemini: `gemini-extension.json` + `hooks/hooks.json`; Cursor: `.cursor-plugin/plugin.json` | developers.openai.com/plugins/build/plugins · geminicli.com/docs/extensions/reference/ · cursor.com/docs/plugins | **thứ cấp** (kết quả tìm kiếm) |

Áp dụng cho khung stdlib-only, CPython ≥ 3.13:

- **zipapp**: hợp nhất. Không thêm phụ thuộc, không cần registry hay tài khoản, đúng "mặc định tự host" của AGENTS §4.
- **PyPI + `uvx`/`pipx run`**: hợp về kỹ thuật, nhưng đòi `uv`/`pipx` và mạng ở mọi máy, CI và phiên cloud; guard fail-closed (ADR-0054) chặn mọi lệnh khi tải lỗi. Chỉ nên là kênh phụ.
- **Binary độc lập** (PyInstaller, Nuitka…): không tra phiên bản; build theo nền tảng và chuỗi build ngoài stdlib. Loại.
- **Plugin host**: không dùng cho guard (phát hiện 4); tên skill thành `<plugin>:autopilot`, lệch `/autopilot` trong toàn bộ tài liệu. Có thể xét lại cho skill tuỳ chọn.
- **copier/cruft**: `install.py` đã có cơ chế ba trạng thái theo hash bằng stdlib; thêm copier là thêm phụ thuộc cho cùng một việc.
- **submodule/subtree**: submodule chưa init thì guard vắng; subtree vẫn là chép mã. Loại.
- **Renovate/Dependabot**: `xt.py upgrade` đã làm nhiều hơn (attestation, sóng canary/soak, bản thu hồi). Hữu ích để bump SHA của reusable workflow.

## 3. Phương án

**A. Giữ nguyên + vá nhỏ.** Mã vẫn chép. `install.py` sinh launcher do đích sở hữu và render `<XT>` trong skill/AGENTS; thêm bộ phân giải tên dùng chung. Thay đổi khoảng 20 chỗ ở §1 #6-7 qua một hàm; không tác động tới đích và ADR; chi phí thấp; lùi bằng revert một PR. Không đạt "đích không chứa mã khung".

**B. Artefact `.pyz` ghim digest + launcher + hợp đồng (khuyến nghị).** Chi tiết §4. Thay đổi: `release-tag.yml` dựng và attest thêm `.pyz`; `install.py` thêm `--layout artifact`; hook `.sh` gộp thành lệnh `hook <sự-kiện>` trong artefact; guard và `xt_adapter.py` nạp từ artefact. Không tác động tới đích cho tới khi chọn layout mới; canary một dự án trước (`upgrade_wave` đã có). ADR liên quan: ADR-0007 giữ tên mặc định và thêm khả năng đặt tên; ADR-0090/0093 (tách module, sibling loader) phải áp trong zip; ADR-0054 cần định nghĩa "artefact hỏng hoặc lệch digest = fail-closed"; ADR-0095 thêm thư mục công cụ vào lớp tác động tức thì; ADR-0082 đổi lệnh adapter. Chi phí trung bình-cao (6-7 PR). Rủi ro: độ trễ hook; đích mất khả năng sửa tay guard và cần điểm mở rộng thay thế. Đường lùi: cài lại `--layout tree`. Hợp ràng buộc: stdlib-only, 3.13 (zip chứa nguồn `.py`, không pyc theo phiên bản), fail-closed mạnh hơn vì kiểm được digest, ID không đổi.

**C. Gói + trình chạy (`uvx --from git+…@<sha>` hoặc wheel ở Release).** Đích chỉ có cấu hình và lock. Thêm `pyproject.toml` và entry point; hook gọi `uvx`. Mọi máy, CI và phiên cloud phải có `uv` và mạng lần đầu; guard không tải được thì chặn toàn bộ; cache ngoài repo nên khó tái lập; đăng PyPI cần tài khoản của chủ dự án. Sạch nhất về "không mã trong đích" nhưng kém nhất ở tiêu chí đúng và an toàn.

**D. Plugin host + marketplace ghim SHA.** Skill/agent/hook ở plugin, đích khai `enabledPlugins`. Guard vắng ở phiên cloud (thứ cấp); tên skill đổi; phải đóng gói riêng cho 5-6 host. Loại cho hàng rào.

**E. Reusable workflow ghim SHA.** Thay workflow chép (#9); là một pha của B, không thay được B. Quyền không nâng được qua chuỗi gọi; `secrets: inherit` chỉ cùng org. `pr-steward` hiện chạy `xt.py` từ nhánh mặc định của đích (`pr-steward.yml:99-100`); mô hình mới chạy mã khung ở SHA ghim, cần review bảo mật riêng.

Chấm theo AGENTS §4 (thang 1-5; tiêu chí trên thắng dưới):

| Tiêu chí | A | B | C | D |
|---|---|---|---|---|
| 1. Đúng và an toàn | 4 | 5 | 2 | 1 |
| 2. Giữ đường lùi | 5 | 4 | 4 | 3 |
| 3. Bền, đơn giản, theo chuẩn, test được | 3 | 4 | 4 | 2 |
| 4. Trải nghiệm cuối (đạt yêu cầu chủ dự án) | 2 | 5 | 4 | 3 |
| 5. Tốc độ/chi phí | 5 | 3 | 3 | 2 |

B thắng ở tiêu chí 1 và 4. A là pha đầu của B nên chọn B không mất gì của A.

## 4. Kiến trúc đích, hợp đồng, di trú

```
Repo khung (X-Templates)                      Dự án đích (tên riêng, ví dụ "acme")
  scripts/*.py, .claude/hooks/*  --build-->   .acme/acme.pyz        artefact, chỉ đọc, ghim sha256
  release-tag.yml: zip tất định                .acme/tool.json       {name, config, env_prefix, contract}
    + attest + Release bất biến                .acme/lock.json       {version, sha256, repo, tag, verified}
  contracts/*.schema.json                      .acme/framework/**    thư viện yêu cầu (dữ liệu, chỉ đọc)
  .github/workflows/target-*.yml               ./acme                launcher sh 3-5 dòng, của đích
    (reusable)                                 acme.yaml             cấu hình, của đích
                                               .claude/settings.json hook: python3 .acme/acme.pyz hook <event>
                                               .claude/skills, agents  sinh từ artefact, đã render tên
                                               .github/workflows/*   caller mỏng: uses: …@<sha>
                                               .autopilot/, BLUEPRINT.md, PROGRESS.md   của đích
```

Công cụ tự suy gốc từ vị trí artefact rồi đọc `tool.json` cạnh nó, nên gốc đích không cần tên cố định nào của khung. Mặc định `name: xt`, thư mục `.xtemplates`, `xt.yaml`, `XT_`.

**Hợp đồng công khai tối thiểu** (SemVer riêng, số `contract: N` trong `tool.json`):
1. CLI mà hook/CI/skill gọi, kèm mã thoát: `doctor`, `ci-check`, `floor`, `commit-gate`, `loop …`, `pr next|steward|reviewed`, `merge-watch`, `release-check --json`, `upgrade check|open-pr` (0/10/11, `xt-upgrade.yml:31-36`), `stage`, `perf field-*`, `feedback`, `hook <event>`.
2. Bộ khoá cấu hình (`templates/xt.yaml`).
3. Định dạng có `schema`: manifest/lock, STAGE, release-check (4), sổ lát, DEPLOYS, biên nhận promotion.
4. Giao thức hook: stdin JSON của host → quyết định.
5. ID yêu cầu và dấu `xt-review vN`.

Mọi thứ khác (cấu trúc module, tên hàm, bố cục trong zip) là riêng của khung.

**Đặt tên riêng:** `install.py --tool-name acme` hoặc lệnh `rename` ghi `tool.json`, launcher, tên tệp cấu hình, và render lại skill/AGENTS/workflow caller. Tiền tố biến đọc `ACME_X` trước, rơi về `XT_X`; secret GitHub đổi sau cùng. Không đổi: ID yêu cầu, dấu review, `.autopilot/`.

**Di trú, mỗi pha một PR, đảo ngược được:**
- **P0** ADR và bảng kê hợp đồng; test đóng băng bề mặt hiện tại. Không đổi hành vi.
- **P1** Một bộ phân giải (gốc, cấu hình, tên) thay 20 chỗ cứng ở `xt.py`, `dev-task.sh`, hook, guard, git hook. Mặc định y nguyên.
- **P2** Launcher và render `<XT>`; `--tool-name` (vẫn layout cây).
- **P3** `release-tag.yml` dựng `.pyz` tất định (tự viết bằng `zipfile`: sắp tên, mtime cố định) và attest; `release-verify` kiểm thêm. Đích chưa đổi.
- **P4** `install.py --layout artifact`; hook thành `hook <event>`; canary một đích. Lùi: `--layout tree`.
- **P5** Reusable workflow cho `ci`, `pr-steward`, `upgrade`, `field`; caller ghim SHA.
- **P6** Bản MAJOR kế: artefact thành mặc định, layout cây giữ thêm một MAJOR; di trú tự động như `migrate_legacy` (`install.py:2341`).

**Tiêu chí nghiệm thu đo được:**
- Layout artefact: tìm tệp `*.py` và `*.sh` của khung trong đích ra 0; chỉ còn launcher.
- Cài với `--tool-name acme`: grep `xtemplates|xt\.py|xt\.yaml` trong đích chỉ còn đúng 1 dòng ghi chú nguồn (WF-DOC-021).
- Đổi tên không đổi kết quả: `release-check --json`, `doctor`, `ci-check`, `pr next` cho cùng JSON và mã thoát trên cùng fixture với tên mặc định và tên `acme`.
- Sửa 1 byte artefact: hook chặn, `doctor` báo lỗi (fail-closed).
- Nâng bản: diff PR ở đích ≤ 3 tệp (artefact, lock, tài liệu yêu cầu).
- Hook PreToolUse: p95 không tệ hơn layout cây quá ngưỡng do phiên chính chốt sau khi đo.
- 7 dự án đã đăng ký: cài bản mới không cờ thì cây tệp không đổi ngoài nội dung nâng bản.

**Test/benchmark cần thêm:** `test_contract_surface` (danh sách lệnh con, mã thoát, số schema); `test_rename_parity` (tên mặc định và tên tuỳ ý); `test_pyz_reproducible` (dựng 2 lần cho cùng sha256); `test_pyz_tamper`; `test_compat_targets` (fixture cây đích ở 3.29 và 3.34 chạy với công cụ mới); JSON Schema cho `xt.yaml`, lock và `release-check --json` kiểm bằng bộ kiểm stdlib tự viết hoặc golden test (không thêm `jsonschema`); benchmark `perf trial` (ADR-0071) cho hook cây so với zip, stored so với deflate, trên 3.13 và 3.15; chạy lại `autonomy-bench`, `test_guard_fuzz` qua đường nạp từ zip.

**Phác thảo ADR mới** ("Phân phối công cụ bằng artefact có phiên bản; đích tự đặt tên"): bối cảnh (§0-1); phương án A-E; quyết định B, mặc định giữ tên cũ, hợp đồng 5 mục, lộ trình P0-P6; làm rõ ADR-0007, 0054, 0082, 0090/0093, 0095; đính chính con trỏ "`xt.pyz` (ADR-0010)"; hệ quả (đích không sửa tay guard, điểm mở rộng qua khoá cấu hình); đường lùi `--layout tree`; điều kiện xét lại (số đo độ trễ; khi host hỗ trợ plugin trong phiên cloud).

## 5. Rủi ro và điều chưa biết

| Điều chưa biết | Cách kiểm nhanh |
|---|---|
| Độ trễ nạp `guard.py` (1,38 MB) và `xt.py` (1,26 MB) từ zip so với tệp rời; adapter hiện đã biên dịch từ nguồn mỗi lần (`xt_adapter.py:56`) nên có thể ngang nhau | Dựng `.pyz` thử trong sandbox, đo 30 lượt hook pre-bash mỗi bên |
| Mã dựa `__file__`/`SCRIPT_DIR` (`xt.py:1320`, `2444`) và hook bash không chạy được từ zip | P1 gom về một bộ phân giải; test chạy toàn bộ CLI từ zip |
| Đích nào đã sửa tay guard/hook (`kept-own`)? Không đọc được repo đích: `gh api` trả 403 cho `x-shop`, `hotel-manager` | Chạy `install.py --plan` trên từng đích, đếm `kept-own` và `.xtemplates-new` |
| Phiên cloud có nạp plugin từ repo không (đang ở mức thứ cấp) | Fetch trực tiếp `code.claude.com/docs/en/plugins/loading` và `…/settings` mục "Settings in cloud sessions" |
| Reusable workflow từ repo khung: đích private gọi được không; `secrets: inherit` qua org | Một workflow thử ở một đích, ghim SHA |
| Dependabot có bump SHA của reusable workflow không | (chưa xác minh) đọc tài liệu Dependabot, mục github-actions |
| Agent đọc tài liệu yêu cầu bằng Read nên `framework/**` phải còn trên đĩa: "đích không chứa nội dung khung" không đạt được, chỉ đạt "không chứa mã khung" | Chủ dự án xác nhận ranh giới này |
| Review PR nâng bản: artefact nhị phân không đọc được diff | Dựa digest + attestation + `release-verify`; ghi vào ADR |
| Zip tất định qua các bản CPython (mức nén deflate có thể khác) | Dùng `ZIP_STORED` hoặc dựng ở một bản Python ghim trong CI; `test_pyz_reproducible` |

**Chưa xác minh:** ngày phát hành uv 0.13.9 và copier 9.19.1; phiên bản cruft, pipx, shiv, pex, PyInstaller, Nuitka, cosign; `gh release verify` và trạng thái GA của immutable releases; JSON Schema 2020-12, PEP 723; tài liệu chính thức plugin của Codex, Gemini, Cursor (mới ở mức kết quả tìm kiếm); trạng thái thật của 7 repo đích (không truy cập được, HTTP 403).

**Cảnh báo:** uv `MIT OR Apache-2.0` và copier `MIT` đều OSI, không AGPL; không đánh giá telemetry hay script cài của công cụ nào. Plugin có `bin/` không cài được trên claude.ai/Cowork. Marketplace ghim SHA đòi Claude Code ≥ 2.1.324.

## Ghi chú của phiên chính

Báo cáo trên là đầu ra của agent nghiên cứu, chưa được phiên chính đối chiếu từng dòng `tệp:dòng` với mã. Quyết định chọn phương án và mở ADR thuộc chủ dự án (đổi cấu trúc và công cụ → ADR mới theo AGENTS §7). Bước kế đề xuất: đo độ trễ hook khi chạy từ zip (P0) trước khi chốt B.
