# Danabus Roadmap V3 - Planner, độ chính xác dữ liệu và UX người dùng

**Ngày:** 2026-09-30
**Trạng thái:** PO đã duyệt - sẵn sàng tạo và triển khai Task
**Workspace:** `/home/opc/danabus`

## Mục tiêu

Nâng Danabus từ PWA tra cứu tuyến thành công cụ tìm hành trình đơn giản cho người dùng phổ thông, dựa trên dữ liệu dịch vụ chính thức, địa chỉ cụ thể, trạm lên/xuống phù hợp, hành trình nhiều tuyến, geometry đã xác minh và UX tối giản.

## Nguyên tắc bắt buộc

- Ưu tiên dữ liệu chính thức.
- Thiếu hoặc chưa xác minh route, stop, geometry, schedule, fare, walking hay realtime thì phải fail-closed.
- Chọn trạm phù hợp nhất cho toàn hành trình, không chỉ chọn trạm gần nhất.
- Ưu tiên direct > 1 transfer > 2 transfers.
- Không đề xuất route inactive/suspended/expired.
- Giữ Leaflet/OSM cho hiển thị bản đồ.
- Capability từ external provider phải được cô lập sau provider abstraction.
- UX chính chỉ cần trả lời một câu hỏi: đi từ A đến B như thế nào?
- Không dùng nhãn realtime nếu chưa có provider realtime được phê duyệt.

## Task 1 - Đối chiếu dữ liệu tuyến chính thức và mô hình dịch vụ theo thời gian

Đối chiếu toàn bộ route records với nguồn DanangBus chính thức.

Phạm vi:
- So sánh mã tuyến, tên, alias, mã lịch sử, trạng thái tuyến, thay đổi dịch vụ, lịch chạy và provenance chính thức.
- Chuẩn hóa các trạng thái `active | suspended | merged | retired`.
- Bổ sung các trường thời gian và provenance như `effectiveFrom`, `effectiveTo`, `sourceUrl`, `sourcePublishedAt`, `lastVerifiedAt`, `serviceVersion`, `supersededBy`, `mergedInto`.
- Tách dữ liệu tuyến lâu dài khỏi temporary service override như detour hoặc tạm ngưng.
- Giữ lịch sử tuyến thay vì xóa.
- Planner chỉ được dùng service record còn hiệu lực tại thời điểm query.

Tiêu chí nghiệm thu:
- 100% route records có provenance.
- Route inactive/suspended/expired không thể xuất hiện trong kết quả hành trình.
- Alias và merged-route resolve deterministic.
- Temporary override hết hiệu lực đúng thời điểm.
- Có reconciliation report máy đọc được.
- Regression search/schedule/planner vẫn PASS.

## Task 2 - Tìm địa chỉ, geocoding và chọn trạm lên/xuống phù hợp

Phạm vi:
- Hỗ trợ địa chỉ cụ thể, tên địa điểm, GPS hiện tại, map pin và swap A/B.
- Dùng Google Places Autocomplete (New) + place details/geocoding qua provider abstraction.
- Bias/restrict khu vực Đà Nẵng - Hội An, tiếng Việt, debounce, session token, field mask tối thiểu, API key bị giới hạn và không commit key vào repo.
- Khi provider lỗi phải fallback sang GPS/map-pin/tìm stop hoặc landmark local và không được làm app crash.
- Candidate stop resolver phải xét nhiều trạm verified gần vị trí, không chọn nearest stop một cách máy móc.
- Loại stop sai direction, route inactive, candidate không kết nối được hoặc dữ liệu thiếu độ tin cậy.
- Rank candidate pair theo walking cost, transfer penalty, transit cost, service validity và data confidence.
- Radius khởi đầu khoảng 800 m; chỉ mở rộng có kiểm soát tới khoảng 1.5 km và phải báo rõ cho user.

Tiêu chí nghiệm thu:
- Address input resolve ra tọa độ hợp lệ.
- Planner có thể loại một stop gần hơn nếu sai direction hoặc không tới được destination.
- GPS origin hoạt động.
- Provider timeout/429/error phục hồi được.
- No-result giải thích được nguyên nhân.
- Có test duplicate street names và địa chỉ ngoài service area.

## Task 3 - Multi-Transfer Transit Graph Planner

Phạm vi:
- Thay giới hạn planner tối đa 1 transfer bằng graph-based routing.
- Node biểu diễn stop + direction.
- Edge gồm ride, board/alight, walking transfer, origin walk và destination walk.
- Search state gồm stop, route, direction và transfer count.
- Tìm direct trước, sau đó 1 transfer, sau cùng tối đa 2 transfers mặc định.
- Chặn route loop, backtracking vô lý, inactive route, unresolved transfer stop và direction chưa planner-ready.
- Hỗ trợ minimum transfer time và giới hạn khoảng cách chuyển trạm.
- Rank theo số lần đổi xe ít hơn, walking thấp hơn, service hợp lệ, travel cost/time ước tính và data confidence.
- Trả ordered leg contract: WALK -> BUS -> WALK_TRANSFER -> BUS -> ... -> WALK.

Tiêu chí nghiệm thu:
- Test trên dataset thật cho direct, 1-transfer, 2-transfer và no-route.
- Không loop và không dùng inactive route.
- Không transfer tại unresolved stop.
- Ranking deterministic.
- Mục tiêu compute local <250 ms sau khi đã resolve origin/destination trên dataset hiện tại.

## Task 4 - Hoàn thiện GPS, stop và shape coverage cho các tuyến active

Phạm vi:
- Ưu tiên tuyến chính thức đang active, tuyến có vai trò transfer cao, urban core, sau đó mới tới intercity/outlying.
- Không tốn công hoàn thiện historical/suspended route chỉ để tăng tỷ lệ coverage.
- Tạo geometry candidate từ official street sequence kết hợp OSM/OSRM hoặc nguồn đã phê duyệt.
- Validate stop order monotonic, stop-to-shape distance, direction, route-distance sanity và provenance.
- Chỉ đánh dấu direction planner-ready khi pass đầy đủ data-quality contract.
- Cải thiện map rendering cho bus geometry, walking leg, boarding/transfer/alighting markers và fit bounds toàn hành trình.
- Mặc định ẩn bớt stop labels để tránh rối.

Mục tiêu release:
- 100% journey được planner đề xuất phải dùng verified geometry.
- Không có unresolved boarding/alighting stop.
- Mục tiêu ban đầu >=90% active directions có verified shape.
- Mục tiêu ban đầu >=85% stop-direction trên active network được verified.
- Phần còn thiếu tiếp tục fail-closed.

## Task 5 - Thiết kế lại UX đơn giản cho người dùng phổ thông

Màn hình Home chính:
- `Đi từ đâu?`
- `Đến đâu?`
- vị trí hiện tại
- swap
- `Tìm đường`

Phạm vi:
- Chuyển route catalog/map exploration thành secondary navigation.
- Kết quả mặc định chỉ mở một hành trình khuyến nghị.
- Summary hiển thị tổng thời gian, số lần đổi xe, walking và fare chỉ khi đã verified.
- Journey timeline hiển thị các bước đi bộ/bus/chuyển tuyến đơn giản.
- Secondary actions gồm phương án khác, bản đồ, các trạm và chi tiết tuyến.
- Ẩn provenance, raw dataQuality, fleet metadata, geometry diagnostics và technical IDs khỏi primary cards.
- Mobile-first với timeline/bottom-sheet.
- Dùng semantics trung thực: `Theo lịch`, `Ước tính`, `Không có dữ liệu`; chỉ ghi realtime khi thực sự có.
- Accessibility gồm keyboard, focus order, screen-reader labels, live status, contrast và touch targets.

Tiêu chí nghiệm thu:
- Browser test mobile + desktop cho autocomplete, GPS, swap, direct journey, transfer journey, no-route, provider failure, dataset failure và accessibility.
- Người dùng phổ thông hoàn thành flow A -> B mà không cần mở chi tiết kỹ thuật.

## Task 6 - Nghiệm thu end-to-end và cổng phát hành production

Phạm vi:
- Final matrix bao gồm official reconciliation, temporal route status, geocoding, best-stop ranking, direct/1/2-transfer planner, inactive-route rejection, GPS/geometry, schedule/fare semantics, provider failures, PWA fresh/warm/offline, mobile UX, accessibility và fail-closed.
- Bump PWA cache/release identity.
- Xác minh critical assets local và production khớp nhau.
- Ghi version của official route dataset trong release report.
- Xác minh không có API secret trong browser bundle hoặc repository.
- Yêu cầu repeated clean-state browser PASS và production smoke PASS.

Artifact:
- final acceptance report;
- official route reconciliation report;
- planner coverage JSON;
- browser evidence;
- release/version manifest.

## Thứ tự triển khai bắt buộc

`Task 1 -> Task 2 -> Task 3 -> Task 4 -> Task 5 -> Task 6`

Lý do:
- Phải khóa đúng dữ liệu trước khi mở rộng planner.
- Address/best-stop resolver phải ổn định trước multi-transfer search.
- Output contract của planner phải ổn định trước khi hoàn thiện UX.
- GPS coverage phải đáp ứng tính trung thực của planner trước final release gate.

## Ngoài phạm vi Roadmap V3

- Không giả realtime vehicle/ETA.
- Không bịa road-walking distance.
- Không phục hồi suspended route chỉ để tăng coverage.
- Không thay toàn bộ Leaflet/OSM bằng Google Maps.
- Không cho số lần transfer vô hạn.
- Không triển khai payment/ticketing.
- Không đưa debug/data-quality metadata ra primary consumer UI.

## Definition of Done của Roadmap V3

- Dữ liệu dịch vụ hiện hành có provenance chính thức và temporal validity.
- User nhập được địa chỉ cụ thể và nhận boarding/alighting stop phù hợp.
- Direct, 1-transfer và 2-transfer deterministic.
- Planner không dùng route/stop/geometry dưới ngưỡng độ tin cậy.
- GPS coverage của active routes đạt release target đã duyệt.
- Primary UX đủ đơn giản cho người dùng không kỹ thuật.
- Local và production acceptance đều PASS.
- Mọi limitation còn lại được hiển thị trung thực, không fabricate.
