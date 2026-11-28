# Hậu kiểm AUD-HAR-568

Ngày 28/11/2026, trên main `2ee23a8c5f0781c13bc5320b9da13629f0508583`. Node 24.21.0, Chromium 159 và phụ thuộc cài bằng lockfile của cây này. `node --test tests_e2e/verify_render.test.mjs` trả 0, đạt 30/30.

| Mục | Bằng chứng sau sửa |
| --- | --- |
| AUD-HAR-558 | Fixture shadow root và nội dung gán qua slot báo tương phản thấp, đo theo nền của host hoặc cây hiển thị tương ứng. |
| AUD-HAR-559 | Fixture chữ con và pseudo có màu khác báo vi phạm. Ca opacity, text-fill và pseudo phủ nền được phân loại theo khả năng đo. |
| AUD-HAR-560 | Fixture iframe báo tương phản thấp qua định danh `frame[1]`. |
| AUD-HAR-561 | Chữ vắt qua mép cắt ngang trong phạm vi đo ở khổ hẹp là vi phạm. Chữ nằm hẳn ngoài khung hoặc hình học chưa chắc chắn là `UNMEASURED`. Ca ellipsis có chủ ý vẫn đạt. [Phạm vi đo](../../framework/templates/ui-gates/README.md). |
| AUD-HAR-566 | [Quality của #818](https://github.com/www-donghanhcungban-org/X-Templates/actions/runs/45721154341/job/139585432601) đạt trên head `b41d5fa1`, merge tại `9f7637d3`. Đây là bằng chứng CI lưu từ PR. |

## Đính chính số dòng

- [ADR-0103](../adr/0103-guard-line-ceiling-for-tag-glob.md) ghi +10 ở tiêu đề. Nội dung quyết định và diff #815 xác nhận +19 (24.645 → 24.664). `git show --numstat f9cff60a -- .claude/hooks/guard.py` cho +22/−3.
- [D-607](../autopilot/DECISIONS.md) ghi +8. [ADR-0104](../adr/0104-guard-line-ceiling-for-glob-only-tags.md) và diff #818 xác nhận +25 (24.664 → 24.689). `git show --numstat 9f7637d3 -- .claude/hooks/guard.py` cho +35/−10.
