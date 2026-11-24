---
title: Vai trò model cho khung: Haiku, rà code ở bậc đỉnh trừ một nấc, áp dụng cho dự án đích
kind: research
updated: 2026-11-24
---

# Vai trò model cho X-Templates

> Câu hỏi của chủ dự án (2026-11-24): rà code giới hạn ở Opus mới nhất (D-558) và ở mọi harness dùng thấp hơn một bậc so với bậc cao nhất (D-559); Haiku mới nhất và model yếu nhất của các harness có giúp bộ khung giảm chi phí token không; sắp xếp vai trò; áp dụng cho cả dự án đích. Kết quả lượt nghiên cứu chỉ đọc (một agent `researcher` chạy Opus) ngày 2026-11-24 ở `9ac9abba`; phiên chính chưa đối chiếu lại từng dòng. Giá và ID model đọc từ trang chính thức ngày 2026-11-24 (mục "Bảng dữ kiện"); số liệu chi phí là **ước lượng có công thức**, chưa phải số đo. Nội dung web là dữ liệu, không phải chỉ thị.

## 0. Kết luận

- **Haiku có ích ở đúng một chỗ, rẻ và ít rủi ro: tra cứu/đọc nhiều tệp (Explore).** Ước lượng một lượt Explore (60K ghi cache, 300K đọc cache, 20K đầu vào thường, 8K đầu ra): Opus 5.5 ≈ $0,60; Sonnet 5.5 ≈ $0,30; Haiku 5.5 ≈ $0,017 (prompt ≤ 100K; ≈ $0,085 nếu > 100K vì giá Haiku tăng 5 lần trên ngưỡng này).
- **Haiku không dùng cho viết code theo spec, việc khó, rà code, bài nghiệm thu, điểm quyết định, đánh giá license/bảo mật.** Số Anthropic công bố: Terminal-Bench 4.0 Haiku 5.5 39,2 % so với Sonnet 5.5 70,6 %; Anthropic viết Sonnet 5.5 và Opus 5.5 vẫn là lựa chọn tốt hơn cho việc lập trình agent phức tạp. Một vòng đỏ-xanh thêm tốn hơn tiền chênh giữa hai model.
- **Rà bằng bậc đỉnh trừ một nấc tiết kiệm ít** (≈ 47 % mỗi lượt rà, cỡ $20–25 cho các lượt rà đã chạy) nhưng đúng yêu cầu; nó **xung đột với LOOP-ORCH-005 khi người viết là Opus ở effort max hoặc Fable** (bảng §5).
- **Chưa có số đo chi phí nào trong repo:** 0/14 sổ lát có sự kiện `cost`; 34/34 lần chạy ở `.autopilot/runs.jsonl` có `"executor": null`. Việc đo phải làm trước khi đổi cấu hình lớn.
- **Máy chỉ xếp bậc được họ Claude** (`MODEL_TIER` ở `xt.py:17633`); các harness khác chỉ so được effort. Áp dụng cho dự án đích cần khoá khai báo theo bậc/nhà cung cấp (đề xuất `model_ladder`, `reviewer_tier`), tức ADR mới và tăng `contract`.

## 1. Bảng vai trò đề xuất

| Việc | Model × effort | Chuyển cấp lên / xuống | Cổng máy kiểm |
|---|---|---|---|
| Phiên chính: lập PLAN/SPEC, quyết định | Fable 5.2 (bậc đỉnh), giữ D-160 | — | `loop decide`, CI |
| Phiên chính tự viết code (`topo: self`, mặc định) | **Opus 5.5 @ high hoặc xhigh**, đổi `/model` trước khi viết code (giữ cache, LOOP-DESIGN-012) | đỏ 2 lần lên `executor-deep`, không lên Fable nếu diff còn cần rà | Gate + `pr reviewed` |
| Tra cứu/đọc nhiều tệp (Explore) | **Haiku 5.5 @ medium**: thêm `.claude/agents/explore.md` với `model: haiku` | kết luận dẫn sai `tệp:dòng` thì phiên chính đọc lại và lần sau dùng `inherit` | phiên chính đối chiếu từng trích dẫn |
| `researcher` | giữ Sonnet; chỉ tra số phiên bản hàng loạt từ JSON registry mới cân nhắc Haiku | — | mỗi dữ kiện có URL + ngày |
| `executor` | giữ Sonnet; **không** Haiku | đỏ 2 lần lên `executor-deep` | Gate |
| `executor-deep` | Opus 5.5 @ high (giữ) | lần 3 `blocked` | Gate |
| `reviewer` (diff Sonnet viết) | Opus 5.5 (đỉnh trừ một nấc), giữ | — | `pr reviewed --clean` (D-161) |
| `reviewer-alt` (diff Opus viết) | Opus 5.5 @ **max**; người viết phải ≤ xhigh | người viết Opus@max hoặc Fable: xem §5 | như trên |
| `acceptance-author` | giữ Sonnet; **không** Haiku | — | lệnh khoá bài nghiệm thu |
| `loop ci-triage`, lint/format | không cần LLM (bộ luật regex, `xt.py:9750`, `CI_TRIAGE_RULES`) | — | — |
| Tóm tắt, nháp mô tả PR | Haiku được nếu sản phẩm vẫn được rà | — | review / guard `ai_attribution` |

## 2. Hiện trạng trong repo (`tệp:dòng`)

| Agent | model | effort | maxTurns | Tệp |
|---|---|---|---|---|
| researcher | sonnet | — | 80 | `.claude/agents/researcher.md:5` |
| executor | sonnet | — | 120 | `.claude/agents/executor.md:5` |
| executor-deep | opus | high | 160 | `.claude/agents/executor-deep.md:5-7` |
| reviewer | opus | — | 80 | `.claude/agents/reviewer.md:5` |
| reviewer-alt | opus | max | 80 | `.claude/agents/reviewer-alt.md:5-7` |
| acceptance-author | sonnet | — | — | `.claude/agents/acceptance-author.md:5` |

- `LOOP-ORCH-005` (`framework/11-autonomous-loop/orchestration-and-subagents.md:108`): bậc Haiku < Sonnet < Opus < Fable; cùng họ thì so effort low < … < max; khác nhà cung cấp thì nhận. `LOOP-ORCH-014` (`:117`) đỏ 2 lần lên `executor-deep`. `LOOP-ORCH-019` (`:121`) tên tầng, không tên model; phiên chính Fable → Opus → Sonnet. `LOOP-ORCH-020` (`:123`) mặc định tự làm; "chi phí/token mỗi task harness chưa ghi". `LOOP-ORCH-022` (`:125`) agent ngoài khung dùng `inherit`.
- Quyết định: ADR-0029 (hai tầng executor), D-160 (chuỗi model phiên chính), D-161 ("năng lực cao hơn"), D-558 (reviewer giới hạn `claude-opus-5-5`; người viết Opus hoặc cao hơn thì INCONCLUSIVE hoặc nâng bậc có lý do), D-559 (mọi harness đỉnh trừ một nấc). Không có D-NNN nào khác về Haiku hay chi phí.
- Cấu hình: `xt.yaml` của repo không khai `*_model_family`/`*_effort`; mẫu cho đích ở `framework/templates/xt.yaml:40-45` (dòng chú thích); `pr-review.yml:98` dùng `${{ vars.XT_REVIEWER_MODEL || 'claude-opus-5-5' }}`, họ tác giả đọc từ `xt.yaml` của nhánh đích.
- Đo chi phí: `docs/specs/SPEC-slice-ledger.md:47-66` định nghĩa sự kiện `cost` (`loop record --cost`, `pr reviewed --cost`), chưa có dữ liệu. `reviews.json`: cả 4 lượt rà ghi nhận đều reviewer `claude-fable-5-2`, author `claude-sonnet-5-5`.

## 3. Bảng bậc theo harness (giá USD/MTok vào/ra, bậc chuẩn; đọc 2026-11-24)

| Harness (adapter khung) | Bậc đỉnh | Đỉnh − 1 (dùng rà code) | Nhẹ nhất | Ghi chú |
|---|---|---|---|---|
| Claude Code | `claude-fable-5-2` $8/$40 | `claude-opus-5-5` $4/$20 | `claude-haiku-5-5` $0,10/$0,50 (≤ 100K), $0,50/$2,50 (> 100K) | 4 bậc; Mythos chỉ cấp hạn chế |
| Codex CLI | `gpt-6.2-astra` $8/$40 | `gpt-6.2-sol` $2/$10 | `gpt-6-luna` $0,10/$0,50 | thêm `gpt-6.1-terra` $1/$5; thứ bậc Astra > Sol > Terra > Luna suy từ mô tả docs, không phải bảng xếp hạng chính thức |
| Gemini CLI | API: `gemini-4-carbon` $2/$10 (từ 2026-12-01: $4/$20) | `gemini-4-argon` (cùng giá, không tiết kiệm) | `gemini-3.5-flash-lite` $0,30/$2,50 | trang CLI chỉ liệt kê Auto (Gemini 3/2.5): CLI có chạy Gemini 4 không **chưa xác minh** |
| Grok CLI | `grok-4.7` $2/$6 | `grok-4.6` (cùng giá, không tiết kiệm) | `grok-4.3` $1,25/$2,50 | model Grok CLI hỗ trợ: chưa xác minh |
| Cursor | đa nhà cung cấp theo model đã chọn | như vậy | Composer 2.5 $0,5/$2,5 | Auto gói cá nhân chỉ có chế độ Cost |
| Copilot CLI | đa nhà cung cấp | theo nhà cung cấp | Haiku 5.5 / GPT-6 Luna | hệ số premium request: chưa xác minh |
| OpenCode | theo nhà cung cấp cấu hình | theo nhà cung cấp | — | chưa tra |

**Khi harness chỉ có một hoặc hai bậc, hoặc đỉnh − 1 cùng giá với đỉnh (Grok, Gemini 4):** rà bằng chính bậc đỉnh với effort cao hơn người viết (máy đã nhận khi cùng họ có khai effort, D-161); người viết đã ở effort cao nhất thì dùng reviewer khác nhà cung cấp (máy nhận), không có thì `pr reviewed --inconclusive` + `loop defer`. **Không hạ cổng bằng cách ghi rà sạch**: Gate máy là trọng tài cuối nhưng không thay được rà khi `merge_review: required`.

## 4. Năm phát hiện

1. **Chưa có số đo chi phí** (§0). Mọi tiết kiệm là ước lượng.
2. **Cơ hội rẻ nhất là Explore.** Theo docs hiện hành, Explore chạy model của phiên cha (cha Fable thì Explore chạy Opus hoặc giữ Fable); cách hạ: tạo agent tên `Explore` với `model: haiku`. Khung chưa có tệp này.
3. **Haiku yếu rõ ở lập trình agent** và có hai bẫy: giá tăng 5 lần khi prompt > 100K (phiên agent dài dễ vượt); trên Bedrock/Vertex alias `haiku` trỏ Haiku 4.5 ($1/$5, không hỗ trợ effort).
4. **D-558 xung đột LOOP-ORCH-005 khi phiên chính viết code bằng Fable.** Mặc định `topo: self`, chuỗi Fable → Opus → Sonnet: Opus rà diff do Fable viết bị `review_capability_error` từ chối (`xt.py:17646-17690`, `MODEL_TIER` `:17633`). `orchestration-and-subagents.md:50` còn ghi "phiên chính chạy Fable → giao `reviewer-alt` với `model: fable`" (chưa theo D-558).
5. **Máy chỉ xếp bậc được họ Claude.** `MODEL_TIER = {haiku, sonnet, opus, fable}`; GPT-6.2 Astra/Sol/Luna ra họ `gpt`, Gemini 4 ra họ `gemini`. Codex agent không có `model` (`install.py:1496`); README adapter thừa nhận cặp `executor`/`reviewer` mặc định "không phân biệt được" (`framework/templates/harness/README.md:60-62`). Bậc theo họ cũng bỏ qua thế hệ: alias `opus` ở Microsoft Foundry là Opus 4.6 nhưng vẫn tính "cao hơn" Sonnet 5.5.

## 5. Xung đột "đỉnh − 1" với LOOP-ORCH-005

| Người viết | Reviewer đỉnh − 1 | Hợp lệ? | Xử lý |
|---|---|---|---|
| Haiku / Sonnet (mọi effort) | Opus 5.5 | có | — |
| Opus @ ≤ xhigh (gồm `executor-deep` @ high) | Opus 5.5 @ max | có (cùng họ, effort cao hơn) | khai `--author-effort`/`--reviewer-effort` |
| Opus @ max | Opus @ max | không | (1) hạ effort viết xuống xhigh; (2) reviewer khác nhà cung cấp (máy nhận); (3) INCONCLUSIVE + defer |
| Fable (phiên chính tự viết code) | Opus | không (bậc thấp hơn) | **đề xuất:** phiên chính chuyển Opus @ high/xhigh trong pha viết code; Fable chỉ để PLAN/SPEC/quyết định |

Đề xuất thứ tư cần sửa câu chữ D-160 và `LOOP-ORCH-019` nên cần D-NNN mới; không cần ADR mới vì ADR-0044/D-161 giữ nguyên.

## 6. Áp dụng cho dự án đích

**Đường đưa cấu hình vai/model vào đích hiện nay:** `.claude/agents/*.md` chép copy-if-absent (`scripts/install.py:13,72,1000-1012`): đích sửa thì giữ (`kept-own`), bản mới ghi `.xtemplates-new`, nâng bản không đè nhưng đích không tự nhận model mới. `xt.yaml` copy-if-absent, khoá mới nối dạng chú thích (`install.py:21,28,1115-1121`). Mẫu `framework/templates/CLAUDE.md:17` ghi chuỗi Fable → Opus → Sonnet; `framework/templates/AGENTS.md:51` liệt kê subagent. Codex: `.codex/agents/*.toml` sinh từ `.claude/agents`, chỉ mang `model_reasoning_effort`, **không có `model`** (`install.py:1494-1504`). Adapter Gemini/Cursor/Copilot/Grok/OpenCode không khai model nào. Workflow rà mẫu dùng biến repo `XT_REVIEWER_MODEL`, mặc định Opus 5.5.

**Đích dùng host khác** (chỉ Codex hay Gemini): quy tắc phải khai theo bậc của nhà cung cấp đó; hiện máy không làm được vì `model_family` gộp `gpt-*`/`gemini-*` thành một họ.

**Đề xuất khoá `xt.yaml`** (khai theo bậc/vai thay cho tên model cứng; cần ADR mới và tăng `contract` của ADR-0097):

```yaml
model_ladder:            # thấp → cao, theo nhà cung cấp; mặc định có sẵn cho anthropic
  anthropic: [haiku, sonnet, opus, fable]
  openai: [luna, terra, sol, astra]
reviewer_tier: top-1     # top | top-1 | <tên bậc>
author_tier: ""          # hoặc vẫn dùng author_model_family như cũ
```

Việc cần đổi: `review_capability_error` tra bậc theo `model_ladder` trước `MODEL_TIER`; `pr reviewed` cảnh báo khi model thật của reviewer lệch `reviewer_tier` và vẫn từ chối khi reviewer không cao hơn người viết; `doctor` cảnh báo khi `.claude/agents/reviewer*.md` ghim model trái `reviewer_tier` và khi đích dùng Codex/Gemini thiếu `model_ladder`; `install.py` render `model:` từ bậc (hoặc `inherit`) thay chuỗi cứng, Codex sinh `model` theo bậc khi đích có khai; mẫu `xt.yaml` thêm dòng chú thích cho khoá mới.

**Với ADR-0097:** bộ khoá `xt.yaml` là hợp đồng công khai nên thêm khoá phải tăng `contract`; mục B4 (tệp render thuộc khung, tuỳ biến ở overlay) nghĩa là khi B4 về, model trong agent phải lấy từ cấu hình hoặc overlay chứ không từ frontmatter sửa tay, nếu không sẽ mất khi nâng bản; đích tự đặt tên công cụ không ảnh hưởng luật bậc.

## 7. Chi phí: công thức và cách đo

Chi phí = Σ(đầu vào thường × giá vào + ghi cache × giá ghi + đọc cache × giá đọc + đầu ra × giá ra).

Một lượt rà (giả định 40K ghi cache 5 phút, 400K đọc cache, 10K đầu vào thường, 20K đầu ra gồm thinking ở effort max): Fable 5.2 ≈ $1,36; Opus 5.5 ≈ $0,72; chênh ≈ 47 % (≈ $0,64). Với số lượt rà đã chạy chỉ tiết kiệm cỡ $20–25: nhỏ. Giả định chưa kiểm: lượng thinking ở effort max của Opus so với Fable. Explore → Haiku ≈ 97 % mỗi lượt so với Opus; tổng phụ thuộc số lần gọi Explore (chưa đo).

**Cách đo:** (1) ghi `loop record --cost` / `pr reviewed --cost` bằng `tokens` + `price{source,as_of}` lấy từ `/usage` (có mục chi phí theo subagent) hoặc `total_cost_usd` khi chạy headless; (2) thí nghiệm Explore: 10 câu tra cứu, mỗi câu chạy cặp `haiku` và `inherit`, đo chi phí, tỉ lệ trích dẫn `tệp:dòng` sai và tỉ lệ phiên chính phải đọc lại tệp; **dừng** nếu Haiku sai > 1/10 hoặc phiên chính đọc lại > 30 %, báo khoảng tin cậy Wilson (AI-EVAL-018); (3) `perf trial` (ADR-0071) không áp dụng được vì đo lệnh tất định chứ không đo agent: dùng eval bật/tắt theo `LOOP-DESIGN-025`.

## 8. Bảng dữ kiện (đọc 2026-11-24; fetch trực tiếp trừ khi ghi khác)

| Mục | Giá trị | URL |
|---|---|---|
| Đội hình Claude | Fable 5.2 / Opus 5.5 / Sonnet 5.5 / Haiku 5.5; đều 1M ngữ cảnh, 128K đầu ra | https://platform.claude.com/docs/en/about-claude/models/overview |
| Giá (vào/ra, đọc cache) | Fable 5.2 $8/$40 ($0,20); Opus 5.5 $4/$20 ($0,20); Sonnet 5.5 $2/$10 ($0,10); Haiku 5.5 $0,10/$0,50 ($0,01) ≤ 100K, $0,50/$2,50 > 100K; Batch −50 % | https://platform.claude.com/docs/en/about-claude/pricing |
| Haiku 5.5 | ra mắt 2026-10-07; adaptive thinking; effort mặc định medium, hỗ trợ low…max (Claude Code) | https://platform.claude.com/docs/en/models/haiku-5-5/overview |
| Điểm chuẩn Haiku 5.5 (Anthropic công bố, chưa tự đo) | Terminal-Bench 4.0 39,2 % (Sonnet 5.5 70,6 %); OSWorld 2.1 72,4 % (83,9 %) | https://www.anthropic.com/claude-haiku-5-5 |
| Điểm chuẩn Opus 5.5 (công bố, chưa tự đo) | Terminal-Bench 4.0 66,4 % @ xhigh; FrontierCode 54,4 % | https://www.anthropic.com/news/claude-opus-5-5 |
| Model của subagent | Explore chạy model của phiên cha; ưu tiên: tham số khi gọi > frontmatter > `CLAUDE_CODE_SUBAGENT_MODEL` > phiên chính | https://code.claude.com/docs/en/sub-agents (đọc 100K/115K ký tự) |
| Alias theo nhà cung cấp | Bedrock/Vertex: `haiku` = Haiku 4.5, `sonnet` = Sonnet 4.5; Foundry: `opus` = Opus 4.6 | https://code.claude.com/docs/en/model-config (đọc 100K/135K) |
| Lời khuyên chi phí Claude Code | "For simple subagent tasks, specify `model: haiku`"; agent teams tốn khoảng 7 lần token | https://code.claude.com/docs/en/costs |
| Codex | Astra / Sol / Terra / Luna; Luna là "the smallest option" | https://learn.chatgpt.com/docs/models |
| Giá OpenAI | 6.2 Astra $8/$40; 6.2 Sol $2/$10; 6.1 Terra $1/$5; 6 Luna $0,10/$0,50 | https://developers.openai.com/api/docs/pricing |
| Giá Gemini (một phần) | Carbon/Argon $2/$10 (từ 2026-12-01 $4/$20); 3.8 Flash $0,75/$3,75; 3.5 Flash-Lite $0,30/$2,50 | https://aistudio.google.com/docs/pricing |
| Gemini CLI | Auto (Gemini 3 / 2.5) | https://geminicli.com/docs/cli/model/ |
| xAI | grok-4.7 / 4.6 $2/$6; grok-4.3 $1,25/$2,50 | https://docs.x.ai/docs/models |
| Cursor | Composer 2.5 $0,5/$2,5 | https://cursor.com/docs/models |
| Copilot (một phần) | danh sách đa nhà cung cấp | https://docs.github.com/en/copilot/reference/ai-models/supported-models |

**Chưa xác minh:** Gemini CLI có chạy Gemini 4 không và thứ bậc Neon/Hydrogen; model Grok CLI và OpenCode hỗ trợ; hệ số premium request của Copilot; thứ bậc chính thức Astra > Sol > Terra > Luna; điểm SWE-bench của Haiku/Sonnet/Opus 5.5; điểm Terminal-Bench của Sonnet 5.5 chỉ lấy từ trang Haiku; điểm độc lập 63,1 % của Opus 5.5 chỉ qua nguồn thứ cấp; chất lượng tiếng Việt của Haiku 5.5 khi viết tài liệu; lượng thinking của Opus ở effort max so với Fable; số lần Explore được gọi trong một lát; phần cuối hai trang docs dài chưa đọc hết.

## 9. Cảnh báo

- Giá: Haiku 5.5 có ngưỡng 100K (gấp 5 lần); Gemini 4 Carbon/Argon tăng gấp đôi từ 2026-12-01; Gemini 3.8 Flash tăng từ 2027-01-01.
- Trạng thái: Gemini CLI đã bị thay bằng Antigravity CLI cho người dùng gói miễn phí và Google One từ 2026-06-18; adapter `gemini-settings.json` cần kiểm lại.
- Tài liệu khung lỗi thời: `orchestration-and-subagents.md:50` trái D-558; `research/2026-10-13-ai-agent-research.md:52` còn ghi Fable 5.1 là bậc đỉnh (nay Fable 5.2 giá $8/$40); `harness-files.md` và `context-and-token-budget.md:63,123` nêu "Fable" không kèm số phiên bản.
- Đặt `DISABLE_TELEMETRY` tắt advisor (`LOOP-ORCH-023`).

## Ghi chú của phiên chính

Chưa đối chiếu từng `tệp:dòng`. Việc làm ngay không cần ADR (đã có D-558/D-559): giao reviewer bằng `model: opus`. Việc cần quyết và ADR mới: thang bậc theo nhà cung cấp, khoá `model_ladder`/`reviewer_tier`, quy tắc cho phiên chính viết code ở bậc Fable (§5), thêm agent `explore` dùng Haiku sau thí nghiệm §7.
