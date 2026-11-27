# Kế hoạch tích hợp nâng cấp X-Templates cho dự án nhỏ đến lớn

**Đề xuất ngày 27/11/2026.** Mục tiêu bàn giao cho một đội mới là khả năng chọn đúng phần của khung, tạo hoặc nâng một dự án, hoàn thành một tác vụ sản phẩm và khôi phục được phiên bản đã kiểm. Với sản phẩm có người vận hành, phạm vi bàn giao bao gồm cách họ quản lý nội dung, dữ liệu hoặc công việc hằng ngày.

[Đặc tả kỹ thuật và ca nghiệm thu](../specs/SPEC-upgrade-by-scale.md) · [Kế hoạch cho các tác vụ quản trị](PLAN-admin-workflows-2026-11-27.md) · [PLAN nâng cấp đang điều phối các task](PLAN-upgrade-2026-11-27.md)

## 1. Mốc đối chiếu và phạm vi quyết định

| Hạng mục | Đã có ở commit `6adbd4ad` | Phần đưa vào kế hoạch |
|---|---|---|
| Core và factory | `compose` ghép profile, ngành, tính năng, S/M/L và giữ trạng thái theo ID. Factory tạo hồ sơ dự án. | Bổ sung dữ kiện chọn mức, các tác vụ quản trị, chủ vận hành và điều kiện xét lại. Thử nâng mức trên blueprint có ghi chú thật trong fixture. |
| Installer | Có `--plan` schema 1 và luồng `--new` riêng. | Thiết kế bản kế hoạch có thể áp dụng đúng nội dung đã xem, phục hồi khi bị ngắt, giữ tùy biến của dự án và đọc lại biên nhận. |
| Pack web | `web-api-ts` có đăng nhập và UI ghi chú theo phạm vi dữ liệu của người dùng. | Làm rõ hợp đồng HTTP, bảo toàn dữ liệu khi ghi đồng thời và kiểm nâng phiên bản. Nghiệp vụ quản trị cần brief và thiết kế quyền riêng cho tác vụ đã chọn. |
| Pack CMS | ADR-0109 đã chọn Astro và Decap CMS. | Hoàn thành starter, CI, cài thử, rồi để biên tập viên thử nháp → duyệt → xuất bản → phục hồi theo kế hoạch CMS. |
| Phát hành | Bản phát hành công khai dùng làm mốc là `v3.36.0`. Lần đo G7 trên checkout sạch `6adbd4ad`, CPython 3.15.2, cho `NO-GO`: 69/69 lệnh blueprint đạt, 10 mục audit và 193 tệp trong phạm vi đối soát review cục bộ. | Đối chiếu review theo PR/SHA, chủ từng khoản audit và tái chạy trên ứng viên. Số tệp là phạm vi cần rà với bằng chứng, không phải số lỗi sản phẩm. |

PLAN gốc quản lý ID, thứ tự task, quyền thực hiện và cổng merge. Bảng dưới là đề xuất phân công giữa các nhóm việc. Khi có chênh lệch, maintainer đối soát và ghi quyết định tại PLAN sở hữu task trước khi lên lịch PR. Mốc đọc mã và G7 ở trên chỉ áp dụng cho phiên bản được nêu. [Quy tắc ghép](../../framework/00-method/composition.md) · [Đặc tả intake](../specs/SPEC-factory-intake.md) · [Pack web](../../framework/templates/packs/web-api-ts/README.md) · [Quyết định CMS](../adr/0109-site-cms-ts-pack.md)

## 2. Chọn đúng việc cho mỗi dự án

Chủ sản phẩm và người tiếp nhận trả lời bốn câu trong hồ sơ đầu vào. Ai dùng phiên bản sắp bàn giao? Họ xử lý dữ liệu gì, hậu quả của một thao tác sai là gì? Ai sẽ quản lý việc gì sau bàn giao? Ai có quyền phát hành, phục hồi và xác nhận cam kết với người dùng? Ghi lại profile, ngành, feature, đơn vị phát hành và thời điểm phải xét lại. Dùng dữ liệu giả để dựng thử khi chủ dự án còn phải xác minh thông tin.

| Mức | Ví dụ và cách thực hiện | Bằng chứng tương ứng |
|---|---|---|
| S | CLI dùng tệp giả, bản thử nội bộ hoặc prototype. Một người có thể nhận nhiều vai. Khi Git hoặc công cụ sẵn có đã đáp ứng, ghi bước thao tác và người nhận. | Một người khác làm được tác vụ từ checkout sạch. Có lệnh tái kiểm và danh sách các yêu cầu áp dụng. |
| M | Sản phẩm phục vụ người dùng thực ngoài nhóm phát triển, kể cả công cụ cho nhân viên. Chọn một luồng trọn vẹn cho người dùng và một tác vụ vận hành nếu có nhu cầu. | Chủ vận hành chạy lại được luồng trên môi trường đại diện, thấy đúng phạm vi dữ liệu, theo dõi lỗi và phục hồi phiên bản hoặc dữ liệu. |
| L | Nhiều đội cùng phát triển, SLA ký hoặc kiểm toán ngoài. Xác định phần có lịch phát hành riêng và luồng liên đội. Với tiền thật hoặc dữ liệu nhạy cảm bắt đầu đánh giá ở L, ghi lý do và kiểm soát bù khi chọn M kèm đúng gói ngành. | Có owner mỗi phần, kiểm tương thích lệch phiên bản và phục hồi liên đội trong mục tiêu đã chốt. Tác vụ đặc quyền có phạm vi, dấu vết và bằng chứng theo rủi ro. |

Với từng tác vụ quản trị, ghi vai trò, đối tượng, phạm vi dữ liệu, người được duyệt và cách khôi phục. Đội có thể dùng công cụ hiện có, dùng CMS hoặc xây màn hình nghiệp vụ. Ví dụ landing page do kỹ sư sửa qua Git, site tin có biên tập và duyệt, còn shop nhỏ có hàng đợi xử lý đơn. Mobile và API có thể dùng cùng một web quản trị khi người vận hành và quy tắc quyền giống nhau. Chọn mô-đun theo nhu cầu và mức kiểm soát theo rủi ro. [Cách chọn và nghiệm thu mô-đun quản trị](PLAN-admin-workflows-2026-11-27.md)

Khi lên S → M hoặc M → L, ghép lại cùng đường dẫn với đầy đủ profile, ngành và feature. Đối soát các ID mới thành MUST, giữ ghi chú cũ và chạy lại bằng chứng thay đổi môi trường. Khi bỏ feature hoặc hạ mức, chủ phạm vi ghi lý do, ảnh hưởng và quyết định với dữ liệu còn lưu. Nhiều đơn vị phát hành có thể dùng blueprint riêng cùng một hồ sơ kiểm luồng toàn hệ thống. [Vòng đời](../../framework/00-method/lifecycle.md) · [Quyền phê duyệt theo mức](../specs/SPEC-factory-scale.md)

## 3. Hàng đợi PR và điều kiện chuyển chặng

Lịch thực thi đã duyệt nằm ở [§0.5 của Revision 4](../../research/2026-11-26-unified-upgrade-plan.md#05-lịch-thực-thi-duy-nhất). Sáu tuần là khung dự trù cho hai kỹ sư, có reviewer và người dùng thử theo lịch. Cửa sổ bên dưới là thời điểm có thể bắt đầu, phụ thuộc thực tế quyết định lúc tích hợp. Phần quản trị dùng chung người và ngân sách với các luồng tương ứng. Nếu cần xây thêm back-office độc lập, nhóm ước lượng riêng sau khi có brief, một mẫu màn hình và ma trận quyền.

| Chặng và người nhận | Đầu việc có thể đưa vào PR | Điều kiện hoàn thành hoặc bàn giao |
|---|---|---|
| 1. Hai ngày đầu, maintainer và QA | Ghim SHA và archive N. Lập bảng PR → job → task → khoảng trống bằng chứng, đối soát T-5064/T-5065. Chốt fixture sạch, fixture có tùy biến và vai trò người tham gia pilot. | Có bản chụp baseline, chủ từng vấn đề và lệnh tái kiểm. Phạm vi G7 còn mở được giữ nguyên trong hồ sơ ứng viên. |
| 2. Tuần 1, chủ Core và chủ sản phẩm | Đề xuất khối phân loại cho hồ sơ và các bản hướng dẫn factory. Thêm câu hỏi về công việc quản trị, chọn kênh sẵn có hoặc tính năng cần xây. Thử với CLI dùng fixture, web có người dùng và dịch vụ nhiều đội. | SCL-01–05, PIL-01 trong SPEC. Quy trình sinh lại giữ trạng thái, báo chênh lệch trước khi ghi và không tự cấp quyền phát hành. |
| 3. Tuần 1–2, maintainer Guard/CLI | Theo hai tuyến của PLAN gốc. Tập trung các mốc T-3996 và T-5069, trước khi mở rộng các tệp nóng. Kiểm parity ở CLI nguồn, bản cài và gói phân phối. | JSON, mã thoát, trợ giúp và hành vi trước/sau khớp. Ghi công người, lượt CI đỏ, timeout và runner-minutes. Đăng ký G05–G11 theo thứ tự và chi phí đã đo của Revision 4. |
| 4. Tuần 1–4, chủ installer và QA độc lập | Trên fixture Linux, tách PR tạo plan → khóa đầu vào → apply → journal/recover → diễn tập N sang N+1. Giữ lối gọi CLI cũ tới khi đạt parity. | INS-01–05. Áp đúng nội dung đã xét, ghi nhận thay đổi đồng thời, giữ file khách chỉnh và phục hồi được tại các điểm ngắt đã cam kết. |
| 5. Tuần 1–5, chủ web/API | Sửa hợp đồng OpenAPI và so client N, rồi tách migration, thao tác ghi trong DB, phản hồi HTTP, giao diện. Kiểm hai người cùng sửa và một yêu cầu gửi lại khi mất kết nối. | WEB-01–05 và UX-01–03. Dữ liệu đúng tenant, giá trị lưu không bị ghi đè âm thầm, có cách phục hồi app và dữ liệu. Chủ pack xác nhận tương thích client cũ. |
| 6. Tuần 1–5, chủ CMS | T-5057 starter → T-5058 CI. T-5059 tích hợp cài đặt/factory sau T-5058 và T-5069. T-5060 dùng repo scratch sau T-5059. | CMS-01–05. Biên tập viên tự đi qua quy trình xuất bản. Bộ kiểm chứng minh quyền duyệt, truy về commit và phục hồi URL công khai. Giữ liên kết tới bằng chứng ở PLAN CMS. |
| 7. Theo luồng sản phẩm đã chọn, chủ nghiệp vụ và chủ quyền | Với một tác vụ nội dung, áp kế hoạch quản trị ngay vào pilot CMS. Với quản trị nghiệp vụ, tách PR ma trận quyền và hợp đồng API → màn hình/hành động → kiểm phạm vi và bàn giao. Dùng dữ liệu tổng hợp. | Chủ nghiệp vụ thực hiện đúng tác vụ; yêu cầu ngoài phạm vi bị từ chối cả khi gọi trực tiếp API, thao tác có hậu quả kiểm được trên nhật ký. QA kiểm bàn phím, xử lý lỗi và kết quả sau phục hồi. |
| 8. Tuần 3–5 khi có chủ dịch vụ, chủ điều phối AI | Ghim hợp đồng quyết định, phạm vi công cụ, thời hạn và đích. Kiểm biên nhận trước hành động có tác động, xử lý lỗi bộ xét quyền và nối lại stream. | AI-01–04, có kết quả theo ngôn ngữ và phạm vi hosted/local đã thử. Nếu chỉ có adapter mô phỏng, ghi rõ điểm cần chủ môi trường xác minh. |
| 9. Tuần 5–6, chủ tiếp nhận và chủ release | Chạy pilot thăng mức và pilot liên đội, tổng hợp chi phí, lỗi, số lần can thiệp, kiểm G7 trên ứng viên. Đối chiếu digest ở nguồn và ở nơi nhận. | PIL-02/03, REL-01–04. Mỗi pack/host có kết luận riêng, chủ vận hành nhận hướng dẫn và biết phiên bản phục hồi. |

Các mã SCL, INS, WEB, CMS, UX, AI, PIL và REL là ca nghiệm thu trong SPEC. Tên chặng chỉ dùng để chia việc. Giữ một người chịu trách nhiệm cho tệp Guard hoặc CLI đang sửa tại cùng thời điểm. Chuẩn bị fixture và mẫu thiết kế trong lúc chờ, rồi đối soát các phụ thuộc trước khi đụng cùng tệp. [Thứ tự tách Core](../../research/2026-11-26-unified-upgrade-plan.md) · [Kế hoạch CMS](PLAN-site-cms-2026-11-26.md) · [Đặc tả triển khai](../specs/SPEC-upgrade-by-scale.md)

## 4. Pilot và quyết định đầu tư

| Pilot | Cách kiểm | Quyết định |
|---|---|---|
| S, công cụ cá nhân | Người mới nhận brief, chạy CLI trên một tệp mẫu và bàn giao lệnh để người khác tái kiểm. Ghi thời gian thực, số lần nhờ tác giả và bước vướng. | Giữ được phạm vi gọn. Nếu một thủ tục làm chậm lần chạy đầu, xác định nó thuộc sàn bắt buộc hay phần có thể dời. |
| M, web đã tùy biến | Hai người chạy hai brief tương đương, đảo thứ tự dùng pack và quy trình hiện tại. Ghi giờ làm, giờ chờ, runner-minutes, ngày công hỗ trợ, số file can thiệp và thời gian quay lui. Thử cả quyền của người vận hành ở luồng đã chọn. | Cân nhắc mở rộng nếu cả hai người giảm công thực và mọi ca bắt buộc qua. Kết quả trái chiều thì sửa bước tốn công và đo lại. |
| L, hai đơn vị phát hành | API và consumer nâng lệch phiên bản. Mỗi owner xác nhận digest, phạm vi tác động và mục tiêu khôi phục; diễn tập quay lui, kiểm nghiệp vụ từ phía người dùng. | Đích và dữ liệu phục hồi đúng mục tiêu đã chốt. Phân loại riêng kết quả mô phỏng và lần áp dụng trên đích thật. |
| CMS, tác vụ quản trị đầu tiên | Gắn pilot tác vụ vào T-5060. Để người biên tập tạo/sửa bài, người có quyền duyệt xuất bản, sau đó trả lại bản trước. Đối soát nội dung công khai, quyền ở bước duyệt và lịch sử. | Tính một lần chạy, tái dùng bằng chứng cho ca CMS và phần quản trị. Ghi rõ cấu hình thật tại Git host mà người tiếp nhận còn phải thực hiện. |

Chỉ mở pack tiếp theo khi có người dùng, owner hỗ trợ, tổ hợp môi trường cần phục vụ, thời hạn bảo trì và ước lượng số lượt dùng. Trong cùng một kỳ, số lượt hòa vốn bằng chi phí xây và duy trì chia cho chi phí tiết kiệm mỗi lượt, làm tròn lên. Tính cả công hỗ trợ của người viết pack. Nếu chênh lệch mỗi lượt bằng 0 hoặc âm, giữ trạng thái thử nghiệm và xem lại bước làm phát sinh chi phí.

## 5. Phát hành và bàn giao

1. **Chủ PR** lưu kết quả cổng trên đúng head, nêu ca đạt, ca chưa chạy, tệp/đơn vị bị ảnh hưởng và người phụ trách. Khi sửa sau review, ghi lại bằng chứng cho head mới. [Quy trình đóng góp](../../CONTRIBUTING.md)
2. **Chủ pack** build một lần, ghi phiên bản và digest, kiểm từ archive dùng để phân phối. Người nhận cài lại trên fixture sạch và đã có tùy biến, thử tác vụ, thử lỗi và phục hồi. Hồ sơ nêu môi trường và phiên bản đã quan sát.
3. **Chủ phát hành** đối soát nợ audit/review và quyết định trên ứng viên theo T-5079. T-4007/T-5020 theo luồng cấu hình quyền và diễn tập của repo. Nếu mất dữ liệu, ghi sai tenant, áp sai digest hoặc công cụ AI vượt quyền, dừng mở rộng ứng viên và xác minh khôi phục. [PLAN vận hành và cổng phát hành](PLAN-harden-2026-11-24.md)
4. **Chủ dự án đích** xác nhận người vận hành, quyền mở rollout, người quay lui và bằng chứng từ nơi chạy. D-610, T-5017/T-5018 và T-5024 chi phối việc ra đích thật và hợp đồng bằng chứng. Khi chưa có đích đủ điều kiện, tiếp tục nhận xét từ fixture và giữ trạng thái đích thật là chờ. [Registry các đích](../ops/registry.json)
5. **Chủ sản phẩm** ghi quyết định tiếp tục, sửa rồi thử lại hoặc dừng cho từng tổ hợp pack/host. Ghi riêng quyền, chi phí và mục tiêu vận hành chưa có người nhận. Nếu quá quỹ hai kỹ sư, ưu tiên một đường nâng có phục hồi và một luồng web chạy trọn trước khi cam kết thêm pack, back-office nghiệp vụ hoặc pilot liên đội.

Biên bản cuối gồm mục tiêu tác vụ, người dùng/role, đơn vị được xét, lý do chọn S/M/L, phiên bản và digest, ca kiểm cùng kết quả, thời gian khôi phục, ngoại lệ còn mở, người nhận và ngày xét lại. Đội tiếp nhận phải dùng được chính biên bản đó để tìm bản chạy, thử lại tác vụ và xác nhận trạng thái sau phục hồi. [Mẫu nghiệm thu và bàn giao](../specs/SPEC-upgrade-by-scale.md)
