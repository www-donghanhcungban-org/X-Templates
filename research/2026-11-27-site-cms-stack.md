# Stack site giới thiệu + CMS tin tức tự host (T-5055)

> Đọc 2026-11-27 từ registry npm, API advisory GitHub, tài liệu chính thức (subagent `researcher`; trích qua công cụ fetch tóm lược — so lại trang gốc trước khi dẫn nguyên văn). Ngày phát hành là `time[version]` của npm. Số advisory = advisory của cả repo (gồm gói phụ trong monorepo) từ 2025-01-01, **chưa đối chiếu từng cái với bản `latest`**. Dùng cho ADR gói `site-cms-ts` (T-5056). Không có SHA commit nào được đọc, trừ Directus (`4856582e`, no-checkout).

## Kết luận dùng cho khung
- **Loại ngay vì giấy phép/trạng thái:** Directus (MSCL-1.0-GPL, không OSI; Core 3 seat cứng, SSO bị khoá), Strapi (open-core, thư mục `ee/` proprietary; không có TOTP gốc cho admin cục bộ — blog chính thức 2026-09-09), PocketBase (repo GitHub archive từ 2026-10-26), Ghost (MIT nhưng production chỉ MySQL 8; 2FA là email + xác minh thiết bị, không TOTP).
- **Ứng viên CMS:** Payload 3.94.2 (MIT, Next.js, Postgres; MFA lõi chưa chứng minh — cộng đồng có `payload-totp`), TinaCMS (Apache-2.0, 22 advisory), Keystone 9.0.0 (MIT, 5 advisory, không MFA), Decap 3.18.0 (MIT, không CSDL, MFA theo git host). Không ứng viên nào có MFA TOTP gốc **đã xác minh** → MFA admin (`ASVS 6.3.3`, L2) phải tự bổ sung hoặc đặt sau proxy xác thực; ghi vào ADR.
- **Framework site:** Astro 7.4.13 (MIT, mặc định tĩnh, `security.csp` từ 6.0.0) hợp site giới thiệu; Next.js 16.4.6 CSP nonce **bắt buộc render động, tắt SSG/ISR** (hash qua SRI còn `experimental`); SvelteKit 3.4.1 có `csp.mode: auto` (hash cho trang prerender, nonce cho trang động). Eleventy 3.1.8: 0 advisory nhưng không có CSP/JSON-LD tích hợp.
- **Animation:** Motion 14.14.0 (MIT; `MotionConfig reducedMotion="user"`), GSAP 3.15.1 (license Webflow "no charge", không OSI), CSS scroll-driven animations (`baseline: low` từ 2026-10-27, cần fallback), WAAPI `baseline: high`. Native CSS/WAAPI **không tự tắt** theo `prefers-reduced-motion` — chưa đọc nguyên văn MDN.
- **Advisory nặng (2025→nay):** Payload 8 critical (SQLi SQLite/Postgres, RCE Form Builder), Next.js 7 critical (RSC RCE CVE-2025-55182), Ghost 3 critical + 24 high, Directus 2 critical, TinaCMS 3 critical, Strapi 2 critical. Dự án đích phải ghim phiên bản + bật quét phụ thuộc, không coi "ít advisory" là bằng chứng an toàn.

## A. Framework site

| Mục | Giá trị | URL | Mức bằng chứng |
|---|---|---|---|
| Astro | `latest` 7.4.13 (2026-11-18), MIT, Node ≥ 22.23.4; `@astrojs/sitemap` 3.7.6, `@astrojs/rss` 4.0.19 (MIT); JSON-LD chính thức: không thấy; 49 advisory (1 critical RCE ảnh AVIF GHSA-26w7-cxv4-gfx2) | https://registry.npmjs.org/astro · https://docs.astro.build/en/reference/configuration-reference/ | fetch trực tiếp; cơ chế CSP hash/nonce chưa đọc |
| Next.js | `latest` 16.4.6 (2026-11-09), MIT, Node ≥ 20.9; `sitemap.ts` tích hợp, có guide JSON-LD (lưu ý thay `<` bằng `<`); CSP nonce → "must use dynamic rendering", SSG/ISR tắt; 65 advisory (7 critical) | https://nextjs.org/docs/app/guides/content-security-policy · https://nextjs.org/docs/app/guides/json-ld | fetch trực tiếp |
| SvelteKit | `latest` 3.4.1 (2026-11-25), MIT, Node ≥ 22.17; `csp.mode` hash/nonce/auto; `checkOrigin` mặc định bật (doc ghi "deprecated and removed in 3.0", thay `trustedOrigins` — mâu thuẫn với bản 3.4.1, chưa đối chiếu); 35 advisory (0 critical) | https://svelte.dev/docs/kit/configuration | fetch trực tiếp |
| Eleventy | `latest` 3.1.8 (2026-11-03), MIT, Node ≥ 18; `@11ty/eleventy-plugin-rss` 3.1.0; 0 advisory | https://registry.npmjs.org/@11ty%2Feleventy | fetch trực tiếp |
| Nuxt | `latest` 4.7.0 (2026-11-23), MIT, Node ^22.22.3 \|\| ^24.15.0 \|\| ≥ 26; `@nuxtjs/sitemap` 9.2.0; `nuxt-security` 2.7.0 (repo Baroshem, Node ≥ 24); 44 advisory (1 critical DevTools) | https://registry.npmjs.org/nuxt | fetch trực tiếp; render/RSS/JSON-LD chưa xác minh |

## B. CMS tự host

| Mục | Giá trị | URL | Mức bằng chứng |
|---|---|---|---|
| Payload | 3.94.2 (2026-11-24), MIT, Node ^22.23.5+; Postgres/Mongo (có `db-sqlite`); Docker chỉ là ví dụ Dockerfile; auth: khoá tài khoản, cookie HTTP-only, JWT, PBKDF2-SHA256 600 000 vòng — **không nhắc MFA**; 55 advisory (8 critical) | https://payloadcms.com/docs/authentication/overview · https://api.github.com/repos/payloadcms/payload/security-advisories | fetch trực tiếp |
| Strapi | 5.64.0 (2026-11-25); GitHub SPDX NOASSERTION (MIT ngoài `ee/`, `ee/` proprietary); "does not ship a built-in TOTP second factor for local admin accounts"; SSO chỉ Enterprise/Growth add-on; "does not build any official container images"; 9 advisory (2 critical, gồm SQLi Content Type Builder) | https://strapi.io/blog/strapi-admin-panel-mfa-2fa · https://docs.strapi.io/cms/features/sso | fetch trực tiếp |
| Directus | 12.7.0 (2026-11-18), MSCL-1.0-GPL (đổi từ BSL-1.1; commit `c6b1e8231`, `6f262df4a`), Node ≥ 26; Core: 3 seat cứng, 25 collection, 5 Flows, SSO không có; 2FA gốc có (policy "Require 2FA"); 56 advisory (2 critical) | https://raw.githubusercontent.com/directus/directus/main/license · https://directus.com/pricing | fetch trực tiếp |
| Keystone | `@keystone-6/core` 9.0.0 (2026-11-25), MIT; auth mật khẩu + session, không nhắc MFA; 5 advisory (1 high) | https://keystonejs.com/docs/config/auth | fetch trực tiếp; CSDL/Docker chưa xác minh |
| Ghost | 6.79.0 (2026-11-24), MIT, Node ^22.23.5 \|\| ^24.22.3; Docker Official Image; production MySQL 8; 2FA email + xác minh thiết bị; 82 advisory (3 critical, loạt 11 cái ngày 2026-11-13) | https://hub.docker.com/_/ghost · https://ghost.org/help/does-ghost-use-2fa/ | fetch trực tiếp |
| Decap CMS | 3.18.0 (2026-11-18), MIT, SPA lưu vào git (không CSDL); đăng nhập OAuth của git host, phải tự dựng proxy `/auth`; 6 advisory (2 critical `decap-server`, 2 high preview render HTML chưa lọc) | https://decapcms.org/docs/authentication-backends/ | fetch trực tiếp |
| TinaCMS | `tinacms` 3.15.2 (2026-11-09), Apache-2.0; self-host qua database adapter + Auth.js; 22 advisory (3 critical, 11 high gồm XSS rich text) | https://tina.io/docs/self-hosted/overview | fetch trực tiếp |
| PocketBase | v0.40.6 (2026-10-23), MIT; **repo archive 2026-10-26**, README chuyển sang `ganigeorgiev.com` (chưa mở); MFA tuỳ chọn từ v0.23 (superusers chưa xác nhận); 2 advisory | https://github.com/pocketbase/pocketbase | fetch trực tiếp |
| Sanity | Studio là SPA mã mở, tự host; Content Lake là dịch vụ hosted; license Studio chưa xác minh | https://www.sanity.io/docs/studio/deployment | fetch trực tiếp (một phần) |

## C. Animation

| Mục | Giá trị | URL | Mức bằng chứng |
|---|---|---|---|
| Motion | `motion` 14.14.0 (2026-11-13), MIT; kích thước doc: `motion` 43 kB, `m`+LazyMotion ~5 kB (không nói gzip); `MotionConfig reducedMotion="user"` tắt transform/layout, giữ opacity/màu | https://motion.dev/docs/react-reduce-bundle-size · https://motion.dev/docs/react-accessibility | fetch trực tiếp |
| GSAP | 3.15.1 (2026-11-04); license "Standard 'no charge'" của Webflow (không OSI; cấm dùng trong công cụ dựng animation trực quan cạnh tranh Webflow; Webflow được đổi điều khoản); `gsap.matchMedia()` cho reduced-motion | https://gsap.com/standard-license | fetch trực tiếp |
| Lenis | 1.3.29 (2026-11-26), MIT; `respectReducedMotion` mặc định `true` | https://github.com/darkroomengineering/lenis | fetch trực tiếp |
| CSS scroll-driven animations | `baseline: low`, từ 2026-10-27; Chrome/Edge 115, Firefox 159, Safari 26 | https://raw.githubusercontent.com/web-platform-dx/web-features/main/features/scroll-driven-animations.yml.dist | fetch trực tiếp |
| View Transitions | cùng tài liệu: `baseline: low` từ 2025-10-14; liên tài liệu (MPA) `baseline: false` | cùng repo `web-features` | fetch trực tiếp |
| WAAPI | `baseline: high` (high 2023-03-16) | cùng repo | fetch trực tiếp |

## D. Kiểm trong CI

| Mục | Giá trị | URL | Mức bằng chứng |
|---|---|---|---|
| `@lhci/cli` | 0.16.1 (2026-11-11), Apache-2.0, Node ≥ 22.19, phụ thuộc `lighthouse` 13.6.0; khoảng trống 16 tháng không phát hành (2025-06-25 → 2026-11-02), nay hoạt động trở lại; 0 advisory | https://registry.npmjs.org/@lhci%2Fcli | fetch trực tiếp |
| `@axe-core/playwright` | 4.14.1 (2026-11-24), MPL-2.0 (copyleft mức tệp, OSI), Node ≥ 22.12 | https://registry.npmjs.org/@axe-core%2Fplaywright | fetch trực tiếp |
| Playwright | 1.65.1 (2026-11-13), Apache-2.0, Node ≥ 20 | https://registry.npmjs.org/playwright | fetch trực tiếp |

## E. OWASP Cheat Sheet (commit cuối trên nhánh mặc định)

CSRF Prevention 2026-11-10; Content Security Policy 2026-10-04; Authentication 2026-10-04; Multifactor Authentication 2026-11-15; XSS Prevention 2026-11-01 (`OWASP/CheatSheetSeries`, qua API commits GitHub).

## Chưa xác minh
- Astro: cơ chế CSP (hash/nonce). Gói JSON-LD chính thức của Astro/SvelteKit; sitemap/RSS của SvelteKit.
- SvelteKit: hành vi CSRF mặc định ở 3.x (doc `checkOrigin` mâu thuẫn bản).
- Nuxt: mô hình render, RSS, JSON-LD, CSP nonce của `nuxt-security`; `@nuxtjs/sitemap` có "chính thức" hay không.
- Payload: MFA ở trang doc khác; lọc XSS rich text (Lexical); mặc định `csrf`/`sameSite`.
- Mọi CMS: cách lọc XSS và CSRF mặc định cho rich text/admin (chưa đọc từng cái). Docker chính thức của Directus (URL thử 404), Keystone, Decap, Tina. TinaCMS có SQLite hay không.
- PocketBase: kho mới chưa mở; MFA cho `_superusers`. Sanity: license Studio, tự host Content Lake.
- Số gzip của GSAP, Lenis, Motion. Directus: 30 ngày ân hạn khi vượt Core (chỉ có trong kết quả tìm kiếm).
- Reduced-motion của CSS scroll-driven/View Transitions/WAAPI: chưa đọc nguyên văn mục accessibility MDN/spec.
- Chưa đối chiếu advisory với bản `latest`, nên không kết luận bản nào đã vá.
