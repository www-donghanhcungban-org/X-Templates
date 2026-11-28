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
`focus` (focus-visible). `element` khớp định danh in trong báo cáo. `check` là `contrast`, `reflow` hoặc `axe:<rule>` ở
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
- Phần tử chưa đo gồm nền ảnh/gradient, độ mờ/bộ lọc/hoà trộn ở bất kỳ tổ tiên nào, chữ trong suốt
  (`-webkit-text-fill-color`, `color: transparent`), `::before`/`::after` có nền, định vị tuyệt đối hay độ mờ riêng, khung
  con không có nền đục, trạng thái không kích hoạt được và trường hợp axe yêu cầu xem lại bằng tay.
- Mỗi điều khiển được đo theo chữ của chính nó, của phần tử con đang hiển thị có chữ và của `::before`/`::after` có chữ;
  kết quả đo được tệ nhất quyết định, và một phần chưa đo không che vi phạm đã đo ở phần khác. Cổng đi theo cây phẳng
  (slot đã có nội dung gán thì bỏ phần dự phòng; shadow `closed` không đọc được nên điều khiển trong đó không được duyệt) và
  duyệt từng iframe (định danh `frame[N] …`, N là thứ tự khung theo Playwright, có thể đổi khi khung chèn động). Điều khiển
  trong shadow root báo `element=null` nên chưa khai ngoại lệ được.
- 320 CSS px là ngưỡng reflow WCAG 2.2 SC 1.4.10. 280 CSS px là phép thử căng của khung. Ở khổ ≤ 400 px, vùng
  `overflow:hidden|clip` cắt chữ giữa dòng là vi phạm `reflow`; chữ nằm hẳn ngoài khung cắt (carousel hay nội dung ẩn có
  chủ ý) báo `UNMEASURED` để người xem và khai ngoại lệ (`check: reflow`). Bỏ qua điều khiển form, chữ ẩn thị giác (`clip`,
  hộp ≤ 1 px) và phần chữ cắt có `text-overflow: ellipsis`. Vùng `overflow-x: auto|scroll` có nội dung cần cuộn ngang
  báo `UNMEASURED`, kể cả `body` khi tự cuộn độc lập. Tràn ngang của viewport được đo ở tài liệu gốc. Pseudo
  `::before` hoặc `::after` có nội dung rỗng và nét vẽ trong vùng đang tràn hoặc có mép cắt nằm trong padding box
  cũng báo `UNMEASURED` để xem thủ công. Cổng xét màu, viền, outline, bóng và ảnh nền theo CSS đã tính. Màu, bóng
  và gradient hoàn toàn trong suốt được bỏ qua. Ảnh nền có điểm ảnh chưa đọc được vẫn cần kiểm thủ công.
  Trong tối đa 20 chẩn đoán vùng reflow mỗi viewport và theme, các vi phạm cắt chữ đã đo được xếp trước.
  Phép kiểm chỉ xét chiều ngang trong tài liệu chính. Cổng đi vào shadow root mở (báo `REFLOW … shadow_measured=N`); host có shadow
  `closed` không đo được nên báo `UNMEASURED … not_measured` (phần tử `shadow[closed]`, khai ngoại lệ được), không coi là
  đạt. Ảnh/video/canvas/svg thò ra khỏi khung cắt báo `UNMEASURED` (cắt ảnh thường có chủ ý).
- Ý tưởng cổng đo trên bản render tham khảo `plugin87/ux-ui-agent-skills` (MIT) qua stored 06 §7d. Mã viết cho khung.
