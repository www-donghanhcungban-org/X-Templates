# ADR-0089: Nâng trần kích thước file và nhóm thư mục lên 5×

- **Trạng thái:** Đã chấp nhận ngày 2026-11-21 (yêu cầu của chủ repo: "x5 giới hạn file hiện tại").
- **Trạng thái triển khai:** Đã triển khai — `tests/test_docs_budget.py` (`CAPS`, `DIR_CAPS`, `SIZE_MARKS`, `MARK_FACTOR = 5`), `scripts/xt.py`, `.claude/hooks/session-start.sh`. **Thay một phần bởi [ADR-0091](0091-progress-hook-cap-and-split-constraints.md):** trần `PROGRESS.md` và hook về lại 8 192 byte (AUD-HAR-461).
- **Làm rõ:** [ADR-0043](0043-size-budget.md), [ADR-0050](0050-raise-dir-size-caps.md), [ADR-0072](0072-review-dir-caps-after-2x.md), [ADR-0083](0083-factory-lifecycle-flow.md), [ADR-0088](0088-docs-ledger-size-caps.md).

## Bối cảnh

Đo tại commit `3e0fff6d1ed7f43a511e2b8f507450ec7d6eb7c6` ngày 2026-11-21 cho thấy các file hướng dẫn nạp đầu phiên và nhóm thư mục đã chạm sát 99,6–100,0 % trần (`AGENTS.md` còn 1 B, `.claude/skills/optimize/SKILL.md` còn 2 B, `PROGRESS.md` còn 29 B, `.claude/hooks/` còn 489 B). Sau khi ADR-0088 cộng 1 MiB cho `docs/ops` và `docs/autopilot`, chủ repo yêu cầu nhân 5 (`5×`) toàn bộ giới hạn kích thước hiện tại để gỡ nghẽn cho các đợt nâng cấp tiếp theo.

| Nhóm đo | Mốc xét lại mới | Commit của phép đo | Trần trước ADR-0089 | Trần mới (5×) |
|---|---:|---|---:|---:|
| `scripts/*.py` và `scripts/xt_app/` | 2026-11-21 · 1 639 253 | `3e0fff6d1ed7f43a511e2b8f507450ec7d6eb7c6` | 1 760 431 | 8 802 155 |
| `.claude/hooks/` | 2026-11-21 · 1 417 480 | `3e0fff6d1ed7f43a511e2b8f507450ec7d6eb7c6` | 1 417 969 | 7 089 845 |
| `framework/11-autonomous-loop/` | 2026-11-21 · 336 675 | `3e0fff6d1ed7f43a511e2b8f507450ec7d6eb7c6` | 1 280 883 | 6 404 415 |
| `docs/ops/` | 2026-11-21 · 798 004 | `3e0fff6d1ed7f43a511e2b8f507450ec7d6eb7c6` | 1 858 690 | 9 293 450 |
| `docs/autopilot/` | 2026-11-21 · 352 327 | `3e0fff6d1ed7f43a511e2b8f507450ec7d6eb7c6` | 1 400 921 | 7 004 605 |

## Quyết định

1. Nhân 5 (`5×`) mọi trần file đơn trong `CAPS` của `tests/test_docs_budget.py` và `PROGRESS_MAX_BYTES` trong `scripts/xt.py` (`8 192` → `40 960` B, đồng bộ `utf8_head 40960` ở `.claude/hooks/session-start.sh`).
2. Nhân 5 (`5×`) mọi trần nhóm thư mục trong `DIR_CAPS` của `tests/test_docs_budget.py`.
3. Ghi mốc kích thước ngày `2026-11-21` trong `SIZE_MARKS` và nâng hệ số cảnh báo mốc của `double_mark_breach` từ `2×` lên `5×` (`MARK_FACTOR = 5`) để đồng bộ với trần mới.

## Hệ quả và đường lùi

- Các PR sửa lỗi, ghi quyết định và nâng cấp kiến trúc không còn bị chặn vì thiếu vài chục byte; cổng máy `DocsBudgetTest` và `progress-check` vẫn giữ ngưỡng cứng ở mức `5×`.
- Đường lùi: revert commit của ADR này để quay về hệ số cũ.
