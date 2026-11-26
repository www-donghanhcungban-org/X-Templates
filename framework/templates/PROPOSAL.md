---
title: Mẫu PROPOSAL (chào giá trước G0)
kind: template
updated: 2026-11-26
---

# Mẫu PROPOSAL.md

> **Ai viết:** người nhận việc (đơn vị/agent hỗ trợ) **trước G0**, khi dự án làm cho khách theo lời mời hay hồ sơ yêu cầu (ADR-0106, `PM-PLAN-019`). **Không** thiết kế, không code trước khi khách chấp nhận bản chào.
> **Cổng dùng:** khách chấp nhận (ghi ngày, kênh) → G0 `PROJECT.md`; khoản "Duyệt thiết kế" chuyển thành dòng `Duyệt thiết kế: khách` của `PROJECT.md` (`UX-DS-023`).
> **Cách điền:** thay `<...>`; không có thì ghi "không áp dụng — lý do". Con số ước lượng là khoảng P50–P90, không một số.

```markdown
# PROPOSAL — <Tên dự án> cho <Khách>

> Phiên bản <n> · ngày <YYYY-MM-DD> · hiệu lực tới <YYYY-MM-DD> · lời mời gốc: <link/tệp>

## 1. Hiểu yêu cầu
- Mục tiêu của khách (1–3 câu, theo lời khách): <...>
- Bảng đối chiếu yêu cầu → cách đáp ứng → mục khung kiểm:
| # | Yêu cầu của khách | Cách đáp ứng | Mục kiểm (ID) |
|---|---|---|---|
| 1 | <Thiết kế Figma Desktop/Mobile> | <designer, công cụ, số màn hình> | UX-DS-023/024 |

## 2. Phạm vi
- Làm: <danh sách trang/tính năng>
- Không làm: <...> (mỗi mục một lý do)
- Giả định: <nội dung, ảnh, tài khoản, tên miền do ai cung cấp>

## 3. Công nghệ
- Hồ sơ/quy mô ghép thử: `xt.py compose --profile <p> --scale <S|M> --out /tmp/BLUEPRINT.md` → <số MUST>
- Stack đề xuất (ứng viên, chốt ở G2 bằng ADR): <...> — phương án thay thế: <...>

## 4. Tiến độ theo cổng
| Mốc | Cổng | Đầu ra khách nhận | Khách duyệt? | Ngày (P50–P90) |
|---|---|---|---|---|
| 1 | G0–G3 | PROJECT, SPEC | có | |
| 2 | G4 | Bản thiết kế Desktop + Mobile | **có — bắt buộc trước code UI** | |
| 3 | G5–G6 | Bản chạy thử (preview) | có | |
| 4 | G7 | GO/NO-GO, bàn giao | có | |

## 5. Báo giá
| Hạng mục | Ước lượng công (P50–P90) | Đơn giá | Thành tiền | Ghi chú |
|---|---|---|---|---|
- Chi phí định kỳ của khách (hosting, tên miền, công cụ thiết kế, dịch vụ trả phí): <...>
- Điều khoản thanh toán theo mốc, số vòng sửa thiết kế đã gồm: <n>

## 6. Rủi ro và cách xử lý
| Rủi ro | Khả năng | Ảnh hưởng | Cách xử lý |
|---|---|---|---|

## 7. Bàn giao
Mã nguồn (repo chuyển quyền), file thiết kế (chuyển quyền trong công cụ, `UX-DS-024`), tài khoản quản trị (qua cơ chế nền tảng, `PM-HANDOVER-004`), tài liệu (`PM-HANDOVER-002`), thời gian bảo hành/hỗ trợ (`PM-HANDOVER-007`).

## 8. Năng lực
Portfolio, link site thật, mẫu thiết kế đã làm — chỉ dự án được phép công bố.
```
