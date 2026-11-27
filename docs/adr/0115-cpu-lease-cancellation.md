# ADR-0115: Giữ lease trong khi nhóm lệnh dừng

- **Trạng thái:** Đã chấp nhận ngày 2026-11-27 (D-635, D-636).
- **Tiếp nối:** [ADR-0113](0113-resource-lease-admission.md), T-5082 và hậu kiểm #865.

## Quyết định

Khi khay nhận một workload trên Linux có procfs, hỗ trợ child subreaper và supervisor không có terminal điều khiển, lệnh chạy trong nhóm tiến trình riêng. Supervisor chuyển SIGINT, SIGTERM và SIGHUP tới nhóm. Sau khi có tín hiệu chuyển tiếp, supervisor chờ các tiến trình còn sống của nhóm trước khi xoá lease và trả mã thoát của lệnh chính. Supervisor dùng Linux child subreaper để nhận hậu duệ mất cha, thu hồi tiến trình đã thoát trong lúc chờ lệnh chính và chờ hậu duệ cùng nhóm bằng `waitpid`. Kiểm nhóm còn con trước khi gửi tín hiệu để tránh dùng nhầm mã nhóm đã được cấp lại. Khay tắt, nền tảng thiếu procfs hoặc child subreaper, hay phiên có terminal điều khiển tiếp tục chuyển tín hiệu tới con trực tiếp. Phiên có terminal giữ `/dev/tty` và job control.

`XT_CPU_SLOTS` vẫn là trần số việc, còn `XT_JOBS` là trần worker do mỗi workload khai. Ca 14 CPU có 12 CPU cấp được cho lịch mặc định 8 + 4. Khi cổng tải mở, ba tác vụ khai `XT_JOBS=4` có thể nhận ba nhóm rời nhau, mỗi nhóm bốn CPU. Hạ mặc định của việc đơn lẻ từ tám còn bốn worker cần số đo độ trễ và throughput trên workload WSL2 trước khi xem xét.

## Kiểm chứng và giới hạn

Ca hồi quy dùng shell và tiến trình Python nền. Shell và tiến trình Python nhận SIGTERM đã thoát, nhưng tiến trình kế tục của handler vẫn giữ được lease trong lúc dọn. Sau khi tiến trình kế tục thoát, supervisor trả nguyên tín hiệu của shell và xoá lease. Với lệnh có terminal điều khiển, SIGTERM gửi riêng tới supervisor vẫn có thể bỏ sót cháu. Supervisor không quản lý nhánh có tiến trình đổi nhóm, kể cả khi một hậu duệ của nhánh đó còn ở nhóm cũ. SIGKILL gửi tới supervisor vẫn phụ thuộc vào vòng đời workload. Khi cần tự tạo phiên bằng `setsid`, dùng `setsid --wait` để giữ mã thoát hoặc tắt khay. Cơ chế subreaper đặt SIGCHLD về mặc định khi chạy lệnh. Khi tiến trình trong nhóm bỏ qua tín hiệu, lease giữ tới khi tiến trình đó thoát.

Đường lùi là hoàn tác lát sửa hoặc dùng `XT_CPU_SHARE=off` cho tác vụ cần cơ chế cũ.
