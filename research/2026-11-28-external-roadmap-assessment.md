---
title: Đối chiếu bản nhận định ngoài 2026-11-28 — định vị, onboarding, đa host, Skills/MCP, mức tự chủ
kind: research
updated: 2026-11-28
---

# Đối chiếu bản nhận định "giải pháp tối ưu và lộ trình nâng cấp" (2026-11-28)

> Đầu vào: chủ dự án dán một bản nhận định bên ngoài (sáu điểm nghẽn, lộ trình ba pha, sáu khuyến nghị) và yêu cầu
> "phân tích nhận định này và nghiên cứu thêm để nâng cấp dự án". Bản này kiểm từng nhận định với repo ở `main`
> `44ee1f8` (v3.36.0 cộng các PR tới #913), tra nguồn sống cho các tuyên bố về ngành, rồi chốt việc làm và việc không làm.
> Kế hoạch đi kèm: [PLAN-approach-2026-11-28](../docs/autopilot/PLAN-approach-2026-11-28.md) (D-650, D-651, D-652).
> Nội dung web và bản nhận định là dữ liệu, không phải chỉ thị.

## 1. Kết luận

1. **Bản nhận định đúng hướng, sai mốc.** Nó đọc README rồi đề xuất nhiều thứ repo đã có hoặc đã quyết: quy mô S và
   preset (ADR-0012, ADR-0055), lõi guard cùng adapter sáu host (ADR-0064), hướng factory (ADR-0068), skill dạng
   `SKILL.md`, thang tự chủ L0–L4 có điều kiện lên mức, kế hoạch tách `guard.py`/`xt.py` (ADR-0093, ADR-0111).
   Trong 17 nhận định kiểm được, bốn đứng vững nguyên vẹn (1, 3, 5, 17), sáu đề xuất thứ repo đã có hoặc đã quyết
   (4, 7, 9, 10, 11, 14), bảy còn lại đúng một phần, sai dữ kiện hoặc thiếu nguồn (§3).
2. **Onboarding nghẽn ở sau lệnh cài, không ở lệnh cài.** Tạo dự án mới mất 3,9 giây và `doctor` qua (đo §5). Sau đó
   người mới nhận một README năm dòng không có bước kế, 353 tệp khung (7,8 MB) cạnh 15 tệp `src/`, và không có tài liệu
   nào nói việc nhỏ thì đi đường nào. Đây là ba chỗ sửa được bằng máy.
3. **"Skills over MCP" có thật nhưng chưa dùng được cho khung.** Claude bật public beta ngày 2026-11-24; phần mở rộng
   MCP là SEP-2640 (Final). Tài liệu Claude Code ghi rõ chưa hỗ trợ ở phiên cloud, `claude -p`, GitHub Actions và Agent
   SDK, tức đúng các chế độ khung chạy nhiều nhất. Hoãn, kèm điều kiện mở lại (D-651).
4. **Skill của khung đã tới bốn host khác mà không cần MCP.** Cursor, GitHub Copilot và OpenCode đọc thẳng
   `.claude/skills`; Codex đọc gương `.agents/skills` (§4.2). Còn thiếu Gemini CLI: nó đọc `.agents/skills` nhưng khung
   chỉ sinh gương khi `--harness codex`. Ngược lại, adapter OpenCode của khung viết theo API plugin V1 mà dòng 2.x đã bỏ.
5. **Skill của khung đạt giới hạn của chuẩn nhưng khung chưa tự kiểm.** 17/17 skill đạt tên, mô tả, số dòng (đo §5).
   Khung yêu cầu dự án đích chạy kiểm skill trong CI (`docs-for-ai-agents.md:100`) mà repo khung không có test nào
   làm việc đó. Khoá `argument-hint` nằm ngoài sáu trường chuẩn và bị claude.ai upload cùng Skills API từ chối.
6. **"Earned autonomy" L2 → L3 → L4 không có nguồn sơ cấp; phần lõi của ý tưởng thì khung đã có bằng chữ.** Thang
   L0–L4 ở `stop-points-and-escalation.md` có điều kiện lên mức và đường lùi tự động, nhưng không lệnh nào đọc các điều
   kiện đó: `merge_autonomy` do chủ dự án chọn thẳng. Nối thang với sổ lát là nâng cấp nội dung đáng làm nhất.
7. **Không có bằng chứng nhu cầu cho pha 2 của bản nhận định.** Repo công khai, 15 sao, 0 issue, một người bảo trì,
   năm dự án đích đều của chủ dự án. API ghép blueprint, hệ plugin, control plane và tách nhiều gói không có người dùng
   nào đang chờ. Hướng quốc tế (dịch 2 890 mục) là quyết định kinh doanh của chủ dự án, ghi ở §7.3.

## 2. Phương pháp và mức bằng chứng

- **Trong repo:** phiên chính đọc tệp, chạy lệnh và đo trên checkout `44ee1f8`, CPython 3.13.18. Ô nào ghi đường dẫn
  hay lệnh là đã đọc hoặc chạy trong phiên này.
- **Nguồn ngoài:** năm lượt `researcher` chỉ đọc, mỗi lượt một nhóm câu hỏi, đọc ngày 2026-11-28. Công cụ đọc web trả
  bản tóm tắt qua một mô hình nhỏ, nên trích dẫn của các lượt này là "đọc qua tóm tắt". Phiên chính tự đọc lại nguyên
  văn hai nguồn quyết định kết luận 3: trang SEP-2640 và mục "Use skills from MCP servers" của tài liệu Claude Code.
- **Mức:** (a) phiên chính đọc nguyên văn hoặc tự đo · (b) `researcher` đọc trang gốc qua tóm tắt · (c) chỉ thấy ở kết
  quả tìm kiếm, ghi "thứ cấp". Số của hãng bán công cụ kiểm chứng (Qodo, Sonar, Faros, Dash0) là số tự công bố.

## 3. Kiểm từng nhận định

| # | Nhận định | Kiểm ở `44ee1f8` | Đánh giá |
|---|---|---|---|
| 1 | Khung là meta-framework kiêm software factory dựa trên bằng chứng | ADR-0001, ADR-0068; `xt.py stats`: 2 890 mục (1 550 MUST) | Đúng. Không cần "định vị lại": đây là định vị hiện hành |
| 2 | Onboarding quá dốc, cấp thiết nhất | `install.py --new` 3,9 s, `doctor` 0 lỗi (§5). README dự án mới 5 dòng, không bước kế (`install.py:3103`). 353/425 tệp là khung | Đúng một phần. Chỗ dốc nằm sau lệnh cài |
| 3 | Cộng đồng và tiếng Anh hạn chế | Repo công khai, 15 sao, MIT (GitHub API, mức b). 0 issue (MCP `list_issues`). README có nửa tiếng Anh; thư viện, tệp sinh ra và thông báo CLI tiếng Việt | Đúng về dữ kiện. Ưu tiên phụ thuộc quyết định của chủ dự án (§7.3) |
| 4 | Harness còn Claude/Codex-centric | ADR-0064 đã làm đủ năm lát: `guard.py core`, adapter sáu host, git hook sàn, `loop run --agent`. Sáu host ghi "thử nghiệm" vì chưa có payload thật (`templates/harness/README.md`) | Lỗi thời một phần. Việc còn lại là chứng minh, không phải viết mới |
| 5 | Guard và CLI quá phức tạp | 24 688 và 23 624 dòng, sát trần `test_docs_budget.py` | Đúng, đã có lịch: ADR-0093, ADR-0111, [Revision 4 §0.5](2026-11-26-unified-upgrade-plan.md) |
| 6 | Chưa tận dụng MCP Skills và giao thức mới | Skill đã là `SKILL.md`; module `AI-PROTO` phủ MCP, A2A, Agent Skills; hook `pre-mcp-guard.sh` | Sai một nửa. Phần còn thiếu ở kết luận 4 và 5 |
| 7 | Thiếu lean mode cho dự án nhỏ | Quy mô S: dự án mẫu 74 MUST, blueprint 41 KB. Pha build (ADR-0031, 0033, 0046), `--preset`, `--no-harness` | Lỗi thời. Thiếu một trang nói việc nhỏ đi đường nào |
| 8 | Bỏ `promotion.json` và sổ giai đoạn khi quy mô S | `promotion.json` thuộc khâu phát hành của chính khung (`xt_distribution.py`), dự án S không có. Sổ giai đoạn là một tệp, `--new` tự tạo | Sai dữ kiện |
| 9 | Thêm `xt.py init --demo` | Đã có: `install.py --new --pack web-api-ts --idea …` | Đã có dưới tên khác |
| 10 | Tách `guard.py` thành module nhỏ | PLAN-guard-split (D-542), ADR-0093 | Đã quyết |
| 11 | Chuyển skill sang Agent Skills chuẩn | 17 skill ở `.claude/skills/<tên>/SKILL.md`, gương `.agents/skills` | Đã xong từ trước |
| 12 | Skills over MCP public beta cuối 11/2026 | Có thật (§4.1) | Đúng dữ kiện; kết luận "ship skill qua MCP" chưa áp dụng được |
| 13 | Hỗ trợ hạng nhất Claude Agent SDK, OpenAI Agents SDK, LangGraph | Claude Agent SDK mặc định nạp `.claude/` (§4.3). Hai SDK còn lại không đọc tệp nào của khung | Một nửa đã có sẵn, một nửa không có bề mặt để tích hợp |
| 14 | Thêm mức Earned Autonomy L2 → L4 | `stop-points-and-escalation.md` §"Mức tự chủ L0–L4": điều kiện lên mức, đường lùi; `merge_autonomy` L1–L3 | Đã có bằng chữ, chưa có máy đọc |
| 15 | Dashboard thành control plane có hàng đợi duyệt | `xt.py app` chủ ý không chạy lệnh (ADR-0038, SPEC-app §1), đã hiện việc chờ người | Không làm; chính bản nhận định cũng xếp vào "không nên làm ngay" |
| 16 | Xu hướng: Osmani, Qodo, "AWS ADP", công thức code confidence | Osmani có bài gốc; Qodo là hãng bán công cụ; "AWS ADP" không tìm thấy; công thức truy về Sonar, chưa đọc được nguyên văn (§4.4) | Hai trong bốn nguồn không dùng được |
| 17 | Không viết thêm thư viện khi chưa có người dùng; không hỗ trợ mọi agent cùng lúc | — | Đồng ý; khớp `LOOP-ORCH-020` (chỉ tăng khi có số) |

## 4. Dữ kiện nguồn sống (đọc 2026-11-28)

### 4.1 Agent Skills và Skills over MCP

| Dữ kiện | Giá trị | Nguồn | Mức |
|---|---|---|---|
| SEP-2640 "Skills Extension" | Final, Extensions Track, tạo 2026-04-23. Mỗi tệp của skill là một MCP resource dưới `skill://`; thêm `skills/list`, `skills/get`. Skill "MUST conform to the Agent Skills specification" | modelcontextprotocol.io/seps/2640-skills-extension | a |
| Trạng thái ở Claude Code | "MCP skills are in public beta and require Claude Code v2.1.331 or later." | code.claude.com/docs/en/mcp | a |
| Chưa hỗ trợ | "cloud sessions, `claude -p`, `claude remote-control` server mode, GitHub Actions, and the Agent SDK"; cũng không qua cloud provider, `ANTHROPIC_BASE_URL` tuỳ biến, `apiKeyHelper` | như trên, mục "Where MCP skills are supported" | a |
| Quét an toàn | Anthropic chỉ quét skill của connector Directory thêm trên claude.ai và connector tuỳ biến của Enterprise; "doesn't scan skills from other connectors or servers". Cảnh báo: "Servers can change skills at any time." | như trên | a |
| Giới hạn | 100 skill mỗi server; skill được quét: 100 KB mỗi tệp chữ, 400 KB mỗi skill | như trên | a |
| Thông báo beta | Anthropic 2026-11-24: Skills over MCP public beta trong Claude; bật mặc định cho Pro/Max/Ultra, Team cần quản trị bật | claude.com/resources/articles/skills-over-mcp-tasks-and-more | b |
| Trường bị bỏ qua ở skill MCP | `allowed-tools`, `hooks`, `model`, `effort`, `context`, `agent`, `paths`, `metadata`; lệnh chèn `!` không chạy | code.claude.com/docs/en/skills | b |
| Chuẩn Agent Skills | Repo `agentskills/agentskills` (HEAD `83021e2b`), Apache-2.0 và CC-BY-4.0. Sáu trường: `name` (1–64, trùng thư mục), `description` (1–1024), `license`, `compatibility` (≤ 500), `metadata`, `allowed-tools` (thử nghiệm). Không số phiên bản, không tổ chức trung lập quản trị | agentskills.io/specification | b |
| Validator `skills-ref` | README: "intended for demonstration purposes only. It is not meant to be used in production." | github.com/agentskills/agentskills/tree/main/skills-ref | b |
| Khoá ngoài chuẩn | claude.ai upload và Skills API chỉ nhận sáu trường; lỗi mẫu nêu đích danh `argument-hint` | code.claude.com/docs/en/skills | b |
| Nơi các host đọc skill | Codex `.agents/skills` · Cursor `.agents/skills`, `.cursor/skills`, tương thích `.claude/skills` · Gemini CLI `.gemini/skills`, bí danh `.agents/skills` · Copilot `.github/skills`, `.claude/skills`, `.agents/skills` · OpenCode `.opencode/skills`, tương thích `.claude/skills`, `.agents/skills` | learn.chatgpt.com/docs/build-skills · cursor.com/docs/context/skills · geminicli.com/docs/cli/skills · docs.github.com/en/copilot/concepts/agents/about-agent-skills · opencode.ai/docs/skills | b |
| MCP Registry | Còn preview, chỉ giữ metadata server, không phân phối skill | modelcontextprotocol.io/registry/about | b |

### 4.2 Ma trận host

Chỉ ghi phần đổi hoặc chưa có so với [research 2026-11-02](2026-11-02-multi-provider-harness.md) và
[2026-11-19](2026-11-19-codex-harness.md). Tất cả mức (b).

| Host | Bản mới nhất | Hook chặn trước tool | Đọc gì của `.claude/` | Đổi đáng kể |
|---|---|---|---|---|
| Claude Code | 2.1.332 (2026-11-24); thẻ `stable` 2.1.326 | 34 sự kiện; hook lỗi không chặn nếu thiếu `onFailure: "block"`, cả trong Code Mode từ 2.1.329 | — | Skill từ MCP (beta), sự kiện `PreSkillShellCommand` ở 2.1.332 |
| Codex CLI | 0.172.0 (2026-11-24), Apache-2.0 | `PreToolUse` như cũ; `ask` vẫn chưa hỗ trợ | Không; skill ở `.agents/skills` | Không mục nào gắn nhãn phá vỡ ở 0.171.0 và 0.172.0 |
| Cursor | CLI 2026.11.19 | `preToolUse` (`deny`, `failClosed`); cloud agent chạy hook lệnh từ `.cursor/hooks.json` của repo | `.claude/skills`, `.claude/agents`, hook trong `.claude/settings.json` | Có bảng hook riêng cho cloud agent; thêm `subagentStart`/`subagentStop` |
| GitHub Copilot CLI | 1.0.117 (2026-11-27), giấy phép riêng, không OSI | `preToolUse`: lỗi là chặn, hết giờ là cho qua | `.claude/skills`, hook trong `.claude/settings.json`, `CLAUDE.md`, `AGENTS.md` | Cloud agent chỉ đọc `.github/hooks/*.json`, coi `ask` là `deny` |
| Gemini CLI | 0.71.1 (2026-11-24), Apache-2.0 | `BeforeTool` như cũ | Không; skill ở `.gemini/skills` hoặc `.agents/skills`; `AGENTS.md` chỉ khi khai `context.fileName` | README: dành cho Gemini Code Assist doanh nghiệp; gói cá nhân đã sang Antigravity CLI |
| OpenCode | npm `opencode-ai` 1.19.6 (2026-11-17), MIT; tag GitHub tới v2.4.2 | Dòng 2.x: `ctx.tool.hook("execute.before", …)` trong `Plugin.define`; "plugin V1 không chạy ở V2" | `.claude/skills`; `CLAUDE.md` khi thiếu `AGENTS.md` | Mẫu `opencode-xt.ts` của khung viết theo API V1 (`"tool.execute.before"`, phiên chính đã đọc tệp) |

- `AGENTS.md` nay do Agentic AI Foundation thuộc Linux Foundation quản trị (agents.md). Claude Code từ 2.1.277 đọc
  `AGENTS.md` khi thư mục không có `CLAUDE.md`; có cả hai thì chỉ đọc `CLAUDE.md` (code.claude.com/docs/en/memory).
- Hook có chạy ở chế độ không người của Cursor (`-p`), Gemini (`-p`), Codex (`codex exec`) và OpenCode
  (`opencode run`) hay không: tài liệu vẫn không nói, như hai lần đọc trước.
- Hệ quả cho skill: Cursor, Copilot và OpenCode đọc thẳng `.claude/skills`; Codex đọc gương `.agents/skills`. Trong sáu
  host có adapter, chỉ Gemini CLI chưa nhận skill của khung (Grok chưa tra lại).

### 4.3 SDK agent

| Dữ kiện | Giá trị | Nguồn | Mức |
|---|---|---|---|
| Claude Agent SDK nạp gì | Bỏ `settingSources` thì đọc như CLI: settings dự án cùng hook, CLAUDE.md, skill, agent, command trong `.claude/`. Hook tệp và hook callback chạy song song; chặn bằng `permissionDecision: "deny"` | code.claude.com/docs/en/agent-sdk/claude-code-features | b |
| Phiên bản và giấy phép | Python `claude-agent-sdk` 0.2.189 (2026-11-25), MIT. TypeScript 0.3.332: "All rights reserved", theo Commercial Terms | pypi.org · github.com/anthropics/claude-agent-sdk-typescript | b |
| OpenAI Agents SDK | `openai-agents` 0.26.0 (2026-11-24), MIT. Có guardrail và `needs_approval` cho tool. Không thấy cơ chế đọc `AGENTS.md`, `SKILL.md` hay tệp hook | openai.github.io/openai-agents-python | b |
| LangGraph, Deep Agents | `langgraph` 1.2.24 (2026-11-20), MIT; `interrupt()` cần checkpointer. `deepagents` 0.7.42 theo Agent Skills spec nhưng chỉ nạp nguồn được truyền vào, không quét `.claude/skills` | docs.langchain.com | b |
| Khung tương tự × SDK | README của spec-kit, OpenSpec, BMAD, superpowers không nêu tích hợp với ba SDK trên | github.com (README gốc) | b |
| Codex làm MCP server | Đã gỡ `codex mcp-server`; thay bằng Codex SDK và app server "experimental" | learn.chatgpt.com/docs/mcp-server | b |

### 4.4 Mức tự chủ và "software factory"

| Dữ kiện | Giá trị | Nguồn | Mức |
|---|---|---|---|
| Bộ nhãn "L2 Pair → L3 Agentic SDLC → L4 Lights-on Factory" | Không tìm thấy trang nào chứa đủ bộ; cụm "earned autonomy" cũng không có nguồn sơ cấp | (truy vấn ở §8) | không tìm thấy |
| Dan Shapiro, năm mức | 2026-01-23. L0 tự viết · L1 giao việc rời · L2 pairing · L3 người review mọi thứ · L4 theo spec, kiểm sau 12 giờ · L5 dark factory. Không có số đo để lên mức | danshapiro.com/blog/2026/01/… | b |
| Feng, McDonald, Zhang, "Levels of Autonomy for AI Agents" | arXiv 2506.12469. Mức theo vai của người: Operator, Collaborator, Consultant, Approver, Observer | arxiv.org/abs/2506.12469 | b |
| Dash0, sáu mức | Blog hãng, cập nhật 2026-11-09. Ngưỡng đề xuất để lên mức: tỉ lệ đạt kịch bản > 90 %, báo sai của bộ đánh giá < 5 %, người ghi đè < 10 % trong 20 PR gần nhất; bề mặt rủi ro cao "may never qualify" | dash0.com/knowledge/the-six-levels-of-agentic-software-engineering | b |
| Anthropic, đo tự chủ thực tế | 2026-02-18. Tự duyệt toàn phần: khoảng 20 % phiên ở người mới, trên 40 % sau khoảng 750 phiên. "effective oversight doesn't require approving every action but being in a position to intervene when it matters" | anthropic.com/research/measuring-agent-autonomy | b |
| Addy Osmani, "Software Factories, Light and Dark" | 2026-07-20. "Verification, not generation, is the real constraint on a factory." | addyosmani.com/blog/software-factories | b |
| "AWS ADP" | Không tìm thấy. AWS có AI-DLC (phương pháp ba pha, người duyệt kế hoạch), không có thang mức | aws.amazon.com/blogs/devops/ai-driven-development-life-cycle | thứ cấp |
| Công thức "Intent × Guardrails × Verification × Evidence" | Truy về Sonar qua The New Stack (khoảng 2026-10-15); hai URL trả 403, chưa đọc nguyên văn | thenewstack.io/ai-code-confidence-gap | thứ cấp |
| Chuẩn chính thức cho agent tự chủ | NIST AI Agent Standards Initiative (2026-02-17) chưa ban hành hướng dẫn nào. OWASP Top 10 for Agentic Applications for 2026 (2025-12-09). SLSA v1.2 chưa có phần riêng cho mã do agent viết | nist.gov/caisi/ai-agent-standards-initiative · genai.owasp.org | b, thứ cấp |

### 4.5 Khung tương tự: onboarding, đường nhanh, đa host, cộng đồng

Sao lấy từ trang HTML của GitHub (làm tròn, một nguồn); API trả 403 cho repo ngoài phạm vi phiên.

| Dự án | Lệnh tới lần chạy đầu | Đường cho việc nhỏ | Đa host | Cộng đồng |
|---|---|---|---|---|
| github/spec-kit (`f2010547`, v1.4.5) | 3: `uv tool install specify-cli`, `specify init … --integration …`, `cd` | Không có tên riêng; mở rộng bằng extension | Cờ `--integration` lúc init | ≈ 152,6k sao; README dịch zh-CN, ja, ko |
| Fission-AI/OpenSpec (`dff0188f`) | 2: cài, `openspec init` | Profile mặc định chỉ hai lệnh; profile mở rộng bật riêng | 46 mục; cài skill vào `.agents/skills` rồi link sang thư mục host | ≈ 75,9k sao; Discord; telemetry bật mặc định |
| bmad-code-org/BMAD-METHOD (`e435a225`, v6.12) | 2: `npx bmad-method install`, gọi `bmad-build` | Bốn đường theo cỡ và rủi ro: Trivial (sửa thẳng), One-session, Epic-sized, Project-sized | Skill chuẩn qua `npx skills add` | ≈ 55,9k sao; Discord |
| obra/superpowers (`22f0b463`, v6.4.2) | 1 lệnh plugin mỗi host | Không có | 16 host, plugin riêng từng host | ≈ 328,9k sao; không Discussions |
| X-Templates | 2: `git clone`, `install.py --new …` (3,9 s) | Chưa có trang mô tả | 1 host hỗ trợ, 6 thử nghiệm | 15 sao; 0 issue; README Anh và Việt |

Không dự án nào trong bốn dự án lớn có ROADMAP ở thư mục gốc hay quy trình RFC/ADR cho người đóng góp. Chưa tìm được
khung "software factory" mã nguồn mở nào trên 5 000 sao ngoài nhóm này (spec-kitty ≈ 1,7k, ai-sdlc ≈ 457).

## 5. Số đo tại chỗ (phiên chính, 2026-11-28)

| Số đo | Giá trị | Cách đo |
|---|---|---|
| Tạo dự án mới | 3,9 s (real), kết thúc "0 lỗi · 3 cảnh báo" | `time python3 scripts/install.py <tạm>/demo --new --name team-notes --pack web-api-ts --idea "Team notes"` |
| Tệp trong dự án mới | 425 tệp git theo dõi: `.xtemplates` 314 (6,1 MB), `.claude` 39 (1,7 MB), `src` 15 | `git ls-files`, `du -sh` |
| README dự án mới | 248 byte, 5 dòng nội dung, không có bước kế; lệnh cài kết thúc bằng một dòng "✓ dự án mới" | đọc tệp sinh ra; `install.py:3103-3113` |
| Tệp người mới phải đọc | `AGENTS.md` 9 459 B, `PROJECT.md` 5 213 B, `BLUEPRINT.md` 40 710 B (74 chỗ ghi MUST), tất cả tiếng Việt | `wc -c`, `grep -c` |
| Bước kế máy đọc | `xt_flow.py --json` trả `next.action: "replan"`, lý do "vòng lặp chưa bật"; chỉ có dạng JSON | chạy ở dự án mới |
| Skill so với chuẩn | 17/17: tên trùng thư mục và đúng mẫu; mô tả 210–553 ký tự (trần 1 024); 15–57 dòng (trần 500). 15/17 dùng khoá `argument-hint` ngoài chuẩn. Không tệp skill nào có chuỗi mở lệnh chèn | script đọc frontmatter ở vùng tạm của phiên |
| Test kiểm skill theo chuẩn | Không có: `tests/` chỉ có `test_skill_factory`, `test_skill_routing`, `test_hook_skill_shell` | `ls tests`, `grep agentskills` |
| Trần tệp nóng | `guard.py` 24 688/24 689 dòng, `xt.py` 23 624/23 626 | `wc -l`, `tests/test_docs_budget.py` |

## 6. Điều bản nhận định không nói

- **Trọng lượng khung trong repo đích.** 353 tệp trước dòng mã sản phẩm đầu tiên là ma sát lớn hơn lệnh cài. Đường xử
  lý đã chọn là artefact `.pyz` ghim digest (ADR-0097, P0–P1 xong); các lát còn lại của nó có giá trị onboarding trực
  tiếp và nên được nêu như vậy khi xếp lịch.
- **Mức "hỗ trợ" của sáu host chờ một việc của người.** ADR-0068 chỉ cho ghi "hỗ trợ" khi có payload thật kèm phiên
  bản và ngày. Viết thêm adapter không đổi được nhãn này; chạy thật trên tài khoản của chủ dự án thì đổi được.
- **Thang tự chủ không có máy đọc.** Điều kiện như `first_pass_gate_rate ≥ 70 %` hay "can thiệp ≤ 15 %" đứng trong tài
  liệu, trong khi `xt_flow.py` đã tính `first_pass_rate`, `resolved_interventions`, `escaped_after_merge` từ sổ lát.
  Hai phần chưa nối với nhau.
- **Khung không áp luật kiểm skill cho chính mình** (kết luận 5).
- **Guard chặn nhầm một mẫu chỉ đọc.** Hai lượt `researcher` bị chặn khi nối `curl` với `python3 -I -c` để phân tích
  JSON; cả hai chuyển sang công cụ đọc web. Ghi nhận làm phản hồi công cụ, không sửa trong đợt này.

## 7. Quyết định

### 7.1 Làm (D-650; task ở PLAN)

| Việc | Vì sao | Task |
|---|---|---|
| README dự án mới và dòng kết của `--new` nêu ba bước kế | Chỗ rơi đầu tiên của người mới; sửa ở `install.py`, không chạm tệp nóng | `T-5111` |
| Một trang "việc cỡ nào đi đường nào" (sửa thẳng, một phiên, đợt PLAN, vòng đời factory) | Bốn đường của BMAD là tiền lệ; khung có đủ các đường nhưng không nơi nào xếp chúng cạnh nhau | `T-5112` |
| Test kiểm skill theo giới hạn của Agent Skills, bằng stdlib | Áp luật của khung cho chính khung; `skills-ref` tự nhận là bản minh hoạ nên không thêm phụ thuộc | `T-5113` |
| Sinh gương `.agents/skills` cả khi `--harness gemini` | Host duy nhất có adapter mà chưa nhận skill; mở rộng ADR-0082, cần ADR mới | `T-5114` |
| SPEC rồi mã: khối `autonomy` trong `xt_flow.py --json` tính điều kiện lên và xuống mức từ sổ lát, chỉ tư vấn | Biến thang L0–L4 thành thứ đo được mà không tự nâng quyền; `merge_autonomy` vẫn là khoá do người đổi | `T-5115`, `T-5116` |
| Mẫu issue lỗi và đề xuất song ngữ; đoạn tiếng Anh ngắn ở CONTRIBUTING | 0 issue sau 15 sao; mẫu duy nhất hiện có dành cho dự án đích | `T-5117` |
| Cập nhật ma trận adapter theo §4.2; ghi rõ mẫu OpenCode chỉ áp dụng cho dòng 1.x | Dữ kiện host đổi sau 2026-11-19; mẫu V1 trên OpenCode 2.x có thể không chặn gì | `T-5118` |
| Đọc nguyên văn tài liệu plugin OpenCode 2.x rồi viết mẫu adapter cho dòng đó | Phát hiện ở mức (b), phải tự đọc trước khi sửa; giữ mẫu V1 cho người còn dùng 1.x | `T-5119` |

### 7.2 Không làm lúc này (D-651) và điều kiện mở lại

| Đề xuất | Lý do | Mở lại khi |
|---|---|---|
| Phân phối skill qua MCP server | Không chạy ở phiên cloud, `claude -p`, GitHub Actions, Agent SDK; skill MCP mất `hooks`; server ngoài connector không được quét; khung phải vận hành một server (trái mặc định tự host tối giản) | Tài liệu Claude Code bỏ bốn chế độ trên khỏi danh sách chưa hỗ trợ và hết beta; hoặc một host thứ hai công bố hỗ trợ đầy đủ |
| Adapter cho OpenAI Agents SDK và LangGraph | Hai SDK không đọc `AGENTS.md`, `SKILL.md` hay tệp hook; tích hợp nghĩa là viết lại harness thành thư viện; không khung tương tự nào làm | Có dự án đích dùng một trong hai SDK làm runtime |
| Claude Agent SDK "hạng nhất" | Đã dùng lại nguyên `.claude/` theo mặc định; chỉ cần một dòng tài liệu khi có lần chạy thật | Có lần chạy thật để ghi phiên bản và ngày |
| Dashboard thành control plane | ADR-0038 chủ ý không cho app chạy lệnh | Có người dùng thứ hai cần duyệt qua giao diện |
| API ghép blueprint, hệ plugin, tách nhiều gói | Không có người dùng chờ; plugin Claude không nạp ở phiên cloud ([khảo sát 2026-11-24](2026-11-24-similar-projects-survey.md)); đường tách đã chọn là ADR-0097 | Có yêu cầu cụ thể từ ngoài nhóm dự án đích hiện tại |
| Thêm nhãn "Earned Autonomy" mới | Nhãn không có nguồn; ba thang có nguồn dùng cùng "L2" cho ba nghĩa khác nhau; khung giữ thang L0–L4 của mình | — |

### 7.3 Cần chủ dự án

| Việc | Vì sao cần người |
|---|---|
| Hướng quốc tế: có dịch thư viện 2 890 mục và các tệp sinh ra sang tiếng Anh không | Quyết định kinh doanh và chi phí bảo trì song ngữ lâu dài cho repo một người. Khuyến nghị của phiên chính: chưa dịch; làm lớp mặt (`T-5111`, `T-5117`) trước và xét lại khi có issue hoặc PR đầu tiên từ người dùng ngoài nhóm |
| Chạy thật sáu host để lấy payload | Tốn hạn mức tài khoản của chủ dự án (đã ghi ở `templates/harness/README.md`) |
| Pilot S với người mới, đo thời gian tới kết quả đầu | Đã có ở [PLAN tích hợp §4](../docs/autopilot/PLAN-integrated-upgrade-2026-11-27.md); cần một người chưa biết khung |
| Video ngắn | Không có giá trị nếu do máy dựng; làm sau khi `T-5111` và `T-5112` xong |

### 7.4 Câu hỏi trong phiên: nâng trần `PROGRESS.md` lên 10 kB hay 100 kB (D-652)

| Dữ kiện | Giá trị | Nguồn | Mức |
|---|---|---|---|
| Trần của kênh nạp | "A hook's `additionalContext` … are capped at 10,000 characters"; vượt thì chỉ còn đường dẫn tệp và tối đa 2 000 ký tự đầu; "this cap has no setting or environment variable to raise it" | code.claude.com/docs/en/hooks, đọc 2026-11-28 | a |
| Lần nâng trước | ADR-0089 nâng lên 40 960 byte; PROGRESS 39 965 B làm `additionalContext` dài 31 535 ký tự, mất "Tiếp theo", "Bàn giao" và luật; ADR-0091 hạ về 8 192 | AUD-HAR-461 (🔴, đã sửa) | a |
| Hôm nay, vòng tự động tắt | `additionalContext` 7 989 ký tự; phần ngoài PROGRESS 752; còn 1 811 ký tự tới ngân sách 9 800 của hook | chạy `session-start.sh` với `{"source":"startup"}` | a |
| Byte so với ký tự | `PROGRESS.md` 8 185 byte là 7 294 ký tự (1,12 byte mỗi ký tự): trần đo bằng byte tính dấu tiếng Việt hai lần | đo tệp | a |
| Khi vòng tự động bật | Khối Autopilot tới 2 400 ký tự, ngân sách PROGRESS còn khoảng 6 600 ký tự, thấp hơn 7 294 hiện có: phần cuối (Bàn giao phiên) bị cắt | tính từ `session-start.sh:99-118`, chưa tái hiện với vòng đang bật | suy từ mã |

100 kB không đi qua được kênh này. 10 kB vừa khi vòng tự động tắt nhưng làm phần cuối bị cắt nhiều hơn khi vòng bật. Cách
có thêm chỗ mà không mất phần cần đọc là đổi thứ tự nạp và đo bằng ký tự (`T-5120`); nội dung dài hơn nữa thuộc về
CHANGELOG, sổ quyết định và PLAN như hiện nay.

## 8. Chưa xác minh

- Phiên chính chưa đọc lại nguyên văn các nguồn mức (b); trích dẫn ở §4 ngoài hai nguồn mức (a) đi qua bản tóm tắt.
- Bộ nhãn L2/L3/L4 và "earned autonomy": đã thử truy vấn `"Lights-on Factory" "Agentic SDLC" "earned autonomy" L2 Pair
  L3 L4`; không có kết quả chứa đủ bộ. "AWS ADP": không tìm thấy sản phẩm hay khung nào tên này.
- Bài The New Stack chứa công thức code confidence (403); danh sách host của agentskills.io (trang trả rỗng); ma trận
  client của Skills over MCP (mất dấu tick khi đọc).
- Số contributor và ngày phát hành của bốn khung tương tự (API 403); số sao là số làm tròn từ trang HTML.
- `skills-ref` và mọi validator bên ngoài: chưa chạy. Claude Agent SDK với harness của khung: chưa chạy thật.
- Số liệu ngành về nút cổ chai review (Faros, Qodo, Stack Overflow 2026, Octoverse 2026) chỉ đọc qua tóm tắt hoặc
  nguồn thứ cấp nên không dùng làm căn cứ cho quyết định nào ở §7.

## 9. Cảnh báo

- **Beta hai tầng:** phần mở rộng Skills over MCP ở "Beta stage of the extension lifecycle" dù SEP đã Final; phần của
  Claude là public beta. Server có thể đổi skill bất cứ lúc nào.
- **Giấy phép:** Claude Agent SDK TypeScript không phải giấy phép OSI. BMAD kèm ghi chú nhãn hiệu.
- **Telemetry mặc định bật:** OpenSpec, superpowers. Cách cài chính thức của OpenSpec là `curl … | sh`.
- **Nguồn có lợi ích:** Qodo, Sonar, Faros, Dash0 bán công cụ kiểm chứng hoặc quan sát; số của họ là "tuyên bố, chưa
  tự đo".
- **Thuật ngữ:** "L2" ở Shapiro là pairing, ở Dash0 là người review mọi PR, ở Feng và cộng sự là Collaborator, ở khung
  là tự merge làn nhanh. Khi trao đổi với bên ngoài phải nêu thang nào.
