# ADR-0109: Gói `site-cms-ts` — Astro tĩnh + Decap CMS cho site giới thiệu có tin tức

- **Trạng thái:** Đã chấp nhận ngày 2026-11-27 (D-624).
- **Trạng thái triển khai:** chưa — ADR này chốt stack; starter, CI và cài đặt là T-5057…T-5059 ở [PLAN-site-cms](../autopilot/PLAN-site-cms-2026-11-26.md).
- **Liên quan:** [ADR-0068](0068-software-factory-direction.md) (gói sản phẩm có phiên bản), [ADR-0106](0106-client-design-approval-gate.md) (khách duyệt thiết kế trước code), [nghiên cứu stack](../../research/2026-11-27-site-cms-stack.md), [nghiên cứu SEO](../../research/2026-11-26-seo-indexing.md).

## Bối cảnh

Yêu cầu mẫu: website giới thiệu công ty theo Figma Desktop/Mobile, landing có animation, trang quản trị tin tức, SEO/Core Web Vitals, chống DDoS/SQLi/XSS/CSRF, bàn giao. Khung chưa có gói cho loại này (`web-api-ts` là ứng dụng nghiệp vụ nhiều tenant). Hồ sơ `static-site` đã đòi bề mặt tấn công nhỏ, CWV và SEO.

Dữ kiện (nghiên cứu 2026-11-27, advisory chưa đối chiếu từng cái với bản mới nhất): Payload 55 advisory từ 2025 (8 critical: SQLi, RCE Form Builder), Next.js CSP nonce buộc render động (tắt SSG/ISR), Strapi không có TOTP gốc cho admin và có phần `ee/` độc quyền, Directus giấy phép không OSI và Core giới hạn 3 seat, PocketBase repo đã archive, Ghost cần MySQL 8. Không CMS ứng viên nào có MFA TOTP gốc **đã xác minh**.

## Quyết định

1. **Site:** Astro (MIT, tĩnh mặc định, `security.csp` từ 6.0.0), `@astrojs/sitemap`, `@astrojs/rss`; JSON-LD tự sinh từ dữ liệu bài (không có gói chính thức).
2. **CMS tin tức:** Decap CMS (MIT) — nội dung là tệp Markdown/JSON trong git, không CSDL, không phiên người dùng phía site. Đăng nhập admin bằng OAuth của git host qua proxy `/auth`, `/callback` tự host.
3. **MFA admin** (`ASVS 6.3.3`, L2) giao cho git host: dự án đích bắt buộc 2FA ở tổ chức/repo, ghi vào hồ sơ bàn giao. Khung không tự viết MFA.
4. **Animation:** CSS (scroll-driven có `@supports` + fallback, View Transitions) và Motion (MIT) khi cần; mọi animation tắt/giảm theo `prefers-reduced-motion` và có test. GSAP không mặc định (giấy phép Webflow, không OSI).
5. **Kiểm trong CI:** `@lhci/cli` (CWV, SEO), `@axe-core/playwright` (a11y), Playwright (E2E, CSRF của proxy, XSS preview, JSON-LD hợp lệ — `FE-RENDER-019`), sitemap/robots test; mutant ≥ 1 ca mỗi lớp (CSRF, lọc HTML bài viết, phân quyền admin/proxy, reduced-motion, JSON-LD, sitemap).
6. **Quy trình:** gói chỉ cài sau khi khách chấp nhận chào giá và duyệt thiết kế (ADR-0106); `/factory` chọn gói theo hồ sơ `static-site` khi yêu cầu có trang giới thiệu + tin tức.

## Phương án đã xét

- **Payload + Next.js (một ứng dụng, Postgres):** admin có sẵn, nhưng 8 advisory critical từ 2025, MFA lõi chưa chứng minh, CSP nonce tắt SSG. Giữ làm đường lùi.
- **Astro + admin tự viết:** tự gánh CSRF, MFA, lọc XSS rich text, phiên. Loại: tăng bề mặt tấn công không cần.
- **Ghost / Strapi / Directus / PocketBase:** loại vì giấy phép/trạng thái/MFA như bối cảnh.
- **Sanity:** Content Lake là dịch vụ hosted, mặc định tự host loại (AGENTS.md §4).

## Hệ quả

- Bề mặt tấn công nhỏ: không CSDL, không phiên phía site; DDoS giảm nhờ CDN/hosting tĩnh.
- Người soạn tin cần tài khoản git host; trải nghiệm kém hơn CMS có admin riêng. Khách không dùng git host → quay lại phương án Payload bằng ADR mới.
- Decap có advisory riêng (preview render HTML chưa lọc, `decap-server` lộ mạng): gói chỉ dùng chế độ git-gateway/OAuth, không chạy `decap-server` ở production, preview đi qua bộ lọc HTML đã thử.
- Phiên bản ghim; `support_until` theo `pack.json`; cập nhật bằng PR nâng gói.

## Đường lùi

Nội dung là tệp trong git; chuyển sang Payload/Ghost bằng script nhập + ADR mới. Gói chưa có starter nên bỏ ADR này không ảnh hưởng dự án đích.
