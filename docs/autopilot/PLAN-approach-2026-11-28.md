# PLAN X-Templates 2026-11-28 — dễ tiếp cận hơn, skill đi được nhiều host, mức tự chủ đọc từ bằng chứng

> Duyệt: D-650 (phiên chính tự duyệt; chủ dự án yêu cầu "phân tích nhận định này và nghiên cứu thêm để nâng cấp dự án"), D-651 (việc không làm lúc này) · Căn cứ: [đối chiếu bản nhận định ngoài](../../research/2026-11-28-external-roadmap-assessment.md) · D-610 (hoãn nâng dự án đích) vẫn hiệu lực

## Tóm tắt
- Bản nhận định ngoài đề xuất lộ trình ba pha. Đối chiếu ở `main` `44ee1f8` cho thấy sáu đề xuất đã có hoặc đã quyết; PLAN này chỉ nhận phần còn hở thật: bước kế sau lệnh cài, trang chọn đường theo cỡ việc, khung tự kiểm skill theo chuẩn, gương skill cho Gemini, thang L0–L4 có máy đọc, mẫu issue, ma trận host.
- Không task nào chạm `guard.py` hay `.claude/settings.json`; riêng `T-5120` đổi hằng số trần trong `xt.py` với 0 dòng ròng. `T-5111` và `T-5114` cùng sửa `scripts/install.py` nên chạy nối tiếp.
- Mỗi task một nhánh từ `origin/main`, một PR. Dự án đích nhận thay đổi khi cắt bản kế.
- Không nới cổng: coverage 100 %, `mypy --strict`, C901 ≤ 10, trần byte và trần dòng giữ nguyên.
- Việc không làm lúc này và điều kiện mở lại: mục 7.2 của bản đối chiếu (D-651). Việc cần chủ dự án: mục cuối tệp này.
- Đặc tả triển khai: [SPEC-accessible-multihost](../specs/SPEC-accessible-multihost.md), mỗi task một mục; ca `ACC-<task>-<n>` là test bắt buộc của task đó.

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí dịch vụ ngoài: 0 · Timeout Gate: 1200 giây · Hạn: xét lại 2026-12-31.

## Task

### Lát 1 — người mới biết làm gì sau lệnh cài
- [ ] `T-5111` `install.py --new`: README dự án mới có mục bước kế (chạy bản dev theo gói, mở agent và gọi factory, mở `xt.py app`, nơi đọc luật) và lệnh in đúng khối đó khi kết thúc; README đã có thì không đụng (files: scripts/install.py, tests/test_install_new.py, CHANGELOG.md; topo: parallel) — Gate: `python3 -m unittest tests.test_install_new tests.test_install && python3 -m mypy --strict --python-version 3.13 scripts/install.py`
- [ ] `T-5112` một trang chọn đường theo cỡ việc: sửa thẳng qua cổng commit · một phiên có PLAN ngắn · đợt `/autopilot` · vòng đời `/factory`; mỗi đường ghi cái được bỏ và cái không bao giờ bỏ; mẫu `AGENTS.md` và README trỏ tới, không chép lại (files: framework/00-method/lifecycle.md, framework/templates/AGENTS.md, README.md, CHANGELOG.md; topo: parallel) — Gate: `python3 scripts/xt.py validate && python3 scripts/check-links.py && python3 -m unittest tests.test_docs_budget tests.test_install`

### Lát 2 — skill đúng chuẩn và tới đủ host
- [ ] `T-5113` test stdlib kiểm mọi skill ở `.claude/skills` và gương `.agents/skills` theo giới hạn Agent Skills (tên 1–64 ký tự đúng mẫu và trùng thư mục, mô tả 1–1024, dưới 500 dòng); khoá frontmatter phải thuộc sáu trường chuẩn hoặc danh sách mở rộng Claude Code khai ngay trong test; `docs-for-ai-agents.md` ghi `skills-ref` là bản minh hoạ (files: tests/test_skills_spec.py, framework/18-cross-cutting/docs-for-ai-agents.md; topo: parallel) — Gate: `python3 -m unittest tests.test_skills_spec && python3 scripts/xt.py validate`
- [ ] `T-5114` `--harness gemini` cũng sinh gương `.agents/skills` bằng bộ sinh của ADR-0082 (cùng luật hash, `kept-own`, không xuyên symlink); ADR mới ghi phạm vi và lý do chưa làm cho host đọc thẳng `.claude/skills` (sau: T-5111; files: scripts/install.py, tests/test_codex_harness.py, tests/test_install.py, framework/templates/harness/README.md, docs/adr/, CHANGELOG.md; exec: deep) — Gate: `python3 -m unittest tests.test_codex_harness tests.test_install tests.test_adapters && python3 -m mypy --strict --python-version 3.13 scripts/install.py`

### Lát 3 — mức tự chủ đọc từ bằng chứng
- [x] `T-5115` SPEC: ánh xạ từng điều kiện lên mức và đường lùi của thang L0–L4 sang số đo đọc từ sổ lát và `runs.jsonl`; hình dạng khối `autonomy` trong `xt_flow.py --json` (mức đang khai, mức đủ điều kiện, từng số đo, phần thiếu dữ liệu là `null` kèm lý do); chỉ tư vấn, không lệnh nào tự đổi `merge_autonomy`; ca Given/When/Then gồm dữ liệu thiếu và cửa sổ chưa đủ dài — viết cùng PR lập kế hoạch, mục 5 của SPEC chung (files: docs/specs/SPEC-accessible-multihost.md; topo: parallel) — Gate: `test -s docs/specs/SPEC-accessible-multihost.md && python3 scripts/check-links.py`
- [ ] `T-5116` triển khai SPEC mục 5 trong `xt_flow.py` (ca ACC-116-1…9), test đi qua sổ ghi bằng lệnh thật trong repo tạm (không đưa sự kiện giả vào bộ tính); `stop-points-and-escalation.md` trỏ tới lệnh đọc (sau: T-5115; files: scripts/xt_flow.py, tests/test_flow.py, framework/11-autonomous-loop/stop-points-and-escalation.md, CHANGELOG.md; exec: deep) — Gate: `python3 -m unittest tests.test_flow && python3 -m mypy --strict --python-version 3.13 scripts/xt_flow.py && python3 scripts/xt.py validate`

### Lát 4 — cửa vào cho người ngoài và ma trận host
- [ ] `T-5117` mẫu issue báo lỗi và đề xuất, song ngữ Anh và Việt; CONTRIBUTING thêm đoạn tiếng Anh ngắn trỏ tới luật hiện có (files: .github/ISSUE_TEMPLATE/, CONTRIBUTING.md; topo: parallel) — Gate: `python3 scripts/xt.py checks && python3 scripts/check-links.py`
- [ ] `T-5118` README adapter cập nhật theo bản đối chiếu mục 4.2: phiên bản và ngày đọc, host nào đọc thẳng `.claude/skills`, mẫu OpenCode chỉ áp dụng cho dòng 1.x, Gemini CLI đổi đối tượng dùng (sau: T-5114; files: framework/templates/harness/README.md, CHANGELOG.md) — Gate: `python3 scripts/xt.py validate && python3 scripts/check-links.py`
- [ ] `T-5119` đọc nguyên văn tài liệu plugin OpenCode 2.x, ghi dữ kiện kèm ngày vào research, rồi thêm mẫu adapter cho dòng 2.x cạnh mẫu 1.x; bộ cài chọn mẫu theo cờ, không đoán phiên bản (sau: T-5118; files: research/, framework/templates/harness/, scripts/install.py, scripts/xt_adapter.py, tests/test_adapters.py, CHANGELOG.md; exec: deep) — Gate: `python3 -m unittest tests.test_adapters tests.test_install && python3 -m mypy --strict --python-version 3.13 scripts/install.py scripts/xt_adapter.py`

### Lát 5 — PROGRESS rộng hơn mà không mất phần cuối (chủ dự án hỏi 2026-11-28, D-652)
- [ ] `T-5120` hook SessionStart nạp PROGRESS theo ưu tiên mục (Đang làm, Tiếp theo, Bàn giao phiên đủ trước; mục Quyết định cắt trước và thay bằng dòng trỏ tệp); `progress-check` và hook đo trần bằng ký tự thay cho byte (cả tệp: đỏ; phần ưu tiên: cảnh báo — SPEC mục 9); test ghim `additionalContext` ≤ 10 000 ký tự khi khối Autopilot ở mức tối đa và ba mục ưu tiên còn nguyên; ADR mới thay một phần ADR-0091; `xt.py` 0 dòng ròng (files: .claude/hooks/session-start.sh, scripts/xt.py, tests/test_hooks.py, framework/11-autonomous-loop/harness-files.md, docs/adr/, CHANGELOG.md; exec: deep) — Gate: `python3 -m unittest tests.test_hooks tests.test_docs_budget && python3 scripts/xt.py progress-check && python3 scripts/xt.py autonomy-bench`

## Việc cần chủ dự án
- Hướng quốc tế: có dịch thư viện 2 890 mục và tệp sinh ra sang tiếng Anh không. Phiên chính khuyến nghị chưa dịch, làm `T-5111` và `T-5117` trước, xét lại khi có issue hoặc PR đầu tiên từ người ngoài nhóm dự án đích.
- Chạy thật Codex, Gemini, Cursor, Copilot, Grok, OpenCode để lấy payload hook; đây là điều kiện đổi nhãn "thử nghiệm" thành "hỗ trợ" (ADR-0068 lát D).
- Pilot S với một người chưa biết khung, đo thời gian từ clone tới bản dev chạy ([PLAN tích hợp §4](PLAN-integrated-upgrade-2026-11-27.md)); làm sau `T-5111` và `T-5112`.
- Video giới thiệu ngắn, sau pilot S.
