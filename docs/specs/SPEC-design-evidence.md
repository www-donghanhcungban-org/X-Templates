# SPEC-design-evidence — Kiểm hồ sơ thiết kế và thử tác vụ

| Trường | Giá trị |
|---|---|
| Phiên bản schema | 1 |
| Quyết định | D-584 |
| Kế hoạch | [`T-5014`, `T-5015`, `T-5017`](../autopilot/PLAN-harden-2026-11-24.md) |

## 1. Mục tiêu

Người chuẩn bị hồ sơ thiết kế có thể dùng một lệnh để biết phần nào còn thiếu, sai kiểu hoặc mâu thuẫn, từ lúc chọn phương án đến lúc thử tác vụ. Dữ liệu nhập lấy từ [brief](../../framework/templates/DESIGN-BRIEF.md), [bảng phương án](../../framework/templates/DESIGN-OPTIONS.md) và [biên bản thử](../../framework/templates/TASK-TRIAL.md). Bộ kiểm đọc hồ sơ đã ghi. Việc xác minh nguồn và kết quả pilot thật thuộc `T-5017`.

## 2. Hồ sơ JSON

Tệp UTF-8 có một object gốc và khoá duy nhất trong từng object. Kích thước theo giới hạn 2 MiB chung của `static-check`. Có thể bổ sung trường cho hồ sơ pilot rộng hơn. Bộ kiểm đọc các trường bắt buộc ở vị trí chỉ định dưới đây. Chuỗi bắt buộc phải còn nội dung sau khi bỏ khoảng trắng hai đầu.

| Trường | Kiểu và quy tắc |
|---|---|
| `schema` | Số nguyên `1` |
| `brief` | Object gồm `primary_user`, `task`, `device`, `long_data`, `empty_data`, `success_criteria`, tất cả là chuỗi |
| `options` | Mảng có ít nhất hai object với `id`, `approach`, `tradeoffs` là chuỗi. ID duy nhất trong mảng |
| `decision` | Object có `selected` là ID của một phương án và `reason` là chuỗi nêu lý do chọn |
| `trial` | Object với `status` và các trường tương ứng ở dưới |

Bộ kiểm so ID có phân biệt hoa thường sau khi bỏ khoảng trắng hai đầu. Mỗi tệp có phạm vi ID riêng. Dùng mã ẩn danh cho người thử.

### `trial.status = "not_tested"`

`reason` nêu lý do chưa thử và `next_step` ghi bước tiếp theo. Cả hai là chuỗi bắt buộc. `participants` và `summary` chỉ dùng với trạng thái `tested`.

### `trial.status = "tested"`

`participants` là mảng có ít nhất một object. Mỗi người thử có đủ năm trường.

| Trường | Kiểu và quy tắc |
|---|---|
| `id` | Chuỗi là mã ẩn danh duy nhất trong `participants` |
| `completed` | Boolean theo tiêu chí trong brief |
| `duration_seconds` | Số hữu hạn không âm, tính bằng giây, kể cả khi người thử dừng trước khi hoàn thành |
| `errors` | Số nguyên không âm đếm lỗi thao tác |
| `help_count` | Số nguyên không âm đếm số lần cần trợ giúp |

`summary` là object có hai số nguyên không âm. `participants` bằng số dòng trong mảng. `completed` bằng số dòng có `completed: true`. Ghi `0` khi giá trị đã đo là 0. Trường thiếu hoặc `null` làm kiểm tra thất bại.

## 3. Lệnh và kết quả

```sh
python3 scripts/xt.py static-check design-evidence DESIGN-EVIDENCE.json --json
python3 scripts/xt.py static-check design-evidence DESIGN-EVIDENCE.json --opt mode=pilot --json
```

Thông số `mode=draft` là mặc định và nhận cả hai trạng thái thử. `mode=pilot` yêu cầu có tệp và tất cả hồ sơ đều ở trạng thái `tested` với kết quả hợp lệ. Khi nhận thư mục, lệnh tìm đúng tên `DESIGN-EVIDENCE.json`. Đường dẫn tệp chỉ định trực tiếp có thể mang tên khác. Dùng đường dẫn tệp cụ thể cho cổng pilot.

| Mã | Khi trả về |
|---|---|
| Exit `0` | Tất cả hồ sơ được tìm thấy đều hợp lệ theo chế độ đã chọn. Bản nháp quét thư mục rỗng có `checked.files = 0` |
| Exit `1` · `DES000` | Tệp không đọc được, JSON sai, cấu trúc hoặc kiểu sai, giá trị ngoài giới hạn, ID trùng, lựa chọn lệch hoặc tổng lệch |
| Exit `1` · `DES001` | Hồ sơ ghi `not_tested` trong chế độ `pilot` |
| Exit `2` | Dùng sai lệnh, ví dụ `mode` lạ hoặc chế độ `pilot` không tìm thấy tệp |

`--json` dùng phong bì `schema`, `kind`, `checked`, `findings` của `static-check`. `checked.files` đếm tệp đã đưa vào kiểm. Các số `briefs`, `options`, `decisions`, `trials`, `participants`, `summaries` đếm object tương ứng mà bộ kiểm đã đọc và kiểm, kể cả object có trường sai. Phần tử mảng sai kiểu sinh phát hiện riêng. Hai số `participants` và `summaries` trong `checked` đều là 0 đối với hồ sơ `not_tested` chỉ có thông tin chờ thử.

## 4. Tiêu chí chấp nhận

| Given | When | Then |
|---|---|---|
| Brief đầy đủ, phương án và lựa chọn hợp lệ, thử có dữ liệu của từng người, tổng khớp | Chạy `mode=pilot` kể cả khi tệp có trường phụ | Exit `0`, `checked` đếm đúng các object được kiểm |
| Hồ sơ có `not_tested`, lý do và bước tiếp theo | Chạy ở `draft`, rồi `pilot` | `draft` exit `0`. `pilot` exit `1` và báo `DES001` |
| Kiểu container hoặc phần tử bắt buộc bị thay, số bị thiếu hoặc sai kiểu, thời gian vô hạn/âm, ID lặp, tổng lệch | Chạy bộ kiểm | Exit `1`, nêu trường sai và báo số mục còn đọc được |
| Thư mục chỉ chứa JSON khác hoặc chế độ gõ sai | Chạy `mode=pilot` hoặc truyền chế độ lạ | Exit `2` |

Gate của `T-5015` là `python3 -m unittest tests.test_check_design_evidence tests.test_static_check tests.test_static_check_shape`.
