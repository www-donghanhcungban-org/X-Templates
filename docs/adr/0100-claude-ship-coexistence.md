# ADR-0100: Chung sống với Claude Ship — không dùng làm đường merge, chặn bằng quy tắc GitHub

- **Trạng thái:** Đã chấp nhận ngày 2026-11-24 (D-565)
- **Làm rõ:** ADR-0018 (guard không hỏi người), ADR-0027 (steward), ADR-0036 (merge ghim head, không auto-merge), ADR-0062 và ADR-0096 (review một lần, dấu ghim head), `LOOP-ORCH-005`
- **Căn cứ:** [nghiên cứu Claude Ship](../../research/2026-11-24-claude-ship.md) (tài liệu chính thức, trích nguyên văn, đọc 2026-11-24)

## Bối cảnh

Ngày 2026-11-23 Anthropic ra mắt Claude Ship: Code Review (GA), PR Steward và Claude Approvals (public beta), cùng `/ship` và `/steward` ở CLI. Chúng trùng một phần với phần của khung (theo dõi PR, rà độc lập, cổng merge) nhưng chạy ngoài hàng rào của khung: theo tài liệu, hook `PreToolUse` và git hooks của dự án không áp dụng cho `gh`/`git` do `/ship` tự chạy; `/ship` không có xác nhận thật (chỉ đếm ngược vài giây); approving review của Claude được GitHub tính là approval.

## Quyết định

1. **Tự động theo bậc, mỗi bậc có hàng rào; không có bậc "merge không ai duyệt".** Mặc định bậc A. Bậc cao hơn là lựa chọn của chủ dự án (việc của người: bật ở cấp tổ chức, đặt trần chi phí), và chỉ khi mọi hàng rào của bậc đó đã có:

   | Bậc | Tự động | Hàng rào bắt buộc |
   |---|---|---|
   | A (mặc định) | autopilot của khung: mở PR, `pr next`, theo dõi nền, rà bằng reviewer bậc cao hơn, merge ghim head qua steward của khung | guard, ruleset GitHub, CI |
   | B | A + Code Review (GA) tự chạy trên mọi PR như tín hiệu rà phụ | trần chi phí đặt trước; không thay dấu `pr reviewed` |
   | C | B + PR Steward ở chế độ Manual (`@claude steward`) + Approvals ở `observe` | mục 3 dưới đây; không `seats: 0`/`seats: 1`; Claude App ngoài bypass list |
   | — (không cho) | merge mà không người duyệt qua Approvals, auto-merge/merge queue với policy không đòi người | — |

   Khung **không** dùng Approvals thay dấu `pr reviewed`; merge vẫn do `pr next` quyết (CI xanh, review khi được đòi, ghim head).
2. **`/ship` và `/steward` không thuộc luồng của khung** (chúng đi vòng qua guard). Dự án đích muốn tắt: managed settings `skillOverrides` đặt `ship-local` và `steward` là `off`. **Không** dùng deny `Bash(git push *)` để tắt, vì nó cũng chặn chính autopilot của khung đẩy nhánh.
3. **Hàng rào thật nằm ở GitHub**: ruleset/branch protection bắt buộc review của người, Claude GitHub App **không** ở danh sách bypass, không bật auto-merge hay merge queue cho policy không đòi người duyệt; nếu bật Approvals thì đặt `observe` trước, không dùng `seats: 0`, `seats: 1` hay `claude: approves` không kèm rà.
4. **Code Review (GA) được phép là một tín hiệu rà phụ**, không thay dấu `pr reviewed` của khung (reviewer bậc cao hơn người viết, ghim head). Bật nó tốn tiền token và cần chủ tổ chức: việc của người, không tự động (AGENTS.md §5).
5. Yêu cầu tương ứng cho dự án đích: `WF-REVIEW-022` (SHOULD, `framework/10-workflow/code-review.md`) kèm cách kiểm; không đổi mã công cụ.

## Hệ quả

- Khung không phụ thuộc dịch vụ trả phí, beta và đóng; dự án đích có đường chung sống rõ ràng thay vì bị bất ngờ bởi `/ship`.
- Mất khả năng tận dụng PR Steward/Approvals tự động; đổi lại không có đường merge ngoài kiểm soát của `pr next`.
- Phải theo dõi: tài liệu Claude Ship còn đổi nhanh (beta).

## Xét lại khi

- PR Steward và Approvals lên GA, hoặc tài liệu nêu rõ hook `PreToolUse` của dự án áp dụng cho `/ship`.
- Có số đo thật trên repo của khung (precision của Code Review ở observe mode) cho thấy giá trị lớn hơn chi phí.
- Anthropic bổ sung trần chi phí mặc định cho PR Steward.

## Phương án đã loại

- Dùng Claude Approvals thay dấu `pr reviewed`: thêm đường approval mà `pr next` không kiểm, ngược P1 và ADR-0096.
- Chặn `/ship` bằng deny `Bash(git push *)`: chặn luôn autopilot của khung.
- Bỏ qua Claude Ship trong tài liệu: dự án đích sẽ dùng `/ship` mà không biết nó đi vòng qua guard.
