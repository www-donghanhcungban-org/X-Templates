# ADR-0093: Thứ tự tách `guard.py` và cách nạp module anh em

- **Trạng thái:** Đã chấp nhận ngày 2026-11-23 (phiên chính tự duyệt, ADR-0008; D-542). Bổ sung [ADR-0090](0090-split-guard-and-xt-monoliths.md) và [ADR-0091](0091-progress-hook-cap-and-split-constraints.md); không thay chúng.
- **Trạng thái triển khai:** Chưa triển khai mã tách. Đã có công cụ đo `scripts/xt_guard_profile.py` (T-3984) và số đo ở [research/2026-11-23-guard-compile-cost.md](../../research/2026-11-23-guard-compile-cost.md). Lát mã là T-3987…T-3990 của [PLAN-guard-split-2026-11-22](../autopilot/PLAN-guard-split-2026-11-22.md).
- **Liên quan:** [ADR-0054](0054-fail-closed-unavailable-state-lock-and-guard-loader.md), [ADR-0018](0018-deny-dangerous-allow-rest.md), AUD-SEC-074, AUD-ARCH-007, AUD-ARCH-010.

## Bối cảnh

ADR-0091 đòi có số đo chi phí compile trước khi quyết tách guard. Số đo ngày 2026-11-23 (CPython 3.15.0b4, container phiên, chưa phải máy chuẩn; chi tiết và lệnh ở báo cáo nghiên cứu):

- `guard.py` 24 423 dòng, 1 379 538 B; compile trung vị 398,5 ms (10 lần) trong ≈ 0,55 s mỗi lệnh Bash của hook. Bộ nạp compile từ nguồn mỗi lần, không pyc (AUD-SEC-074).
- 463 họ hàm theo tiền tố, 240 họ chỉ một định nghĩa; họ lệnh cụ thể (`gh`, `git`, `xargs`, `push`, `sed`, `find`, `tar`) chiếm 17,9 % dòng định nghĩa. Nếu chỉ họ đó nạp lười thì tiết kiệm tối đa ≈ 71 ms trên 399 ms compile; thực tế thấp hơn vì `git` bị 25 họ khác gọi, `gh` 13 họ.
- Tám họ nhỏ (`is`, `normalize`, `dequote`, `positionals`, `strip`, `split`, `flag`, `no`) tổng ≈ 290 dòng nhưng nối với phần lớn tệp; 277 hằng được ≥ 2 họ dùng. Họ theo tiền tố là trùng tên, không phải module gắn kết: họ `split` gồm tám hàm khác mục đích rải từ dòng 2052 đến 20897. Nên chúng chỉ là ứng viên theo tên, ranh giới tách phải lấy từ đồ thị gọi ở mức hàm.

## Quyết định

1. **Thứ tự tách:** (a) lõi dùng chung sang một module riêng; (b) họ từ xa (`git`, `gh`, `push` và những gì chỉ chúng dùng); (c) các họ còn lại, từng cụm một. Lõi đi trước để module sau nhập từ lõi mà không nhập vòng với `guard.py`. **"Lõi dùng chung" và ranh giới mỗi cụm xác định bằng đồ thị gọi ở mức hàm**, cụ thể bao đóng bắc cầu của nhóm hàm cần tách (hàm nó cần, hằng nó dùng) và các hàm ngoài nhóm gọi vào nó; không xác định bằng tiền tố tên. Công cụ đo cần mở rộng để in được bao đóng đó (T-3995) trước khi tách mã. Tên module cụ thể và danh sách hàm chốt ở từng PR theo kết quả đó.
2. **Mục tiêu là bảo trì** (độ trễ đọc, xung đột PR song song, kiểm kiểu): ADR-0090 đã nêu. Giảm thời gian hook chỉ là lợi ích phụ, tối đa vài chục ms; không dùng nó làm lý do nới an toàn.
3. **Cách nạp module anh em:** `guard.py` nạp chúng bằng một hàm nạp riêng, compile từ nguồn giống `PY_LOADER`/`py_run`: đọc tệp byte, `compile`, `exec` trong module mới, đăng ký ở `sys.modules`; không dùng `import` thường. Lý do: `-B` chỉ tắt ghi bytecode, `import` thường vẫn đọc pyc hợp lệ đặt sẵn trong `__pycache__` (AUD-SEC-074). Danh sách tên module là hằng cố định trong `guard.py`, đường dẫn tính từ thư mục của `guard.py`; thiếu hoặc lỗi nạp một module thì ngoại lệ lan lên và guard lỗi nạp, nên Bash bị chặn (ADR-0054). Ba bộ nạp hiện có (`_lib.sh`, `PY_LOADER`, `xt_adapter.load_guard`) giữ nguyên vì chúng chỉ nạp `guard.py`; hàm nạp mới nằm trong `guard.py` nên cả ba tự hưởng.
4. **Tự bảo vệ:** module guard mới nằm trong tập tệp hàng rào như `guard.py` (chặn sửa và ghi qua Bash, `pre-edit-guard`, baseline `guard_fence_baseline.json`), `install.py` đồng bộ tệp companion dưới `.claude/hooks/`, `typecheck` trong `xt.yaml` và coverage phủ chúng. Đây là task T-3988, làm trước khi tách mã.
5. **Đường nhanh (quyết ngay lệnh hiển nhiên an toàn, mọi ca không chắc rơi về guard đầy đủ) không thuộc ADR này.** Nó là hướng thật duy nhất giảm mạnh thời gian mỗi lệnh, nhưng đụng bất biến an toàn (đường nhanh phải là tập con an toàn của guard đầy đủ); cần ADR riêng với bằng chứng parity trên toàn bộ corpus 4 019 ca guard của `autonomy-bench` và fuzz.
6. **Điều kiện mỗi PR tách** giữ như ADR-0090 mục 3 (một cụm nhỏ, không đổi hành vi, qua `autonomy-bench`, `test_guard_fuzz`, `test_green_shell`, `test_green_gh`, so quyết định thô base ↔ nhánh ở cả hai chính sách là tập cha không lọt) và dẫn mục "Ràng buộc" của ADR-0091; thêm review độc lập ở head trước khi merge.

## Hệ quả và đường lùi

- Lát đầu (T-3987/T-3988) không đổi hành vi hàng rào: chỉ thêm bộ nạp và bảo vệ module. Mỗi lát sau là một PR độc lập, revert được.
- Tách xong chưa chắc nhanh hơn đáng kể; ai cần độ trễ thấp phải đi qua ADR đường nhanh.
- Đường lùi: đóng PLAN từ T-3987, giữ `guard.py` một tệp; công cụ đo và báo cáo giữ lại.

## Phương án đã xét

- **Tách ngay kèm đường nhanh:** bị loại ở lát đầu vì rủi ro an toàn và chưa có bằng chứng parity.
- **Không tách:** bị loại vì ADR-0090 đã chấp nhận mục tiêu bảo trì và `guard.py` đã gần trần nhóm.
- **`import` thường cho module anh em:** bị loại vì đọc pyc đặt sẵn (AUD-SEC-074).
