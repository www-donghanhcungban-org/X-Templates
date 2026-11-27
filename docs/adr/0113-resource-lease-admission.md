# ADR-0113: Cấp phát lease CPU và RAM ước lượng

- **Trạng thái:** Đã chấp nhận ngày 2026-11-27 (D-631).
- **Trạng thái triển khai:** bước đầu của X-Resource Manager trong T-5082.
- **Tiếp nối:** [ADR-0112](0112-machine-cpu-share-tray.md), D-629 và D-630. Các quy tắc nhận việc dưới đây cập nhật chính sách tương ứng của ADR-0112.

## Quyết định

Đếm worker còn giữ chỗ dưới cùng khóa ghi lease. Cách chia cũ cho việc đầu 8 và việc sau 6 trên máy 14 CPU có phần dùng được là 12. Việc đang chạy không co lại. Với lease, hai lần cấp tương ứng là 8 và tối đa 4, với hai tập affinity rời nhau khi hệ điều hành hỗ trợ.

`XT_JOBS` là nhu cầu tối đa. Việc của PR đầu hàng có thể qua cổng áp lực và dùng thêm một suất hàng đợi khi còn ngân sách. `XT_RESOURCE_WAIT_TIMEOUT` đặt thời gian chờ tính theo giây nếu cần. Khi không đặt, áp dụng cách chờ của ADR-0112. Sau khi khay được bật, lỗi đọc lease hay lỗi quyền thư mục làm lệnh dừng với mã 2. Cờ `XT_CPU_SHARE=off` phục hồi đường chạy trước đây. CI vẫn dùng đường đó mặc định.

Đọc affinity và quota CPU cgroup v2 tại mount chuẩn, xét các nhóm cha nhìn thấy được. Giữ quota phân số khi báo cáo và làm tròn xuống khi tính worker. Quota dưới một CPU vẫn chạy được một worker dưới hạn mức OS.

`XT_RESOURCE_RAM_PER_WORKER` bật ước lượng RAM, đơn vị MiB. Dùng cùng cấu hình trong các workload cần phối hợp RAM. Headroom lấy số nhỏ nhất của `MemAvailable` và các giới hạn RAM cgroup v2 đọc được. `XT_RESOURCE_RAM_RESERVE` mặc định 512 MiB khi bật ước lượng. Trừ toàn bộ RAM đã giữ chỗ vì chưa đo được RAM từng cây tiến trình. Cách tính này có thể cho ít worker hơn khi các lease đã dùng một phần RAM. Hết headroom thì chờ, thiếu nguồn đo thì báo lỗi. Công cụ và hệ điều hành vẫn có thể dùng nhiều RAM hơn dự toán.

`dev-task.sh` nhận ngân sách cho các tác vụ nặng. Core dùng ngân sách cho full test và shard. `gate-par` chia một worker cho lint và một worker cho typecheck, phần còn lại cho build rồi test. Dưới ba worker, ba nhóm chạy lần lượt với thứ tự báo lỗi cũ. Lệnh tùy chỉnh nhận biến môi trường theo hợp đồng mẫu.

## Bằng chứng

Trên môi trường Linux kiểm thử có 9 CPU khả dụng, ngân sách là 7. Cùng kịch bản hai gate giữ lease đồng thời: bản PR #865 cấp 5 + 3 và ghim trùng một CPU. Sau thay đổi, khi một gate chạy trên khung và một gate chạy qua bộ cài của dự án thử, cấp 5 + 2, affinity không trùng và cả hai trả 0. Ca mô phỏng 14 CPU ghim mức 8 + 4. Đây là thử điều phối worker, chưa phải số đo tốc độ hay RAM trên WSL2 14 CPU / 12 GB.

## Giới hạn của lần triển khai

`slots` và `XT_CPU_SLOTS` chỉ là trần trên của số việc nặng, không bảo đảm đạt (D-633). Việc đầu lấy `ceil(2·usable/3)`, việc sau lấy phần còn lại, nên mặc định tối đa 2 việc nặng cùng lúc; việc thứ ba chỉ vào khi còn ngân sách. Việc đầu hàng được ưu tiên nhưng vẫn chờ khi hết ngân sách. Mã giữ nguyên để không đổi hành vi đã đo; nợ 🟠 AUD-HAR-581 theo dõi việc quyết định có cấp việc đầu tối đa `usable // slots` hay không.

Khay dùng đường dẫn cache hiện tại theo người dùng. Chỉ chia sẻ trong một miền mà các bản cài cùng nhìn thấy tiến trình và hệ thống tệp. Bản trước ADR này có thể cấp chồng nếu còn khởi chạy chung. Nên kết thúc các lượt chạy bản cũ trước khi bật bản mới. Giá trị RAM ước lượng cần được đo trên workload trước khi áp dụng rộng.

Việc dọn sau `SIGKILL` vẫn theo PID của supervisor. Chưa chứng minh thu hồi an toàn khi cây con sống tiếp. Mount cgroup không chuẩn, cgroup v1, Windows native, cân bằng theo áp lực I/O và single-flight commit nằm ngoài lần triển khai này.
