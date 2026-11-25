---
title: Cải tiến gần đây của Anthropic và cách giảm đốt token (khung và dự án đích)
kind: research
updated: 2026-11-25
---

# Cải tiến gần đây của Anthropic và cách giảm đốt token

Đọc ngày 2026-11-25 từ tài liệu chính thức. Mức bằng chứng: **(a)** trang chính thức đọc trực tiếp; **(b)** tóm tắt qua trung gian hoặc nguồn thứ cấp; **(c)** chưa xác minh. Chưa có số đo token/chi phí trên chính dự án (xem §5).

## 1. Kết luận

- Không có cải tiến nào buộc đổi khung ngay. Phần đáng làm là chỉnh cấu hình giảm token và cập nhật số liệu cho dự án đích.
- Claude Ship: không có thay đổi mới so với [`2026-11-24-claude-ship.md`](2026-11-24-claude-ship.md); giữ ADR-0100.
- Thực thi mã với MCP: lợi ích thật nhưng con số 150.000 → 2.000 token chỉ là ví dụ của Anthropic; Code Mode còn thử nghiệm và không có ở phiên cloud — chưa bật, đo trước (§6).
- Điều phối và bộ nhớ: mô hình trạng thái trên đĩa của khung khớp mẫu Anthropic khuyến nghị; auto memory (cục bộ máy, không review được) không hợp autopilot cloud. Việc đáng làm: để máy cưỡng chế độ sâu và số subagent đồng thời, `omitClaudeMd` cho agent nhẹ, `.claude/rules` có `paths:` cho dự án đích (§8).
- Đặc tả MCP bản mới nhất: **chưa xác minh** (host `modelcontextprotocol.io` bị chặn trong môi trường; nguồn thứ cấp nói có bản sửa 2026-07-28 bỏ phiên — mức c).

## 2. Claude Code 2.1.318 → 2.1.332 (changelog chính thức, đọc 2026-11-25)

Mức (a) cho 2.1.332, 2.1.331 và một phần 2.1.325; mức (b) cho 2.1.318–2.1.330. Bản 15/10–03/11 chưa đọc.

| Bản (ngày) | Mục liên quan | Đối với dự án |
|---|---|---|
| 2.1.332 (11-25) | Skills từ máy chủ MCP (beta); hook `PreSkillShellCommand`; `--model default` lùi về model cũ khi cần | Skill từ MCP là nguồn không tin cậy; kiểm `guard.py` có phủ hook mới |
| 2.1.331 (11-23) | Code Mode trên Bedrock/Agent Platform/Foundry; sửa Code Mode resume mất prompt cache | Code Mode còn thử nghiệm, chờ số đo |
| 2.1.330 (11-20) | Tóm tắt tiến độ subagent dùng ít token hơn qua gateway; `/ultrareview` hiện chi tiêu còn lại | Tín hiệu chi phí |
| 2.1.329 / 2.1.328 (11-19) | `/code-review` rà cả nhánh, chỉ báo bug và vi phạm CLAUDE.md; thêm `/simplify`; cache tốt hơn cho phiên Code Mode có MCP; mô tả tool Code Mode ngắn hơn | Dùng làm tín hiệu phụ, không thay dấu `pr reviewed` |
| 2.1.327 (11-17) | Thông báo tiến độ subagent viết từ ghi chú ngắn | Giảm token nền |
| 2.1.326 (11-16) | Code Mode với agent teams; `/update-config` từ ~93.000 xuống ~13.000 token | — |
| 2.1.325 (11-13) | Bash trong sandbox theo luồng quyền thường (`sandbox.autoAllowBashIfSandboxed: true` để giữ cũ); prompt suggestions làm mới ít hơn sau 8 lượt nền | Liên quan đánh giá sandbox D-331/332 (hạn 2027-01-21) |
| 2.1.323 (11-12) | Code Mode (thử nghiệm, tự chọn bật); `CLAUDE_CODE_DISABLE_AGENT_PROGRESS_SUMMARIES`; model ID lạ coi là 1M context | Xem §3 |
| 2.1.321 (11-09) | `claude-fable-5-2` thành Fable mặc định; thông báo lệnh nền chỉ hiện đầu/cuối khi dài hơn 1.000 ký tự | — |
| 2.1.319 (11-06) | `permissions.denyInsteadOfPrompting`; `/context` giữ 10 hàng lớn nhất | Hợp autopilot không hỏi người |
| 2.1.318 (11-04) | Lệnh shell của subagent nền chuyển nền sau 3 phút "so the prompt cache doesn't expire" | — |

## 3. Giảm token: Claude Code (trang `costs` và `prompt-caching`, mức a)

Số và tên đúng như trang ghi.

**Đo trước.** `/usage` có dòng `Prompt cache (main)` (hit rate, miss, còn ấm hay không); status line đọc được `current_usage.cache_read_input_tokens` / `cache_creation_input_tokens`. Mức trung bình doanh nghiệp ~13 USD/dev/ngày hoạt động; agent teams ~7 lần token phiên thường.

**Cache.**
- TTL mặc định luồng chính: 1 giờ với thuê bao trong hạn mức gói; **5 phút** với API key, usage credits, nhà cung cấp cloud. Subagent, compaction và trợ lý khác mặc định 5 phút.
- Chỉnh: `promptCacheTtl` / `CLAUDE_CODE_PROMPT_CACHE_TTL`; `subagentPromptCacheTtl` / `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL`; `ENABLE_PROMPT_CACHING_1H=1`; `FORCE_PROMPT_CACHING_5M=1` (ưu tiên cao nhất). Ghi 1 giờ tốn nhiều hơn ghi 5 phút (xem §4).
- Làm mất cache: đổi model; đổi effort (trừ Opus 5.5, Sonnet 5.5, Haiku 5.5, Fable 5.1+ qua API key/thuê bao); bật/tắt fast mode; thêm/bớt máy chủ MCP **khi tool search tắt**; bật/tắt plugin cấp MCP; `/compact`; nhiều ảnh; nâng Claude Code. Phiên ở thư mục khác không dùng chung cache.
- Giữ cache: sửa file repo; sửa CLAUDE.md giữa phiên (có hiệu lực sau `/clear`, `/compact`, khởi động lại); đổi permission mode; gọi skill/lệnh; `/rewind`; spawn subagent.
- Cổng cache: gateway xoá `cache_control` thì cả hội thoại tính như không cache.

**Context.** `/clear` giữa việc không liên quan; `/compact <hướng dẫn>` và mục `# Compact instructions` trong CLAUDE.md; `/rewind` thay cho compact khi bỏ nhánh sai; CLAUDE.md ≤ ~200 dòng; skill chỉ nạp khi gọi. Output thô: hook PreToolUse (matcher `Bash`) có thể cắt output test còn 100 dòng cuối trước khi vào context (ví dụ của tài liệu, script `filter-test-output.sh`).

**Model và effort.** Sonnet cho phần lớn việc, Opus cho thiết kế; subagent việc đơn giản dùng `model: haiku`; thinking tính như output token; không tắt được thinking trên Opus 5.5/Sonnet 5.5/Haiku 5.5/Fable, chỉnh bằng `/effort`.

**MCP.** Định nghĩa tool hoãn nạp mặc định (chỉ tên vào context); `/mcp` tắt server thừa; ưu tiên CLI (`gh`, `aws`, `gcloud`) hơn MCP.

**Nền khi rảnh.** `idleCompaction: false` (từ v2.1.290); tắt prompt suggestions; `/loop` trong phiên vẫn gửi toàn bộ context khi kích (xem hàng Loops trong `/usage`); `crossSessionInbound: hold`; `CLAUDE_CODE_GOAL_CHECKIN_MINUTES=0`.

## 4. Giảm token: API cho dự án đích có gọi LLM (trang `prompt-caching`, `manage-tool-context`)

| Mục | Dữ kiện | Trạng thái |
|---|---|---|
| Giá cache | Ghi 5 phút = 1,25× giá vào; ghi 1 giờ = 2×; đọc = 0,1× (0,05× với Opus 5.5 và Sonnet 5.5; 0,025× với Fable/Mythos 5.1–5.2) | (a) |
| Ngưỡng tối thiểu để cache | 512 token (Fable 5.x, Mythos 5.x, Opus 5.5, Opus 5, Sonnet 5.5, Haiku 5.5); 1.024 (Opus 4.8, Sonnet 5, 4.6, 4.5…); 2.048 (Mythos Preview, Opus 4.7); 4.096 (Opus 4.6/4.5, Haiku 4.5). Ngắn hơn thì xử lý không cache, không báo lỗi | (a) |
| Cache tự động | Một `cache_control: {type: ephemeral}` ở cấp cao nhất; tối đa 4 điểm ngắt tường minh; cửa sổ nhìn lại 20 khối; thứ tự `tools` → `system` → `messages`; `bedrock-runtime` trả 400 | (a) |
| Làm mất cache | Đổi định nghĩa tool (mọi tầng); đổi `speed: fast`; đổi tham số thinking hoặc `output_config.effort` (tầng messages); thêm/bớt ảnh | (a) |
| Tool search | `defer_loading: true`; biến thể `tool_search_tool_regex_20251119` / `tool_search_tool_bm25_20251119`; mặc định trả tối đa 5 tool; ≥ 1 tool không hoãn; không header beta; tool hoãn không gắn `cache_control` | ổn định (a) |
| Gọi tool bằng mã | Cần `code_execution_20260120` trở lên, tool khai `allowed_callers`; không ZDR | ổn định (a) |
| Context editing | `clear_tool_uses_20250919` (trigger mặc định 100.000 token, `keep` 3), `clear_thinking_20251015`; header `context-management-2025-06-27`; trang khuyên compaction phía máy chủ là chiến lược chính | **beta** (a; mặc định từ tóm tắt, b) |
| Compaction API | Header `compact-2026-09-04`; ngưỡng mặc định 100.000 token | **beta** (a/b) |
| Memory tool | `memory_20250818`, client-side, không header beta | ổn định (a) |
| Chiết khấu Batch API | Trang chỉ nói hệ số nhân "stack"; phần trăm không đọc được | (c) |

## 5. Khuyến nghị cho khung (chưa làm)

1. Đặt biến giảm token nền (§3 nhóm "Nền khi rảnh") và cân nhắc `promptCacheTtl`/`subagentPromptCacheTtl` trong `.claude/settings.json` của khung và mẫu dự án đích — **sau khi có số** (`LOOP-ORCH-020`): ghi 1 giờ chỉ đáng khi khoảng chờ CI/merge thường quá 5 phút và dùng API key.
2. Thêm hook PreToolUse cắt output lệnh Gate (hiện chỉ `loop record` giữ 40 dòng; output Bash thô vẫn vào context).
3. Cập nhật `LOOP-CTX-011` (cache tự động, ngưỡng, hệ số giá, thứ tự prefix) và `LOOP-CTX-014`, và module `13-ai-engineering` (tool search, gọi tool bằng mã, context editing/compaction còn beta).
4. Rà `reviewer-alt` ở effort `max` (khả năng là khoản đốt lớn nhất mỗi PR) khi có dữ liệu T-4010.
5. Mục `# Compact instructions` trong `CLAUDE.md` mẫu.
6. Kiểm `.claude/hooks/guard.py` có phủ hook `PreSkillShellCommand` và nguồn skill từ MCP.
7. Ghi vào hồ sơ đánh giá sandbox (D-331/332) thay đổi 2.1.325.

## 6. Thực thi mã với MCP và Code Mode (bổ sung 2026-11-25)

**Bài gốc** ("Code execution with MCP", 2025-11-04, Adam Jones và Conor Kelly; đọc nguyên trang, mức a): ví dụ Google Drive → Salesforce giảm "from 150,000 tokens to 2,000 tokens—a time and cost saving of 98.7%". Bài không nêu khối lượng, model hay số tool đằng sau con số: đây là một ví dụ minh hoạ, không phải đo lường. Năm lợi ích bài nêu và mức khớp với khung:

| Lợi ích (theo bài) | Khớp khung | Việc |
|---|---|---|
| Nạp dần: tool là tệp dưới `./servers/`, mở đúng tệp cần; tuỳ chọn `search_tools` với mức chi tiết | Tool search hoãn nạp đã mặc định ở Claude Code (§3) | Không |
| Kết quả gọn: lọc 10.000 dòng trong mã, model chỉ thấy 5 dòng | `LOOP-CTX-002` và `loop record` (40 dòng) | Hook cắt output Bash thô (§7 mục 2) |
| Luồng điều khiển trong mã: vòng lặp, rẽ nhánh, thăm dò chạy ngoài model; bài nói còn giảm độ trễ "time to first token" | `LOOP-DESIGN-029`, `merge-watch` nền | Rà chỗ agent còn tự thăm dò bằng nhiều lượt |
| Riêng tư mặc định: kết quả trung gian ở lại môi trường chạy; có thể thay PII bằng token như `[EMAIL_1]` để model không thấy giá trị thật | Chưa có | Đề xuất cho dự án đích xử lý dữ liệu cá nhân (§7 mục 4) |
| Giữ trạng thái và skills: lưu hàm chạy tốt vào `./skills/` kèm `SKILL.md` | `.claude/skills/` | Không |

Chi phí bài nêu: cần môi trường chạy an toàn có sandbox, giới hạn tài nguyên và giám sát; "These infrastructure requirements add operational overhead and security considerations that direct tool calls avoid." Bài yêu cầu cân nhắc lợi ích so với chi phí này.

**Code Mode của Claude Code** (trang `code-mode`, đọc 2026-11-25, mức a; các trang env-vars, mcp, hooks chỉ đọc một phần, mức b):
- Trạng thái: "experimental and off by default. It may change or be removed in any release". Bật bằng biến `CLAUDE_CODE_EXPERIMENTAL_CODE_MODE=1` (shell hoặc khối `env` của settings người dùng); **file settings dự án bỏ qua biến này**, nên repo tải về không tự bật được; managed settings đặt `0` để chặn cả tổ chức. Chưa thấy khoá settings hay cờ CLI.
- Điều kiện: Claude Code ≥ 2.1.323 (nhà cung cấp cloud ≥ 2.1.331, agent teams ≥ 2.1.326); model Opus 5.5, Sonnet 5.5, Haiku 5.5 hoặc Fable 5.2 (tên đầy đủ, không dùng bí danh); phiên `claude` tương tác trong terminal; **không** có ở phiên cloud, VS Code, Desktop, gateway, cấu hình HIPAA hoặc ZDR; không dùng với Remote Control, Claude in Chrome, computer use. Subagent cần thêm `REPL` vào danh sách `tools`.
- Cơ chế: model viết JavaScript gọi nhiều tool trong một bước; người dùng thấy lời gọi tool, xem mã bằng `Ctrl+O`.
- Quyền và hook: quy tắc quyền và hook viết theo tên tool quen thuộc (`Bash`, tên tool MCP), nên `PreToolUse` **áp dụng** cho lời gọi bên trong Code Mode. Muốn kiểm chính đoạn mã thì khớp `REPL` và đọc `tool_input.code`. Sandbox chỉ bao lệnh shell mà mã chạy; JavaScript và các lời gọi file, web, MCP của nó chạy ngoài sandbox (cần container hoặc VM nếu muốn cô lập). Chế độ Auto: bộ phân loại duyệt cả đoạn mã, không thấy giá trị tính lúc chạy. Quy tắc `ask` trên `REPL` buộc duyệt từng đoạn mã. `"onFailure": "block"` trên hook `command`, `http`, `mcp_tool` (≥ 2.1.295; `mcp_tool` ≥ 2.1.328) làm hook lỗi hoặc hết giờ thì từ chối thay vì cho qua kiểm quyền; không tác dụng với `Stop`, `SubagentStop`, `TaskCompleted`, `TeammateIdle` hay hook nền.
- Giới hạn: mã không chạy nền dừng sau 10 phút, chạy nền tối đa 2 giờ ở Auto hoặc `bypassPermissions`; phiên chỉ nối lại được khi Code Mode đang bật.
- Số token hoặc chi phí: **trang không nêu số nào**; lập luận là giảm số vòng gọi tool.

**Kết luận.** Lợi ích thật nhưng chưa đo trên dự án này, và Code Mode không có ở phiên cloud mà khung đang chạy (ghi chú này viết từ phiên cloud). Chưa bật; đo thử cục bộ ở một dự án đích trước (`LOOP-ORCH-020`). Phần dùng được ngay không cần Code Mode là hai ý của bài: lọc output trong mã và đưa thăm dò ra khỏi model.

## 7. Khuyến nghị bổ sung cho khung (chưa làm)

1. Guard (`guard.py`): xác nhận phủ lời gọi tên `REPL` và đọc được `tool_input.code`, vì hook `PreToolUse` áp dụng cho Code Mode; đồng thời hook của khung nên đặt `"onFailure": "block"` cho hàng rào (guard hiện fail-open về luồng, fail-closed về hành động nguy hiểm — ADR-0002).
2. Hook cắt output lệnh Gate (nhắc lại §5 mục 2); đây là cách rẻ nhất có hiệu lực tương tự "lọc trong mã".
3. Không bật `CLAUDE_CODE_EXPERIMENTAL_CODE_MODE` trong mẫu dự án đích; ghi trong tài liệu rằng settings dự án vốn bỏ qua biến này.
4. Dự án đích có dữ liệu cá nhân (Luật 91/2025, NĐ 356/2025; số điều NĐ chưa đối chiếu bản gốc): đề xuất mẫu "token hoá PII trước khi đến model" thành mục SHOULD ở module `13-ai-engineering` sau khi tra pháp lý.

## 8. Điều phối và bộ nhớ agent (bổ sung 2026-11-25)

Nguồn: trang `sub-agents`, `agent-teams`, `memory` của Claude Code; bài kỹ thuật của Anthropic; tài liệu memory tool và Managed Agents. Trạng thái mức đọc ghi ở từng dòng; phần cuối trang `sub-agents` và `memory` chỉ có tóm tắt (b).

### 8.1 Điều phối (Claude Code)

| Dữ kiện | Mức | Đối chiếu khung |
|---|---|---|
| Subagent có thể lồng tới 3 tầng mặc định; `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` tắt lồng | b | `LOOP-ORCH-001` cấm lồng bằng kỷ luật; **settings.json của khung chưa đặt biến này** |
| Số subagent đồng thời mặc định 20 (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`, ≥ 2.1.217) | b | `LOOP-ORCH-008` đòi ≤ 5; **chưa đặt biến** |
| Subagent tuỳ chỉnh gọi từ phiên chính mặc định chạy **nền** (trừ `web-fetch`); kết quả về ở lượt sau; `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` hoặc `CLAUDE_CODE_FORK_SUBAGENT=0` để buộc chờ | b | Ảnh hưởng luồng "chạy Gate rồi tick" (`LOOP-ORCH-004`): cần kiểm kết quả đã về trước khi tick |
| Fork (`/subtask`): kế thừa toàn bộ hội thoại, prompt, tool, model và cache; chỉ trả kết quả cuối; mặc định bật từ 2.1.302; chặn bằng `permissions.deny` `"Agent(fork)"` | b | Chưa có trong khung; rẻ hơn khi cần ngữ cảnh chung (cache dùng chung) |
| Trường frontmatter đáng dùng: `omitClaudeMd: true` (≥ 2.1.271, bỏ CLAUDE.md), `autoCompactWindow` (≥ 100000, ≥ 2.1.296), `skills` (nạp trước tối đa 32), `effort`, `maxTurns` (đầy thì đánh dấu một phần và có thể nối lại), `isolation: worktree`, `background`, `experimental.cacheTtl` | a | Các agent của khung có `model`, `effort`, `maxTurns`; **chưa dùng `omitClaudeMd`**. Mỗi subagent nạp lại CLAUDE.md và AGENTS.md của khung — với `explore` và `executor-mech` là phí cố định |
| Thứ tự chọn model subagent: tham số gọi → `model` trong định nghĩa → `CLAUDE_CODE_SUBAGENT_MODEL` → model phiên chính; `…_FORCE=1` (≥ 2.1.257) ép một model | a | Khớp `LOOP-ORCH-022` |
| Agent teams: thử nghiệm, tắt mặc định; mỗi teammate là một instance riêng; danh sách việc chung có khoá tệp, hook `TeammateIdle` `TaskCreated` `TaskCompleted`; khuyến nghị 3–5 teammate, 5–6 việc mỗi người; hợp với nghiên cứu, rà, module tách tệp, debug nhiều giả thuyết; không hợp với việc tuần tự, sửa chung tệp, phụ thuộc nặng; cache mỗi teammate 5 phút | a | Giữ `LOOP-ORCH-021` (không bật trừ khi có ADR) |
| Hướng dẫn chọn: phiên chính cho việc lặp qua lại hoặc ngữ cảnh chung; subagent khi output dài, cần hạn chế quyền hoặc việc khép kín trả tóm tắt; skill cho prompt tái dùng | b | Khớp `LOOP-ORCH-012` |

Bài kỹ thuật: hệ nghiên cứu đa agent (Anthropic, 2025-06-13) báo agent dùng ~4 lần token chat, đa agent ~15 lần, lead Opus 4 cộng subagent Sonnet 4 hơn Opus 4 đơn "by 90.2%" trên bộ đánh giá nghiên cứu nội bộ (số tự công bố); mô hình điều phối-thực thi hợp việc rộng chạy song song, **"most coding tasks"** ít phần song song hoá được; mỗi subagent cần mục tiêu, khuôn đầu ra, hướng dẫn tool và ranh giới việc; thang nỗ lực: tra cứu đơn giản 1 agent 3–10 lần gọi tool, so sánh 2–4 subagent, phức tạp > 10; lỗi gặp: sinh 50 subagent cho câu hỏi đơn giản, việc trùng lặp, sai số cộng dồn. *Building effective agents* (2024-12-19, tác giả ghi chú nhiều công cụ đã đổi): "find the simplest solution possible"; năm mẫu (chuỗi prompt, định tuyến, song song, điều phối-thực thi, đánh giá-tối ưu). Đối chiếu: khớp `LOOP-ORCH-020` (mặc định tự làm), `LOOP-ORCH-011` (báo cáo ngắn) và vòng reviewer; không có gì buộc khung đổi.

### 8.2 Bộ nhớ agent

Ba lớp khác nhau, đừng nhầm:

| Lớp | Nơi lưu | Chia sẻ | Hợp với khung? |
|---|---|---|---|
| `CLAUDE.md`, `.claude/rules/` (a) | Trong repo | Cả nhóm, đưa vào git | **Có** — chính là nhà của luật |
| Bộ nhớ tự động (auto memory, a/b): `~/.claude/projects/<project>/memory/`, nạp 200 dòng hoặc 25 KB đầu của `MEMORY.md` mỗi phiên, tệp chủ đề đọc khi cần; bật mặc định ở phiên cục bộ; tắt bằng `autoMemoryEnabled: false` (settings dự án) hoặc `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`; phiên nền và phiên do phiên khác khởi động không bật lại được | Cục bộ máy, cá nhân | **Không cho autopilot**: container cloud mất sau phiên, trạng thái phải nằm trong repo (`LOOP-CTX-006`); ngoài repo thì không review được và có thể lệch kết quả giữa các phiên |
| Bộ nhớ subagent (`memory: user\|project\|local`, a): `.claude/agent-memory/<tên>/` (`project`, khuyến nghị), `~/.claude/agent-memory/<tên>/`, `.claude/agent-memory-local/<tên>/`; cùng giới hạn 200 dòng hoặc 25 KB; tự bật Read/Write/Edit; vô hiệu nếu auto memory tắt | Theo phạm vi | **Có điều kiện** — xem 8.3 |

Mẫu từ tài liệu API và bài kỹ thuật (a): memory tool `memory_20250818` ở phía client, thư mục `/memories`, lệnh `view`, `create`, `str_replace`, `insert`, `delete`, `rename`; xem tệp cắt ở 16.000 ký tự; mẫu nhiều phiên là phiên khởi tạo ghi nhật ký tiến độ và danh sách tính năng, phiên sau đọc và cập nhật trước khi kết thúc, lời nhắc "ASSUME INTERRUPTION"; rủi ro nêu rõ: duyệt đường dẫn (`/memories/../../secrets.env`), dữ liệu nhạy cảm trong bộ nhớ, tệp phình, ký ức cũ. Bài ngữ cảnh (2025-09-29): nạp "lightweight identifiers" khi chạy thay vì nhét sẵn, ghi chú có cấu trúc ra ngoài cửa sổ (`NOTES.md`), compaction giữ tóm tắt cộng năm tệp truy cập gần nhất, subagent trả tóm tắt 1.000–2.000 token, "context rot" khi dài. **Khung đang làm đúng mẫu này** bằng `PROGRESS.md` + `PLAN.md` + `DECISIONS.md` + checkpoint PreCompact; đây là xác nhận, không phải thiếu sót.

Managed Agents (beta, header `managed-agents-2026-04-01`; không ZDR/HIPAA): kho bộ nhớ (memory stores, beta, header `agent-memory-2026-07-22`, gắn vào phiên lúc tạo, gắn ở `/mnt/memory/`, mặc định `read_write` hoặc `read_only`, mỗi ký ức ≤ 100 kB, mỗi kho ≤ 10.000 ký ức, ≤ 8 kho mỗi phiên, phiên bản giữ 30 ngày; trang cảnh báo prompt injection có thể ghi vào kho `read_write`) và "dreams" (research preview: gộp một kho với 1–100 phiên thành kho mới, kho gốc không bị sửa). Mức: kho bộ nhớ đọc nguyên văn phần đầu, phần sau là tóm tắt (b).

### 8.3 Kết luận và đề xuất cho khung

1. **Giữ nguyên mô hình trạng thái trên đĩa** (`PROGRESS.md`, `PLAN.md`, `DECISIONS.md`); không chuyển sang auto memory. Cân nhắc đặt `autoMemoryEnabled: false` trong `.claude/settings.json` mẫu để phiên autopilot không nạp ký ức ngoài repo (kiểm: ký ức không review được là nguồn lệch).
2. **Đặt `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` và `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=5`** để máy cưỡng chế `LOOP-ORCH-001` và `LOOP-ORCH-008` thay vì kỷ luật; ghi vào `harness-files.md` và mẫu dự án đích. Kiểm trước: các biến này chỉ đọc từ môi trường hoặc `env` của settings; chưa xác minh settings dự án có hiệu lực (khác với `CLAUDE_CODE_EXPERIMENTAL_CODE_MODE`, bị bỏ qua ở settings dự án).
3. **Thêm `omitClaudeMd: true` cho `explore` và `executor-mech`** (agent chỉ đọc hoặc cơ học, đã nhận hướng dẫn đầy đủ trong gói handoff): bỏ phí nạp CLAUDE.md và AGENTS.md mỗi lần gọi. Không dùng cho `reviewer`/`executor` vì cần luật khung. Cần đo trước/sau.
4. **Bộ nhớ subagent (`memory: project`): chưa dùng**; nếu thử thì chỉ cho `executor`/`researcher` ghi quy ước repo học được, **không bao giờ cho `reviewer`/`reviewer-alt`** (làm lệch độc lập của người chấm — `LOOP-ORCH-005`), và nội dung phải qua review như mã vì nằm trong git (rủi ro persistence của prompt injection).
5. **Dự án đích**: dùng `.claude/rules/` có `paths:` để luật theo thư mục chỉ nạp khi chạm tệp khớp (giảm chi phí cố định, vì `@import` không giảm); `/doctor prompt-audit` (≥ 2.1.283) kiểm xung đột luật trong `/gate`; giữ `AGENTS.md` làm nguồn và `CLAUDE.md` mỏng (AGENTS.md chỉ được đọc khi không có CLAUDE.md, nên cầu nối `@AGENTS.md` là đúng).
6. **Ba lần gọi nền**: xác nhận quy trình tick task chờ kết quả subagent nền trước khi `loop record`; thêm `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` hay `CLAUDE_CODE_FORK_SUBAGENT=0` nếu thấy kết quả về trễ.
7. **Agent teams, Managed Agents memory stores, dreams**: không dùng cho khung; ghi vào danh sách theo dõi. Với dự án đích làm sản phẩm agentic, module `AI-AGENTIC` nên nêu: memory tool (ổn định) cần chặn duyệt đường dẫn, giới hạn kích thước, loại dữ liệu nhạy cảm, hết hạn ký ức; kho bộ nhớ Managed Agents còn beta, mặc định `read_only` cho agent không cần ghi.
8. Giữ nguyên `LOOP-ORCH-020/021`: số của chính Anthropic (15 lần token, "most coding tasks" ít song song hoá được) ủng hộ mặc định tự làm.

## 9. Chưa xác minh

- Đặc tả MCP bản mới nhất và các thay đổi của nó; cần cho phép host `modelcontextprotocol.io`.
- Changelog Claude Code 2026-10-15 → 2026-11-03; chi tiết các bản 2.1.318–2.1.330 (chỉ có tóm tắt).
- Số token/chi phí thực mỗi lát và mỗi PR của dự án; mức tiết kiệm của từng đề xuất ở §5 và §7.
- Biến `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` và `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS` có hiệu lực khi đặt trong settings dự án hay không; hành vi fork, nền, lồng subagent chỉ có tóm tắt; chưa đọc trang costs về chi phí agent teams, trang worktrees, cross-session messaging; trang Managed Agents memory đọc nguyên văn khoảng 40.000/52.500 ký tự; bài `engineering/managed-agents` chưa đọc.
- Quan hệ giữa Code Mode và tool search; lời gọi tool lập trình (programmatic tool calling) không được trang Code Mode nhắc; số tiết kiệm của Code Mode.
- Phần trăm chiết khấu Batch API; trạng thái GA của context editing và compaction API.

## Nguồn

- <https://code.claude.com/docs/en/changelog> — 2026-11-25
- <https://code.claude.com/docs/en/costs> — 2026-11-25
- <https://code.claude.com/docs/en/prompt-caching.md> — 2026-11-25
- <https://platform.claude.com/docs/en/agents-and-tools/tool-use/manage-tool-context> — 2026-11-25
- <https://platform.claude.com/docs/en/build-with-claude/prompt-caching> — 2026-11-25 (đọc đầu và cuối nguyên văn, phần giữa qua tóm tắt)
- <https://www.anthropic.com/engineering/advanced-tool-use>
- <https://www.anthropic.com/engineering/code-execution-with-mcp> — 2025-11-04, đọc 2026-11-25
- <https://code.claude.com/docs/en/code-mode> — 2026-11-25 (cùng các trang settings, env-vars, mcp, hooks đọc một phần)
- <https://code.claude.com/docs/en/sub-agents> · <https://code.claude.com/docs/en/agent-teams> · <https://code.claude.com/docs/en/memory> — 2026-11-25 (phần cuối sub-agents và memory chỉ có tóm tắt)
- <https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool> · <https://platform.claude.com/docs/en/managed-agents/overview> · <https://platform.claude.com/docs/en/managed-agents/memory> · <https://platform.claude.com/docs/en/managed-agents/dreams> — 2026-11-25
- <https://www.anthropic.com/engineering/multi-agent-research-system> (2025-06-13) · <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents> (2025-09-29) · <https://www.anthropic.com/engineering/building-effective-agents> (2024-12-19) — đọc 2026-11-25
