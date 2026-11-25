---
title: Mẫu biên bản thử tác vụ
kind: template
updated: 2026-11-25
---

# Mẫu TASK-TRIAL.md

> Người quan sát điền biên bản khi thử phương án trên prototype hoặc bản chạy ở G4–G7. Cho người dùng thực hiện cùng một nhiệm vụ trong [brief](DESIGN-BRIEF.md) và ghi dữ liệu quan sát được. Định trước mốc bắt đầu/kết thúc, tiêu chí hoàn thành và cách đếm lỗi, lần cần trợ giúp.

```markdown
# TASK-TRIAL — <tên tính năng>

- **Brief và phương án đang thử** — <đường dẫn brief, ID phương án, bản chạy hoặc prototype>
- **Thiết bị và dữ liệu** — <điều kiện thử, bộ dữ liệu dùng trong tác vụ>
- **Cách ghi** — <mốc bắt đầu và kết thúc, cách xác định hoàn thành, lỗi thao tác và trợ giúp>

## Kết quả

| Mã người thử ẩn danh | Hoàn thành (có/không) | Thời gian (giây) | Số lỗi thao tác | Số lần cần trợ giúp | Bước gặp lỗi hoặc cần trợ giúp |
|---|---|---|---|---|---|
| <mã> | <có/không> | <thời gian đo> | <số> | <số> | <bước và điều quan sát được> |

- **Số người thử** — <số dòng>
- **Số người hoàn thành** — <số dòng đánh dấu có>
- **Điều sẽ sửa hoặc thử lại** — <thay đổi, tiêu chí kiểm lại>
```

Khi chưa có buổi thử, thay mục **Kết quả** bằng `Chưa thử` kèm lý do và bước tiếp theo. Dùng `0` khi đã quan sát và đếm được 0. Dùng mã ẩn danh cho mỗi người thử.
