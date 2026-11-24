# PLAN X-Templates 2026-11-24 — vai trò model và đồng bộ harness (ADR-0098, lát R1)

> Duyệt: D-560 (phiên chính tự duyệt, chủ dự án yêu cầu "triển khai theo hướng tốt nhất", "chỉnh cho các harness khác để đồng bộ") · Căn cứ: [báo cáo vai trò model](../../research/2026-11-24-model-roles-haiku-and-top-minus-one.md); D-558 (rà code ở Opus), D-559 (mọi harness rà ở bậc thấp hơn đúng một nấc)

## Tóm tắt
- Mục tiêu: một bảng bậc model theo nhà cung cấp làm nguồn duy nhất (`framework/templates/harness/model-tiers.json`); agent `explore` (model nhẹ nhất, chỉ đọc) cho tra cứu; phiên chính viết code ở bậc đỉnh trừ một nấc để reviewer ở bậc đó cao hơn người viết; gương Codex và tài liệu/mẫu cho dự án đích đồng bộ.
- Lát R1 (đợt này): ADR-0098, bảng bậc, agent `explore` và gương Codex, tài liệu khung và mẫu đích, test khớp. Chưa đổi mã `xt.py`.
- Lát R2 (sau, PR riêng): `model-tiers.json` thành nguồn bậc cho `review_capability_error` ở nhà cung cấp đã xác minh; khoá `xt.yaml` `reviewer_tier`/`author_tier` (tăng `contract` của ADR-0097); `doctor` cảnh báo agent ghim model trái bậc; `install.py` sinh `model` cho agent Codex khi dự án khai bật.
- Đo trước khi mở rộng Haiku: thí nghiệm `explore` 10 câu (ADR-0098) và ghi `--cost` ở `loop record`/`pr reviewed`.
- Ngoài phạm vi: đổi `executor`/`acceptance-author` sang Haiku (Terminal-Bench 4.0 39,2 % so với Sonnet 70,6 %, loại); Gemini/Grok/Cursor/Copilot/OpenCode chỉ nhận bảng và hướng dẫn (chưa xác minh bậc).

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí ngoài phiên: 0 · Timeout Gate: 1200 giây · Hạn: 3 giờ.

## Task
- [x] `T-4301` ADR-0098: bảng bậc theo nhà cung cấp, vai → bậc, quy tắc phiên chính viết code, Haiku chỉ cho tra cứu chỉ đọc, đo trước khi mở rộng (files: docs/adr/0098-model-tiers-and-role-mapping.md, docs/autopilot/DECISIONS.md) — Gate: `test -s docs/adr/0098-model-tiers-and-role-mapping.md && python3 -m unittest tests.test_docs_budget`
- [x] `T-4302` `model-tiers.json`, agent `explore` và gương Codex, test khớp agent–bảng–gương–tài liệu (sau: T-4301; files: framework/templates/harness/model-tiers.json, .claude/agents/explore.md, .codex/agents/explore.toml, tests/test_model_tiers.py, tests/test_codex_harness.py) — Gate: `python3 -m unittest tests.test_model_tiers tests.test_codex_harness`
- [x] `T-4303` đồng bộ tài liệu khung và mẫu cho dự án đích: `orchestration-and-subagents.md`, mẫu `CLAUDE.md`/`AGENTS.md`, `AGENTS.md`, README adapter có bảng bậc theo harness, CHANGELOG (sau: T-4302; files: framework/11-autonomous-loop/orchestration-and-subagents.md, framework/templates/CLAUDE.md, framework/templates/AGENTS.md, AGENTS.md, framework/templates/harness/README.md, CHANGELOG.md) — Gate: `python3 scripts/xt.py validate && python3 scripts/xt.py changelog-check && python3 -m unittest tests.test_docs_budget tests.test_model_tiers`
