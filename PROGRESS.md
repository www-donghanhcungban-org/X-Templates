# PROGRESS.md — Khung X-Templates

> Giai đoạn hiện tại: G8 Vận hành & tiến hoá (khung 3.36.0, pha `harden` — D-136) · Cập nhật: 2026-11-24

## Đang làm

- 2026-11-24 **3.36.0 đã phát hành** (tag `v3.36.0` ở `42f3c64b`, agent ký GO-NO-GO §5, ADR-0074; release nháp → công bố có archive + biên nhận, `release-verify` attestation hợp lệ). Gồm #746–#765: rà sớm lớp tác động tức thì (ADR-0095), dấu review v2, sổ lát, release bất biến, `release-check` ba trạng thái. Rà: 2 🔴 AUD-HAR-484/485 sửa; [audit delta](docs/ops/AUDIT-REPORT-2026-11-23-delta.md) 0 🔴; 🟠 chấp nhận hạn 2026-12-15 (AUD-HAR-488, AUD-DEP-038, AUD-CI-043) và 2027-01-21 (AUD-HAR-478/479/480/487/492, AUD-CI-041/042/044; D-551, D-554). 3.35.0: tag `v3.35.0` ở `7fc43e74`.
- ADR-0081 (D-511, #673): `compose` giữ quy mô cũ, mặc định mới S; `doctor` ở build không cảnh báo chậm MINOR/PATCH.
- **Factory**: [MVP ghi chú](docs/ops/FACTORY-PILOT-1.md) có bốn ca xanh (#699); quyền triển khai, trần duyệt và G7 đã nối (#701); `feedback routine-check` (#700). Điều kiện vận hành và số đo còn thiếu ở [PLAN](docs/autopilot/PLAN-factory-e2e.md).
- **Guard** (#704, D-530): chặn đường lách tag phiên bản (`--follow-tags`, `fetch` vào `refs/tags/`, cụm cờ `gh release`, glob) — AUD-SEC-996/997 (#704), 999 (#707) đã sửa. Nợ 🟢: AUD-HAR-449/450/451/455/456, AUD-SEC-998, AUD-TEST-133/135, AUD-XFEAT-050.
- Dự án đích ([registry](docs/ops/registry.json)): X-Company, xboss, dhcb, x-shop và hotel-manager ở 3.34.0. [Pilot lọc tầng](research/2026-11-20-hotel-floor-pilot.md) từ checkout đến merge mất 18 phút 11 giây. Còn mở bài kiểm host Codex/Gemini.
- D-457: PLAN factory-A/BE đã lưu kho. `LOOP-ORCH-020`: chỉ tăng agent khi có số. [Đã phân loại 10 nhóm phản hồi công cụ](docs/ops/FEEDBACK-ROUTINE-CHECK.md). Hoãn: T-1690/T-1691 (quét lại SEC-091…099); rà `seeker19110/stored` chờ chủ repo (hạn xét 2026-12-31).

## Tiếp theo
1. Các đợt 16–18 đã merge (#676–#696): test 8 shard, harness Codex và bảo vệ tệp sinh. Nợ còn ở sổ audit; chưa chạy host Codex thật.
2. **Kế hoạch cải tiến** ([PLAN](docs/autopilot/PLAN-improve-2026-11-23.md), D-544): đợt 1–2 xong, phát hành 3.36.0. Còn: T-4007 (ruleset tag live, GitHub App phát hành, cần admin); T-4010 (baseline 20 PR/CI) là việc đọc dữ liệu có thể tự làm; T-3555; `test_field_trigger` đỏ ~12 phút đầu mỗi ngày UTC đã sửa ở #764 (AUD-TEST-152); tách sâu `guard.py` ([PLAN](docs/autopilot/PLAN-guard-split-2026-11-22.md), D-542) về đợt 4. Phiên `stored` merge tài liệu `framework/` vào `main` làm lệch vân tay GO-NO-GO — dừng chúng khi đang cắt bản. Ngoài PLAN: nâng 3.35.0 vào dự án đích (cần `XT_STEWARD_TOKEN`; X-Scanner 3.29.0, X-Agents 2.0.0 giữ nguyên); stored XT-H-117…139; `pre-push.sh`; AUD-HAR-436; AUD-TEST-126.
3. Hạn: 2026-12-02 bỏ `pull_request_target` khỏi `pr-review.yml`; 2026-12-31 rà stored; **2027-01-21** xét lại hàng rào guard + đánh giá sandbox Bash opt-in (D-331/D-332, ADR-0072) và các chấp nhận AUD-SEC-406/931/943/955/965.
4. Ruleset `main` đủ 5 check (2026-11-20); ruleset tag live chưa có. Việc của người: T-4007; xoá stash `d497-dup`, `d498-dup-x9`; `XT_STEWARD_TOKEN`, Dependabot security updates (RUNBOOK-PR-STEWARD §1).
5. Còn: máy hoá `LOOP-HARNESS-031`, `LOOP-STOP-030`; task `[perf]` trong `loop` (D-041); URL phiên do máy chủ MCP gắn vào thân PR; ép báo "đã đo/chưa đo" cho UI (`LOOP-DESIGN-021`); tách khung khỏi đích bằng `.pyz` ([PLAN](docs/autopilot/PLAN-tool-independence-2026-11-24.md), ADR-0097: P0–P1 xong).
6. #786 đã merge ở `08a9ad2`: [kế hoạch nâng trần](docs/autopilot/PLAN-ceiling-2026-11-24.md), D-573. Đang thực thi [PLAN-harden](docs/autopilot/PLAN-harden-2026-11-24.md), D-574: T-5021 sửa AUD-HAR-514; đang đưa SBOM/VEX, strict pack và parser tài liệu qua CI. Cổng đầu vào NO-GO (audit, review_debt); T-5020/5017/5018 chờ quyền admin, người thử hoặc môi trường thật. Không coi kế hoạch là triển khai xong.
7. Giữ cổng: C901 ≤ 10, `mypy --strict`, coverage dòng + nhánh 100 %, `changelog-check`, trần byte (`tests/test_docs_budget.py`, ADR-0043), không ngưỡng thời gian/CPU cứng (BASE-GATE-005), quy ước tên định danh ở `scripts/AGENTS.md` — không `noqa`/pragma; nới trần chỉ bằng ADR (ADR-0092).

## Quyết định
> Chi tiết ở `docs/adr/` và `docs/autopilot/DECISIONS.md` (D-NNN); ở đây chỉ giữ điều chưa có nhà khác.
- Khung = thư viện yêu cầu có ID + ghép blueprint + máy kiểm "xong" (ADR-0001); hook fail-open về luồng, fail-closed về hành động nguy hiểm (ADR-0002); blueprint theo quy mô S/M (ADR-0003/0004/0012).
- Luật VN: Luật 91/2025/QH15 + NĐ 356/2025 (thay NĐ 13/2023 từ 01/01/2026); Luật ANM 116/2025 (01/07/2026). OWASP LLM Top 10 2026; EU AI Act Đ.50 áp dụng 02/08/2026. Mặc định OSI: OpenTofu, Valkey.
- Repo khung: CPython ≥ 3.13, CI 3.15.2 (D-545, ADR-0094); `mypy --strict`; coverage 100 % (cả subprocess); `changelog-check`/`progress-check` trong `lint`; PROGRESS chỉ ghi SHA trên `main` (squash-merge). Tên: X-stored → X-Templates (ADR-0006/0007).
- Commit/PR không ghi tên model hay URL phiên AI (LOOP-HARNESS-027); tag phát hành qua `release-tag.yml` — gọi bằng REST `workflow_dispatch` (`gh workflow run` cần GraphQL, bị chặn trong phiên).
- Autopilot: tự duyệt (ADR-0008), một phiên (ADR-0009), phản hồi dự án đích (ADR-0010), cổng rỗng là đỏ (ADR-0011), `doctor --fix` đầu tiên; pha build/harden (ADR-0031), tối giản pha build (ADR-0033). Merge theo làn (ADR-0013…0016, 0020, 0024/0025, 0028/0032), steward (ADR-0027); cơ chế: merge ghim head, không auto-merge, không `merge-gate` (ADR-0036). Guard không hỏi người (ADR-0018/0019), ghi tay `.autopilot/` bị chặn (ADR-0026). Reviewer năng lực cao hơn người viết (D-161): cần review thì spawn agent mới và chỉ định `model`. Cấu hình agent theo loại việc, `max_rethink` 1/PR (ADR-0061).
- Phiên nhiều lát: mỗi lát một nhánh từ `origin/main`, mở PR tuần tự; guard chặn force-push; sửa PR đang mở khi cây bẩn → worktree riêng.
- Sửa thân PR (chân trang do máy chủ MCP gắn) từng kích `edited` → chỉ `pr-title.yml` nghe `edited`. Phiên khung không merge được PR ở repo khác → để `pr-steward` của dự án merge ghim head.
- CI đã gỡ macOS (2026-10-17). Nợ chấp nhận: 4 MUST/module là phán đoán; số điều NĐ 356/2025 chưa đối chiếu bản gốc. D-142 chưa làm: tách `xt.py`, merge queue, reviewer LLM mọi PR, thu nhỏ guard. ADR-0075 lập kế hoạch song song worktree theo file (T-3850).
- Coverage cục bộ < 100 % khi `coverage` cài ở site người dùng: hook chạy `python3 -I` nên tiến trình con không được đo — CI là cổng coverage (đo 2026-11-05).

## Bàn giao phiên
- Mốc `main` `42f3c64` (#765; tag `v3.36.0` cùng commit). Cắt bản: cần CPython 3.15.2 (`dev-task.sh bootstrap`, `XT_PYTHON`; `uv` không tải được: dựng từ nguồn); PLAN mới có dòng Gate sinh nợ review sau mốc quét; ký bằng một lệnh đơn `python3 scripts/xt.py release-sign --note …`. "Tiếp tục": đọc [sổ audit](docs/ops/AUDIT-STATUS.md) và CHANGELOG.
- Container mới: `scripts/dev-task.sh setup`; trước khi đẩy `gate-fast`, CI là cổng đầy đủ. Gate cục bộ: `coverage` và `pip` phải ở site-packages của `python3` (hook chạy `python3 -I`) — venv đầu PATH; G7 cần `fetch --unshallow --tags`; `release-check` chạy ở worktree sạch.
