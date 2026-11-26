# PLAN X-Templates 2026-11-26 — site giới thiệu: SEO kỹ thuật, duyệt thiết kế, gói site + CMS

> Duyệt: D-615 (phiên chính tự duyệt; chủ dự án yêu cầu "lập PLAN bổ sung ba chỗ hở") · Căn cứ: đối chiếu khung với một yêu cầu tuyển đơn vị làm site giới thiệu công ty (Figma Desktop/Mobile, landing có animation, admin tin tức, SEO/Index/CWV, chống DDoS/SQLi/XSS/CSRF, bàn giao) — đáp ứng khoảng 70–75 %.

## Tóm tắt
- Ba chỗ hở: (a) không có gói khởi tạo cho "site giới thiệu + quản trị nội dung" — `/factory` mặc định `web-api-ts` (nhiều tenant, RLS), sai hồ sơ; (b) thiếu mục kiểm SEO kỹ thuật: dữ liệu có cấu trúc JSON-LD, sitemap/robots, xác minh Search Console; (c) không có bước duyệt thiết kế của khách trước khi code và hợp đồng bàn giao file thiết kế.
- Khung **không** sinh file Figma: lát 2 định nghĩa hợp đồng duyệt + bàn giao (file thiết kế là đầu vào/đầu ra do người làm), không hứa tự vẽ.
- Thứ tự theo rủi ro tăng dần: lát 1–2 chỉ tài liệu + test (áp mọi dự án); lát 3 mở bằng nghiên cứu nguồn sống + ADR rồi mới viết mã gói; lát 4 pilot bằng chính yêu cầu mẫu.
- Không nới cổng: coverage 100 %, `mypy --strict`, C901 ≤ 10, trần byte (`tests/test_docs_budget.py`). Đổi điều dự án đích phải làm (ID mới MUST) → cắt bản minor sau khi lát 1–2 merge.

## Ngân sách
- Số vòng: mặc định `--single-session` · Chi phí dịch vụ ngoài: 0 (CMS/hosting tự host trong pilot) · Timeout Gate: 1200 giây · Hạn mong muốn: 2026-12-15 (lát 1–2), 2027-01-21 (lát 3–4, trùng `support_until` của gói hiện có).

## Điểm dừng bắt buộc (việc cần người — `loop defer`)
- Tài khoản Google Search Console / Bing Webmaster và xác minh tên miền thật: pilot chỉ kiểm phần máy làm được (sitemap, robots, JSON-LD hợp lệ); bước gửi sitemap ghi `defer`.
- Tài khoản Figma trả phí: không cần — lát 2 dùng Penpot tự host làm mặc định (AGENTS.md §4), Figma là phương án khi khách đã có.
- Duyệt thiết kế của khách là việc của người theo định nghĩa: khung chỉ máy hoá việc *chặn lát UI cho tới khi có bằng chứng duyệt*.
- (Chọn stack, CMS, cấu trúc gói **không** dừng: phiên chính tự quyết bằng `loop decide` + ADR.)

## Task

### Lát 1 — SEO kỹ thuật (tài liệu + test)
- [ ] `T-5050` nghiên cứu nguồn sống, ghi ngày: phạm vi Google Indexing API (loại trang được dùng), IndexNow (máy tìm kiếm hỗ trợ), xác minh Search Console, schema.org `Organization`/`WebSite`/`Article`/`BreadcrumbList`, công cụ kiểm JSON-LD chạy được trong CI không cần mạng (files: research/2026-11-26-seo-indexing.md) — Gate: `python3 scripts/check-links.py && python3 -m unittest tests.test_docs_budget`
- [ ] `T-5051` thêm vào nhà SEO `07-frontend/rendering-and-routing.md`: `FE-RENDER-019` MUST@M JSON-LD hợp lệ cho trang công khai (kiểm: parse + so khóa bắt buộc theo loại); `FE-RENDER-020` MUST sitemap.xml + robots.txt hợp lệ, `lastmod` thật, chỉ URL canonical trả 200; `FE-RENDER-021` SHOULD xác minh Search Console và gửi sitemap (việc cần người, có checklist); `FE-RENDER-022` MAY IndexNow; `static-site.md`/`web-app.md` trỏ về, không chép (sau: T-5050; files: framework/07-frontend/rendering-and-routing.md, framework/07-frontend/README.md, framework/02-profiles/static-site.md, framework/02-profiles/web-app.md, CHANGELOG.md) — Gate: `python3 scripts/xt.py validate && python3 scripts/check-links.py && python3 -m unittest tests.test_docs_budget && python3 scripts/xt.py changelog-check`

### Lát 2 — duyệt thiết kế và bàn giao file thiết kế
- [ ] `T-5052` nghiên cứu nguồn sống: Figma REST API/Plugin API/máy chủ MCP của Figma (đọc hay ghi được node thiết kế), Penpot tự host (license, API, xuất/nhập token DTCG), cách chuyển quyền sở hữu file ở mỗi công cụ (files: research/2026-11-26-design-handoff.md) — Gate: `python3 scripts/check-links.py && python3 -m unittest tests.test_docs_budget`
- [ ] `T-5053` thêm vào `06-design-ux/design-system-and-tokens.md`: `UX-DS-023` MUST khi `PROJECT.md` khai "Duyệt thiết kế: khách" — PLAN có task duyệt thiết kế đứng trước mọi task UI (khai phụ thuộc), bằng chứng `docs/design/APPROVAL.md` (link file thiết kế, phiên bản, người duyệt, ngày, khung Desktop + Mobile của mỗi màn hình trong SPEC); `UX-DS-024` MUST@M bàn giao file thiết kế qua chuyển quyền sở hữu nền tảng (trỏ `PM-HANDOVER-004`); mẫu `DESIGN-OPTIONS.md` thêm mục Duyệt; mẫu `PROJECT.md` thêm dòng "Duyệt thiết kế: không | khách"; `06-design-ux/README.md` thêm bước (sau: T-5052; files: framework/06-design-ux/design-system-and-tokens.md, framework/06-design-ux/README.md, framework/templates/DESIGN-OPTIONS.md, framework/templates/PROJECT.md, CHANGELOG.md) — Gate: `python3 scripts/xt.py validate && python3 scripts/check-links.py && python3 -m unittest tests.test_docs_budget && python3 scripts/xt.py changelog-check`
- [ ] `T-5054` máy hoá `UX-DS-023`: `blueprint-status` (hoặc kiểm PLAN tương ứng) báo đỏ khi `PROJECT.md` khai "Duyệt thiết kế: khách" mà PLAN có task UI không phụ thuộc task duyệt, hoặc thiếu `docs/design/APPROVAL.md` khi task UI đã `[x]`; test bằng PLAN/PROJECT giả, phủ 100 % dòng + nhánh (sau: T-5053; topo: review; files: scripts/, tests/) — Gate: `scripts/dev-task.sh gate-fast`

### Lát 3 — gói `site-cms-ts`
- [ ] `T-5055` nghiên cứu nguồn sống, ghi ngày, ≥ 2 phương án mỗi hạng: framework site (SSG/SSR tĩnh được, hỗ trợ đảo hydrate), CMS tự host có admin CRUD tin tức (license OSI, bản ổn định, lịch sử CVE, MFA cho admin, CSRF mặc định, lưu Postgres), thư viện animation tôn trọng `prefers-reduced-motion`, kiểm JSON-LD/sitemap trong CI (files: research/2026-11-26-site-cms-stack.md) — Gate: `python3 scripts/check-links.py && python3 -m unittest tests.test_docs_budget`
- [ ] `T-5056` ADR-0106 gói `site-cms-ts`: stack chọn, ranh giới (site công khai tĩnh/edge; admin tách đường, chỉ IP/VPN tuỳ chọn), lớp bảo vệ bắt buộc (CSP, CSRF, MFA admin, rate limit đăng nhập, WAF ở chế độ log), phạm vi không làm (đa tenant, thương mại điện tử); ghi `loop decide` (sau: T-5055; files: docs/adr/0106-site-cms-pack.md, docs/adr/README.md, docs/autopilot/DECISIONS.md) — Gate: `python3 scripts/xt.py validate && python3 scripts/check-links.py`
- [ ] `T-5057` starter gói theo `packs/README.md`: `pack.json` (owner, `support_until`, `compat`, `profiles: [static-site, web-app]`, `controls` gồm `UX-VISUAL-001/003`, `FE-RENDER-010/019/020`, `SEC-WEB-007`, `BE-AUTH-013`), landing có token motion + khối reduced-motion, admin thêm/sửa/xoá tin, JSON-LD + sitemap sinh lúc build, lockfile; bộ nghiệm thu chạy từ repo sạch (sau: T-5056; topo: review; exec: deep; files: framework/templates/packs/site-cms-ts/) — Gate: `python3 -m unittest tests.test_packs tests.test_pack`
- [ ] `T-5058` CI nghiệm thu `pack-site-cms.yml` (managed) + `mutants.json` ≥ 1 ca cho mỗi lớp: CSRF, lọc HTML bài viết (XSS), phân quyền admin, MFA admin, reduced-motion, JSON-LD, sitemap; thêm dòng bảng gói, CHANGELOG (sau: T-5057; topo: review; files: .github/workflows/pack-site-cms.yml, framework/templates/packs/site-cms-ts/mutants.json, framework/templates/packs/README.md, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_packs tests.test_pack_ci_setup && python3 scripts/xt.py changelog-check`
- [ ] `T-5059` `install.py --new --pack site-cms-ts` qua test cài (repo sạch, `--plan`, brownfield ra `.xtemplates-new`); `/factory` chọn gói theo hồ sơ (`static-site`/site giới thiệu → `site-cms-ts`, web nghiệp vụ → `web-api-ts`) thay cho mặc định cứng (sau: T-5058; files: tests/test_install_pack.py, .claude/skills/factory/SKILL.md, CHANGELOG.md) — Gate: `python3 -m unittest tests.test_install_pack && python3 scripts/xt.py changelog-check`

### Lát 4 — pilot bằng yêu cầu mẫu
- [ ] `T-5060` pilot ngoài repo khung: `install.py <scratch> --new --pack site-cms-ts --idea "<yêu cầu site giới thiệu>"` → preview dev, `/ui-verify` desktop + mobile, Lighthouse ≥ 0.9 bốn nhóm, thêm/sửa/xoá một tin qua admin, curl kiểm JSON-LD/sitemap/CSP, test CSRF 403; ghi số (thời gian, chỗ vấp, mục N/A của `media-content`) vào `research/` (sau: T-5059; files: research/2026-11-26-site-cms-pilot.md) — Gate: `python3 scripts/check-links.py && python3 -m unittest tests.test_docs_budget`

## Sau PLAN
- Cắt bản minor (CHANGELOG + `VERSION`) sau lát 2 vì thêm ID MUST cho dự án đích; lát 3 cắt bản riêng khi gói qua nghiệm thu CI.
- Gói ngành `media-content` không vừa site công ty (mục UGC, gỡ nội dung): xét ghi chú N/A trong hồ sơ `static-site` sau pilot, không trước.
