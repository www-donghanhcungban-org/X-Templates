# Nâng trần eval — 29/11/2026

Mốc tích hợp là `main` tại `44ee1f8d`. D-649 áp dụng các hợp đồng của hồ sơ 28/11. Kiểm kê nhánh local và GitHub không tìm thấy mã nguồn có SHA `98b0e7e0` được hồ sơ cũ nhắc tới, nên kết quả cũ chỉ dùng để đối chiếu phạm vi.

| Lớp | Điều được kiểm | Cổng |
|---|---|---|
| Nghiệm thu | Đúng danh tính từng testcase và kết quả xanh; khóa legacy phải được amend | [SPEC acceptance identity](../specs/SPEC-acceptance-eval-identity.md) |
| Báo cáo eval | Cấu trúc, manifest theo case/lượt, nguồn bằng chứng được khai, freshness và ngưỡng độc lập | [Hợp đồng eval-report](../../framework/00-method/eval-report-contract.md) |
| Bytes artefact | Bằng chứng đúng digest, đọc có trần, khử lượt đọc lặp | [Hợp đồng eval-evidence](../../framework/00-method/eval-report-contract.md#7-cổng-mở-và-kiểm-bytes-artefact) |
| Kết quả trial | Tỷ lệ hoàn thành, tự hoàn thành, có lỗi và p95 trên danh sách người thử đã ghim | [Hợp đồng design-outcome](../../framework/00-method/design-outcome-contract.md) |

## Tài nguyên đo được

Trên CPython 3.15.2, so phép kiểm danh sách ở bản triển khai trung gian với phép kiểm tập hợp trong cùng tiến trình. Cả hai xử lý cùng dữ liệu trong bộ nhớ và trả kết quả giống hệt. Mỗi cỡ chạy năm cặp xen kẽ. Đo CPU bằng `process_time_ns` và đo riêng bộ nhớ cấp phát đỉnh bằng `tracemalloc`.

| Ca tổng hợp, một lượt/ca | CPU trung vị trước → sau | Bytes cấp phát đỉnh trước → sau |
|---:|---:|---:|
| 1.000 | 5,16 → 1,88 ms | 99.136 → 99.136 |
| 4.000 | 50,30 → 7,62 ms | 710.952 → 458.112 |
| 8.000 | 207,84 → 17,55 ms | 2.041.968 → 1.409.128 |

Schema loại cặp trùng. Cổng kiểm mỗi cặp thuộc miền policy và tổng số cặp bằng kích thước miền, qua đó tránh dựng thêm toàn bộ tích case × lượt. Tập ID bắt buộc dùng tra cứu theo hash. Kiểm hồi quy so tăng trưởng theo cỡ dữ liệu và giữ nguyên các điều kiện thất bại.

Các phép đo trên là fixture evaluator. Token, chi phí model, tỷ lệ thành công của agent và kết quả pilot người thật chưa có số đo trong đợt này. Không có phụ thuộc runtime mới hoặc thay đổi ruleset CI.

## Điều kiện cắt 3.37.0

`release-check --json` trên `main` tại `44ee1f8d` trả exit 1 và `NO-GO`. Hàng `verify` thiếu hồ sơ máy cho cây ứng viên ở checkout đó. Hàng `review_debt` ghi 169 tệp ngoài tài liệu cần rà từ mốc audit. `audit check --strict` vẫn exit 0 vì kiểm trạng thái các mục đã ghi trong sổ. [PLAN cắt bản](../autopilot/PLAN-upgrade-2026-11-27.md) còn giữ các điều kiện của T-5079.
