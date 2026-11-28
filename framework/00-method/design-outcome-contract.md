---
title: Hợp đồng cổng kết quả thử tác vụ
kind: method
updated: 2026-11-28
---

# Hợp đồng cổng kết quả thử tác vụ

`static-check design-outcome` chấm kết quả thử tác vụ theo manifest và ngưỡng bên nghiệm thu đã duyệt. Nó dùng cùng hồ sơ `DESIGN-EVIDENCE.json` với `design-evidence mode=pilot`, nhưng yêu cầu cả **chất lượng kết quả**. Validator cũ tiếp tục chỉ kiểm cấu trúc; hồ sơ ghi mọi người thất bại vẫn là hồ sơ hợp lệ.

## 1. CLI và ranh giới

```bash
python3 scripts/xt.py static-check design-outcome DESIGN-EVIDENCE.json --json \
  --opt policy=DESIGN-OUTCOME-POLICY.json \
  --opt revision=<SHA-Git-đầy-đủ> --opt at=2026-11-28T15:00:00Z
```

Trong dự án đã cài, thay `scripts/xt.py` bằng `.xtemplates/scripts/xt.py`. Cần đúng một hồ sơ và đủ ba tuỳ chọn; không nhận `ignore` hoặc trường lạ. Exit 0 = các quan sát được cung cấp đạt policy, 1 = có finding, 2 = dùng sai. `DSO000` báo cấu trúc; `DSO001` báo ngưỡng hoặc provenance không khớp; hồ sơ chưa thử còn có thể báo `DES001` từ validator pilot.

Policy phải được kiểm soát độc lập với người tạo kết quả. Chốt manifest/ngưỡng trước pilot; sau khi thu nhận hồ sơ, bên nghiệm thu ghim digest và thời điểm quan sát từ nguồn có thể truy lại. Không tự thay ngưỡng hoặc bớt người thất bại để đạt. Giá trị `revision` và `at` truyền từ cổng xét ứng viên, không chép từ policy.

Digest chỉ nối đúng bytes hồ sơ đã duyệt. Cổng không xác thực danh tính người thử, không chứng minh họ đã dùng sản phẩm và không tự tạo pilot. Nhận định về quần thể cần thiết kế mẫu và khoảng bất định riêng; ngưỡng trên hai người không chứng minh tỷ lệ thành công ngoài thực tế.

## 2. Policy schema 1

Object JSON có đúng các trường bên dưới. JSON trùng khoá, NaN/Infinity, boolean thay số, ID rỗng/trùng hoặc khoá lạ đều thất bại. Tệp UTF-8 thường tối đa 2 MiB; manifest và danh sách participant tối đa 100.000 phần tử, giới hạn bytes vẫn áp dụng trước.

| Trường | Ý nghĩa |
|---|---|
| `schema`, `kind`, `policy_id` | Số nguyên `1`, chuỗi `design-outcome-policy`, ID chính sách khác rỗng. |
| `revision` | SHA Git 40 hoặc 64 ký tự hex thường, khớp revision độc lập ở CLI. |
| `evidence_sha256` | SHA-256 của **bytes UTF-8 gốc** của hồ sơ; đổi khoảng trắng cũng đổi digest. |
| `observed_at`, `max_age_seconds` | Thời điểm quan sát theo [cùng quy tắc RFC 3339 của eval-report](eval-report-contract.md#2-báo-cáo-schema-1). Tuổi tối đa 1–31.536.000 giây. Thời điểm tương lai hoặc quá hạn tại `at` bị từ chối. |
| `participant_ids` | Toàn bộ ID người thử ẩn danh đã chốt, không rỗng, không trùng; phải khớp chính xác tập ID trong hồ sơ. |
| `required_completed_ids` | Tập con của manifest phải hoàn thành; thất bại ở đây không được bù bằng tỷ lệ chung. |
| `min_completion_rate` | Số hoàn thành / **toàn bộ người thử**, ngưỡng hữu hạn trong [0, 1]. |
| `min_unassisted_rate` | Số hoàn thành với `help_count=0` / **toàn bộ người thử**, trong [0, 1]. Người không hoàn thành dù không được giúp không được tính là đạt. |
| `max_error_rate` | Số người có `errors>0` / **toàn bộ người thử**, trong [0, 1]; không phải tổng số lỗi chia số người. |
| `max_p95_duration_seconds` | Trần giây dương hữu hạn; p95 nearest-rank trên mọi trial, **kể cả trial thất bại**. Vị trí là `ceil(0,95 × n)` trong dãy thời gian tăng dần. |

Hồ sơ phải đạt schema pilot và có số tổng khớp từng người. Cổng mới dùng đúng bộ trường ở mọi cấp:

| Object | Các trường được nhận |
|---|---|
| Hồ sơ gốc | `schema`, `brief`, `options`, `decision`, `trial` |
| `brief` | `primary_user`, `task`, `device`, `long_data`, `empty_data`, `success_criteria` |
| Mỗi phần tử `options` | `id`, `approach`, `tradeoffs` |
| `decision` | `selected`, `reason` |
| `trial` | `status`, `participants`, `summary`; `status` phải là `tested` |
| Mỗi phần tử `trial.participants` | `id`, `completed`, `duration_seconds`, `errors`, `help_count` |
| `trial.summary` | `participants`, `completed` |

Metadata bổ sung như `source` ở hồ sơ gốc có thể được validator `design-evidence` chấp nhận, nhưng bị `design-outcome` từ chối. Đây là hợp đồng chặt hơn của cổng mới, không thay đổi validator cũ. Metadata ngoài hợp đồng cần được lưu riêng; không chèn vào hồ sơ đã ghim digest. Tập thiếu/thừa/trùng người, summary nói sai hoặc trial chưa thử không được quality-pass.

`checked` báo số hồ sơ hợp lệ, tổng người, hoàn thành, hoàn thành không giúp, người gặp lỗi và `quality_gates`. Chỉ `quality_gates=1` khi tất cả điều kiện đạt. Không gắn điểm 10/10 vào kết quả này.

## 3. Cách nghiệm thu evaluator

Trong checkout nguồn:

```bash
python3 -m unittest tests.test_check_design_outcome tests.test_static_check_shape
python3 -m unittest tests.test_eval_surface_parity
```

Ca đối chứng có pilot hoàn thành và policy biên hợp lệ. Ca đối kháng có 0 người hoàn thành, thiếu người, thay ID, ngưỡng tự nới trong hồ sơ, sai summary, hỗ trợ người dùng bị ẩn, lỗi nhiều ở cùng người, p95 bỏ trial thất bại, digest/SHA cũ và policy hết hạn. Tests dựng cả hồ sơ và digest một cách tất định, nhãn fixture không thay số đo người thật.

Nhà quy trình thiết kế là [design/UX](../06-design-ux/README.md), hồ sơ thu thập ở [biên bản thử tác vụ](../templates/TASK-TRIAL.md); quy tắc bằng chứng chung ở [evidence-and-sources](evidence-and-sources.md), các mức trưởng thành eval ở [evaluation](../13-ai-engineering/evaluation.md).
