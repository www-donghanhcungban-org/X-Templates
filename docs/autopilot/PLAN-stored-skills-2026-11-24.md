# PLAN X-Templates 2026-11-24 — áp dụng gợi ý skill từ stored, ghi chi phí vào sổ lát, trả nợ rà #774

> Duyệt: D-562 (phiên chính tự duyệt; chủ dự án yêu cầu "xem các nâng cấp skill cho từng catalog … áp dụng cho dự án (đã tổng hợp từ stored)") · Căn cứ: `data/xt-handoff.json` của stored (162 mục, mọi mục XT-H đã vào khung, trạng thái đã ghi ở stored) và PLAYBOOK §6/§7 "ý tưởng skill/tính năng" (đọc 2026-11-24 ở commit `597c05f`, đề xuất chưa ai xây) · `docs/specs/SPEC-slice-ledger.md` §2.3

## Tóm tắt
- Chọn theo ba tiêu chí: có cổng kiểm máy tất định, chưa có ở khung (đã grep), làm được bằng stdlib trong một lát. Hai ý qua sàng: "dò drift AGENTS.md" (cờ `--xxx` trong skill/tài liệu phải có thật ở lệnh) và "sổ chi phí" (SPEC đã định nghĩa người ghi, chưa ai cài).
- Đã có ở khung, không làm lại: test kích hoạt skill (`XC-DOCAI-025`, `tests/test_skill_routing.py`), mutation (`mutate-guard`), traceability spec → test (blueprint), kiểm cấu hình agent (`harness-check`), khoá `model:` agent ngoài (`LOOP-ORCH-022`).
- Không chọn: ý cần mô hình chạy thật hoặc công cụ ngoài (eval A/B có/không skill, quét SBOM/VEX, fuzz, benchmark reviewer SARIF) — để trong sổ ý tưởng, mở lại khi có số đo cần.
- Trả nợ rà #774 (nợ-review: #774): 🟠 AUD-HAR-498 và các 🟢 AUD-HAR-499/500 ngay trong lát này.

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí ngoài phiên: 0 · Timeout Gate: 1200 giây · Hạn: 3 giờ.

## Task
- [x] `T-4401` `loop record --cost` và `pr reviewed --cost` ghi sự kiện `cost` vào sổ lát theo SPEC-slice-ledger §2.3 (`id=<duy nhất>,usd=` hoặc token kèm giá có nguồn và ngày; sai đối số dừng trước khi chạy gì) — Gate: `python3 -m unittest tests.test_cost_flag tests.test_slice_ledger` (files: scripts/xt.py, tests/test_cost_flag.py, docs/specs/SPEC-slice-ledger.md, CHANGELOG.md)
- [x] `T-4402` test dò drift lệnh trong tài liệu cho agent: mọi cờ `--xxx` nhắc sau `xt.py <lệnh>`/`<XT> <lệnh>` ở AGENTS.md, CLAUDE.md, README, skill, agent và `framework/` phải có ở parser (files: tests/test_doc_command_drift.py, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_doc_command_drift`
- [x] `T-4403` trả nợ rà #774: `xt_toolcfg.load` đọc chặt (không theo liên kết, chỉ tệp thường, trần 1 MiB, khoá trùng/`null`/khoá lạ bị từ chối, JSON lồng sâu thành lỗi rõ), `root` kiểm trước khi đọc và không trùng thư mục công cụ khác, `contract ≥ min_contract`, `env()` rơi về `XT_`; `_read_json_obj` bắt `RecursionError` (files: scripts/xt_toolcfg.py, scripts/xt.py, tests/test_toolcfg.py, tests/test_xt_core.py, docs/ops/AUDIT-STATUS.md, tests/fixtures/autonomy/scope.json) — Gate: `python3 -m unittest tests.test_toolcfg tests.test_xt_core`
