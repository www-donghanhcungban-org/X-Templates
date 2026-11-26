# ADR-0107: Lời khách duyệt thiết kế gắn với hash nội dung bằng chứng

- **Trạng thái:** Đã chấp nhận ngày 2026-11-26 (D-620).
- **Liên quan:** [ADR-0106](0106-client-design-approval-gate.md) (sổ `DESIGN.json`, khoá task `ui`; ADR này bổ sung §3–§5 và đóng "Giới hạn đã biết" về dòng khai), [ADR-0058](0058-product-stages-machine-lock.md).

## Bối cảnh

Rà độc lập một bản làm riêng của ADR-0106 (PR #843, đã đóng) tìm ra các lỗ mà bản trên `main` (PR #844) còn giữ; cả hai đã tái hiện bằng test đỏ trên `main` 972d3203:

1. **Lời duyệt không gắn với nội dung.** `lock_reason` trả "không khoá" mỗi khi `status == "approved"`. Agent trình bản 2 (`design-submit`, commit sổ) rồi `git revert` commit ghi sổ → sổ về `approved` của bản 1 trong khi mockup bản 2 vẫn ở cây: `loop record` task `ui` exit 0 dù không ai duyệt bản 2. Sửa, xoá hay thay mockup bằng symlink sau khi duyệt cũng không khoá lại; `stage approve --design` duyệt được cả bản đã bị sửa sau khi trình.
2. **Agent tự tắt khoá bằng `PROJECT.md`.** `declared` coi vắng `PROJECT.md` hay dòng khai là "không khai", nên khi sổ đã có lịch sử trình mà `PROJECT.md` đổi `khách` → `không` hoặc bị xoá thì task `ui` mở (đã ghi là giới hạn ở ADR-0106).

Bản #843 vá lỗ 1 lần đầu bằng "SHA đã duyệt là tổ tiên của HEAD và tệp bằng chứng không đổi từ SHA đó tới HEAD"; review đo được cách đó khoá oan sau merge squash/rebase (SHA cũ không còn là tổ tiên dù nội dung y hệt) và ở clone nông (SHA không có trong repo), và mỗi lần đọc khoá phải gọi git.

## Quyết định

1. `stage design-submit` ghi `evidence_sha256` — SHA-256 (64 hex thường) nội dung tệp bằng chứng ở cây làm việc lúc trình (cây sạch nên bằng nội dung ở HEAD) — vào `submitted` và vào sự kiện `submit` của `history`. Phát lại `history` đòi trường này; sổ thiếu hay sai dạng là **sổ hỏng** (fail-closed: mọi lệnh đọc sổ chặn, task `ui` khoá). `schema` giữ `1` vì tính năng chưa phát hành.
2. Khoá chỉ mở khi `status == "approved"` **và** tệp bằng chứng hiện tại (tệp thường, không symlink, đọc từ cây làm việc) có đúng hash của lần `submit` đã được duyệt. Lệch hay tệp mất → khoá, lý do "bản bằng chứng … đã đổi sau khi trình/duyệt" chỉ cách trả đúng nội dung hoặc `stage design-reopen` rồi trình lại. Kiểm không gọi git. SHA commit lúc trình giữ trong sổ để dẫn chứng, không dùng để khoá.
3. `stage approve --design` kiểm hash **trong khoá** `state.lock` và từ chối khi bằng chứng đã đổi sau khi trình — người duyệt đúng nội dung đã trình.
4. Sổ `DESIGN.json` đã có `history` → coi là đã khai `khách`, bất kể `PROJECT.md`: đổi dòng khai sang `không` hay xoá tệp không tắt khoá. Chỉ người xoá sổ bằng commit mới tắt. Sổ có mà hỏng → khoá kể cả khi `PROJECT.md` không khai (không biết đã từng trình chưa). Dự án không có sổ và không khai: hành vi không đổi.
5. Kèm theo (cùng lát, không đổi luật): verdict `loop` coi task `ui` đang bị giữ như `loop defer` (chỉ trong bộ nhớ, không ghi state) nên không dẫn agent vào task sẽ bị `loop record` từ chối; chỉ còn chúng → `done-pending-human` kèm lý do khoá. Thẻ `ui:` mọi giá trị khác `no` (kể cả rỗng, `true`, `có`) là giao diện. Lý do chặn `STAGE_APPROVE` của guard nói rõ `--design` không bao giờ được qua (chỉ đổi chữ, giữ số dòng).

## Phương án đã xét

- **SHA đã duyệt là tổ tiên của HEAD** (bản đầu của #843): khoá oan sau squash/rebase và clone nông, cần git ở mọi lần đọc khoá. Loại.
- **Tách khai báo khỏi `PROJECT.md`** (chỉ sổ quyết định có khoá): đổi giao ước ADR-0106 cho mọi dự án và thêm một bước khởi tạo sổ; coi "sổ có `history`" là khai `khách` vá đúng lỗ với ít thay đổi nhất. Loại.
- **Ký lời duyệt bằng khoá của người duyệt:** cần khoá chỉ chủ dự án có (ADR-0008 §mặc định tự host), không bắt được lỗ 1 tốt hơn hash. Để sau nếu cần chống agent cố ý vượt rào (ngoài phạm vi D-015, như ADR-0106).

## Hệ quả

- Tốt: lời duyệt bám nội dung được duyệt — revert sổ, sửa/xoá/thay symlink mockup đều khoá lại; trả đúng nội dung thì mở lại; squash/rebase/clone nông không khoá oan. Agent không tắt khoá bằng tệp khai.
- Xấu: hash tính trên byte ở cây làm việc — `core.autocrlf`, bộ lọc `clean/smudge` hay LFS chưa kéo làm hash lệch theo máy dù nội dung git như nhau → khoá (hướng an toàn); khi đó người xem lại bản và trình/duyệt lại trên máy đó. Tệp bằng chứng nên là tệp nhị phân hoặc có `.gitattributes` cố định dòng. Bằng chứng chỉ là một tệp: tài sản mà tệp đó dẫn link tới (Figma, ảnh khác) không được hash — người duyệt vẫn phải xem đúng phiên bản ghi trong tệp.
- Sổ tạo trước bản này (thiếu `evidence_sha256`) là sổ hỏng: người xoá `DESIGN.json` bằng commit, agent trình lại.
