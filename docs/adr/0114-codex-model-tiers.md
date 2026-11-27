# ADR-0114: Phân bậc model Codex theo vai Claude Code

- **Trạng thái:** Đã chấp nhận ngày 2026-11-27 (D-634).
- **Liên quan:** [ADR-0098](0098-model-tiers-and-role-mapping.md) và [ADR-0110](0110-reviewer-effort-ceiling-and-routing.md).

## Quyết định

X-Templates dùng chung bảng bậc theo vai của Claude Code và Codex. Danh mục `codex debug models` trên CLI 0.172.0-alpha.2 ngày 2026-11-27 liệt kê bốn ID dưới đây và hỗ trợ effort `medium` và `high` cho cả bốn. Thứ tự là quy ước của X-Templates dựa trên mô tả model và chính sách phân vai ADR-0098.

| Bậc | Claude Code | Codex | Vai |
|---|---|---|---|
| `bottom` | Haiku | `gpt-6-luna` | `explore`, `executor-mech` |
| `top-2` | Sonnet | `gpt-6.1-terra` | `executor`, `researcher`, `acceptance-author` |
| `top-1` | Opus | `gpt-6.2-sol` | `executor-deep`, `reviewer`, `reviewer-alt` |
| `top` | Fable | `gpt-6.2-astra` | Phiên lập PLAN/SPEC khi chủ dự án bật |

`--sync-codex` luôn sinh gương repo khung từ bảng vai. Dự án đích tự chọn ghim bằng `--harness codex --codex-models`. Khi ghim model, executor thường mặc định `medium`. Executor sâu giữ `medium` và hai reviewer giữ `high`.

Dấu review dùng ID model thực tế. Máy so bậc với bốn ID Codex đã đối chiếu, tiếp tục đòi effort cao hơn khi model cùng bậc, và từ chối khi so một ID đã xếp bậc với model OpenAI chưa có bậc. Các bậc tin cậy được đóng trong mã cổng để bảng cấu hình dự án không đổi được luật review. Test buộc các bậc đó khớp bảng phân vai của khung.

## Hệ quả và đường lùi

Reviewer nhận clean cho executor thường theo bậc. Reviewer-alt nhận clean cho executor sâu cùng model khi tác giả chạy effort thấp hơn `high`. Nếu tác giả chạy cùng model với effort từ `high` hoặc viết ở bậc `top`, reviewer hiện hành báo INCONCLUSIVE. Hoàn tác thay đổi để gương khung trở lại kế thừa model phiên và cổng trở lại cách nhận diện trước đó.
