# ADR-0108: Guard nhận `xt_design`, dòng khai "Duyệt thiết kế" không nới được khi sổ đã có

- **Trạng thái:** Đã chấp nhận ngày 2026-11-26 (D-622).
- **Trạng thái triển khai:** đã triển khai cùng PR với ADR này — guard (`.claude/hooks/guard.py`, luật AUD-SEC-498, sửa tại chỗ, số dòng không đổi), `scripts/xt_design.py` (`declared`), test `tests/test_stage_agent_approval.py`, `tests/test_design_gate.py`, corpus `tests/fixtures/autonomy/guard.json`.
- **Liên quan:** [ADR-0106](0106-client-design-approval-gate.md) (thay hai giới hạn đã biết của nó), [ADR-0058](0058-product-stages-machine-lock.md) (sổ giai đoạn, phạm vi D-015), [ADR-0069](0069-agent-stage-approval.md); luật guard AUD-SEC-498 (D-377).

## Bối cảnh

Reviewer vòng 2 của PR #844 (ADR-0106) tái hiện hai lỗ, đã ghi ở ADR-0106 §Giới hạn đã biết:

1. Luật AUD-SEC-498 chặn script trình thông dịch (`-c`, stdin, heredoc, here-string) nạp `xt` trong tiến trình rồi gọi hàm duyệt, nhưng chỉ nhận tên `xt`. Script `import xt_design as d; d.update(xt, '.', lambda led: d.approve(…))` ghi lời duyệt thiết kế mà guard không thấy lệnh con `stage approve --design`.
2. `declared()` chỉ đọc dòng khai ở `PROJECT.md` của cây làm việc. Sau `stage design-submit`, sửa dòng thành `không` (chưa commit) hay xoá `PROJECT.md` là mở khoá task `(ui: yes)`.

## Quyết định

1. **Guard nhận `xt_design`, chặn mọi lần nạp nó trong tiến trình** (luật AUD-SEC-498, sửa tại chỗ, `guard.py` giữ nguyên số dòng, không đổi `LINE_CAPS`):
   - `import xt_design`, `import scripts.xt_design`, `from xt_design import …`, `from scripts import xt_design` tính là nạp mô-đun. Tên `xt_design` chứa chữ rủi ro `sign`, và tên mô-đun nguồn của `from … import` nay cũng được xét như một tên. Vì vậy **mọi lần nạp `xt_design` trong tiến trình trình thông dịch đều bị chặn** (`STAGE_APPROVE`), kể cả script chỉ đọc. Đọc sổ thì dùng `xt.py stage design-check --json`; câu lý do của guard nêu lệnh này.
   - Tên/đường `xt_design`, `scripts.xt_design`, `scripts/xt_design.py` cho `run_path`, `import_module`, `spec_from_file_location`, `-m runpy` → chặn.
   - Luật chữ (script không phải Python hợp lệ) nhận `import … xt_design`; câu lý do nhắc cả hai mô-đun.
   - Không có ngoại lệ cho script đọc `xt_design`. Lý do: hàm ghi `update` và các hằng `STATUSES`/`REPLAY`/`LEDGER` không chứa chữ rủi ro. Review PR #849 đã tái hiện chuyện này: nếu cho qua script đọc thì `d.update(xt, Path('.'), lambda l: {**l, 'status': d.STATUSES[2], …})` ghi được lời duyệt trong phiên agent (rc 0, sổ thành `approved`). So vi sai với guard trước PR (corpus `guard.json`, mọi chuỗi nhắc `xt`/`sign` trong `tests/`, chế độ mặc định và `XT_GUARD_POLICY=strict`) cho thấy không có dạng nào bị nới. Thư viện đọc của `xt` (`xt.parse_plan`, `from xt import parse_plan`) vẫn qua như trước.
2. **Dòng khai một chiều khi sổ đã có:** `docs/autopilot/DESIGN.json` tồn tại (kể cả hỏng, rỗng, không đọc được hay symlink gãy) → dự án là khách bất kể `PROJECT.md` (dòng `không`, không có dòng khai, tệp bị xoá), kèm ghi chú "sổ `DESIGN.json` đã có — dòng khai không nới được" trong lý do khoá và `design-check`. Sổ chưa có → hành vi cũ nguyên vẹn. Đã `approved` thì task giao diện vẫn mở như cũ (khoá chỉ giữ khi `status` khác `approved`). Mã làm đúng như D-622 ghi: "sổ tồn tại, kể cả hỏng, rỗng".

## Phương án đã xét

- **Đòi `PROJECT.md` ở nhánh chính của remote cũng khai `khách`** (đọc `git show origin/main:PROJECT.md`, như khoá ADR-0069): mạnh hơn nhưng phụ thuộc remote, tăng bề mặt lỗi (offline, clone nông, worktree) và phải hoà hai nguồn. Loại; xét lại khi có số liệu.
- **Cho qua script chỉ đọc `xt_design` (bỏ khớp `sign` trong tên mô-đun), như thư viện đọc `xt.parse_plan`:** bản đầu của PR #849 làm vậy. Loại vì phân tích tĩnh không tách được đọc với ghi khi hàm ghi và hằng trạng thái không có chữ rủi ro (Quyết định 1).
- **Không sửa mã, giữ giới hạn đã ghi ở ADR-0106:** để hở hai lỗ đã tái hiện. Loại.

## Hệ quả

- Tốt: dòng khai nay một chiều sau khi đã trình bản thiết kế; guard nhận cả `xt` lẫn `xt_design`. Dự án không khai và chưa từng trình không đổi gì.
- Xấu: dự án lỡ trình rồi muốn bỏ cổng phải xoá sổ `DESIGN.json` — việc của người, như mọi sửa tay sổ bằng chứng. Script chỉ đọc sổ bằng thư viện `xt_design` cũng bị chặn; dùng `xt.py stage design-check --json`.

### Giới hạn đã biết

- **Trình nhầm ở dự án khai `không` thì khoá vĩnh viễn:** `design-submit` ở dự án khai `không` mà chưa có sổ sẽ tạo sổ. Sau đó `design-reopen` không gỡ được, vì sổ đã tồn tại nên dự án coi là `khách`. Agent không gỡ được, chỉ người (xoá sổ). Việc sau: từ chối `design-submit` khi dự án chưa khai `khách` và chưa có sổ.
- **Giới hạn guard có từ trước** (phạm vi D-015; AUD-SEC-090/161/988; không phải của ADR này): guard là lớp chặn nhầm cho agent làm đúng quy trình, không cách ly được agent cố ý vượt rào. Các dạng vẫn lọt: script ghi ra tệp rồi chạy, bỏ biến môi trường agent, đường dẫn hay tên ghép lúc chạy (AUD-SEC-161), `find -exec`, alias hàm nạp (`from runpy import run_path as rp`), tệp `.pyc` thật trong `__pycache__`, `import XT` viết hoa, `git stash push -u -- <sổ>`, `ln -sfn`, `shutil.rmtree('docs/autopilot')`, và worktree mới khi sổ chưa commit.
