# Task 9 Plan - UI Integrity, Realtime Semantics & Accessibility

Task-ID: tsk_e8940d90-789f-4e1f-b311-0b58a8a44e59

## Mục tiêu

Làm cho production UI của Danabus chỉ thể hiện capability và dữ liệu thực sự có, phân biệt rõ schedule-derived với realtime, loại bỏ demo action giả, và đạt accessibility baseline cho zoom, native controls, keyboard/focus/ARIA.

Task này không triển khai realtime vehicle provider mới và không triển khai Address-to-Address Trip Planner.

## Baseline đã xác minh

Các điểm production hiện tại cần xử lý:

1. `index.html` khóa pinch-to-zoom bằng `maximum-scale=1.0, user-scalable=no`.
2. Meta/hero wording có thể khiến người dùng hiểu ứng dụng có realtime: `thời gian thực`, `xe buýt trực tiếp`.
3. `startSpotlightTicker()` và trip result dùng `calculateNextDeparture()` từ schedule nhưng hiển thị countdown/pulse như realtime; có trạng thái text `Đang chạy`/`Còn X phút` không nêu nguồn lịch.
4. `#btn-floating-map` ghi `Xem bản đồ số & Theo dõi trực tiếp` nhưng handler chỉ mở map route.
5. `#home-voice-btn` là simulation: sau 1.2s tự điền `Phố cổ Hội An`, không có permission/listening/transcript thật.
6. Trip result có UI fallback/hard-code dễ fabricate dữ liệu: distance fallback `35 km`, stop count fallback `29`, fleet/amenity text hard-coded như `Xe Kim Long` và `Máy lạnh 100%`; route label fallback không dựa đầy đủ trên provenance.
7. Một số action chính dùng `div/section onclick` thay vì native control, và icon-only buttons còn thiếu accessible name rõ ràng.
8. CSS chưa có focus-visible baseline rõ ràng.
9. Production không thấy reminder implementation trong `index.html`/`js/app.js`; vì vậy Task 9 không được thêm demo reminder giả chỉ để khớp mockup.

## Quyết định kỹ thuật đề xuất cho vòng TL -> DEV discussion

### A. Schedule vs realtime

- Giữ `calculateNextDeparture()` như schedule-derived contract đã được Task 7 verify.
- UI phải gắn nguồn rõ: `Theo lịch`, `Chuyến dự kiến theo lịch`, hoặc wording tương đương.
- Không dùng `Live`, `trực tiếp`, `Đang chạy` hay pulse/animation ngụ ý vehicle tracking khi không có realtime provider.
- CTA map chỉ mô tả capability thật: xem bản đồ/lộ trình GPS tĩnh + GPS vị trí người dùng, không nói theo dõi xe trực tiếp.

### B. Voice

Ưu tiên phương án nhỏ và fail-closed: disable hoặc hide voice action với wording `Chưa hỗ trợ tìm kiếm bằng giọng nói` thay vì triển khai Web Speech API trong Task 9.

Chỉ chọn real voice flow nếu DEV chứng minh được permission -> listening -> transcript -> search có browser fallback/error rõ ràng và testable trong scope hiện tại.

### C. Reminder

- Không thêm reminder nếu production hiện không có persistence + trigger + notification + cancel/update.
- Nếu có action reminder bị phát hiện thêm trong production path, disable/hide với state trung thực.

### D. UI data integrity

- Không dùng numeric/text fallback giả cho distance, stop count, fleet, amenity, seat/vehicle state.
- Khi source không có field hợp lệ, render `Chưa có dữ liệu` hoặc ẩn block tương ứng.
- Vehicle type chỉ render từ field dataset hợp lệ; không suy luận bằng danh sách route hard-code nếu không có provenance được Task hiện tại cho phép.

### E. Accessibility

- Viewport giữ `width=device-width, initial-scale=1.0, viewport-fit=cover`; bỏ zoom lock.
- Action chính phải là native `button`/`a` khi semantic phù hợp.
- Icon-only controls có `aria-label`/accessible name.
- Bổ sung focus-visible state đủ tương phản, không dựa riêng vào hover.
- Keyboard Enter/Space phải kích hoạt action chính đúng một lần; focus không bị mất vô lý sau modal/view transition.
- Dynamic status/error cần cân nhắc `aria-live` phù hợp, tránh spam screen reader.

## File dự kiến

- `index.html`
- `js/app.js`
- `css/app.css`
- Có thể `js/busService.js` chỉ nếu cần expose metadata/provenance đã tồn tại; không đổi schedule contract Task 7.
- Thêm test Task 9 dưới `scripts/` nếu cần để khóa regression interaction/accessibility.

Không sửa các Stitch template chỉ để làm đẹp nếu chúng không nằm trên production runtime path.

## Acceptance matrix Task 9

1. Không còn `user-scalable=no` hoặc `maximum-scale=1.0` trên production viewport.
2. Không còn production wording ngụ ý realtime vehicle tracking khi chỉ có schedule/static route/GPS user.
3. Schedule countdown/status có label nguồn lịch và không biểu diễn như live ETA.
4. Voice action không tạo fake transcript/fake success.
5. Reminder không tạo fake scheduling success.
6. Missing route fields không biến thành fake distance/stop/fleet/amenity values.
7. Các action chính có native semantics hoặc keyboard contract tương đương; icon-only controls có accessible name.
8. Focus-visible baseline tồn tại và keyboard path chính PASS.
9. Loading/empty/error/offline state không collapse thành success hoặc fabricated data.
10. Regression Task 6 Search, Task 7 Schedule/Fare, Task 8 Data Quality, Map/GPS và security smoke vẫn PASS.

## Verification dự kiến

- Static grep/assert cho viewport, realtime wording, fake voice handler và hard-coded UI fallback.
- Browser interaction test cho keyboard/focus, voice disabled/fail-closed, no-result/error states.
- Browser smoke hiện có.
- `scripts/test_search_correctness.py`
- `scripts/test_schedule_and_fare.py`
- `scripts/test_data_quality_and_planner_readiness.py`
- `scripts/test_map_and_gps.py`
- `scripts/security_smoke_test.py`
- `scripts/test_browser_schedule_and_fare.py`

## Out of scope

- Realtime vehicle GPS/ETA provider mới.
- Full notification scheduler/reminder infrastructure mới nếu chưa tồn tại.
- Address-to-Address Trip Planner.
- Business-logic regression wave tổng thể của Task 10 ngoài regression cần thiết để bảo vệ thay đổi Task 9.

## Handoff discussion cần DEV phản biện

DEV cần kiểm tra và phản hồi ngắn gọn:

1. Có production path nào khác ngoài `index.html` + `js/app.js` đang expose fake realtime/voice/reminder không?
2. Với voice, chọn disable/hide hay real Web Speech flow; nêu tradeoff/testability.
3. Liệt kê các hard-coded/fallback UI values thuộc Task 9 cần fail-closed.
4. Đề xuất test tối thiểu để chứng minh keyboard/focus/ARIA/zoom và offline/error semantics mà không lấn sang Task 10.
