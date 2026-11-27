# Kế hoạch triển khai trang quản trị cho X-Templates

**Phụ lục đặc tả triển khai theo quy mô · Đề xuất ngày 27/11/2026.** Dành cho chủ sản phẩm, kỹ sư, thiết kế, người vận hành và người nghiệm thu. Mỗi dự án xác định ai cần quản lý việc gì sau bàn giao. Khi đã có công cụ phù hợp, đội có thể bàn giao quyền và hướng dẫn sử dụng công cụ đó. Khi phải xây giao diện, chỉ đưa vào phạm vi các tác vụ có người chịu trách nhiệm và điều kiện nghiệm thu.

**Quyết định đề xuất.** Core lưu quyết định chọn cách quản trị. Các pack sở hữu màn hình và quy tắc nghiệp vụ tương ứng. Lần triển khai đầu bàn giao một luồng hoàn chỉnh cho mỗi cách quản trị được chọn. Ví dụ, một cửa hàng cần xử lý đơn từ hàng đợi tới biên nhận trước khi cần biểu đồ doanh thu.

## 1. Phạm vi và quyết định lúc khởi tạo

Ở mốc mã nguồn `6adbd4ad`, pack `web-api-ts` chạy được ứng dụng ghi chú. Với `site-cms-ts`, ADR-0109 đã chọn Astro, Decap CMS và nhà cung cấp Git để xác thực. Starter, kiểm thử CI, tích hợp factory và pilot có chỗ trong T-5057–T-5060. Phần quản trị nghiệp vụ, cấu hình intake và các ca ADM dưới đây là đề xuất. [Mẫu web hiện có](https://github.com/www-donghanhcungban-org/X-Templates/tree/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/framework/templates/packs/web-api-ts) · [Quyết định CMS](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/adr/0109-site-cms-ts-pack.md)

| Hình thức | Điều kiện chọn | Ví dụ và việc bàn giao |
|---|---|---|
| Công cụ hiện có | Người phụ trách làm được tác vụ bằng Git, nhà cung cấp dịch vụ hoặc công cụ nội bộ. | Landing page ít đổi. Bàn giao quyền sửa, xem thử, xuất bản và phục hồi một thay đổi. |
| CMS biên tập | Nội dung có nháp, xem trước, duyệt hoặc xuất bản theo lịch biên tập. | Website tin tức. Bàn giao danh sách bài, trình biên tập, quyền xuất bản và lịch sử. |
| Quản trị nghiệp vụ | Nhân viên tra cứu hay thay đổi trạng thái đơn, tài khoản, yêu cầu hoặc cấu hình. | Shop, SaaS, app di động, dịch vụ API. Có thể dùng chung một trang web cho nhân viên qua dịch vụ nghiệp vụ sẵn có. |
| Kết hợp | Một sản phẩm có cả vòng đời nội dung và tác vụ vận hành. | Shop có tin tức. Biên tập viên quản lý bài viết, nhân viên kho xử lý đơn. Hai nhóm dùng quyền riêng kể cả khi dùng chung đăng nhập. |

**Hồ sơ đầu vào.** Trong `PROJECT.md`, đề xuất thêm trường tùy chọn `admin` gồm hình thức, công cụ/pack, danh sách tác vụ ưu tiên, người vận hành, dữ liệu và phạm vi, thao tác khó hoàn tác, người chịu rủi ro, đường khôi phục và sự kiện cần xét lại. Ví dụ, shop ghi “xử lý đơn đã xác nhận · nhân viên kho · chỉ cửa hàng được giao · không có quyền hoàn tiền”. Dự án cũ thiếu trường này được ghi “chưa khảo sát”. Khi nâng cấp, factory hiển thị phần bổ sung để chủ dự án duyệt. Chỉ mở giao diện khi đã có lựa chọn rõ ràng. Tên trường và cách ghép là thiết kế cho PR tương lai. [Factory intake](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/specs/SPEC-factory-intake.md)

## 2. Cấu hình cho dự án nhỏ vừa và lớn

| Mức X-Templates | Phạm vi điển hình | Cách nghiệm thu |
|---|---|---|
| S · thử nghiệm | Một người, dữ liệu giả, môi trường cô lập. Chọn công cụ sẵn có hoặc một tác vụ mẫu. | Người nhận lặp lại tác vụ, thử tài khoản thiếu quyền nếu có đăng nhập, và hoàn tác. Ghi điều kiện phải xét lại khi đưa vào dùng thật. |
| M · có người dùng thật | Ít nhất M khi bàn giao cho người dùng ngoài đội phát triển. Có tài khoản theo người, MFA cho đặc quyền, kiểm phía dịch vụ và nhật ký các thao tác nhạy cảm. | Người vận hành và QA thực hiện luồng thật trên dữ liệu thử. Kiểm bàn phím, trình đọc màn hình, hết phiên, sai quyền và khôi phục. |
| L · nhiều bên hoặc ảnh hưởng cao | Nhiều đội, SLA hợp đồng hoặc kiểm toán ngoài. Với tiền thật hoặc dữ liệu nhạy cảm, ưu tiên L. Ngoại lệ M cần chủ rủi ro, gói ngành và lý do có bằng chứng. | Thử hai phạm vi dữ liệu khi sản phẩm có nhiều khách hàng. Kiểm thu hồi đặc quyền, tác vụ hàng loạt, tách người duyệt khi cần và diễn tập phục hồi có nhân chứng. |

Số lượng màn hình theo số tác vụ. Một shop nhỏ vẫn có thể cần quy trình hoàn tiền có duyệt. Một nền tảng lớn có thể chỉ cần một màn hình xuất báo cáo trong giai đoạn đầu. Mỗi quyết định đổi mức ghi tác vụ nào thay đổi, quyền phát sinh và bộ thử cần chạy lại.

## 3. Danh mục màn hình và luồng ưu tiên

| Khi có nhu cầu | Trang bàn giao | Điểm kết thúc quan sát được |
|---|---|---|
| Quản lý nội dung | Bài viết, soạn/xem trước, chờ duyệt, lịch sử | Bài đã duyệt xuất hiện đúng URL. Người vận hành tìm lại phiên bản và phục hồi được. |
| Xử lý đơn | Hàng đợi theo cửa hàng, chi tiết và lịch sử đơn | Nhân viên tìm đúng đơn và chuyển trạng thái hợp lệ. Hai lần gửi cùng yêu cầu chỉ tạo một chuyển trạng thái. |
| Quản lý thành viên | Danh sách, lời mời, cấp/thu hồi vai trò | Người quản trị chỉ sửa được thành viên thuộc phạm vi của mình. Thu hồi quyền có hiệu lực với phiên đang mở. |
| Chăm sóc người dùng | Hàng đợi yêu cầu, hồ sơ tối thiểu và lịch sử xử lý | Nhân viên xem trường cần dùng, gửi yêu cầu can thiệp và truy được kết quả theo mã vụ việc. |
| Xử lý việc nhạy cảm | Danh sách chờ duyệt, xem thay đổi, xác nhận và biên nhận | Quyết định ghi đúng người đề nghị, người duyệt và nội dung đã được duyệt. Đổi nội dung thì phải duyệt lại. |
| Đối soát hoặc báo cáo | Tra nhật ký, chọn bộ lọc, yêu cầu xuất, trạng thái tệp | Người có quyền tra theo sự kiện. Dữ liệu trong tệp, quyền tải và thời hạn tải khớp chính sách. |

**Trang đầu theo vai trò.** Nhân viên xử lý đơn thấy hàng đợi đang chờ. Biên tập viên thấy bản nháp và bài bị trả lại. Chỉ thêm bảng tổng quan khi có câu hỏi cần trả lời, định nghĩa chỉ số, nguồn dữ liệu và hành động tiếp theo. Các màn hình danh sách lớn có bộ lọc, phân trang phía máy chủ, trạng thái đang tải, trống, không có kết quả, lỗi có thể thử lại và cấm truy cập. Trang chi tiết hiển thị trạng thái hiện hành, lịch sử và hành động khả dụng.

**Luồng tham chiếu cho shop.** Nhân viên kho mở đơn được giao → kiểm trạng thái → xác nhận đã đóng gói → nhận mã biên nhận → thấy sự kiện trong lịch sử. Nếu người khác vừa hủy đơn, dịch vụ từ chối chuyển trạng thái và giao diện mời tải lại. Hoàn tiền là luồng riêng, có hạn mức và quyền riêng do chủ sản phẩm phê duyệt. Tất cả kiểm thử tiền dùng giao dịch mô phỏng.

## 4. Ma trận quyền và hợp đồng dịch vụ

| Vai trò tham chiếu | Trong phạm vi được giao | Giới hạn cần kiểm |
|---|---|---|
| Biên tập viên / người xuất bản | Soạn và gửi duyệt / duyệt và phát hành | Nếu quy trình yêu cầu người duyệt độc lập, tác giả không thể tự phát hành phiên bản vừa gửi. |
| Nhân viên vận hành | Đọc phần dữ liệu cần thiết và thực hiện chuyển trạng thái được giao | Không tự cấp quyền, xuất tệp hay duyệt đề nghị nhạy cảm của mình. |
| Người duyệt | Phê hoặc từ chối yêu cầu theo phạm vi, hạn mức và phiên bản | Không sửa nội dung âm thầm trong lúc phê. Hết hạn hoặc có thay đổi thì lập lại yêu cầu. |
| Quản trị tổ chức | Mời, khóa, thu hồi vai trò trong tổ chức mình | Không cấp quyền cao hơn trần được giao, chuyển sang tổ chức khác hoặc làm mất đường khôi phục quyền sở hữu. |
| Hỗ trợ / kiểm tra | Hỗ trợ xem dữ liệu đã che. Người kiểm tra đọc dấu vết được giao. | Quyền xem trường đầy đủ, tải tệp, sửa nghiệp vụ và tra nhật ký là các quyền tách riêng. |
| Vận hành nền tảng | Quản lý cấu hình hạ tầng và xử lý sự cố | Truy cập dữ liệu khách hàng cần lý do, phạm vi, thời hạn và dấu vết. Quyền tạm hết hạn tự động. |

**Điểm thực thi.** Mỗi thao tác khai báo đối tượng, hành động, phạm vi tổ chức/cửa hàng, trường được đọc hoặc sửa và trạng thái cho phép. Máy chủ kiểm quyền cho mọi đường gọi, gồm danh sách, tìm kiếm, dữ liệu đếm, chi tiết, lệnh hàng loạt, tệp xuất và tác vụ nền. Lấy danh tính và phạm vi từ phiên đã xác thực. Phạm vi do trình duyệt chọn phải thuộc tập phạm vi đã cấp. Giao diện dùng cùng danh mục quyền để chỉ ra thao tác khả dụng. Quy tắc chưa được định nghĩa dẫn đến từ chối.

**Một hợp đồng mẫu.** Với thao tác “đóng gói đơn”, đầu vào gồm mã đơn, phiên bản mà nhân viên đã xem và mã chống gửi lặp. Dịch vụ xác thực phiên và quyền, kiểm trạng thái rồi ghi thay đổi cùng biên nhận trong một giao dịch. Gửi lại cùng lệnh và nội dung trả về cùng kết quả. Dùng lại mã cho nội dung khác trả xung đột. Khi dùng điều kiện HTTP `If-Match`, phiên bản cũ trả `412`. Xung đột nghiệp vụ trả `409`; hết phiên `401`; sai quyền `403` hoặc `404` theo chính sách che sự tồn tại áp dụng nhất quán. UI giữ bộ lọc và cho phép đọc lại trạng thái. Tác vụ có tác động bên ngoài dùng mã chống lặp và cơ chế đối soát ở phía thực hiện trước khi báo xong.

**Quản lý phiên và vòng đời tài khoản.** Dùng danh tính cá nhân, xác thực đa yếu tố (MFA) cho quyền quản trị môi trường thật, đường khôi phục tài khoản có xác minh và giới hạn phiên nhàn rỗi/tổng thời gian phía máy chủ. Yêu cầu xác thực lại khi thay đổi MFA, thông tin khôi phục hoặc thực hiện thao tác mà chủ rủi ro xếp mức cao. Thu hồi quyền trước lần đọc/ghi đặc quyền kế tiếp. Kiểm lại quyền ở thời điểm thực hiện công việc nền còn chờ. Nếu sản phẩm yêu cầu hai người phê và đội chỉ có một người, dùng quy trình phê duyệt hiện hữu hoặc để tác vụ đó ngoài phạm vi pilot. [ASVS V6](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x15-V6-Authentication.md) · [ASVS V7](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x16-V7-Session-Management.md) · [ASVS V8](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x17-V8-Authorization.md)

## 5. Chuẩn áp dụng và bằng chứng

Đội ghi rõ phiên bản chuẩn, phạm vi màn hình/dịch vụ, tiêu chí áp dụng, cách thử, kết quả và người rà. S/M/L mô tả quy mô và rủi ro vận hành của dự án. Mức ASVS mô tả phạm vi kiểm chứng bảo mật. AAL của NIST mô tả mức bảo đảm xác thực. Chọn và ghi lý do cho từng mức. Các kiểm soát dưới đây là đầu mối cho thiết kế và thử nghiệm. Muốn công bố phù hợp toàn bộ một mức phải đánh giá toàn bộ các yêu cầu áp dụng của mức đó.

| Tham chiếu | Cách dùng trong trang quản trị | Bằng chứng cần lưu |
|---|---|---|
| OWASP ASVS 5.0.0, V8.1.1, V8.2.1–3, V8.3.1 và V8.4.1 khi đa tổ chức | Ma trận tác vụ, bản ghi, trường và phạm vi. Cưỡng chế trong dịch vụ tin cậy. | Ca cho phép và từ chối theo vai trò. Đối chiếu danh sách đường gọi, tác vụ nền và tệp xuất. |
| ASVS V6.3.3, V7.3–5 và NIST SP 800-63B-4 §2 | MFA, thời hạn phiên, đăng xuất, thu hồi và khôi phục. Khi chọn AAL2, xét đầy đủ yêu cầu gồm hai yếu tố và lựa chọn xác thực chống lừa đảo. | Cấu hình nhà cung cấp danh tính, thử thiếu yếu tố, thu hồi phiên và thử khôi phục đúng chủ tài khoản. |
| ASVS V3.5 và V16.1–4 | Bảo vệ thao tác đổi trạng thái qua trình duyệt theo cơ chế xác thực. Kiểm soát lưu, đọc và vòng đời nhật ký. | Ca yêu cầu thiếu bảo vệ bị từ chối, kiểm bản ghi theo mã yêu cầu và quyền đọc/sửa nhật ký. |
| WCAG 2.2, mục tiêu A và AA | Bao trọn các trang và mọi bước của luồng web đã nêu, kể cả đăng nhập, MFA, duyệt, thông báo kết quả. | Ma trận tiêu chí, kiểm tự động và kiểm tay bằng bàn phím/trình đọc màn hình, ghi môi trường và lỗi tồn. |
| W3C Privacy Principles, tối thiểu hóa dữ liệu | Liệt kê trường nào cần cho từng tác vụ, chủ dữ liệu, trường được xuất và thời hạn lưu. | Đối chiếu phản hồi dịch vụ, tệp tải và log với danh sách trường cho phép. |

[OWASP ASVS 5.0.0](https://github.com/OWASP/ASVS/releases/tag/v5.0.0) · [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b/aal/) · [WCAG 2.2](https://www.w3.org/TR/WCAG22/) · [W3C Privacy Principles](https://www.w3.org/TR/privacy-principles/#data-minimization). Nguồn đối chiếu ngày 27/11/2026.

**Khả năng tiếp cận trong luồng thật.** Danh sách dùng tiêu đề cột gắn được với ô dữ liệu. Mọi chức năng chính thao tác được bằng bàn phím, thứ tự focus hợp lý, dấu focus nhìn thấy và không bị thanh cố định che hoàn toàn (2.1.1, 2.4.3, 2.4.7, 2.4.11). Ở bề rộng 320 CSS px, nội dung thông thường đọc được với một chiều cuộn. Nếu bảng cần hai chiều, giữ phần cuộn trong bảng (1.4.10). Kiểm tương phản chữ/nút, nhãn trường, mô tả lỗi và thông báo trạng thái cho trình đọc màn hình (1.4.3, 1.4.11, 3.3.1–2, 4.1.3). Cho phép trình quản lý mật khẩu và dán thông tin xác thực, thử cả bước MFA (3.3.8). Với thao tác thay đổi dữ liệu thuộc 3.3.4, có cách hoàn tác, kiểm lỗi trước khi gửi hoặc xem lại và xác nhận. Hộp thoại có tên, giữ focus khi mở và trả focus hợp lý khi đóng. [Phạm vi phù hợp WCAG](https://www.w3.org/TR/WCAG22/#conformance-reqs) · [Hướng dẫn hộp thoại](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)

**Đối chiếu trong X-Templates.** Dùng lại PRF-WEB-020, PRF-STATIC-018/019 cho khu vực đặc quyền, BE-AUTH-005/009/010/013 cho phiên và quyền, IND-SAAS-001–004 khi có nhiều tổ chức, SEC-LOG-001/002/007 cho nhật ký, UX-A11Y và QA-E2E cho kiểm tự động và kiểm tay. Với CMS đặt nội dung trong Git, cần kiểm riêng từng ranh giới do đội vận hành, gồm giao diện admin, proxy OAuth và cấu hình của Git host. Ghi rõ bằng chứng nào do nhà cung cấp giữ. [Hồ sơ web](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/framework/02-profiles/web-app.md) · [Hồ sơ site tĩnh](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/framework/02-profiles/static-site.md) · [Nghiệm thu giao diện](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/framework/14-testing-quality/e2e-and-accessibility.md)

## 6. Dữ liệu nhật ký và phục hồi

**Dữ liệu.** Danh sách trả các trường tối thiểu từ máy chủ. Quyền mở một trường đã che tách khỏi quyền đọc hồ sơ. Tệp xuất gắn người yêu cầu, phạm vi tổ chức, trường được phép, thời hạn và chính sách tải. Dịch vụ xác thực lại người tải và quyền còn hiệu lực. Khi dự án thuộc phạm vi pháp luật Việt Nam về dữ liệu cá nhân, chủ dữ liệu cùng người phụ trách pháp lý đối chiếu mục đích xử lý, phạm vi chia sẻ, thời hạn lưu/xóa và cách tiếp nhận yêu cầu của chủ thể. Chốt lịch lưu riêng theo loại dữ liệu, hợp đồng và căn cứ áp dụng. [Luật 91/2025/QH15](https://chinhphu.vn/?docid=214590&pageid=27160) · [Nghị định 356/2025/NĐ-CP](https://chinhphu.vn/?docid=216387&pageid=27160)

**Nhật ký.** Mỗi hành động nhạy cảm ghi thời điểm UTC, tác nhân, phạm vi, hành động, mã đối tượng tối thiểu, kết quả, mã tương quan và lý do khi cần. Với AI hoặc việc nền, ghi cả chủ thể ủy quyền, tác nhân thực thi và tham chiếu phê duyệt. Ghi đăng nhập thành công/thất bại, từ chối quyền, đổi vai trò, xuất dữ liệu và sự kiện nghiệp vụ nhạy cảm. Mang cùng mã tương quan khi ghi ở nhiều hệ thống. Bảo vệ nhật ký khỏi sửa/xóa bằng quyền ứng dụng. Một tác vụ riêng thi hành retention và lưu dấu đã xử lý. Không đưa mật khẩu, token, nội dung hồ sơ hay thông tin thanh toán thô vào log. [ASVS V16](https://github.com/OWASP/ASVS/blob/v5.0.0/5.0/en/0x25-V16-Security-Logging-and-Error-Handling.md)

**Khi lỗi.** Lệnh nhạy cảm phải ghi được dấu vết bền vững trong cùng giao dịch hoặc hàng đợi sự kiện bền vững trước khi báo thành công. Nếu mất kết nối sau khi gửi lệnh, hiển thị trạng thái chưa xác định và cho phép tra biên nhận. Với hệ thống ngoài, đối soát kết quả trước khi thử lại. Khi lùi bản, tắt quyền ghi của mô-đun, giữ lối vận hành cũ và đối soát giao dịch đã nhận. Dùng phục hồi phiên bản nội dung hoặc bút toán/giao dịch bù theo nghiệp vụ. Ghi người có thẩm quyền, điểm khôi phục và kết quả diễn tập. Với dữ liệu thật, kiểm việc phục hồi không làm sống lại quyền hoặc tệp xuất đã thu hồi.

## 7. Lộ trình triển khai và liên kết với backlog

Các bước dưới đây là thứ tự phụ thuộc của phần quản trị. Người duy trì đưa PR vào lịch chung đã có. Các khoảng công dưới đây là ước tính ban đầu theo ngày công, giả định đã có môi trường thử, danh tính thử và một người vận hành tham gia. Ước lượng lại sau khi đo luồng đầu tiên. Mọi phép thử dùng dữ liệu giả hoặc đã được phép dùng cho mục đích này.

| Gói công việc | Chủ trì và phụ thuộc | Bàn giao và điều kiện chuyển bước |
|---|---|---|
| A · khảo sát và factory, 1–2 ngày | Chủ sản phẩm + người duy trì Core | Hồ sơ quyết định, quy tắc cho repo cũ và ba ví dụ S/M/L. Một lập trình viên khác ghép lại cùng đầu vào ra cùng phạm vi. |
| B · danh mục quyền và giao diện, 2–4 ngày | Backend + thiết kế, sau A | Danh mục tác vụ/quyền, trường dữ liệu, phác thảo danh sách và trang chi tiết. QA duyệt ca cho phép và từ chối trước khi viết luồng. |
| C · một luồng nghiệp vụ, 3–5 ngày | Chủ pack web, sau B | Dịch vụ, UI, nhật ký, lỗi lặp/xung đột và đường phục hồi. Trình diễn trọn một tác vụ. Chỉ bật mô-đun trên dự án đã chọn. |
| D · luồng nội dung, theo lịch CMS | Chủ pack CMS, sau A; phối hợp B khi có danh tính dùng chung | Tái sử dụng T-5057–T-5060. Bổ sung bằng chứng phân vai, OAuth, bản dựng đã duyệt và phục hồi phiên bản. |
| E · thử độc lập và bàn giao, 2–4 ngày | QA, người vận hành và chủ phát hành, sau luồng tương ứng | Thử khả năng tiếp cận, sai quyền, cách ly dữ liệu và sự cố. Ghi kết quả từng ca, học cách vận hành và ký theo phạm vi. |

**Ba pilot.** S dùng một site dữ liệu giả với người mới nhận việc sửa và phục hồi nội dung qua công cụ đã chọn. M dùng shop mô phỏng để hai nhân viên xử lý cùng một đơn và đối soát kết quả. L dùng hai tổ chức giả trong SaaS để thử quản trị thành viên, yêu cầu hỗ trợ có thời hạn, thu hồi quyền và xuất báo cáo. Mỗi pilot đo thời gian hoàn thành, lỗi, số lần cần trợ giúp và kết quả phục hồi. Người phụ trách chốt ngưỡng thành công theo tác vụ trước khi chạy. Kết quả của một pilot có giá trị cho luồng, cấu hình và phiên bản đã thử. [Backlog CMS](https://github.com/www-donghanhcungban-org/X-Templates/blob/6adbd4ade5a2a4188c6c3404740f1913e40ea60d/docs/autopilot/PLAN-site-cms-2026-11-26.md)

## 8. Ma trận nghiệm thu và quyết định bàn giao

Các mã ADM là mã ca thử đề xuất dành cho công việc này. Chủ dự án chọn ca theo hình thức và rủi ro ở mục 1–2. Mỗi ca cần phiên bản, dữ liệu thử, người thực hiện và bằng chứng. Nếu ghi “không áp dụng”, nêu lý do và ranh giới mà một bên khác sở hữu.

| Ca | Tình huống thử | Kết quả chấp nhận |
|---|---|---|
| ADM-01 | Tạo site S dùng Git, sau đó nâng một repo cũ thiếu trường admin. | Lưu quyết định và người vận hành. Repo cũ hiển thị đề xuất bổ sung, vẫn dựng được; không tự mở quyền mới. |
| ADM-02 | Đăng nhập quyền quản trị môi trường thật, thử thiếu MFA, hết hạn nhàn rỗi/tổng và đăng xuất. | Phiên không đủ điều kiện bị từ chối. Người dùng quay về luồng đăng nhập tiếp cận được. |
| ADM-03 | Thử đúng vai, sai vai và dùng đường gọi dịch vụ trực tiếp trên dữ liệu mẫu. | Dịch vụ chỉ cho phép đúng quyền và phạm vi. Dữ liệu và nhật ký cho thấy quyết định đúng. |
| ADM-04 | Dùng hai tổ chức giả để tìm kiếm, mở chi tiết, đếm, chạy việc nền và tải tệp. | Mỗi kênh chỉ trả dữ liệu thuộc tổ chức được cấp. Không suy ra bản ghi của tổ chức còn lại từ kết quả đếm. |
| ADM-05 | Hai nhân viên cùng xử lý đơn, một người gửi lại lệnh sau khi mất kết nối. | Một thay đổi nghiệp vụ và một biên nhận cho cùng yêu cầu. Phiên bản cũ bị từ chối, người dùng thấy cách tải lại. |
| ADM-06 | Gửi đề nghị vượt hạn mức, tự duyệt và thay nội dung sau duyệt. | Dịch vụ áp đúng hạn mức và tách vai theo chính sách. Người duyệt thấy nội dung mới trước khi quyết định lại. |
| ADM-07 | Khóa thành viên khi họ đang dùng trang quản trị và còn một việc đặc quyền chờ chạy. | Yêu cầu tiếp theo và việc nền chưa thực hiện bị kiểm lại. Nhật ký ghi thu hồi quyền. |
| ADM-08 | Kiểm trường trả về trong danh sách, tệp xuất và log; hết hạn hoặc thu hồi quyền tải. | Chỉ có các trường được cấp. Tệp hết hạn/sai người không tải được. Không có bí mật trong nhật ký. |
| ADM-09 | Dùng bàn phím và trình đọc màn hình từ đăng nhập tới trang xác nhận. Kiểm ở bề rộng 320 CSS px. | Có thể hoàn tất luồng, nhận biết lỗi và kết quả, không mất focus. Các lỗi với tiêu chí AA trong phạm vi đã ghi được xử lý. |
| ADM-10 | Biên tập viên gửi nháp, người xuất bản duyệt, rồi khôi phục bài trước đó. | Truy được URL công khai, phiên bản nội dung, bản dựng và người duyệt. Quyền truy cập CMS đúng vai. |
| ADM-11 | Trong môi trường thử, làm gián đoạn đường ghi audit ở một lệnh nhạy cảm; khôi phục và đối soát. | Không báo thành công khi thiếu dấu vết bền vững. Khôi phục xác định được tác vụ đã ghi/chưa ghi và tránh tác động lặp. |
| ADM-12 | Người vận hành mới nhận bàn giao, xử lý một yêu cầu và lùi mô-đun về đường vận hành cũ. | Người nhận hoàn thành theo hướng dẫn, biết ai xử lý sự cố, tra được biên nhận và ký kết quả. |

**Điều kiện phát hành.** Mỗi tác vụ được bật có chủ sở hữu, ma trận quyền, dữ liệu thử và biên bản kiểm chức năng, quyền, khả năng tiếp cận và phục hồi theo phạm vi. Chặn bàn giao luồng có truy cập ngoài quyền, lộ dữ liệu giữa tổ chức, nhân đôi giao dịch, mất dấu vết bắt buộc hoặc người sử dụng không hoàn tất được tác vụ thiết yếu. Ghi người sửa và ca cần chạy lại. Nếu giảm phạm vi, tắt phần chưa đạt, cập nhật hồ sơ và kiểm lại phần còn bật.

**Phiếu ký.** Ghi sản phẩm, phiên bản, môi trường, hình thức quản trị, tác vụ đã bật, kết quả ADM, tiêu chí chuẩn đã rà, phần do nhà cung cấp đảm nhiệm, lỗi còn mở, quyết định phát hành và đầu mối phục hồi. Chủ sản phẩm ký phạm vi, người vận hành ký luồng công việc, QA ký bằng chứng và chủ phát hành ký quyết định đưa vào sử dụng.
