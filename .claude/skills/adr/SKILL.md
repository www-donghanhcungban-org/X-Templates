---
name: adr
description: Tạo bản ghi quyết định kiến trúc (ADR) mới từ mẫu của khung, đánh số tăng dần, không sửa ADR cũ (đổi ý → ADR mới + đổi dòng trạng thái của ADR cũ). Dùng khi chốt quyết định kiến trúc/công nghệ lớn hoặc gõ /adr.
argument-hint: "<tiêu đề quyết định>"
---

# /adr — một quyết định, một bản ghi

`<FW>` = `.xtemplates/framework` trong dự án đích, hoặc `framework` trong repo khung.

1. Mẫu: `<FW>/templates/ADR.md`. Thư mục dự án: `docs/adr/NNNN-<slug>.md` (4 chữ số, tăng dần; `ls docs/adr` để lấy số kế).
2. Viết đủ theo mẫu MADR của khung (`ARC-ADR-003`): **Bối cảnh** (vấn đề + ràng buộc + bằng chứng đã nghiên cứu, có ngày) · **Yếu tố quyết định** (3–5 điều đo được, vd chạy offline, license OSI) · **Phương án đã xét** (≥ 2, ưu/nhược, chi phí; luôn có "giữ nguyên hiện trạng") · **Quyết định** (một câu, gắn với yếu tố quyết định) · **Hệ quả** (tốt/xấu/nợ) · **Xác nhận** (cái gì bảo vệ quyết định: luật phụ thuộc, test, hook, mục blueprint; chưa có thì ghi "chưa có hàng rào — nợ", `ARC-ADR-010`) · **Điều kiện đọc lại** (sự kiện đo được khiến phải xem lại: tenant thứ hai, phiên bản EOL, vượt một máy) · **Status** (Proposed/Accepted/Superseded by NNNN/Deprecated) · **Implementation status** (chưa/đang/đã — do code chứng minh, kèm PR).
3. Quyết định dính phiên bản/chuẩn/luật → `/research` trước, ghi nguồn + ngày (`ARC-ADR-006`; không xác minh được → "(chưa xác minh)"). Quyết định về hiệu năng/chi phí → có số đo hoặc PoC, không chọn theo cảm giác.
4. **Không sửa nội dung ADR đã Accepted.** Đổi ý → ADR mới, ADR cũ chỉ đổi `Status: Superseded by NNNN`.
5. Liên kết ADR từ PR/PLAN/PROGRESS ("Quyết định quan trọng"). Commit `docs(adr): NNNN <tiêu đề>` (hook chạy cổng commit).
