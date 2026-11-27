---
title: Baseline giao hàng — 20 PR merge gần nhất vào main (T-4010)
kind: research
updated: 2026-11-26
---

# Baseline giao hàng: 20 PR merge gần nhất (đo 2026-11-26)

> Baseline của `T-4010` ([PLAN-improve-2026-11-23](../docs/autopilot/PLAN-improve-2026-11-23.md), lát 1E), đo trước mọi tối ưu CI và review. Mọi con số đo ngày **2026-11-26** từ GitHub REST API của repo `www-donghanhcungban-org/X-Templates`. Mỗi cột ghi mã nguồn đo (N1–N7, §2); lần đo sau dùng đúng định nghĩa và lệnh ở §2 để so được. Số nào không lấy được ghi "(chưa đo)" kèm lý do (§5).

## 1. Kết luận

1. **CI là chi phí chính, review đăng lên PR hiếm.** 20 PR dùng 180 run workflow, 1 033 job và **2 729,4 runner-minutes** (tổng thời lượng job, chưa làm tròn), tức 3 310 phút nếu làm tròn lên từng job như cách GitHub tính phút. Trung vị mỗi PR: 8 run, 47 job, **118,7 runner-minutes**.
2. **Push thêm vào PR đang mở là nguồn tốn lớn nhất có thể cắt.** 3/20 PR (#818, #815, #801) có nhiều lần push. 29 run chạy ở head cũ và đã chạy hết vì không có run nào bị huỷ (`cancelled` = 0). Ba PR này dùng 759,8 runner-minutes, bằng 27,8 % tổng. `ci.yml`, `pack-web-api.yml`, `pr-title.yml` và `pr-review.yml` đã đặt `concurrency` với `cancel-in-progress`, nhưng lệnh này không cắt được chi phí ở đây. Các lần push cách nhau lâu hơn thời gian một lượt CI (ở #818 là 17:02, 17:51 và 23:24 UTC ngày 2026-11-25), nên run ở head cũ đã xong trước khi có push mới. Mỗi lần push vẫn chạy lại đủ bộ CI.
3. **Không có run đỏ.** Không run nào kết luận `failure`, `timed_out` hoặc `cancelled`. Có 24 run `skipped`, đều là `pr-review` (sự kiện `pull_request_target`), và 1 lần chạy lại (CodeQL ở #821, `run_attempt` = 2).
4. **Lượt reviewer đăng lên PR: 4 lượt ở 3/20 PR** (dấu `xt-review` do `pr reviewed` đăng). Trung vị là 0 lượt mỗi PR. Ngoài ra có 1 review của bot code scanning ở #813. Không có review của người.
5. **Lead time** (mở PR → merge) có trung vị 12,7 phút. PR chậm nhất là #818 với 396,8 phút, do có nhiều lần push cách nhau nhiều giờ.

## 2. Định nghĩa và lệnh đo (chạy 2026-11-26)

`R=repos/www-donghanhcungban-org/X-Templates`. Mọi lệnh chỉ đọc (`GET`).

| Mã | Số đo | Định nghĩa | Lệnh / công cụ |
|---|---|---|---|
| N1 | Tập 20 PR | 20 PR có `merged: true`, `base: main`, `merged_at` mới nhất. Không tính PR đang mở (#822, #810). | GitHub MCP `list_pull_requests` (`state=closed`, `base=main`, `sort=updated`, `direction=desc`, `perPage=30`), đối chiếu từng PR bằng `gh api -X GET $R/pulls/<N>` (`.merged`, `.merged_at`) |
| N2 | Run CI | Run workflow có `head_sha` thuộc commit của PR và `created_at` trong [PR `created_at`, `merged_at`]. Tính mọi workflow và mọi sự kiện. Không tính run `push` lên main sau merge. | `gh api -X GET --paginate "$R/actions/runs?branch=<head.ref>&per_page=100"` lọc theo `gh api -X GET --paginate "$R/pulls/<N>/commits?per_page=100"` |
| N3 | runner-minutes | Σ(`completed_at` − `started_at`) của mọi job trong các run N2, gồm cả các lần chạy lại (`filter=all`), chia 60. Cột "làm tròn" cộng ⌈giây/60⌉ từng job. | `gh api -X GET --paginate "$R/actions/runs/<run_id>/jobs?filter=all&per_page=100"` |
| N4 | Run ở head cũ | Run N2 có `head_sha` khác head lúc merge, nghĩa là đã bị một lần push sau thay thế. | Như N2, so với `.head.sha` của `$R/pulls/<N>` |
| N5 | Run bị huỷ / chạy lại / skipped / đỏ | Đếm theo `conclusion` (`cancelled`; `skipped`; `failure`, `timed_out`, `startup_failure`). Chạy lại = Σ(`run_attempt` − 1). | Như N2 |
| N6 | Lượt reviewer | (a) Comment có dấu `<!-- xt-review v1/v2 head=… verdict=… -->` (`REVIEW_MARK_RE` ở `scripts/xt.py`), kèm verdict và cho biết head có trùng head lúc merge hay không. (b) Review GitHub. | (a) `gh api -X GET --paginate "$R/issues/<N>/comments?per_page=100"`; (b) `gh api -X GET --paginate "$R/pulls/<N>/reviews?per_page=100"` |
| N7 | Lead time | `merged_at` − `created_at` của PR, tính bằng phút. | `gh api -X GET $R/pulls/<N>` |

Lệnh `gh search` không trả đủ tập 20 PR. `gh api -X GET "search/issues?q=repo:www-donghanhcungban-org/X-Templates+is:pr+is:merged+base:main&sort=created&order=desc"` (2026-11-26) thiếu #815 và #816, dù REST `pulls/815` và `pulls/816` trả `merged: true` vào `main`. Có thể chỉ mục tìm kiếm cập nhật trễ. Vì vậy N1 lấy tập PR từ REST `pulls`, không lấy từ search.

## 3. Bảng từng PR (đo 2026-11-26)

Tất cả run ở đây thuộc hai sự kiện `pull_request` và `pull_request_target`. Run không `skipped` đều kết luận `success`. Cột "Huỷ" = 0 và "Đỏ" = 0 ở mọi dòng nên bỏ khỏi bảng (N5).

| PR | Commit | Lead time (phút, N7) | Run (N2) | Run head cũ (N4) | Skipped (N5) | Chạy lại (N5) | Job (N3) | runner-minutes (N3) | Làm tròn từng job (N3) | Lượt reviewer (N6) | Kết quả review (N6) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| #821 | 3 | 24,4 | 8 | 0 | 1 | 1 | 48 | 142,7 | 169 | 0 | — |
| #820 | 3 | 9,4 | 8 | 0 | 1 | 0 | 47 | 119,3 | 144 | 0 | — |
| #819 | 2 | 13,9 | 8 | 0 | 1 | 0 | 47 | 118,5 | 144 | 0 | — |
| #818 | 3 | 396,8 | 21 | 14 | 3 | 0 | 117 | 313,6 | 384 | 1 | `clean` ở head merge |
| #817 | 6 | 9,4 | 7 | 0 | 1 | 0 | 39 | 103,6 | 125 | 0 | — |
| #816 | 4 | 14,5 | 8 | 0 | 1 | 0 | 47 | 119,4 | 144 | 0 | — |
| #815 | 2 | 69,6 | 14 | 7 | 2 | 0 | 78 | 211,4 | 257 | 1 | `clean` ở head merge |
| #814 | 2 | 12,0 | 8 | 0 | 1 | 0 | 47 | 118,9 | 145 | 0 | — |
| #813 | 1 | 12,1 | 8 | 0 | 1 | 0 | 47 | 116,0 | 143 | 0 (+1 bot) | bot code scanning: `COMMENTED` |
| #812 | 2 | 16,2 | 8 | 0 | 1 | 0 | 47 | 120,2 | 148 | 0 | — |
| #811 | 3 | 10,4 | 7 | 0 | 1 | 0 | 39 | 111,2 | 132 | 0 | — |
| #809 | 1 | 12,7 | 7 | 0 | 1 | 0 | 39 | 101,4 | 124 | 0 | — |
| #808 | 1 | 11,2 | 8 | 0 | 1 | 0 | 47 | 121,6 | 148 | 0 | — |
| #807 | 1 | 15,8 | 7 | 0 | 1 | 0 | 39 | 108,1 | 130 | 0 | — |
| #806 | 1 | 9,3 | 7 | 0 | 1 | 0 | 39 | 107,3 | 129 | 0 | — |
| #805 | 2 | 12,7 | 8 | 0 | 1 | 0 | 47 | 121,8 | 149 | 0 | — |
| #804 | 1 | 13,2 | 7 | 0 | 1 | 0 | 39 | 108,9 | 134 | 0 | — |
| #803 | 5 | 11,1 | 8 | 0 | 1 | 0 | 47 | 117,0 | 144 | 0 | — |
| #801 | 2 | 75,6 | 16 | 8 | 2 | 0 | 94 | 234,8 | 281 | 2 | `blocking` ở head cũ, rồi `debt` ở head merge |
| #800 | 1 | 11,3 | 7 | 0 | 1 | 0 | 39 | 113,7 | 136 | 0 | — |

## 4. Tổng và trung vị (20 PR, đo 2026-11-26)

| Số đo | Tổng | Trung vị / PR | Nhỏ nhất | Lớn nhất |
|---|---|---|---|---|
| Run CI (N2) | 180 | 8 | 7 | 21 |
| Run ở head cũ (N4) | 29 | 0 | 0 | 14 |
| Run bị huỷ (N5) | 0 | 0 | 0 | 0 |
| Run skipped (N5) | 24 | 1 | 1 | 3 |
| Run đỏ (N5) | 0 | 0 | 0 | 0 |
| Lần chạy lại (N5) | 1 | 0 | 0 | 1 |
| Job (N3) | 1 033 | 47 | 39 | 117 |
| runner-minutes (N3) | 2 729,4 | 118,7 | 101,4 | 313,6 |
| runner-minutes làm tròn từng job (N3) | 3 310 | 144 | 124 | 384 |
| Lượt reviewer dấu `xt-review` (N6a) | 4 (3 `clean`/`debt` ở head merge, 1 `blocking` ở head cũ) | 0 | 0 | 2 |
| Review GitHub (N6b) | 1 (bot code scanning) | 0 | 0 | 1 |
| Lead time, phút (N7) | 761,6 | 12,7 | 9,3 | 396,8 |
| Commit trong PR | 46 | 2 | 1 | 6 |

## 5. Chưa đo

- **Lượt reviewer chạy trong phiên mà không đăng lên PR:** (chưa đo). Sổ review cục bộ (`pr reviewed` trước khi đăng) và sổ lát của `T-4009` nằm ở `.autopilot/` của từng phiên, không có trên GitHub. Ở thời điểm đo, sổ lát chưa có sự kiện thật cho 20 PR này (đính chính 2026-11-24 ở PLAN, xem `T-5009`). N6 vì vậy chỉ đếm lượt đã đăng.
- **Phát hiện được xác nhận hay bị bác trong mỗi lượt review:** (chưa đo). Dấu `xt-review` chỉ mang verdict, không mang danh sách phát hiện. Nguồn đúng là sổ lát theo `T-4009`.
- **Chi phí USD:** (chưa đo). Repo public, phút runner GitHub-hosted không bị tính tiền; N3 là thời lượng, không phải tiền. Chi phí token của phiên AI không có trên GitHub.
- **Thời gian chờ hàng đợi runner** (`started_at` − `created_at` của job): (chưa đo). Lần đo này không tách thời gian chờ ra khỏi thời lượng job. Lần đo sau có thể tính bằng cùng lệnh N3.
- **Run `push` lên main sau merge** (CI và release trên main): không tính, theo định nghĩa N2. Các run này là chi phí sau merge, không thuộc một PR.

## 6. Dùng cho lần đo sau

Dùng lại N1–N7 nguyên văn trên 20 PR merge kế tiếp. Muốn kết luận về tiết kiệm thì so trung vị runner-minutes/PR (118,7) và tỉ lệ runner-minutes ở head cũ (27,8 % dồn vào 3 PR). Không so tổng thô vì số lần push khác nhau theo PR. Kết quả từ một mẫu 20 PR chỉ là baseline, chưa đủ để kết luận tỷ lệ tiết kiệm ([PLAN-improve §Bảng đo](../docs/autopilot/PLAN-improve-2026-11-23.md)).
