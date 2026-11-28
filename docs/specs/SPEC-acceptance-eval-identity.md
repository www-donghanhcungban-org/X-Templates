# SPEC — Danh tính testcase trong nghiệm thu

| Thuộc tính | Giá trị |
|---|---|
| Trạng thái | Approved |
| Quyết định | D-649, [ADR-0118](../adr/0118-eval-outcomes-and-evidence.md) |
| Phạm vi | `xt_acceptance.py`, sổ ACCEPTANCE và report JUnit |

## Vấn đề và kết quả

Số lượng ca theo file chưa đủ chứng minh completeness: chạy A hai lần hoặc thay B bằng C vẫn có thể đạt số hai. Khóa mới phải lưu danh tính ca từ baseline có chạy lệnh thật; release phải so tập danh tính với tập đã khóa.

Mỗi row khóa mới/amend có `testcases`: object file → danh sách cặp `[classname, name]`. File đã được quy về phạm vi khóa; classname có thể rỗng khi `file` đủ xác định, `name` phải rõ và khác rỗng. Khóa cũ không có manifest được đọc để báo `legacy_locks`/`identity_binding`; release từ chối cho tới amend tường minh, không suy manifest từ số ca.

## Tiêu chí nghiệm thu

- AC-01: Given bộ test thật có hai ca khác nhau, When lock rồi triển khai sửa đúng, Then release chỉ đạt khi cả hai danh tính đã khóa có kết quả đạt.
- AC-02: Given cùng số ca, When bỏ B và nhân đôi A hoặc đổi B thành C, Then parser/release thất bại.
- AC-03: Given test tham số khác tên hoặc cùng tên ở lớp khác, When report có danh tính duy nhất và đúng manifest, Then không bị chặn oan.
- AC-04: Given ca skip/error/fail, tên trống, attribution mơ hồ hoặc trạng thái XML mâu thuẫn, Then không được dùng để bù số ca cần chạy.
- AC-05: Given sổ cũ thiếu `testcases`, When kiểm cấu trúc, Then đọc và báo rõ legacy; When release, Then FAIL với hướng amend có quyết định/reviewer. Xóa field khỏi khóa mới cũng không làm release xanh.
- AC-06: Given có quyết định sửa khóa và reviewer độc lập, When `acceptance amend` chạy lại baseline, Then ghi manifest mới cùng lịch sử, không tự sửa khóa khi chạy check.
- AC-07: Given report mới bị thay bytes hoặc bộ test/lệnh lệch khóa, Then các bảo đảm digest/freshness/source hiện hữu vẫn từ chối.

Lệnh kiểm trong checkout nguồn: `python3 -m unittest tests.test_acceptance_lock`.

## Tập định dạng JUnit được hỗ trợ

Parser nhận root `testsuite` hoặc `testsuites`, các suite/testcase lồng theo cấu trúc được kiểm, kết quả `failure`, `error`, `skipped` và metadata `properties`/`property`, `system-out`, `system-err`. XML có namespace, phần tử không được hỗ trợ hoặc phần tử đặt sai vị trí bị từ chối; không nhúng testcase vào metadata để bù ca thiếu. Thuộc tính `status`/`result` không nhận dạng được hoặc mâu thuẫn với phần tử kết quả cũng bị từ chối.

Mỗi report giới hạn 5 MiB và độ sâu suite 100 cấp. Xuất JUnit với phần tóm tắt cần thiết, đồng thời lưu log chi tiết riêng nếu bộ test sinh nhiều đầu ra.

Các counter `tests`, `failures`, `errors`, `skipped` ở suite là tùy chọn; khi có, chúng phải là số nguyên không âm và khớp tổng tính từ testcase bên dưới. Không dùng counter tự khai thay cho testcase thực. Mọi testcase phải có tên khác rỗng và quy được về đúng một file thuộc phạm vi khóa.

Reporter hiện hữu có namespace hoặc phần tử mở rộng của một dialect JUnit khác có thể cần adapter sang tập định dạng này. Thay đổi tương thích gồm cả cách đọc report, ngoài việc bổ sung manifest danh tính trong sổ; không tự coi mọi XML mang nhãn JUnit đều được hỗ trợ.

## Giới hạn

Tập testcase đúng không chứng minh assertion đủ mạnh. Comment chứa AC/S-ID vẫn chỉ là truy vết tĩnh; no-op, seeded defect và độ phủ AC→outcome cần oracle/mutation theo dự án. Tests chạy mã thật để kiểm pipeline nghiệm thu nhưng không tự tuyên bố mọi dự án đích đã chạy acceptance.

## Nâng khóa cũ

Khi phiên bản chứa thay đổi được đưa vào dự án có khóa cũ: xem `acceptance check`, ghi quyết định theo workflow đang dùng, rồi dùng `acceptance amend --help` để chọn khóa và reviewer độc lập; giữ nguồn baseline và lịch sử. Không thêm `testcases` bằng tay, không xóa khóa, không bỏ hàng acceptance trong release. Phạm vi đợt này chỉ sửa framework; chưa nâng/cài lại bất kỳ dự án đích nào.

Runtime cũ dùng exact-key validator sẽ từ chối row có `testcases`. Sau amend, giữ phiên bản công cụ hỗ trợ manifest; downgrade công cụ không phải đường lùi tương thích của sổ mới. Giữ bản sao và lịch sử theo quy trình nâng phiên bản, không tự xóa manifest để dùng lại gate cũ.
