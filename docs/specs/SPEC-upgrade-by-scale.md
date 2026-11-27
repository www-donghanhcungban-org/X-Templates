# X-Templates · Đặc tả kỹ thuật triển khai theo quy mô dự án

**Đặc tả đề xuất · Phiên bản 1.0 · 27/11/2026.** Dành cho người duy trì Core, người viết pack, người nghiệm thu và chủ dự án. Đường cơ sở kỹ thuật là commit `6adbd4ad`. Các giao diện ghi “đề xuất” là hợp đồng để triển khai và kiểm thử. [Mốc mã nguồn](https://github.com/www-donghanhcungban-org/X-Templates/commit/6adbd4ade5a2a4188c6c3404740f1913e40ea60d)

Đặc tả có 10 phần và định nghĩa 34 ca nghiệm thu. Người mở PR đối chiếu các gói công việc trong kế hoạch tích hợp với lịch đã duyệt của repo. Người thiết kế và vận hành trang quản trị dùng kế hoạch quản trị để chọn tác vụ, phân quyền và nghiệm thu. [Kế hoạch tích hợp](../autopilot/PLAN-integrated-upgrade-2026-11-27.md) · [Kế hoạch quy trình quản trị](../autopilot/PLAN-admin-workflows-2026-11-27.md)

Kết quả cần bàn giao là một luồng người khác có thể chạy lại: phân loại một dự án, tạo hoặc ghép blueprint, nâng một repo có tùy biến, kiểm một tác vụ sản phẩm và quyết định phát hành đúng bản đã kiểm. Đội nhỏ dùng cùng công cụ với đội lớn. Khối lượng kiểm và người chịu trách nhiệm thay đổi theo rủi ro của bản bàn giao.

## 1. Phạm vi triển khai và hành vi hiện có

| Người dùng | Quyết định hoặc hành động | Bằng chứng bàn giao |
|---|---|---|
| Chủ sản phẩm | Xác nhận người dùng, dữ liệu, rủi ro, phạm vi thử và ai chịu trách nhiệm vận hành. | Hồ sơ phân loại, lý do chọn mức và điều kiện phải xét lại. |
| Kỹ sư tiếp nhận | Tạo dự án đúng loại hoặc ghép khung vào repo có sẵn; đọc diff rồi chạy lại đúng kế hoạch nâng. | Blueprint, bản ghi cài đặt và biên nhận gắn với bản phân phối. |
| Chủ pack và QA độc lập | Dựng các luồng web/CMS; QA nhận hợp đồng, dữ liệu mẫu và bản cài để thử qua giao diện người dùng thực sự dùng. | Kết quả ca tốt/xấu, phiên bản client/server, ảnh hoặc bản ghi khi cần, quyết định sửa hay đạt. |
| Chủ vận hành/phát hành | Xác minh bản ký, đối tượng triển khai, cách phục hồi và phạm vi quyền. | Quyết định G7, biên nhận triển khai và xác nhận của người có thẩm quyền cho phần việc tương ứng. |

**Điểm nối với repo.** Factory intake đã tạo `PROJECT.md`; `compose` đã có S/M/L và giữ trạng thái theo ID. Installer có `--plan` schema 1. Pack thực thi hiện có là `web-api-ts`. Stack của `site-cms-ts` đã được chọn theo ADR-0109. Các PR chỉ bổ sung phần sai khác mô tả dưới đây, dùng lại mã, PLAN và SPEC gốc. [Factory intake](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/specs/SPEC-factory-intake.md) · [Quy tắc ghép](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/framework/00-method/composition.md) · [ADR về CMS](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/adr/0109-site-cms-ts-pack.md)

**Phạm vi nghiệm thu đợt đầu.** Dùng fixture cách ly, dữ liệu giả, Linux cho tuyến installer và tổ hợp được manifest pack hỗ trợ. Một bản cài chạy được, một lần ký cho ứng viên, một lần deploy dev và một lần nghiệm thu sản xuất là bốn sự kiện, mỗi sự kiện phải có bằng chứng riêng. D-610 giữ việc nâng dự án đích thật theo quyết định của chủ dự án. [Phạm vi và lịch chính thức](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/research/2026-11-26-unified-upgrade-plan.md#L73-L120)

## 2. Phân loại dự án và giao ước với factory

### 2.1 Hồ sơ đầu vào

Ghi một khối JSON dưới mục “Cấu hình ghép blueprint” trong `PROJECT.md` cho mỗi đơn vị phát hành. Factory và người vận hành đọc cùng khối này, cập nhật đúng khối của đơn vị và giữ ghi chú của chủ dự án. Repo cũ chưa có khối vẫn ghép được bằng CLI hiện hành. Lần tiếp nhận đầu, factory lấy profile/ngành/tính năng từ blueprint cũ nếu đọc được, trình diff để chủ sở hữu xác nhận trước khi thay. Các giá trị `null` trong mẫu dành cho dữ kiện chưa xác minh, trừ lựa chọn dùng Core được ghi bằng `pack: null`. Bàn giao live chỉ tiến khi các dữ kiện ảnh hưởng mức hoặc quyền đã được xác nhận.

| Nhóm trường | Kiểu và giá trị | Quy tắc |
|---|---|---|
| Danh tính | `schema=1`, `unit`, `owner`, `review_on` là mô tả sự kiện xét lại | Tên đơn vị ổn định trong dự án; ghi người hoặc nhóm thực sự nhận trách nhiệm. |
| Yêu cầu | `profile` là một ID có trong khung; `industries` và `features` là mảng ID; `pack` là ID hoặc null | Kiểm ID theo danh mục tại phiên bản ghim. Chuẩn hóa danh sách theo thứ tự ổn định và bỏ trùng. Pack phải tương thích với stack và host để chạy. |
| Rủi ro | `use` = sandbox/live, `data_class` = synthetic/operational/sensitive, `money`, `multi_team`, `contract_sla`, `external_audit` là boolean hoặc null | Null nghĩa là cần xác minh. Có thể dựng mẫu với dữ liệu giả; để phát hành cần có kết luận cho mọi giá trị ảnh hưởng mức hoặc quyền. |
| Quyết định | `scale` = S/M/L, `reason` là chuỗi không rỗng | Lưu lý do chọn mức. Dùng một quyết định mới khi dữ liệu, người dùng hoặc phạm vi ảnh hưởng thay đổi. |
| Quản trị | `admin` vắng, `null` hoặc đối tượng theo [mẫu PROJECT](../../framework/templates/PROJECT.md) | Vắng hoặc `null` là chưa khảo sát. Nếu khảo sát cho thấy không có tác vụ quản trị, ghi lý do trong phạm vi. Kết quả chọn công cụ hoặc pack được ghi trong hồ sơ, quyền được cấp qua quy trình hiện hành. |

Ví dụ hợp lệ của một đơn vị sắp phục vụ nhân viên nội bộ:

```json
{
  "schema": 1, "unit": "notes-web", "owner": "nhom-van-hanh",
  "review_on": "thêm thanh toán hoặc đội thứ hai",
  "profile": "web-app", "industries": [], "features": ["auth"],
  "pack": "web-api-ts", "use": "live", "data_class": "operational",
  "money": false, "multi_team": false, "contract_sla": false,
  "external_audit": false, "scale": "M",
  "reason": "nhân viên ngoài nhóm phát triển sẽ dùng"
}
```

### 2.2 Quyết định, ghép lại và xử lý sai lệch

Thứ tự đánh giá: nhiều đội cùng phát triển, SLA ký hoặc kiểm toán ngoài → L; xử lý tiền thật hoặc dữ liệu nhạy cảm → khuyến nghị L, cho phép M kèm đúng gói ngành khi có lý do, chủ rủi ro và bằng chứng; có người dùng thật ngoài nhóm phát triển → ít nhất M; thử nghiệm với dữ liệu giả và phạm vi cục bộ → S. Lấy mức cao nhất trong các điều kiện áp dụng. Đề xuất lưu thêm tham chiếu quyết định nếu chọn ngoại lệ M. Tách mức của thành phần khỏi mức của toàn hệ thống có phụ thuộc liên đội. [Hướng dẫn chọn mức](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/framework/00-method/composition.md#L65-L77)

Trong repo mới, dùng `--new --pack … --idea … --scale …` khi có pack phù hợp. Bootstrap hiện lấy profile đầu của pack. Sau bootstrap, factory gọi lại `compose` với **đủ** profile, industry, feature và scale của hồ sơ. Khi stack chưa có pack phù hợp, cài Core rồi ghép profile; danh mục chỉ được ghi hỗ trợ chạy sau khi có bằng chứng. Trong repo cũ, hiện diff trước khi ghi blueprint. Giữ cách gọi CLI trực tiếp để đội tiếp nhận vẫn dùng được khung khi factory vắng mặt. [Đường bootstrap](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/scripts/install.py#L2990-L3020) · [Factory](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/.claude/skills/factory/SKILL.md)

Factory so bộ cờ sắp dùng với hồ sơ trước khi ghi. Khi tiếp nhận hoặc đổi cách ghép, sao chép blueprint và backlog sang thư mục tạm với nguyên tên tệp, ghép lại vào bản tạm, rồi so theo ID. Nếu mất ngành, mất feature hoặc giảm mức, hiển thị các ID đổi mức và lưu lý do đã duyệt trước khi ghép vào đường dẫn cũ. Đây là bước của factory, còn `compose` trực tiếp phát cảnh báo khi bỏ feature. Ở S, feature chưa nâng mục chuyên sâu lên MUST. Ở M, chỉ các mục đã được ánh xạ mới nâng. Quyền ký phát hành và trần quyền agent được xét tại các cổng hiện hành. [Quy tắc feature](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/adr/0030-essential-items-not-capped-at-m.md#L31-L51) · [Quyền ký theo quy mô](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/specs/SPEC-factory-scale.md#L16-L42)

| Ca chấp nhận | Thao tác | Kết quả quan sát |
|---|---|---|
| SCL-01 | Ghép CLI dùng dữ liệu giả, sau đó ghép lại cùng tham số. | Chọn S, nội dung có hiệu lực ổn định; dự án không cần pack để tạo blueprint. |
| SCL-02 | Dự án web chuyển tới người dùng thật; ghép M kèm auth và cùng đường dẫn đầu ra. | ID `BE-AUTH-003` chuyển từ backlog đến MUST; dấu tick và ghi chú của fixture còn nguyên. Kiểm lại bằng chứng trên bản phát hành mới. |
| SCL-03 | Chạy lại factory mà tham số thiếu auth, trong khi hồ sơ vẫn ghi có đăng nhập. | Phát hiện sai khác trước khi ghi. Bản xem trước chỉ rõ ID sẽ hạ mức. |
| SCL-04 | Hai đội dùng chung API hoặc có SLA; thử chọn M không đáp ứng luật. | Trả khuyến nghị L kèm lý do. Quá trình ghép không cấp thêm quyền ký hay deploy. |
| SCL-05 | Repo đang chạy thiếu khối JSON, hoặc hồ sơ có thông tin quan trọng chưa biết. | Giữ nguyên dữ liệu/blueprint cũ, trình phương án tiếp nhận. Bản fixture có thể chạy; bàn giao live ghi còn chờ xác nhận. |

## 3. Hợp đồng lập kế hoạch, áp dụng và phục hồi installer

**Phạm vi đầu tiên** là cài hoặc nâng pack trong thư mục dự án đã tồn tại trên Linux. Plan mô tả những thay đổi được phép. Apply thực hiện chính các thay đổi đó. Recover đưa một lần cài bị gián đoạn về trạng thái có thể xác minh. Chủ installer chịu trách nhiệm mã và tính tương thích. Người kiểm độc lập dựng lại fixture từ hai bản phân phối N và N+1.

### 3.1 Giao diện và tương thích

Lệnh đang có dưới đây in JSON schema 1 ra stdout, giữ nguyên cây đích. `--new` có giao diện riêng, cần `--pack` và `--idea`, giữ output dở khi bootstrap lỗi. Tại mốc đối chiếu, `--new --plan` là tổ hợp không hợp lệ. Bộ cài hiện dùng chung một số hàm quyết định cho starter và managed nhưng tính lại khi ghi. [Plan và đường cài](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/scripts/install.py#L2717-L2837) · [Bootstrap và ràng buộc cờ](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/scripts/install.py#L3057-L3156)

```bash
python3 scripts/install.py ./project --pack web-api-ts --plan
```

**Ba giao diện đề xuất** dưới đây dùng plan schema 2. Đường dẫn `./plans/` nằm ngoài cây đích. Apply và recover lấy lựa chọn pack, preset và harness từ giao dịch. CLI từ chối cờ khai lại các lựa chọn này hoặc kết hợp nhiều chế độ trong một lệnh.

```bash
python3 scripts/install.py ./project --pack web-api-ts --write-plan ./plans/upgrade.json
python3 scripts/install.py ./project --apply-plan ./plans/upgrade.json
python3 scripts/install.py ./project --recover
```

`--write-plan` chỉ ghi tệp được chỉ định. Apply/recover xuất kết quả máy đọc được gồm `state`, `reason`, `plan_digest` và `transaction_id` khi đã mở giao dịch. Exit 0 khi đạt trạng thái cuối đã xác minh, gồm cả `restored` của lệnh recover. Exit 2 khi đầu vào hoặc tiền điều kiện chưa đạt; exit 1 khi gặp lỗi I/O hoặc giao dịch dở cần xử lý. Bên gọi đọc `state` để phân biệt cài thành công với phục hồi bản cũ.

### 3.2 Ràng buộc của plan schema 2

| Nhóm trường bắt buộc | Nội dung và quy tắc |
|---|---|
| Phiên bản và nguồn | `schema`, phiên bản bộ lập kế hoạch, mã pack, digest của archive và nguồn đã xác minh. Xác minh lại bytes của nguồn bằng chính sách tin cậy của bên cài. Mã băm của plan giúp phát hiện thay đổi; quyền chạy đến từ người hoặc tiến trình được ủy quyền. |
| Đích và lựa chọn | Gốc đích chuẩn hóa, trạng thái Git `commit/unborn/not_git` cùng HEAD nếu có, hash manifest cũ và các lựa chọn ảnh hưởng tới file. Ghi cả đường dẫn chưa tồn tại nếu plan dự kiến tạo tại đó. |
| Danh sách thao tác | Mỗi thao tác có ID duy nhất, thứ tự và quan hệ phụ thuộc, loại thao tác trong tập cố định, đường dẫn tương đối, chủ sở hữu, dấu vết trước/sau gồm loại file, mode và SHA-256 nếu có. Danh sách bao gồm cả file đề xuất `.xtemplates-new` và manifest. Mọi byte dự kiến ghi phải suy được từ đầu vào đã khóa. MVP hỗ trợ tạo, thay, đề xuất file bên cạnh và giữ nguyên theo ownership; đổi cây cần có ảnh chụp trước/sau cho toàn bộ cây chịu tác động. |
| Tính digest | SHA-256 trên JSON UTF-8 với khóa sắp tăng, không khoảng trắng phân cách, cấm khóa trùng, số thực và giá trị ngoài schema. Danh sách thao tác có thứ tự xác định. Loại trường `plan_digest` khỏi dữ liệu đem băm; thời điểm thực thi và ID giao dịch nằm trong journal/receipt. |

Sau khi giữ khóa theo đích, apply kiểm schema, nguồn, đích, quyền sở hữu và dấu vết từng đường dẫn. Các thao tác phải khớp tập hành động hợp lệ mà installer có thể suy ra từ nguồn và lựa chọn đã khóa. Kiểm xong mới ghi file dự án. `STALE_PLAN`, `SOURCE_MISMATCH` hoặc `OWNERSHIP_CONFLICT` trả lý do và đường dẫn liên quan. Giữ starter đã bàn giao theo quy ước pack, chỉ nâng managed còn khớp baseline; file được dự án tùy biến dùng cách đề xuất hiện hành. Nếu chính file đề xuất đã bị chỉnh kể từ lúc lập plan, giữ bản đó và yêu cầu lập lại plan. [Quy ước pack](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/framework/templates/packs/README.md#L17-L32)

**Tên trường đề xuất để các đội thống nhất khi viết fixture.** Phong bì gồm `schema, engine_version, source, target, options, operations, plan_digest`. `source` có `pack_id, pack_version, archive_sha256` với phiên bản của pack được định danh bởi bản phân phối nếu pack chưa có version riêng. `target` có `root, git_state, head, manifest_before_sha256`; giá trị vắng phải thể hiện rõ bằng null khi schema cho phép. Mỗi operation có `id, depends_on, kind, path, ownership, before, after`. Ảnh chụp của một đường dẫn có `type`, `mode`, `sha256` phù hợp với loại của nó. Với cây, hash danh mục các đường dẫn tương đối đã sắp thứ tự cùng mode, loại và hash nội dung từng mục; đường dẫn liên kết xử lý theo chính sách installer đã kiểm. Phiên bản đầu phải bác bỏ trước khi ghi các loại chưa được engine hỗ trợ.

Khóa chỉ cho phép một writer trên đích. Nếu đang có giao dịch khác, trả exit 2 với `TARGET_BUSY`; nếu journal còn dở, ưu tiên `RECOVERY_REQUIRED` và giữ nguyên bản sao phục hồi. Receipt commit ghi `transaction_id, plan_digest, archive_sha256, manifest_after_sha256, state, verified_at`. Hai lần gọi lại cùng giao dịch đã commit phải trả cùng `transaction_id`; chỉ xác nhận khi postimage còn đúng.

### 3.3 Trạng thái giao dịch và điểm ngắt

Một đích chỉ có một giao dịch đang ghi. Staging, backup và journal nằm ngoài cây con sắp thay, cùng filesystem với nơi kích hoạt. Trên Linux ghi bền file và thư mục cha liên quan trước khi đánh dấu hoàn tất bước. Giữ khóa tới khi có trạng thái cuối hoặc trả kết quả cần phục hồi; nếu tiến trình chết, lần gọi tiếp theo lấy khóa và đọc journal cũ trước khi nhận giao dịch khác.

| Điểm ngắt | Quy tắc cho recover |
|---|---|
| `prepared`, chưa kích hoạt | Xác minh bản cũ. Hủy staging của giao dịch theo ID, trả `restored`. |
| `applying`, có thể ngắt trước hoặc sau rename | Ghi bền ý định trước từng thay đổi. Đối chiếu hash đích, staging và backup. Mặc định khôi phục theo thứ tự ngược khi chưa có bằng chứng toàn bộ postimage còn đúng. |
| `verifying`, chưa ghi receipt | Nếu mọi file và manifest khớp postimage, hoàn tất kiểm rồi tạo receipt. Khi không đủ điều kiện, quay về backup đã xác minh. |
| Receipt đã ghi, journal chưa chuyển `committed` | Xác minh receipt, manifest và postimage rồi đánh dấu commit. Retry cùng plan trả lại đúng receipt cũ, một hiệu ứng. Chỉ dọn backup sau khi trạng thái cuối đã bền. |
| Đang khôi phục hoặc gặp file khác cả hai dấu vết | Tiếp tục từ bước khôi phục đã ghi. Với file đã thay đổi ngoài giao dịch, giữ file, backup và journal, trả `MANUAL_CONFLICT` cùng danh sách cần đối soát. Dữ liệu nghiệp vụ trong DB có quy trình khôi phục riêng. |

### 3.4 Nghiệm thu và đưa vào sử dụng

| Mã | Fixture và điều kiện đạt |
|---|---|
| INS-01 | Chạy hai dry-run cố định; digest schema 2 bằng nhau, snapshot cây đích giữ nguyên. Lệnh `--plan` schema 1 và luồng `--new` tiếp tục qua test cũ. |
| INS-02 | Thay lần lượt HEAD, nội dung file cùng HEAD, mode hoặc bytes archive. Apply dừng trước lần ghi file dự án và trả đúng lý do. |
| INS-03 | Chạy hai tiến trình cùng đích, ngắt tại từng ranh giới trong bảng trên rồi recover hai lần. Sau cùng cây cũ hoặc cây mới nguyên vẹn, tối đa một receipt commit cho cùng giao dịch. |
| INS-04 | Nâng N→N+1 trên repo đã sửa starter, managed và file đề xuất. Đối chiếu diff theo ownership, thử chỉnh file trong lúc cần phục hồi, kiểm không mất nội dung của người dùng. |
| INS-05 | Cài từ archive thật, bật/tắt các lựa chọn đã hỗ trợ theo fixture và so với đường cài cũ. Với thao tác có tác động chưa thể ghi journal, schema 2 từ chối trước khi ghi và nêu lựa chọn còn thiếu hỗ trợ. |

Giao theo thứ tự bộ sinh plan và kiểm parity, đường apply có khóa, phục hồi từng ranh giới, rồi nghiệm thu từ archive. Giữ phép thử ở `tests/test_install_atomic.py`, `tests/test_install_pack.py`, `tests/test_install_new.py`, `tests/test_install.py` và `tests/test_pack.py`. Chỉ chuyển đường cài mặc định sang engine chung khi đã chứng minh parity hành vi, mã thoát và receipt trong các cấu hình được hỗ trợ.

## 4. Hợp đồng và luồng ghi của web-api-ts

**Kết quả bàn giao.** Người tạo một ghi chú đánh dấu nó đã hoàn tất và biết trạng thái cuối khi trình duyệt mất phản hồi. Bản cài ứng viên phải chạy được với client đang phát hành và client mới. Tại mốc đối chiếu, starter đã có đăng nhập, đọc và tạo ghi chú; `Principal` có `userId`, `tenantId` và bảng `notes` đã lưu `created_by`. Các thay đổi dưới đây là giao ước cho PR mới. [Router và handler hiện hành](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/framework/templates/packs/web-api-ts/starter/src/server.ts#L113-L179) · [Migration bảng notes](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/framework/templates/packs/web-api-ts/starter/src/migrations/0002_notes.ts)

### 4.1 Hợp đồng HTTP và quyền ghi

| Giao diện | Hành vi phải bàn giao |
|---|---|
| `GET /v1/notes/{id}` | Thành công trả 200 và strong ETag của bản biểu diễn, ví dụ `"note-42-r7-f1"` minh họa quy ước. ID thực là UUID. Bổ sung `status` và `version` dạng trường mở rộng. Mọi thay đổi ảnh hưởng dữ liệu trả về phải làm đổi ETag, kể cả khi đổi cách biểu diễn. |
| `PATCH /v1/notes/{id}` | Nhận JSON `{"status":"done"}`, header `If-Match` và `Idempotency-Key`. Chỉ người tạo trong đúng tenant được cập nhật. Thành công trả 200 với receipt gồm `operationId`, `noteId`, `outcome` (`applied` hoặc `no_change`) và `resultVersion`. UI đọc lại GET để lấy trạng thái hiện tại. |
| Tiền điều kiện | Thiếu `If-Match` trả 428. Cú pháp header hỏng trả 400. Với danh sách ETag, áp dụng so sánh mạnh với từng tag; tag yếu đứng một mình không khớp. Khi ý định mới không còn khớp, trả 412. Endpoint yêu cầu biết phiên bản cụ thể; giá trị wildcard `*` hợp lệ trong HTTP, nhưng bị từ chối bằng 422 theo chính sách nghiệp vụ của route này. |
| Quyền và đầu vào | Thiếu hoặc hết phiên trả 401. Ghi chú thuộc tenant khác hoặc không tồn tại trả 404. Thành viên cùng tenant đọc được ghi chú nhưng thiếu quyền sửa trả 403. Thiếu hoặc sai định dạng khóa tác vụ trả 400; JSON sai cú pháp trả 400; trạng thái đích ngoài `done` trả 422. Lỗi của PATCH dùng `application/problem+json` với URI `type`, `title`, `status` và mã ổn định. Các route cũ giữ định dạng lỗi client đang dùng. |

Mở rộng kiểu `Handler` và hàm trả HTTP để chuyển header thành công từ handler đến response. Bộ xử lý lỗi cần nhận diện hợp đồng của PATCH kể cả khi lỗi xảy ra trước khi ghi. Ghim cú pháp khóa tác vụ trong OpenAPI, đề xuất UUID v4 được tạo một lần cho mỗi ý định. [HTTP If-Match](https://www.rfc-editor.org/rfc/rfc9110.html#section-13.1.1) · [HTTP 428](https://www.rfc-editor.org/rfc/rfc6585.html#section-3) · [Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html)

**Ví dụ kết quả PATCH thành công** cho client mới. `resultVersion` luôn là phiên bản mà thao tác đã tạo hoặc xác nhận; nếu có thay đổi sau đó, GET cung cấp phiên bản hiện hành.

```json
{
  "operationId": "ca73b69d-d0ec-40bc-86f0-96f039283e0b",
  "noteId": "683ed43e-8940-4119-99ab-106f32af748a",
  "outcome": "applied", "resultVersion": 2
}
```

### 4.2 Migration, giao dịch và phục hồi

1. Thêm migration mở rộng, tên đề xuất `0006_note_completion.ts`, đăng ký trong `MIGRATIONS` của `src/migrate.ts` và cập nhật kiểu ở `src/db.ts`. Ghi chú cũ có `status=open`, `version=1`; DB ràng buộc trạng thái và version dương. Thêm bảng kết quả yêu cầu và bảng audit với `tenant_id`, ràng buộc quyền tenant tương ứng. Triển khai schema trước binary mới. [Danh sách migration tĩnh](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/framework/templates/packs/web-api-ts/starter/src/migrate.ts#L1-L20)
2. Trong `withTenant`, kiểm actor hiện tại và phạm vi đối tượng. Dùng khóa duy nhất theo `tenant + actor + action + noteId + idempotencyKey`. Fingerprint là SHA-256 của biểu diễn chuẩn hóa gồm phiên bản hợp đồng, action, ID, trạng thái đích và tập ETag điều kiện ban đầu. Nếu cùng khóa đã xử lý và fingerprint trùng, trả lại receipt đã commit sau khi kiểm quyền hiện tại. Thực hiện bước này trước khi so với version hiện tại; nếu không, một lần ghi thành công bị mất phản hồi có thể bị báo nhầm 412. Cùng khóa nhưng fingerprint khác trả 409.
3. Với ý định mới, tuần tự hóa các yêu cầu cùng khóa và kiểm version khi cập nhật. Khi `open → done`, ghi bản ghi mới nhất của note, tăng version một, thêm một sự kiện audit và hoàn tất receipt trong cùng giao dịch. Nếu đang `done` và điều kiện version đúng, ghi receipt `no_change`, giữ version và số sự kiện audit. Nếu transaction thất bại, không để lại reservation đã hoàn tất hoặc tác động một phần. Hai caller cùng khóa nhận cùng `operationId`.
4. Đề xuất giữ receipt ít nhất 24 giờ từ khi commit và công bố cửa sổ này cho client. Sau khi hết hạn, yêu cầu gửi lại được đánh giá theo trạng thái và tiền điều kiện hiện tại; UI đọc lại bản mới trước khi đề nghị người dùng tạo ý định khác. Khi quay lui ứng dụng, chạy binary N trên schema mở rộng sau khi đã có dữ liệu từ N+1. Kiểm restore riêng trên bản sao DB. Bản rollback vận hành không phụ thuộc việc xóa bảng có audit hay receipt. [Giao dịch theo tenant](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/framework/templates/packs/web-api-ts/starter/src/db.ts#L99-L108)

### 4.3 Bộ nghiệm thu web

| Ca | Tình huống và điều kiện qua |
|---|---|
| **WEB-01** | Ghim OAS và client từ archive N. Candidate OAS 3.1.0 khai mô tả cho mọi response và khai tham số path UUID bắt buộc. Sửa vòng lặp trong `test/contract.test.ts` để phân biệt HTTP method với metadata Path Item. Validator qua, kiểm tương thích bắt được việc bỏ header đã hứa; client N vẫn đọc được dữ liệu và lỗi cũ. |
| **WEB-02** | Với note mẫu cũ, người tạo hoàn tất từ UI. Kiểm receipt, version, DB và audit. Kiểm độc lập 401/403/404, thiếu precondition và dữ liệu không hợp lệ. Thử bàn phím, focus, trạng thái đang lưu và thông báo hoàn tất. |
| **WEB-03** | Hai kết nối của cùng người tạo, cùng ETag, hai khóa khác nhau: một lần ghi, một 412. Hai kết nối cùng khóa, cùng fingerprint: hai receipt cùng ý định, một lần ghi, một audit. Khóa cũ với payload/điều kiện khác: 409 và giữ dữ liệu. |
| **WEB-04** | Mất phản hồi ngay sau commit, retry cùng khóa. UI hiển thị kết quả xác minh lại từ server. Phiên bị thu hồi trước retry phải trả 401. Sau khi đổi tenant, dữ liệu của phiên trước không xuất hiện. |
| **WEB-05** | Build/cài candidate, nâng DB chứa dữ liệu N và chạy client N/N+1. Diễn tập quay về binary N, sau đó restore backup tách biệt và đối soát dữ liệu nghiệp vụ. Lưu SHA, digest, kết quả test và thời gian phục hồi. |

Mở rộng các suite hiện có `contract.test.ts`, `slice.test.ts`, `restore.test.ts`, browser matrix và ca preview dùng API/DB thật. Chạy `pnpm typecheck`, `pnpm test`, `pnpm build` trong starter đã cài trên tổ hợp hỗ trợ. Job `contract-baseline` hiện kiểm thay baseline đối với nhánh gốc; khi nghiệm thu cần cả kết quả validator và client chạy trên candidate. [Contract test](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/framework/templates/packs/web-api-ts/starter/test/contract.test.ts#L80-L105) · [Workflow pack](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/.github/workflows/pack-web-api.yml#L85-L105)

## 5. Biên tập và xuất bản tin với site-cms-ts

**Kết quả bàn giao.** Biên tập viên tạo nháp, người có quyền duyệt và xuất bản bài. Đội vận hành truy từ URL công khai về đúng commit nội dung, digest bản dựng và khôi phục được phiên bản trước. D-624/ADR-0109 đã chọn Astro tĩnh và Decap CMS, nội dung Markdown/JSON thuộc Git, admin dùng Git host qua OAuth proxy tự vận hành. Stack đã duyệt; starter, CI, tích hợp và pilot còn phải thực hiện. [ADR-0109](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/adr/0109-site-cms-ts-pack.md)

| Task và ca | Phạm vi PR, tiêu chí chấp nhận |
|---|---|
| **T-5057 / CMS-01** | Tạo `framework/templates/packs/site-cms-ts/` với manifest, starter, lockfile, cấu hình CMS, schema bài và lệnh build/test. Dùng cùng quy ước cho tiêu đề, slug duy nhất, ngày, nội dung, ảnh và alt nếu có. Bài hợp lệ tạo HTML, canonical, JSON-LD và sitemap đúng URL; bài thiếu trường bắt buộc hoặc trùng slug làm build báo lỗi chỉ rõ bài. Cổng repo: `python3 -m unittest tests.test_packs tests.test_pack`. |
| **T-5058 / CMS-02** | Thêm workflow pack và ca đối chứng theo bảy lớp của PLAN: bảo vệ yêu cầu quản trị, lọc nội dung hiển thị, phân quyền admin, cấu hình MFA, giảm chuyển động, JSON-LD, sitemap. Mỗi lớp lưu ID phép kiểm, kết quả fixture tốt và kết quả fixture không đạt đúng vì nguyên nhân dự kiến. Cổng repo: `python3 -m unittest tests.test_packs tests.test_pack_ci_setup` và `python3 scripts/xt.py changelog-check`. |
| **T-5059 / CMS-03** | Sau T-5058 **và** T-5069, nối installer và factory. Brief site giới thiệu có tin chọn CMS; web nghiệp vụ nhiều tenant chọn pack web. Thử repo sạch, dry-run và repo cũ có tùy biến, xung đột ra `.xtemplates-new`. Cổng repo: `python3 -m unittest tests.test_install_pack` và `python3 scripts/xt.py changelog-check`. |
| **T-5060 / CMS-04** | Trong repo thử tách biệt, mở preview desktop/mobile; tạo → sửa nháp → duyệt → xuất bản → sửa → xóa. Khi brief yêu cầu duyệt, bật `editorial_workflow`; cấu hình nhánh Git phải thực thi quyền tách giữa người viết và người duyệt. Nháp chưa xuất hiện trên site. Bài đã duyệt xuất hiện đúng nội dung và URL; sửa/xóa cập nhật sitemap. Lưu SHA nội dung, digest output và người duyệt. |
| **T-5060 / CMS-05** | Chạy lại bản dựng đã ghim để phục hồi trang công khai. Nếu cần phục hồi cả trạng thái nguồn, tạo commit hoàn tác có review giữ được lịch sử, dựng và đối soát lại URL, nội dung và sitemap. Đo thời gian phục hồi. Giữ Lighthouse ≥0,9 ở bốn nhóm theo PLAN, ghi phiên bản công cụ và cấu hình lab. Đóng pilot theo gate của PLAN và hồ sơ bằng chứng đã lưu. |

**Ranh giới xác nhận.** CI kiểm schema, kết quả build, hành vi proxy và quyền trên fixture. Phát hành cho khách cần người có quyền xác nhận chào giá và bản thiết kế, Git host/IdP xác nhận MFA, owner nhận bàn giao repo, nội dung và cách khôi phục. Nếu thiếu quyền tên miền hoặc Search Console, ghi việc còn chờ cùng người phụ trách. Chỉ công bố bằng chứng ở đúng môi trường đã kiểm. [PLAN CMS và gate các task](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/autopilot/PLAN-site-cms-2026-11-26.md#L32-L40) · [Lịch tích hợp installer](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/research/2026-11-26-unified-upgrade-plan.md#L87-L113) · [Decap editorial workflow](https://decapcms.org/docs/editorial-workflows/)

## 6. Quyết định của AI và quyền thực thi

Bộ điều phối chịu trách nhiệm phân loại ở đầu vào, duyệt kế hoạch, cấp quyền ngay trước thao tác và kiểm đầu ra trước khi chuyển cho người dùng. Chủ dịch vụ xác lập phạm vi sử dụng, phiên bản chính sách và đầu mối tiếp nhận yêu cầu xem xét lại. Mục này đặc tả kết quả mà bên gọi có thể quan sát và các phép kiểm tính toàn vẹn. Khi bổ sung bộ điều phối phía dịch vụ, mỗi công cụ ghi file, gửi dữ liệu hay deploy chỉ thực hiện một thao tác có phạm vi rõ. Hook đã có trong harness là một điểm kiểm ở host; T-5081 vẫn cần bằng chứng payload trên host được hỗ trợ. [Hook hiện tại](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/.claude/settings.json) · [Kế hoạch harness](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/autopilot/PLAN-upgrade-2026-11-27.md)

### 6.1 Hợp đồng trạng thái đề xuất

| Trạng thái | Bên gọi làm gì | Đầu ra và lưu vết |
|---|---|---|
| `allowed` | Xét quyền hiện tại tại nơi thao tác. So `principal_id, run_id, plan_digest, action, target, expires_at, policy_version` trước khi ghi. | Lưu ID quyết định và ID thao tác trong receipt nội bộ. Thay bất kỳ phần phạm vi nào thì xét quyết định mới. |
| `needs_review` | Tạm dừng phần việc phụ thuộc, nêu thông tin tối thiểu cần bổ sung. Người có thẩm quyền xem lại. | Tạo quyết định mới có tham chiếu quyết định trước. Xác minh quyền hiện tại trước khi chạy tiếp. |
| `unavailable` | Khi bộ kiểm hết thời gian hoặc dịch vụ lỗi, tạm dừng tác động. Bên gọi có thể xét lại sau khi dịch vụ phục hồi. | Phân biệt lỗi vận hành với từ chối theo chính sách trong số liệu và UI. |
| `blocked` | Kết thúc đúng phần việc đã bị chặn, hủy các bước phụ thuộc chưa thực hiện, giữ tác vụ hợp lệ độc lập. | API dùng phong bì bên dưới. UI giữ đúng câu thông báo. Client gộp sự kiện cuối trùng khi nối lại stream. |

```json
{"status":"blocked","message":"Tôi không thể hỗ trợ yêu cầu này."}
```

Với yêu cầu bị chặn trước cấp quyền, phải đo được 0 thao tác gây tác động, 0 thay đổi file/DB, 0 byte nháp được phát. Nếu mục đích thay đổi sau một bước hợp lệ đã commit, ghi đúng kết quả của bước đã hoàn tất. Lưu log nội bộ tối thiểu gồm mã run, thời gian, phiên bản policy, kết quả, mã lý do và lớp công cụ. Owner dịch vụ xác định thời hạn lưu và quyền đọc trước khi thu log thật. Công bố phạm vi bảo đảm theo hosted hoặc local trong receipt. Trên máy khách tự quản chỉ ghi nhận những phép kiểm host đã chứng minh được.

### 6.2 Ca nghiệm thu và mở dần

| Ca | Dữ liệu thử và kết quả mong đợi |
|---|---|
| AI-01 | Dữ liệu giả gồm 20 cặp hợp lệ/bị chặn gần nghĩa và 10 ca cần làm rõ, mỗi trường hợp có bản Việt và Anh. Báo số đúng/sai theo ngôn ngữ và loại. Tách tập giữ lại khỏi tập chỉnh policy. |
| AI-02 | Yêu cầu đã bị chặn đi qua điều phối, agent con và công cụ mô phỏng. Client chỉ thấy kết quả cuối theo hợp đồng; snapshot cây đích và DB giữ nguyên. |
| AI-03 | Mất kết nối, quyết định hết hạn hoặc đổi đích giữa hai bước. Không cấp quyền cho bước kế tiếp. Khôi phục dịch vụ phải xét lại trước khi chạy. |
| AI-04 | Một giao việc chứa phần bị chặn, phần phụ thuộc và phần độc lập hợp lệ. Chỉ phần hợp lệ độc lập tạo artifact. Khiếu nại có mã tra cứu; người xem lại không tự chạy lại thao tác. |

Owner sản phẩm và QA chạy bộ ca trên fixture trước; chủ dịch vụ duyệt canary nếu có scope hosted. Khi có tác động ngoài phạm vi hoặc trả thành công sai, dừng mở rộng, khôi phục phiên bản policy trước đã xác minh, giữ hồ sơ sự cố đã loại dữ liệu nhạy cảm. Theo dõi tỷ lệ chặn nhầm, số chuyển người xem, P95 thời gian xử lý và chi phí từng lần. Ngưỡng “0” nói trên là điều kiện nghiệm thu tập thử.

## 7. Hồ sơ bằng chứng và nghiệm thu theo quy mô

### 7.1 Liên kết đúng đối tượng được kiểm

Đề xuất một **chỉ mục bằng chứng** cho từng ứng viên. Mỗi dòng có `requirement_id, case_id, subject_sha, artifact_sha256, scope, environment, result, evidence_ref, observed_at`; thêm `plan_digest` cho ca installer, `policy_version` cho ca AI. Chấp nhận `pass, fail, needs_evidence, not_applicable`. Dòng ngoài phạm vi phải có lý do được rà; một ca bắt buộc đang chờ, bị bỏ qua, hoặc trỏ tới digest khác làm dừng promotion. ID duy nhất của một lần chạy kết hợp ca, digest và mã lượt. Khi chạy lại, lưu thêm lượt mới và chỉ rõ lượt nào quyết định cho ứng viên.

QA dùng đường dẫn tới hồ sơ gốc. Biên nhận cài đặt ở mục 3 xác minh thay đổi file; sổ `docs/ops/DEPLOYS.json` của deploy tiếp tục lưu `current/previous/unknown`, subject, served digest và kết quả rollback. Danh sách `docs/autopilot/ACCEPTANCE.paths` phục vụ khóa bộ nghiệm thu độc lập trước khi chạy. Gắn bằng chứng cùng ứng viên bằng digest, đồng thời ghi tên artifact để phân biệt ZIP evidence, archive cài và bundle ứng dụng. [SPEC deploy](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/specs/SPEC-factory-deploy.md#L215-L222) · [SPEC nghiệm thu](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/specs/SPEC-factory-acceptance.md#L11-L24)

### 7.2 Chính sách kết quả UX

Giữ `DESIGN-EVIDENCE` schema 1 cho mỗi nhiệm vụ, gồm mã người thử ẩn danh, `completed`, `help_count`, thời lượng và số lỗi. Bộ kiểm hiện tại xác nhận tính đầy đủ và các tổng, có thể chấp nhận hồ sơ `tested` với 0 người hoàn tất. Lớp kết luận đề xuất đọc hai tệp nhiệm vụ, danh sách người tham gia, digest bản cài và bản ghi sự cố. Khóa điều kiện trước khi mời người dùng. [SPEC design evidence](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/specs/SPEC-design-evidence.md)

| Ca | Given / When | Then |
|---|---|---|
| UX-01 | Năm người thử hai tác vụ web trên cùng digest: hoàn tất ghi chú và xử lý xung đột. | Mỗi tác vụ có ít nhất 4/5 người `completed=true` và `help_count=0`; không có ghi nhầm tenant, mất dữ liệu hoặc trở ngại nghiêm trọng. Kết luận `pass`. |
| UX-02 | Đủ mẫu, chỉ 3/5 tự hoàn thành một tác vụ, dù bộ kiểm cấu trúc báo đạt. | Kết luận `rework` cho tác vụ, ghi màn hình/bước thất bại; chỉ mục ghi `fail`. Dữ liệu nhiệm vụ khác vẫn được giữ. |
| UX-03 | Chưa đủ người, khác digest, thiếu tệp hoặc danh sách người giữa hai nhiệm vụ lệch. | Kết luận `needs_evidence`; bổ sung hoặc chạy lại đúng bản. Một lỗi nghiêm trọng đã xác minh đủ để yêu cầu sửa ngay, kể cả khi thiếu mẫu. |

### 7.3 Ba pilot độc lập

| Ca / owner | Phép thử | Điều kiện kết thúc và quyết định |
|---|---|---|
| PIL-01 · Core và một người mới | Một CLI chạy trên tệp giả. Người thử bắt đầu từ checkout sạch, đọc hướng dẫn, chạy luồng chính và bàn giao lệnh tái kiểm. | Mục tiêu một buổi, ghi phút thực làm, lần nhờ hỗ trợ, số tài liệu tự viết và kết quả chạy lại. Nếu phải nhờ tác giả can thiệp, ghi đúng nguyên nhân và chỉnh hướng dẫn trước lần thử sau. |
| PIL-02 · chủ web và QA | Nâng ứng dụng đã tùy biến, kiểm luồng ghi, giữ dữ liệu, chạy lại và phục hồi. Hai người thực hiện hai brief tương đương, đảo thứ tự dùng pack và cách làm hiện tại. | Mỗi lượt ghi giờ công thực, giờ chờ, runner-minutes, số file sửa tay và thời gian phục hồi. Chỉ đề xuất mở rộng khi cả hai người giảm công và tất cả ca bắt buộc qua. |
| PIL-03 · hai owner độc lập | API và consumer phát hành lệch phiên bản, ca tương thích lúc nâng từng phần và một lần quay lui. Ghim mục tiêu thời gian khôi phục và dữ liệu được phép mất trước lượt chạy. | Định vị đúng thành phần, owner và digest; luồng nghiệp vụ phục hồi trong mức đã chốt, dữ liệu trong giới hạn đã đồng ý. Nếu chỉ diễn tập ở fixture, phạm vi nghiệm thu là mô phỏng liên đội. |

Báo theo từng pilot: đủ điều kiện tiếp tục / cần sửa / thiếu bằng chứng. Kết quả CLI ở S không tự chứng nhận phân phối ở M hoặc L. Công của tác giả pack hỗ trợ người tiếp nhận được cộng vào chi phí. Với một kỳ hỗ trợ, so chi phí xây và bảo trì với phần tiết kiệm trên mỗi dự án cùng phạm vi. Khi chênh lệch công mỗi lượt bằng 0 hoặc âm, giữ mức thử và xác định bước cần tối ưu.

## 8. Cổng CI và quyết định phát hành

| Cổng / ca | Đầu vào và phép kiểm | Ai quyết định và bằng chứng khi dừng |
|---|---|---|
| REL-01 · PR Core | Chạy các suite chạm tới, kiểm hợp đồng CLI ở source và bản cài, CI đúng head; tệp nóng giữ ngân sách dòng và thứ tự Revision 4. Khi đổi mã, ghi lại số đo chi phí lượt đỏ và timeout nếu có. | Maintainer cùng reviewer theo chính sách repo. Bằng chứng cũ được ghim theo SHA và không chuyển nguyên kết luận sang SHA mới. |
| REL-02 · pack | Ứng viên được build một lần, xác minh nguồn ký và digest tại phía nhận, cài archive đó vào repo sạch và fixture N→N+1. Chạy suite độc lập và rollback. | Chủ pack nộp chỉ mục mục 7. Ca bắt buộc bị skip hoặc digest không khớp giữ trạng thái chờ, ghi chính xác job cần chạy. [SLSA](https://slsa.dev/spec/v1.2/verifying-artifacts) |
| REL-03 · bản framework | T-5079 theo các phụ thuộc đã duyệt, sổ audit, review delta, chữ ký và `release-check --json` tại ứng viên. Khi tag tồn tại, đối chiếu kiểu tag, SHA và trạng thái release qua workflow hiện có. | Chủ phát hành xác nhận phạm vi và ngoại lệ theo PLAN. T-4007 cần quyền quản trị bảo vệ tag/App/immutability; T-5020 diễn tập sau cấu hình. [T-5079](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/autopilot/PLAN-upgrade-2026-11-27.md#L57-L67) |
| REL-04 · đích thật | T-5024 kiểm hợp đồng bằng chứng bằng máy. D-610 chi phối phạm vi, T-5017/T-5018 có owner, quyền và phụ thuộc riêng. Registry tách bản khai báo khỏi phiên bản/digest đã quan sát. | Chủ đích cho phép, chỉ định người quay lui và mốc kiểm. Khi phục hồi không xác minh được trạng thái đang chạy, ghi `unknown`, dừng đợt rollout và đối soát. [PLAN harden](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/autopilot/PLAN-harden-2026-11-24.md) |

**Mốc đối chứng.** Tại `6adbd4ad`, G7 trên CPython 3.15.2, phụ thuộc ghim hash và checkout sạch trả `NO-GO`; 69/69 lệnh blueprint đạt, còn 10 mục audit strict và phạm vi rà cục bộ 193 tệp. Cần đối chiếu bằng chứng review trên PR có quyền đọc trước khi phân công. Bản công khai gần nhất khi so là `v3.36.0`; biên nhận của bản này chỉ có hiệu lực cho chính bản đó. [Sổ audit](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/ops/AUDIT-STATUS.md) · [Release đã công bố](https://github.com/www-donghanhcungban-org/X-Templates/releases/tag/v3.36.0)

**Chỉ số sau khi mở thử.** Chủ đích theo dõi lỗi tác vụ, tỷ lệ retry, xung đột phiên bản, can thiệp thủ công và thời gian khôi phục so với mục tiêu của mình. Ghi chi phí Core theo cùng định nghĩa runner-minutes của các PR trước. Mất dữ liệu, ghi nhầm tenant, sai digest hoặc tác động AI ngoài quyền đều dừng quảng bá bản hiện tại, giữ bằng chứng rồi phục hồi bằng bản đã xác minh. Quyết định quay lui app và quyết định restore DB có người chịu trách nhiệm và phép xác nhận riêng.

## 9. Gói công việc để mở PR và giao người thực hiện

Bảng dưới là hàng đợi đề xuất cho **hai kỹ sư trong sáu tuần** với người thử và reviewer theo lịch. Một hàng có thể tách thành các PR nhỏ theo ranh giới tệp. Chữ “sau” là điều kiện bắt đầu tích hợp; có thể chuẩn bị fixture và viết tiêu chí trước. Khi task đã có trong repo, dùng chính ID đó. Các mã ca SCL/INS/WEB/CMS/AI/UX/PIL/REL ở tài liệu này chỉ dùng để truy nghiệm thu.

| Thời điểm và người nhận | Phạm vi thay đổi dự kiến | Phụ thuộc và đầu ra PR |
|---|---|---|
| Hai ngày đầu · maintainer + QA | Đối soát 10 mục strict theo owner, 193 tệp với review trên GitHub, ghim archive N, khởi tạo fixture sạch và fixture đã tùy biến. Đối soát #854/#856 theo phạm vi đã merge. | Lưu SHA, môi trường, kết quả cổng và phần còn thiếu. Chốt người nhận ba pilot, lịch QA và số đo gốc. |
| Tuần 1 · chủ Core + người dùng mới | Bổ sung khối hồ sơ quy mô vào mẫu `PROJECT.md` và hai bản hướng dẫn factory; giữ CLI cũ. Chạy pilot CLI. | SCL-01–05 và PIL-01. Chưa triển khai giao diện G05–G11 khi chưa đủ điều kiện đăng ký. |
| Tuần 1–2 · maintainer hai tuyến | Guard theo T-5041 → T-5067 → T-5068 → T-3996 → T-3987/88 → T-3989/90. CLI theo T-5063 → T-5069 để tách shard. Mỗi tệp nóng có một chủ tại một thời điểm. | So CLI/mã thoát/JSON và corpus trước-sau ở source, installer, .pyz; ghi công của lát di chuyển đầu. T-5009 → T-5010 → T-5011 theo dõi cả lượt kiểm lỗi. |
| Tuần 1–2 · chủ pack web | Sửa `starter/contract/openapi.json`, cách so Path Item và kiểm client N. Tách PR hợp đồng khỏi PR thêm route; QA giữ bản gốc từ archive. | WEB-01 đi trước migration/HTTP. Khoanh thay đổi tương thích và có fixture làm đỏ phép kiểm khi hợp đồng bị phá. |
| Từ tuần 1 · chủ CMS khi có sức người | T-5057 starter → T-5058 CI; đặt fixture biên tập trước, khóa schema nội dung và đường phục hồi. | CMS-01–02. T-5059 chờ T-5058 và T-5069; T-5060 chờ T-5059. |
| Tuần 2–4, có điều kiện · chủ installer | Tách PR sinh plan và parity → khóa và apply → journal/recover → archive N→N+1. Tái dùng hàm phân loại starter/managed và wrapper CLI. | INS-01–05. Dùng tuỳ chọn mới trên fixture. Chuyển đường mặc định sau parity, có đường quay lại engine đã kiểm cho giao dịch mới. |
| Tuần 3–5 · chủ web + QA | Tách migration/DB → handler/HTTP → giao diện → nghiệm thu. Chủ CMS nối installer, factory rồi chạy pilot CMS đúng thứ tự. | WEB-02–05, UX-01–03, CMS-03–05. T-5012/5013 đối soát job Chromium và vòng lặp theo PLAN trước khi tick. |
| Tuần 3–5 · chủ điều phối AI | Khóa hợp đồng quyết định, adapter công cụ giả, thử stream và xử lý kết nối lại. Nếu chưa có dịch vụ hosted phù hợp thì chỉ hoàn thành phần mô phỏng. | AI-01–04. Có bảng đánh giá chặn nhầm và người xử lý khiếu nại. Thử thật cần owner của môi trường. |
| Tuần 5–6 · hai owner tiếp nhận + chủ release | Chạy PIL-02/PIL-03, lập chỉ mục bằng chứng, đối soát REL-01–04. Chuẩn bị tài liệu vận hành và quyết định hỗ trợ từng tổ hợp. | Ghi pass/fail/needs_evidence từng đích, chi phí thực và đề xuất đầu tư tiếp. Kênh production tuân theo D-610 và quyền đã cấp. |

**Thứ tự ưu tiên khi thiếu người.** Quỹ dự trù 60 ngày-người, dành 12 cho review và khắc phục, còn 48 phân bổ ban đầu: 12 Core/audit, 12 installer, 10 web, 8 CMS, 6 cho số đo, đặc tả và đánh giá AI bằng fixture. Ghi công từng tuần; sau T-5069 cập nhật dự báo từ chi phí thực. Khi vượt quỹ, hoàn thiện một đường cài có phục hồi và một luồng web trước, ghi CMS/AI/L ở cột còn thiếu đúng phạm vi. Admin thực hiện cấu hình thật và thời gian của người dùng thử phải dự trù riêng.

**Điều kiện đăng ký tính năng mới.** Revision 4 §0.5 yêu cầu hàng 11 và 12 merge, cùng chi phí đã đo, trước khi đăng ký các lát G05–G11. PLAN-upgrade viết gọn T-3996/T-5069. Maintainer đối soát và ghi thứ tự thống nhất trong PLAN trước khi triển khai các lát phụ thuộc. Các PR đã có task độc lập tiếp tục theo nhà và gate của chúng. Các mốc rà đã ghi gồm 02/12, 15/12, 31/12/2026 và 21/01/2027; ngày cuối gồm hạn hỗ trợ pack web và ngoại lệ X-Scanner, mỗi mục có owner riêng. [Revision 4](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/research/2026-11-26-unified-upgrade-plan.md#L87-L120) · [PLAN nâng cấp](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/autopilot/PLAN-upgrade-2026-11-27.md#L57-L67) · [Đích tiếp nhận](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/ops/TARGETS.md)

## 10. Phiếu nghiệm thu và cách bàn giao

**Mẫu cho từng PR hoặc đợt thử.** Điền người thực hiện, người nghiệm thu, ID task hoặc quyết định đề xuất, dải thay đổi, SHA nguồn và digest bản được thử. Liệt kê ID ca, trạng thái, số lần chạy, dữ liệu trước/sau, lệnh hoặc URL bằng chứng, giới hạn và owner xử lý phần còn thiếu. Ca chưa có môi trường/người thử phải ghi lý do và điều kiện mở lại. Người nhận có thể chạy lại bằng chính phiên bản đã ghim.

| Phần việc | Tệp hoặc điểm nối chính | Bộ kiểm hiện có làm nền | Yêu cầu mới phải có bằng chứng |
|---|---|---|---|
| Quy mô và factory | `framework/templates/PROJECT.md`, hai gương skill factory, `compose` trong `scripts/xt.py` | `tests.test_xt.EssentialNotCappedTest`, `tests.test_install_new`, `tests.test_skill_factory` | SCL-01–05 và PIL-01. |
| Cài và nâng | `scripts/install.py`, suite installer và pack, manifest của pack | `tests.test_install_atomic`, `tests.test_install_pack`, `tests.test_pack` | INS-01–05 trên archive N và ứng viên N+1. |
| Pack web | `starter/src/`, `starter/contract/`, `starter/test/`, `starter/tests_e2e/` trong pack | Kiểm contract hiện có, test PostgreSQL, restore, browser, `tests.test_pack_ui` | WEB-01–05 và UX-01–03; chạy cả client đang phát hành. |
| Pack CMS | `framework/templates/packs/site-cms-ts/` và `.github/workflows/pack-site-cms.yml` dự kiến | Gate tại từng task T-5057–5060 | CMS-01–05 và xác nhận riêng cho quyền/phạm vi ngoài fixture. |
| Điều phối AI | Điểm cấp quyền, API và stream của dịch vụ được chọn; harness theo từng host | T-5081 kiểm đăng ký hook và bằng chứng host theo PLAN | AI-01–04, log giới hạn phạm vi, quyết định rollback policy. |
| Nghiệm thu và phát hành | Khóa acceptance, sổ deploy, báo cáo outcome, `release-check` và sổ audit | `tests.test_check_design_evidence`, `tests.test_factory_metrics`, `tests.test_deploy_receipt` | PIL-02–03, REL-01–04 và quyết định độc lập theo từng kênh. |

**Bằng chứng nền tại `6adbd4ad`.** Dùng CPython 3.15.2 và chạy từ gốc checkout của commit này để đối chiếu lại kết quả dưới đây.

```bash
python3 -m unittest tests.test_xt.EssentialNotCappedTest tests.test_check_design_evidence tests.test_factory_metrics
```

Kết quả **26/26 test nền đạt**. Số này bao phủ ba suite hiện có về feature theo quy mô, cấu trúc hồ sơ thiết kế và số đo factory. Các ca với ID trong bảng trên là tiêu chí thực hiện tiếp theo. Người nghiệm thu chỉ ghi tính năng hoàn thành khi các ca liên quan có bằng chứng đúng digest và đúng phạm vi.
