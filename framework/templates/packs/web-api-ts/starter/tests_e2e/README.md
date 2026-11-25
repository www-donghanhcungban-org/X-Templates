---
title: Kiểm thử bản dev của dự án bằng trình duyệt
kind: index
updated: 2026-11-25
---

# Kiểm thử bản dev

Từ gốc repo với mã đã commit, chạy lệnh sau trên Linux x86_64 có CPython 3.15, Node 24 và Docker Compose v2. Lần đầu cần mạng để tải phụ thuộc, Chromium và image. Cổng 4317 trên loopback cần trống hoặc thuộc bản dev hiện tại của dự án.

```bash
bash tests_e2e/preview.sh
```

Lệnh tạo venv tạm, dựng artifact, triển khai ứng dụng và PostgreSQL, rồi mở Chromium. Bài kiểm trong `tests_e2e/pack_preview.py` đăng nhập, tạo ghi chú và đọc lại đúng ID qua một phiên trình duyệt mới. Khi đạt, kết quả nằm ở `dist/preview-browser.json`, kèm digest để đối chiếu với `docs/ops/DEPLOYS.json`. Tham số `--output FILE` đổi nơi lưu. Khi chạy lại, lệnh lưu bản kết quả trước ở file có đuôi `.previous.*`.

Mở <http://127.0.0.1:4317/> sau khi kiểm thử để dùng bản dev. Chạy `node scripts/dev-preview.mjs credentials` ở terminal riêng để xem tài khoản và `node scripts/dev-preview.mjs stop` để dừng dịch vụ.

Workflow `.github/workflows/dev-preview.yml` gọi cùng lệnh trên pull request và cho phép chạy thủ công bằng **Actions → dev-preview → Run workflow**. Artifact `dev-preview-evidence` chứa kết quả browser và receipt. Để chỉ chạy thủ công, bỏ sự kiện `pull_request` trong workflow của dự án.


## Ma trận giao diện của starter

Repo khung chạy `python3 tests_e2e/pack_ui.py` sau khi cài Playwright theo tệp khoá và khởi chạy Chromium bằng `prepare-chromium.sh`. Runner dựng starter trong thư mục tạm, kiểm [cặp tương phản](../src/notes-ui/contrast-pairs.txt) và mở UI ở 1280, 390, 320 CSS px. Chromium đi hết các bước bằng bàn phím. Bản kiểm lưu ảnh và kết quả axe của trang đăng nhập, đang tải, rỗng, lỗi và lưu thành công. Hai đối chứng cố ý gây tràn ngang ở 320 px và xóa nhãn trường email.

Trên starter đã scaffold, `python3 tests_e2e/pack_preview.py --ui-matrix THU_MUC_MOI --axe TEP_AXE_DA_GHIM` chạy ma trận trên HTML/CSS/JS của starter với phản hồi API xác định. Lệnh `--output FILE` ở trên vẫn chạy trên bản dev đã triển khai thật và ghi biên nhận riêng.
