# ADR-0103: Nới trần dòng của guard thêm 10 dòng cho luật glob tag

- **Trạng thái:** Đã chấp nhận ngày 2026-11-25 (D-606, AUD-HAR-541).
- **Liên quan:** [ADR-0018](0018-deny-dangerous-allow-rest.md), [ADR-0092](0092-raise-caps-10x.md), T-5016, AUD-SEC-996, AUD-HAR-543, PLAN-guard-split (D-542).

## Bối cảnh

`tests/test_docs_budget.py` đặt trần dòng cho `.claude/hooks/guard.py` đúng bằng số đo tại lúc đặt (24.645 dòng, T-5016), và nới trần cần ADR. Khi rà diff tích luỹ, `reviewer-alt` báo AUD-HAR-541: luật tag phiên bản F-144 của guard bỏ sót glob chỉ gồm `?` và lớp ký tự. Bộ phân tích trả `NONE` cho `git push origin HEAD:refs/tags/??.?.?`, `git tag ??.?.?` và `git update-ref refs/tags/??.?.? HEAD`, còn `HEAD:refs/tags/v1.2.?` bị chặn. Bash bung `??.?.?` theo tệp ở thư mục hiện tại, nên một tệp tên `v1.2.3` làm lệnh đó tạo tag phiên bản. Ruleset `tags.json` phía máy chủ chưa chạy thật (T-4007 cần quyền admin), nên guard là hàng rào duy nhất ở phiên này.

Nguyên nhân: `_tag_glob` chỉ coi đoạn là tag khi chữ còn lại sau khi bỏ đơn vị glob có `v` hoặc chữ số. Đoạn như `??.?.?` hay `[v][0-9].[0-9].[0-9]` không còn chữ nào nên lọt.

## Quyết định

Thay đơn vị glob bằng chữ số (đơn vị đầu bằng `v`, dấu `*` đầu bằng `v0`) để dựng chuỗi tag nhỏ nhất mà glob có thể bung ra rồi khớp với `RELEASE_VERSION_TAG`. Phép dò này cộng thêm vào luật cũ, nên guard mới là tập cha của guard cũ. Cùng chỗ đó đổi regex đơn vị glob thành `\[[^\][]*\]|[*?\[]` để không còn thời gian bậc hai với nhiều dấu `[` không đóng (AUD-HAR-543).

Sửa này thêm 10 dòng vào `guard.py`. Nâng `LINE_CAPS` của `.claude/hooks/guard.py` từ 24.645 lên 24.655, đúng số đo sau sửa và không dư. Trần của `scripts/xt.py` giữ nguyên.

Phương án đã xét:

| Phương án | Lý do không chọn |
|---|---|
| Nén hoặc gộp dòng ở chỗ khác để giữ trần | Chạm luật bảo vệ không liên quan, rủi ro lệch hành vi; trần dòng nhằm buộc tách module, không nhằm buộc nén. |
| Tách phần luật tag ra module riêng | Guard được nạp như một tệp một khối qua bộ nạp `py_run`; tách là việc của PLAN-guard-split (D-542), lớn hơn lát này. |
| Chấp nhận rủi ro, chờ tách guard | Lỗ hổng đã tái hiện và guard là hàng rào duy nhất cho tag phiên bản khi ruleset máy chủ chưa chạy. |

## Hệ quả

- Ca hồi quy trong `tests/test_hooks.py` (`RELEASE_TAG_DENY`: tám lệnh; `RELEASE_TAG_OK`: bốn đối chứng) đỏ khi thiếu bản sửa. Bench tự hành 4.103 ca guard và các bộ `test_green_*`, `test_signoff2_scripts`, `test_audit_dot4_har` giữ xanh.
- Đoạn glob dài hơn một dòng chỉ gồm đơn vị không thể ra `vX.Y.Z` (như `?.?.?`, `[ab]??`) vẫn đi qua luật cũ; dạng như `[ab].[cd].[ef]` bị coi là tag vì đơn vị đầu có thể là `v` theo cách đoán thận trọng.
- Nới trần lần sau vẫn cần ADR riêng. Hướng dài hạn vẫn là tách guard theo PLAN-guard-split.
