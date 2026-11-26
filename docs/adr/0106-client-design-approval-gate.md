# ADR-0106: Chào giá trước G0 và cổng khách duyệt thiết kế do máy khoá

- **Trạng thái:** Đã chấp nhận ngày 2026-11-26 (D-619; chủ dự án duyệt quy trình "chào giá → G0–G3 → G4 thiết kế → khách duyệt (bắt buộc dừng) → G5–G8 → bàn giao").
- **Trạng thái triển khai:** đã triển khai cùng PR với ADR này — tài liệu (`PM-PLAN-019`, `UX-DS-023/024`, mẫu `PROPOSAL.md`/`DESIGN-REVIEW.md`) và máy khoá (`scripts/xt_design.py`, `xt.py stage design-*`, khoá `loop next/record` và `plan waves`, test `tests/test_design_gate.py`).
- **Liên quan:** [ADR-0058](0058-product-stages-machine-lock.md) (sổ giai đoạn, hai lớp chặn nhầm), [ADR-0069](0069-agent-stage-approval.md), [ADR-0092](0092-raise-caps-10x.md) (nới trần chỉ bằng ADR); [PLAN-site-cms](../autopilot/PLAN-site-cms-2026-11-26.md) lát 2; [nghiên cứu](../../research/2026-11-26-design-handoff.md).

## Bối cảnh

Đối chiếu khung với một lời mời làm site giới thiệu công ty (Figma Desktop/Mobile, bàn giao file thiết kế) cho thấy hai lỗ của quy trình khi dự án làm **cho khách**:

1. Không có bước trước G0: lời mời đòi portfolio, công nghệ, báo giá, tiến độ — chưa phải sản phẩm. `/factory` nhận ý tưởng là bắt đầu viết SPEC và code.
2. G4 chỉ đòi "wireframe/tokens" và phiên chính tự duyệt (ADR-0008). Giai đoạn 1 của `/factory` viết SPEC rồi code UI ngay, không chờ khách duyệt thiết kế.

Dữ kiện (đọc 2026-11-26, chi tiết ở nghiên cứu): Figma REST không có trạng thái "đã duyệt" đọc được — Dev Mode status (`READY_FOR_DEV`, `COMPLETED`) là nhãn ai có quyền cũng đặt, không ghi người duyệt, đọc qua webhook chứ không qua REST; ghi canvas qua MCP của Figma còn beta và cần seat trả phí. Penpot (MPL-2.0, tự host, 2.19.5) có MCP ghi được. Vậy bằng chứng "khách đã duyệt" phải nằm ở sổ của khung, và công cụ thiết kế chỉ là nơi chứa bản thiết kế.

## Quyết định

1. **Trước G0 — chào giá** (dự án làm cho khách): đầu ra `PROPOSAL.md` theo mẫu `framework/templates/PROPOSAL.md` (hiểu yêu cầu, phạm vi và ngoài phạm vi, giả định, công nghệ từ blueprint ghép thử, tiến độ theo cổng G, ước lượng có khoảng, rủi ro, các điểm khách duyệt). Không thiết kế, không code trước khi khách chấp nhận. Mục `PM-PLAN-019`.
2. **Khai báo:** `PROJECT.md` có dòng `Duyệt thiết kế: khách` (hoặc `không`, mặc định khi vắng). Máy nhận dòng theo nhãn (bỏ dấu markdown đầu dòng, ký tự vô hình, khác biệt hoa thường/khoảng trắng) và lấy chữ đầu sau `:` — chỉ `không` là không khoá; giá trị khác, rỗng, hay nhiều dòng mâu thuẫn đều coi là `khách` (cách hiểu chặt hơn). Siết sau review: dòng mở đầu bằng nhãn mà không tách giá trị bằng `:`/`|` (`- Duyệt thiết kế - khách`, nhãn kèm ngoặc hay link, tiêu đề `## Duyệt thiết kế`) và giá trị `không` có kèm chữ `khách` (không phân biệt hoa thường/dấu: `không → khách`, `~~không~~ khách`) đều là `khách` kèm ghi chú; dòng khai trong comment HTML (một hay nhiều dòng) vẫn tính; code fence chỉ được giấu dòng có giá trị `không` (ví dụ trong rào); dòng trong code fence có giá trị khác `không` vẫn tính là khai kèm ghi chú "trong code fence vẫn tính" — nhờ vậy đọc sai ranh giới rào (rào không đóng, rào trong mục danh sách hay comment, `<pre>`) chỉ đổi ghi chú, không bao giờ nới khoá; dòng chỉ tách ở `\r\n`, `\r`, `\n`. Mục `UX-DS-023`.
3. **Sổ** `docs/autopilot/DESIGN.json` (`schema: 1`, theo git, chỉ `xt.py stage design-*`/`stage approve --design` ghi): `status` `none|awaiting_approval|approved`, `submitted` (SHA + đường bằng chứng), `history` (`submit` · `reopen` · `approve`) phát lại đúng thứ tự như sổ giai đoạn. Guard coi là sổ bằng chứng (thêm vào `EVIDENCE_LEDGERS`): ghi tay bị chặn.
4. **Lệnh:** `stage design-submit --evidence <tệp>` (agent; HEAD cây sạch; máy chỉ đòi tệp bằng chứng là tệp thường trong dự án, đã commit ở HEAD — không kiểm nội dung; mẫu `DESIGN-REVIEW.md` là hướng dẫn cho người: link bản thiết kế, phiên bản, danh sách màn hình × Desktop/Mobile khớp SPEC) · `stage design-reopen --reason` (khách đòi sửa) · `stage approve --design --sha <≥7 ký tự> --note` (**luôn chỉ người**, kể cả khi `stage_approval: agent`: guard chặn mọi `stage approve` có cờ ngoài `--sha/--note` — đã thử bằng payload 2026-11-26; `xt.py` từ chối phiên agent) · `stage design-check` (exit 0 khi bản trình mới nhất đã duyệt hoặc dự án không khai `khách`).
5. **Khoá:** khi khai `khách`, `loop next` không đưa ra, `plan waves` (có hay không `--handoff`) chuyển vào `blocked` (như task defer, lan sang task `sau:` nó) và `loop record` từ chối task gắn `(ui: yes)` tới khi bản thiết kế mới nhất `approved` (`loop record` khi đang khoá mà PLAN của vòng không đọc được → từ chối); trình bản mới (`design-submit` sau `approve`) khoá lại. Câu báo khoá gợi ý `loop defer` khi vòng đã có PLAN, chưa `loop init` thì gợi ý `loop init --plan <PLAN>`. Máy tin thẻ `ui` tự khai — review là lớp kiểm phạm vi (như ADR-0058 với dòng giai đoạn).
6. **Bàn giao file thiết kế:** chuyển quyền sở hữu bằng cơ chế của công cụ (Figma: owner transfer file/folder, chuyển folder/team sang tổ chức khác cần gói trả phí bên nhận; Penpot: chuyển owner của team) — `UX-DS-024`, trỏ `PM-HANDOVER-004`.
7. **Trần dòng:** logic ở module mới `scripts/xt_design.py`; `xt.py` chỉ nối lệnh và khoá. Nâng `LINE_CAPS` của `scripts/xt.py` đúng số dòng đo sau lát B (23.667), rồi 23.668 khi `plan waves` không `--handoff` cũng giữ task giao diện; `guard.py` không đổi số dòng.

## Phương án đã xét

- Gắn sự kiện thiết kế vào `STAGE.json`: phải sửa bộ phát lại lịch sử, và `stage_approval: agent` sẽ cho agent tự duyệt thiết kế — trái bản chất "khách duyệt". Loại.
- Chỉ tài liệu + `loop defer`: agent tự viết được tệp duyệt; trái P1. Loại.
- Đọc trạng thái duyệt từ Figma: không có API trạng thái duyệt có người ký; khoá cứng vào một công cụ trả phí. Loại.

## Hệ quả

- Tốt: dự án làm cho khách dừng đúng chỗ — agent không code UI khi khách chưa duyệt; bằng chứng duyệt có người, SHA bản trình và lịch sử sửa. Dự án không khai không đổi gì.
- Xấu: chủ dự án phải chạy một lệnh ngoài phiên agent để ghi lời duyệt của khách (như ADR-0058); `by` là cấu hình git tự khai, không phải chữ ký của khách — lời duyệt gốc (email, comment) dẫn trong `--note`. Thẻ `ui` tự khai. Nới trần dòng `xt.py` lần sau vẫn cần ADR riêng.

### Giới hạn đã biết (việc sau, chưa có mã)

- **Guard chưa nhận `import xt_design`:** luật chặn script trình thông dịch nạp `xt` trong tiến trình (AUD-SEC-498) bắt `import xt`, chưa bắt script `import xt_design` rồi gọi `update`/`approve` — mở rộng luật guard ở việc riêng.
- **Dòng khai chỉ đọc ở cây làm việc:** sửa `PROJECT.md` thành `không` sau khi đã trình bản thiết kế là nới khoá được. Khuyến nghị cho việc sau: coi như `khách` khi `DESIGN.json` đã có lịch sử (dự án từng trình thì không tự rút khai báo).
- **Dòng khai đọc theo nhãn có dấu, neo đầu dòng:** các dạng sau đang ra `không` (không khoá) — nhãn bỏ dấu (`- Duyet thiet ke: khach`), nhãn không mở đầu dòng (`- Khách duyệt thiết kế: có`, `- G4 — Duyệt thiết kế: khách`, `<!-- x --> Duyệt thiết kế: khách`), bảng nhiều cột có nhãn ở cột sau (`| G4 | Duyệt thiết kế | khách |`), `không` kèm giá trị thay thế không phải chữ `khách` (`không → có`, `không / có`), và `không` kèm từ đồng nghĩa thay chữ `khách` (`không — đối tác duyệt`, `không — client duyệt`). Bắt các dạng này cần tìm nhãn trên chữ bỏ dấu ở mọi vị trí, dễ chặn oan dòng giải thích — thiết kế ở việc riêng.
- **"Luôn chỉ người" trong phạm vi D-015:** guard và từ chối phiên agent ở `xt.py` là lớp chặn nhầm của agent làm đúng quy trình, không phải cách ly agent cố ý vượt rào — cùng phạm vi với sổ giai đoạn (ADR-0058).
