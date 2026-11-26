# ADR-0108: Guard nhận `xt_design`, dòng khai "Duyệt thiết kế" không nới được khi sổ đã có

- **Trạng thái:** Đã chấp nhận ngày 2026-11-26 (D-622).
- **Trạng thái triển khai:** đã triển khai cùng PR với ADR này — guard (`.claude/hooks/guard.py`, luật AUD-SEC-498, sửa tại chỗ, số dòng không đổi), `scripts/xt_design.py` (`declared`), test `tests/test_stage_agent_approval.py`, `tests/test_design_gate.py`, corpus `tests/fixtures/autonomy/guard.json`.
- **Liên quan:** [ADR-0106](0106-client-design-approval-gate.md) (thay hai giới hạn đã biết của nó), [ADR-0058](0058-product-stages-machine-lock.md) (sổ giai đoạn, phạm vi D-015), [ADR-0069](0069-agent-stage-approval.md); luật guard AUD-SEC-498 (D-377).

## Bối cảnh

Reviewer vòng 2 của PR #844 (ADR-0106) tái hiện hai lỗ, đã ghi ở ADR-0106 §Giới hạn đã biết:

1. Luật AUD-SEC-498 chặn script trình thông dịch (`-c`, stdin, heredoc, here-string) nạp `xt` trong tiến trình rồi gọi hàm duyệt, nhưng chỉ nhận tên `xt`. Script `import xt_design as d; d.update(xt, '.', lambda led: d.approve(…))` ghi lời duyệt thiết kế mà guard không thấy lệnh con `stage approve --design`.
2. `declared()` chỉ đọc dòng khai ở `PROJECT.md` của cây làm việc. Sau `stage design-submit`, sửa dòng thành `không` (chưa commit) hay xoá `PROJECT.md` là mở khoá task `(ui: yes)`.

## Quyết định

1. **Guard nhận `xt_design` như `xt`** (luật AUD-SEC-498, sửa tại chỗ, `guard.py` giữ nguyên số dòng, không đổi `LINE_CAPS`):
   - `import xt_design`, `import scripts.xt_design`, `from xt_design import …`, `from scripts import xt_design` tính là nạp mô-đun; đi cùng tên/chữ rủi ro (`approve`, `main`, `stage`, biến môi trường, truy cập động…) → chặn (`STAGE_APPROVE`).
   - Tên/đường `xt_design`, `scripts.xt_design`, `scripts/xt_design.py` cho `run_path`, `import_module`, `spec_from_file_location`, `-m runpy` → chặn.
   - Luật chữ (script không phải Python hợp lệ) nhận `import … xt_design`; câu lý do nhắc cả hai mô-đun.
   - Chữ `sign` trong danh sách tên rủi ro không còn khớp khi là phần của chính tên `xt_design`: script chỉ đọc (`import xt, xt_design as d; print(d.problem(xt, …))`) vẫn qua, cùng tinh thần thư viện đọc `xt.parse_plan`. Đây là chỗ duy nhất luật hẹp hơn luật cũ: script vừa `import xt` vừa nhắc tên `xt_design` mà không có tên rủi ro nào khác, trước bị chặn, nay qua.
2. **Dòng khai một chiều khi sổ đã có:** `docs/autopilot/DESIGN.json` tồn tại (kể cả hỏng, rỗng, không đọc được hay symlink gãy) → dự án là khách bất kể `PROJECT.md` (dòng `không`, không có dòng khai, tệp bị xoá), kèm ghi chú "sổ `DESIGN.json` đã có — dòng khai không nới được" trong lý do khoá và `design-check`. Sổ chưa có → hành vi cũ nguyên vẹn. Đã `approved` thì task giao diện vẫn mở như cũ (khoá chỉ giữ khi `status` khác `approved`). D-622 ghi "sổ có lịch sử hay hỏng"; mã dùng "sổ tồn tại" vì sổ do `xt.py stage` tạo luôn có lịch sử, và sổ rỗng tạo tay là cách hiểu chặt hơn.

## Phương án đã xét

- **Đòi `PROJECT.md` ở nhánh chính của remote cũng khai `khách`** (đọc `git show origin/main:PROJECT.md`, như khoá ADR-0069): mạnh hơn nhưng phụ thuộc remote, tăng bề mặt lỗi (offline, clone nông, worktree) và phải hoà hai nguồn. Loại; xét lại khi có số liệu.
- **Không sửa mã, giữ giới hạn đã ghi ở ADR-0106:** để hở hai lỗ đã tái hiện. Loại.

## Hệ quả

- Tốt: dòng khai nay một chiều sau khi đã trình bản thiết kế; guard nhận cả `xt` lẫn `xt_design`. Dự án không khai và chưa từng trình không đổi gì.
- Xấu: dự án lỡ trình rồi muốn bỏ cổng phải xoá sổ `DESIGN.json` — việc của người, như mọi sửa tay sổ bằng chứng. Luật guard hẹp hơn luật cũ ở đúng một dạng nêu ở Quyết định 1.
- Giới hạn có từ trước (phạm vi D-015, không phải của ADR này): guard là lớp chặn nhầm cho agent làm đúng quy trình, không cách ly agent cố ý vượt rào — script ghi ra tệp rồi chạy và bỏ biến môi trường agent, đường dẫn hay tên ghép lúc chạy (AUD-SEC-161), `find -exec`, tên viết thường, worktree vẫn là giới hạn đã biết.
