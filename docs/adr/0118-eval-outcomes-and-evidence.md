# ADR-0118: Danh tính nghiệm thu và chính sách eval độc lập

- **Trạng thái:** Đã chấp nhận (D-649, 2026-11-29)

## Bối cảnh

Số ca trùng nhau không chứng minh cùng bộ nghiệm thu đã chạy. Báo cáo hợp lệ về cấu trúc cũng có thể chứa kết quả thất bại. Mỗi lớp cần bằng chứng gắn với đúng đối tượng trước khi có thể dùng để ký phát hành.

## Quyết định

- Khóa bộ nghiệm thu theo file và cặp classname/name. Đọc được khóa cũ và yêu cầu quy trình amend có lịch sử trước khi release chấp nhận.
- Chạy `eval-report` với policy độc lập khi cần kiểm chất lượng. Chế độ validate kiểm schema và phép đếm. Gate đối chiếu danh tính, ca bắt buộc, các lượt và kết quả.
- Chạy `eval-evidence` khi cần xác minh bytes. Đọc mỗi digest một lần và áp giới hạn mỗi blob, toàn kho và số digest. Report và policy dùng chung snapshot đã đọc.
- Chạy `design-outcome` riêng trên hồ sơ trial và manifest đã ghim. Mẫu số giữ toàn bộ người thử. P95 dùng nearest-rank.

## Phương án đã cân nhắc

Chỉ lưu số đếm và kết quả tổng hợp dễ triển khai, nhưng không phát hiện ca bị thay thế. Chạy thêm model hoặc bộ đo toàn bộ ở mọi PR tăng chi phí và không giải quyết chuyện policy phụ thuộc vào chính báo cáo. Bộ kiểm mới dùng thư viện chuẩn và fixture tổng hợp để kiểm hành vi của evaluator. Chất lượng model, chi phí token và pilot đích cần số đo riêng theo phạm vi.

## Tương thích và đường lùi

Release với khóa legacy cần amend đúng quy trình đã review. Trước khi đổi phiên bản công cụ hoặc khóa, giữ bản sao có thể đối chiếu. Khi cần quay lại runtime cũ, dùng bản sao khóa tương ứng với runtime đó. Giữ các yêu cầu CI hiện hành và tách riêng phép đo mô hình khi có ngân sách và môi trường phù hợp.
