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
| Compile (10 lần, lượt 1) | trung vị 398,5 ms; nhỏ nhất 357,0 ms; lớn nhất 444,1 ms | `python3 scripts/xt_guard_profile.py --repeat 10` |
| Compile (10 lần, lượt 2 chạy lại) | trung vị 393,4 ms; nhỏ nhất 358,3 ms; lớn nhất 415,4 ms | như trên |
| Compile (5 lần, lần đo trước) | trung vị 385,6 ms; nhỏ nhất 379,3 ms; lớn nhất 468,4 ms | `python3 scripts/xt_guard_profile.py --repeat 5` |
| Compile (reviewer độc lập chạy lại, cùng container) | trung vị 426,6 ms; hook 0,537–0,679 s | như trên |
| Hook Bash đầu-cuối | 0,51–0,59 s mỗi lệnh (5 lần với `ls`: 0,508–0,576 s; `git push --force` bị chặn: 0,593 s) | `bash .claude/hooks/pre-bash-guard.sh` với payload JSON |
| So với lần đo cũ | 0,21–0,28 s ở 510 KB (AUD-PERF-013) | trong sổ audit |

Compile chiếm khoảng 70–75 % thời gian hook đo được (≈ 0,40 s trong ≈ 0,55 s; reviewer đo lại ra cùng tỉ lệ). Phần còn lại gồm khởi động Python
(`python3 -I -B -c pass` đo được 0,019–0,024 s), chạy thân module (guard có hơn 500 dòng `NAME = re.compile(…)` cấp tệp thực thi ở mỗi lần nạp) và phân tích lệnh.
**Chưa biết:** thời gian thực thi thân module và thời gian quyết định tách riêng (luật không cho chạy `guard.py` bằng script tự do); số đo ở máy chuẩn.

## Cấu trúc họ hàm (họ = tiền tố tên sau khi bỏ gạch dưới đầu)

- Chỉ 16 088 trong 24 423 dòng nằm trong định nghĩa hàm hoặc lớp cấp tệp; khoảng 8 300 dòng còn lại là câu lệnh cấp tệp, bảng hằng, biểu thức chính quy, chú thích.
- 463 họ, trong đó 240 họ chỉ có một định nghĩa. Họ lớn nhất (`gh`) chỉ chiếm 6,3 % dòng định nghĩa; 5 họ lớn nhất 17,3 %; 20 họ lớn nhất 33,1 %; 50 họ lớn nhất 51,3 %. Tiền tố quá mịn để ánh xạ thẳng sang ba lớp của ADR-0090.
- Họ lệnh cụ thể (`gh`, `git`, `xargs`, `push`, `sed`, `find`, `tar`): 2 880 dòng = 17,9 % dòng định nghĩa.
- Họ bị nhiều họ khác gọi nhất (ứng viên lõi dùng chung; 2 097 cặp họ khi không cắt bảng): `is` (79 họ gọi tới, 60 dòng), `normalize` (68, 8 dòng), `dequote` (57, 8 dòng), `split` (49, 79 dòng), `positionals` (47, 22 dòng), `git` (39, 901 dòng), `no` (36, 15 dòng), `strip` (32, 82 dòng), `CodeView` (27, 107 dòng), `stdin` (25, 168 dòng), `flag` (25, 19 dòng). Tám họ nhỏ (`is`, `normalize`, `dequote`, `positionals`, `strip`, `split`, `flag`, `no`) tổng 293 dòng nhưng nối với phần lớn tệp.
- Họ lệnh cụ thể cũng bị gọi từ nhiều nơi: `git` từ 39 họ, `gh` từ 21 họ, `xargs` từ 11, `sed` và `find` từ 7, `push` từ 6, `tar` từ 4. Đây là phần rối nhất khi tách.
- Hằng dùng chung nhiều họ: 277 hằng được ≥ 2 họ dùng; nhiều nhất `INTERP_RE` (20 họ), `SHELL_KEYWORDS` (19), `SHELLS` (18), `ENV_ASSIGN_RE` (11), `DECLARE_CMDS` (10).
- **Họ theo tiền tố là trùng tên, chưa phải module gắn kết.** Ví dụ họ `split` gồm `_split_free` (dòng 2052), `_split_why` (5322), `_split_trigger`, `_split_name`, `_split_view` (5437), `split_commands` (7917), `_split_words` (7954) và `_split_args` (20897): tám hàm khác mục đích rải trên gần 19 000 dòng (đọc bằng Grep ngày 2026-11-23). Vì vậy các "họ lõi dùng chung" ở trên là ứng viên theo tên; ranh giới tách phải lấy từ đồ thị gọi ở mức hàm (bao đóng bắc cầu), điều `--closure` (T-3995) nay in.
- Giới hạn của công cụ: bảng cạnh và hằng cắt ở `--top`; các số ở báo cáo này lấy từ `--top 100000` (không cắt). Bản nháp đầu của báo cáo dùng `--top 1000` nên đếm thiếu số họ gọi tới (reviewer phát hiện). Cạnh gọi xấp xỉ theo tên: tên cục bộ trùng tên định nghĩa cấp tệp bị tính nhầm, annotation và `isinstance` tính như lời gọi, và tham chiếu ở cấp tệp (bảng hàm, hằng dựng từ hằng) không được tính.

## Hệ quả cho quyết định tách

1. **Lợi ích hiệu năng khi tách theo họ lệnh là nhỏ và chỉ có khi nạp lười.** Ước lượng thô: nếu compile tỉ lệ theo dòng định nghĩa và chỉ họ lệnh cụ thể ở trên nạp lười thì tiết kiệm khoảng 70 ms trên 393 ms (≈ 18 %), tương đương ≈ 13 % thời gian hook. Đây là ước lượng chứ không phải cận trên chặt: cụm nạp lười có thể kéo theo cả regex và hằng riêng của nó, và các họ đó bị nhiều họ khác gọi nên thực tế thấp hơn. **Giả định chưa kiểm:** compile tỉ lệ tuyến tính theo dòng định nghĩa; phần cấp tệp (≈ 34 % số dòng, nhiều hằng) vẫn compile ở mọi lệnh. Nạp hết (eager) thì tổng compile không đổi, nên lợi ích hiệu năng bằng 0.
2. **Tách chỉ để bảo trì vẫn có giá trị, nhưng cần lõi dùng chung trước.** Tách `git`/`gh` thành module riêng mà không tách lõi dùng chung (nhóm `is`, `normalize`, `dequote`, `positionals`, `strip`, `split`, `flag`) tạo nhập vòng với `guard.py`. Thứ tự hợp lý: lõi dùng chung → họ lệnh từ xa (`git`, `gh`, `push`) → các họ còn lại, với "lõi dùng chung" xác định bằng bao đóng phụ thuộc ở mức hàm của nhóm cần tách (công cụ cần mở rộng, T-3995), không bằng tiền tố tên.
3. **Muốn giảm mạnh thời gian mỗi lệnh phải đổi kiến trúc, không chỉ chia tệp.** Hướng được đưa ra xét: một đường nhanh nhỏ quyết định ngay các lệnh hiển nhiên an toàn, mọi ca không chắc rơi về guard đầy đủ. Hướng này đụng bất biến an toàn (đường nhanh phải là tập con an toàn của guard đầy đủ), nên cần chứng minh bằng so quyết định thô trên toàn bộ corpus của `autonomy-bench` (4 019 ca guard) và fuzz, không đưa vào lát đầu.
4. **Ràng buộc từ ADR-0091** giữ nguyên: bộ nạp compile từ nguồn, thiếu module sau cài dở thì Bash bị chặn (ADR-0054; chỉ đúng khi nạp ngay lúc nạp `guard.py`, vì `main()` bắt mọi ngoại lệ rồi gọi `_failure_decision` cho qua trừ merge — nạp lười phải tự deny), `perf trial` chạy một blob `xt.py` (tách `xt.py` ngoài phạm vi ở đây).

## Cách tái hiện

```bash
python3 scripts/xt_guard_profile.py --repeat 10
python3 scripts/xt_guard_profile.py --repeat 10 --top 100000 --json
python3 scripts/xt_guard_profile.py --closure family:git family:gh family:push
```

Số dẫn xuất tính từ JSON không cắt: tỉ lệ dòng của k họ lớn nhất là tổng `lines` của k hàng đầu chia tổng `lines` của mọi họ (16 088); "số họ gọi tới" của một họ là số `from` khác nhau trong các cạnh có `to` bằng họ đó; 240 họ một định nghĩa là số hàng có `defs` bằng 1.
