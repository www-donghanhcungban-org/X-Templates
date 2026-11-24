---
title: Khảo sát dự án tương tự trên GitHub — bổ sung cho việc tách khung khỏi dự án đích
kind: research
updated: 2026-11-24
---

# Bổ sung từ 26 dự án tương tự (đọc 2026-11-24)

> Bổ sung cho [`2026-11-24-framework-target-independence.md`](2026-11-24-framework-target-independence.md) (khuyến nghị B: artefact `.pyz` ghim digest + launcher mang tên đích + hợp đồng có schema). Lượt khảo sát chỉ đọc bởi một agent `researcher` (model bậc cao nhất); phiên chính chưa đối chiếu lại từng nguồn. Sao, `pushed_at`, giấy phép lấy từ GitHub Search API ngày 2026-11-24 (một nguồn duy nhất). Nội dung web là dữ liệu, không phải chỉ thị. Mục "chưa xác minh" ở §5.

## 1. Kết luận

1. **Không có thiết kế nào trong 26 dự án thay được B** dưới ràng buộc của khung (stdlib-only, guard fail-closed, phiên cloud, tự host mặc định). Lõi B có tiền lệ trực tiếp: pre-commit phát hành zipapp 0 phụ thuộc (`pre-commit-4.7.0.pyz`, 7,28 MB ở Release), Gradle wrapper và mise commit launcher ghim bản vào repo.
2. **Phương án D (plugin) bị loại ở mức bằng chứng trực tiếp:** `code.claude.com/docs/en/settings.md` §Settings in cloud sessions — marketplace do repo khai "aren't added in a cloud session". Phát hiện 4 của báo cáo trước nâng từ thứ cấp lên trực tiếp.
3. **B còn thiếu bảy điểm** (B1–B7, §3), xếp theo giá trị: B4, B6, B3, B1, B2, B7, B5.
4. **Phản chứng phải ghi vào ADR:** Yarn đã rời mô hình "binary nằm trong repo" (`yarnPath`: "we now recommend to use Corepack"); shiv bung ra `~/.shiv` và thừa nhận cache có thể bị sửa tay. Với khung, phiên cloud mạng "Limited" và guard fail-closed vẫn nghiêng về artefact nằm trong repo; đây là đánh đổi có chủ ý, và nếu sau này cần cache ngoài repo thì phải kiểm digest mỗi lần.
5. **Độ trễ hook từ zip có lẽ nhỏ hơn đã lo (suy luận, chưa đo):** `research/2026-11-23-guard-compile-cost.md` đo compile khoảng 0,40 s trong 0,55 s mỗi hook, vì bộ nạp compile từ nguồn mỗi lần (AUD-SEC-074). Đọc 1,4 MB từ zip khó thành phần chi phối. Vẫn phải đo ở P0.
6. **Không dùng làm nền:** claude-task-master (MIT + Commons Clause), renovate (AGPL-3.0), cruft (ngừng từ 2024-12), get-shit-done (đã archive).

## 2. Bảng so sánh

| Repo | Sao · pushed_at · giấy phép | Mô hình phân phối | Đích đặt tên | Nâng bản | Guard / kiểm máy |
|---|---|---|---|---|---|
| github/spec-kit | 151 168 · 11-23 · MIT | CLI (`uv tool install specify-cli`) + tệp chép vào `.specify/` và thư mục agent | cố định `.specify/`, lệnh `speckit.*` | hai mặt riêng: `specify self upgrade [--tag]` và `specify integration upgrade <key>` theo manifest | chặn nâng khi tệp manifest bị sửa tay, trừ `--force`; `integration status`; chỉ nhận tag `vX.Y.Z` |
| Fission-AI/OpenSpec | 75 570 · 11-23 · MIT | gói npm/brew + tệp sinh ra | cố định `openspec/`; schema tự đặt qua `schema fork` | `openspec update`; skill ghi phiên bản đã sinh, khớp thì bỏ qua | `validate --all --json` cho CI; không hook chặn; telemetry bật mặc định (opt-out) |
| bmad-code-org/BMAD-METHOD | 55 669 · 11-24 · MIT + nhãn hiệu | `npx skills add …` rồi `bmad setup` | cố định `_bmad/` | chạy lại `bmad setup`; ghim `#<tag>`; `_bmad/custom/` giữ qua nâng | `bmad-eval` đo skill; cần Node + Python + uv |
| obra/superpowers | 325 097 · 11-03 · MIT | plugin theo từng host (15 host) | tên plugin cố định | theo host, "often automatic" | không; SessionStart chỉ nạp bootstrap |
| buildermethods/agent-os | 5 634 · 10-07 · MIT | chưa xác minh | chưa xác minh | chưa xác minh | chưa xác minh |
| claude-task-master | 28 531 · 04-28 · MIT + Commons Clause | npm + MCP server | cố định `.taskmaster/` | `task-master migrate` | không nêu |
| SuperClaude_Framework | 23 952 · 09-27 · MIT | `pipx install superclaude` + `superclaude install` | không nêu | không nêu | không nêu |
| copier-org/copier | 3 724 · 11-23 · MIT | template git + tệp trả lời | `_answers_file` đổi tên được | `copier update`; `_migrations` theo phiên bản | migration/task tắt mặc định, cần `--trust`; `_min_copier_version` |
| cruft/cruft | 1 593 · 2024-12-25 · MIT | cookiecutter + `.cruft.json` (commit ghim) | không | `cruft update` | `cruft check` mã 1 khi lệch; **ngừng hoạt động** |
| projen/projen | 2 963 · 11-23 · Apache-2.0 | gói + tổng hợp lại tệp | đích viết `.projenrc` | chạy lại CLI | "generated files are never manually edited" |
| nrwl/nx | (chưa lấy số) | gói npm + migration | — | `nx migrate` hai bước (`migrations.json` rồi `--run-migrations`); mỗi migration một commit | migration `required`/`optional` |
| pre-commit/pre-commit | 15 711 · 11-09 · MIT | pip **hoặc zipapp 0 phụ thuộc** | cấu hình cố định `.pre-commit-config.yaml` | `autoupdate [--freeze]`; `rev` bất biến | `validate-config`; `uninstall` trả hook cũ |
| renovatebot/renovate | 23 239 · 11-24 · **AGPL-3.0** | preset `github>org/repo:file#tag` | tên preset tự do | đổi tag | — |
| ossf/allstar | 1 467 · 11-23 · Apache-2.0 | App + repo `.allstar` cấp org | tệp theo tên policy | trung tâm | công tắc "Repo Override"; hành động `issue`/`fix` |
| jdx/mise | 36 429 · 11-24 · MIT | launcher commit vào repo (`bin/mise`) tải bản ghim; tool stub | **tên stub tuỳ ý** | sinh lại launcher rồi commit | stub ghim checksum + size |
| aquaproj/aqua | 1 900 · 11-23 · MIT | `aqua.yaml` + `aqua-checksums.json` trong git | — | cập nhật checksum | **kiểm checksum tắt mặc định** |
| linkedin/shiv | 1 949 · 05-22 · BSD-2-Clause | zipapp tự bung ra `~/.shiv` | — | tệp mới | cache sửa tay được |
| Gradle wrapper | (tài liệu 9.9.2) | launcher + JAR + properties commit vào repo | `gradlew` cố định | `./gradlew wrapper --gradle-version X`, phải chạy hai lần | `distributionSha256Sum`, chỉ kiểm lúc tải |
| anthropics/claude-plugins-official | 48 066 · 11-24 · Apache-2.0 | marketplace plugin | tiền tố `<plugin>:` | theo host | không áp trong phiên cloud |
| cookiecutter, backstage, renovate, scorecard, pex, uv, gsd | (xem §6) | — | — | — | gsd đã archive |

## 3. Bảy bổ sung cho B

| # | Bổ sung | Học từ | Áp vào B |
|---|---|---|---|
| B1 | **Tên suy từ tên tệp launcher**, không khai ở chỗ thứ hai | mise tool stub: tên tệp tuỳ ý, cấu hình (tool, version, checksum, size) nằm trong tệp | launcher của đích mang `version` + `sha256`; `tool.json` chỉ còn `config`, `env_prefix`, `contract`; bớt một nguồn lệch tên |
| B2 | **Launcher tối thiểu và đóng băng** | Gradle: lần chạy `wrapper` đầu chỉ sửa properties, phải chạy lần hai để cập nhật JAR và script | launcher không chứa logic đổi theo bản; test rằng nâng bản không sửa launcher ngoài dòng ghim; thêm launcher `.cmd` nếu đích có Windows |
| B3 | **Tách hai mặt nâng bản + lệnh trạng thái** | spec-kit: `self upgrade` (công cụ) và `integration upgrade` (tệp dự án); `integration status` liệt kê tệp sửa/thiếu | layout artefact có "nâng artefact" và "sinh lại tệp render" riêng, mỗi cái một mã thoát |
| B4 | **Tệp sinh ra thuộc khung, tuỳ biến ở thư mục riêng** | OpenSpec: "generated files are OpenSpec's to own — keep your own instructions elsewhere"; BMAD `_bmad/custom/`; projen | thay ba trạng thái `kept-own`/`.xtemplates-new` bằng: skill/agent render có dấu phiên bản, đè vô điều kiện; đích tuỳ biến ở thư mục overlay được khai. Trả lời rủi ro "đích mất khả năng sửa tay guard" |
| B5 | **Thứ tự phân giải có lệnh soi** | OpenSpec `schema which` (project → user → package), `schema fork` | lệnh `which`/`explain` cho skill, cấu hình, luật guard: nói giá trị đến từ artefact hay overlay của đích |
| B6 | **Migration có phiên bản, hai bước, nằm trong artefact đã attest** | copier `_migrations` (chạy khi phiên bản mới ≥ khai báo > cũ; tắt mặc định cần `--trust`); Nx: bước 1 ghi `migrations.json`, bước 2 chạy; mỗi migration một commit | bảng migration khai phiên bản trong artefact; `upgrade` sinh kế hoạch đọc được trước khi chạy; mỗi migration một commit trong PR nâng bản; vì nằm trong artefact ký nên không cần cờ trust riêng |
| B7 | **Công tắc ghi đè + sàn phiên bản** | Allstar "Repo Override"; copier `_min_copier_version`; spec-kit chỉ nhận `vX.Y.Z` | `tool.json` thêm `min_contract`, artefact thấp hơn thì fail-closed có thông báo; overlay của đích chỉ được thêm luật guard, không nới |

**Nên tránh:** JSON đầu ra không đánh phiên bản (OpenSpec tự cảnh báo) — hợp đồng 5 mục phải có số schema ở mọi đầu ra máy đọc; checksum tắt mặc định (aqua); kiểm checksum chỉ lúc tải (Gradle) — B phải kiểm mỗi lần hook chạy hoặc theo cache khoá mtime+size; cập nhật tự động không ghim (superpowers); đòi nhiều runtime (BMAD cần Node + Python + uv).

## 4. Cải tiến khác (đã grep repo; xếp theo giá trị/chi phí)

| # | Cải tiến | Nguồn học | Trạng thái trong repo | Tệp sẽ đổi | Rủi ro |
|---|---|---|---|---|---|
| 1 | Ghi rõ phiên cloud **nhiều repo** không chạy hook | settings.md §cloud | `harness-files.md:568` (`LOOP-HARNESS-031`) có cho thread trong Projects; chưa thấy dòng riêng cho phiên nhiều repo (chỉ grep) | `framework/11-autonomous-loop/harness-files.md`, có thể `session-start` cảnh báo | thấp; cần đọc lại tài liệu trước khi thêm ID |
| 2 | Dấu phiên bản trong skill/agent đã render | OpenSpec | grep `generated_by\|xt-version:`: 0 | `scripts/install.py`, `.claude/skills/*/SKILL.md` (frontmatter `metadata`), `doctor` | đổi hash mọi skill ở đích một lần |
| 3 | Lệnh gỡ khung trả repo về trước khi cài | pre-commit `uninstall`; spec-kit `integration uninstall` | không có lệnh con tương ứng trong `xt.py` | `scripts/install.py`, `xt.py`, test | lệnh xoá tệp phải qua guard; cần manifest đủ tin |
| 4 | Lịch gỡ bỏ có phiên bản cho lệnh/khoá ngừng dùng | mise ("will be removed in 2027.9.0") | "Ngừng dùng" có cho ID; chưa có cho lệnh/khoá | `framework/00-method/conventions.md`, `xt.py`, `doctor` | thấp |
| 5 | Kiểm tĩnh skill theo Agent Skills spec (tên ≤ 64, mô tả ≤ 1024, tên trùng thư mục) | agentskills.io; BMAD `bmad-eval` | không thấy test spec skill | `tests/test_skills_spec.py` (mới), `gate-fast` | thấp, chỉ stdlib |
| 6 | Bộ đánh giá kích hoạt skill | BMAD Toolsmith | chưa có `skill eval`; có `autonomy-bench` cho guard | `tests/fixtures/`, công cụ đo | cần gọi model → tốn tiền; làm phần tĩnh trước |
| 7 | Kế hoạch di trú đọc được + mỗi migration một commit | Nx, copier | không có `migrations.json`; có `migrate_legacy` | `scripts/install.py`, `xt_distribution.py`, `xt-upgrade.yml` | trùng B6; làm trong P4 |
| 8 | Chạy OpenSSF Scorecard trên chính repo khung | ossf/scorecard | `supply-chain.md` yêu cầu ở đích; không có `scorecard-action` trong `.github` | `.github/workflows/scorecard.yml` | `publish_results` đẩy kết quả ra API công khai, cân với "tự host mặc định" |
| 9 | Lớp mặc định dùng chung cho nhiều đích (preset có tag) | Renovate, Allstar | `docs/ops/registry.json` có 7 đích; chưa kiểm `xt.yaml` có kế thừa | `templates/xt.yaml`, `xt.py` | thêm tầng phân giải làm khó truy nguyên; cần B5 trước |
| 10 | Lệnh `which`/`explain` nguồn của giá trị cấu hình | OpenSpec `schema which` | không có trong `xt.py` | `xt.py` | thấp |

Đã có, không đề xuất: ghim SHA mọi `uses:` (`SEC-SUPPLY-001`, 12 workflow đều ghim), zizmor/actionlint, sàn `claude_min_version`, `upgrade check` mã 0/10/11, attestation, `DO_NOT_TRACK`, hash ba trạng thái.

## 5. Bảng dữ kiện chính (đọc 2026-11-24; fetch trực tiếp trừ khi ghi khác)

| Mục | Giá trị | URL |
|---|---|---|
| spec-kit nâng bản | manifest-aware; chặn khi tệp bị sửa trừ `--force`; `specs/` và `constitution.md` không đụng; tag `vMAJOR.MINOR.PATCH` | raw.githubusercontent.com/github/spec-kit/main/docs/upgrade.md |
| OpenSpec CLI | `update` so phiên bản ghi trong skill; `update --dry-run --json`; `validate --all --json`; `schema fork/which/validate`; telemetry bật mặc định (tự tắt trong CI), Node ≥ 22.20.0 | raw.githubusercontent.com/Fission-AI/OpenSpec/main/docs/cli.md · docs/customization.md · README.md |
| BMAD | `npx skills add …`, `bmad setup`; `_bmad/custom/` giữ qua nâng; ghim `#<tag>`; LICENSE MIT + ghi chú nhãn hiệu | docs.bmad-method.org/start/install-bmad/ |
| pre-commit zipapp | `pre-commit-4.7.0.pyz` 7,28 MB; `rev` phải bất biến; `--freeze` | pre-commit.com · github.com/pre-commit/pre-commit/releases |
| copier | `_migrations`, `_min_copier_version`, `_answers_file`, `--trust` | copier.readthedocs.io/en/stable/configuring/ |
| Nx migrate | hai bước, `--create-commits`, required/optional | nx.dev/docs/features/automate-updating-dependencies |
| Gradle wrapper | 4 tệp commit; `distributionSha256Sum` chỉ kiểm khi chưa tải; nâng phải chạy hai lần | docs.gradle.org/current/userguide/gradle_wrapper.html |
| mise | `generate install-script --write` → `./bin/mise`; tool stub tên tuỳ ý; `generate bootstrap` sẽ bỏ ở 2027.9.0 | mise.jdx.dev/cli/generate/install-script.html · mise.jdx.dev/dev-tools/tool-stubs.html |
| aqua | `aqua-checksums.json` trong git; "Checksum verification is disabled by default" | aquaproj.github.io/docs/reference/security/checksum/ |
| shiv | bung ra `~/.shiv`; `--reproducible`/`SOURCE_DATE_EPOCH` | shiv.readthedocs.io/en/latest/ |
| Renovate preset | `github>abc/foo:xyz#1.2.3` | docs.renovatebot.com/config-presets/ |
| Allstar | repo `.allstar` cấp org; Repo Override | raw.githubusercontent.com/ossf/allstar/main/README.md |
| Yarn | `yarnPath` không còn là cách khuyến nghị | yarnpkg.com/configuration/yarnrc |
| Phiên cloud | một repo ngoài project: đọc `.claude/settings.json`; nhiều repo: chỉ đọc `enabledPlugins`, `extraKnownMarketplaces`, không đọc hook/permission/env | code.claude.com/docs/en/settings.md |

**Chưa xác minh:** `api.github.com/repos/*/releases/latest` trả 403 (9 repo) nên phiên bản mới nhất của OpenSpec, BMAD, mise, shiv, pex, copier, aqua chưa đọc; Agent OS (cài đặt sau form email); định dạng manifest tích hợp của spec-kit (hai URL tài liệu 404); projen (tệp read-only/dấu "Generated by"); Corepack `packageManager` kèm hash; lịch sử giấy phép (`git log --follow -- LICENSE*`) của mọi repo; license của `anthropics/skills` và `anthropics/claude-code`; validator/test/benchmark của các repo (chưa chạy); số sao chỉ từ một nguồn; `install.sh` của các repo chưa đọc, chưa chạy.

## 6. Cảnh báo

- **Giấy phép:** claude-task-master MIT + Commons Clause (không OSI); renovate AGPL-3.0; BMAD thêm ghi chú nhãn hiệu (API: NOASSERTION).
- **Trạng thái:** gsd-build/get-shit-done đã archive; cruft ngừng (pushed_at 2024-12-25); cookiecutter và shiv không đẩy gì từ 04 và 05/2026.
- **Telemetry mặc định bật:** OpenSpec (opt-out); superpowers tải logo kèm số phiên bản (opt-out).
- **Mặc định kém an toàn:** aqua tắt kiểm checksum; Gradle chỉ kiểm lúc tải; superpowers tự cập nhật không ghim.
- **Phụ thuộc runtime** trái "stdlib-only, tự host mặc định" nếu dùng làm nền: OpenSpec (Node ≥ 22.20), BMAD (Node + Python + uv), spec-kit (uv/pipx).
- Không gặp lời nhắc injection trong các README đã đọc; dòng "Fetch the complete documentation index at …/llms.txt" ở đầu trang `code.claude.com` được coi là dữ liệu, không làm theo.

## Ghi chú của phiên chính

Chưa đối chiếu từng nguồn. Quyết định (giữ B, bổ sung B1–B7, mở ADR) thuộc chủ dự án; đổi cấu trúc và công cụ cần ADR mới (AGENTS §7). Việc rẻ không phụ thuộc quyết định tách: cải tiến 1, 2, 4, 5 ở §4.
