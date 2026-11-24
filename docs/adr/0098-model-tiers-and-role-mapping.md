# ADR-0098: Bảng bậc model theo nhà cung cấp và vai trò của từng agent, đồng bộ mọi harness

- **Trạng thái:** Đã chấp nhận ngày 2026-11-24 (D-558, D-559, D-560); triển khai theo hai lát (R1 bảng bậc, agent `explore`, tài liệu, đồng bộ Codex; R2 máy nhận bậc của nhà cung cấp khác và khoá `xt.yaml`).
- **Làm rõ:** ADR-0029 (hai tầng executor), ADR-0044 và D-161 (reviewer năng lực cao hơn người viết), ADR-0061 (cấu hình theo loại việc), ADR-0082 (harness Codex sinh từ `.claude/`), ADR-0097 (đích tự đặt tên, hợp đồng công khai).
- **Căn cứ:** [báo cáo vai trò model](../../research/2026-11-24-model-roles-haiku-and-top-minus-one.md) (giá, ID và điểm chuẩn đọc 2026-11-24; ước lượng chi phí chưa phải số đo).

## Bối cảnh

Phiên chính chạy Fable, reviewer đang là Opus (D-558) và mọi harness rà ở bậc thấp hơn đúng một nấc so với bậc cao nhất của nó (D-559). Ba chỗ chưa khớp: (1) mặc định `topo: self` nên phiên chính tự viết code ở Fable, mà Opus rà diff do Fable viết bị `review_capability_error` từ chối (`LOOP-ORCH-005`); (2) agent Codex sinh từ `.claude/agents` không có `model` nên cặp `executor`/`reviewer` không phân biệt được; (3) các adapter Gemini, Cursor, Copilot, Grok, OpenCode không nói gì về model. Chưa có số đo chi phí nào (0/14 sổ lát có sự kiện `cost`).

## Quyết định

1. **Một nguồn duy nhất là `framework/templates/harness/model-tiers.json`**: bậc theo vị trí so với đỉnh của nhà cung cấp (`bottom`, `top-2`, `top-1`, `top`), model cụ thể của mỗi bậc (ID, alias, giá, ngày đọc, mức xác minh) và bảng vai → bậc. Agent Claude (`model:`), agent Codex (`model`, lát R2) và mọi hướng dẫn cho harness khác đọc từ đó; một test đòi hai phía khớp nhau.
2. **Vai → bậc:** `explore` (tra cứu/đọc nhiều tệp, chỉ đọc) → `bottom`; `researcher`, `executor`, `acceptance-author` → `top-2`; `executor-deep`, `reviewer`, `reviewer-alt` → `top-1`. Phiên chính lập PLAN/SPEC/quyết định ở `top`; **khi viết code, phiên chính chuyển xuống `top-1` với effort ≤ xhigh** (giữ cache theo `LOOP-DESIGN-012`), để reviewer ở `top-1` effort `max` luôn cao hơn người viết. Người viết ở `top-1` effort `max` hoặc ở `top` thì reviewer phải khác nhà cung cấp; không có thì `pr reviewed --inconclusive` và `loop defer` (không hạ cổng).
3. **Haiku (`bottom`) chỉ cho việc tra cứu chỉ đọc**, qua agent `explore` (tool `Read`, `Glob`, `Grep`, không `Bash`, không ghi). Không giao Haiku viết code, việc khó, rà code, bài nghiệm thu, điểm quyết định, đánh giá license/bảo mật. Phiên chính đối chiếu từng trích dẫn `tệp:dòng` của `explore`; trích dẫn sai thì lần sau dùng `inherit`.
4. **Harness chỉ có một hoặc hai bậc, hoặc bậc `top-1` cùng giá với `top`** (Grok, Gemini 4 ở thời điểm đọc): rà bằng chính bậc đỉnh với effort cao hơn người viết; người viết đã ở effort cao nhất thì reviewer khác nhà cung cấp; không có thì INCONCLUSIVE. Harness chưa xác minh bậc ghi `chưa xác minh` trong bảng và không được máy dùng để xếp hạng.
5. **Phạm vi áp dụng:** repo khung và dự án đích. Agent Claude chép vào đích như cũ (copy-if-absent, ADR-0097 B4 sẽ chuyển sang render có dấu phiên bản); Codex sinh lại từ `.claude/agents` (`install.py --harness codex`, `--sync-codex`); Gemini/Cursor/Copilot/Grok/OpenCode không có tệp agent nên chỉ nhận bảng bậc và hướng dẫn ở `framework/templates/harness/README.md`.
6. **Máy kiểm (lát R2):** `model-tiers.json` thành nguồn bậc cho `review_capability_error` ở các nhà cung cấp đã xác minh (OpenAI: `luna` < `terra` < `sol` < `astra`); khoá `xt.yaml` `reviewer_tier` (`top` | `top-1`; mặc định `top-1`) và `author_tier`; `doctor` cảnh báo khi agent reviewer ghim model trái bậc. Thêm khoá `xt.yaml` là đổi hợp đồng công khai (ADR-0097): tăng `contract` và ghi CHANGELOG.

## Phương án đã cân nhắc

- **Chỉ đổi cấu hình Claude:** nhanh nhưng Codex vẫn không phân biệt được người viết và người rà, các adapter khác vẫn im lặng.
- **Haiku cho `executor`:** rẻ hơn nhưng Terminal-Bench 4.0 39,2 % so với Sonnet 5.5 70,6 % (số Anthropic công bố, chưa tự đo); một vòng đỏ-xanh thêm tốn hơn tiền chênh. Loại.
- **Giữ phiên chính viết code ở Fable:** xung đột với D-558 và `LOOP-ORCH-005`; giải bằng INCONCLUSIVE mỗi lần là bỏ rà. Loại.
- **Ghim tên model trong từng harness:** lệch khi nhà cung cấp đổi tên. Bảng bậc có ngày đọc và mức xác minh nên đổi một chỗ.

## Đo trước khi mở rộng

Giữ `explore` ở Haiku khi thí nghiệm nhỏ đạt: 10 câu tra cứu, mỗi câu chạy cặp `haiku` và `inherit`; đo chi phí, tỉ lệ trích dẫn `tệp:dòng` sai và tỉ lệ phiên chính phải đọc lại tệp; dừng nếu Haiku sai hơn 1/10 hoặc phiên chính đọc lại hơn 30 %; báo khoảng tin cậy Wilson. Ghi `--cost` ở `loop record`/`pr reviewed` (SPEC sổ lát) để có số thật. `perf trial` (ADR-0071) không áp dụng: nó đo lệnh tất định, không đo agent.

## Hệ quả

- Chi phí rà giảm khoảng 47 % mỗi lượt (ước lượng ở báo cáo) nhưng tổng nhỏ; khoản lớn hơn nằm ở `explore` nếu được gọi nhiều (chưa đo).
- Người viết ở `top-1` effort `max` không còn reviewer cùng nhà cung cấp hợp lệ: phải hạ effort viết, đổi nhà cung cấp hoặc chấp nhận INCONCLUSIVE.
- Giá Haiku 5.5 tăng 5 lần khi prompt vượt 100K: `explore` giới hạn `maxTurns` và chỉ trả bảng ngắn.
- Gemini CLI đã bị thay bằng Antigravity CLI cho một số gói từ 2026-06-18 (nguồn báo cáo, chưa tự kiểm): adapter Gemini cần kiểm lại trước khi dựa vào.
- Xét lại khi: số đo `--cost` cho thấy tiết kiệm lớn hơn hoặc nhỏ hơn dự kiến; nhà cung cấp đổi thang bậc; Codex hay Gemini công bố thứ bậc chính thức.
