# ADR-0096: Guard chặn lệnh merge khi PR chưa đủ điều kiện merge

- **Trạng thái:** Đã chấp nhận ngày 2026-11-23 (D-547, T-3999).
- **Sửa:** ADR-0018/0019, phần «còn lại mặc định cho chạy» của `LOOP-STOP-002` và chấp nhận AUD-HAR-454 ở D-534.
- **Giữ:** L3, `merge_review: optional`, `merge_hard_exceptions: auto`, `release_signoff: agent`; ADR-0095 quyết phạm vi rà sớm.
- **Triển khai:** T-4000…T-4002 của [PLAN cải tiến](../autopilot/PLAN-improve-2026-11-23.md).

## Bối cảnh

Ở `main` `7ce015f`, `_merge_verdict` và `_merge_ask` có thể trả `ask` không mã khi `merge-check` chưa cho merge hoặc
head đã đổi. Chính sách mặc định coi đó là `OTHER_ASK` và cho chạy. Đã tái hiện bằng kết quả `merge-check` giả trên
CLI, REST và MCP; không gửi lệnh merge thật. Ruleset nhánh không thay thế được quyết định tự chủ, nguồn review hay
phân loại làn của khung, và dự án đích có thể chưa áp ruleset.

## Phương án

1. Giữ hành vi, dựa vào CI/ruleset phía máy chủ. Không đủ khi lớp đỡ chưa được cấu hình hoặc chỉ khung biết điều kiện.
2. Thêm dấu văn xuôi vào `REASON_CODES`. Ít sửa nhưng đổi lời giải thích có thể làm mất hàng rào lần nữa.
3. **Đặt mã tại nơi sinh, truyền metadata cùng lý do qua các đường gọi** (chọn). Bộ luật vẫn trả `ask`; mặc định ánh
   xạ mã thành `deny`, chế độ `strict` giữ `ask`.

## Quyết định

| Kết quả kiểm | Mặc định | `strict` | Lớp đỡ phía máy chủ và bước tiếp |
|---|---|---|---|
| Ngoại lệ cứng | Giữ `HARD_EXCEPTION`, chặn | Hỏi | Ruleset không biểu diễn đầy đủ ngoại lệ khung; chủ dự án xử lý theo chính sách đã chọn |
| Không đọc được kiểm/repo/PR | Giữ `UNVERIFIED`, chặn | Hỏi | Không biết trạng thái; đọc lại bằng `pr next`, không đoán |
| Thiếu review hợp lệ | Giữ `REVIEW_MISSING`, chặn | Hỏi | Ruleset có thể chỉ biết review GitHub, không biết bằng chứng của khung |
| `wait` | `MERGE_INELIGIBLE`, chặn | Hỏi | Nháp được GitHub giữ; CI chờ chỉ được giữ khi đã cấu hình required checks; đợi `pr next` |
| `fix` | `MERGE_INELIGIBLE`, chặn | Hỏi | GitHub giữ conflict; CI đỏ cần required checks; sửa đúng lý do máy trả |
| `update` | `MERGE_INELIGIBLE`, chặn | Hỏi | Yêu cầu cập nhật base phụ thuộc ruleset; cập nhật rồi kiểm lại |
| `human`, không ngoại lệ cứng | `MERGE_INELIGIBLE`, chặn | Hỏi | L1/L2 và làn của khung không được máy chủ tự hiểu; người merge ở giao diện GitHub/terminal riêng, tuân thủ ruleset |
| `closed` | `MERGE_INELIGIBLE`, chặn | Hỏi | GitHub từ chối PR đã đóng; máy kết thúc theo `pr next` |
| Verdict khác `merge` chưa biết | `MERGE_INELIGIBLE`, chặn | Hỏi | Không có bằng chứng đủ điều kiện; không tự diễn giải thành `merge` |
| `merge`, head khác pin | `MERGE_HEAD_MISMATCH`, chặn | Hỏi | `sha` của REST hoặc `--match-head-commit` giữ pin phía máy chủ; đọc lại head, không tự đổi pin |
| `merge`, head và repo khớp | Cho phép | Cho phép | Gửi pin đã kiểm; máy chủ từ chối nếu head đổi sau khi kiểm |

Các đường merge thiếu pin/có cờ khác vẫn phải kiểm cùng verdict trước khi áp hành vi cũ. Lát này không mở rộng quyền
cho chúng và không thay sàn cú pháp shell. `UNVERIFIED` chỉ giữ nghĩa cũ, không dùng làm tên thay thế cho quyết định
đã đọc được. Mã mới đi qua shell lồng, MCP và adapter; lời giải thích chỉ phục vụ người đọc. Không dùng biến toàn cục
có thể rò quyết định giữa hai lệnh.

Khoảng từ kiểm tới ghi không thể nguyên tử bằng hook: `pr next`/steward vẫn ghim đúng SHA, GitHub kiểm SHA khi ghi.
CI/ruleset phía máy chủ vẫn cần thiết; không tuyên bố hook thay thế ranh giới quyền hay xử lý mọi thay đổi trạng thái
ở cùng SHA. Không đổi mức tự chủ để cho một lệnh bị chặn đi qua. Người ở L1/L2 dùng luồng riêng của người; agent ghi
việc cần người và tiếp tục phần độc lập theo `loop defer`.

## Kiểm chứng và đường lùi

- Ma trận verdict × CLI/REST/MCP/adapter × mặc định/strict; đối chứng merge đúng head và chặn cũ.
- Corpus `autonomy-bench` gắn AUD-HAR-454; regression các lệnh lành, shell lồng và không rò metadata.
- Chạy cổng commit, CI và một lượt rà độc lập theo ADR-0095 trước merge. Revert riêng PR này là đường lùi.

## Nguồn

Đối chiếu ngày 2026-11-23:

- [GitHub CLI: gh pr merge](https://cli.github.com/manual/gh_pr_merge) — pin bằng `--match-head-commit`.
- [GitHub REST: merge a pull request](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request) — tham số `sha`,
  HTTP 409 khi head không khớp.
