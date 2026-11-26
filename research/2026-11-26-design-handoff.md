# Công cụ thiết kế: ghi, duyệt, bàn giao (T-5052)

> Đọc 2026-11-26 từ trang chính thức (subagent `researcher`; trích qua công cụ fetch tóm lược — so lại trang gốc trước khi dẫn nguyên văn). Dùng cho ADR-0106, `UX-DS-023/024`.

## Kết luận dùng cho khung
- **Không có trạng thái "khách đã duyệt" đọc được từ công cụ.** Figma Dev Mode status (`READY_FOR_DEV`, `COMPLETED`) là nhãn ai có quyền đều đặt được, không ghi người duyệt; đọc qua webhook `DEV_MODE_STATUS_UPDATE`, REST không trả (nguồn thứ cấp, chưa đối chiếu OpenAPI). → Bằng chứng duyệt nằm ở sổ của khung (`docs/autopilot/DESIGN.json`).
- **Agent vẽ hộ là tuỳ chọn, không phải mặc định.** Figma MCP ghi canvas được nhưng đang beta, cần seat Full trả phí; Penpot MCP ghi được, tự host. Người thiết kế (designer) vẫn chịu trách nhiệm bản thiết kế.
- **Mặc định tự host khi chưa có công cụ** (AGENTS.md §4): Penpot; khách đã dùng Figma thì giữ Figma.

## Dữ kiện

| # | Câu hỏi | Trả lời | URL |
|---|---|---|---|
| 1 | Figma REST tạo/sửa node? | Không thấy trên trang tổng quan (đọc file/layer; ghi comment, webhook, dev resources, variables) — chưa rà OpenAPI | https://developers.figma.com/docs/rest-api/ |
| 2 | Figma Variables API ghi | `POST /v1/files/:file_key/variables`, chỉ full member org **Enterprise** | https://developers.figma.com/docs/rest-api/variables-endpoints/ |
| 3 | Figma Plugin API | Tạo/sửa node trong file đang mở; không chạy nền | https://developers.figma.com/docs/plugins/ |
| 4 | Figma MCP | Đọc + ghi canvas (beta, miễn phí trong beta, sau tính theo mức dùng); seat Dev/Full gói Professional trở lên; ngày GA chưa xác minh | https://developers.figma.com/docs/figma-mcp-server/ |
| 5 | Figma chuyển quyền file/folder | Chủ hiện tại chuyển cho cộng tác viên; chuyển folder không đổi chủ file bên trong | https://help.figma.com/hc/en-us/articles/360038512093-Transfer-ownership-of-files-or-folders |
| 6 | Figma chuyển folder/team sang tổ chức khác | Chỉ admin; bên nhận folder: Professional trở lên, team: Organization/Enterprise…; gói Starter (miễn phí) không nhận — lưu bản local rồi import (mất branch, comment, lịch sử phiên bản) | https://help.figma.com/hc/en-us/articles/10250387712407-Transfer-a-project-or-team-to-a-different-account |
| 7 | Figma Dev Mode status | Có trên Professional trở lên; "Completed" chỉ Organization/Enterprise…; không có người duyệt riêng | https://help.figma.com/hc/en-us/articles/26781702258583-Dev-Mode-statuses-and-notifications |
| 8 | Penpot license, bản ổn định | MPL-2.0; 2.19.5 (2026-11-24) — phát hành dày, ghim `PENPOT_VERSION` | https://github.com/penpot/penpot · https://api.github.com/repos/penpot/penpot/releases/latest |
| 9 | Penpot tự host | Docker Compose chính thức, cổng 9001, HTTPS qua reverse proxy, nâng cấp từng bước nhỏ | https://help.penpot.app/technical-guide/getting-started/docker/ |
| 10 | Penpot MCP | Đọc + ghi trang đang mở; local MCP cần Node; nhãn beta/GA chưa xác minh | https://help.penpot.app/mcp/ |
| 11 | Penpot design tokens | Import/export JSON theo Design Tokens Format Module; bản spec DTCG theo bản Penpot nào chưa xác minh | https://help.penpot.app/user-guide/design-systems/design-tokens/ |
| 12 | Penpot chuyển quyền | Owner team chuyển cho thành viên khác bất kỳ lúc nào | https://help.penpot.app/user-guide/teams/ |
| 13 | Penpot xuất file bàn giao | `.penpot` (v1) và `.zip` (v2) ghi deprecated cho xuất (chỉ ≤ 2.3), import mọi bản — định dạng xuất ở 2.19.x chưa xác minh | https://help.penpot.app/user-guide/export-import/export-import-files/ |
| 14 | DTCG | Bản ổn định đầu tiên 2025.10 (ngày 2025-10-28 suy từ URL thông báo) | https://www.designtokens.org/TR/2025.10/format/ |

## Chưa xác minh
Ngày GA ghi canvas của Figma MCP; REST có trả Dev Mode status không (chỉ nguồn thứ cấp); người nhận file Figma có cần seat trả phí không; branching review của Figma; định dạng xuất Penpot 2.19.x; telemetry mặc định của Penpot.
