---
title: Đối chiếu stored XT-H-163 — khối hướng dẫn agent do công cụ sinh và MCP tài liệu của design system Astryx
kind: research
updated: 2026-11-24
---

# Đối chiếu XT-H-163 với khung (commit `8201df2`)

Bổ sung cho [đợt 24/11](2026-11-24-stored-delta-xt-h-113-162.md). Bàn giao này đến từ hồ sơ `meta/astryx` ở catalog stored (mục 06 §7zh, đọc mã commit `72d06aa618b001c09970756b19890bb157be100d`, 24/11/2026). Quan sát về Astryx là **đọc mã ở một commit, chưa chạy**; hiệu quả với agent chưa có số đo công khai. Đây là đề xuất: không sửa `framework/` trong PR này.

## 1. Quan sát

- `astryx init` ghi một khối hướng dẫn vào `AGENTS.md`/`CLAUDE.md`, bọc bằng cặp đánh dấu `ASTRYX:START`/`ASTRYX:END` kèm sha256; plugin skill bảo agent chạy `astryx build` rồi `astryx template` trước khi viết trang.
- Máy chủ MCP có hai dạng: `astryx mcp` chạy cục bộ theo bản của dự án; bản host `--docs-only` do trang docs chạy, trả lời theo bản đã công bố (không theo bản dự án) và không nhận đầu vào nêu thư mục, file hay gói.
- CI của repo gọi `check:agent-plugin-skill` và `check:setup-contract` ở chế độ `--check`: văn bản hướng dẫn sinh ra phải khớp nguồn trong repo, nếu lệch thì CI đỏ.
- Kiểm lại độc lập ở stored: không thấy SDK đo lường trong CLI; `postinstall` chỉ in lời nhắc, không gọi mạng, không làm hỏng cài đặt.

## 2. Kết quả đối chiếu

| Control đã đọc | Kết luận | Xử lý đề xuất |
|---|---|---|
| `XC-DOCAI-028` | Đã đòi manifest phiên bản + sha256, chạy lại là no-op, không ghi đè mục người dùng sửa, `--check` cho CI. Thiếu: kiểm văn bản do **công cụ của chính dự án sinh ra** so với nguồn trong repo | Thêm một vế (shallower) |
| `XC-DOCAI-016` | Đã đòi MCP tài liệu read-only, ít tool. Thiếu: nói rõ bản đặt trên máy chủ chung trả theo bản công bố và không nhận tham số đường dẫn | Thêm một vế (shallower) |
| `XC-DOCAI-014` | Đã đòi quy tắc kiểm được thành cổng | Không sửa |
| `UX-DS-001` | Đã kiểm đầu ra sinh của token (`diff = 0`); không phủ văn bản hướng dẫn | Không sửa, dẫn chéo từ vế mới |
| `UX-DS-019` | Phủ việc dùng component của design system; không liên quan phần sinh văn bản | Không sửa |

## 3. Đề xuất

- **`XC-DOCAI-028` (SHOULD, không đổi mức):** dự án phát hành CLI/plugin sinh khối hướng dẫn cho agent có lệnh sinh kèm `--check` chạy trong CI và đỏ khi văn bản đã commit lệch nguồn; khối ghi vào repo người dùng có đánh dấu bắt đầu/kết thúc và băm để cập nhật không đè phần người dùng viết ngoài khối. Kiểm: sửa một dòng trong khối sinh rồi chạy `--check` thoát khác 0; chạy `init` hai lần, cây không đổi.
- **`XC-DOCAI-016` (MAY, không đổi mức):** MCP tài liệu đặt trên máy chủ chung ghi rõ nó trả lời theo bản đã công bố, không theo bản dự án đang dùng, và không nhận tham số tên thư mục, file hay gói. Kiểm: gọi tool với đường dẫn bị từ chối.

## 4. Giới hạn

- Ví dụ Astryx là đọc mã, chưa chạy `init`, chưa gọi MCP host, chưa chạy `--check`.
- Đối chiếu là đọc nguyên văn control, không phải chạy kiểm; chưa thử vế mới trên một dự án đích thật.
- Nguồn: [hồ sơ stored](https://github.com/www-donghanhcungban-org/stored/blob/main/06-ui-ux-design/README.md) (neo `ch-astryx-meta` và §7zh), [`meta/astryx` ở commit đã đọc](https://github.com/meta/astryx/tree/72d06aa618b001c09970756b19890bb157be100d).
