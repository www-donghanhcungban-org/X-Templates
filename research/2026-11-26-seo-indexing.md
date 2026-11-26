# SEO kỹ thuật, lập chỉ mục, dữ liệu có cấu trúc (T-5050)

> Đọc 2026-11-27 từ trang chính thức (subagent `researcher`; trích qua công cụ fetch tóm lược — so lại trang gốc trước khi dẫn nguyên văn). Dùng cho `FE-RENDER-019/020/021`. Không có SHA commit nào được đọc.

## Kết luận dùng cho khung
- **JSON-LD là định dạng khuyến nghị**, nhưng Google chấp nhận cả ba định dạng nếu markup hợp lệ. Markup phải khớp nội dung hiển thị; đánh dấu nội dung người đọc không thấy là vi phạm chính sách. → `FE-RENDER-019`.
- **Organization, Article/NewsArticle/BlogPosting không có thuộc tính bắt buộc** (chỉ khuyến nghị); `WebSite` (tên site) cần `name`, `url`; `BreadcrumbList` cần `itemListElement`, mỗi `ListItem` cần `position` và `item`/`name`. Bài "bắt buộc" của khung là hợp lệ cú pháp + khớp nội dung, không phải đủ trường khuyến nghị.
- **Danh sách rich result đổi nhanh**: FAQ ngừng hẳn (2026-05), practice problem (2026-01), sitelinks search box gỡ (2024-11), HowTo không còn trên desktop (2023-09), Dataset chỉ còn cho Dataset Search (2025-11). → Mục kiểm không được chốt cứng danh sách loại; đối chiếu lại ngày làm.
- **Trang quản trị**: `robots.txt` không giữ trang khỏi chỉ mục. Dùng `noindex` (meta hoặc `X-Robots-Tag`) và **không** chặn trong robots.txt (nếu không crawler không thấy `noindex`), hoặc bảo vệ bằng mật khẩu.
- **Sitemap**: tối đa 50 000 URL / 50 MB chưa nén; Google bỏ qua `priority`/`changefreq`; `lastmod` phải là ngày trang đổi thật, không phải ngày sinh sitemap. Endpoint ping đã ngừng.
- **Search Console**: Domain property chỉ xác minh bằng DNS; thêm hơn một cách phòng một cách hỏng. API gửi sitemap còn dùng đường dẫn `webmasters/v3`. Indexing API chỉ cho `JobPosting`/`BroadcastEvent`. → `FE-RENDER-020` là SHOULD, việc của chủ site.
- **IndexNow**: Bing, Yandex, Naver, Seznam, Yep, Amazon; **Google không thấy trong tài liệu** (chưa xác minh). Khoá 8–128 ký tự, tệp `{key}.txt` ở gốc, tối đa 10 000 URL/lần. Chỉ là MAY. → `FE-RENDER-021`.

## Dữ kiện

| # | Câu hỏi | Trả lời | URL |
|---|---|---|---|
| 1 | Định dạng khuyến nghị | JSON-LD "in most cases"; cả ba định dạng đều ổn nếu hợp lệ | https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data |
| 2 | Organization: bắt buộc | Không có; khuyến nghị `name`, `url`, `logo`, `sameAs`, `contactPoint`, `address`… | https://developers.google.com/search/docs/appearance/structured-data/organization |
| 3 | WebSite (tên site) | Bắt buộc `name`, `url` (trang chủ canonical); khuyến nghị `alternateName` | https://developers.google.com/search/docs/appearance/site-names |
| 4 | Article / NewsArticle / BlogPosting | Cả ba được chấp nhận, không có trường bắt buộc; khuyến nghị `author`, `datePublished`, `dateModified`, `headline`, `image` | https://developers.google.com/search/docs/appearance/structured-data/article |
| 5 | BreadcrumbList | Bắt buộc `itemListElement`; `ListItem` cần `position`, `item` (trừ mục cuối), `name` | https://developers.google.com/search/docs/appearance/structured-data/breadcrumb |
| 6 | Markup khớp nội dung | Có: "must be a true representation of the page content" | https://developers.google.com/search/docs/appearance/structured-data/sd-policies |
| 7 | Thư viện rich result | 25 loại trong gallery; FAQ, HowTo, sitelinks search box đã ngừng — xem nhật ký | https://developers.google.com/search/docs/appearance/structured-data/search-gallery · https://developers.google.com/search/updates |
| 8 | Giới hạn sitemap | 50 000 URL hoặc 50 MB (52 428 800 byte) chưa nén; có sitemap index | https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap · https://www.sitemaps.org/protocol.html |
| 9 | `lastmod` / `priority` | `lastmod` = ngày trang đổi, là tín hiệu lập lịch; Google không dùng `priority`, `changefreq` | https://developers.google.com/search/blog/2023/06/sitemaps-lastmod-ping |
| 10 | Ping sitemap | Ngừng (blog 2023-06-26 báo "6 months"; ngày tắt chính xác chưa có nguồn Google) | cùng URL · https://www.seroundtable.com/google-sitemaps-ping-endpoints-no-longer-work-36692.html (thứ cấp) |
| 11 | robots.txt vs noindex | robots.txt không phải cơ chế giữ trang khỏi Google; dùng `noindex` hoặc mật khẩu; trang `noindex` không được chặn trong robots.txt | https://developers.google.com/search/docs/crawling-indexing/robots/intro · https://developers.google.com/search/docs/crawling-indexing/block-indexing |
| 12 | RFC robots | RFC 9309 (2022-09, Proposed Standard) | https://www.rfc-editor.org/info/rfc9309 |
| 13 | Canonical | Redirect và `rel=canonical` mạnh, sitemap yếu; dùng URL tuyệt đối; header `Link` chỉ cho web search. Trailing slash: trang không đề cập (chưa xác minh) | https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls |
| 14 | Xác minh Search Console | DNS (TXT/CNAME), tệp HTML, meta, GA, GTM; chỉ DNS cho property Domain; nên có ≥ 2 cách | https://support.google.com/webmasters/answer/9008080 |
| 15 | API gửi sitemap | `PUT https://www.googleapis.com/webmasters/v3/sites/{siteUrl}/sitemaps/{feedpath}`, scope `auth/webmasters` | https://developers.google.com/webmaster-tools/v1/sitemaps/submit |
| 16 | Indexing API | Chỉ `JobPosting` hoặc `BroadcastEvent` trong `VideoObject` | https://developers.google.com/search/apis/indexing-api/v3/quickstart |
| 17 | IndexNow: bên tham gia, khoá, giới hạn | Bing, Yandex, Naver, Seznam, Yep, Amazon; khoá 8–128 ký tự (tài liệu tự mâu thuẫn hex vs chữ-số-gạch ngang); ≤ 10 000 URL/lần; Google chưa xác minh | https://www.indexnow.org/faq · https://www.indexnow.org/documentation |
| 18 | Core Web Vitals "good" | LCP ≤ 2,5 s; INP ≤ 200 ms; CLS ≤ 0,1; phân vị 75, tách mobile/desktop; INP thay FID 2024-03-12 | https://web.dev/articles/vitals · https://web.dev/blog/inp-cwv-march-12 |

## Công cụ kiểm offline trong CI

| Công cụ | Bản mới nhất (ngày) | License | Ghi chú |
|---|---|---|---|
| `lighthouse` | 13.6.0 (2026-10-27) | Apache-2.0 | Cần Chrome, Node ≥ 22.19. Nhóm SEO: canonical, crawlable-anchors, hreflang, http-status-code, is-crawlable, link-text, meta-description, robots-txt; **structured-data là thủ công**, không kiểm khoá theo loại |
| `schema-dts` | 2.1.0 (2026-10-02) | Apache-2.0 | Kiểu TypeScript theo schema.org lúc biên dịch; không kiểm trường bắt buộc theo tài liệu Google (suy luận, chưa đọc README) |
| `ajv` | 8.20.0 (2026-04-24) | MIT | JSON Schema; phải tự viết schema (chưa xác minh có schema chính thức) |
| `structured-data-testing-tool` | 4.5.0 (2020-03-11; repo push cuối 2023-07-31) | ISC | **Ít bảo trì**; chưa xác minh chạy offline hay còn bám thay đổi của Google |
| `lychee` | 0.24.2 (2026-05-01) | Apache-2.0 theo GitHub (chưa đọc LICENSE) | Kiểm link; chế độ offline chưa đọc tài liệu |

**Hệ quả**: không có công cụ nào đã xác minh kiểm "đúng loại, đủ trường, khớp nội dung" ngoài mạng. Mục kiểm của `FE-RENDER-019` nên là test của chính dự án (parse JSON-LD từ HTML build, kiểm `@type` + trường theo bảng ở trên + giá trị khớp thẻ hiển thị), có thể dùng `ajv` với schema tự viết.

## Chưa xác minh
- Ngày Google tắt ping sitemap; Google có tham gia IndexNow không; trailing slash.
- Phần sau của nhật ký `search/updates` (chỉ đọc 100 000/200 186 ký tự đầu).
- README các công cụ: `structured-data-testing-tool`, `schema-dts`, `lychee`; mã các audit Lighthouse ngoài `canonical`, `robots-txt`; license thật của `lychee`; Schema.org Validator, `xmllint`/XSD.
- Search Console Sitemaps API có bản `searchconsole` v1 tương đương không.
