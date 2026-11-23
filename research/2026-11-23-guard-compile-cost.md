---
title: Chi phí compile và cấu trúc họ hàm của guard.py (số đo cho việc tách guard)
kind: research
updated: 2026-11-23
---

# Chi phí compile và cấu trúc họ hàm của `guard.py`, 2026-11-23

> Mục đích: số đo cho [ADR-0091](../docs/adr/0091-progress-hook-cap-and-split-constraints.md) ("đo chi phí compile trước khi
> quyết tách guard", T-3984/T-3985) và cho quyết định ranh giới ở [ADR-0090](../docs/adr/0090-split-guard-and-xt-monoliths.md).
> Nguồn: `scripts/xt_guard_profile.py` (chỉ đọc) chạy trên `.claude/hooks/guard.py` ở `main` `b47cdf08`; thời gian hook
> đo bằng chính `pre-bash-guard.sh`. Mục nào chưa đo được ghi **chưa biết**.

## Môi trường đo

- Container phiên làm việc, CPython 3.15.0b4 (bản beta), không phải máy chuẩn; thời gian có thể lệch so với máy dev hay CI.
- Bộ nạp hook compile từ nguồn mỗi lần, không dùng pyc (AUD-SEC-074), nên chi phí compile trả lại ở mỗi lệnh Bash.

## Số đo

| Đại lượng | Giá trị | Lệnh |
|---|---|---|
| Kích thước | 24 423 dòng, 1 379 538 B, 1 436 định nghĩa cấp tệp | `python3 scripts/xt_guard_profile.py` |
| Compile (10 lần) | trung vị 398,5 ms; nhỏ nhất 357,0 ms; lớn nhất 444,1 ms | `python3 scripts/xt_guard_profile.py --repeat 10` |
| Compile (5 lần, lần đo trước) | trung vị 385,6 ms; nhỏ nhất 379,3 ms; lớn nhất 468,4 ms | `python3 scripts/xt_guard_profile.py --repeat 5` |
| Hook Bash đầu-cuối | 0,51–0,59 s mỗi lệnh (5 lần với `ls`: 0,508–0,576 s; `git push --force` bị chặn: 0,593 s) | `bash .claude/hooks/pre-bash-guard.sh` với payload JSON |
| So với lần đo cũ | 0,21–0,28 s ở 510 KB (AUD-PERF-013) | trong sổ audit |

Compile chiếm khoảng 70–75 % thời gian hook đo được (≈ 0,40 s trong ≈ 0,55 s). Phần còn lại là khởi động Python và phân tích lệnh.
**Chưa biết:** tách riêng phần quyết định với khởi động trong hook; số đo ở máy chuẩn.

## Cấu trúc họ hàm (họ = tiền tố tên sau khi bỏ gạch dưới đầu)

- Chỉ 16 088 trong 24 423 dòng nằm trong định nghĩa hàm hoặc lớp cấp tệp; khoảng 8 300 dòng còn lại là câu lệnh cấp tệp, bảng hằng, biểu thức chính quy, chú thích.
- 463 họ, trong đó 240 họ chỉ có một định nghĩa. Họ lớn nhất (`gh`) chỉ chiếm 6,3 % dòng định nghĩa; 5 họ lớn nhất 17,3 %; 20 họ lớn nhất 33,1 %; 50 họ lớn nhất 51,3 %. Tiền tố quá mịn để ánh xạ thẳng sang ba lớp của ADR-0090.
- Họ lệnh cụ thể (`gh`, `git`, `xargs`, `push`, `sed`, `find`, `tar`): 2 880 dòng = 17,9 % dòng định nghĩa.
- Họ bị nhiều họ khác gọi nhất (ứng viên lõi dùng chung): `is` (46 họ gọi tới, 60 dòng), `normalize` (41, 8 dòng), `dequote` (26, 8 dòng), `positionals` (24, 22 dòng), `strip` (20, 82 dòng), `split` (20, 79 dòng), `flag` (15, 19 dòng). Tám họ nhỏ này tổng khoảng 290 dòng nhưng nối với phần lớn tệp.
- Họ lệnh cụ thể cũng bị gọi từ nhiều nơi: `git` từ 25 họ, `gh` từ 13 họ, `xargs`, `sed` từ 5 họ mỗi họ. Đây là phần rối nhất khi tách.
- Hằng dùng chung nhiều họ: 277 hằng được ≥ 2 họ dùng; nhiều nhất `INTERP_RE` (20 họ), `SHELL_KEYWORDS` (19), `SHELLS` (18), `ENV_ASSIGN_RE` (11), `DECLARE_CMDS` (10).
- **Họ theo tiền tố là trùng tên, chưa phải module gắn kết.** Ví dụ họ `split` gồm `_split_free` (dòng 2052), `_split_why` (5322), `_split_trigger`, `_split_name`, `_split_view` (5437), `split_commands` (7917), `_split_words` (7954) và `_split_args` (20897): tám hàm khác mục đích rải trên gần 19 000 dòng (đọc bằng Grep ngày 2026-11-23). Vì vậy các "họ lõi dùng chung" ở trên là ứng viên theo tên; ranh giới tách phải lấy từ đồ thị gọi ở mức hàm (bao đóng bắc cầu), điều công cụ hiện chưa in.
- Giới hạn của công cụ: bảng cạnh và hằng cắt ở `--top 1000` (cạnh đạt trần 1 000, nên tổng số cạnh thật lớn hơn); cạnh gọi xấp xỉ theo tên, tên cục bộ trùng tên định nghĩa cấp tệp bị tính nhầm.

## Hệ quả cho quyết định tách

1. **Lợi ích hiệu năng tối đa khi tách theo họ lệnh bị chặn trên.** Nếu compile tỉ lệ theo dòng định nghĩa và chỉ họ lệnh cụ thể ở trên nạp lười, mức tiết kiệm tối đa khoảng 71 ms trên 399 ms (≈ 18 %), tương đương ≈ 13 % thời gian hook. Con số thực tế thấp hơn vì các họ đó bị nhiều họ khác gọi. **Giả định chưa kiểm:** compile tỉ lệ tuyến tính theo dòng định nghĩa; phần cấp tệp (≈ 34 % số dòng, nhiều hằng) vẫn compile ở mọi lệnh.
2. **Tách chỉ để bảo trì vẫn có giá trị, nhưng cần lõi dùng chung trước.** Tách `git`/`gh` thành module riêng mà không tách lõi dùng chung (nhóm `is`, `normalize`, `dequote`, `positionals`, `strip`, `split`, `flag`) tạo nhập vòng với `guard.py`. Thứ tự hợp lý: lõi dùng chung → họ lệnh từ xa (`git`, `gh`, `push`) → các họ còn lại, với "lõi dùng chung" xác định bằng bao đóng phụ thuộc ở mức hàm của nhóm cần tách (công cụ cần mở rộng, T-3995), không bằng tiền tố tên.
3. **Muốn giảm mạnh thời gian mỗi lệnh phải đổi kiến trúc, không chỉ chia tệp.** Hướng được đưa ra xét: một đường nhanh nhỏ quyết định ngay các lệnh hiển nhiên an toàn, mọi ca không chắc rơi về guard đầy đủ. Hướng này đụng bất biến an toàn (đường nhanh phải là tập con an toàn của guard đầy đủ), nên cần chứng minh bằng so quyết định thô trên toàn bộ corpus của `autonomy-bench` (4 019 ca guard) và fuzz, không đưa vào lát đầu.
4. **Ràng buộc từ ADR-0091** giữ nguyên: bộ nạp compile từ nguồn, thiếu module sau cài dở thì Bash bị chặn (ADR-0054), `perf trial` chạy một blob `xt.py` (tách `xt.py` ngoài phạm vi ở đây).

## Cách tái hiện

```bash
python3 scripts/xt_guard_profile.py --repeat 10
python3 scripts/xt_guard_profile.py --repeat 10 --top 1000 --json
```
