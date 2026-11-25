# ADR-0104: Nới trần dòng của guard thêm 8 dòng cho tag glob chỉ gồm glob

- **Trạng thái:** Đã chấp nhận ngày 2026-11-25 (D-607, AUD-HAR-541, AUD-HAR-566).
- **Liên quan:** [ADR-0103](0103-guard-line-ceiling-for-tag-glob.md), [ADR-0018](0018-deny-dangerous-allow-rest.md), AUD-HAR-543.

## Bối cảnh

ADR-0103 đóng một phần AUD-HAR-541. Rà lại #815, `reviewer-alt` đo thêm các dạng còn lọt guard mà bash bung ra `v1.2.0` khi thư mục có tệp đó: đoạn chỉ gồm glob mà dấu chấm do glob sinh (`??????`, `*.*`), lớp ký tự mở bằng `!`, `]` hay lớp POSIX (`[!x]?.?.?`, `v1.2.[]0]`, `[[:digit:]]`, vốn chứa `:` nên bị tách đoạn), `[v]*`, và `shopt -s nocaseglob` với `V1.2.?`. Một lỗi nữa nằm trong bản sửa trước: `_glob_sub(..., count=1)` truyền `0` cho phần đuôi, mà `re.sub(..., 0)` thay tất cả, nên `[!x]?.?.?` không còn bị chặn (AUD-HAR-566).

## Quyết định

- `_glob_sub` giữ đúng số lần thay cho phần đuôi.
- Đơn vị lớp ký tự đọc `[!^]`, `]` đầu lớp và lớp POSIX; lớp POSIX không tách đoạn ở dấu `:`.
- Chữ còn lại sau khi bỏ glob xét không phân biệt hoa thường (`nocaseglob`).
- Đoạn mà chữ còn lại chỉ là dấu chấm bị coi là tag nếu: có `*` kèm dấu chấm hoặc lớp ký tự, hoặc không có `*` mà đủ dài (từ 6 ký tự) để khớp `vX.Y.Z`. `?.?.?` (5 ký tự) và `*` đơn lẻ vẫn được qua.

Nâng `LINE_CAPS` của `.claude/hooks/guard.py` từ 24.664 lên 24.672, đúng số đo sau sửa. Trần của các tệp khác giữ nguyên.

Phương án đã xét: coi mọi glob ở vị trí tên tag là tag phiên bản (đơn giản hơn nhưng chặn oan `HEAD:refs/heads/*` và refspec `fetch`, vì `_tag_glob` dùng chung cho refspec); chấp nhận lỗ hổng và chờ ruleset tag phía máy chủ (T-4007 cần quyền admin).

## Hệ quả

- Hồi quy: `RELEASE_TAG_DENY` thêm 10 lệnh. So với `main` trước #815, fuzz độ dài ≤ 5 (alphabet `[]!v0.?*aV`) chỉ có hai chuỗi base chặn mà head bỏ (`[]v[]`, `[]0[]`): đó là một lớp ký tự khớp đúng một ký tự, bash không bung ra tag nên không phải hồi quy an toàn.
- Dạng chặn oan thêm: đoạn glob kèm dấu chấm như `*.*` ở tên tag hay đích refspec. Chấp nhận được vì `git` từ chối `*`, `?`, `[` trong tên ref.
- Nới trần lần sau vẫn cần ADR riêng.
