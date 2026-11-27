---
title: Kế hoạch nâng cấp hợp nhất — tách xt.py/guard.py, review high/120, giao hàng theo bằng chứng (Revision 4)
kind: research
updated: 2026-11-27
---

# Kế hoạch nâng cấp hợp nhất (Revision 4, 2026-11-27)

> **Trạng thái: đã duyệt để thực thi (D-626, 2026-11-27).** §0 là bản hợp nhất hiện hành và **thắng mọi phần khác** của tệp. §1–§37 là căn cứ và lịch sử của ba revision trước (bản chuyển PDF 40 trang, Revision 2, Revision 3): số đo, phân tích và định nghĩa gói/lát ở đó còn dùng; **thứ tự, trạng thái và phạm vi thì theo §0**. Việc thực thi đăng ký ở `docs/autopilot/PLAN-upgrade-2026-11-27.md` và các PLAN đã có. **D-610** (hoãn nâng dự án đích) vẫn hiệu lực.

## 0. Bản hợp nhất hiện hành — Revision 4 (2026-11-27, `main` `be1bf6b4`)

Lập sau khi ba reviewer độc lập (chỉ đọc) đối chiếu §1–§13, §14–§25, §26–§37 với `origin/main` `be1bf6b4`. Phần "đã kiểm, đúng" và "chưa kiểm" của ba lượt ở §0.8.

### 0.1 Cách đọc
- **Một lịch duy nhất: §0.5.** Bốn bảng lịch cũ (§6, §12.6, §23, §35) xếp cùng một việc ở bốn chỗ khác nhau (chính sách reviewer: Đợt 0 / PR 3 song song / 0D sau 0C / R2 sau R1) và ba câu cùng tự nhận "thắng khi xung đột". Từ Revision 4 chúng chỉ còn giá trị lịch sử; G01–G12, G12.0–.7, I0–I5, Cửa A–E giữ nguyên **định nghĩa**.
- **Một nguồn trạng thái: dấu `[x]` trong PLAN và hàng trong sổ audit.** Câu nào trong §1–§37 ghi một PR "đang mở/nháp" hay một lỗi "chưa sửa" thì đối chiếu §0.2.
- Nguồn ngoài (web) ở §11, §12.5, §37 không được kiểm lại trong Revision 4.

### 0.2 Hiện trạng ở `main` `be1bf6b4` (đo 2026-11-27)
| Mục | Trạng thái | Bằng chứng |
|---|---|---|
| `scripts/xt.py` · `.claude/hooks/guard.py` | 23.668 / 23.668 dòng · 24.689 / 24.689 dòng — **hết ngân sách dòng**; 1.270.558 · 1.391.040 byte; 1.301 · 1.421 `def`; `build_parser` 647 dòng | `tests/test_docs_budget.py:22-23` |
| PR đã merge sau khi tài liệu viết | #839 (T-5039), #840 (T-5043), #810, #847 (ADR-0107), #849 (ADR-0108), #850 (`FE-RENDER-019…021`), #851 (ADR-0109, D-624) | `git log origin/main` |
| Lỗi §3: ghi tệp cài bị cụt | **Đã sửa** (#840): `write_copy` qua `write_bytes_atomic`. Còn lại: `guard.py` đã cụt từ bản cài cũ không tự sửa (chỉ `--force-harness`); `rules` trong manifest mất sau lần cài hỏng rồi chạy lại. AUD-HAR-574 còn ghi "mở" | `install.py:451-460`; rà #840 |
| Lỗi §3: `executor-mech` chưa qua CLI | Còn | `xt.py:1573` `EXEC_TIER_RE`, `:1580`, `:5103`, `:23385` |
| Lỗi §3: cost lượt Gate đỏ bị bỏ | Còn; thuộc `T-5010` | `xt.py:9689` |
| Lỗi §3: release gặp tag có sẵn thoát 0 | Còn; **đã có ID `AUD-CI-042`** (chấp nhận, D-554, hạn 2027-01-21) | `release-tag.yml:60-63`, `:128-132` |
| Lỗi §3: Guard `core` mất ngữ cảnh khi lỗi | Còn; **chưa có ID** | `guard.py:24529-24542`, `:24602-24605` |
| Cấu hình reviewer | `reviewer`: opus, không khai effort, `maxTurns: 80`; `reviewer-alt`: opus, `effort: max`, `maxTurns: 80`; bản Codex `max`; `agent_toml` không map `maxTurns`; `review/SKILL.md` và mô tả `reviewer-alt` còn dặn "giao kèm model của phiên chính" (trái D-623) | `.claude/agents/`, `install.py:1551` |
| `pr-review.yml` | Còn `pull_request_target`; job đang tắt (biến kích hoạt rỗng, 5 run gần nhất `skipped`); `--max-turns 40`, không truyền effort; đã có nhánh inconclusive cho diff cắt/thiếu (AUD-CI-016) | workflow `:14`, `:55-57`, `:96-98`, `:114-116` |
| AUD-HAR-541 (tag glob) | Ca gốc đã chặn; **còn lọt `git tag *`** trong thư mục chỉ có tệp tên `v1.2.0` | rà Revision 4; `T-5041` vẫn cần |
| Khoá duyệt thiết kế | `evidence_sha256` và cơ chế "sổ tồn tại → khách" đã ở `main`. Nợ review: hồi sinh lời duyệt cũ khi bản 2 dùng tệp bằng chứng khác; nạp `xt_design` qua `pkgutil.resolve_name`/`pydoc.locate` lọt guard | rà #847, #849 |
| PLAN chưa tick dù đã merge | `T-5035`, `T-5037`, `T-5039`, `T-5042`…`T-5049`, `T-5043` (đối chiếu từng PR trước khi tick) | `PLAN-optimize-2026-11-26*.md` |
| Sổ audit | 1.187 hàng: 672 đã sửa, 362 mở (5 🟠, 357 🟢), 146 chấp nhận, 7 bác bỏ; 0 🔴 mở | `docs/ops/AUDIT-STATUS.md` |
| Chính sách merge của repo khung | `merge_review: optional`, `delivery_phase: harden`, `merge_hard_exceptions: auto`; lớp tác động tức thì (guard, hook, workflow — ADR-0095) vẫn đòi review sạch ở head | `xt.yaml:51-64` |

### 0.3 Quyết định hiệu lực
- **D-610:** không mở PR nâng ở dự án đích. `T-5017` (pilot Hotel Manager) và `T-5018` (nâng năm đích) hoãn; phần máy làm được đã tách ở `T-5024`.
- **D-623** (chủ dự án chốt 2026-11-26, ghi sổ 2026-11-27): `reviewer-alt` chỉ opus trở xuống; trần effort `high`. Lý do ghi lúc đầu có một câu sai, đã đính chính trong sổ.
- **D-625 — tuyến review dưới trần `high`.** Luật máy (`review_capability_error`): cùng họ thì effort reviewer phải cao hơn hẳn; khác bậc cùng nhà cung cấp thì so bậc. Với reviewer cao nhất là opus/`high`:

  | Người viết | Reviewer opus/`high` | Tuyến |
  |---|---|---|
  | `executor-mech` (haiku), `executor`, `researcher`, `acceptance-author` (sonnet) | bậc cao hơn → nhận | **Mặc định cho diff lớp bắt buộc review** |
  | `executor-deep` ở opus/`medium` — **mặc định của vai từ D-627** (frontmatter và gương Codex), khai `--author-effort medium` | cùng họ, `high` > `medium` → nhận | **Việc khó**, kể cả diff lớp bắt buộc review |
  | `executor-deep` bị đè effort lên ≥ `high` (tham số lần gọi, biến môi trường); phiên chính opus tới `xhigh`; phiên chính bậc top | không cao hơn → **từ chối clean** | Vẫn rà để tìm 🔴, ghi `--inconclusive`. Lớp bắt buộc review thì PR đứng ở `missing` và **không merge được** — không gọi là "nợ trả sau" |

  Hệ quả: diff chạm guard, hook, workflow, ngoại lệ cứng do bậc thấp hơn reviewer viết; phiên chính viết đặc tả và ca kiểm trước, không tự viết diff lớp đó. Không sửa lời khai tác giả, không tự nâng reviewer. Lối "(d) ghi nợ rồi trả theo lô" của §12.4 chỉ còn đúng khi `review_deferrable` đúng (pha build, không ngoại lệ cứng); repo khung đang `harden`. Dự án đích đặt `merge_review: required` mà không theo tuyến này sẽ kẹt. Reviewer khác nhà cung cấp để sau, khi bảng bậc ngoài Anthropic hết `verified: false`. Đo lại chất lượng người viết bậc thấp/effort thấp bằng bộ đánh giá G10.
- **Cần ADR mới (ADR-0110, `T-5063`):** thay phần effort của ADR-0098 §2 **và** câu "reviewer-alt Opus max" của D-605; `maxTurns` 80 → 120 ghi cùng ADR. Cho tới khi ADR-0110 merge, cấu hình hiện hành (`reviewer-alt` effort `max`) còn hiệu lực.
- **D-627** (chủ dự án chỉ đạo 2026-11-27): việc khó giao `executor-deep` opus ở effort `medium`, đặt làm mặc định của vai ở cả Claude Code và Codex; mã hoá cùng ADR-0110 (`T-5063`).
- **D-624 / ADR-0109:** gói `site-cms-ts` = Astro tĩnh + Decap CMS; việc ở `T-5057…T-5060`.
- **D-626:** duyệt Revision 4 và PLAN-upgrade.

### 0.4 Điều chỉnh phạm vi so với ba revision trước
| Đề xuất cũ | Revision 4 | Lý do |
|---|---|---|
| §15, §18: module mới `scripts/xt_code_index.py` (`locate/search/context/impact`) | **Không tạo.** G12.6a = mở rộng `scripts/xt_guard_profile.py` (đóng AUD-ARCH-019, thêm alias và symtable; đã có `dependency_edges`, `transitive_closure`, `entry_points`, `--closure`, `--path` chạy được trên `xt.py`) và thêm trường `symbols` tuỳ chọn cho `xt.py context --json` | Trùng công cụ đã có và trái §30.1 ("không viết một analyzer thứ hai"); ánh xạ test đã có ở `test-select` (AST import, lan theo lớp); bề mặt hợp đồng đã có `tests/fixtures/contract-surface.json` |
| §17: cache bền, SQLite/FTS5, ma trận 19 ca, I1 | **Hoãn.** MVP parse lại từ bytes mỗi lần gọi (compile 261 ms / 308 ms). Chỉ mở cache khi p50 của một lần tra vượt 2 s trên cả hai tệp lớn; §17 và I1 chỉ áp khi cache tồn tại | Chưa có số đo cho thấy cần; không có cache thì không có gì để cũ |
| §22: so A/B/C trên 24–36 task × ≥ 3 lần × 3 nhánh (216–324 lượt agent) | Chạy **A trên 8 task** trước. Chỉ dựng B khi A trượt ngữ cảnh bắt buộc ở ≥ 2/8 task hoặc tốn ≥ 30 % token cho việc định vị. Ước lượng token × 1,5 trước khi chạy. "Lợi" = trung vị token đọc nguồn giảm ≥ 30 % và độ phủ ngữ cảnh bắt buộc không thấp hơn A | Không có ngân sách và ngưỡng dừng (`LOOP-ORCH-020`) |
| §16: "manifest tối thiểu có owner" cho module | Sinh từ ba danh sách đã có (`install.py:913`, `xt_pack.py:33`, `typecheck` của `xt.yaml`); không thêm danh sách thứ tư | Một chủ đề một nhà |
| §16 ví dụ `"encoding":"utf8-byte"` trên span dòng | `"coordinate_system":"line1-incl/col-utf8-byte-excl"` | Khớp quy ước dòng 1-based của chính §16 |
| §19, §23: C15 chỉ phụ thuộc L05 | C15 sau **C14 và L05** | `framework-optimization.md:236` |
| §19: baseline parity Guard chụp sau bản sửa `core` | Chụp sau bản sửa `core` **và** `T-5041` (cùng chạm `guard.py` và corpus); một chủ, nối tiếp | Tránh chụp hai lần |
| §12.4 mục 1: "kèm ADR nới trần (ADR-0092)" | ADR-0092 nới trần **byte**; trần dòng đặt ở `T-5016`, mỗi lần nới có ADR riêng (0103, 0104, 0106) | Dẫn sai |
| §12.4 mục 2: "phiên chính effort tới `xhigh` — D-558/D-559" | Nguồn là ADR-0098 §2 và D-605 | Dẫn sai |
| §29.2: thêm inconclusive cho diff cắt/thiếu ở `pr-review.yml` | Đã có (AUD-CI-016); việc còn lại: kết quả dở do model trả về | Đã làm |
| §29.3: tách đặc quyền workflow review trước hạn 2026-12-02 | Đợt 0 chỉ **gỡ trigger** `pull_request_target` (job đang tắt); thiết kế tách đặc quyền dời tới khi bật lại review trên CI | Việc nhỏ nhất đáp ứng hạn |
| G04/§4B pilot Hotel Manager; G03 bằng chứng release; R0 "checklist T-4007/T-5020"; `T-5019` | Nhà = `T-5017` (hoãn, D-610); `T-5024`; `T-5024`; `T-5019` gộp vào `T-3989`/`T-3990` | Trùng task đã có |

### 0.5 Lịch thực thi duy nhất
Mỗi dòng một PR, một nhánh từ `origin/main`. Cột "Viết" theo D-625 (người viết phải dưới bậc reviewer ở lớp bắt buộc review). "0 dòng" = `guard.py`/`xt.py` không tăng dòng. Task mới (`T-5062…T-5073`) ở PLAN-upgrade; task cũ ở PLAN gốc của nó.

| # | Đợt | PR | Task | Tệp chính | Sau | Viết · rà | Gate |
|---|---|---|---|---|---|---|---|
| 1 | 0 | Đồng bộ sổ: tick task đã merge, AUD-HAR-574 phần đã sửa, repro mới AUD-HAR-541, ghi nợ review #840/#847/#849 | `T-5062` | `PLAN-optimize-2026-11-26*.md`, `AUDIT-STATUS.md` | — | phiên chính · không | `xt.py audit check docs/ops/AUDIT-STATUS.md`; `tests.test_plan_files` |
| 2 | 0 | ADR-0110: reviewer `high`/120, opus trở xuống, tuyến D-625 | `T-5063` | `.claude/agents/reviewer*.md`, `review/SKILL.md` (2 gương), `.codex/agents/`, ADR mới | — | `executor` · `reviewer-alt` | `tests.test_model_tiers tests.test_codex_harness`; `xt.py validate` |
| 3 | 0 | Gỡ `pull_request_target` khỏi `pr-review.yml` (hạn 2026-12-02), sửa chú thích reviewer bậc top | `T-5064` | `.github/workflows/pr-review.yml`, `PROGRESS.md` | — | `executor` · `reviewer-alt` | `xt.py ci-check`; `tests.test_ci` |
| 4 | 0 | `verify-render` đi vào shadow root (AUD-HAR-567, hạn 2026-12-02) | `T-5065` | `framework/templates/ui-gates/verify-render.mjs` | — | `executor` · `reviewer` | job CI có Chromium (D-603) |
| 5 | 0 | Settings: `PreSkillShellCommand`, độ sâu subagent | `T-5040` | `.claude/settings.json`, hook | — | `executor` · `reviewer-alt` | Gate của task; thêm `claude_min_version` ≥ 2.1.332 (bản cũ hơn bật hộp thoại lúc khởi động) |
| 6 | 0 | `release-tag` gặp tag có sẵn: kiểm SHA/kiểu tag và nháp trước `exit 0`; đóng AUD-CI-042 | `T-5066` | `.github/workflows/release-tag.yml` | — | `executor` · `reviewer-alt` | `xt.py ci-check`; `tests.test_release_assets` |
| 7 | 0 | Bộ kiểm bằng chứng tag-drill/pilot/rollout (phần máy) | `T-5024` | theo task | — | theo task | Gate của task |
| 8 | 1 | Guard: glob ở vị trí tên tag (thêm ca `git tag *`), 0 dòng | `T-5041` | `guard.py`, corpus | 2 | `executor` · `reviewer-alt` | Gate của task |
| 9 | 1 | Guard: lỗi runtime ở `core` không rơi về quyết định rỗng; đăng ký AUD trước; 0 dòng | `T-5067` | `guard.py`, corpus, sổ audit | 8 | `executor` · `reviewer-alt` | `tests.test_hooks tests.test_guard_corpus tests.test_autonomy_bench`; có ca tốt đối chứng từng mode |
| 10 | 1 | Guard: `XT_INPROC_LOADERS` thêm `resolve_name`, `locate`, `importfile`; 0 dòng | `T-5068` | `guard.py`, corpus | 9 | `executor` · `reviewer-alt` | `tests.test_stage_agent_approval tests.test_guard_corpus`; so vi sai guard cũ/mới: 0 lệnh bị nới |
| 11 | 1 | Chụp baseline parity Guard, rồi tách: bao đóng → loader/fence → cụm đầu | `T-3996` → `T-3987/88` → `T-3989/90` | `.claude/hooks/` | 10 | theo PLAN-guard-split | theo task |
| 12 | 2 | ADR-0111 (L05) + lát `xt_shard` chỉ di chuyển, hạ trần dòng `xt.py` | `T-5069` | `xt.py`, `scripts/xt_shard.py`, `install.py`, `xt_pack.py`, `xt.yaml`, `test_docs_budget.py` | 2 | `executor` · `reviewer-alt` | `tests.test_ci_shard tests.test_docs_budget tests.test_xt_cli tests.test_install tests.test_pack`; `typecheck`; patch trong test trỏ nơi tra cứu thật |
| 13 | 2 | Sổ lát: sáu nguồn → cost lượt đỏ → xuất bền | `T-5009` → `T-5010` → `T-5011` | `xt.py`, `xt_flow.py` | 12 | theo task | theo task |
| 14 | 2 | `executor-mech` qua CLI, đỏ một lần chuyển cấp | `T-5070` | `xt.py` (0 dòng ròng sau #12), test | 12 | `executor` · `reviewer-alt` | `tests.test_xt_cli tests.test_model_tiers`; `xt.py loop next` nhận `exec: mech` |
| 15 | 2 | Máy cưỡng chế trần reviewer: `pr reviewed` từ chối effort > `high` và bậc top; hook kiểm `tool_input.effort`; `doctor` báo `CLAUDE_CODE_EFFORT_LEVEL` | `T-5071` | `xt.py`, hook, test | 2, 12 | `executor` · `reviewer-alt` | ca `HIGH/HIGH`, `XHIGH/HIGH`, override `max`, biến môi trường đều bị từ chối clean |
| 16 | 2 | G12.6a: `xt_guard_profile.py` đóng AUD-ARCH-019; `xt.py context --json` thêm `symbols` | `T-5072` | `xt_guard_profile.py`, `xt.py` | 12 (phần `xt.py`) | `executor` · `reviewer` | `tests.test_guard_profile`; `--closure policy_action --json` có hằng khởi tạo |
| 17 | 3 | Khoá duyệt thiết kế: trả nợ review #847 | `T-5073` | `scripts/xt_design.py`, test, ADR-0107 | — | `executor` · `reviewer-alt` | `tests.test_design_gate`; ca revert sổ với tệp bằng chứng khác phải khoá |
| 18 | 3 | Gói `site-cms-ts`: starter → CI nghiệm thu → cài → pilot | `T-5057` → `T-5058` → `T-5059` → `T-5060` | `packs/site-cms-ts/`, workflow mới, `install.py` | `T-5059` sau 12 | theo PLAN-site-cms | theo task |
| 19 | 3 | Starter `web-api-ts` token + ma trận viewport; `verify-render` axe hẹp | `T-5012`, `T-5013` | theo task | 4 | theo task | job CI có Chromium |
| 20 | 0 | `LOOP-STOP-031` dạng tài liệu: mọi PR nháp, chỉ PR số nhỏ nhất bật CI (ADR-0105 chưa có máy) | `T-5074` | `stop-points-and-escalation.md`, AGENTS.md, mẫu AGENTS, skill `/autopilot` | — | `executor` · `reviewer` | `cmp` hai gương skill; `tests.test_docs_budget tests.test_codex_harness` |
| 21 | 0 | Runbook steward §4: tag tay phải kèm release | `T-5076` | `docs/ops/RUNBOOK-PR-STEWARD.md` | — | `executor` · không | `check-links.py`; `changelog-check` |
| 22 | 2 | Máy hàng merge FIFO theo số PR (ADR-0105) | `T-5075` | `scripts/xt_merge_queue.py`, `xt.py` (0 dòng ròng), `xt.yaml` | 12, 20 | `executor` · `reviewer-alt` | `tests.test_merge_queue`; `typecheck`; steward có/không `XT_STEWARD_TOKEN` |
| 23 | 0 | Luật tuyến review vào mẫu dự án đích | `T-5078` | `framework/templates/{CLAUDE.md,xt.yaml,AGENTS.md,harness/model-tiers.json}` | 20 | `executor` · `reviewer` | `tests.test_model_tiers tests.test_install` |
| 24 | 0 | Lọc `autoCompactWindow` khỏi bản chép sang đích (D-628) | `T-5080` | `scripts/install.py`, tests | — | `executor` · `reviewer` | `tests.test_install`; mypy |
| 25 | 0 | Đăng ký `PreSkillShellCommand` (cần Claude Code ≥ 2.1.332) | `T-5081` | `.claude/settings.json`, `harness-files.md` | sau #858; cần phiên mới | người/phiên ≥ 2.1.332 · `reviewer-alt` | `tests.test_hook_skill_shell`; xác minh payload thật |
| 26 | 1 | Guard chặn `gh pr create` thiếu `--draft` (cưỡng chế `LOOP-STOP-031`) | `T-5077` | `guard.py` (0 dòng ròng), corpus | 10, 20 | `executor` · `reviewer-alt` | `tests.test_hooks`; vi sai 0 lệnh bị nới |
| 27 | — | Cắt bản 3.37.0 để đích nhận hai luật | `T-5079` | `VERSION`, `CHANGELOG.md`, GO-NO-GO | 20, 23, 24, 28, 8–10 | phiên chính · không | `xt.py release-check` GO |
| 28 | 0 | Giới hạn CPU tổng quát theo số nhân (khay dùng chung), khung và đích (D-629) | `T-5082` | `scripts/xt_cpu_share.py`, `dev-task.sh`, `xt.yaml` + mẫu | 24 | `executor-deep` (opus/medium) · `reviewer-alt` | `tests.test_cpu_share` (bảng 1/2/4/14/64 nhân); hai gate đồng thời không vượt phần dùng được |

**Song song được:** dòng 1–7 với nhau (không chạm tệp nóng; `CHANGELOG.md` rebase khi xung đột); đợt 1 (`guard.py`) với đợt 2 (`xt.py`), mỗi tệp nóng một chủ, nối tiếp trong đợt; dòng 17–19 với đợt 1–2 trừ `T-5059`. **Đường găng:** 2 → 8 → 9 → 10 → 11 (Guard) và 2 → 12 → 13/14/15 (XT). **Hạn đã ghi:** 2026-12-02 (dòng 3, 4), 2026-12-15 (nhóm chấp nhận của bản phát hành), 2026-12-31 (AUD-HAR-572…574), 2027-01-21 (hàng rào guard, D-609, `support_until` gói). Không đặt hạn hoàn tất toàn chương trình; ước lượng lại sau dòng 12.

Các lát sau đó (G12.3 tách miền XT, C15/C16/C21–C24, G05–G11, ADR-0097 P2b…P6) giữ định nghĩa ở §5, §19, §24; chỉ đăng ký task khi dòng 11 và 12 đã merge và có số đo chi phí di chuyển thật của lát đầu.

### 0.6 Việc cần người
- `T-4007`: ruleset tag live, GitHub App phát hành, **bật release immutability** (`v3.36.0` đang `immutable=false`) → sau đó `T-5020`.
- `T-5017`, `T-5018`: mở lại khi chủ dự án thay D-610.
- D-625 là phiên chính tự duyệt để gỡ thế kẹt giữa D-161 và D-623; chủ dự án đổi tuyến (ví dụ nâng trần effort reviewer, hoặc cho reviewer khác nhà cung cấp) thì ghi D-NNN mới trước khi `T-5063` merge.

### 0.7 Điều kiện xong và điều kiện dừng
- Mỗi PR: Gate ở bảng xanh trong hook commit và CI; lớp bắt buộc review có `pr reviewed --clean` ở đúng head theo D-625; `CHANGELOG.md` khi đổi mục/ID/công cụ; task tick kèm số PR.
- Đợt 0 xong khi dòng 1–7 merge. Đợt 1 xong khi baseline parity Guard được chụp và lát đầu merge với `guard.py` giảm dòng. Đợt 2 xong khi `LINE_CAPS` của `xt.py` hạ và `T-5010` ghi được cost lượt đỏ.
- Dừng một lát khi: cùng lỗi đỏ 3 lần; phải nới trần dòng/byte (cần ADR riêng); không có reviewer hợp lệ theo D-625 (ghi `--inconclusive`, `loop defer`, làm lát độc lập kế).
- Không tuyên bố: tiết kiệm token, chất lượng review tương đương, hay sẵn sàng production khi chưa có số đo cùng bộ tác vụ.

### 0.8 Kết quả rà của Revision 4
- **Đã kiểm, đúng (ở `be1bf6b4`):** số dòng và trần hai tệp lớn; bốn lỗi §3 còn lại như bảng §0.2; frontmatter reviewer; logic `review_capability_error`; trạng thái `T-3995` xong, `T-3996`, `T-3987…3990`, `T-5009…5011`, `T-5019`, `T-5020`, `T-5040`, `T-5041`, `T-4007` chưa làm; AUD-HAR-541/572/573 mở, 542 đã sửa, AUD-ARCH-019 mở; nội dung ADR-0090/0091/0093/0094/0099 khớp điều tài liệu gán; D-542, D-558, D-559, D-605, D-610, D-620, D-624 có trong sổ; cụm shard/weights 7 hàm (`xt.py:2915-3035`, cộng `cmd_test_weights` `:3018-3047`); `test-select`, `context`, `plan waves --handoff`, `blueprint-status` có; chỉ có gói `web-api-ts`; registry 6 đích (5 bản 3.34.0, 1 bản 3.29.0); `VERSION` 3.36.0.
- **Chưa kiểm:** mọi nguồn web; số coupling (407 dòng patch / 55 tệp), corpus 4.106 ca, thời gian compile, bao đóng 15.714 dòng; thứ tự ưu tiên effort của Claude Code; ngày cưỡng chế `pull_request_target` trên GitHub Docs (`PLAN-3.13-next-level.md:11` ghi 2026-11-02, `PROGRESS.md` ghi 2026-12-02); ma trận §27; liên kết §37. Không chạy Gate hay CI nào cho các số đo cũ.
- **Nghi ngờ chưa tái hiện:** race `HEAD_SHA` ở §29.2 (có vẻ vô hại: dấu review gắn head cũ không mở được head mới, `cancel-in-progress: true`).

### 0.9 Ghi chú đầu tệp của ba revision trước (lịch sử; hết hiệu lực về quyền ưu tiên)

> **Bản gốc (2026-11-26): đề xuất, chưa phải PLAN.** Bản chuyển từ PDF "Kế hoạch nâng cấp hợp nhất" (40 trang, đối chiếu mã ở commit `02480424`). Chưa có task ID đăng ký, chưa sửa mã. Khi triển khai phải ánh xạ vào PLAN đang có (không lập kế hoạch cạnh tranh), giữ task đã xong, và ghi rõ ADR bị thay thế. **D-610** (hoãn nâng dự án đích) vẫn hiệu lực.
>
> Bản chuyển này gồm đủ 40 trang PDF (cô đọng; số đo giữ nguyên), §11 kiểm chứng một bài đăng về harness ba agent của Anthropic, và **§12 nghiên cứu lại ở `main` `259ac21c`**: số đo mới, trạng thái năm lỗi và 31 lát, sáu hệ quả PDF chưa nêu, thứ tự Đợt 0 đề xuất. Số ở §2, §3, §8 là của PDF; chỗ nào lệch với `main` thì §12 thắng.

> **Revision 27/11/2026:** bổ sung §14–§25 về X-Code Intelligence, bản đồ mã nguồn theo working tree, độ mới, tách lõi, chính sách reviewer, harness và backlog. Khi có xung đột, §14–§25 ưu tiên hơn §1–§13 (đặc biệt lịch §6/§12.6); giữ G01–G12, Cửa A–E, D-610 và các task/ADR hiện có. Đây vẫn là đề xuất nghiên cứu, chưa phải PLAN, chưa triển khai mã.

> **Revision 3 — 27/11/2026:** §26–37 tái đánh giá toàn khung ở main 045622d, cập nhật delta #849/#850 và PR #847/#851; bổ sung ma trận bằng chứng, P0 trust/review, CI/test, pack/UI, phân phối, registry/app và thứ tự R0–R6 ánh xạ G01–G12. §26–37 thắng về hiện trạng và thứ tự nếu xung đột; không thay D-610/D-623, không đăng ký task hoặc đổi mã.

## 1. Ba quyết định chính
1. **Tách theo trách nhiệm và phụ thuộc.** Một chương trình thống nhất, chia module có hợp đồng rõ; kế thừa ADR-0090/0091/0093, registry, cơ chế quyết định; bảo toàn loader, CLI, bản cài, bộ kiểm.
2. **Reviewer effort tối đa `high`, `maxTurns` 120.** Cả `reviewer` và `reviewer-alt` khai `effort: high`, tuyệt đối không vượt `high`; `maxTurns` 80 → 120. Agent kết thúc sớm khi xong. Giới hạn vòng agent phân biệt với số lần review lại một PR.
3. **Đo và giao hàng theo bằng chứng.** Sửa lỗi đã tái hiện trước baseline; mỗi lát có parity và kiểm bản đã cài; giữ coverage dòng + nhánh 100 %, `mypy --strict`, C901 ≤ 10. Pilot bắt đầu từ một yêu cầu nghiệp vụ mới và một pack hiện có.

## 2. Hiện trạng đo (commit đối chiếu)
| Chỉ tiêu | `xt.py` | `guard.py` |
|---|---|---|
| Dòng vật lý / trần | 23.643 / 23.644 | 24.689 / 24.689 |
| Kích thước nguồn (byte) | 1.268.478 | 1.390.801 |
| Hàm cấp module | 1.300 | 1.421 |
| Coupling test cần rà | 407 dòng match patch / 55 file | 112 `patch.object` / 36 file |

Dòng vật lý tính bằng `len(read_bytes().splitlines())`, giống test ngân sách. Số patch là thống kê hỗ trợ rà soát, không phải lỗi đã chứng minh. Bộ kiểm chọn lọc đã chạy (CPython 3.13.5): 47 test của `test_docs_budget`, `test_python_floor`, `test_guard_profile`, `test_release_assets` đạt — không thay full CI, parity hay coverage của kiến trúc mới.

## 3. Lỗi đã tái hiện, cần xử lý trước khi tách sâu
| Phát hiện | Đưa vào |
|---|---|
| `executor-mech` chưa được CLI nhận (parser trả `SystemExit 2`; bảng vai chỉ có `executor`/`executor-deep`) | G01 |
| Lượt Gate đỏ bị bỏ chi phí (wrapper chỉ gọi `write_cost` khi rc = 0) | G02 (tiếp T-5010 sau T-5009) |
| Ghi file cài đặt có thể bị cụt (tiêm lỗi sau 4 byte làm mất nội dung cũ; hook rỗng bị phân loại kept-own) | G03 / C05 / C17 |
| Release gặp tag có sẵn thoát sớm (exit 0, `GITHUB_OUTPUT` rỗng, chưa kiểm trạng thái release) | G03 |
| Guard core mất ngữ cảnh khi lỗi (`RuntimeError` trong `_rule_decision` với payload merge: core allow/NONE; bash deny/UNPARSED) | Bugfix riêng trước baseline; chưa gán audit ID |

Phạm vi phát hiện Guard: payload `gh pr merge 17` chỉ vào bộ đánh giá trong bộ nhớ, không chạy lệnh merge. Chưa chứng minh trigger tự nhiên ở production; `xt_adapter.decide` có bước đổi tool về mode Bash. PR sửa lỗi phải làm rõ hành vi mong đợi (kèm ca tốt đối chứng và ngoại lệ từng mode) rồi mới chụp baseline cho parity. Thay đổi tăng bảo vệ pre-edit/loader cần quyết định policy riêng; PR move-only không tự đổi allow/ask/deny.

## 4. Chính sách reviewer: effort tối đa `high`
- Nguồn vai (`.claude/agents/reviewer*.md`) và `/review`: effort `high`, `maxTurns: 120`; bỏ chỉ dẫn "effort cao nhất" không giới hạn; reviewer vẫn chỉ đọc, context độc lập.
- Bản sinh theo host: sửa nguồn rồi sinh lại Codex và bản gương `.agents`; kiểm bản cài sạch và nâng cấp cùng nhận chính sách.
- Định tuyến/launch: kiểm effective effort (session, frontmatter, invocation, biến môi trường) trước launch; chặn nếu không áp được trần theo vai. XHIGH/MAX không được thành yêu cầu thực thi, kể cả qua override. Trần không áp cho tác giả/executor/researcher/phiên chính.
- Hiện trạng cần sửa: `reviewer-alt` khai `effort: max` (và bản Codex `model_reasoning_effort = max`); `reviewer` chưa khai effort; `/review`, mô tả agent và ADR-0098 còn dựa vào giả định "reviewer MAX cao hơn người viết cùng bậc". ADR kế tiếp chỉ thay phần lựa chọn effort và định tuyến; giữ lịch sử ADR-0098. Review MAX hợp lệ theo revision cũ vẫn lưu đúng lịch sử, không cho phép lượt mới dùng MAX.

Định tuyến khi trần là `high` (HIGH là trần effort, không chứng nhận reviewer mạnh hơn):
| Tác giả / reviewer | Quyết định |
|---|---|
| Cùng họ model/tier (tier-only): MEDIUM / HIGH | Hợp lệ về effort; còn kiểm phạm vi, độc lập, bằng chứng |
| Cùng họ: HIGH / HIGH hoặc XHIGH / HIGH | Không đủ điều kiện năng lực cao hơn; không ghi clean; không tự nâng reviewer |
| Tác giả bậc thấp / reviewer bậc cao, HIGH | Có thể hợp lệ nếu bậc reviewer nằm trong phạm vi cho phép |
| Khác nhà cung cấp, reviewer ≤ HIGH | Đường độc lập theo chính sách hiện hành; không diễn giải thành ưu thế năng lực |
| Không có reviewer hợp lệ | INCONCLUSIVE hoặc thiếu reviewer; defer phần cần review, làm tiếp việc độc lập |

Mỗi lượt review ghi repo, head, phạm vi diff, tác giả, reviewer, effort requested/effective, revision chính sách và nguồn setting (mặc định/host/override); không rõ → `unknown`. Kiểm cặp hợp lệ trước khi giao review. Ma trận nghiệm thu: tên model và đường tier-only; default giải quyết tường minh; override XHIGH/MAX bị từ chối trước launch; HIGH/HIGH và HIGH/XHIGH bị từ chối clean; không route nào ghi INCONCLUSIVE được; event noncompliant không mở gate sạch. Đo chất lượng sau thay đổi bằng cùng bộ diff có lỗi gieo + đối chứng (lỗi bỏ sót, chặn oan, thời gian, chi phí, chuyển tuyến); chưa có số thì chưa kết luận tiết kiệm hay chất lượng tương đương.

### 4.1 `maxTurns` 80 → 120: giữ từng loại ngân sách riêng
`maxTurns: 120` là trần lượt agent trong **một lần chạy**, không phải 120 lần review mỗi PR; agent được kết thúc sớm khi xong phạm vi.
| Giới hạn | Thay đổi |
|---|---|
| `maxTurns` hai reviewer | 80 → 120; kiểm giá trị nguồn, cấu hình hiệu lực, hành vi dừng của host |
| `REVIEW_ROUNDS = 1` | Giữ; `review_window`, luồng debt/rethink không đổi |
| `max_rethink` mặc định 1 | Độc lập với lượt agent; không tăng, không bỏ trần |
| Poll, timeout, retry, song song | Không lấy 120 làm số poll/retry/reviewer đồng thời |

Nguồn chung chưa bảo đảm các host giống nhau: `agent_toml` hiện chỉ đưa name, description, effort hợp lệ và thân hướng dẫn sang Codex (thêm model khi bật), **không map `maxTurns`**. Test frontmatter chứa `maxTurns: 120` chỉ chứng minh đọc được nguồn. Xác minh schema từng host trước khi map; không tự thêm khoá TOML chưa xác nhận; chưa có trần tương đương thì báo khoảng trống trong bằng chứng cài. Hết lượt → kết quả có thể chưa đủ; ghi định danh lần chạy, head, phần đã rà/chưa rà, dấu tiếp tục; chưa đủ bằng chứng → INCONCLUSIVE. Nghiệm thu: assertion hai vai `maxTurns = 120`, `effort = high`; giữ trần `executor-mech` riêng; kiểm dừng sớm và biên 119/120/121, hết lượt có partial, resume.

## 4A. Tách lõi an toàn (trang 8–16 của PDF)

**Kiến trúc đích: modular monolith.** XT là CLI điều phối, Guard là lớp đánh giá/bảo vệ; tách miền trong cùng bundle để đổi từng lát và quay lại được. Chưa có bằng chứng cần microservice, plugin tải động, ngôn ngữ policy mới hay vector DB. Bốn khối trách nhiệm: XT entrypoint/đăng ký command → miền XT (loop, PR, doctor, scan, release) → hợp đồng và dữ kiện (kiểu, policy, state, evidence) ↔ ports/adapter (Git, file, clock, process, events) ← miền Guard (Edit, MCP, commit, Bash/SCC) ← Guard đầu vào theo mode (loader nguồn tin cậy). Đây là quan hệ trách nhiệm đích, không phải sơ đồ import đã có. Sáu lớp logic của bản gốc (dữ kiện → năng lực → quyết định → thực thi → kiểm chứng → phát hành/phản hồi) là trách nhiệm, không phải sáu service; module `xt_decision`/`xt_design`/`xt_agent_roles`/`xt_evidence`/`xt_metrics` chỉ tạo khi có lát dùng thật. **Chống chia file hình thức:** không chuyển nguyên khối sang `legacy_core.py`, `guard_core.py`, `common.py`.

**Tách `xt.py` (kế thừa ADR-0090; `build_parser` 641 dòng):**
| Lát ứng viên | Số đo tĩnh và hướng |
|---|---|
| Shard/weights | 7 hàm, 121 dòng, 3 tham chiếu ngoài → `xt_shard` |
| Chọn test | 21 hàm, 241 dòng, 1 phụ thuộc ngoài; giữ fallback chạy toàn suite |
| CSS contrast | 24 hàm, 269 dòng, không gọi ra ngoài cụm; giữ CLI |
| Doctor | tách checker runtime/cấu hình/bản cài/tổng hợp từng lát |
| Loop và PR | PLAN, state, evidence, ledger, runner; PR: dữ liệu, quyết định merge, review ledger, handlers |
| Release/compose | đưa vào module có sẵn; giữ contract phát hành, carry-forward |

Giữ Core(Protocol) làm cầu; bắt đầu từ cụm thấp coupling; `LOOP_HANDLERS` tĩnh đã có, chưa cần plugin discovery; parser register theo miền ở giai đoạn sau, giữ `main(argv)`. Autonomy benchmark và perf trial là miền riêng (blob XT theo ADR-0091). Một chủ sở hữu tích hợp `xt.py`; entrypoint < 150 dòng là đích dài hạn.

**Hợp đồng lõi khi di chuyển:** state/quyền sở hữu (lock, revision/CAS, atomic write, một nơi chuyển trạng thái) · PLAN/evidence (dependency, Gate, task, head, digest liên kết đúng) · ledger/attempt (schema, chống đếm trùng; G02 thêm attempt identity, nối T-5010) · CLI/caller (flags, defaults, JSON, mã thoát, stdout/stderr, import). Patch phải chuyển tới **nơi lookup thật** (407 dòng patch XT/55 file): re-export giữ tên import nhưng thân hàm đã chuyển đọc globals ở module mới → test xanh giả. `SCRIPT_DIR`, cache, dispatch dict, `PR_READ_HOST` ContextVar, `sys.path`, `sys.modules` cần chủ sở hữu. PR extraction không trộn sửa hành vi; characterization test ghi hành vi hiện có nhưng không coi lỗi cũ là đặc tả.

**Tách Guard theo bao đóng phụ thuộc** (Decision, CodedReason, `reason_code`, `policy_action`, `apply_policy`, POLICY đã có; chuyển luật sang YAML chưa đáng chi phí kiểm lại shell parser). Đo tại `02480424`:
| Hạt giống | Định nghĩa | Span dòng |
|---|---|---|
| `edit_decision` | 61 | 629 |
| `mcp_decision` | 34 | 330 |
| `commit_msg_problem` | 5 | 45 |
| `decide` + `apply_policy` | 6 | 58 |
| Nhóm git/gh/push | 534 | 6.061 |
| `bash_decision` | 1.402 | 15.714 |

Các cụm chồng lấn, không cộng thành số dòng xoá được. Công cụ repo cho nhóm từ xa 498 định nghĩa (thấp hơn 36 do chưa lần qua bảng như `GIT_RULES`, `FILE_WRITERS`); 13 nhóm phụ thuộc vòng, lớn nhất 21 định nghĩa quanh `bash_decision` và vòng scan — giữ cụm này trong lượt đầu. Lát ưu tiên: shared helpers + Edit/Write (bao đóng nhỏ; helper dùng chung với Bash một nơi định nghĩa; giữ identity class và ContextVar mỗi bundle), rồi MCP, commit-msg, cuối cùng Bash. T-3995 xong; T-3996, T-3987…3990 tiếp tục. C14 cần ADR bổ sung sửa ADR-0090 §2, ADR-0093 §1-2 và D-542. Mức 376 → 54 ms của C14 là nguyên mẫu lịch sử, chưa benchmark lại.

**Nạp Guard và bảo vệ gói cài.** Companion đọc từ source bytes, tên trong allowlist cố định, đường dẫn tính từ bundle đã chọn; không dò plugin qua cwd/PYTHONPATH; mỗi instance một namespace riêng. Kiểm năm tuyến (`_lib.sh::py_run`, `PY_LOADER`, `xt_adapter.load_guard`, `xt._load_guard`, `BenchEnv.module`) với thiếu file, lỗi cú pháp, nạp dở, pyc đặt sẵn, hai phiên bản cùng tiến trình. Ma trận lỗi hiện hữu:
| Tình huống | Hành vi hiện tại |
|---|---|
| Bash lỗi runtime thường | Fallback rỗng: fail-open (ADR-0002) |
| Bash lỗi runtime khi kiểm merge/gh api | UNPARSED: mặc định deny; strict giữ ask |
| Pre-bash không nạp được Guard | Mặc định deny; strict ask; có ngoại lệ xem/khôi phục |
| Pre-edit không nạp được Guard | Shell thoát 0: fail-open |
| Adapter nạp Guard ném lỗi | Trả BROKEN_GUARD theo giao thức host |

Đổi pre-edit sang chặn khi hỏng là **đề xuất tăng bảo vệ**, cần quyết định và đường khôi phục riêng. Theo CPython: `-B` tắt ghi pyc, `-I` không loại toàn bộ site-packages, `-S` tắt site; hoàn tất AUD-HAR-572/573 bằng chính sách nạp thống nhất, kiểm `-I -S -B` trên runtime hỗ trợ và bộ đo coverage. Companion là một phần hàng rào: manifest khai dependency và phiên bản; doctor phát hiện thiếu/rỗng/cụt/trộn phiên bản.

**Chứng minh tương thích:** so raw decision và kết quả sau policy ở cả mặc định lẫn strict trên bốn nhóm — quyết định (decision, reason, code, confidence, missing, thứ tự ưu tiên), cổng thực thi (`commit`, `no_verify`, `push_no_verify`, `commit_dir`, `commit_alone`), giao thức (thứ tự NUL, JSON, exit code, stdout/stderr), tác động (IO, log, số sự kiện, hành động chỉ một lần). Corpus Guard 4.106 ca là nền so hai phiên bản, không phải bằng chứng phủ mọi hành vi; giữ `autonomy-bench`, `guard_fuzz`, `green_shell`, `green_gh`, `signoff2_scripts`, `audit_dot4_har`. Shadow dùng snapshot filesystem/Git/cấu hình, namespace/cache/ContextVar tách, recorder/replayer IO; không chạy lại action. Rà 112 `patch.object(guard, …)`/36 file; kiểm reset ContextVar trong `finally`. Không hạ coverage về 90 % để dễ tách.

**Hiệu năng gắn đường chạy.** Đo compile nguồn (CPython 3.13.5, Linux x86_64): XT trung vị 358,79 ms (334,11–450,79), Guard 259,00 ms (236,35–282,53) — không gồm khởi động process, đọc file, Git hay quyết định policy; không suy ra p95 hook. Bộ benchmark trước mỗi lát: CLI phổ biến (help, validate, doctor, test-select, loop/pr đọc; cold/warm) · Guard theo mode (Bash đơn/đệ quy, merge/API, Edit/Write, MCP, commit-msg) · tích hợp đã cài (checkout, `.xtemplates`, artifact; số module/byte nạp) · CI và agent (critical path, runner-minutes, time-to-green, token mọi attempt). p50/p95 đủ mẫu, so A/B xen kẽ cùng fixture; ngưỡng regression khoá sau baseline.

**Bản cài và phục hồi là một phần lát tách.** `registered_hooks()` suy companion từ settings và chuỗi shell, không tự tìm mọi dependency Python mới; mỗi lát cập nhật manifest, hash, version, typecheck, coverage, test-select. Ca bắt buộc: checkout/`.xtemplates` (fresh install, upgrade, downgrade, CWD khác, path có dấu/khoảng trắng, thiếu module) · artifact `.pyz`/tarball (chạy entry point thật, không dựa `sys.path` checkout) · perf trial một blob · tệp người dùng đã sửa (owned/customized/deleted, `.xtemplates-new`) · gián đoạn/cạnh tranh (mid-write, thiếu companion, mixed version, hai tiến trình). C05: file tạm cùng filesystem, đủ nội dung và quyền rồi `os.replace`; fsync chỉ khi cần bảo đảm qua mất điện; replace không phải giao dịch cả bundle. Nghiên cứu trước ghi 15/15 gián đoạn hội tụ khi chạy lại nhưng còn ca ghi cụt → atomic từng file + kiểm toàn vẹn + repair; không dựng transaction framework khi chưa có bằng chứng.

**Giảm ngữ cảnh đi cùng độ mới.** Module map và symbol index từ AST (gắn SHA, owner, entry point, callers, tests); BLUEPRINT/SPEC projection phát hiện drift theo dependency; gói giao việc (mục tiêu, constraint, file owner, base/head, decision revision, ca nghiệm thu, unknown); handoff sau compaction (việc xong, diff dở, test đã/chưa chạy, lỗi mở, việc kế, link log); đầu ra lỗi ≤ 8.000 ký tự + full log (C02). C04 cửa sổ 400K là thí nghiệm theo host/model. Nghiệm thu: cùng task/head/fixture, context giảm mà tỷ lệ hoàn thành không giảm, không tăng lượt sửa.

## 4B. Sản phẩm, agent và giao hàng (trang 17–26 của PDF)

**Bối cảnh trước giải pháp.** Mỗi fact có ID, giá trị, phạm vi, nguồn, thời điểm, trạng thái `confirmed`/`observed`/`assumed`/`unknown`; mâu thuẫn lưu thành conflict có tham chiếu. Sáu trục: software profile · kiến trúc và dữ liệu · pack triển khai · design profile · vai agent và model · chính sách thực thi. Sản phẩm đang chạy ưu tiên tận dụng stack/design system; không suy "có AI" thành agentic-system hay "có màn hình điện thoại" thành mobile-app. Chỉ hỏi người khi đáp án đổi lựa chọn đáng kể hoặc dữ kiện chỉ chủ sản phẩm có.

**Chọn phương án có đủ bằng chứng.** Mỗi candidate một hàng cho từng hard constraint: pass/fail/unknown + nguồn + bằng chứng đúng phiên bản; điểm thẩm mỹ/tốc độ/chi phí không bù được vi phạm bắt buộc. Trạng thái: `needs_resolution` · `needs_evidence` · `no_fit` · `selected_provisional` · `validated_for_scope` · `superseded`. Lỗi đọc registry hay danh mục chưa phủ không được gọi là `no_fit`. Đề xuất kiểm độ nhạy trọng số và lưu điều kiện xét lại (phản chứng).

**Bảy hợp đồng dữ liệu logic** (đề xuất, chưa phải bảy file): CONTEXT · PRODUCT-SPEC · CAPABILITY-REGISTRY · DECISION · DECISION.lock · VALIDATION · RUN-EVENTS. JSON Schema kiểm cấu trúc; validator ngữ nghĩa kiểm tham chiếu chéo; giữ DESIGN-EVIDENCE schema 1; VALIDATION nối quyết định với build. Digest trên biểu diễn chuẩn hoá; đổi nghiệp vụ/quyền/candidate làm mất hiệu lực đúng phần phụ thuộc. Schema và policy cho hook đóng gói cùng phiên bản, không tải từ mạng.

**UI/UX theo tác vụ.** Design profile sáu trục (họ trải nghiệm, kiến trúc thông tin, kiểu tương tác, mật độ, ngôn ngữ hình ảnh, chuyển động). Sáu họ trải nghiệm (danh mục để thử, không phải pack có sẵn): vận hành nghiệp vụ · hiện trường · khám phá dữ liệu · nội dung/chuyển đổi · mua hàng/giao dịch · workspace có agent. Quyết định lớn dựng 2–3 phương án trên cùng tác vụ và dữ liệu; review trên UI render với tên dài, số tiền, chữ có dấu, dữ liệu thật. UI sinh động chỉ dựng từ catalog component và action contract đã kiểm.

**Kiểm UI, a11y và outcome** — năm lớp kết luận khác nhau: hồ sơ · candidate · kỹ thuật UI · thử tác vụ · theo dõi tại đích. WCAG 2.2 AA là mục tiêu cho web pilot: reflow 320 CSS px, phóng chữ 200 %, focus không bị che, kéo có cách thay thế, target 24×24 CSS px tối thiểu có ngoại lệ (44×44 không phải yêu cầu AA). DTCG 2025.10 là định dạng của Community Group, không phải W3C Recommendation. Catalog component cần trạng thái empty, loading, lỗi, mất quyền, thành công, gián đoạn, tiếp tục; tôn trọng giảm chuyển động. Web Vitals tham chiếu LCP ≤ 2,5 s, INP ≤ 200 ms, CLS ≤ 0,1 tại p75; báo lab và field riêng; thiếu dữ liệu → `not_measured`. Mọi báo cáo dùng `pass`/`fail`/`not_tested`/`not_applicable` có lý do.

**Điều phối agent.** Registry vai nối tên agent, loại việc, năng lực, quyền, CLI và dữ liệu thực thi; vai công bố phải chạy được qua CLI thực. Sáu trách nhiệm logic (điều phối · phân tích/thiết kế · tác giả nghiệm thu · thực thi · review/kiểm chứng · giao hàng/vận hành) có thể cùng một agent đảm nhiệm, nhưng nghiệm thu và review giữ độc lập. `executor-mech` đỏ một lần phải chuyển cấp đúng quy định. **Bộ đánh giá agent thật:** 24–36 tình huống đã review có đáp án, một phần holdout không dùng để chỉnh prompt (brief mơ hồ, dữ kiện tra được trong repo, pack không hỗ trợ, nguồn mâu thuẫn, SPEC đổi giữa chừng, compaction, nối phiên, hành động vượt quyền); chạy lặp, báo thành công trên tổng trials; phân biệt "ít nhất một lần" với "nhất quán"; code grader cho điều kiện tất định, model grader cho phần mở cần hiệu chuẩn với người.

**Nghiệm thu độc lập và ca sai critical.** Giữ tác giả nghiệm thu độc lập, khoá digest, đỏ trước code ứng viên. Mỗi quy tắc critical nối nguồn yêu cầu → SPEC → test hành vi → ca sai cố ý đã review → kết quả trên artifact; quyền, tenant, gửi lại an toàn, đồng thời, biên thời gian, tiền kiểm khi liên quan. Bộ thử phải bắt toàn bộ tập sai critical đã chốt — không bảo đảm phát hiện mọi lỗi.

**Sổ sự kiện và chi phí.** Producer: requirement, task_green, pr, review, merged, artefact, deployed, incident, cost; gắn ID lát/run/attempt/event. Lần thành công, thất bại, huỷ, review bị bác, retry đều ghi khi có usage; thiếu usage giữ `unknown`, không thành 0. Chỉ số: hoàn thành đúng tác vụ · lead time (tách làm và chờ) · chi phí hoàn thành · sửa lại và lỗi lọt · chất lượng lựa chọn · phục hồi. Ingestion idempotent. OpenTelemetry GenAI conventions còn Development → ghim phiên bản; không capture prompt/output mặc định; ledger cost cần đường ghi đầy đủ riêng vì sampling bỏ dữ liệu.

**Cài đặt và phát hành chịu gián đoạn.** Release có trạng thái rõ (tag đã tạo, asset đã tải và xác minh, đã công bố); chạy lại gặp tag có sẵn phải đối chiếu commit và trạng thái. Chuỗi bằng chứng: source → build (receipt) → release (digest khớp asset; thiếu asset = incomplete) → cài đặt (manifest module, hash, quyền) → phục vụ (receipt tại đích) → chạy lại (tiếp tục đúng bytes hoặc lỗi rõ). Quan sát 26/11: `v3.36.0` có `immutable=false`. Registry đích cần source SHA, phiên bản, pack, môi trường, release, thời điểm, trạng thái `current`/`deferred`/`unknown`/`unsupported`.

**Pilot trọn vòng.** Một yêu cầu nghiệp vụ mới trên Hotel Manager (luồng lọc tầng chỉ là đối chứng): brief, baseline, context, lựa chọn, suite độc lập, triển khai, thử UI, phản hồi, release, kiểm tại đích, theo dõi; không dựng trial người dùng hay receipt production giả; người thử dùng mã ẩn danh. Mức bộ chọn mới: shadow → tự chọn hẹp → canary → mở rộng; không giảm tự hành L3 đang được phép. Diễn tập phục hồi A→B gồm dữ liệu phát sinh khi B chạy; chốt RPO/RTO theo sản phẩm; rollback code không tự phục hồi dữ liệu.

## 5. Backlog hợp nhất G01–G12
| Gói | Đầu ra | Điều kiện nghiệm thu chính |
|---|---|---|
| G01 Điều phối agent | Registry vai thống nhất, `executor-mech` qua CLI + escalation, reviewer high/120, mapping host/route | Parser/dispatch đúng; override/env/fallback không vượt high; host chưa áp được trần → pending/unsupported; hết lượt mà chưa đủ bằng chứng không khai sạch |
| G02 Sự kiện và chi phí | 9 loại sự kiện, attempt ID, cost lượt đỏ, coverage nguồn, export xuyên phiên/worktree | Tiếp T-5009/5010/5011; chống trùng; thiếu nguồn giữ null + lý do |
| G03 Cài và phát hành | Atomic write, doctor hook rỗng, bundle integrity, release retry theo identity, bằng chứng admin tách riêng | Fault cases cài/upgrade phục hồi; tag có sẵn không giả success; T-5020 chỉ xong khi diễn tập thật trong quyền đã giao |
| G04 Pilot và baseline | Một feature nghiệp vụ mới, một sản phẩm/pack hiện có; baseline riêng | Yêu cầu có nguồn; constraints, tiêu chí, phạm vi khoá trước code |
| G05 Quyết định | Context/constraint snapshot, schema, decision/lock, invalidation | Candidate thiếu bằng chứng không bị chọn; đổi input → stale đúng dependency |
| G06 Registry tối thiểu | Tổ hợp pack/host/profile/data đã kiểm phục vụ pilot | Mỗi tuyên bố supported có bằng chứng đúng tổ hợp/version; không tải plugin động từ tên trong cấu hình |
| G07 Thiết kế trải nghiệm | Profile theo tác vụ/vai trò, token ngữ nghĩa, prototype dữ liệu thật, DESIGN-EVIDENCE schema 1 | Phép đo trình duyệt đúng build; T-5012/5013 mở khi đủ bằng chứng |
| G08 Nghiệm thu độc lập | Suite từ SPEC công khai, manifest requirement, ca sai critical | Bắt toàn bộ tập sai đã khoá; ca đúng không bị chặn oan; không sửa tiêu chí để hợp kết quả |
| G09 Tích hợp tại nơi dùng | Factory/compose/stage nối contract; artifact/bản cài sạch | Không dựa source checkout; Python floor, loader matrix đạt; packaging/monkeypatch không làm test xanh giả |
| G10 Agent eval và pilot | Bộ 24–36 tình huống khởi đầu, holdout, trials lặp | Agent/model/tool thật, production receipts thật; thiếu quyền/trial/recovery vẫn pending |
| G11 Mở rộng | Canary theo digest/receipt, registry năng lực | D-610 còn hiệu lực thì chưa nâng repo đích; T-5038 đã bỏ, không đưa lại |
| G12 Lõi và ngữ cảnh | Inventory, compatibility, XT/Guard extraction, bundle, context freshness, retire (G12.0–G12.7) | Mỗi lát hạ cap và giảm coupling có số đo; giữ 100 % line+branch, mypy strict, C901 ≤ 10, Guard source-only |

Thứ tự ưu tiên: sửa tính đúng và khoảng trống cấu hình của G01–G03; G04–G06 triển khai phần contract song song khi owner không trùng. Giữ việc đã có nhà: T-5010 chứa lỗi cost lượt đỏ; T-5016 đã đặt cap dòng — không mở task trùng. Phát hiện Guard core chỉ cấp ID khi đăng ký vào audit thật.

Điểm nối: G07 có thể dựng prototype song song G08 sau khi yêu cầu và hợp đồng công khai ổn định; code nghiệp vụ chỉ triển khai sau khi suite độc lập đã được review và khoá. G12 không là lý do trì hoãn pilot.

### G12 — các lát lõi
- **G12.0 Inventory/baseline:** danh sách symbol, imports, tham chiếu qua hàm, bảng callable/constants/type alias; SCC và caller ngoài cụm; ghi riêng dynamic import, exec, monkeypatch, callback; chốt SHA, công cụ đếm và workload đo.
- **G12.1 Tương thích:** khoá command args/help/exit/stdout/stderr, hook fields/NUL order, schema, import surface; phân biệt API công khai với private helper bị test patch. Quyết định L05 về XT/blob/bytecode + ADR bổ sung cho C14.
- **G12.2 Leaf và port I/O:** cụm nhỏ, ít cạnh ngoài; giữ Core(Protocol) chuyển tiếp rồi thu hẹp; port clock/Git/files/process/events có ngữ nghĩa lỗi, timeout, quyền.
- **G12.3 Miền XT:** tách C15, doctor, state/lock, PLAN/dependency, evidence, ledger/cost, runner, GitHub adapter, quyết định thuần, sổ review, command; parser/register CLI đi sau; facade cũ vẫn hoạt động.
- **G12.4 Guard:** sửa riêng lỗi fallback core; Decision/CodedReason nhỏ; eager-load đủ closure; MCP/commit-msg tiếp theo; vòng scan Bash giữ cùng cụm rồi mới tách theo SCC.
- **G12.5 Loader và ma trận bản cài:** `_lib.sh::py_run`, `guard.PY_LOADER`, `xt_adapter.load_guard`, `xt._load_guard`, `BenchEnv.module`; allowlist cố định, source-only; kiểm thiếu module, pyc giả, hai bản chung process, CWD khác.
- **G12.6 Context đúng miền/revision:** module map, lấy thông tin theo ID và dependency; handoff chứa công việc, constraint, version, phần chưa kiểm; đo token và tỷ lệ hoàn thành trên cùng task.
- **G12.7 Thu hồi đường cũ:** chỉ bỏ shim/stub `merge-gate.yml` khi consumer, bản cài, công cụ đo đã chuyển; hạ ngân sách dòng/byte sau extraction; kiểm SCC, fan-in/out.

Bằng chứng đóng mỗi lát: manifest chuyển symbol; delta trước/sau (LOC/byte, coupling, module nạp, test + benchmark cùng fixture); khả năng đảo (commit độc lập, artifact trước khôi phục được, không lẫn delta policy không tương thích). Mục tiêu facade < 100–150 dòng là đích dài hạn, không phải điều kiện đóng.

Không nhập nhầm chính sách lỗi: pre-edit hiện có đường load lỗi cho qua; Bash thường và merge/API khác nhau — sửa hành vi đó phải là thay đổi policy có nghiệm thu riêng.

## 6. Thứ tự triển khai và Cửa A–E

> **Revision 4:** bảng đợt dưới đây hết hiệu lực về thứ tự — lịch duy nhất ở §0.5. Định nghĩa Cửa A–E còn dùng.
| Đợt | Đi trước | Song song được |
|---|---|---|
| 0 Tính đúng và cấu hình | G01 high/120, mech; G02 cost; bugfix core; baseline và atomic file | G04 brief/baseline; G05 contract; inventory, fixtures |
| 1 Lát module đầu | G12.1/2, L05; C14 bổ sung ADR; loader/protection/install cùng lát | XT và Guard ở path owner riêng; registry, UX prototype, suite độc lập |
| 2 Tích hợp pilot | G09 từ bản cài; G05–G08 nhất quán; ledger và bằng chứng release | Agent eval, test UI, recovery trên môi trường được phép |
| 3 Outcome và mở rộng | G10 đủ dữ liệu thật; sau đó G11 theo D-610 | G12 tiếp tục ratchet/context/retire; không trì hoãn pilot vì archive |

Dependency kỹ thuật: L01 → L02; L04 → C03; L05 → C15/C22; C04 đo đạt → C20. C14 cần ADR, closure, loader, fence; C15 giải phóng capacity cho C16/C17. C08 cùng L01 đo lại trước xét C21. Mọi module đưa vào artifact đi qua G03 fault cases và G09 installed-copy.

| Cửa | Điều kiện đóng |
|---|---|
| A Máy thực thi và đo | G01–G03 đạt phần máy làm được; giới hạn live/admin ghi đúng, không giả đã hoàn tất |
| B Quyết định có căn cứ | G04–G08 nhất quán; thiếu/mâu thuẫn không bị ép chọn; acceptance đã khoá |
| C Tích hợp | G09 đạt ở bản cài/artifact; checkout xanh chưa đủ |
| D Pilot đầy đủ | G10 đạt toàn scope đăng ký: task người dùng, bản tại đích, diễn tập phục hồi |
| E Mở rộng | G11 canary đúng host đã hỗ trợ và quyền hiện hành; host mới cần chứng nhận riêng |

Đợt bắt đầu có thể giao ngay: PR cấu hình review + route/host contract; PR lỗi core; PR cost đã có task; PR atomic write/doctor; chia quyền sở hữu file rõ (nhiều việc cùng chạm XT/install); sửa quyết định và test trước khi tách sâu, rồi lấy một lát ít coupling để đo chi phí migration thực.

## 7. Đo hiệu quả và rủi ro
Trục đo: tính đúng (parity corpus khoá, bugfix có delta riêng) · cấu trúc (cap XT/Guard giảm từng lát, không thêm chu kỳ import) · chất lượng mã (giữ Gate hiện có) · review (hai role high tối đa + 120 lượt; partial/hết lượt khi thiếu bằng chứng ≠ APPROVE) · hiệu năng (p50/p95 cold/warm theo mode và bản cài; budget khoá trước PR) · CI/phát triển (critical path, time-to-green, runner-minutes) · chi phí agent (cost mọi attempt, token/thời gian trên một thay đổi được nghiệm thu) · outcome sản phẩm (hoàn thành tác vụ, thời gian, lỗi, trợ giúp, accessibility, field performance).

Rủi ro chính và biện pháp: chặn oan (parity gồm cả ca cho phép) · test xanh giả (kiểm nơi lookup của mock) · mixed bundle (manifest/integrity + fault tests) · chi phí điều phối (chỉ song song khi task có owner độc lập, so tổng token/thời gian) · thiếu bằng chứng (để unknown/pending) · rò ngữ cảnh (log tối thiểu, gắn revision) · policy tự biến đổi (lịch sử chỉ đề nghị sửa có version/review) · nợ kiến trúc chuyển chỗ (đo tổng coupling) · `maxTurns` tăng (không tự bảo đảm chất lượng; đo mọi attempt, dừng sớm khi xong). Để sau: dynamic plugin, microservice, DSL luật, vector DB, học xếp hạng tự động, installer journal — chỉ mở lại khi có nhu cầu đo được.

## 8. Ánh xạ 31 lát nghiên cứu hiện có
Dấu task trong PLAN là nguồn trạng thái; số đo trong nghiên cứu [framework-optimization](2026-11-26-framework-optimization.md) là dữ liệu lịch sử/nguyên mẫu, đo lại ở HEAD trước khi áp dụng.
| Lát | Gói | Ghi chú |
|---|---|---|
| L00 / T-5032 | G04, G12.0 | giữ 10 hướng; bổ sung mốc SHA, loại bằng chứng, phép tái hiện |
| L01 / T-5033 | G12, G02 | phân hoạch fuzz; giữ coverage và tên consumer cần |
| L02 | G12 | trọng số/tripwire sau L01; đo job chậm nhất, headroom thật |
| L03 / T-5034 | G09, G12 | ánh xạ verify-render; fallback bảo thủ |
| L04 / T-5035 | G01, G03 | kiểu settings đã biết; mở rộng kiểm high/maxTurns theo schema và host |
| L05 | G12.1/3 | ADR XT split/bytecode; perf trial một blob; Guard source-only |
| L06 / T-5036 | G11 | X-Scanner giữ ngoại lệ đến 21/01/2027; X-Agents rời registry theo D-610 |
| C01 / T-5037 | G12, G04 | check-links đúng worktree; fixture tự dựng |
| C02 | G02, G12.6 | excerpt lỗi ≤ 8.000 ký tự + pointer full log |
| C03 | G01, G03 | `PreSkillShellCommand`/depth theo host đã hỗ trợ; phụ thuộc L04 |
| C04 | G01/2, G12.6 | 400K là trial; kiểm effective config và chất lượng trước C20 |
| C05 | G03 | atomic write bảy điểm và hook rỗng; fault suite |
| C06 | G03, G08 | tag glob: đối chiếu trạng thái HEAD trước; nếu còn khoảng trống, oracle trước code. **Không mở lại mù**: một số phát hiện tag/glob đã có cập nhật sau đó (AUD-HAR-541/542) |
| C07 | G05, G12.6 | compose BLUEPRINT, kiểm 17 MUST; freshness theo dependency |
| C08 | G02, G12 | bỏ bước test-main dư trên push; required checks và nhánh PR vẫn đúng |
| C09 | G12 | prefilter PostToolFailure; đo hit rate, overhead |
| C10 | G12.3 | doctor tránh compile/lặp harness check |
| C11 | G01, G02 | handoff/log và lệnh chờ |
| C12 | G01, G08 | review bản sửa ở head theo scope; effort high/maxTurns 120 là cấu hình agent riêng |
| C13 | G12.6 | blueprint-status và truy xuất bằng ID |
| C14 | G12.1/4/5 | Edit closure + ADR sửa thứ tự + loader/fence/install/parity trong một lát đủ dùng |
| C15 | G12.3/5 | scan sang `xt_scan.py` theo L05; giữ blob trial hoặc nâng hợp đồng trước; hạ cap |
| C16 | G09, G12 | test-select/weights theo mapping mới |
| C17 | G03, G12 | doctor phát hiện hook rỗng; context bytes tính tệp tracked |
| C18 | G03, G09 | installer bảo toàn ý định xóa owned file; test upgrade/customized/conflict |
| C19 | G03, G11 | upgrade bot giữ merge thủ công; chưa chạy nâng đích dưới D-610 |
| C20 | G09, G11 | settings merge chỉ sau C04 có bằng chứng; không áp 400K cho mọi host/model |
| C21 | G12 | hợp CI test-main vào compat chỉ khi đo sau L01/C08 còn lợi |
| C22 | G12 | bytecode test/XT theo L05; không đổi trust policy Guard theo suy diễn |
| C23 | G12.6/7 | archive audit/PLAN đã đóng; giữ ID, link, truy vết quyết định |
| C24 | G12.7 | bỏ stub merge-gate sau khi hết consumer và thời gian chuyển |

T-5038 (canary X-Company) đã bỏ theo D-610; phương án nâng đích giữ làm tài liệu cho đợt sau. T-5018 có nội dung rollout cũ cũng phải được diễn giải cùng quyết định hoãn.

## 9. Phương pháp và giới hạn kiểm chứng
Đã đọc PDF gốc 40 trang, mã ở `02480424`, AGENTS/ADR/PLAN liên quan, nghiên cứu 31 lát, tests, đường cài/phát hành. Nhận định cấu trúc dùng AST/symbol table, mở rộng qua assignment, bảng callable, alias; không chứng minh mọi dynamic reference.

Kiểm thử chọn lọc: `python3.13 -m unittest tests.test_docs_budget tests.test_python_floor tests.test_guard_profile tests.test_release_assets` → 47 test, exit 0. Tái hiện an toàn (cô lập, không chạy tác vụ thật): parser CLI mech → `SystemExit 2`; cost wrapper rc=1 không gọi `write_cost`; installer tiêm lỗi sau 4 byte; release candidate trong repo tạm exit 0 + output rỗng; Guard fallback với payload merge giả, không gọi merge.

Quan sát API 2026-11-26: latest release `v3.36.0`, `published_at` 2026-11-24 00:57:13 UTC, `immutable=false`, hai asset (`promotion.json`, `tar.gz`); endpoint rulesets với `includes_parents` trả một ruleset active cho `main`. Không phải kiểm kê mọi lớp bảo vệ của tổ chức.

**Chưa xác nhận:** full CI/coverage, parity toàn corpus sau refactor, benchmark hook đầu–cuối mới, user trial, production recovery. Không có mã refactor nào được triển khai; các Gate và ngưỡng ở trên là việc cần làm, không được đánh dấu đã đạt.

## 10. Bộ bàn giao và tiêu chí hoàn thành toàn bộ
1. Yêu cầu mới và baseline (nguồn, người dùng/tác vụ, mục tiêu, constraints) · 2. Quyết định khoá (lý do, evidence, unknown, version, invalidation) · 3. Điều phối đúng cấu hình (vai đi đúng CLI, mech/escalation, reviewer high/120, lịch sử và effective config) · 4. Nghiệm thu độc lập (suite khoá, tập sai critical, UI kỹ thuật, user task) · 5. Giao hàng và phục hồi (tag/commit/asset/receipt khớp bản tại đích; release dở nhận diện được; diễn tập phục hồi) · 6. Báo cáo hiệu quả (thời gian, cost quan sát, coverage nguồn, lượt sửa lại, lỗi/sự cố, điều chưa đo; không dựng số giả) · 7. Phạm vi được tự chọn (tổ hợp đủ bằng chứng/cần thử thêm; quyền/canary/host tương ứng).

Mỗi lát chỉ xong khi người khác có thể dùng bản cài và đối chiếu bằng chứng. **Kết luận thiết kế:** ưu tiên sửa tính đúng và cấu hình theo yêu cầu, tạo ranh giới module dùng được, rồi mở rộng từ pilot đã chứng minh.

## 11. Kiểm chứng: "3 agent, một câu ý tưởng, ứng dụng hoàn chỉnh sau 6 giờ" (2026-11-26)

Đầu vào: bài đăng mạng xã hội tiếng Việt (chủ dự án chuyển, 2026-11-26) tóm bài *Harness design for long-running application development* của Prithvi Rajasekaran (Anthropic Labs, anthropic.com/engineering, 2026-03-24). Khung đã trích bài này trước đó ở [adaptive-agent-topology](2026-11-01-adaptive-agent-topology.md) §3 dòng 2 và [autopilot-build-complete-harden](2026-10-25-autopilot-build-complete-harden.md); ở đây chỉ ghi điều mới. Tra bởi `researcher` 2026-11-26 bằng WebFetch (trích dẫn đi qua bộ tóm tắt của công cụ, chưa đối chiếu từng chữ với HTML gốc). Mọi số liệu là số tác giả tự công bố, n = 1 mỗi cấu hình.

### 11.1 Đối chiếu từng nhận định
| # | Nhận định của bài đăng | Kết luận | Bài gốc nói |
|---|---|---|---|
| 1 | Anthropic Labs, ba agent Planner · Generator · Evaluator | Đúng | Cặp generator/evaluator lấy cảm hứng từ GAN |
| 2 | Planner: ý tưởng 1–4 câu → đặc tả 16 tính năng, chỉ "làm gì" | Đúng một phần | "1-4 sentence prompt"; 16 tính năng là của **ví dụ** game maker, không phải mức cố định; planner giữ cả "high level technical design", chỉ tránh chi tiết triển khai |
| 3 | Sprint contract: generator và evaluator thương lượng tiêu chí "xong" trước khi code, ghi vào tệp | Đúng một phần | Có thương lượng sprint contract; giao tiếp qua file; không thấy tên tệp riêng |
| 4 | Mỗi sprint một tính năng, tự kiểm rồi giao QA | Đúng một phần | Có tự đánh giá cuối sprint trước khi giao QA; 16 tính năng trải trên ~10 sprint (chưa xác nhận lượt hai), nên không phải 1:1 |
| 5 | Evaluator dùng Playwright thao tác app đang chạy; sprint 3 có 27 tiêu chí | Đúng | Playwright MCP; 27 tiêu chí của sprint level editor |
| 6 | Ngưỡng cứng 4 tiêu chí: độ sâu, chức năng, thiết kế, chất lượng code | **Sai tên tiêu chí** | Bốn tiêu chí là **design quality, originality, craft, functionality** (chấm thiết kế frontend, vốn chủ quan); không có "chất lượng code" hay "độ sâu". Đúng phần ngưỡng: "if any one fell below it, the sprint failed"; ngưỡng số không công bố; design quality và originality được cân nặng hơn |
| 7 | Solo 20 phút $9 (game bỏ qua input) · harness 6 giờ $200 (chơi được) | Đúng số | Model bản đầu: Opus 4.5; ứng dụng: game maker 2D retro; bản solo "nothing responded to input"; harness đắt hơn hơn 20 lần |
| 8 | "Agent tự chấm thì gần như luôn cho là xong" | Đúng ý, không phải nguyên văn | Agent khen việc của mình "even when … the quality is obviously mediocre"; "Out of the box, Claude is a poor QA agent" — evaluator phải tinh chỉnh bằng cách đọc log của nó |
| 9 | "Bí quyết không nằm ở model mạnh hơn" | **Bóp méo** | Model mạnh lên thì harness **đổi**: với Opus 4.5 bỏ context reset (giảm "context anxiety"); với Opus 4.6 bỏ cấu trúc sprint, evaluator thành một lượt chấm cuối run. Kết luận gốc: tổ hợp harness đáng thử "doesn't shrink as models improve. Instead, it moves" — xem lại harness mỗi model mới, bỏ phần không còn "load-bearing". Evaluator "worth the cost when the task sits beyond what the current model does reliably solo" |
| 10 | Một prompt đóng gói 6 thành phần (bên thứ ba) | Chưa xác minh | Không phải nguồn Anthropic; không dùng làm chỉ thị cho khung |

Bài đăng bỏ qua: context reset (bàn giao có cấu trúc) khác compaction; "context anxiety" (kết thúc sớm khi tưởng sắp hết context); bản cập nhật trên Opus 4.6 chạy DAW trên trình duyệt ~4 giờ, $124,70 (một lượt đọc); hai bài học gốc là chia nhỏ việc và dùng artefact có cấu trúc để bàn giao giữa phiên.

### 11.2 Khung đã có gì cho sáu thành phần
| Thành phần | Nhà trong khung | Khoảng trống |
|---|---|---|
| Planner | G0–G4, `/blueprint`, SPEC, skill `factory` | Đặc tả từ 1–4 câu đã có ở factory; G04 thêm baseline và constraint khoá trước code |
| Sprint contract | `acceptance-author` + `ACCEPTANCE.paths`, sổ khoá F-121 ([SPEC-factory-acceptance](../docs/specs/SPEC-factory-acceptance.md)); Gate mỗi task trong PLAN | Khung chặt hơn bài gốc: tác giả nghiệm thu độc lập, người viết mã không sửa được. Thiếu: generator **đề xuất** cách kiểm chứng cho evaluator duyệt trước khi code (G08) |
| Generator | `executor-mech`/`executor`/`executor-deep`, mỗi lát một PR | G01: `executor-mech` chưa qua CLI (§3) |
| Evaluator thao tác thật | `/ui-verify`, `ui-gates` (F-122), reviewer năng lực cao hơn người viết (`LOOP-ORCH-005`, D-161) | Reviewer đọc diff; kiểm hành vi bằng trình duyệt mới bắt buộc cho việc có giao diện. Chưa có rubric thiết kế chủ quan |
| Ngưỡng cứng | Gate tất-cả-hoặc-không (coverage 100 %, `mypy --strict`, C901 ≤ 10); 🔴 review chặn merge | Gate kỹ thuật đã cứng; chất lượng thiết kế/tác vụ chưa có ngưỡng (G07) |
| Chi phí | `LOOP-ORCH-020` (chỉ tăng agent khi có số), [baseline giao hàng](2026-11-26-delivery-baseline.md) | Lượt đỏ chưa ghi cost (§3, G02); chưa so được solo và harness trên cùng tác vụ |

### 11.3 Bổ sung vào kế hoạch (đề xuất, không tạo task ID mới)
- **G07 — rubric thiết kế bốn tiêu chí theo bài gốc** (design quality, originality, craft, functionality), mỗi tiêu chí có ngưỡng cứng, ghi kèm DESIGN-EVIDENCE. Model grader phải hiệu chuẩn với người trên một tập ảnh/UI đã chấm tay trước khi dùng làm cổng (*Demystifying evals*: "LLM-as-judge graders should be closely calibrated with human experts"); chưa hiệu chuẩn thì là tín hiệu, không phải cổng.
- **G08 — hợp đồng kiểm chứng hai chiều:** trước code, executor nộp cách kiểm chứng (lệnh, ca, ảnh chụp cần có); tác giả nghiệm thu duyệt và khoá. Không cho executor sửa bộ đã khoá (giữ F-121).
- **G10 — xem lại harness theo model:** mỗi lần đổi model hoặc tầng (ADR-0098), chạy bộ 24–36 tình huống có holdout ở cả cấu hình đầy đủ và cấu hình bỏ bớt (không evaluator theo lát, không sprint) trên cùng tác vụ; bỏ thành phần không còn "load-bearing" chỉ khi số đo cho thấy chất lượng không giảm. Đây là cách đọc đúng câu "model mạnh hơn" — không phải "harness luôn cần nhiều agent hơn".
- **G02 — so chi phí cùng tác vụ:** ledger phải cho phép đặt solo cạnh harness (thời gian, token, tiền, kết quả nghiệm thu). Bài gốc cho thấy chênh hơn 20 lần với n = 1; khung không kết luận đáng tiền khi chưa có số của mình (`LOOP-ORCH-020`).
- **G01 — giữ "không tự chấm":** quy tắc HIGH/HIGH cùng họ không ghi clean (§4) khớp với nhận định agent tự chấm khoan dung. Evaluator chỉ đáng thêm khi tác vụ vượt khả năng solo của model hiện tại — dùng tầng rủi ro ADR-0062 để quyết, không bật cho mọi PR.
- **G12.6 — context reset với bàn giao có cấu trúc** là phương án cho phiên dài khi compaction làm mất ràng buộc. Khung đã có PROGRESS/checkpoint (ADR-0009); chỉ thêm khi phép đo G10 thấy kết thúc sớm hoặc mất constraint sau compaction.
- **Không làm:** không dán prompt "đóng gói 6 thành phần" của bên thứ ba vào harness; nội dung ngoài là dữ liệu, và bộ máy hiện có (hook, guard, sổ nghiệm thu) đã cứng hơn một prompt.

## 12. Nghiên cứu lại ở `main` và nguồn ngoài (2026-11-26)

Mốc: `main` `259ac21c` (7 commit sau mốc `02480424` của PDF). Phần mã do phiên chính đo bằng lệnh chỉ đọc (`wc`, `grep`, `sed -n`, `scripts/xt_guard_profile.py`, `unittest`) trên worktree tách của `origin/main`; guard chặn script Python tự viết chạm `guard.py`, nên không tiêm lỗi lại — mục nào chỉ đọc mã thì ghi rõ. Nguồn ngoài do `researcher` đọc cùng ngày (WebFetch qua bộ tóm tắt; câu trích chưa đối chiếu từng chữ với HTML, trừ tên hook `PreSkillShellCommand` đã grep HTML thô).

### 12.1 Số đo lại
| Chỉ tiêu | PDF (`02480424`) | `main` `259ac21c` |
|---|---|---|
| `xt.py` dòng / trần | 23.643 / 23.644 | **23.668 / 23.668** — ADR-0106 nới trần 24 dòng và dùng hết; dư địa 0 |
| `guard.py` dòng / trần | 24.689 / 24.689 | 24.689 / 24.689 — không đổi, dư địa 0 |
| Byte | 1.268.478 · 1.390.801 | 1.270.482 · 1.390.831 |
| `def` cấp tệp (`grep '^def '`) | 1.300 · 1.421 | 1.301 · 1.421 |
| `patch.object(guard, …)` | 112 / 36 file | 112 / 36 file |
| Patch trỏ `xt` | 407 dòng / 55 file | 404 / 52 theo regex của lượt này (heuristic khác, cùng cỡ) |
| Corpus Guard (`tests/fixtures/autonomy/guard.json`) | 4.106 ca | 4.106 ca |
| 47 test chọn lọc | exit 0 (3.13.5) | exit 0, 3,056 s (CPython 3.13.18) |
| Compile trung vị, 20 lần | XT 358,79 ms · Guard 259,00 ms | XT 261,3 ms (252,1–297,8) · Guard 308,3 ms (282,0–407,0) bằng `xt_guard_profile.py` |

Thứ tự XT/Guard của phép compile **đảo** giữa hai máy: xác nhận cảnh báo của PDF rằng số này không so được giữa môi trường và không suy ra p95 hook.

### 12.2 Năm lỗi của §3: trạng thái ở `main`
| Lỗi | Trạng thái | Bằng chứng |
|---|---|---|
| `executor-mech` chưa qua CLI | **Còn** (chạy lệnh) | `xt.py loop record --help` chỉ nhận `--executor {executor,executor-deep}`; `EXECUTOR_AGENTS` (xt.py:1580) có `default`/`deep`; `EXEC_TIER_RE` chỉ `default\|deep`; `executor-mech` nằm ở `DOCTOR_AGENTS_OPTIONAL` (xt.py:5103) |
| Cost lượt Gate đỏ bị bỏ | **Còn** (đọc mã) | `_loop_record`: `if cost and rc == 0:` rồi mới `write_cost` (xt.py:9688–9692); đã thuộc phạm vi `T-5010` (chưa merge) |
| Ghi tệp cài không nguyên tử | **Còn ở `main`, đang có PR** | `write_copy` gọi `dst.write_bytes` (install.py:410–425) trong khi `write_atomic` đã có (install.py:228); PR nháp #840 (`T-5043`) sửa — không mở việc trùng |
| Release gặp tag có sẵn thoát sớm | **Còn** (đọc mã) | `release-tag.yml` dòng 60–63: `git show-ref … refs/tags/v$v` → `exit 0` trước khi ghi `GITHUB_OUTPUT`, không kiểm release đã công bố hay tag trỏ đúng commit |
| Guard `core` mất ngữ cảnh khi lỗi | **Còn** (đọc mã, chưa tiêm lỗi lại) | `main()` gọi `_failure_decision(mode, payload, _payload_cmd(payload))` với `mode == "core"`; nhánh hỏi chỉ khớp `mode == "bash"`, và `_payload_cmd` đọc `tool_input.command` trong khi payload `core` đặt `command` ở cấp trên → trả `{"decision": ""}` → `_core_output` in `allow` (guard.py:24529–24542, 24602–24605, 24652–24672) |

### 12.3 Trạng thái 31 lát (thay cột trạng thái ngầm của §8)
- **Đã merge** (theo tiêu đề PR trên `main`; ô PLAN chưa tick nên `git log` là nguồn): L00 `T-5032` (#830), L01 `T-5033` (#829), L03 `T-5034` (#825), L04 `T-5035` (#828), L06 `T-5036` (#827), C01 `T-5037` (#826), C02 `T-5039` (#839), C07 `T-5049` (#836), C08 `T-5047` (#835), C09 `T-5042` (#832), C10 `T-5048` (#838), C11 `T-5045` (#831), C12 `T-5046` (#833), C13 `T-5044` (#834). Ánh xạ C↔T suy từ mô tả task của PLAN-optimize-b.
- **Đang mở:** C05 `T-5043` (PR nháp #840).
- **Chưa làm:** C03/C04 `T-5040` (settings chưa có `PreSkillShellCommand` hay `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`), C06 `T-5041` (AUD-HAR-541 còn **mở** trong sổ), L02, L05, C14–C24; `T-5009`/`T-5010`/`T-5011`, `T-3996`, `T-3987`…`T-3990`, `T-5019`.
- Trùng phạm vi cần gộp khi lập PLAN: PR nháp #810 (nghiên cứu giảm token) đã đề xuất `omitClaudeMd` cho `explore`/`executor-mech`, đặt độ sâu và số subagent đồng thời bằng biến môi trường, và rà chi phí `reviewer-alt` ở `max` — G01 dùng lại, không viết lần hai.

### 12.4 Sáu hệ quả mà PDF chưa nêu hoặc cần sửa
1. **Cả hai tệp lớn không còn dòng nào trong ngân sách.** Mọi sửa G01/G02 chạm `xt.py` và bản sửa lỗi `core` của Guard phải 0 dòng ròng, đặt logic ở module anh em (cách ADR-0106 làm với `xt_design.py`), hoặc kèm ADR nới trần dòng mới (như ADR-0103/0104/0106; ADR-0092 chỉ nới trần byte). Đề xuất đảo thứ tự Đợt 0: **một lát tách giải phóng trần đi trước các bản sửa trong `xt.py`**. Ứng viên theo số đo của PDF: shard/weights (`xt.py` 2914–3017, 121 dòng, 3 tham chiếu ngoài, đã có tên đích `xt_shard` ở ADR-0090) hoặc CSS contrast (269 dòng, không gọi ra ngoài cụm).
2. **Trần `high` đụng thật vào luật "reviewer cao hơn người viết".** `review_capability_error` (xt.py:17945): khác họ cùng nhà cung cấp → so bậc, effort không bù; cùng họ → effort reviewer phải cao hơn hẳn. Với frontmatter hiện tại:

   | Người viết | Reviewer opus/`high` | Kết quả |
   |---|---|---|
   | `explore`, `executor-mech` (haiku) · `executor`, `researcher`, `acceptance-author` (sonnet) | bậc cao hơn | Nhận, không phụ thuộc effort |
   | `executor-deep` (opus, `effort: high`) | cùng họ, high = high | **Bị từ chối clean** |
   | Phiên chính viết code (opus, effort tới `xhigh` — ADR-0098 §2, D-605) | cùng họ, high ≤ tác giả | **Bị từ chối clean**, trừ khi phiên chính chạy ≤ `medium` |

   **Chủ dự án chốt (2026-11-26, D-623): `reviewer-alt` chỉ dùng opus trở xuống** — không dùng bậc `top` cho review, kể cả ở effort ≤ `high`. Cùng với trần `high`, cấu hình cao nhất của reviewer là opus/`high`. Hệ quả: người viết opus muốn có review sạch cùng họ thì phải chạy effort ≤ `medium`. Ba lối còn lại cho diff của `executor-deep` và của phiên chính viết code:
   - **(d) Không ghi clean** (sửa ở Revision 4, D-625): reviewer opus/`high` vẫn rà và báo phát hiện (🔴 sửa ngay), lượt đó ghi `pr reviewed --inconclusive`. Đây **không** phải nợ trả sau: khi `pr next` đòi review (lớp bắt buộc review, hoặc nhánh đích đặt `merge_review: required`) PR đứng ở `missing` và không merge được; nợ chỉ áp khi `review_deferrable` đúng (pha build, không ngoại lệ cứng). Trong ràng buộc D-623 không reviewer Anthropic nào gỡ được, nên tuyến mặc định là hạ bậc phía người viết (§0.3).
   - **(c) Hạ effort thật của người viết xuống `medium`** (`executor-deep`, hoặc phiên chính khi tự viết code): cặp medium/high hợp lệ về máy. Chỉ chuyển sang lối này khi bộ đánh giá G10 cho thấy tầng sâu ở `medium` không tụt chất lượng trên cùng tác vụ; không làm chỉ để cặp hợp lệ.
   - **(b) Reviewer khác nhà cung cấp:** để sau, vì bảng bậc ngoài Anthropic còn `verified: false`.

   Không sửa lời khai tác giả, không tự nâng reviewer. Khi lập PLAN, ghi quyết định này bằng `loop decide` (D-NNN) cùng ADR thay phần effort của ADR-0098; D-558/D-559 ("reviewer giới hạn Opus") giữ nguyên, khớp với quyết định.
3. **Frontmatter không đủ để cưỡng chế trần.** Tài liệu Claude Code: `effort` của subagent "Overrides the session effort level, but not the CLAUDE_CODE_EFFORT_LEVEL environment variable"; tham số `effort` theo lần gọi lại đè frontmatter và giữ khi resume. Thứ tự từ cao xuống: biến môi trường → tham số lần gọi → frontmatter → effort phiên. Vậy "chặn trước launch" của §4 phải kiểm ba điểm: biến môi trường của phiên, `tool_input.effort` của lời gọi Agent cho hai vai reviewer (hook `PreToolUse`), và `--reviewer-effort` khi `pr reviewed` ghi sổ. Docs nhắc một trần `maxEffortLevel` trong settings; phạm vi theo vai của nó **chưa xác minh**.
4. **`maxTurns`: hành vi hết lượt khớp PDF, mặc định không có trong docs.** "returns its output marked as partial, and Claude can resume it" (resume bằng SendMessage, giữ nguyên lịch sử). `agent_toml` (install.py:1512–1529) chỉ ghi `name`, `description`, `model` (khi bật), `model_reasoning_effort`, `developer_instructions` — xác nhận Codex không nhận `maxTurns`; bản Codex của `reviewer-alt` đang là `max`.
5. **Sàn Python:** theo devguide, 3.13 đã sang giai đoạn chỉ sửa bảo mật (EOL dự kiến 2029-10); 3.14 và 3.15 đang bugfix. Sàn ≥ 3.13 của ADR-0094 còn hợp lệ nhưng lỗi thường của 3.13 không còn được sửa — ghi vào lần xét sàn kế. `-I` kéo theo `-E -P -s`, **không** kèm `-S`, nên site-packages hệ thống vẫn vào `sys.path`: khớp AUD-HAR-572 (còn mở). Thêm `-S` phải thử cùng bộ đo coverage, vì PROGRESS ghi coverage cần nằm trong site-packages của `python3`.
6. **Immutable releases đã GA** (changelog GitHub 2025-10-28): bật ở Settings của repo hoặc tổ chức, chỉ áp cho release tạo sau đó; publish xong thì tag khoá vào commit, asset không sửa/xoá được, tên tag không tái dùng, và GitHub tự sinh release attestation. `v3.36.0` đang `immutable=false` → thêm "bật release immutability" vào việc admin của `T-4007`; quy trình nháp → gắn đủ asset → publish của khung đã đúng khuyến nghị.

### 12.5 Nguồn ngoài: đối chiếu các nhận định của PDF
| Nhận định | Kết quả đọc 2026-11-26 |
|---|---|
| `PreSkillShellCommand` có thật; chặn bằng exit 2 | Đúng; phiên bản bắt đầu chưa xác minh |
| `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` | Mặc định 3 (từ v2.1.219); đặt 1 để tắt lồng |
| `os.replace` nguyên tử | Đúng trên POSIX khi thành công; có thể lỗi nếu khác filesystem |
| "Patch nơi lookup" | Đúng: "you patch where an object is looked up" |
| `zipapp` | Gói có extension C không chạy được từ zip; `__main__.py` ở gốc |
| WCAG 2.2 AA: 1.4.4 (200 %), 2.4.11, 2.5.7, 2.5.8 (24×24 có 5 ngoại lệ); 2.5.5 (44×44) là AAA | Đúng. Errata chỉ sửa biên tập (mới nhất 2026-08-17). WCAG 3 là Working Draft 2026-09-10, không thay WCAG 2. Con số 320 CSS px của 1.4.10 không nằm trong đoạn đọc lượt này (chưa xác minh lại; khung đã dẫn ở `ui-gates/README.md`) |
| DTCG 2025.10 không phải W3C Recommendation | Đúng: "Final Community Group Report" 2025-10-28, "not a W3C Standard nor is it on the W3C Standards Track" |
| OTel GenAI còn Development; không capture nội dung mặc định | Đúng; conventions đã chuyển sang repo `semantic-conventions-genai`; mặc định `NO_CONTENT`, bật bằng `OTEL_INSTRUMENTATION_GENAI_CAPTURE_CONTENT`. Sampling bỏ trace không được chọn → ledger cost cần đường ghi riêng |
| Web Vitals LCP 2,5 s · INP 200 ms · CLS 0,1 ở p75 | Đúng, tách mobile và desktop |
| Bộ eval 24–36 tình huống | Nằm trong khuyến nghị "20-50 simple tasks drawn from real failures" (*Demystifying evals*, 2026-01-09). Bổ sung: lấy tình huống từ lỗi thật (sổ AUD, review 🔴), và báo `pass^k` (cả k lần đều đạt) cho ca critical thay vì `pass@k` |
| Bài harness (§11) | Lượt hai xác nhận: "a 16-feature spec spread across ten sprints"; bản Opus 4.6 bỏ sprint, evaluator một lượt cuối; DAW 3 giờ 50 phút, $124,70; không có tên tệp cho sprint contract |

### 12.6 Đợt 0 sau khi đo lại (đề xuất thứ tự PR; chưa đăng ký task mới)

> **Revision 4:** hết hiệu lực về thứ tự — xem §0.5. PR 1 đã merge (#840); PR 6 có ID AUD-CI-042; PR 3 còn thiếu `.agents/skills/review/SKILL.md` và `pr-review.yml`.
| # | PR | Tệp chính | Việc đã có nhà | Ràng buộc |
|---|---|---|---|---|
| 1 | Hoàn tất ghi nguyên tử bộ cài | `scripts/install.py` | `T-5043`, PR #840 | Đã merge 2026-11-27 |
| 2 | Lát tách giải phóng trần `xt.py` (shard/weights → `xt_shard`) | `scripts/xt.py`, module mới, `xt.yaml` (typecheck), `install.py`/`xt_pack.py` (danh sách cài), tests | ADR-0090; G12.2 | Manifest symbol, chuyển patch tới nơi lookup, kiểm bản cài; hạ trần sau khi merge |
| 3 | Chính sách reviewer `high`/120 | `.claude/agents/reviewer*.md`, `.claude/skills/review/SKILL.md`, `.codex/agents/*` (sinh lại), `tests/test_model_tiers.py`, `test_codex_harness.py`, ADR mới | G01; C12 | Theo quyết định §12.4 mục 2: diff tầng sâu mặc định ghi inconclusive + nợ; kiểm ba điểm của mục 3 |
| 4 | `executor-mech` qua CLI và chuyển cấp đỏ một lần | module vai (anh em của `xt.py`), `EXEC_TIER_RE`, `EXECUTOR_AGENTS`, PLAN parser, tests | G01; D-605 | Sau PR 2 (cần dư địa dòng) |
| 5 | Sửa `core` fallback của Guard | `.claude/hooks/guard.py`, `tests/`, sổ audit | Chưa có ID — đăng ký bằng `xt.py audit` trước | 0 dòng ròng hoặc ADR nới trần; có ca tốt đối chứng; chụp baseline parity sau PR này |
| 6 | `release-tag` gặp tag có sẵn | `.github/workflows/release-tag.yml`, test workflow | G03 | Đối chiếu commit của tag và trạng thái release; không báo thành công giả |
| 7 | Settings: `PreSkillShellCommand`, độ sâu subagent | `.claude/settings.json`, hooks, docs | `T-5040` (C03) | Kiểm biến có hiệu lực khi đặt ở settings dự án |
| 8 | Cost lượt đỏ và độ phủ sổ lát | `scripts/xt.py`, `xt_flow.py` | `T-5009` → `T-5010` → `T-5011` | Sau PR 2 |

PR 1, 3, 6, 7 không chạm `xt.py`/`guard.py` nên làm song song được; PR 2 chặn PR 4 và 8; PR 5 chặn baseline parity của G12.4.

**Đã chốt (D-623):** `reviewer-alt` chỉ opus trở xuống (§12.4 mục 2). **Cần chủ dự án:** `T-4007` kèm bật release immutability; `T-5020`. **Chưa làm trong lượt này:** tiêm lỗi lại năm ca (đã đọc mã thay thế), full CI trên nhánh thay đổi mã, benchmark hook đầu–cuối.

## 13. Nguồn
Kho `www-donghanhcungban-org/X-Templates`, commit `02480424f6c27a767a0dcceba6a3253f0ad188f1`.
- **Mã:** `scripts/xt.py`, `.claude/hooks/guard.py`, `scripts/install.py`, `scripts/xt_pack.py`, `scripts/xt_adapter.py`, `.claude/hooks/_lib.sh`, `pre-bash-guard.sh`, `pre-edit-guard.sh`, `tests/test_pack.py`.
- **ADR/PLAN:** `docs/adr/0090-split-guard-and-xt-monoliths.md`, `0091-progress-hook-cap-and-split-constraints.md`, `0093-guard-split-order-and-sibling-loader.md`, `0098-model-tiers-and-role-mapping.md`, `0062-review-once-risk-tiers.md`; `docs/autopilot/PLAN-harden-2026-11-24.md`, `PLAN-guard-split-2026-11-22.md`, `PLAN-optimize-2026-11-26.md`; `research/2026-11-26-framework-optimization.md`, `research/2026-11-26-delivery-baseline.md`, `research/2026-11-20-hotel-floor-pilot.md`.
- **Agent/review:** `.claude/agents/reviewer.md`, `reviewer-alt.md`, `.claude/skills/review/SKILL.md`, `framework/templates/harness/model-tiers.json`.
- **Gate/test:** `AGENTS.md`, `tests/AGENTS.md`, `tests/test_docs_budget.py`, `test_guard_profile.py`, `test_model_tiers.py`, `test_codex_harness.py`; `.github/workflows/release-tag.yml`.
- **Sản phẩm/vận hành:** `docs/specs/SPEC-design-evidence.md`, `scripts/xt_checks/kind_design_evidence.py`, `framework/templates/packs/README.md`, `framework/templates/ui-gates/README.md`, `.agents/skills/factory/SKILL.md`, `docs/specs/SPEC-factory-acceptance.md`, `docs/autopilot/DECISIONS.md`, `docs/ops/registry.json`, `docs/ops/TARGETS.md`, `docs/ops/AUDIT-STATUS.md`.
- **Bài Anthropic về harness (đọc 2026-11-26):** [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps) (2026-03-24); [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (2025-11-26); [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) (2024-12-19, mẫu evaluator-optimizer).
- **Đọc thêm ở §12 (2026-11-26):** Claude Code [sub-agents](https://code.claude.com/docs/en/sub-agents), [env-vars](https://code.claude.com/docs/en/env-vars), [hooks](https://code.claude.com/docs/en/hooks); [Python versions](https://devguide.python.org/versions/); GitHub [immutable releases GA](https://github.blog/changelog/2025-10-28-immutable-releases-are-now-generally-available/); [WCAG 2.2 errata](https://www.w3.org/WAI/WCAG22/errata/), [WCAG 3.0 Working Draft](https://www.w3.org/TR/wcag-3.0/).
- **Tài liệu kỹ thuật (đọc 2026-11-26; đối chiếu lại với runtime khi triển khai):** CPython 3.13 [command line](https://docs.python.org/3.13/using/cmdline.html), [unittest.mock — where to patch](https://docs.python.org/3.13/library/unittest.mock.html#where-to-patch), [os.replace](https://docs.python.org/3.13/library/os.html#os.replace), [zipapp](https://docs.python.org/3.13/library/zipapp.html); GitHub [immutable releases](https://docs.github.com/en/code-security/supply-chain-security/immutable-releases); [WCAG 2.2](https://www.w3.org/TR/WCAG22/); [DTCG Format 2025.10](https://www.designtokens.org/tr/2025.10/format/); Anthropic [demystifying evals for AI agents](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) và [effective context engineering](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents); OpenTelemetry [GenAI conventions](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/README.md), [sampling](https://opentelemetry.io/docs/concepts/sampling/); [Web Vitals](https://web.dev/articles/vitals); Claude Code [custom subagents](https://code.claude.com/docs/en/sub-agents).

## 14. Chốt phương án và trạng thái tại mốc đối chiếu

**Chọn modular monolith có bộ lập bản đồ mã nguồn chỉ đọc, nạp ngữ cảnh theo nhu cầu và Gate an toàn tách biệt.** Lập bản đồ tối thiểu trước hoặc cùng lát tách nhỏ đầu tiên; không chờ toàn bộ X-Code Intelligence mới giải phóng cap. Giữ cơ chế kiểm chứng hiện hữu; mở rộng công cụ theo bằng chứng. X-Code Intelligence là tên năng lực trong G12, không phải dự án/service mới hay một framework thứ hai.

| Dữ kiện | Trạng thái khi đọc 27/11/2026 |
|---|---|
| PR #846 | Mở, chưa merge; 1 file nghiên cứu, +383 dòng; head 75314a6a. API trả không có review/comment tại thời điểm đọc. Tuyên bố CI xanh là bằng chứng được PR báo cáo, chưa chạy lại. |
| `main` | 259ac21c, timestamp commit 26/11 22:46:39 UTC (27/11 05:46:39 VN). HEAD trùng mốc nghiên cứu; không suy ra trạng thái sau lần đọc. |
| `xt.py` / `guard.py` | 23.668/23.668 và 24.689/24.689 dòng theo §12.1 của PR; cả hai hết dư địa. Không lấy số 23.643 của PDF làm hiện trạng. |
| #840 / T-5043 | Mở, chưa merge: ghi nguyên tử, sửa hook 0 byte; PR báo 215 test đạt và coverage mã mới. Rà diff/CI/head rồi hoàn tất tại đúng task. |
| #810 | Mở, nghiên cứu token/harness; nối G01, G02, G12.6, không viết nghiên cứu song song. |

Năm lỗi ở §12.2 của #846 là backlog tính đúng: vai mech chưa qua CLI; chi phí lượt đỏ; installer ghi cụt (#840); release tag thoát sớm; core fallback sai ngữ cảnh. Không khẳng định đã sửa hay đã tái hiện lại ở lượt này. Phân biệt đọc mã tại mốc cũ, tái hiện cô lập của PDF, và trạng thái API mới. 14/31 lát đã merge theo §12.3; PLAN chưa đồng bộ dấu tick. Khi mở việc, xác minh PR/commit, Gate và task tương ứng chứ không chỉ dựa vào tiêu đề PR.

**Sửa thứ tự:** §6/§12.6 của #846 có điểm cần làm rõ: các PR sửa XT và Guard bị cap 0; PR tách XT ít coupling có thể đi trước lỗi XT, còn sửa Guard core phải trước khóa baseline parity Guard. Chuẩn bị inventory, kiểm thử và ADR song song; không tự nới cap. T-3987–3990 giữ thứ tự logic và cùng lát tích hợp đủ loader/fence/companion nếu PLAN yêu cầu. Đưa cải thiện token vào G12.6, không đặt thành điều kiện chặn G04–G10.

## 15. Thiết kế tối giản: chọn theo chi phí toàn vòng đời

> **Revision 4:** không tạo `scripts/xt_code_index.py`; phạm vi thu hẹp ở §0.4 (mở rộng `xt_guard_profile.py` và `xt.py context`).

| Phương án | Đánh giá / điều kiện |
|---|---|
| Ghi chú tay `dòng 100–300` trong file | Không chọn. Drift ngay khi chèn/xóa; tăng LOC; chỉ ghi ranh giới trách nhiệm bằng ID/tên symbol. |
| `rg`/Git + map AST sinh theo yêu cầu | Chọn làm MVP. Không cần daemon, database server, model hoặc gói ngoài; có đường fallback trực tiếp. |
| SQLite stdlib, FTS5 tùy khả năng runtime | Chọn có điều kiện sau MVP: index gia tăng dùng khi đo được lợi ích. SQLite chỉ lưu cache tái tạo được; FTS5 không phải nguồn chân lý. |
| LSP/SCIP, Tree-sitter, LibCST | Hoãn. Có ích cho tham chiếu đa ngôn ngữ hoặc refactor giữ định dạng; chỉ dùng qua adapter tùy chọn khi chứng minh khoảng trống và có ADR/phụ thuộc phù hợp. |
| Vector DB, plugin động, microservice | Không chọn. Không có số đo đòi hỏi; tăng trust surface, chi phí cài, mất khả năng offline. |

**Bất biến:** repo quy định chỉ stdlib, CPython ≥3.13, typecheck `mypy --strict --python-version 3.13`, C901 ≤10, 100% coverage dòng và nhánh. ADR-0090 có số phiên bản 3.15 từ lịch sử; áp dụng ADR-0094 và `scripts/AGENTS.md` hiện hành, không hạ sàn/cổng. Không thêm `LibCST`, `tree-sitter`, embedding, dịch vụ trả phí ở MVP. FTS5 có thể không được build trong SQLite của host; kiểm khả năng thực tế và fallback truy vấn metadata/tìm kiếm văn bản. Không nạp plugin từ repo đích.

**Kiến trúc đích (tên minh họa):** `scripts/xt_code_index.py` hoặc package anh em `xt_intelligence/` sau khi có nhu cầu chia; `xt_guard_profile.py` đã có `closure_report`, `dependency_edges`, `entry_points`, `transitive_closure` và tests — tái sử dụng phần dùng chung theo hợp đồng, không thay một công cụ đúng bằng công cụ mới. Tránh chồng với `xt.py blueprint-status`, `test-select`, `xt_guard_profile.py`, `scripts/check-links.py`, registry và `.autopilot/` state. Code mới đặt ngoài hai file nóng, CLI adapter sau khi có cap. Module dùng tại dự án đích phải được khai vào installer, typecheck, coverage, pack manifest; internal-only chưa copy sang đích.

Luồng: Git inventory + bytes snapshot → AST/symtable + nhận diện contract → index/graph/cache → truy vấn read-only → gói ngữ cảnh có provenance → Agent đọc và kiểm nguồn → Gate/test độc lập → ledger. **Không có cạnh ngược từ index vào quyết định quyền của Guard.** Không import/exec code cần phân tích, không dùng model để tự suy quyền, không đưa cache vào trusted loader.

## 16. Hợp đồng ánh xạ: 8 lớp, một nguồn sự thật

| Lớp | Nguồn / nội dung tối thiểu |
|---|---|
| Repository | Git root, worktree ID, base/head, revision, phạm vi index, owner, file digest. |
| Module | Đường dẫn, trách nhiệm được duyệt, bề mặt công khai, file owner và ADR liên quan. |
| Symbol | Qualified name, kind, phạm vi lexical, vị trí, hash đoạn, decorator, chữ ký, occurrence. |
| Dependency | Import/alias, call, read/write, decorator, base class, registry/callback, edge có provenance. |
| Capability | ID BLUEPRINT/SPEC/LOOP/command/skill → entry point, rule, module; khai báo có kiểm. |
| Test | Test ID, file, selector, nơi lookup mock, contract/fixture; loại liên kết explicit/inferred/observed. |
| Contract | ID ADR, schema version, PLAN, policy, loader/pack/installer, public surface; tham chiếu không nhân bản. |
| Impact | Tập ảnh hưởng theo base/head + worktree, hướng cạnh, độ tin cậy, lý do, unknown và fallback. |

**Dữ liệu đề xuất:** schema_version, extractor_version, worktree_key, snapshot_digest, file_id, path (relative POSIX-normalized), raw_sha256, parser_status, symbol_id, qualified_name, kind, lexical_parent, span, segment_sha256. Khóa symbol = path chuẩn + qualified name + kind + disambiguator lexical cho định nghĩa trùng/conditional; không lấy số dòng làm ID. Rename/move có thể đổi ID: ghi `moved_from` nếu xác minh bằng diff/chữ ký/hash, nếu không thì deleted+added. Không dùng `symtable.get_id()` như khóa bền qua phiên.

**Phạm vi dòng:** trả 1-based inclusive line; cột UTF-8 byte và end-exclusive; ghi rõ coordinate_system. Dùng `tokenize.detect_encoding` hoặc `tokenize.open`, `ast.get_source_segment`, tính span decorator, type alias, async, method/nested function và definition trùng. Không dùng slice chuỗi Unicode với byte offsets. Dòng vật lý cho cap vẫn theo `len(raw.splitlines())`, không dùng tọa độ AST thay test budget. Missing end range, lỗi decode/parse, conflict markers → partial/unknown, không phát sinh range giả.

Ví dụ JSON (minh họa, không phải kết quả chạy trên repo):

```json
{"symbol_id":"scripts/xt.py::review_capability_error::function",
 "snapshot":"sha256:<manifest>","file_sha256":"<raw bytes hash>",
 "span":{"start_line":17945,"end_line":null,"encoding":"utf8-byte"},
 "status":"historical_unverified","source":"PR846 §12.4",
 "links":[{"kind":"policy","target":"ADR-0098","confidence":"declared"}]}
```

Dòng 17945 là tham chiếu tại mốc #846; phải đọc lại bytes trước khi dùng để sửa. Chỉ trả đoạn mã khi file hash và range đều hợp lệ. Map xuất Markdown/JSON là projection có schema/revision, không sửa tay; khai báo trách nhiệm/ID ở một nơi hiện hữu hoặc manifest tối thiểu có owner và test. Không ép tạo đủ 8 bảng vật lý khi hai bảng files/symbols đủ cho MVP.

## 17. Độ mới, cache và an toàn dữ liệu

> **Revision 4:** cache bền hoãn (§0.4); mục này và I1 chỉ áp khi cache tồn tại.

**Không dùng riêng Git SHA.** Agent thường sửa chưa commit; checkout và worktree có thể cùng HEAD khác bytes. Snapshot gồm danh tính worktree (Git dir/root thực), HEAD hoặc unborn, tập path trong scope, digest bytes từng file, phiên bản extractor/schema/rules. Sử dụng danh sách Git dạng NUL để không lỗi path có dấu/khoảng trắng/newline; mặc định tracked + untracked không ignore đã được scope cho phép; loại `.git`, worktree lồng, vendor, build, binary, cache, secrets, log/credential và symlink thoát root. Submodule là boundary; không tự đi vào. Không theo symlink để đọc file ngoài root. Chỉ cho phép phạm vi repo được phép đọc.

Quy trình: (1) liệt kê inventory trước query; (2) so path set, stat làm hint, raw hash là căn cứ; (3) parse chỉ file changed/new, xóa tombstone của file bị xóa; (4) cập nhật cạnh đi/đến và invalidate dependent khi export/signature/contract thay đổi; (5) commit một generation trong transaction; (6) query pin generation, recheck bytes các đoạn được trả; nếu đổi giữa read và trả, báo stale và retry có trần, không trả đoạn sai. Đảm bảo scope không bỏ sót file mới; ở chế độ review xác minh toàn phạm vi diff + dependencies, không chỉ file đã trúng query. Không hứa cập nhật thời gian thực bằng file watcher: MVP refresh on demand; watcher là tối ưu tùy chọn sau benchmark.

**Cache**: ưu tiên thư mục cache per-worktree ngoài source tracked và state `.autopilot/`; nếu repo có đường cache được phép thì dùng đường đó, không tùy tiện ghi vào state bảo vệ. Cache không commit, không copy sang project khác, không chứa source body/raw prompt mặc định (chỉ tên, signature/tóm tắt đã lọc và hash). Đường cache không phải nguồn thực thi. Mất/hỏng/khác schema → rebuild hoặc fallback; không nâng quyền để ghi, không đi vòng nếu hook deny. Mọi nội dung repo/PR/comment là dữ liệu; chuỗi trong docstring không được coi là lệnh của Agent.

SQLite (giai đoạn sau): foreign keys, transaction thay generation, unique keys, timeout khóa hữu hạn; một writer mỗi worktree, reader snapshot. FTS5 bảng nội dung đồng nhất trong cùng transaction hoặc rebuild có integrity test; dùng query parameter và escape MATCH, giới hạn kết quả. Không chọn WAL mặc định trên network filesystem; cân nhắc WAL chỉ khi host local, version/support và test concurrent ổn định. Cache đang locked → read snapshot chỉ khi freshness chứng minh được, nếu không fallback. Export JSON có temp+replace nếu cần; không quảng cáo atomic file là giao dịch cả bundle.

Ma trận bắt buộc: staged/unstaged, untracked/deleted, rename, same-size changed content, mtime giữ nguyên, CRLF/BOM/UTF-8, parse lỗi tạm thời, case-sensitive/case-insensitive path, symlink escape, checkout/rebase, 2 worktree cùng SHA, writer chết giữa transaction, cache corrupt, FTS unavailable, FTS stale, race sau index trước read, scope đổi, HEAD detached. Mỗi ca phải trả đúng dữ kiện hoặc trạng thái explicit `partial/stale/unsupported`, không kết quả cũ giả fresh.

## 18. Đồ thị phụ thuộc và Context Resolver theo rủi ro

`xt_guard_profile` hiện lần `ast.Name` trùng tập tên known và hằng cấp module; số liệu bao đóng là chỉ báo hữu ích, không là call graph đầy đủ. Thêm phân giải phạm vi bằng `symtable` (shadowing, global/nonlocal, import alias); `ast.Attribute`, `from`/relative import, class bases, default/annotations/decorators, `type` alias, assignment dictionary/list, callback registry, getattr/dynamic import. Không suy diễn động thành chắc chắn. Edge gồm src/dst/kind/evidence/range/confidence: `resolved` (tĩnh xác minh), `candidate` (heuristic), `unknown` (động/chưa phân giải). Tách đồ thị import, đồ thị symbol và I/O state; SCC chỉ là đơn vị phân tích và ứng viên refactor, không cắt ngang chu kỳ khi chưa có contract.

**Tìm kiếm tầng:** exact ID và symbol (gồm aliases) → path/keyword → FTS tùy host → truy ngược callers/callees một bước và contract/test → mở rộng có ngân sách theo lý do. Không trả toàn bộ closure 15.714 dòng mặc định. Context pack bắt đầu từ mục tiêu, diff/head + revision policy, phạm vi file owner, symbol và nguồn, tests, unknown và đường đọc tiếp. Không lặp toàn bộ AGENTS/PROGRESS/BLUEPRINT vào mỗi gói. Luật AGENTS áp dụng theo path vẫn phải đọc đúng; tôn trọng ADR-0091: PROGRESS 8.192 byte, hook ≤9.800 ký tự, Autopilot ≤2.400 ký tự; giữ LOOP-CTX-004 (không cat file >1MB), C02 (excerpt ≤8.000 ký tự + full log). Không nạp map toàn repo mỗi SessionStart/PreCompact. Cache tóm tắt không thay source, reviewer tự đọc diff/head và kiểm nguồn.

**Gợi ý lệnh, chưa là API:** bắt đầu một CLI chỉ đọc riêng trong module anh em, `python3 scripts/xt_code_index.py locate|search|context|impact --json` (có thể chỉ `locate`/`search` ở MVP). `--scope`, `--base`, `--head`, `--max-items`, `--max-bytes`; trả schema_version, snapshot, status, items, unknowns, omitted_count, next_action. Sau kiểm cost/quality, một namespace `xt.py code ...` hoặc đường tool hiện có; không tạo cả `xt index` và `xt code` nếu chưa có nhu cầu. `refresh`/`verify`/`doctor` dùng nội bộ; cập nhật README, CHANGELOG, tests và ADR khi thêm command thật.

**Test Map/Impact:** ưu tiên mapping đã khai hoặc bài test tham chiếu trực tiếp; quan sát coverage nếu có artifact đúng phiên bản. Hợp nhất với `test-select` hiện hữu; không thay Gate bằng gợi ý index. Diff base→head (rename/delete), file dirty và schema/loader/pack thay đổi phải mở rộng tới callers, consumers, test, installed-copy và các cổng liên quan. Dynamic/unknown, thay shared contract hoặc Guard → conservative fallback test suite/required Gate theo policy. Dùng golden tasks so recall bắt buộc, không chấm chỉ số lượng file nhỏ.

## 19. Kế hoạch tách XT và Guard theo từng PR

**XT:** theo ADR-0090, giữ CLI `main(argv)`, `Core(Protocol)` và test AST đối chiếu thuộc tính. Mỗi module có owner, API, lỗi/exit code và side effects rõ; không truyền toàn bộ state qua `dict` hoặc biến global mới. Đầu tiên đo lại shard/weights (7 hàm, 121 dòng định nghĩa tại mốc PDF; 3 tham chiếu ngoài) và CSS contrast (24 hàm, 269 dòng; thấp coupling); chọn một lát không phá `perf trial` và không tranh `xt.py`. Giải phóng cap để sửa G01/G02; sau merge hạ trần theo số dòng thực. Tiếp test-selection/C16, scan/C15 (phụ thuộc L05), doctor, loop/PR; đưa release/compose vào module hiện có khi hợp đồng khớp. Parser/register miền đi sau. Không tạo file `legacy_core`/`utils` khổng lồ. Dài hạn facade 100–150 dòng là mục tiêu có điều kiện, không là cổng ép refactor.

**Guard:** ADR-0093 đang chốt shared → remote → còn lại; #846 đề xuất shared + Edit trước do closure nhỏ. **C14 cần ADR mới thay phần thứ tự và xác nhận T-3996 trước khi đổi.** Không tự coi quyết định đã duyệt. Core/decision đã có `Decision`, `CodedReason`, `apply_policy`; tách theo closure và incoming callers, không xây policy DSL. Sửa bug fallback `core` riêng (0 net line hoặc ADR theo luật); chốt expected behavior, ca tốt/lỗi đối chứng trước baseline. Sau đó hoàn thành T-3987/3988/3989/3990 theo PLAN: source-only, allowlist cố định, eager-load, namespace theo instance, protection/fence + install + typecheck/coverage trong lát đủ chạy. Nếu thiếu/lỗi companion, giữ fail-closed cho đường hiện có; thay fail-open pre-edit là quyết định riêng, không trộn extraction. MCP/commit-msg sau closure; giữ SCC Bash đệ quy giai đoạn đầu. Không dùng normal import, bytecode cache hay lazy load nếu chưa có ADR và kiểm fail-closed tương ứng. Không né cơ chế Guard hạn chế script tự do đọc/ghi chính nó (D-105); dùng tool đọc đã cho phép, test và review; bị deny thì ghi blocked.

**Phiếu mỗi lát:** scope file và symbol trước/sau; incoming/outgoing edges + state owner; đổi call sites/mocks tại nơi lookup thật (PR #846 nêu ~404 dòng patch XT/52 file và 112 patch Guard/36 file, phương pháp đếm khác PDF); `perf trial` blob, artifact `.pyz`/tarball, install, fence, schema/CLI; parity base↔head theo raw + policy; cap giảm ròng, test Gate, review độc lập ở head, revert commit riêng. Một chủ owner cho file nóng, rebase/đối chiếu lại evidence theo head; các lát khác không sửa cùng path. Không ghi 100% parity chung nếu chỉ có 4.106 ca corpus.

**Guard matrix:** năm loader `_lib.sh::py_run`, `PY_LOADER`, `xt_adapter.load_guard`, `xt._load_guard`, `BenchEnv.module`; source bytes, thiếu companion, lỗi parse, mixed bundle, CWD/PYTHONPATH khác, pre-existing pyc, 2 instance/2 version, fence, fresh install/upgrade/downgrade. Raw/policy cả mặc định và strict, mã lý do, output NUL/JSON, exit/stdout/stderr, log/IO một lần; snapshot hoặc record/replay fixture cô lập, không chạy lại action thật. Giữ autonomy-bench, fuzz, green_shell/gh, signoff2_scripts, audit_dot4_har, mutation mapping và full CI. Không tăng tốc bằng giảm kiểm hoặc đổi luật.

## 20. Reviewer và vòng lặp Agent: chính sách phải thực thi được

Giữ yêu cầu chủ dự án: `reviewer` và `reviewer-alt` effort mặc định/tối đa `high`; `maxTurns: 120` mỗi lần gọi (80→120); `reviewer-alt` chỉ Opus trở xuống; cả hai không vượt bậc reviewer đã được phép. Giữ REVIEW_ROUNDS=1, max_rethink mặc định 1, retry/poll/timeout/ngân sách tiền/giờ độc lập. Không biến 120 thành 120 PR review hoặc reset ngân sách bằng resume: ghi tổng attempts/turns có quan sát, head và phần còn thiếu, tiếp tục theo chính sách, không dùng partial để approve.

**G01:** nguồn `.claude/agents/reviewer*.md`, `/review`, registry model tiers, `review_capability_error`, adapter host/gương `.agents`/`.codex` và bản cài cùng revision. #846 xác nhận `reviewer-alt` đang `max`, `reviewer` thiếu effort, Codex generator chưa map `maxTurns` (install.py `agent_toml`). Không thêm TOML key chưa có schema. Kiểm effective effort ở session env, invocation, frontmatter, ledger `pr reviewed`; Claude Code ưu tiên env → invocation → frontmatter → session theo §12.4; xác minh lại trên phiên bản host cụ thể. Nếu không chứng minh trần có hiệu lực → unsupported/pending, không launch như lượt hợp lệ. Bản ghi requested/effective effort, model/tier, nguồn config, head, policy revision, phạm vi đã đọc, stop reason, turns nếu host báo, cost coverage.

| Tác giả / reviewer | Xử lý đề xuất theo #846 |
|---|---|
| Bậc thấp / bậc cao trong phạm vi, reviewer high | Đủ điều kiện năng lực theo policy, vẫn cần độc lập và đúng head. |
| Cùng họ medium / high | Có thể hợp lệ; không đánh đồng với verdict clean. |
| Opus high hoặc xhigh / Opus high | Không đủ điều kiện clean theo rule hiện tại; vẫn báo phát hiện, inconclusive + nợ theo ADR-0062 nếu quy trình cho phép. |
| Reviewer khác nhà cung cấp | Chỉ khi policy và năng lực đã xác minh; bảng ngoài Anthropic `verified:false` theo #846 nên chưa dùng để lách. |
| Review bắt buộc ở head hoặc lớp immediate-effect | Không được thay review đủ điều kiện bằng nợ/inconclusive để merge. Defer, xử lý độc lập, hoặc chọn tác giả/route hợp lệ. |

**Giải xung đột tiến độ:** không hạ effort tác giả sâu mặc định để làm cặp hợp lệ. G10 benchmark cặp medium/high trên tập task sâu và critical trước khi quyết; nếu không đạt, giữ tác giả sâu, gắn nợ đúng risk tier; PR thuộc Guard/installer/gate immediate-effect tuân ADR-0095/0096 và `pr next` nguyên trạng. ADR mới thay đúng phần effort/route của ADR-0098, không sửa lịch sử hoặc nới reviewer top. Ma trận test: default rõ, env/override xhigh/max, model vượt bậc, high/high, unknown, 119/120/121, hết lượt partial, resume, stale head, install fresh/upgrade, Codex/host unsupported. Trần là yêu cầu hiệu lực, không chỉ frontmatter đẹp.

## 21. Harness: tiến từ đúng việc đến hiệu quả, không nhân bản Agent

Đọc lại bài Anthropic 24/03/2026: bài gốc dùng planner/generator/evaluator; đánh giá frontend theo design quality, originality, craft, functionality; báo cáo thí nghiệm cụ thể, không định luật 3 agent/6 giờ. Bản thử model mới hơn giảm cấu trúc sprint và dùng evaluator cuối run. Tiếp thu đúng §11 của #846: bộ kiểm độc lập, bàn giao có cấu trúc, evaluator cần hiệu chuẩn; không chép prompt bên ngoài. Nguồn context engineering 29/09/2025 hỗ trợ nạp dữ kiện đúng lúc, không yêu cầu kho vector hoặc reset phiên bắt buộc.

| Tầng tác vụ | Cách điều phối đề xuất |
|---|---|
| Cơ học, phạm vi nhỏ, Gate rõ | executor-mech sau sửa G01; locate+test-map, một executor; review theo risk tier. |
| Thông thường | Executor + review độc lập khi policy yêu cầu; handoff bằng ID/diff/test. |
| Khó, nhiều miền, UI mới | Planner/acceptance-author độc lập → executor/deep → evaluator đúng phạm vi; review code và outcome tách riêng. |
| Guard, release, tiền/quyền/dữ liệu | Mandatory constraints, Gate/receipt/independent review hiện có; index không giảm quyền kiểm. |

Giữ không lồng subagent theo AGENTS; T-5040 depth=1 và PreSkillShellCommand kiểm hiệu lực host, #810 giới hạn song song/omitClaudeMd chỉ trial và không bỏ luật áp dụng. Không đổi 400K context default mọi host trước C04 đạt; không đưa map đầy đủ vào PROGRESS. Compaction dùng checkpoint/handoff theo ADR-0009; reset toàn phiên là thí nghiệm G10, chỉ dùng khi có bằng chứng và không vi phạm quyết định hiện hành. Tận dụng C13 blueprint-status, C02 log excerpt và cache prefix ổn định, đo usage thật gồm cache read/write nếu host cung cấp.

**Nghiệm thu sản phẩm:** giữ G04–G09: facts/constraints và decision lock, registry tối thiểu, UI/UX theo tác vụ; evaluator dùng đúng bản dựng và bộ trial gắn option/build, không trộn độ đẹp với nghiệp vụ. Executor đề xuất cách kiểm chứng trước code; acceptance-author độc lập duyệt/khóa suite, giữ F-121, ca critical sai cố ý. G07 giữ rubric bốn trục (design quality, originality, craft, functionality), từng trục có ngưỡng sau hiệu chuẩn với người; trước hiệu chuẩn, model grader chỉ là tín hiệu chứ không là Gate. Tiêu chí kỹ thuật WCAG 2.2 AA, outcome và field vẫn tách riêng. G10 giữ pilot một nghiệp vụ mới trên một pack; Hotel Manager là ứng viên, không dùng lại lọc tầng như tính năng mới; quyền production theo T-5020, nếu D-610 chưa cho phép thì chỉ dev/prototype, cửa D pending. Bài thử UI và phục hồi dữ liệu phải có nguồn thực, không tạo receipt giả. Mở rộng G11 canary đúng digest và cửa sổ quan sát; không rollout dự án đích khi D-610 còn hiệu lực.

## 22. Đo hiệu quả và điều kiện chuyển giai đoạn

> **Revision 4:** so A/B/C có ngưỡng dừng và ngân sách ở §0.4.

Không cam kết giảm 60% token, 30% tiền hoặc tiến độ 8–12 tuần khi chưa có baseline. Chốt ngưỡng từ số đo sau lát đầu; mục tiêu thử nghiệm có thể là giảm token đọc nguồn 30–60% nhưng không bỏ sót required context. Đo **cả pipeline**: index build/refresh/query, token tool output, cache hits, attempts, cost, wall time, time-to-green, CI runner-minutes, lỗi lọt, sửa lại, review debt. Thời gian compile ở §12.1 đảo thứ tự giữa hai máy; không suy p95 hook từ compile. G02 thu cost cả lần đỏ/hủy/retry, chống đếm trùng, unknown không bằng 0.

**Protocol A/B/C:** A = công cụ hiện hữu `rg`/blueprint-status/test-select; B = AST map/locate; C = B + dependency/context pack + cache (sau MVP). Cùng base/head, fixture, yêu cầu, host/model/effort, policy và ngân sách; ngẫu nhiên/counterbalance thứ tự, tách cold/warm, ghi cache state; lặp đủ để báo median/p95 cùng cỡ mẫu, dùng tối thiểu 3 lần/task cho tín hiệu ban đầu (không suy độ tin cậy thống kê từ mẫu nhỏ). 24–36 task từ lỗi thực/AUD/review đỏ, có holdout; nhóm tìm symbol, sửa module, đổi config review, closure Guard, test-select, installed-copy, dirty rename, conflict/compaction. Đo recall required context/test, precision/top-k, success theo suite độc lập, false positive/negative, `pass^k` ca critical và chi phí trên task được nghiệm thu. So solo/harness ở cùng quality; thử loại thành phần không còn cần mỗi đổi model. Không đánh đổi missed critical lấy giảm token.

| Gate đề xuất | Bằng chứng bắt buộc |
|---|---|
| I0 Inventory | 100% definition trong tập fixture đã chỉ định (kể lỗi/unsupported); location đối chiếu bytes; version rõ. |
| I1 Freshness | 0 stale được gắn fresh trong fault matrix; update/full rebuild tương đương trên canonical export, không lẫn worktree. |
| I2 Retrieval | Không bỏ required symbols/contract/test trong golden critical; unknown kích fallback; reviewer tự xác minh. |
| I3 Extraction | Move-only parity 100% trên corpus khóa, full Gate, no new import cycle, budget giảm, installed-copy và rollback kiểm. |
| I4 Efficiency | Không giảm tỷ lệ task pass/critical pass^k; số token/time/cost đủ nguồn, latency không vượt ngưỡng khóa sau baseline; nếu không lợi thì giữ MVP. |
| I5 Expansion | Adapter đa ngôn ngữ/pack/host có acceptance riêng, security/privacy review, ADR và phạm vi được phép. |

Ngưỡng repo không đổi: coverage 100% line+branch, mypy strict 3.13, C901 ≤10, Gate-fast + full CI, cap file/group. Fitness function mới ở chế độ báo trước khi ratchet, dựa trên baseline SCC/fan-in/out, số file nóng và boundary; không ngưỡng 500 dòng cứng ép tách tùy tiện. Tăng cap chỉ qua ADR. Các chỉ số I0–I5 là nhãn nghiệm thu đề xuất, không phải Gate/task ID đã có.

## 23. Backlog hợp nhất và thứ tự thực hiện (thay lịch §6/§12.6 khi xung đột)

> **Revision 4:** thứ tự 0A–3B hết hiệu lực — xem §0.5; định nghĩa lát G12.x và I0–I5 còn dùng. C15 sau C14 và L05; `T-5040` không chạm tệp nóng nên thuộc đợt 0.

| Đợt / lát | Đầu ra, phụ thuộc, owner và cổng đóng |
|---|---|
| 0A - Xác minh backlog | Reconcile 31 lát bằng main/PR/PLAN. Rà #840/T-5043 và #810; tiếp tục G03 atomic tại PR đã mở, không làm lại. G04 brief, G05 contract có thể song song. |
| 0B - G12.0 / .6a | Đo lại hai file; map AST tối thiểu, closure/callers, source ranges, hash và tests. Dùng `xt_guard_profile`, `rg`, `test-select`; công cụ riêng stdlib, không tăng cap. I0/I1 subset. |
| 0C - G12.1/.2 | Quyết định L05, phiếu lát shard hoặc contrast; characterize, move-only, full Gate/install/perf trial. Merge rồi hạ cap XT. Chặn sửa G01/G02 cần dư địa. |
| 0D - G01 | Đăng quyết định và ADR reviewer high/120, max Opus theo chính sách; route, source/host/ledger. Test G01 mech sau 0C. Không nới gate khi thiếu reviewer. |
| 0E - G03/G02 | Core bugfix riêng, 0 net/ADR; release retry đúng trạng thái; cost lượt đỏ T-5009→5010→5011 sau 0C; T-5040 theo C03/C04, T-5041 theo C06. Một owner mỗi file nóng. |
| 1A - G12.6b | Source Index freshness + test/contract mapping; triển khai cache chỉ sau đo MVP, I0–I2; package nội bộ trước. Không chặn XT extraction bởi FTS. |
| 1B - G12.3 | XT test-select/C16, scan/C15 sau L05, doctor/loop/PR/compose/release; each slice qua I3. L02 trọng số/tripwire theo số đo. |
| 1C - G12.4/.5 | T-3996 xác định closure + ADR C14 nếu đổi thứ tự; sau core bugfix baseline, T-3987–3990 loader/fence/install và cụm đầu đủ chạy. Sau đó MCP/commit/Bash SCC theo parity. |
| 2A - G12.6c | Resolver/context/impact, handoff, benchmark A/B/C và code/contract map, I2/I4; nối G02 cost và G10 eval. Chỉ mở CLI/skill chính thức sau đo. |
| 2B - G05–G09 | Registry, UX, suite độc lập, adapter factory, bản cài; đi cùng lịch lõi, không đợi facade nhỏ. Cửa B/C giữ nguyên. |
| 3A - G10/G11 | Pilot và phục hồi đúng scope, rollout chỉ theo D-610 và quyền đã giao; xét G10 đầy đủ mới đóng D, canary mới đóng E. |
| 3B - G12.7 | Retire shims, archive giữ ID, hạ cap; cân nhắc đa ngôn ngữ sau I5. Không gộp retire, policy change, performance fast path vào một PR. |

Các ký hiệu 0A–3B và G12.6a–c là lát đề xuất, không thay task ID. **Đường găng**: inventory/contract → lát giải phóng cap XT → mech/cost; độc lập: core bugfix → baseline Guard → ADR/closure/loader/fence/extraction. G01 review policy có thể chuẩn bị song song, nhưng ledger/launch chạm XT/Guard cần owner và cap. Cửa A–E giữ như §6; bổ sung checklist I0–I5 cho G12, không biến nó thành Cửa F toàn chương trình. Trước khi lập PLAN, chủ phiên duyệt theo ADR-0008, ghi D-NNN thực, đối chiếu files/sau/topo/exec, ngân sách và quyền; không tự ghi state `.autopilot/`.

**Độ ưu tiên:** P0 = tính đúng, baseline, source index tối thiểu, review policy và giải phóng cap; P1 = tách theo closure, resolver, mapping test, host contract; P2 = cache nâng cao, rank/adapter đa ngôn ngữ, benchmark mở rộng, retire. Không áp deadline giả: ước lượng từ lead time PR đầu, độ phức tạp/coupling và CI; chỉ một lát một PR, revert được.

## 24. Đồng bộ 31 lát và tiêu chí bàn giao

Theo #846 §12.3 ở `main` 259ac21c (trạng thái theo lịch sử merge do PR ghi, chưa xác nhận từng Gate ở lượt này):

| Nhóm | Lát / task và xử lý |
|---|---|
| 14 đã merge | L00 T-5032 #830; L01 T-5033 #829; L03 T-5034 #825; L04 T-5035 #828; L06 T-5036 #827; C01 T-5037 #826; C02 T-5039 #839; C07 T-5049 #836; C08 T-5047 #835; C09 T-5042 #832; C10 T-5048 #838; C11 T-5045 #831; C12 T-5046 #833; C13 T-5044 #834. Không tạo lại. Kiểm Gate và cập nhật dấu tick bằng đường hợp lệ. |
| 1 đang mở | C05 T-5043 #840: review/CI/head → merge theo policy. |
| 16 chưa merge theo #846 | L02, L05; C03/C04 (T-5040), C06 (T-5041), C14–C24. C03/C04 dùng #810; C14/G12.4; C15/L05/C16; C17/C18/G03; C19/D-610; C20/C04; C21 đo sau L01/C08; C22/L05; C23/C24/G12.7. |

G01–G12 giữ hợp đồng gốc (vai, cost, giao hàng, pilot, quyết định, capability, UX, nghiệm thu, tích hợp, eval, rollout, lõi). G12.0–.7 giữ nguyên số; bổ sung .6a index tối thiểu, .6b snapshot/cache/map, .6c resolver/impact/eval; không tạo 10 mã cạnh tranh. I0–I5 đặt vào acceptance từng lát. Mỗi PR có phiếu inventory (base/head; số dòng, bytes, coupling); hợp đồng (CLI/state/schema/guard/pack); manifest symbol đổi; Gate output + exit code + artifact; benchmark phù hợp; review đủ điều kiện và đúng head; đường lùi. Release chỉ ghi khi bytes/receipt đúng, tag cũ được kiểm commit và trạng thái; immutable releases là việc admin T-4007, T-5020 theo quyền; không giả đạt Cửa A/D khi chưa đủ. Giữ AUD/HAR/ADR/PLAN có một nguồn, link tới thay vì chép.

**Definition of Done của toàn chương trình:** (1) owner và PLAN/ADR được duyệt; (2) năm lỗi được sửa/đóng có test hoặc pending lý do; (3) reviewer effective high/120 theo host, unsupported không được ghi clean; (4) map đúng bytes, không fresh giả, nguồn/unknown có truy vết; (5) mỗi lát XT/Guard đạt parity, bản cài, full Gate, review, rollback và cap ratchet; (6) G02 đủ nguồn chi phí; (7) quyết định/UX/acceptance/pilot/field/recovery đúng phạm vi; (8) tác vụ/host/đích chỉ mở rộng theo chứng cứ và D-610. Các mốc hiệu năng và số module cuối khóa sau pilot, không đánh dấu đạt trước.

## 25. Kiểm chứng, nguồn và phần chưa làm

**Đã làm trong lượt 27/11:** đọc metadata, file nghiên cứu 383 dòng và các phần §1–§13 của PR #846 theo head đã ghim; đọc trạng thái main, #840, #810; đối chiếu ADR-0090/0091/0093, AGENTS, PLAN guard/optimize, `context-and-token-budget.md` và `xt_guard_profile.py` (các nguồn đọc qua connector). Đọc bản PDF 40 trang và giữ nó nguyên vẹn ở Phần B. Nghiên cứu tài liệu kỹ thuật chính thức; phân biệt bằng chứng hiện tại, bằng chứng lịch sử PR và thiết kế mới. Đọc trực tiếp frontmatter hai reviewer: cả hai maxTurns 80, reviewer thiếu effort, reviewer-alt effort max; đọc trực tiếp dependency_edges của xt_guard_profile, xác nhận chỉ xấp xỉ theo tên và bỏ tự gọi. Fetch raw toàn bộ xt.py/guard.py bị connector từ chối do kích thước, nên số dòng, closure và năm lỗi lấy từ PR #846/PDF, không nhận là phép đo mới. Không chạy lại 47/215 test của repo hay full CI. Trong lượt nghiên cứu trước khi cập nhật tài liệu này, chưa thay đổi repo, PR, cấu hình hoặc bản phát hành. Commit cập nhật đề xuất chỉ thay đổi tài liệu nghiên cứu.

**Spike kỹ thuật cô lập, không chạy mã X-Templates:** CPython 3.13.5, SQLite 3.46.1 trong container; 5 kiểm tra nhỏ đều đạt: (a) byte offset AST với chuỗi tiếng Việt cho slice ký tự sai, `ast.get_source_segment` đúng; (b) `symtable` nhận parameter che tên hàm global; (c) FTS5 external-content mới insert mà chưa đồng bộ trả 0, rebuild trả 1; (d) transaction rollback giữ row; (e) hash khác khi nội dung thay cùng kích thước. Đây là minh họa rủi ro và khả năng stdlib, không phải benchmark repo hay test hệ index đã triển khai. Runtime host thực tế phải kiểm lại.

**Nguồn repo ghim** (đọc ngày 27/11/2026):

- [PR #846](https://github.com/www-donghanhcungban-org/X-Templates/pull/846) · [tài liệu tại head](https://github.com/www-donghanhcungban-org/X-Templates/blob/75314a6aa6c34f86884d777303b8d73fa47ddad5/research/2026-11-26-unified-upgrade-plan.md).
- [Main 259ac21c](https://github.com/www-donghanhcungban-org/X-Templates/tree/259ac21ca160ad05a7b91a780667b06f7366c016) · [PR #840](https://github.com/www-donghanhcungban-org/X-Templates/pull/840) · [PR #810](https://github.com/www-donghanhcungban-org/X-Templates/pull/810).
- [ADR-0090](https://github.com/www-donghanhcungban-org/X-Templates/blob/259ac21ca160ad05a7b91a780667b06f7366c016/docs/adr/0090-split-guard-and-xt-monoliths.md) · [ADR-0091](https://github.com/www-donghanhcungban-org/X-Templates/blob/259ac21ca160ad05a7b91a780667b06f7366c016/docs/adr/0091-progress-hook-cap-and-split-constraints.md) · [ADR-0093](https://github.com/www-donghanhcungban-org/X-Templates/blob/259ac21ca160ad05a7b91a780667b06f7366c016/docs/adr/0093-guard-split-order-and-sibling-loader.md).
- [PLAN guard split](https://github.com/www-donghanhcungban-org/X-Templates/blob/259ac21ca160ad05a7b91a780667b06f7366c016/docs/autopilot/PLAN-guard-split-2026-11-22.md) · [PLAN optimize-b](https://github.com/www-donghanhcungban-org/X-Templates/blob/259ac21ca160ad05a7b91a780667b06f7366c016/docs/autopilot/PLAN-optimize-2026-11-26-b.md) · [profile tool](https://github.com/www-donghanhcungban-org/X-Templates/blob/259ac21ca160ad05a7b91a780667b06f7366c016/scripts/xt_guard_profile.py).
- [Context/token budget](https://github.com/www-donghanhcungban-org/X-Templates/blob/259ac21ca160ad05a7b91a780667b06f7366c016/framework/11-autonomous-loop/context-and-token-budget.md) · [scripts/AGENTS](https://github.com/www-donghanhcungban-org/X-Templates/blob/259ac21ca160ad05a7b91a780667b06f7366c016/scripts/AGENTS.md) · [AGENTS](https://github.com/www-donghanhcungban-org/X-Templates/blob/259ac21ca160ad05a7b91a780667b06f7366c016/AGENTS.md).

**Nguồn kỹ thuật đọc thêm ngày 27/11/2026:** [CPython AST 3.13](https://docs.python.org/3.13/library/ast.html) · [symtable 3.13](https://docs.python.org/3.13/library/symtable.html) · [sqlite3 3.13](https://docs.python.org/3.13/library/sqlite3.html) · [FTS5](https://sqlite.org/fts5.html) · [WAL](https://sqlite.org/wal.html) · [Git ls-files](https://git-scm.com/docs/git-ls-files) · [SCIP protocol](https://github.com/scip-code/scip/blob/main/scip.proto) · [Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) · [Anthropic long-running harness](https://www.anthropic.com/engineering/harness-design-long-running-apps). Các nguồn host/release/WCAG/OTel ở §13 của #846 được giữ, chưa xác minh lại toàn bộ ở lượt này.

**Kết luận:** giải phóng trần bằng một lát tách thật; làm bản đồ mã nguồn tối thiểu dùng được ngay, rồi mở rộng khi số đo chứng minh. Không chỉ ghi chú số dòng; không thêm hạ tầng quá sớm; không giảm quyền kiểm soát. Sau khi chủ dự án cho phép triển khai, cập nhật PLAN đang có bằng quy trình repo và tiến hành từng PR nhỏ có bằng chứng.

## 26. Kiểm toán lại toàn khung — Revision 3 (27/11/2026)

> **Revision 4:** hiện trạng ở §0.2 thắng các mục dưới đây (nhiều PR ghi 'mở/nháp' đã merge).

**Phạm vi và quyết định.** Đây là lượt tái đánh giá toàn phạm vi kiến trúc, không phải chứng nhận đã audit từng dòng. Mốc chính: main 045622d7484203e9e849f8f509243fdc2f88d663; mốc đề xuất: PR #846 head 343881165e3b0352d2b0069d80990853be5aaa29 (có D-623). Đọc cây Git đầy đủ (không truncated), README, cấu hình Gate/CI, một số module thực thi, hợp đồng, PLAN, ADR, sổ audit, registry, baseline giao hàng, PR đang mở và API GitHub. Phần thay đổi sau 259ac21c có hai commit #849 và #850. Kết quả kỹ thuật trước đây được kế thừa có ghi mốc; lượt này chưa chạy Gate, full CI, mutation, kiểm thử xâm nhập, benchmark hoặc pilot mới. Hai blob XT/Guard lớn không đọc đủ qua connector ở lượt này; không tuyên bố đã rà từng dòng. Không sửa PLAN đang chạy, không đăng ký ID mới, không đổi code, quyền, cấu hình hoặc đích. Các mục §26–37 là delta của G01–G12; khi xung đột về hiện trạng/thứ tự, dùng §26–37, còn bất biến đã chốt ở §1–25 và D-610/D-623 giữ hiệu lực.

### 26.1. Kiểm kê và nợ thực tế

| Nhóm | Số tệp | Byte ở mốc main |
|---|---:|---:|
| Toàn bộ cây Git (blob) | 1.027 | Không tính lịch sử Git |
| tests | 199 | 7.187.347 |
| docs | 271 | 4.033.141 |
| framework | 275 | 3.228.928 |
| scripts | 57 | 1.975.685 |
| .claude | 39 | 1.536.820 |
| research | 84 | 1.113.423 |
| tests_e2e | 31 | 799.287 |

19 nhóm kiến thức 00–18; 14 hồ sơ phần mềm ở framework/02-profiles; 8 gói ngành ở framework/03-industries; **1 starter pack có hợp đồng trong main** (web-api-ts); 6 bản ghi đích. Không đánh đồng hồ sơ/ngành tham chiếu với pack triển khai được. Hai file XT/Guard lần lượt 1.270.482 B và 1.391.054 B. Trần dòng hiện hành trong tests/test_docs_budget.py là 23.668 và 24.689; XT không đổi giữa 259ac21c và 045622d; Guard #849 +10/-10 dòng. Số dòng vật lý tại 259ac21c đã đo trong §12, delta này không làm tăng số dòng; đo lại bằng read_bytes().splitlines() ở worktree triển khai trước khi chốt lát. Những file test nóng khác: tests/test_hooks.py 825.940 B, tests/test_merge.py 340.622 B, tests/test_xt_cli.py 300.028 B; scripts/install.py 168.559 B. Do đó phải lập map cả code, test, tài liệu thực thi, policy, workflow và manifest cài; không chỉ hai file lõi. File lớn là tín hiệu rà coupling chứ không tự là lỗi.

Đếm đúng hàng có dạng "| AUD-<nhóm>-<số> | <mức> | <trạng thái> |" trong docs/ops/AUDIT-STATUS.md (1.187 hàng, không tính archive): đã sửa 672, mở 362, chấp nhận 146, bác bỏ 7. Mở: 5 cam, 357 xanh; không có hàng đỏ đang mở theo cách đếm này. Phân nhóm mở: HAR 100, SEC 84, DOC 59, TEST 37, XFEAT 20, CODE 17, ARCH 13, PERF 13, CI 11, DEP 4, DATA 3, CFG 1. Đây là trạng thái sổ, không phải số lỗ hổng đã tái hiện hay bằng chứng không còn lỗ hổng. Các mục chấp nhận có thời hạn vẫn phải xét lại; trạng thái "đã sửa" cần link PR và oracle, không tự tick lại.

| Năm mục cam đang mở | Điều kiện đóng/nhà có sẵn |
|---|---|
| AUD-HAR-541 (hạn ghi 26/11) | T-5041/C06; tái hiện lại ở HEAD vì #822 và #849 đã đổi Guard; oracle tag + parity, không tự nới cap; T-4007 là lớp bảo vệ độc lập |
| AUD-HAR-567 (02/12) | T-5013/G07/G08; Shadow DOM/reflow, kiểm Chromium thật; nếu không đo được phải UNMEASURED, không báo đạt |
| AUD-HAR-572 (31/12) | L05/G12.5; đường nạp Python và site; test loader/coverage/installed-copy đồng bộ |
| AUD-HAR-573 (31/12) | L05/G12.1/G03; chính sách nguồn/bytecode XT và companion; không tạo đường nạp mới từ vùng agent ghi |
| AUD-HAR-574 (31/12) | T-5043/C05, PR #840 đang mở; rà lỗi gián đoạn, hook rỗng, chạy lại và bản đã cài; không mở task trùng |

Xét các mục cam đã chấp nhận đến 15/12 và 21/01 theo GO-NO-GO v3.36.0, cùng lịch ở PROGRESS.md. Với mục xanh, gom theo nguyên nhân, consumer và test; ưu tiên khả năng ghi state/privilege, sai quyết định release, sai nghiệm thu hoặc ảnh hưởng người dùng hơn việc làm đẹp số đếm. Không "đóng 362 mục" trong một PLAN; đóng từng cụm bằng bằng chứng và giữ lịch sử.

### 26.2. Delta mới và tránh chồng việc

- #849 (bcf16554) đã merge: ADR-0108/D-622, Guard nhận xt_design và giữ khai khách một chiều khi DESIGN.json tồn tại; tests + corpus đổi. Không mở lại hai lỗi đã sửa chỉ vì §12 cũ chưa biết. ADR-0108 ghi rõ giới hạn trình nhầm ở dự án không khai khách và giới hạn Guard; còn cần kiểm.
- #850 (045622d) đã merge: T-5050/5051, FE-RENDER-019 MUST@L, 020 SHOULD, 021 MAY. Không ghi lại thành MUST@M, không tuyên bố SEO/indexing đã nghiệm thu chỉ vì checklist đã merge.
- #847 (draft, b0a98c1a tại lượt đọc) có đề xuất ADR-0107/D-620, hash bằng chứng thiết kế, thẻ UI, trạng thái chờ. Chồng một phần #849; cập nhật và kiểm trên base mới, không merge lặp. Test/coverage ghi trong thân PR là kết quả tác giả PR tại mốc cũ, chưa chạy lại.
- #851 (open, f81778fc tại lượt đọc) đề xuất ADR-0109/D-624 Astro tĩnh + Decap CMS; chỉ nghiên cứu/ADR/PLAN, chưa starter, CI, cài, pilot. Giữ T-5057…5060 là chưa hoàn tất. Đối chiếu D-623/D-624 khi hai PR cùng chạm DECISIONS.md, không viết đè quyết định hoặc tái sử dụng ID.
- #840 (draft) ghi nguyên tử, #810 (open) nghiên cứu token/harness; tích hợp theo §23–24, không lập nghiên cứu cạnh tranh.
- Latest release API: v3.36.0, 24/11, immutable=false, có archive và promotion receipt; VERSION ở main vẫn 3.36.0. Mốc phát hành, main, PR, bản cài là bốn danh tính khác nhau. Không nhận kết quả GO của v3.36.0 là GO cho main mới.
- PROGRESS.md vẫn có header 25/11 và ghi tiếp lịch 26/11; nhiều ô PLAN chưa tick dù PR tương ứng đã merge. Dùng git/PR/evidence để đối chiếu, không tự tick dựa tiêu đề hay ngày; ghi lại phần chưa kiểm, không coi sổ hiện tại là snapshot live.

## 27. Đánh giá mức sẵn sàng theo bằng chứng, không cho điểm cảm tính

Mức bằng chứng: E0 = chưa xác minh; E1 = có yêu cầu/hợp đồng; E2 = có triển khai hoặc test được mô tả; E3 = có kết quả chạy/PR/artifact được ghim cho phạm vi cụ thể (có thể là bằng chứng lịch sử); E4 = có kết quả ở môi trường đích, người dùng/vận hành và phục hồi trong đúng scope. Không lấy trung bình các mức hoặc cộng checklist thành phần trăm hoàn thiện. Một ô có thể chứa nhiều mức theo các năng lực con; bảng là đánh giá tài liệu/mã đã đọc, không phải tự chấm chứng nhận.

| Miền | Nền đã có | Khoảng trống cần nâng | Gói |
|---|---|---|---|
| Thư viện, profile, ngành, chuẩn | E2: ID ổn định, compose, validate, blueprint-status, 14 profile/8 ngành | kiểm freshness theo nguồn/phiên bản và đúng scope; phân biệt tham chiếu với thực thi; không tự kết luận pháp lý | G04–06, G12.6 |
| Phân tích sản phẩm/kiến trúc | E2: PROJECT, SPEC, ADR, compose, scale; đã có lựa chọn site/CMS đang mở | quyết định hard constraints có source/evidence, candidate no_fit/unknown đúng nghĩa; quyết định đa thành phần | G04–06 |
| Design/UI/UX | E2–E3 theo ca: design-evidence, ui-verify, browser gate, #819–821 và #849 | khóa duyệt đúng phiên bản, coverage thật của UI, trial độc lập; SEO nội dung/đích không chỉ parse | G07–09 |
| Factory/pack | E3 cho starter web-api-ts và bản dev trong pilot đã ghi; site-cms E1 | chứng minh lựa chọn đúng gói, chỉ đăng supported đúng phạm vi; brownfield không đổi stack mặc định | G06, G09–11 |
| Agent/harness | E2–E3 theo CLI/host hiện hỗ trợ; vai, loop, evidence, policy, checkpoints | mech route/cost, high/120 thực thi, review đủ tư cách, eval thật, giảm context không mất constraint | G01–02, G10, G12 |
| Guard/trust | E2–E3: corpus, fuzz, mutation, source loader; ADR nêu giới hạn | không phải sandbox; sửa 541/572/573, fallback core; policy/loader/host trust và bản cài | G03, G08–09, G12 |
| Cấu trúc lõi và test | E2: nhiều module anh em, Core(Protocol), profile/closure tool | hai entrypoint sát cap, graph còn xấp xỉ; test nóng; dependency và lookup thực, installed parity | G12 |
| CI, chất lượng, release | E3 lịch sử: Gate, 100% line+branch được báo ở release, mutation, attest, branch ruleset | đo hiệu quả thực; review trigger hạn 02/12; tag/release recovery và immutability live chưa đủ | G01–03, G08–09 |
| Telemetry/flow | E2: slice ledger, run evidence, baseline 20 PR | nối đủ producer/attempt và export; cost unknown; đo cả failed/partial; không nhầm runner-minutes với USD | G02, G10 |
| Phân phối/đa host | E2: .pyz prototype, contract surface, toolcfg, adapter | P2 nối thực còn sau P2a; P3–P6 chưa hoàn tất; chứng nhận theo host/layout/OS; giữ fallback | G03, G09, G11–12 |
| Vận hành/registry | E2–E3 trong thử nghiệm dev, 6 đích ghi registry | provenance/receipt/SLO theo đích, restore dữ liệu và canary thật khi được phép | G10–11 |
| App cục bộ | E2: catalog, compose, blueprint, plan, PR/loop, registry; 127.0.0.1 | biến dữ liệu có bằng chứng thành màn đọc hiểu; không dựng control plane điều khiển mới | G05–06, G09–10, G12.6 |

**Kết luận:** nền tảng đã vượt mức thư viện checklist đơn thuần. Điểm nghẽn chính là chuyển yêu cầu → lựa chọn → thực thi → bằng chứng → giao hàng thành một tuyến kiểm chứng nhất quán. Chưa có cơ sở gọi framework là factory đa nền tảng production-ready cho mọi loại sản phẩm.

## 28. Kiến trúc đích điều chỉnh: một nguồn sự thật, nhiều projection

Giữ modular monolith. Các lớp logic đã chốt ở §1–25 không thành sáu service. Chọn bốn lớp chạy: (a) dữ kiện/yêu cầu/contract; (b) quyết định và điều phối; (c) adapter thực thi/Guard; (d) chứng minh và trình bày. Source map hỗ trợ cả bốn, không cấp quyền. Tách control-plane (PLAN, state transition, review, release) khỏi data-plane (mã sản phẩm, logs, fixtures), nhưng không dựng server cho mỗi lớp. Đường ghi state có owner, schema, lock/revision, validate và CAS phù hợp; nguồn ngoài/diff/comment/prompt được xem là dữ liệu.

| Đối tượng | Nguồn có thẩm quyền | Projection/nối mới |
|---|---|---|
| Yêu cầu áp dụng, miễn trừ | framework ID + PROJECT/SPEC/BLUEPRINT và quyết định | Context/decision snapshot, source revision, lý do miễn trừ |
| Việc và phụ thuộc | PLAN, loop state/evidence | Mốc task trên main, blocked/deferred, file ownership; không ghi tay state |
| Năng lực/gói | pack.json, profile, version/compat, acceptance CI | Capability registry/projection với supported/partial/experimental/unsupported/unknown |
| Hành vi và phạm vi | code, contract-surface, Guard policy, tests | 8 map §16; không chép source code/luật vào tài liệu tay |
| Chạy và chi phí | runs/slices, review, CI, receipt | attempt id + source identity, export bất biến theo revision |
| Phát hành/đích | VERSION, artifact digest, release-verify, DEPLOYS, registry | release/canary view; unknown khác false, defer khác pass |

**Chỉnh đề xuất CLI:** README ở main đã có lệnh context --task T-NNNN [--json] [--plan F], gồm ID, đoạn spec, Gate, files, thiếu file và số byte; plan waves --handoff, blueprint-status --strict --run, test-select, guard-profile, registry, app đã có. G12.6a bắt đầu bằng công cụ AST đọc riêng như §19 và mở rộng **context hiện có** qua module anh em/contract tùy chọn. Không tạo Context Resolver cạnh tranh, không chuyển toàn bộ sang kiến trúc mới một lần. Chỉ thêm namespace code khi task thật không giải quyết được bằng lệnh hiện có; dữ liệu schema version + required/optional/omitted/unknown + căn cứ source, fallback grep/full suite. Hợp đồng cũ phải giữ theo ADR-0097 và tests/fixtures/contract-surface.json; mỗi thay đổi công khai có compat test, tài liệu và quyết định. App chỉ đọc projection qua cùng adapter; không giữ một bản state riêng.

## 29. P0 — Trust, quyền và review thực thi được

### 29.1. Ranh giới tin cậy và cơ chế an toàn

ADR-0108 nói rõ Guard là hàng rào heuristic cho agent làm đúng quy trình, không cô lập được agent cố ý vượt rào. Vì vậy không tăng số regex rồi gọi đó là sandbox. Tách ba lớp độc lập: (1) hướng dẫn/Guard/contract quyết định; (2) giới hạn thực thi của host (filesystem, process, quyền mạng và thông tin xác thực theo phạm vi) khi môi trường hỗ trợ, sandbox opt-in có bài thử; (3) GitHub ruleset, danh tính reviewer/phát hành/deploy và bằng chứng không thuộc quyền ghi thường của agent. Không thử vượt Guard để audit; test dùng repo/fixture cô lập và entrypoint được phép. Giữ đường khôi phục hợp lệ. Các dữ kiện AUD-HAR-572/573/574 và lỗi core được sửa riêng với parity trước extraction. Không đổi fail-open/deny ngoài scope đã duyệt trong PR move-only. Không dùng index, cache, output model hoặc "confidence" để cấp quyền, quyết định merge, skip Gate.

API ruleset 25128933 tại ngày đọc: main active, cấm xóa/non-fast-forward, 5 required contexts (quality, protection-guard, dep-audit, gitleaks, pack-npm-audit), strict up-to-date, squash, required_approving_review_count=0; API includes_parents trả ruleset main, không có tag rule trong danh sách quan sát. xt.yaml hiện merge_review: optional, merge_hard_exceptions: auto, merge_autonomy: L3, delivery_phase: harden. Đây là quyền thật đã chọn; không tự đổi cấu hình. Cần đối chiếu với ADR-0095 (review sớm lớp tác động tức thì) và release-sign: test PR chạm guard/loader, workflow đặc quyền, approval ledger, release/promotion, acceptance lock; máy phải mô tả đúng làn và điều kiện ở head. Đề xuất ADR riêng nếu muốn enforce review theo rủi ro thay cho kỷ luật; giữ L3 cho phần được giao, không biến tất cả PR docs thành review bắt buộc.

T-4007: chủ quản trị xác nhận live tag rule, danh tính phát hành giới hạn, immutable release; T-5020 diễn tập trên tag/artifact thử được phép (không phá bản phát hành thật). Verify đúng repo, ref, builder/workflow identity, SHA/digest, expected provenance, asset/receipt; thiếu/chệch → fail. Chỉ dùng SLSA build/source track và NIST SSDF để lập ma trận kiểm còn thiếu, không tự xưng đạt level/chứng nhận. L05 kết hợp P2–P5 ADR-0097: tách runtime đã attest khỏi cây code dự án ghi được; ghi trust boundary theo layout. Chưa có bằng chứng host/sandbox thì ghi giới hạn, không tuyên bố cách ly.

### 29.2. Review: áp dụng D-623 trên tất cả tuyến, không làm yếu tiêu chuẩn

Đã đọc D-623 trong PR #846: reviewer-alt chỉ Opus trở xuống, effort tối đa high; lý do cùng họ cao hơn chỉ đúng khi effort người viết thấp hơn high. Cả reviewer/reviewer-alt giữ mặc định và trần high, maxTurns 120 (80 → 120); không đổi REVIEW_ROUNDS, max_rethink, hoặc ngân sách tiền hiện có. Cặp high/high cùng họ không thành clean; top/model không hợp lệ, effort unknown/override không chứng minh được không thành clean. Người viết tầng sâu giữ năng lực, không hạ chỉ để review xanh. Với PR cần review, thiếu route hợp lệ thì INCONCLUSIVE + giữ chặn/nợ theo đúng policy; không dùng nợ để vượt điều kiện merge bắt buộc hoặc release. Reviewer phải độc lập và đọc đủ scope; kết quả evaluator sản phẩm không thay reviewer code.

**Khoảng trống mới xác minh trên workflow:** .github/workflows/pr-review.yml (main) dùng route headless riêng, --max-turns 40, --max-budget-usd 2, --model từ XT_REVIEWER_MODEL, chưa khai effort, lệnh ghi chỉ --reviewer-model và schema verdict chỉ clean/blocking. Frontmatter không chi phối tuyến này. 40 là trần thấp hơn 120 của tuyến CI, không tự tăng chi phí; đồng bộ một nguồn policy và ghi rõ limit có hiệu lực, nếu owner muốn 120 trên CI thì phải thử với ngân sách đã được phép, không mở rộng tiền. Thêm verdict partial/inconclusive, missing/truncated/timeout/unknown → không ghi clean; check model/effort trước launch và khi ghi ledger. Kiểm mọi host (Claude local/CI, bản sinh Codex, fallback), mapping env/invocation/frontmatter, dấu review ở head, policy revision; host chưa chứng minh cap ghi unsupported/pending. Test override XHIGH/MAX, top tier, stale SHA, sai reviewer, hết turn, output lỗi, không đủ diff và cặp không đủ năng lực.

**Giả thuyết cần kiểm trước khi sửa:** workflow tải diff theo số PR lúc chạy nhưng HEAD_SHA lấy từ event. Khi head đổi giữa lúc lấy diff và ghi review, cần chứng minh cơ chế hiện hành từ chối mismatch (chưa đọc đủ thân pr reviewed, chưa tái hiện); concurrency không tự chứng minh snapshot. Thiết kế review bundle ghim repo, PR, base/head, diff digest + completeness; kiểm HEAD trước/sau lấy và trước ghi, pin compare đúng SHA hoặc trả stale/inconclusive; một ca cập nhật head khi fetch trễ bắt buộc. Không coi đây là lỗi đã xác nhận.

### 29.3. Hạn 02/12/2026 — tách đặc quyền workflow review

> **Revision 4:** đợt 0 chỉ gỡ trigger (`T-5064`); thiết kế tách đặc quyền dời tới khi bật lại review trên CI.

PROGRESS.md đã ghi bỏ pull_request_target khỏi pr-review.yml trước 02/12; GitHub Docs xác nhận chính sách mặc định với repo public bị ảnh hưởng bắt đầu cưỡng chế ngày này. Trạng thái policy riêng của repo và biến XT_REVIEWER_ENABLED không đọc được trong lượt này; baseline cũ có run review skipped, không suy trạng thái live. Ưu tiên rà trước hạn. So sánh hai tuyến: review chỉ đọc chạy ngoài workflow do phiên/tài khoản có quyền (đơn giản khi không cần chạy CI reviewer) hoặc workflow tách privilege (job/dispatch được kiểm quyền, chỉ đọc diff như dữ liệu và checkout mã trusted default branch; khâu publish chỉ nhận kết quả cấu trúc đã xác minh head). Không checkout/chạy mã PR trong môi trường có secret; workflow_run cũng là đặc quyền, không mặc nhiên an toàn; artifact/output từ PR không được thực thi. Giữ danh tính độc lập, token tối thiểu, không ghi secret, fail nếu thiếu bằng chứng; fork chỉ báo theo quyền hiện có. Thiết kế, test bằng fixture rồi mới chuyển; nếu cần admin/secret giữ pending-human. Không xin bật lại pull_request_target mặc định chỉ để CI xanh.

## 30. Tối ưu kiến trúc, test và CI theo chi phí toàn vòng đời

### 30.1. Tách mã và test đúng ranh giới

Tiếp tục §19 và ADR-0090/0093: inventory AST/symtable, closure qua import, assignment, bảng callable, alias, caller ngoài cụm; ghi dynamic/unknown; SCC giữ nguyên khi chưa có seam. xt_guard_profile.py hiện dùng ast.Name gần đúng theo tên, không theo các vế khởi tạo hằng qua closure (AUD-ARCH-019 mở). Mở rộng chung extractor theo task này, không viết một analyzer thứ hai; có ca hằng dựng từ hằng, shadowed name, decorator, default args, dispatch table, import alias, nested scope, lỗi cú pháp. Kiểm closure bằng thủ công/fixture trước khi dùng quyết định tách. MVP không thực thi module để lấy symbol. Source map hash working tree, phạm vi worktree, UTF-8, file rename/delete; untracked source chỉ khi được phép và trong scope, loại ignore/cache/secret. Dữ liệu dirty không được nâng thành evidence của commit. Map có confidence và fallback, không thay test-select/full Gate.

Tách XT một cụm leaf (shard/weights hoặc contrast sau đo L05) trước khi nối mech/cost đòi cap; giữ CLI, argv/exit/output, Core(Protocol), manifest, .pyz và perf trial. Guard sửa core fallback trước baseline hành vi; T-3996 và ADR bổ sung nếu đổi thứ tự, T-3987…3990 loader/fence + cụm đủ chạy. Module thực thi mới vào typecheck, coverage, install và pack đồng thời. Tách tests/test_hooks.py, test_merge.py, test_xt_cli.py **sau khi có baseline test identity và module graph**: chia theo hành vi (loader, hook mode, merge rule, CLI contract...), fixture builders dùng chung có tên/owner; không sửa assertion chỉ để coverage xanh. Dữ liệu fixture giữ ID, mode, policy. So inventory lớp/test ID trước–sau (mapping rename rõ), shard-weights/test-select, patch đúng nơi lookup, mutation/fuzz và toàn suite; không tự chuyển tên test làm consumer mất ca. Tách install.py sau #840 và kiểm fault matrix, tránh một PR vừa thay hành vi ghi vừa di chuyển. Entry point nhỏ là đích dài hạn, không tối ưu số dòng bằng chuyển nguyên khối hoặc wrapper rỗng.

### 30.2. CI: không đổi 100% coverage để tiết kiệm

ci.yml ghim Actions full SHA, permissions contents:read mặc định, persist-credentials false ở job đọc, Python chính 3.15.2 + compat 3.13, requirements-dev hash, 8 test shard, test-main, 8 compat shard, coverage fan-in, quality tổng hợp. dev-task.sh có pipefail cho bash -c, phát hiện 0 test, fallback full suite khi không biết mapping. Giữ các điểm mạnh; không mở lại như lỗi. Mutation Guard có workflow lịch/dispatch, chưa đủ thay cho mutation ở lát critical. .coveragerc đo dòng + nhánh + subprocess. Cổng 100%, mypy strict, C901 ≤10, required check và oracle giữ nguyên. Khi đổi partition, chạy chính tập test trên cả hai cấu hình, chứng minh không mất test/trùng, mỗi shard có evidence và coverage cùng source/head, artifact thiếu/cũ/duplicate gây đỏ; phần compatibility smoke không thay chứng nhận host.

Dùng baseline T-4010 ngày 26/11: 20 PR merge, 180 run, 1.033 job, 2.729,4 runner-minutes, median 118,7 phút runner/PR; 29 run ở head cũ; 3 PR nhiều push dùng 759,8 phút (27,8% tổng của mẫu, **không** phải toàn bộ chi phí có thể tiết kiệm); median PR→merge 12,7 phút; 4 dấu review đã đăng (3 PR), chưa đo local review, tiền hay post-merge run. L01/C08 đã tối ưu; đo lại theo đúng N1–N7 trên mẫu kế (20 PR, nhóm theo loại/rủi ro, ghi sample và head), bổ sung queue, p95 shard, retry, post-merge và ledger cost. Không quy số phút thành USD, không giảm cổng vì sample xanh.

Ưu tiên L02 (trọng số/shard/tripwire); C21 chỉ khi đo sau L01/C08 còn lãng phí; đo chi phí khởi động/interpreter, download/cache/hook end-to-end theo workload, không suy từ compile. Chọn test nhanh bằng dependency graph + hiện hữu test-select, ca unknown/đổi policy/build/config/cross-module chạy rộng; CI merge và release đầy đủ. Dùng artifact build một lần cho cùng input khi digest/hợp đồng chứng minh, không dùng artifact của run không tin cậy trong job đặc quyền. Chỉ thử rút ngắn CI cho docs có safe classifier + oracle trước, không đổi required checks, không tắt scan; so full và classifier trên tập diff historical/holdout, bỏ sót critical = 0, không đủ dữ liệu giữ như cũ.

## 31. Sản phẩm, kiến trúc, UI/UX và lựa chọn pack

Bộ chọn trong G04–06 phải hiểu mục tiêu, tác nhân, dữ liệu, nền tảng, rủi ro, constraint, môi trường, ngân sách và nguồn. Một profile chính như compose đã quy định, hợp đồng component khác tham chiếu qua module/profile phụ; industry 0..n; scale theo rủi ro. Loại candidate vi phạm hard constraint trước ranking; missing proof → needs_evidence chứ không tự chọn mặc định. Capability ở mỗi tổ hợp (profile, pack version, OS, host, layout, runtime, evidence build, support_until); supported chỉ khi starter/managed/lock/compat/acceptance thật. web-api-ts pack.json hiện khai profile web-app/api-service, Linux, Claude Code, support_until 21/01/2027. README xác nhận harness chủ yếu POSIX/Linux + Claude/Bash/GitHub; macOS chưa có CI, Windows qua WSL2/container. Không gọi 14 profile là 14 stack sẵn sàng hoặc tuyên bố native cross-platform.

### 31.1. Hai tuyến sản phẩm có nhu cầu, không mở đồng loạt pack

| Tuyến | Hiện trạng | Nghiệm thu mới |
|---|---|---|
| web-api-ts | starter nhiều tenant, Postgres RLS, worker lease/idempotency, contract, test restore, dev preview; có pilot lịch sử | G07/G08 và T-5012/5013: browser thật từ installed-copy, UI state + keyboard + axe + reflow/zoom; test sai critical tenant/auth/migration/restore; dữ liệu phát sinh khi B chạy, receipt và phục hồi phù hợp |
| site-cms-ts | PR #851 chốt kiến trúc đề xuất Astro tĩnh + Decap CMS Git-backed, OAuth proxy, MFA ở Git host; chưa có starter | T-5057…5060: xác minh constraint trước chốt gói; nếu khách không dùng Git host/cần DB hoặc MFA native thì unknown/no_fit hoặc chọn phương án đã nghiên cứu lại. Kiểm OAuth state/CSRF và callback/proxy permissions, enforce MFA ở host bằng bằng chứng, không có secret ở site tĩnh, sanitization preview/XSS, quyền biên tập và audit, rollback nội dung và rebuild, robots/sitemap/JSON-LD khớp nội dung, reduced-motion, desktop/mobile, mutation từng lớp; chưa chứng minh không ghi supported |

Không nhận khẳng định advisory/licence/version CMS của bản nghiên cứu #851 như bằng chứng mới của lượt này; khi implement xác minh lại phiên bản ghim, phạm vi advisory và license. T-5055/5056 là nghiên cứu/ADR ở PR mở; không viết lại stack. Cơ sở chính: ADR-0109 và PLAN-site-cms. Không dùng pack mới để ép dự án đang chạy đổi stack. G06 registry tối thiểu dùng hai candidate theo tiến độ thực tế; không mở pack mobile/desktop/AI/ERP cho đủ bảng. Lựa chọn pack khác cần nhu cầu pilot, owner và hợp đồng test.

### 31.2. Duyệt thiết kế, trải nghiệm thực và SEO

Giữ DESIGN-EVIDENCE schema 1 + VALIDATION của §4B, không đồng nhất hồ sơ cấu trúc, đủ constraint, UX kỹ thuật, trial và field outcome. #849 đã giữ khai khách và nhận module xt_design; main xt_design.py lock_reason vẫn mở khi status=approved; #847 có hash nội dung + pending logic nên rà/merge vào base mới, không tạo lỗi trùng. Cần ca đối chứng: khách duyệt bản A, B thay đổi nhưng sổ cũ; bản sửa/xóa/rename/symlink, external design URL/version mutable, squash/shallow, task sửa UI nhưng khai sai scope; chỉ người có quyền duyệt lại. Hash một tệp evidence không tự chứng minh hình mockup/link đã được duyệt: nếu có nhiều artifact thiết kế, manifest tham chiếu/version/digest đúng phạm vi; tài nguyên ngoài không xác minh được giữ pending. Kiểm khi submit/approve/consume (race dưới lock, snapshot đổi); không tự tạo approval, không agent bỏ dòng khai để nới. ADR-0108 ghi giới hạn trình nhầm ở dự án khai không: từ chối design-submit mới khi không khai khách và chưa có sổ, hoặc đưa vào #847/lát riêng sau đối chiếu. Cần ca ui: và actual diff phù hợp, chưa có oracle tuyệt đối nhận mọi thay đổi UI.

Reflow Shadow DOM (AUD-HAR-567) và ma trận CSP/axe (AUD-HAR-562) phải thử đúng build thật; chưa đo được → UNMEASURED/not_tested. Dùng WCAG 2.2 AA đúng scope, design rubric bốn tiêu chí §11, grader chủ quan hiệu chuẩn với người; không giảm ngưỡng theo cảm tính. SEO FE-RENDER-019/020/021 đã là yêu cầu trong main; test HTML build và header, sitemap canonical/lastmod, admin noindex không phải cơ chế auth, Search Console và DNS xác minh cần người/đích thật; IndexNow chỉ máy tìm kiếm hỗ trợ, không suy index/ranking từ API 200. Bằng chứng SEO kỹ thuật, lập chỉ mục và conversion tách riêng. G07 làm design token, accessibility, content state và prototype có giả định; G08 khóa kiểm nghiệp vụ trước mã, cùng SPEC public, test độc lập.

## 32. Nghiệm thu, Agent Harness và sổ sự kiện

T-5009/5010/5011 là đường găng của G02: SPEC-slice-ledger §2.3 chỉ ghi cost lượt Gate xanh ở bản hiện có và sổ theo checkout; không thay bằng analytics service mới. Ghi mỗi attempt có id, owner, head, policy/host/effective effort, kind, start/end, exit/cancel/partial, cost input/output/cache nếu có, đơn vị/nguồn giá, review scope và event id; producer thật từ loop init/record, pr next/reviewed, receipt deploy và incident. Export gộp cross-worktree idempotent; duplicate cùng id cùng data chỉ một, conflict khác data cảnh báo; thiếu/không đọc nguồn → partial/null, không 0. Không log prompt/source/bí mật mặc định, redaction và retention. Reconcile field evidence đúng release; cost ở local/CI/failed/timeout included khi có, không tái tính cùng attempt. Đo baseline §30, G10 pilot và A/B/C §22 bằng cùng task, head, fixture, model/effort và budget. T-3851/3852/3853/3854 về scope/parallel/shared file/worker ngoài phiên đã có PLAN factory; chưa bật worker mới nếu thiếu lock/owner/test và số đo. Phiên chính điều phối; mặc định self cho lát nhỏ, reviewer khi yêu cầu, parallel khi độc lập file/contract, evaluator ở task product risk; không tăng số agent, context window, turn cap ngoài yêu cầu chỉ vì model mới. Xác minh /review, /factory, /autopilot, mirror và host; test hành vi không chỉ tìm chữ.

Đánh giá tối thiểu 24–36 tình huống từ AUD, review lỗi và pilot, holdout, lặp nhiều lần; nhóm: no-fit/unknown, dirty source/index, dependency/patch/test, policy/loader, review stale/head + cap, compaction, pack selection, UI state/design approval, restore/release, quyền thiếu. Mỗi ca có required context + oracle độc lập, critical pass^k, false block, miss, cost/latency cả pipeline. Các ngưỡng chất lượng cứng khóa trước eval; không đổi testcase sau khi thấy kết quả để đạt. Baseline so A (lệnh hiện hữu), B (map tối thiểu), C (resolver/cache nếu cần); test agent thật và solo/harness cùng budget. Gate 100% coverage là yêu cầu kỹ thuật, không thay oracle nghiệp vụ, threat model hoặc outcome. Phần model grader có hiệu chuẩn, chưa có người/field/restore thì không gọi production-ready.

## 33. Phân phối độc lập, compatibility và vận hành nhiều repo

ADR-0097 đã chọn .pyz tất định + launcher mang tên đích, tool.json contract/min_contract, overlay không nới guard, nâng artifact và render riêng, migration có phiên bản. PLAN-tool-independence: P0–P1 đã làm, T-4205/P2a module xt_toolcfg đã ghi [x] nhưng chưa nối XT; P2b–P6 chưa chứng minh hoàn tất. Không phát minh X-Core runtime cạnh tranh. Chọn thứ tự: L05 chốt trust + perf trial và layout → tách XT/Guard an toàn → P2b nối resolver + contract test → P3 tên/launcher → P4 build/attest/verify .pyz đúng bytes → P5 artifact layout/guard hooks + upgrade/downgrade/fault → P6 reusable workflow ghim SHA khi đã đủ chứng nhận. Có thể chuẩn bị P2/P4 song song không chạm file nóng; không trộn đổi tên/di chuyển/đổi policy trong một PR. .pyz có cùng module/surface, digest trên đúng artifact, không dựa cwd hoặc checkout, không tin overlay/bytecode không được phép; test thiếu companion/trộn version/pyc/site/dirty install/đổi tên/đường Unicode & space, clone nông, cùng process hai version, lỗi publish, rollback đúng bytes, no-op version. Không suy .pyz tự nhỏ dưới 1 MiB (ZIP_STORED có số đo latency, kích thước cần đo artifact cuối); X-Scanner ngoại lệ D-609 giữ đến 21/01/2027, D-610 không nâng đích.

Registry schema 1 ở main ghi 5 core 3.34.0 (hotel-manager, X-Company, xboss, dhcb, x-shop), một 3.29.0 (X-Scanner); cả 6 có type/risk/pack/release null, environments rỗng, SLO rỗng. Đây là **ghi nhận trong registry**, không kiểm live các repo đích; không coi null là không có môi trường/sự cố. G11 nâng provenance (observed_at, repo/default branch/ref, version/digest, host/OS, evidence, status current/deferred/unknown/unsupported, expiry/owner), TARGETS/registry một nguồn chính + projection/compat test. Sau khi có quyền, read-only reconcile bản cài/receipt và thời điểm; chạy canary trên đích được phép, receipt digest khớp, health/negative case, window đủ, RPO/RTO theo sản phẩm, diễn tập rollback cả dữ liệu. Không tạo PR nâng đích, không triển khai production dưới D-610; Hotel Manager pilot mới trong scratch hoặc môi trường được phép, không tự áp core mới vào repo đích. Thiếu người, tài khoản, DNS, secrets, admin, production hoặc tiền thật thì defer và chỉ giao phần dev đã chứng minh.

Ma trận host tách khả năng đọc framework, CLI, hook enforcement, review effective limits, installed-copy, pack acceptance, field. Linux/Claude có nền kiểm; Codex/Gemini/OpenCode theo adapter và chứng nhận từng hành vi, không suy ngang bằng chỉ vì bản gương tồn tại. macOS thử CI/scratch khi có runner; Windows WSL2/container là đường POSIX, native chưa hỗ trợ khi fcntl/Bash/POSIX contract chưa thay. Không mở cross-platform runtime mới trước khi chứng minh nhu cầu. Đưa support_until và policy revision vào báo cáo để dự án biết giới hạn.

## 34. Dashboard, quản trị tri thức và độ mới

SPEC-app và scripts/xt_app/server.py đã có app local (127.0.0.1, Host/Origin/token, route allowlist, JSON body ≤65.536 B, API no-store, chỉ ghi BLUEPRINT theo hợp đồng); không cần viết dashboard/control plane mới. G09/G10/G12.6: thêm màn đọc sau khi CLI/projection có schema ổn định: (1) capability/decision, lý do candidate và bằng chứng thiếu; (2) task/dependency/owner và head; (3) audit theo risk/expiry/PR; (4) CI/ledger chi phí và unknown; (5) artifact/registry/rollback; (6) code/context map cho task với link file/symbol/hash. Phân biệt xanh của test, approval, release và production; trạng thái stale/partial/deferred phải nhìn thấy và truy được source. Không thêm nút merge, deploy, cấp quyền hoặc execute tool ngoài hợp đồng SPEC-app; nếu cần action phải có SPEC/ADR quyền riêng, test CSRF/auth/permission và rollback. Giữ loopback, kiểm Host/Origin, token không vào URL log, no-store, render text ngoài là dữ liệu; test route đầy đủ từ bản cài .pyz/layout và CWD khác, Unicode/large results/truncated; không nạp plugin tùy ý từ target.

Quản trị tri thức: từng requirement/standard/procedure giữ ID và source, ngày/phiên bản đọc, effective date/phạm vi, owner, review_due; kiểm source sống cho quyết định có ảnh hưởng lớn. Không nhân bản văn bản pháp luật hay tạo một danh mục song song; registry projection đọc một nguồn. NIST SSDF 1.1 SP 800-218 vẫn Final, 1.2 Rev.1 ở trang NIST là Draft tại lượt đọc; chỉ dùng đối chiếu phương pháp, không đổi chuẩn mặc định vì draft. Hợp đồng approval/policy/guard/CI/pack cập nhật thì invalidation đúng dependency, không dùng stale proof. Research, audit và PLAN có bản đang dùng + archive chỉ đọc giữ ID/links/provenance (C23); PROGRESS giữ 8 KiB và SessionStart <=9.800 ký tự theo ADR-0091, chỉ pointer/delta/next action, không nạp toàn sổ audit/blueprint/plan. Agent tiếp tục sau compaction theo checkpoint, không bắt đọc toàn bộ doc. Sổ 362 mục mở ưu tiên bằng impact/expiry, phân loại false positive/accepted/known issue/reproduce needed; evidence không có ghi rõ, không sửa trạng thái tự động chỉ bằng suy đoán.

## 35. Kế hoạch thực hiện hợp nhất: giữ G01–G12, thứ tự theo rủi ro và dependency

> **Revision 4:** bảng R0–R6 hết hiệu lực về thứ tự — xem §0.5 (có task ID, tệp, phụ thuộc, Gate cho từng PR). #840, #847, #851 đã merge.

Các mã R0–R6 dưới đây chỉ là đợt triển khai đề xuất, không phải task ID mới. §23 và §24 vẫn là nhà các lát G12.0–.7, I0–I5 và 31 lát; bảng này chỉ điều chỉnh thứ tự và nối phần đánh giá toàn hệ. Đóng từng PR, một owner mỗi path nóng, không lập một mega-PR; mở worktree độc lập khi files/contract không giao; cổng hiện có không hạ. Trước thực thi, lấy main mới, reconcile PR/PLAN/AUD/ADR và quyết định thật. Các PR đang mở có thể thay đổi, kiểm lại.

| Đợt | Ưu tiên/nhà | Đầu ra, điều kiện chuyển |
|---|---|---|
| R0 — chặn rủi ro hiện hữu | G01/G03/G07/G08; PROGRESS hạn 02/12; T-5041, #840/T-5043, #847/#849, AUD-HAR-567/T-5013 | Đối chiếu PR chưa merge; đổi tuyến review đặc quyền/contract (không bật live khi thiếu quyền); test tag + design hash + UI measurement, sửa theo từng PR; mở phần L05/572/573 và core bugfix. Admin T-4007/T-5020 chuẩn bị checklist song song, không giả xong. |
| R1 — giải phóng lõi và inventory | G12.0/1/2/5/6a; AUD-ARCH-019, T-3995 đã có, L05, C14/15 | AST map tối thiểu và oracle closure, phiếu lát XT leaf; Gate/installed/perf trial/contract; hạ cap. Guard sửa core rồi baseline, ADR/loader/fence/companion và parity. Không bắt mọi lát chờ cache. |
| R2 — Agent/review/ledger | G01–03; D-623, #810, T-5040, T-5009…5011, G12.6 | hai role high/120 và Opus, host caps thực thi; route CI/headless riêng được kiểm; mech + escalation, cost failed/partial, export, freshness context hiện có. XT sửa sau có headroom; Guard không đổi policy ngoài PR riêng. |
| R3 — chất lượng và hiệu năng | G08/G12.3/4/6b/7; L02, C15/16/21/22/23/24, test nóng | Tách XT theo miền, Guard theo SCC, test identity, type/coverage/mutation/parity, loader matrix. So A/B/C và CI baseline; cache chỉ khi lợi và không làm sai, archive giữ ID; không làm fast path guard nếu chưa ADR/oracle. |
| R4 — sản phẩm và gói | G04–09; T-5012/13, T-5057…5060 sau #851, #847; PLAN-factory-e2e | Có thể chuẩn bị SPEC, decision/capability, prototype và acceptance độc lập song song R1/R2 (không chạm file nóng). web-api-ts trial/restore và site-cms scratch theo constraint, host/pack CI + mutation, hash approval; không dùng mẫu cũ làm feature mới. |
| R5 — phân phối, app và đo đầu-cuối | G03/G09–11/G12; ADR-0097 P2b…P6, T-5017/5018/5020 theo quyền, SPEC-app | .pyz/layout contract, verify/cài lỗi/upgrade/downgrade; local app evidence view; agent eval, pilot dev với receipt/behavior, phần prod/canary chỉ sau đủ điều kiện và D-610 được thay bằng quyết định có thẩm quyền. |
| R6 — mở rộng có điều kiện | G10/11 và G12.7 | Chỉ tăng host/pack/agent khi metric và evidence đạt; debt review theo lô, accepted expiry, support_until. Không tuyên bố tự chọn mọi stack, production hay giảm chi phí nếu chưa đo. |

Đi song song có điều kiện: PR docs/contract/UI prototype không giao file với XT/Guard; T-5057…5060 theo PLAN site-CMS; ledger/mech/CLI sau lát XT headroom; loader/fence/Guard sau baseline fix. Deadline đã ghi: 02/12 pr-review và AUD-HAR-567, 15/12 nhóm accepted của release, 31/12 AUD-HAR-572…574, 21/01/2027 review Guard/D-609/support pack. Không tự đặt deadline hoàn tất toàn hệ; ước lượng sau lát đầu và baseline. Giữ Cửa A–E, I0–I5: R0/R2 phục vụ A; R4 phục vụ B/C; R1/R3/R5 phục vụ C; R5/R6 phục vụ D/E đúng quyền. G12 có thể tiến song song, không cản pilot được phép.

## 36. Phiếu nghiệm thu bổ sung và bộ bàn giao

Bổ sung vào acceptance từng lát, không tạo gate vũ trụ mới:

| Miền | Điều kiện không được giả xanh |
|---|---|
| Hợp đồng/traceability | ID nguồn, revision, scope, owner, expected/actual, command + exit, head/digest; nguồn chưa đọc/không đủ bằng chứng giữ unknown |
| Source intelligence | mọi symbol trong fixture có phạm vi đúng; hash/revision drift, dirty rename, alias/assignment/dispatch, stale/failure; không bỏ required context/critical test; fallback direct read/full suite |
| Reviewer | D-623 và high/120 thực tế ở vai; CI lower cap khai riêng; route độc lập đủ capability; head/diff digest và completeness; partial/unsupported ≠ clean |
| Guard & installed runtime | raw + final parity cả 2 mode, ca cho phép/chặn, 5 loader, companion/fence, failure isolation, không đọc bytecode vùng không tin; coverage 100% line+branch và mutation/fuzz đã chọn |
| Delivery & release | 5 checks hiện hữu, Gate không hạ; candidate/tag/asset/receipt/recovery đúng identity, live/admin pending riêng; lỗi retry không báo success giả |
| Pack & UI | supported chỉ đúng host/OS/layout/version; lock, installed test, critical mutant, design approval đúng version, browser/axe/reflow, SEO đúng scope; người/field chưa thử ghi pending |
| Ledger & efficiency | 9 loại sự kiện thật + mọi attempt có usage nếu có; dedup, source coverage, partial; so N1–N7 và A/B/C, chất lượng không giảm, ngưỡng hiệu năng khóa sau baseline |
| Quản trị & mở rộng | không mất task/ADR/decision/ID; accepted expiry; registry provenance và rollback; không rollout đích dưới D-610 |

Mỗi PR bàn giao phiếu base/head/paths, thay đổi hành vi hay move-only, phạm vi oracle, dependency impact + unknown, test/CI kết quả thật, installed artifact, benchmark (khi tối ưu), review và đường revert. Khi có bug critical chưa đủ reviewer, không hợp thức hóa APPROVE; record INCONCLUSIVE, xử theo policy. Hợp đồng artifact và field receipt được kiểm từ consumer sạch, không chỉ checkout tác giả. Bản cuối chương trình cần chỉ rõ 12 gói nào đủ Cửa A–E và phần nào pending; không đánh đồng việc đã viết kế hoạch với đã triển khai.

## 37. Nguồn, phương pháp và giới hạn lượt Revision 3

Nguồn repo đọc 27/11/2026, ghim main 045622d7484203e9e849f8f509243fdc2f88d663: [cây Git](https://github.com/www-donghanhcungban-org/X-Templates/tree/045622d7484203e9e849f8f509243fdc2f88d663), [delta sau 259ac21c](https://github.com/www-donghanhcungban-org/X-Templates/compare/259ac21ca160ad05a7b91a780667b06f7366c016...045622d7484203e9e849f8f509243fdc2f88d663). Các nhà nội dung: README.md, xt.yaml, .coveragerc, PROGRESS.md, VERSION; docs/ops/AUDIT-STATUS.md, GO-NO-GO-2026-11-23-v3.36.0.md, registry.json, TARGETS.md; tests/test_docs_budget.py, scripts/xt_guard_profile.py, scripts/xt_design.py, scripts/dev-task.sh, scripts/xt_app/server.py; docs/specs/SPEC-app.md, SPEC-slice-ledger.md, SPEC-factory-intake.md; ADR-0097, ADR-0108; PLAN-harden-2026-11-24, PLAN-site-cms-2026-11-26, PLAN-tool-independence-2026-11-24, PLAN-factory-e2e; framework/02-profiles/README.md, 03-industries/README.md, 07-frontend/rendering-and-routing.md, 11-autonomous-loop/context-and-token-budget.md và orchestration-and-subagents.md, templates/packs/README.md và web-api-ts/pack.json/README.md; workflows ci.yml, pr-review.yml, release-tag.yml, pr-steward.yml, mutation.yml; research/2026-11-26-delivery-baseline.md. API ruleset main 25128933 và latest release là quan sát tại thời điểm đọc; không có quyền xác nhận settings/secret/host usage/live deployment đầy đủ.

PR tham chiếu: [#846 head trước Revision 3](https://github.com/www-donghanhcungban-org/X-Templates/tree/343881165e3b0352d2b0069d80990853be5aaa29), [#840](https://github.com/www-donghanhcungban-org/X-Templates/pull/840), [#810](https://github.com/www-donghanhcungban-org/X-Templates/pull/810), [#847](https://github.com/www-donghanhcungban-org/X-Templates/pull/847), [#849](https://github.com/www-donghanhcungban-org/X-Templates/pull/849), [#850](https://github.com/www-donghanhcungban-org/X-Templates/pull/850), [#851](https://github.com/www-donghanhcungban-org/X-Templates/pull/851) (ADR-0109 đọc ở f81778fc4ce5003ed71d07719ff98fd7c6b4bfe0). Đã đọc nội dung trước đó ở #846, gồm D-623; giữ lịch sử, không thay kết luận cũ không có delta.

Nguồn ngoài kiểm ngày 27/11 (chỉ dùng cho đề xuất): [GitHub Securely using pull_request_target](https://docs.github.com/en/actions/reference/security/securely-using-pull_request_target) (chính sách mặc định, hạn 02/12/2026 với repo public bị ảnh hưởng); [GitHub Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use) (đặc quyền, SHA pin, code/artifact không tin cậy); [GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations); [SLSA v1.2 Tracks](https://slsa.dev/spec/v1.2/tracks) (Build/Source); [NIST SSDF publications](https://csrc.nist.gov/Projects/ssdf/publications) (SP 800-218 final, revision 1.2 draft). Không coi việc tham chiếu là chứng nhận đạt chuẩn.

Giới hạn: census và phân loại audit được tính trực tiếp từ dữ liệu Git/API và hàng sổ; số benchmark/test trước đây là báo cáo repo, không chạy lại trong lượt này. Connector không trả đủ mã hai blob lớn hay corpus Guard khi đọc range; trạng thái 23.668/24.689 dựa mốc đo trước + delta, fixture có thay đổi ở #849; baseline parity phải lấy corpus mới, không cố định số ca cũ. Chưa kiểm mọi tệp, dynamic path, legal source, vulnerability advisory, native OS/host, user trial hoặc hiện trạng deploy của đích. Chưa tái hiện giả thuyết race review; không đặt ID lỗi cho tới khi oracle xác nhận. Không tuyên bố CI mới xanh khi chưa xem head. Chỉ cập nhật tài liệu nghiên cứu, không thay đổi PLAN, mã, cấu hình, phát hành hoặc dự án đích. D-610 và D-623 được bảo toàn.
