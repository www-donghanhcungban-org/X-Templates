---
title: Đề xuất từ stored PR 186 — nâng trần các nhóm còn lại, XT-H-159…161
kind: research
updated: 2026-11-23
---

# Đề xuất từ stored: egress mặc định của khoá API, cổng duyệt và log bất biến phải kiểm hành vi, license open-core theo thư mục

Bổ sung cho [đợt 18/11](2026-11-18-stored-delta-nov-18.md). Nguồn là ba bàn giao XT-H-159…161 trong catalog stored (đợt nâng trần các nhóm còn lại, mốc 2.450 hồ sơ). Các quan sát lấy từ **đọc mã tại commit cố định, chưa chạy**; ví dụ nào chưa kiểm lại thì còn là "chưa xác minh". Đề xuất này **không cấp ID mới** và không đổi mức: chỉ thêm vế kiểm và ví dụ vào ID hiện có.

## 1. Đối chiếu với khung hiện hành (commit `4282d65`)

| Bàn giao | ID hiện có | Đã bao phủ | Phần bổ sung |
|---|---|---|---|
| XT-H-159 | `SEC-INFRA-027` (bổ sung `SEC-INFRA-018`) | Đã yêu cầu bảng công tắc kèm cột "endpoint mặc định khi chưa có khoá" và chặn egress | Thêm ví dụ `autoevals` (gateway mặc định khi không đặt `OPENAI_BASE_URL`) và vế đặt biến đích tường minh trong CI |
| XT-H-160 | `AI-AGENTIC-008`, `CMP-AUDIT-002` | HITL `waiting_approval` và audit append-only đã có | Vế kiểm hành vi: đi vòng không qua prompt phải bị chặn; thử UPDATE/DELETE bảng audit bằng vai trò ứng dụng phải bị từ chối |
| XT-H-161 | `CMP-LIC-004` | Đã yêu cầu đọc LICENSE theo từng thư mục cho skill/prompt pack | Mở sang thư viện/ứng dụng open-core: thư mục `ee/`, header Enterprise, license kép |

## 2. Quan sát từ stored (đọc mã, chưa chạy)

- **XT-H-159:** `autoevals` gọi Braintrust Gateway khi chưa đặt `OPENAI_BASE_URL`, nên khoá OpenAI có thể đi qua gateway bên thứ ba.
- **XT-H-160:** cổng phê duyệt của OpenAgents Control là quy tắc trong prompt; chỉnh sửa khi duyệt ở Workflow Builder được lưu nhưng chưa áp vào bước sau; OpenMES tuyên bố audit log do PostgreSQL cưỡng chế nhưng migration không có trigger hay REVOKE.
- **XT-H-161:** Carbon giữ `packages/ee` theo giấy phép thương mại; Archestra có nhiều file backend mang header Enterprise; OpenMES có AGPL kèm AFL ở `modules` và giấy phép thương mại song song.

## 3. Thay đổi trong PR này

Chỉ sửa chữ, thêm ví dụ và vế kiểm vào bốn ID: `SEC-INFRA-027`, `CMP-LIC-004`, `CMP-AUDIT-002`, `AI-AGENTIC-008`. Không đổi mức, không thêm ID, không đổi công cụ.

## 4. Giới hạn

- Chưa chạy thử vế kiểm mới trong dự án đích; "kiểm" là thiết kế.
- Các ví dụ là quan sát đọc mã ở một commit của từng repo; license và hành vi có thể đã đổi.
- Số liệu hồ sơ stored (2.450) và thông tin từng repo do phía stored ghi; chưa đọc lại nguồn upstream trong phiên này.
