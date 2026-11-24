# ADR-0101: Báo phạm vi đã kiểm của static-check

- **Trạng thái:** Đã chấp nhận ngày 2026-11-24 (D-574).
- **Bổ sung:** [ADR-0099](0099-static-check-kinds.md).

## Bối cảnh

Kết quả sạch trước đây có thể xuất hiện khi `components` hoặc `statements` là chuỗi. Bộ kiểm bỏ qua toàn bộ nội dung của trường rồi trả cùng danh sách phát hiện như khi đã kiểm thành công. Người dùng cần biết trường nào hỏng và bao nhiêu mục thực sự được kiểm.

## Quyết định

- JSON giữ `schema: 1` và thêm `checked`. Mọi loại báo `files`, số lượt tệp được chọn để kiểm sau bước lọc, gồm cả tệp đọc hoặc phân tích thất bại. Thư mục không có tệp phù hợp cho kết quả 0.
- `sbom` đếm `components` theo số object đã được kiểm theo các luật thành phần trong cây `components` của tài liệu, kể cả thành phần lồng nhau. Thành phần mô tả công cụ tạo BOM hoặc sản phẩm gốc trong metadata không thuộc mẫu số tỷ lệ license. `vex` đếm số object statement đã được kiểm. Một object có phát hiện vẫn được tính.
- Mỗi container sai kiểu hoặc phần tử sai kiểu tại những trường đã hỗ trợ sinh `SBM000` hoặc `VEX000` với đường dẫn trường và chỉ số từ 0. Tiếp tục với các phần tử hợp lệ. Giữ các quy tắc hiện có cho danh sách dependency rỗng (`SBM007`) và danh sách sản phẩm rỗng (`VEX002`).
- `run_report` trả cả số đếm lẫn phát hiện. Loại cần đếm mục cung cấp `check_report` để ghi cả hai trong cùng lượt phân tích. `run` và `check` tiếp tục trả danh sách phát hiện.

## Hệ quả và phương án đã xét

Đọc tệp lần nữa để đếm có thể quan sát nội dung khác với lượt kiểm. Thay kiểu trả về của `run` sẽ buộc mã gọi cũ phải đổi. Việc thêm trường báo cáo giữ mã thoát và các trường JSON cũ, không cần phụ thuộc mới. Kiểm toàn bộ schema theo từng phiên bản là việc riêng.

## Nguồn

- [CycloneDX 1.7 JSON Reference](https://cyclonedx.org/docs/1.7/json/) — đối chiếu ngày 2026-11-24.
- [OpenVEX Specification](https://github.com/openvex/spec/blob/main/OPENVEX-SPEC.md) — đối chiếu ngày 2026-11-24.
