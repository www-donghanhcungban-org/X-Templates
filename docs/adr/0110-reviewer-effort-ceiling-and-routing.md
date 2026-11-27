# ADR-0110: Trần effort `high` cho reviewer và bảng tuyến theo người viết

- **Trạng thái:** Đã chấp nhận ngày 2026-11-27 (D-623, D-625, D-627).
- **Trạng thái triển khai:** lát nguồn — frontmatter hai vai, skill `/review` và gương `.agents`, `AGENTS.md` §8, `orchestration-and-subagents.md`, gương Codex sinh lại, test. Máy cưỡng chế trần (biến môi trường, tham số lần gọi, `--reviewer-effort`) là T-5071, chưa làm.
- **Liên quan:** [ADR-0098](0098-model-tiers-and-role-mapping.md) (thay phần effort `max` của reviewer; giữ bảng bậc và D-558/D-559), [ADR-0044](0044-reviewer-higher-capability.md) (D-161, reviewer cao hơn người viết), [ADR-0095](0095-immediate-effect-early-review.md) (rà sớm lớp tác động tức thì), [nghiên cứu hợp nhất](../../research/2026-11-26-unified-upgrade-plan.md) §4, §4.1, §12.4.

## Bối cảnh

ADR-0098 giữ reviewer ở `top-1` (opus) và dựa vào effort `max` để cao hơn người viết opus ≤ `xhigh`. Chủ dự án chốt (D-623) reviewer không dùng bậc cao nhất và không vượt effort `high`. Khi đó `review_capability_error` từ chối clean cho người viết cùng họ ở `high` trở lên (cùng họ thì effort reviewer phải cao hơn hẳn). `reviewer` chưa khai effort, `reviewer-alt` khai `max` (cả bản Codex), `maxTurns` 80.

## Quyết định

1. `reviewer` và `reviewer-alt`: `model: opus`, `effort: high`, `maxTurns: 120`. Bỏ mọi chỉ dẫn giao kèm `model` hoặc effort cao nhất của phiên chính. Dấu review cũ ở effort `max` giữ nguyên lịch sử.
2. **Bảng tuyến (D-625):**

   | Người viết | Reviewer | Kết quả |
   |---|---|---|
   | haiku/sonnet: `executor-mech`, `executor`, `researcher`, `acceptance-author` | `reviewer` opus/high | nhận clean |
   | `executor-deep`: opus/`medium` (mặc định của vai, D-627), khai `--author-effort medium` | `reviewer-alt` opus/high | nhận clean; đây là tuyến cho việc khó, kể cả diff lớp bắt buộc review (guard, hook, workflow — ADR-0095) |
   | Phiên chính opus effort ≥ `high` hoặc bậc cao nhất tự viết; lời gọi `executor-deep` bị đè effort lên ≥ `high` (tham số lần gọi hay biến môi trường) | `reviewer-alt` vẫn rà tìm 🔴 | không ghi clean: `pr reviewed --inconclusive` |

   Không sửa lời khai tác giả, không tự nâng reviewer.
3. `maxTurns: 120` là trần lượt của một lần chạy, không phải số lần review mỗi PR. `REVIEW_ROUNDS`, `max_rethink` không đổi. Hết lượt mà chưa đủ bằng chứng → INCONCLUSIVE.

## Phương án đã xét

- **Giữ effort `max`:** loại theo D-623 (trần chủ dự án); giữ được cặp opus/max so với người viết ≤ `xhigh` nhưng không phải điều chủ muốn.
- **Nới luật "reviewer cao hơn người viết" cho cùng họ:** loại — hạ cổng `LOOP-ORCH-005`, review clean rỗng.
- **Reviewer khác nhà cung cấp:** để sau; bảng bậc ngoài Anthropic còn `verified: false`.
- **Giữ frontmatter `executor-deep` ở `high`, hạ theo lần gọi:** loại (D-627) — dễ quên, lời khai `--author-effort` lệch thực tế. `medium` là mặc định của vai.

## Hệ quả

- Diff của `executor-deep` ở `high` và của phiên chính opus ≥ `high` không có review clean: nợ review tăng, trả theo lô ở pha harden (ADR-0062).
- Việc khó, kể cả lớp guard/hook/workflow, giao `executor-deep` opus/`medium`; chưa đo chất lượng tầng sâu ở `medium`: cần bộ đánh giá G10.
- Chi phí mỗi lượt reviewer giảm (effort thấp hơn), trần lượt tăng 80 → 120 (chưa đo).

## Giới hạn đã biết

- Frontmatter không cưỡng chế được trần: biến môi trường `CLAUDE_CODE_EFFORT_LEVEL` và tham số `effort` theo lần gọi đè frontmatter. Máy cưỡng chế là T-5071; đến lúc đó trần là kỷ luật.
- `agent_toml` không map `maxTurns` sang Codex và khoá TOML tương ứng chưa xác nhận: bản Codex chưa có trần lượt tương đương (khoảng trống, không tự thêm khoá).
- Bảng tuyến ghi nhận cặp hợp lệ theo luật hiện hành; chưa đo chất lượng review ở `high` so với `max`.

## Đường lùi

Đặt lại `effort`/`maxTurns` trong hai tệp agent (đổi `executor-deep` về `high` bằng D-NNN mới), chạy `python3 scripts/install.py . --sync-codex`, ADR mới thay ADR này. Dấu review đã ghi không bị ảnh hưởng.
