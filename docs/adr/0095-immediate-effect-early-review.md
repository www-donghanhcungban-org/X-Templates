# ADR-0095: Rà độc lập sớm theo tác động tức thì

- **Trạng thái:** Đã chấp nhận ngày 2026-11-23 (D-546; chủ dự án duyệt PLAN-improve-2026-11-23 và lệnh thực thi cùng ngày).
- **Sửa:** ADR-0079 (thu hẹp — xem Quyết định 3) và nhịp 1 của ADR-0080 (thêm một ngoại lệ hẹp). **Giữ:** ADR-0062 (review 1 lần), ADR-0057 (`review_debt`), ADR-0009.
- **Trạng thái triển khai:** Văn bản ở PR này; máy cưỡng chế ở `T-4003` của PLAN-improve (sau khi quyết định chặn merge ở `T-3999`…`T-4002` nhất quán).

## Bối cảnh

ADR-0079 chọn `merge_review: optional` (merge theo check xanh), ADR-0080 gom review về cổng ký vì nhánh chính chưa phải
bản phát hành: lỗi lọt qua một PR bị chặn bởi `release-check` và chữ ký trước khi ra khỏi repo. Hai tiền đề đó **không
đúng** với thay đổi mà chính nó là lớp đỡ hoặc có hiệu lực ngay khi merge:

- hook và `settings.json` của harness, workflow, ruleset, khoá chính sách của `xt.yaml` — merge xong là lớp kiểm của mọi PR
  sau đã đổi; cổng ký đến sau cả chục PR đã đi qua lớp đã yếu;
- nhánh tự triển khai production sau merge — merge chính là lúc đưa vào dùng, không còn "trước phát hành".

PLAN tách guard (`PLAN-guard-split-2026-11-22`) và `PLAN-harden-2026-11-22-b` đã đòi review ở head cho mọi PR chạm guard
bằng câu riêng của từng PLAN, mâu thuẫn với ADR-0080; đó là chỗ lệch cần một nhà.

## Phương án đã xét

1. Giữ nguyên: mọi review dồn về cổng ký. Đúng ADR-0080, nhưng để hàng rào yếu đi tới cổng ký.
2. Review ở head cho mọi PR chạm `scripts/*` hoặc có nhãn rủi ro. Là phương án D-533 đã loại; tốn lượt reviewer ở phần
   `release-check` và CI đã đỡ.
3. **Một lớp ngoại lệ hẹp theo tác động tức thì, đọc từ nhánh đích** (chọn).

## Quyết định

1. **Lớp ngoại lệ.** PR nào chạm một trong các nhóm sau cần một lượt rà độc lập có trọng tâm ở head **trước merge**, kể
   cả khi `merge_review: optional`:
   - hook và cấu hình hook của harness (`.claude/hooks/*`, `.claude/settings.json`, bản sinh cho host khác);
   - `.github/workflows/*` và `.github/rulesets/*`;
   - khoá chính sách của `xt.yaml`: `merge_*`, `release_signoff`, `delivery_phase`, `commit_gate`, `ai_attribution`;
   - nhánh tự triển khai production sau merge, do dự án đích khai.
2. **Ngoài lớp.** `scripts/*` nói chung, văn xuôi thuần, mã thường chưa phát hành, auth hoặc migration chưa đưa vào dùng
   không vào lớp: lớp đỡ là CI, ruleset và cổng ký (ADR-0080). Không mở rộng lớp này thành "mọi PR có nhãn rủi ro".
3. **Thu hẹp ADR-0079.** Với đúng các nhóm trên, `merge_review: optional` không còn nghĩa "không review": `merge-check`
   trả `review` (đường `protected` sẵn có ở `_merge_eval`). Lý do chọn khác D-533: D-533 xét câu chữ của `WF-REVIEW-007`
   cho PR rủi ro nói chung; ở đây phạm vi chỉ gồm thay đổi tự nó là lớp đỡ hoặc có hiệu lực ngay (đề xuất của chủ dự án
   2026-11-23 §2). Dự án đích tắt được bằng khoá `immediate_review: off` trong `xt.yaml` (khoá mới do `T-4003` thêm, mặc định `on`); khoá này thuộc nhóm khoá chính
   sách nên đổi nó cũng là thay đổi trong lớp (một PR có rà, người hay agent có quyền merge như mọi PR khác).
4. **Nguồn chính sách là nhánh đích.** Tập đường dẫn và khoá đọc từ nhánh đích, nên PR sửa chính sách được xét theo bản
   cũ; nhãn hay cấu hình nằm trong chính PR không tự miễn.
5. **PR Dependabot nâng action trong workflow** vào lớp như mọi PR chạm `.github/workflows/*`: một lượt rà hẹp đối chiếu
   SHA ghim với tag phát hành, không rà chi tiết mã của action.
6. **Nghi ngờ cụ thể** (ngoài lớp) xử lý bằng xác minh hẹp: đầu vào, kết quả cần kiểm, điểm dừng rõ; không mở lại review
   toàn PR hay toàn repo.
7. **Lỗi đã xác minh** vẫn xử lý theo tác động thật dù review là `optional`; không hạ mức lỗi để vừa ngân sách review.

## Hệ quả

- Thêm một lượt rà cho PR chạm hàng rào; bù lại hàng rào không yếu đi âm thầm giữa hai cổng ký.
- Hết lệch giữa PLAN riêng và ADR-0080: các PLAN chỉ liên kết về đây (`T-3998`).
- Máy cưỡng chế ở `T-4003`; tới lúc đó lớp ngoại lệ là kỷ luật, không phải cổng máy.

Đường lùi: revert PR này; ADR-0079/0080 có hiệu lực nguyên văn lại.
