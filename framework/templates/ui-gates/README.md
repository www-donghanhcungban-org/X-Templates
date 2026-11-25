---
title: Mẫu cổng render UI (Playwright + axe)
kind: template
updated: 2026-11-25
---

# Mẫu cổng render UI

> Cổng đo trên bản render thật cho dự án web. Chạy axe theo tag WCAG 2.2, kiểm tràn ngang và đo tương phản chữ của điều
> khiển ở trạng thái mặc định, hover và focus-visible. Bổ sung cho `xt.py contrast` khi nền ảnh, lớp phủ hoặc trạng thái
> tương tác làm đổi màu thấy trên màn hình. Mục tiêu [`UX-A11Y-001`](../../06-design-ux/accessibility.md),
> `UX-A11Y-013`, `UX-A11Y-028` và `UX-A11Y-029`.

## Cách dùng

1. Chép `verify-render.mjs` vào `scripts/` của dự án, nơi tìm thấy `node_modules` của dự án.
2. Chạy `npm i -D --save-exact playwright@1.64.0 @axe-core/playwright@4.13.0 playwright-core@1.64.0` và commit lockfile.
   Trong CI, chạy `npm ci` rồi `npx playwright install --with-deps --only-shell chromium`. Có thể đặt
   `XT_CHROMIUM=/đường/dẫn/chromium` để dùng Chromium đã cài.
3. Chạy sau bước build và khởi động server. Truyền URL của từng trang và trạng thái giao diện cần kiểm kể cả lỗi và
   dialog. Có thể truyền tệp HTML cục bộ.

```sh
node scripts/verify-render.mjs http://localhost:3000/ http://localhost:3000/login --themes light,dark --strict
```

| Tuỳ chọn | Mặc định và ý nghĩa |
|---|---|
| `--widths 320,280` | Danh sách viewport bổ sung, tính bằng CSS px. Luôn có 1280 × 800. Tất cả viewport cao 800 px. |
| `--themes light,dark` | Mặc định `light`. Mô phỏng `prefers-color-scheme` của trình duyệt cho từng theme. |
| `--limit 60` | Đo tối đa 60 điều khiển nhìn thấy trong mỗi viewport và theme. Điều khiển nằm ngoài giới hạn được báo `UNMEASURED`. |
| `--tags …` | `wcag2a,wcag2aa,wcag21aa,wcag22aa`. |
| `--strict` | Bật ở cổng phát hành để `UNMEASURED` chưa có ngoại lệ làm đỏ. |
| `--exceptions <file.json>` | Đọc ngoại lệ hữu hạn cho các phép đo chưa thực hiện được. |

Mỗi tổ hợp viewport và theme tải trang mới trước khi chạy axe, kiểm tràn ngang và đo tương phản theo từng trạng thái.
Dòng `CONTRAST` đếm phần tử đã đo và chưa đo cho từng trạng thái. Dòng `AXE` đếm cặp phần tử và rule trong trạng thái
mặc định. `measured` gồm cả vi phạm đã đo, `unmeasured` gồm cả trường hợp đã có ngoại lệ và `exempted` đếm phần có ngoại lệ.
Với nền trong suốt, phép đo ghép màu với màu hệ thống `Canvas` theo `color-scheme` thực tế ở gốc tài liệu.
Nếu Chromium không xác định được màu `Canvas` đục, phép đo được báo `UNMEASURED`.

Exit 0 khi không có vi phạm đã đo và điều kiện nghiêm ngặt đã chọn được đáp ứng. Exit 1 khi có vi phạm đã đo hoặc
`--strict` còn `UNMEASURED` chưa miễn. Exit 2 khi cấu hình sai hoặc cổng không chạy hết, ví dụ thiếu Chromium, thiếu
phụ thuộc, lỗi tải trang hoặc phản hồi HTTP không phải 2xx. Điều khiển vô hiệu (`:disabled`, kể cả trong `fieldset`
vô hiệu) nằm ngoài phạm vi đo. Báo cáo vẫn ghi `UNMEASURED` khi ngoại lệ được áp dụng. Định danh `target` trong báo cáo
bỏ userinfo, query và fragment (đánh dấu `[đã che]`), cả trong thông điệp lỗi của trình duyệt; ngoại lệ vẫn khớp theo URL
đầy đủ. Transition và animation hữu hạn được kết thúc trước khi đọc màu; hoạt ảnh vô hạn chạm tới điều khiển thì báo
`UNMEASURED`.

## Ngoại lệ có bằng chứng

Sao chép đúng phạm vi từ dòng `UNMEASURED` vào tệp JSON. `target` là URL hoặc đường dẫn dùng khi gọi lệnh, chuẩn hoá từ
thư mục chạy lệnh. `width` là số nguyên dương, `theme` là `light` hoặc `dark`, `state` là `default`, `hover` hoặc
`focus` (focus-visible). `element` khớp định danh in trong báo cáo. `check` là `contrast` hoặc `axe:<rule>` ở
`default`. Mỗi phạm vi cần một lý do và đường dẫn hoặc URL tới bằng chứng đo tay. Hạn `expires` là ngày UTC có thật
dạng YYYY-MM-DD, còn hiệu lực hết ngày đó.

```json
{
  "schema": 1,
  "exceptions": [
    {
      "target": "http://localhost:3000/login",
      "width": 320,
      "theme": "light",
      "state": "hover",
      "check": "contrast",
      "element": "#signin",
      "reason": "Gradient cần phép đo tay tại vị trí chữ",
      "evidence": "docs/reviews/ui-login.md#contrast-hover",
      "expires": "2026-12-31"
    }
  ]
}
```

Phạm vi dùng giá trị chính xác, không có wildcard hoặc mục trùng (`*` đã escape bằng `\`, như `#star\*name`, là ký tự thật). Ngoại lệ hết hạn và không dùng được in riêng. Ngoại lệ
chỉ áp dụng cho `UNMEASURED`. Mọi vi phạm axe, reflow hoặc tương phản đã đo vẫn làm đỏ.

## Giới hạn

- Đo chữ của `a[href]`, `button`, `input`, `select`, `textarea`, `[role=button]`, `[tabindex]`. Trạng thái
  `disabled` được miễn theo WCAG 1.4.3. Dùng phép kiểm bổ sung cho viền/icon, `active` và `selected`.
- Phần tử chưa đo gồm nền ảnh/gradient, trạng thái không kích hoạt được và trường hợp axe yêu cầu xem lại bằng tay.
- 320 CSS px là ngưỡng reflow WCAG 2.2 SC 1.4.10. 280 CSS px là phép thử căng của khung.
- Ý tưởng cổng đo trên bản render tham khảo `plugin87/ux-ui-agent-skills` (MIT) qua stored 06 §7d. Mã viết cho khung.
