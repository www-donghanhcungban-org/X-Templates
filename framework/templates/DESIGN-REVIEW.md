---
title: Mẫu DESIGN-REVIEW (bản thiết kế trình khách duyệt)
kind: template
updated: 2026-11-26
---

# Mẫu DESIGN-REVIEW.md

> **Ai viết:** người thiết kế cùng agent, cuối G4, khi `PROJECT.md` khai `Duyệt thiết kế: khách` (`UX-DS-023`, ADR-0106).
> **Cổng dùng:** commit tệp này rồi `xt.py stage design-submit --evidence docs/design/DESIGN-REVIEW.md`; chủ dự án ghi lời duyệt của khách bằng `xt.py stage approve --design --sha <bản trình> --note "<kênh + ngày + link lời duyệt>"` ở terminal ngoài phiên agent. Trước lúc đó máy không cho chạy task `(ui: yes)`.
> **Đường dẫn:** `docs/design/DESIGN-REVIEW.md`; khách đòi sửa → `stage design-reopen --reason`, sửa, trình lại (mỗi lần trình là một phiên bản). Lời duyệt gắn với hash nội dung tệp đã trình: sửa tệp sau khi trình/duyệt là khoá lại (ADR-0107).

```markdown
# DESIGN-REVIEW — <Tên dự án> · phiên bản <n>

- Công cụ và link: <Figma/Penpot URL> · phiên bản/ngày lưu: <...> · quyền xem của khách: <đã mời / link chia sẻ>
- Token: <đường tệp token trong repo (`UX-DS-*`), ngày đồng bộ>
- Spec đối chiếu: docs/specs/SPEC-<slug>.md

## Màn hình × thiết bị (đủ mọi màn hình trong SPEC)
| Màn hình | Desktop (frame) | Mobile (frame) | Trạng thái rỗng/lỗi/tải | Chuyển động (token, reduced-motion) |
|---|---|---|---|---|
| Trang chủ | <link frame> | <link frame> | <link> | <...> |

## Thay đổi so với bản trước
- <mục — lý do — theo yêu cầu nào của khách>

## Điểm cần khách quyết
- <...>
```
