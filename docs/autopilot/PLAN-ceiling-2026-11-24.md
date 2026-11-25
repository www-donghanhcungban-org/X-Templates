# PLAN X-Templates 2026-11-24 — nâng trần sau báo cáo đánh giá ngoài (bằng chứng, số đo, UI/UX)

> Duyệt: D-573 (kế thừa quyết định D-571 chưa merge của nhánh; giữ nguyên D-571/D-572 đã có trên `main`) · Chủ dự án yêu cầu "phân tích đánh giá lại nhận định này, lên kế hoạch nâng trần hoàn thiện dự án", sau đó tiếp quản nhánh và merge · Căn cứ: [đối chiếu báo cáo](../../research/2026-11-24-external-review-reassessment.md) — các phát hiện đã tái hiện ở `b82e369`, rà lại kế hoạch trên `7a1cf1d`

## Tóm tắt
- Thứ tự: bằng chứng đúng → ranh giới thực thi → số đo thật → UI/UX có pilot → lan truyền và nợ lõi. Pilot chạy trên bộ kiểm báo sạch sai hoặc sổ thiếu sự kiện thì số đo không dùng được, nên hai đợt đầu đi trước.
- Mảng UI/UX không thêm luật MUST. Việc là nối cổng có sẵn vào starter và sản phẩm, thêm đường thiết kế (brief, phương án, lý do chọn) và thử tác vụ với người thật.
- Mỗi task "nối luồng" có Gate đi qua lệnh thật trong repo tạm; không nhận Gate chỉ đưa dữ liệu giả vào bộ tính (bài học `T-4009`).
- Trạng thái: PR #786 duyệt kế hoạch; triển khai và bằng chứng được theo dõi tại [PLAN-harden](PLAN-harden-2026-11-24.md), D-574/D-575. Tệp kiểm thử/bộ kiểm trong Gate là đầu ra phải tạo; không coi lệnh dự kiến là bằng chứng đã chạy.
- Không làm: đổi cấu hình tự chủ (L3, review optional, agent ký) — báo cáo không yêu cầu; thêm người duyệt mọi PR; design system lớn trước khi có một luồng đạt.

## Ngân sách
- Số vòng: mặc định `--single-session` mỗi đợt · Chi phí ngoài phiên: 0 cho đợt 1–3 và 5; đợt 4 cần môi trường production của dự án đích · Timeout Gate: 1200 giây · Mỗi task một PR (`LOOP-DESIGN-029`).

## Việc của người (không chặn các task tự động của đợt 1–3)

| Việc | Chặn task | Ghi chú |
|---|---|---|
| Áp ruleset tag `v*` live và cấp danh tính phát hành | `T-4007` ở PLAN-improve, `T-5020` | Lệnh qua `xt.py admin-plan --script`; quyền admin repo. Chưa có quyền thì defer `T-5020`, vẫn làm `T-5008` |
| Cấp `XT_STEWARD_TOKEN` | `T-5018` | RUNBOOK-PR-STEWARD §1 |
| Mời 3–5 người đúng vai trò thử tác vụ; cấp môi trường production và khoá của Hotel Manager | `T-5017` | Mẫu nhỏ, nghiên cứu hình thành |

## Mốc "đã nâng trần" (đo được)

| Mốc | Điều kiện |
|---|---|
| Bằng chứng | Mọi loại `static-check` đỏ hoặc không kết luận khi container sai kiểu; kết quả kèm số mục đã kiểm |
| Số đo | Test tích hợp diễn tập đủ 9 đường ghi bằng lệnh thật; pilot chỉ ghi sự kiện thực, báo rõ nguồn đã nối và `no_events`/`window_open`; báo cáo có tỷ lệ bao phủ, chi phí gồm lượt đỏ |
| Ranh giới | Ruleset tag live có biên bản diễn tập; adapter production chạy với allowlist khai rõ |
| UI/UX | Starter xanh với ma trận viewport, bàn phím, axe, contrast trong CI mặc định; một pilot có brief, phương án, số thử tác vụ, receipt production và rollback |
| Lõi | `xt.py` và `guard.py` không tăng dòng; một module guard tách có parity |

## Thực thi

Hai mươi task `T-5001`…`T-5020` giữ nguyên ID, nội dung và Gate ở [PLAN-harden-2026-11-24](PLAN-harden-2026-11-24.md). D-575 chuyển danh sách máy đọc sang một nhà duy nhất để không cấp trùng ID; lịch sử kế hoạch gốc được giữ trong PR #786. Trạng thái, phụ thuộc và tick sau `loop record` chỉ cập nhật ở kế hoạch thực thi đó.
