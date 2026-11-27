# ADR-0112: Khay CPU dùng chung theo máy và cổng nhận việc theo áp lực CPU

- **Trạng thái:** Đề xuất ngày 2026-11-27 (D-629, D-630), chờ phiên chính duyệt cùng PR của T-5082. Số 0111 đã giữ cho ADR của T-5069 (PLAN-upgrade-2026-11-27) nên ADR này lấy 0112.
- **Trạng thái triển khai:** T-5082 — `scripts/xt_cpu_share.py`, `dev-task.sh` (`gate`/`gate-fast` trong khay, `test_jobs()`), `test_fast` của `xt.yaml`, chú thích ở mẫu `xt.yaml`, ba danh sách mô-đun, `LOOP-ORCH-025`.
- **Liên quan:** [ADR-0061](0061-adaptive-agent-topology.md) (số agent theo loại việc), [ADR-0076](0076-guard-positive-grammar-gate.md) (lệnh `xt.yaml` trong tập con guard đọc chắc), D-367/D-369 (`XT_JOBS`, pytest-xdist), BASE-GATE-005.

## Bối cảnh

Nhiều phiên hoặc agent cùng chạy cổng commit, cổng đầy đủ và test song song trên một máy. Mỗi tiến trình tự lấy số nhân của máy (`nproc`, `-n auto`, `xargs -P nproc`), nên tải lên 12–13 trên máy 14 nhân. Khi đó hook, guard và phiên tương tác chạy chậm. Chủ dự án chỉ đạo: tham số suy ra từ số nhân, không dùng con số cố định, áp cho cả khung lẫn dự án đích (D-629). Thêm cổng theo tải thật, ngưỡng mặc định 85 % (D-630).

## Quyết định

1. **Số nhân hiệu dụng** `n` = số nhân trong affinity của tiến trình (WSL và container có thể đã giới hạn), cắt theo quota cgroup v2 (`cpu.max`) nếu có.
2. **Công thức**, mọi tham số là hàm của `n` và ghi đè được:
   - `reserve = ceil(n/8)` (0 khi `n = 1`, tối đa `n − 1`), ghi đè bằng `XT_CPU_RESERVE`.
   - `slots = max(1, n // 4)`, ghi đè bằng `XT_CPU_SLOTS`.
   - `usable = n − reserve`.
   - Mỗi việc nhận `clamp(usable // active, min(2, usable), ceil(2·usable/3))`, với `active` là số việc đang đăng ký, tính cả việc mới.

   | n | reserve | slots | usable | 1 việc | 2 việc | 3 việc |
   |---|---|---|---|---|---|---|
   | 1 | 0 | 1 | 1 | 1 | — | — |
   | 2 | 1 | 1 | 1 | 1 | — | — |
   | 4 | 1 | 1 | 3 | 2 | — | — |
   | 14 | 2 | 3 | 12 | 8 | 6 | 4 |
   | 64 | 8 | 16 | 56 | 38 | 28 | 18 |
3. **Khay** là thư mục `$XDG_CACHE_HOME/xt-cpu` (mặc định `~/.cache/xt-cpu`). Mỗi việc ghi một tệp `job-<pid>.json` (pid, thời điểm khởi động tiến trình, các nhân được ghim, số tiến trình). Mọi lần đọc và ghi diễn ra dưới `flock`; tiến trình chết thì hệ tự nhả khoá. Tệp của PID đã chết, của PID bị tái dùng (thời điểm khởi động khác), của zombie, hoặc tệp hỏng đều bị xoá ở lần đọc kế. Vì vậy việc crash không để lại khoá mồ côi.
4. **Nhận việc**, theo thứ tự:
   - Việc của PR đầu hàng (`--head` hoặc `XT_CPU_HEAD=1`) luôn được nhận: bỏ qua cả giới hạn số việc lẫn cổng tải, vì để việc đầu hàng đợi đứng chờ phá mục đích của hàng đợi. Việc này vẫn được đăng ký và tính vào `active`, nên các việc khác nhận phần nhỏ hơn. Hệ quả: tối đa `slots + 1` việc cùng lúc.
   - Việc của PR đầu hàng đang chờ thì việc khác nhường.
   - Khay đầy (`active ≥ slots`) thì chờ.
   - Khay trống thì luôn nhận.
   - Không đo được áp lực thì bỏ qua cổng tải; còn lại theo cổng tải ở mục 5.

   Áp lực chỉ được đo khi kết quả phụ thuộc vào nó (khay có việc, còn chỗ, không phải việc đầu hàng, không có việc đầu hàng đang chờ), vì đo mức dùng CPU tốn 0,5 s. Bị từ chối thì chờ lùi dần (1 s, nhân đôi, trần 30 s), không có hạn thời gian (BASE-GATE-005).
5. **Cổng tải — cách quy về "85 % CPU".** Áp lực là giá trị **lớn nhất** của ba đại lượng, mỗi đại lượng quy về thang [0, 1] với 1 là bão hoà (quyết định của phiên chính ngày 2026-11-27 sau số đo ở mục Hiệu chỉnh):
   - **Mức dùng CPU thật** từ dòng `cpu` của `/proc/stat`, đọc hai lần cách nhau 0,5 s: `(Δtổng − Δ(idle + iowait)) / Δtổng`. 0,5 s là khoảng lấy mẫu, không phải hạn thời gian của việc. Thiếu tệp, tệp hỏng hoặc không có nhịp nào trôi qua thì bỏ đại lượng này.
   - **`loadavg` 1 phút chia `n`.** Giá trị 1,0 là mỗi nhân trung bình một tác vụ chạy được.
   - **PSI** `/proc/pressure/cpu` dòng `some`, trường `avg10`, chia 100: phần thời gian trong 10 s có ít nhất một tác vụ chờ nhân. Giá trị ngoài [0, 100] hoặc tệp hỏng thì bỏ.
   - Đại lượng nào thiếu thì bỏ đại lượng đó; thiếu cả ba thì bỏ qua cổng.

   Cổng đóng khi áp lực vượt ngưỡng cao (`XT_CPU_HIGH`, mặc định 85), mở lại khi xuống dưới ngưỡng thấp (`XT_CPU_LOW`, mặc định bằng ngưỡng cao trừ 15 điểm, tức 70; không bao giờ cao hơn ngưỡng cao). Trạng thái đóng/mở lưu trong khay (`gate-closed`) để mọi tiến trình dùng chung độ trễ; lần không đo thì giữ nguyên trạng thái.

   Vì sao lấy giá trị lớn nhất: mức dùng CPU khớp nghĩa "85 % CPU" của D-630 và phản ứng nhanh (0,5 s). `loadavg`/`n` thấy cả tác vụ đang chờ nhân. PSI chỉ tăng cao khi quá tải nặng (mục Hiệu chỉnh) nên một mình không đủ, nhưng vẫn giữ để bắt tranh nhân mà hai đại lượng kia làm mượt mất.
6. **Áp lên việc.** `run` đặt `XT_JOBS` bằng phần nhận được khi người dùng chưa đặt (người đặt thắng, kể cả giá trị rác, để dev-task xử lý như cũ). `run` cũng đặt `XT_CPU_SHARE_ID`, ghim việc vào các nhân ngoài phần dành bằng `os.sched_setaffinity` (khi hệ có và `reserve > 0`, ưu tiên nhân ít việc khác dùng; con cháu thừa kế), và hạ `nice` 5 cho việc không phải PR đầu hàng. Khi không ai khai việc đầu hàng, mọi việc bằng nhau ở `nice` 5, thấp hơn phiên tương tác. `run` trả đúng mã thoát của lệnh; lệnh chết vì tín hiệu thì `run` tự gửi cùng tín hiệu cho chính nó.
7. **Lồng.** Việc chạy bên trong một việc đã đăng ký thì chạy thẳng, không đăng ký lại, nên không thể tự chờ chính mình. Việc được coi là lồng khi có `XT_CPU_SHARE_ID`, hoặc khi một tổ tiên trong `/proc` đã đăng ký (test dựng môi trường sạch vẫn được nhận ra). `jobs` trong việc lồng in số nhân được cấp.
8. **Chỗ nối.**
   - `dev-task.sh gate` và `gate-fast` chạy lại chính script dưới `run` (cổng commit, `loop record`).
   - **Ở CI khay và cổng mặc định tắt**: biến `CI` được đặt (GitHub Actions đặt `CI=true`; giá trị `false`/`0` coi như không đặt) thì xử lý như `XT_CPU_SHARE=off`, vì runner dành riêng cho một việc; `XT_CPU_SHARE=on` bật lại. Trên CI, `test_jobs()` vẫn trả `auto` và `test_fast` vẫn dùng `ceil(nproc/2)` như trước. `framework/templates/ci.yml` không đổi.
   - `test_jobs()` lấy phần của khay khi `XT_JOBS` không đặt.
   - `test_fast` của `xt.yaml` lấy `-P` từ `jobs --fallback ceil(nproc/2)`.
   - Lệnh `test` dùng `nproc`, nên tự thấy số nhân đã ghim.
9. **Fail-open về luồng, không về kết quả.** `XT_CPU_SHARE=off` (hoặc CI không bật lại), mô-đun vắng, python không chạy được, thư mục cache không ghi được, hoặc thiếu `fcntl`: lệnh chạy như trước khi có khay (`exec`). Khay không bao giờ đổi mã thoát của lệnh được bọc.

## Hiệu chỉnh (máy 14 nhân, WSL2, 2026-11-27)

Cách đo: lấy mẫu `/proc/pressure/cpu` (`some avg10`) và `loadavg`/`n` mỗi 2 s.

| Tải | PSI `some avg10` (%) | `loadavg`/`n` |
|---|---|---|
| Toàn bộ test (`dev-task.sh test`, `xargs -P 14`, coverage), 220 s, 110 mẫu | min 1,5 · trung vị 5,3 · p90 9,2 · max 12,1 | tới 1,05 |
| Cùng lúc, 17 tiến trình test (quá tải nhẹ), 20 s | 11,3–16,3 | 1,10–1,12 |
| Hai việc qua khay (8 + 6 tiến trình đốt CPU, ghim trong 12 nhân) | ~5 sau 6 s | — |
| 28 tiến trình đốt CPU không ghim (2×`n`), 24 s | tăng dần, trung vị 61,5 · p90 79,7 · max 85,6 | tới 1,42 |

Kết luận đo: trên máy này, cả khi `loadavg`/`n` ≈ 1 (mọi nhân đều bận), PSI `some avg10` vẫn chỉ quanh 5–16 %; PSI chỉ lên 80–86 % khi quá tải gấp đôi số nhân. Dùng riêng PSI với ngưỡng 85 thì cổng gần như không bao giờ đóng ở mức một cổng đầy đủ, trái ý định "85 % CPU" của D-630. Vì vậy áp lực lấy giá trị lớn nhất của ba đại lượng (mục 5). Số đo theo công thức mới, lúc máy đang chạy toàn bộ test của một phiên khác (tải ngoài khay): trước khi có việc nào, mức dùng CPU 0,99, `loadavg`/`n` 1,14, PSI 0,09, áp lực 1,14. Việc A vào ngay (khay trống). Việc B và C chờ cổng tải (áp lực ghi lại 1,20–1,41) và chỉ được nhận khi khay trống. Việc của PR đầu hàng vào sau khoảng 2 s dù cổng đang đóng. Tức là cổng đóng đúng khi máy bận vì tải ngoài khung, điều mà riêng PSI (0,09–0,31) không thấy. Khi máy rảnh, trước lần đổi công thức: hai việc qua khay dùng nhân 2–13 ở mức 86–99 %, còn nhân dành riêng 0/1 chỉ bận 10 % và 3 %.

## Phương án đã xét

- **Con số cố định cho máy 14 nhân** (dành 2, 3 việc, mỗi việc 4): loại vì hỏng khi đổi máy (D-629).
- **Chỉ cgroup/`systemd-run` ở máy người dùng:** loại vì nằm ngoài kho, dự án đích không nhận được.
- **Giữ nguyên** (mỗi tiến trình tự lấy số nhân): loại vì máy vẫn bị tranh nhân.
- **Chỉ đếm khay, không có cổng tải:** loại theo D-630, vì khay không thấy tải ngoài khung (trình duyệt, build khác).
- **Ngưỡng 80 % hoặc 90 %:** chủ dự án chọn 85 % làm điểm xuất phát (D-630).
- **Ghim nhân bằng lệnh `taskset`:** dùng `os.sched_setaffinity` thay thế. Cùng cơ chế nhân của hệ điều hành, nhưng không cần gói `util-linux`.

## Hệ quả

- Máy 14 nhân: một việc một mình dùng 8 nhân (`test_fast` trước đây dùng `ceil(14/2) = 7`). Hai việc dùng 8 và 6 nhân, hợp ghim nằm trong 12 nhân dùng được, 2 nhân dành riêng không bị việc nặng chạm.
- Máy 4 nhân: mỗi lúc một việc, dùng 2 nhân. Việc thứ hai chờ, trừ việc của PR đầu hàng.
- Việc của PR đầu hàng vượt giới hạn số việc: tối đa `slots + 1` việc cùng lúc, và lúc đó tổng phần chia có thể vượt `usable` nhiều hơn.
- Cổng commit tốn thêm khoảng hai lần khởi động python (`probe` rồi `run`), cộng 0,5 s đo CPU khi đã có việc khác trong khay.
- CI của khung và dự án đích không đổi hành vi (khay mặc định tắt khi có `CI`).
- `test_fast` tôn trọng `XT_JOBS` người đặt (trước đây bỏ qua).
- Dự án đích nhận mô-đun qua `install.py`. Mẫu `xt.yaml` chỉ thêm chú thích, không thêm khoá.

## Giới hạn đã biết

- PSI (10 s) và `loadavg` (1 phút) là trung bình trượt nên đo trễ: cổng có thể còn đóng một lúc sau khi tải đã giảm. Khay đếm vẫn cần để chặn tức thì.
- `loadavg` của Linux đếm cả tác vụ ngủ không ngắt được (thường là chờ I/O), nên máy chờ đĩa hoặc mạng có thể đóng cổng dù CPU rảnh. Vì lấy giá trị lớn nhất, sai lệch này nghiêng về phía đóng cổng (chậm, không hỏng).
- Mức dùng CPU từ `/proc/stat` là của cả máy, không riêng các nhân trong affinity; trong container bị giới hạn nhân, con số có thể lệch.
- `CI` được người dùng đặt ở máy dev (hiếm) thì khay tắt ở máy đó.
- Khay chỉ ràng buộc lệnh khởi chạy qua mô-đun. Phần chia theo số việc, không theo lượng việc thực sự cần.
- Việc đến sau nhận phần nhỏ hơn, nhưng việc đang chạy không bị co lại. Vì vậy tổng số tiến trình có thể vượt `usable` (8 + 6 trên 12 nhân), dù nhân bị ghim vẫn nằm trong phần dùng được.
- Việc bị `SIGKILL` thì lệnh con mồ côi vẫn chạy mà không còn được đếm.
- Chờ khay không có hạn trong mã, nhưng hook commit có hạn riêng (1200 s ở settings của khung): chờ quá hạn đó thì hook đỏ.
- Không có `/proc` (macOS) thì chỉ nhận ra việc lồng qua biến môi trường.
- Chưa có cách tự xác định PR đầu hàng: người gọi phải đặt `XT_CPU_HEAD=1`.

## Đường lùi

Đặt `XT_CPU_SHARE=off` (máy hoặc dự án). Muốn bỏ hẳn: gỡ mô-đun, hai chỗ gọi ở `dev-task.sh` và dòng `test_fast`, về `ceil(nproc/2)`. Đổi ngưỡng mặc định sau khi đo thì ghi D-NNN mới.
