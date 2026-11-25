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

## 6. Chưa xác minh

- Đặc tả MCP bản mới nhất và các thay đổi của nó; cần cho phép host `modelcontextprotocol.io`.
- Changelog Claude Code 2026-10-15 → 2026-11-03; chi tiết các bản 2.1.318–2.1.330 (chỉ có tóm tắt).
- Số token/chi phí thực mỗi lát và mỗi PR của dự án; mức tiết kiệm của từng đề xuất ở §5.
- Phần trăm chiết khấu Batch API; trạng thái GA của context editing và compaction API.

## Nguồn

- <https://code.claude.com/docs/en/changelog> — 2026-11-25
- <https://code.claude.com/docs/en/costs> — 2026-11-25
- <https://code.claude.com/docs/en/prompt-caching.md> — 2026-11-25
- <https://platform.claude.com/docs/en/agents-and-tools/tool-use/manage-tool-context> — 2026-11-25
- <https://platform.claude.com/docs/en/build-with-claude/prompt-caching> — 2026-11-25 (đọc đầu và cuối nguyên văn, phần giữa qua tóm tắt)
- <https://www.anthropic.com/engineering/advanced-tool-use>
