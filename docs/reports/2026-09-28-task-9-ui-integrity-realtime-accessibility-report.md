# Báo Cáo Triển Khai Kỹ Thuật: Task 9 - UI Integrity, Realtime Semantics & Accessibility

Task-ID: tsk_e8940d90-789f-4e1f-b311-0b58a8a44e59

- **Dự án:** Danabus (`danabus.638686.xyz`)
- **Người thực hiện:** Developer (DEV)
- **Người nhận bàn giao:** Tech Lead (TL)
- **Ngày thực hiện:** 28/09/2026
- **Trạng thái:** TL VERIFIED PASS - TECHNICAL ACCEPTANCE

---

## 1. Phạm Vi Triển Khai (Scope)

Triển khai đầy đủ theo kế hoạch đã thống nhất tại [`docs/plans/2026-09-28-task-9-ui-integrity-realtime-accessibility-plan.md`](file:///home/opc/danabus/docs/plans/2026-09-28-task-9-ui-integrity-realtime-accessibility-plan.md) và chỉ đạo của TL:

1. **Khôi phục Quyền Trợ năng Phóng to (Viewport Zoom Lock Removal)**:
   - Loại bỏ `maximum-scale=1.0` và `user-scalable=no` khỏi thẻ `<meta name="viewport">` trong [`index.html`](file:///home/opc/danabus/index.html).
   - Giữ chuẩn `width=device-width, initial-scale=1.0, viewport-fit=cover` cho phép người khiếm thị / người dùng di động tự do pinch-to-zoom theo chuẩn WCAG 2.1 AA.

2. **Chuẩn hóa Ngữ Nghĩa Lịch Trình vs. Realtime (Truthful Schedule Semantics)**:
   - Loại bỏ toàn bộ các cụm từ gây ngộ nhận realtime trong deliverables:
     - `index.html`: Thay meta description `thời gian thực` bằng `lịch trình xuất bến`; thay hero text `xe buýt trực tiếp` bằng `lịch trình xe buýt`; thay CTA `#btn-floating-map` `Xem bản đồ số & Theo dõi trực tiếp` bằng `Xem bản đồ số & Lộ trình trạm`.
     - `manifest.json`: Loại bỏ `thời gian thực`, cập nhật mô tả PWA theo đúng dữ liệu lịch trình.
     - `js/app.js`: Sửa subheader bản đồ từ `Định vị GPS trực tiếp` thành `Lộ trình & trạm dừng GPS`.
   - Toàn bộ countdown và trạng thái chạy xuất phát từ `calculateNextDeparture()` được gắn nhãn nguồn lịch minh bạch: `Theo lịch: Chuyến tới...`, `Theo lịch: Đang hoạt động...`, `Theo lịch: Chuyến đầu...`, `Theo lịch: Hết chuyến...`.
   - Loại bỏ các animation nhấp nháy (`animate-pulse`) ngụ ý live telemetry tại spotlight clock, trạng thái tuyến và countdown tìm chuyến.

3. **Liêm Chính Chức Năng Giọng Nói & Nhắc Nhở (Voice & Reminder Integrity)**:
   - Nút tìm kiếm giọng nói (`#home-voice-btn`, `#picker-voice-btn`): Ẩn (`hidden`, `style="display: none;"`) và vô hiệu hóa (`disabled="true"`, `aria-hidden="true"`). Xóa bỏ toàn bộ simulation listener tự động điền giả văn bản `"Phố cổ Hội An"`.
   - Nút nhắc nhở chuyến xe (`#btn-remind-trip`): Ẩn và vô hiệu hóa, xóa bỏ hoàn toàn hàm gọi `alert()` giả lập thông báo khi chưa có hạ tầng Push Notification thực tế.

4. **Xóa Bỏ Triệt Để Dữ Liệu Fallback Giả (No-Fake UI Fallbacks)**:
   - Cự ly (`#trip-stat-km`): Sử dụng cự ly thực tế từ dataset `route.distanceKm`; khi thiếu fail-closed hiển thị `Chưa có dữ liệu`, tuyệt đối không fallback hard-code `35 km`.
   - Số trạm dừng (`#trip-stat-stops`): Sử dụng số trạm thực tế theo chiều đi/về; khi thiếu hiển thị `Chưa có dữ liệu`, tuyệt đối không fallback hard-code `29 trạm`.
   - Thời gian di chuyển (`#trip-stat-time`): Dataset Danabus không có trường `duration`, fail-closed ẩn hoàn toàn block thời gian và dấu phân cách, tuyệt đối không hard-code `~75-90 phút`.
   - Thông tin đoàn xe (`#trip-fleet-value` & `#trip-fleet-desc`): Bổ sung hàm `formatRouteVehicleInfo(route)` phân tích nhãn hiệu và sức chứa từ `vehicleInfo` chính thức (Kim Long, GAZ, Huyndai Solati, Samco, Thaco, Tracomeco); khi thiếu fail-closed hiển thị `Chưa có dữ liệu` / `Phương tiện`. Tuyệt đối không gán nhãn hàng loạt `Xe Kim Long` hay `Máy lạnh 100%`.
   - Ghi chú chuyến sau (`#trip-later-note`): Đổi thành `Xuất bến theo lịch trình công bố`, xóa bỏ tuyên bố giả `Đầy đủ ghế ngồi`.
   - Lọc xe điện: Bỏ danh sách mã tuyến hardcode `['02', '03', '09', '13', '14', '21']` trong [`js/busService.js`](file:///home/opc/danabus/js/busService.js) và [`js/app.js`](file:///home/opc/danabus/js/app.js); chỉ lọc các tuyến có nguồn `vehicleInfo` ghi rõ nhiên liệu điện.

5. **Trợ Năng Giao Diện (Accessibility Baseline)**:
   - Thẻ ngữ nghĩa chuẩn: Chuyển đổi các thẻ container clickable (`div`/`section`) thành native button (`#btn-home-origin`, các trạm trong picker `.picker-item`), hoặc bổ sung `role="button"` + `tabindex="0"` (`#home-spotlight-card`, `.route-card`).
   - Accessible Names: Bổ sung thuộc tính `aria-label` và `title` cho tất cả các nút chỉ chứa biểu tượng (`#btn-header-back`, `#btn-swap-locations`, `#btn-clear-route-search`, `#btn-trip-swap`, `#btn-close-picker`, `#btn-map-locate`).
   - Bổ sung `:focus-visible` baseline trong [`css/app.css`](file:///home/opc/danabus/css/app.css) với viền tương phản cao 2px màu xanh ngọc thương hiệu (`#059669`) và shadow nổi bật khi điều hướng bằng phím Tab.
   - Hỗ trợ bàn phím Enter & Space kích hoạt hành động hợp lệ cho các phần tử `[role="button"][tabindex="0"]`.
   - Vùng thông báo động (`aria-live`): Thiết lập `role="alert"` + `aria-live="assertive"` cho `#home-search-error`, `aria-live="polite"` cho `#trip-countdown-timer`, `#route-count-label`, `#picker-current-location-status`.

6. **Triển Khai Trạng Thái Loading / Lỗi / Ngoại Tuyến Thực Tế (Loading/Error/Offline State)**:
   - `BusService.init()`: Bắt fetch failures, kiểm tra `res.ok`, ghi nhận `isLoading`, `isLoaded`, `loadError`, xóa trắng dữ liệu và rethrow lỗi để controller xử lý thay vì nuốt ngoại lệ. Expose `getLoadStatus()`.
   - `DanabusApp.init()`: Tích hợp `loadDataAndRender()`, hiển thị `#app-loading-state` trong khi nạp dữ liệu. Khi gặp sự cố mạng hoặc lỗi dataset, tự động kích hoạt `showErrorState(err)`:
     - Ẩn toàn bộ `.view-screen`, ngăn chặn hoàn toàn việc hiển thị dữ liệu fabricated/rác.
     - Hiển thị `#app-error-state` (`role="alert"`, `aria-live="assertive"`) với thông báo lỗi rõ ràng, phân biệt lỗi ngoại tuyến với lỗi máy chủ.
     - Reset các text counter (`#route-count-label`, `#spotlight-countdown`, `#spotlight-fare`) về trạng thái fail-closed `Chưa có dữ liệu`.
     - Cung cấp nút `#btn-retry-load` ("Thử lại") và tự động lắng nghe sự kiện `window.online` để phục hồi tự động (recovery).

7. **Nâng Cấp Service Worker Cache (danabus-cache-v9)**:
   - Nâng cấp `CACHE_NAME = 'danabus-cache-v9'` trong [`sw.js`](file:///home/opc/danabus/sw.js).
   - Gắn query tham số phiên bản `?v=20260928_v9` cho toàn bộ tài nguyên mutable (`app.css`, `icons.js`, `busService.js`, `mapService.js`, `app.js`) trong [`index.html`](file:///home/opc/danabus/index.html) và `STATIC_ASSETS`.
   - Cơ chế dọn dẹp cache cũ trong `activate` tự động quét và giải phóng toàn bộ cache lỗi thời (`danabus-cache-v4` đến `danabus-cache-v7`).
   - Cập nhật kịch bản kiểm thử [`scripts/browser_smoke_test.py`](file:///home/opc/danabus/scripts/browser_smoke_test.py) để mô phỏng và xác minh việc di trú cache từ `v7` sang `v9`.

---

## 2. Chi Tiết File Thay Đổi

| File | Thay đổi kỹ thuật |
| :--- | :--- |
| [`index.html`](file:///home/opc/danabus/index.html) | Bỏ `maximum-scale=1.0, user-scalable=no`; sửa meta description; chuyển hàng điểm đón thành native button; thêm `aria-label` cho 6 icon buttons; gán `role="alert"` + `aria-live="assertive"` cho search error; gán `role="button"` + `tabindex="0"` cho spotlight card; ẩn và vô hiệu hóa `#home-voice-btn`, `#picker-voice-btn`, `#btn-remind-trip`; xóa toàn bộ các chuỗi hardcode giả (`35 km`, `29 trạm`, `~75-90 phút`, `Xe Kim Long`, `Máy lạnh 100%`, `Đầy đủ ghế ngồi`); bổ sung `#app-loading-state` và `#app-error-state` kèm nút `#btn-retry-load`; bump asset query sang `v=20260928_v9`. |
| [`manifest.json`](file:///home/opc/danabus/manifest.json) | Loại bỏ cụm từ `thời gian thực`, cập nhật mô tả chính xác theo lịch trình xuất bến. |
| [`sw.js`](file:///home/opc/danabus/sw.js) | Nâng cấp `CACHE_NAME = 'danabus-cache-v9'`, bump `STATIC_ASSETS` sang `v=20260928_v9`, cơ chế `activate` quét và giải phóng toàn bộ cache cũ. |
| [`css/app.css`](file:///home/opc/danabus/css/app.css) | Bổ sung quy tắc `:focus-visible` chuẩn accessibility cho `button`, `a`, `input`, `[role="button"]`, `[tabindex="0"]` với outline 2px và focus ring rõ ràng. |
| [`js/busService.js`](file:///home/opc/danabus/js/busService.js) | Thêm quản lý trạng thái tải `isLoading`, `isLoaded`, `loadError`, `getLoadStatus()`; kiểm tra `res.ok`, fail-closed và rethrow lỗi khi tải dataset thất bại; loại bỏ danh sách tuyến hardcode trong bộ lọc `electric`; bổ sung phương thức `formatRouteVehicleInfo(route)` bóc tách nhãn hiệu / sức chứa từ `vehicleInfo` có provenance rõ ràng. |
| [`js/app.js`](file:///home/opc/danabus/js/app.js) | Tích hợp loading/error/offline state (`showLoadingState`, `hideLoadingState`, `showErrorState`, `hideErrorState`, `retryLoad`); kết nối nút thử lại `#btn-retry-load` và sự kiện `online`; xóa bỏ fake voice simulation và fake reminder `alert()`; cập nhật nhãn countdown sang `Theo lịch: ...`; tích hợp `formatRouteVehicleInfo`; fail-closed ẩn trường duration; sửa subheader map; thêm keyboard listener Enter/Space cho `[role="button"][tabindex="0"]`; chuyển picker items sang native button. |
| [`scripts/test_ui_integrity_and_accessibility.py`](file:///home/opc/danabus/scripts/test_ui_integrity_and_accessibility.py) | Tạo mới bộ test acceptance tự động kiểm tra tĩnh (viewport, no-fake, focus-visible, sw cache v9, loading/error HTML containers), hợp đồng Node.js, và browser automation headless Chrome CDP (ARIA, keyboard Enter/Space, trip results truthful, negative dataset block & recovery via CDP). |
| [`scripts/browser_smoke_test.py`](file:///home/opc/danabus/scripts/browser_smoke_test.py) | Cập nhật Check 7 kiểm tra di trú cache sang `danabus-cache-v9`, thanh trừng `danabus-cache-v7`, và asset query `v=20260928_v9`. |
| `/var/www/danabus/public/*` | Deploy toàn bộ deliverables cập nhật lên web root phục vụ production domain `danabus.638686.xyz`. |

---

## 3. Bằng Chứng Kiểm Thử & Nghiệm Thu (Verification Evidence)

### 3.1. Test Suite Task 9: `test_ui_integrity_and_accessibility.py` (PASS 100%)

```text
--- 1. STATIC DELIVERABLE & TRUTHFULNESS ASSERTIONS ---
 [PASS] Viewport zoom lock strictly removed (pinch-to-zoom allowed)
 [PASS] Realtime wording eradicated across HTML, manifest, and JS
 [PASS] No fake fallbacks (35 km, 29 stops, ~75-90 min, Máy lạnh 100%, Đầy đủ ghế ngồi)
 [PASS] Electric filter relies strictly on vehicleInfo provenance without hardcoded route arrays
 [PASS] Accessible :focus-visible baseline defined in CSS
 [PASS] Service Worker cache version bumped to v9 with clean cache busting
 [PASS] App-level loading and error/offline state containers present in HTML

--- 2. NODE.JS CONTRACT & PROVENANCE CHECKS ---
 [PASS] formatRouteVehicleInfo and electric category provenance strictly verified

--- 3. HEADLESS CHROME BROWSER INTERACTION & ACCESSIBILITY TESTS ---
 -> Live viewport meta: 'width=device-width, initial-scale=1.0, viewport-fit=cover'
 [PASS] Live browser viewport allows pinch-to-zoom
 [PASS] All 6 icon-only buttons have explicit accessible names (aria-label)
 [PASS] ARIA live regions verified (role='alert', aria-live='assertive'/'polite')
 [PASS] Voice & Reminder disabled/hidden without fake alerts or transcript simulation
 [PASS] Keyboard Enter on spotlight card opens Route 02 detail
 -> Trip Results State: {'km': '10 km', 'stops': '46 trạm (Chiều đi)', 'timeText': 'Chưa có dữ liệu', 'timeHidden': True, 'timer': 'Theo lịch: 15-30 phút', 'fleet': 'Kim Long', 'fleetDesc': '30 chỗ (bao gồm: 11 chỗ đứng và 19 chỗ ngồi)', 'laterNote': 'Xuất bến theo lịch trình công bố', 'ctaText': 'Xem bản đồ số & Lộ trình trạm'}
 [PASS] Route 02 trip results verified: truthful distance, stops, fleet, schedule source, no fake claims
 -> Route 21 Trip State: {'routeId': '21', 'fleet': 'Chưa có dữ liệu', 'fleetDesc': 'Xe buýt'}
 [PASS] Missing vehicle fleet fails-closed to 'Chưa có dữ liệu'
[Check 7] Testing Negative Dataset Failure / Offline State & Recovery...
 -> Live Error State: {'appLoadState': 'error', 'busServiceLoaded': False, 'busServiceRoutesCount': 0, 'errorVisible': True, 'errorRole': 'alert', 'errorLive': 'assertive', 'errorDesc': 'Không thể kết nối mạng hoặc thiết bị đang ngoại tuyến. Vui lòng kiểm tra kết nối và thử lại.', 'loadingHidden': True, 'homeHidden': True, 'routeCountText': 'Chưa có dữ liệu', 'spotlightText': 'Chưa có thông tin lịch', 'hasHeader': True, 'hasRetryBtn': True}
 [PASS] Negative dataset failure verified: visible error state, fail-closed UI, zero fabricated data, no white screen crash
 -> Testing Recovery via Retry Button...
 -> Recovery successful: {'appLoadState': 'ready', 'busServiceLoaded': True, 'routesCount': 23, 'errorHidden': True, 'activeViewRestored': True}
 [PASS] Error state recovery successfully verified
 [PASS] Deliverable screenshot captured: docs/reports/task9_ui_accessibility_evidence.png (45874 bytes)

======================================================================
ALL TASK 9 ACCEPTANCE CRITERIA STRICTLY VERIFIED (100% PASS)
======================================================================
```

### 3.2. Toàn Bộ Ma Trận Regression Tests (8/8 Suites PASS)

| Test Suite | File Kiểm Thử | Kết quả | Ghi chú |
| :--- | :--- | :---: | :--- |
| **Task 9: UI & Accessibility** | [`scripts/test_ui_integrity_and_accessibility.py`](file:///home/opc/danabus/scripts/test_ui_integrity_and_accessibility.py) | **PASS (100%)** | Toàn bộ tiêu chí zoom, a11y, no-fake, voice/reminder |
| **Task 6: Search Correctness** | [`scripts/test_search_correctness.py`](file:///home/opc/danabus/scripts/test_search_correctness.py) | **10/10 PASS** | Direct match, monotonic direction, swap, validation |
| **Task 7: Schedule & Fare** | [`scripts/test_schedule_and_fare.py`](file:///home/opc/danabus/scripts/test_schedule_and_fare.py) | **9/9 PASS** | Schedule window, tiered/flat fare models |
| **Task 8: Data Quality** | [`scripts/test_data_quality_and_planner_readiness.py`](file:///home/opc/danabus/scripts/test_data_quality_and_planner_readiness.py) | **11/11 PASS** | Contract `dataQuality`, spatial nearby stops |
| **Task 2: Map & GPS Unit** | [`scripts/test_map_and_gps.py`](file:///home/opc/danabus/scripts/test_map_and_gps.py) | **11/11 PASS** | Spatial resolution, bounds, fail-closed GPS |
| **Task 5: Security Smoke** | [`scripts/security_smoke_test.py`](file:///home/opc/danabus/scripts/security_smoke_test.py) | **26/26 PASS** | Kiểm tra trực tiếp production `danabus.638686.xyz` |
| **Task 7: Browser Tests** | [`scripts/test_browser_schedule_and_fare.py`](file:///home/opc/danabus/scripts/test_browser_schedule_and_fare.py) | **7/7 PASS** | DOM Chrome thực tế, dynamic fare/schedule tags |
| **Task 2: Browser Smoke** | [`scripts/browser_smoke_test.py`](file:///home/opc/danabus/scripts/browser_smoke_test.py) | **8/8 PASS** | Chạy trực tiếp trên `https://danabus.638686.xyz` |

### 3.3. Hình Ảnh Bằng Chứng Nghiệm Thu (Evidence Screenshots)

1. Ảnh chụp tự động nghiệm thu giao diện Task 9 (Chrome Headless CDP):
   [`docs/reports/task9_ui_accessibility_evidence.png`](file:///home/opc/danabus/docs/reports/task9_ui_accessibility_evidence.png) (kích thước: 45.874 bytes).
2. Ảnh chụp kiểm thử trình duyệt production smoke:
   [`docs/reports/browser_smoke_evidence.png`](file:///home/opc/danabus/docs/reports/browser_smoke_evidence.png) (kích thước: 38.363 bytes).

---

## 4. Hạn Chế Đã Biết (Known Limitations)

1. **Telemetry Vị Trí Xe Buýt Thời Gian Thực (Live GPS Tracking)**: Hiện tại hệ thống xe buýt công cộng Đà Nẵng chưa cung cấp API telemetry GPS xe buýt mở được cấp phép; ứng dụng Danabus tuân thủ nghiêm ngặt nguyên tắc trung thực (truthfulness) bằng cách thể hiện rõ thông tin là lịch trình xuất bến dự kiến (`Theo lịch: ...`), không giả lập tọa độ xe di chuyển trên bản đồ.
2. **Hạ Tầng Nhắc Nhở Chuyến Xe (Push Notification Scheduler)**: Chưa triển khai Notification Service Worker / Push API server backend; do đó nút `#btn-remind-trip` được ẩn và vô hiệu hóa fail-closed thay vì tạo alert giả.
3. **Thời Gian Chuyến Đi (Trip Duration)**: Dữ liệu lộ trình Danabus chính thức hiện không cung cấp trường thời lượng chuyến tiêu chuẩn; hệ thống fail-closed bằng cách ẩn chỉ số thời lượng thay vì tự suy diễn sai lệch theo vận tốc giả định.
4. **Bộ Lập Lộ Trình Đổi Tuyến (Trip Planner)**: Theo roadmap đã phê duyệt, Address-to-Address Trip Planner thuộc phạm vi Task 4 và sẽ được triển khai sau khi hoàn tất đợt remediation.

---

## 5. Kết Quả Review Của Tech Lead

Tech Lead đã re-review trực tiếp source và re-run độc lập toàn bộ acceptance/regression matrix trong workspace hiện tại sau vòng fix cuối.

### Implementation evidence đã xác minh

- Loading/error/offline state fail-closed đã được triển khai qua `BusService.init()` + `getLoadStatus()`, `DanabusApp.loadDataAndRender()` / `retryLoad()`, `#app-loading-state`, `#app-error-state` và `#btn-retry-load`.
- Negative browser test thực sự chặn `data/*.json`, xác minh UI chuyển sang error state, xóa dữ liệu in-memory, không render success/fabricated data và phục hồi được sau retry.
- Service Worker đã bump thật sang `danabus-cache-v9`; browser smoke xác minh các cache cũ `v4-v7` bị purge và asset query dùng `v=20260928_v9`.
- Các yêu cầu truthfulness, voice/reminder fail-closed, no-fake fallbacks và accessibility baseline vẫn giữ nguyên sau fix.

### Checks/tests TL re-run

- `scripts/test_ui_integrity_and_accessibility.py`: **PASS 100%**, gồm negative dataset failure + recovery.
- `scripts/test_search_correctness.py`: **10/10 PASS**.
- `scripts/test_schedule_and_fare.py`: **9/9 PASS**.
- `scripts/test_data_quality_and_planner_readiness.py`: **11/11 PASS**.
- `scripts/test_map_and_gps.py`: **11/11 PASS**.
- `scripts/security_smoke_test.py`: **PASS 100%** trên production domain.
- `scripts/test_browser_schedule_and_fare.py`: **7/7 PASS**.
- `scripts/browser_smoke_test.py`: **8/8 PASS**, gồm Service Worker/cache migration `danabus-cache-v9`.

### Review result

**PASS - TL VERIFIED PASS - TECHNICAL ACCEPTANCE.** Không còn finding bắt buộc nào trong scope Task 9.

Known limitations còn lại là boundary đã chấp nhận: chưa có realtime vehicle telemetry/provider, chưa có Push Notification scheduler thật, dataset chưa có trip duration chuẩn, và Address-to-Address Trip Planner thuộc Task 4.
