# ADR-0105: Hàng merge FIFO theo số PR — chỉ PR đầu hàng được cập nhật nhánh hoặc merge (LOOP-STOP-031)

- **Trạng thái:** Đã chấp nhận ngày 2026-11-26 (D-614).
- **Trạng thái triển khai:** T-5075 đưa cổng FIFO vào CLI và steward; kiểm bằng dữ liệu giả trong `tests/test_merge_queue.py`.
- **Liên quan:** [ADR-0027](0027-pr-steward-on-github.md), [ADR-0079](0079-green-check-merge.md), ADR-0036, ADR-0096, `LOOP-ORCH-013`.

## Bối cảnh

Chủ dự án yêu cầu ngày 2026-11-26: merge PR từ nhỏ lên lớn theo số, bỏ nháp, main luôn nằm ở PR nhỏ nhất để merge không xung đột; đưa thành luật cho khung và cho dự án đích.

Hiện trạng:

- Steward (ADR-0027/0079) và đường agent (`pr next`/`merge-check`/`merge-watch`) xét từng PR riêng lẻ.
- PR nào CI xanh mà GitHub báo BEHIND đều nhận `update`. Steward có `XT_STEWARD_TOKEN` nên cập nhật mọi PR tụt.
- Steward chỉ sắp theo số khi `merge_review: optional`.
- `LOOP-ORCH-013` (SHOULD FIFO) chưa có máy cưỡng chế.

Số đo (2026-11-26, GET API):

- Ruleset main của repo khung bật `strict: true`.
- Hôm nay có 13 lượt update-branch trên #827, #829–#834 và #810. Mỗi head chạy 38 job, khoảng 107 phút-job. Phần lãng phí khoảng 1 390 phút-job (khoảng 494 job).
- Riêng CI một PR có 32 job, đã vượt trần 20 job đồng thời của gói Free.
- Run steward 45773849992 ghi `#833 update ✓` trong khi #827, #829–#831 và #834 còn chạy CI.

Repo đích:

- PR đỏ treo từ 16/11: hotel-manager #155 và #157; x-shop #41, #44 và #45 (`action_required`).
- Merge sai thứ tự số: 11/30 (hotel-manager), 13/30 (x-shop). FIFO tuyệt đối sẽ làm hai repo này đứng khoảng 10 ngày.

Merge queue gốc của GitHub không áp dụng được:

- Chỉ có cho repo public thuộc Organization hoặc trên GHEC (changelog GA 2023-07-12), trong khi chủ cả 3 repo là tài khoản User.
- `PUT /pulls/N/merge` (đường merge ghim head, ADR-0036) "does not support merge queues".
- Queue gốc xếp theo thời điểm vào hàng, không theo số. Mọi công cụ hàng đợi đã đọc (Mergify, GitLab, Kodiak, Trunk) đều xếp theo lúc đến; xếp theo số PR là lựa chọn thiết kế theo yêu cầu chủ dự án, không phải chuẩn ngành.

Ràng buộc kỹ thuật: `scripts/xt.py` đang ở 23 643/23 644 dòng.

## Quyết định

Hàng chỉ do khung tự làm, đặt trong module mới `scripts/xt_merge_queue.py` (stdlib, mypy --strict 3.13, coverage 100 %). Module nhận host là `sys.modules[__name__]`, theo tiền lệ sẵn có trong `xt.py`.

1. **Một cổng chung** `gate(host, pr, d, action)` thay thân `_check_live_base`. `cmd_merge_check` (merge-check, merge-watch, guard) và `_eval_pr_next` (pr next, steward) đều đi qua cổng này; điều kiện `out["action"] == "merge"` ở `_eval_pr_next` bỏ đi, chuyển lọc vào gate.
   - Cổng hàng chỉ áp khi verdict thuộc {merge, update}, action thuộc {"", merge, update, disable-auto-merge}, và PR có `live_intent`.
   - Đo strict live-base giữ đúng logic cũ: verdict `merge`, action thuộc {"", merge}, có `strictBaseRepo`.
2. **Định nghĩa hàng.**
   - Ứng viên lấy từ listing `pulls?state=open`: cùng `base.ref`, cùng repo với head, không nháp, số nhỏ hơn, xét theo thứ tự tăng dần.
   - Lớp của từng ứng viên tính bằng `_merge_eval(_pr_rest(n, local_check=False))`, chạy trên bản PR có BEHIND đổi thành CLEAN.
   - RA HÀNG: verdict fix/human/closed, `hard` khác rỗng, `stacked`, `steward_untrusted` (trừ làn derived), hoặc KẸT.
   - TRONG HÀNG: verdict merge/review/wait. Verdict `review` giữ chỗ.
   - KẸT: `now − min(startedAt)` của check trên head vượt `merge_queue_stall_minutes` (mặc định 120). Head chưa có check nào bắt đầu thì đồng hồ tính từ `updated_at` trên listing. PR có verdict thô `update` (BEHIND) không bao giờ KẸT.
   - Đọc lỗi thì giữ hàng nếu `updated_at` còn trong TTL, quá TTL thì ra hàng.
   - PR đang xét bị giữ khi tồn tại ứng viên TRONG HÀNG: trả bản sao `d` với `verdict=wait`, lý do `chờ tới lượt: #N đứng đầu hàng (LOOP-STOP-031) — kẹt thì chuyển nháp`, `eligible=False`, bỏ `next_rest`. PR đã có `auto_merge` bị giữ thì `pr_next` trả `disable-auto-merge`, nên steward không update-branch.
3. **Cấu hình.** Hai khoá `merge_queue: fifo|off` và `merge_queue_stall_minutes: <int ≥ 0>` đọc ở `xt.yaml` đã commit trên nhánh ĐÍCH (cùng cách `_merge_eval` đọc chính sách), không đọc ở HEAD. Không đọc được hoặc giá trị lạ thì dùng fifo/120 (fail-closed); `doctor` báo giá trị sai.
4. **Chi phí và memo.** Memo theo khoá (số, head) chỉ sống trong một phạm vi tường minh `with queue_scope():` (một `steward_pass`, hoặc một lần gọi gate), không memo theo tiến trình. Đường agent đọc mạng tối đa 12 PR nhỏ hơn; vượt thì trả `wait` ("chưa xác minh được hàng"). Steward xét theo số tăng dần nên chi phí O(n).
5. **Steward.** Luôn sắp tăng dần và lọc nháp từ listing (trừ nháp có `auto_merge`). Chạy tuần tự; sau `merge ✓` thêm PR TRONG HÀNG kế tiếp vào lượt. Summary thêm dòng `hàng: đầu #N (lý do) · rời hàng: … · sau: …`. Cảnh báo `LOOP-STOP-033`: đầu hàng cần `update` mà steward không có quyền cập nhật; nhánh đích không có check bắt buộc.
6. Không dùng nhãn, không lưu trạng thái, không dùng merge queue gốc, không hạ strict. Khoá idempotent, `stale_action`, `expected_head_sha` và ghim head ADR-0036/0096 giữ nguyên.
7. ADR-0027 và ADR-0079 thêm dòng trạng thái "bổ sung bởi ADR-0105"; thân hai ADR không đổi.

D-614 ghi các quyết định chuyên môn: (a) PR fix/human/hard/chồng/fork/untrusted/nháp ra hàng ngay; (b) chặn cả merge chen ở repo không strict; (c) `review` giữ chỗ, chịu TTL; (d) không khoá đầu hàng: PR nhỏ hơn quay lại thì giành lại đầu, tốn tối đa 1 lượt CI thừa mỗi lần; (e) TTL 120 phút (khoảng 2 lần p90 từ CI xanh tới merge là 61 phút); (f) trần quét 12.

## Phương án đã xét và bác

- **Merge queue gốc của GitHub:** không bật được ở repo tài khoản User; `PUT /merge` ghim head không hỗ trợ queue; "Merge when ready" bật auto-merge mà guard chặn; mọi workflow phải nghe `merge_group`; xếp theo lúc vào hàng, không theo số.
- **Nhãn `xt-queue-head`:** giả mạo được bằng `gh pr edit --add-label` (guard cho chạy), nên PR có nhãn vượt hàng ở repo `strict: false`; là trạng thái ghi lên GitHub, cần quyền `issues: write` và dọn khi kẹt.
- **Đánh giá nhẹ bằng `_merge_blockers` kèm trần 5:** không thấy `hard`/`human`/làn nên PR ngoại lệ cứng hoặc Dependabot ở L2 tắc hàng; repo có ≥ 6 PR nhỏ hơn đỏ không merge được PR nào.
- **Phân lớp theo verdict thô:** BEHIND che `hard`/`human`, nên PR cần người mà tụt base thành đầu hàng và hàng tắc vô hạn.
- **Đọc khoá `merge_queue` ở HEAD:** ở guard và merge-check của phiên, HEAD là nhánh PR, nên commit `merge_queue: off` trên nhánh PR là tự vượt hàng.
- **Memo theo tiến trình:** `merge-watch` gọi `cmd_merge_check` trong cùng tiến trình mỗi 30 giây, memo cũ giữ `wait` đến hết `--max-minutes` dù đầu hàng đã merge.
- **FIFO tuyệt đối không có lớp ra hàng:** hotel-manager và x-shop đứng khoảng 10 ngày.
- **Hạ ruleset strict về false:** là nới cổng (AGENTS §3, `LOOP-CI-001`).
- **Giữ nguyên hiện trạng:** trường hợp xấu tốn N(N+1)/2 lượt CI (8 PR: 36 so với 8), tranh trần 20 job, trái yêu cầu chủ dự án.

## Hệ quả

Lợi ích:

- Với N PR tụt base cùng lúc, lượt CI do cập nhật nhánh giảm từ tối đa N(N+1)/2 xuống N. Riêng 2026-11-26 tránh được khoảng 13 lượt × 107 phút-job ≈ 1 390 phút-job.
- Đầu hàng không phải tranh trần 20 job.
- Không PR nào merge chen trước PR nhỏ hơn còn trong hàng; guard chặn qua `MERGE_INELIGIBLE` mà không cần luật guard mới.
- PR đỏ, cần người hoặc kẹt quá 120 phút không làm tắc hàng.

Đánh đổi:

- Thông lượng tuần tự: khoảng 42 phút wall CI mỗi PR, 8 PR mất khoảng 5–6 giờ; cập nhật song song cũng không rút ngắn vì mỗi lần merge làm các PR kia tụt.
- PR nhỏ, xanh, CLEAN vẫn phải chờ đầu hàng, kể cả ở repo `strict: false`.
- PR nhỏ hơn quay lại hàng giành đầu hàng, tốn tối đa 1 lượt CI thừa mỗi lần.
- Mỗi merge-check tốn thêm 1 GET listing và (k+1) lượt `_pr_rest` (k ≤ 12).
- Đầu hàng BEHIND ở repo không có token chỉ tiến nhờ phiên agent (`LOOP-STOP-033` cảnh báo).
- Phần "agent không tự update-branch" là kỷ luật (`LOOP-STOP-032`), vì guard chưa có luật cho `update-branch`; có thể thêm ở ADR sau khi guard.py có chỗ dưới trần dòng.

Dự án đích:

- Hành vi đổi mặc định vì vắng khoá được tính là fifo; cắt bản 3.37.0. CHANGELOG ghi "Dự án đích:" kèm đường lùi `merge_queue: off`.
- `install.py` copy thêm `xt_merge_queue.py`; mẫu `xt.yaml` ghi tường minh hai khoá. `pr-steward.yml` (copy-if-absent) không phải sửa job vì logic nằm ở `.xtemplates/scripts`.

Bảo trì:

- `xt.py` giảm khoảng 16 dòng ròng; thêm 1 module và 1 lớp test (trọng số shard).
- Sửa lệch tài liệu concurrency của steward: tài liệu ghi `pr-steward-<N>`, workflow thật dùng một nhóm `pr-steward`.

## Số đo (cách đếm, để đo lại sau 2 tuần)

- Lượt update-branch = commit `Merge branch` có committer GitHub, tạo sau lúc mở PR, đọc bằng `gh api repos/<repo>/pulls/<N>/commits`. 2026-11-26: 13 lượt trên #827 (3), #829 (2), #830–#834 (1 mỗi PR), #810 nháp (1).
- Một head PR ở repo khung chạy 38 job, khoảng 107 phút-job (CI: 32 job, wall khoảng 42 phút, n=5). Phần lãng phí 13 × 107 ≈ 1 390 phút-job.
- Nền: 60 PR merge gần nhất có 98 lượt CI (1,63/PR), 6 PR có update, mỗi PR 1 lượt. Merge sai thứ tự số: repo khung 5/60, hotel-manager 11/30, x-shop 13/30.
- Ngưỡng: lượt update-branch mỗi PR merge ≤ 1 khi có ≥ 2 PR mở, và tổng lượt update thừa giảm ≥ 80 % so với 2026-11-26. Không đạt thì xét lại bằng ADR mới.
