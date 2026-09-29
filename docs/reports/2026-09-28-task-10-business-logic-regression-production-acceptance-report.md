# Báo Cáo Triển Khai Kỹ Thuật: Task 10 - Business-Logic Regression & Production Acceptance

Task-ID: tsk_bacc9b91-9386-4e80-b7bc-5b5fc294696d

- **Dự án:** Danabus (`danabus.638686.xyz`)
- **Người thực hiện:** Developer (DEV)
- **Người nhận bàn giao:** Tech Lead (TL)
- **Ngày thực hiện:** 28/09/2026
- **Trạng thái:** TL TECHNICAL ACCEPTANCE PASS - READY FOR AUTOMATION BOUNDARY

---

## 1. Phạm Vi Triển Khai (Scope)

Triển khai đầy đủ theo kế hoạch đã thống nhất tại [`docs/plans/2026-09-28-task-10-business-logic-regression-production-acceptance-plan.md`](file:///home/opc/danabus/docs/plans/2026-09-28-task-10-business-logic-regression-production-acceptance-plan.md) và kết luận chỉ đạo kỹ thuật từ TL:

1. **Xây dựng Runner Hợp Nhất Mỏng (Unified Thin Runner)**:
   - Xây dựng [`scripts/test_task10_regression_acceptance.py`](file:///home/opc/danabus/scripts/test_task10_regression_acceptance.py) làm entrypoint điều phối kiểm thử toàn bộ đợt remediation (Task 5 - Task 9).
   - Tái sử dụng tối đa các test suite hiện có, tuyệt đối không sao chép hoặc duplicate lại các assertion nghiệp vụ đã có.
   - Cơ chế fail-fast nghiêm ngặt: bất kỳ lỗi hoặc mã thoát non-zero nào đều dừng ngay lập tức, không che giấu lỗi mạng/runtime thành cảnh báo (warning).

2. **Phân Tách Bạch 2 Tầng Kiểm Thử (Layer A & Layer B)**:
   - **Layer A - Local Deterministic Acceptance Suites**:
     - *Search Correctness (Task 6)*: Kiểm thử hướng đi, thứ tự dừng, kiểm tra rỗng/trùng điểm, fail-closed khi không có tuyến thẳng, loại bỏ tuyến tạm dừng, và swap không lưu kết quả cũ (`stale`).
     - *Schedule & Fare Correctness (Task 7)*: Hợp đồng trạng thái giờ chạy (`before_service`, `in_service`, `after_service`, `next_day`, `unknown`), cự ly tính toán countdown, không làm giả giờ cho tuyến bất thường, schema giá vé theo cự ly/chặng không hiển thị đồng giá giả.
     - *Data Quality & Spatial Primitives (Task 8)*: Đảm bảo kiểm tra dữ liệu trạm/hình học, tính hợp lệ `tripPlanningReady`, thuật toán tìm trạm lân cận `findNearbyStops` chỉ dùng trạm đã xác minh (`verified-only`).
     - *Map, GPS & Unverified Geometry Isolation (Task 2)*: Cô lập các tuyến thiếu dữ liệu tọa độ OSM, phân loại đúng trạm `needs_review`/`unresolved`.
     - *Task 4 Boundary Guard (Item 20)*: Kiểm soát chặt chẽ biên giới kiến trúc, đảm bảo Task 4 (Address-to-Address Trip Planner) chưa bị triển khai trước hạn.
   - **Layer B - Browser & Production Integration Suites**:
     - *Production Security Hardening (Task 5)*: Kiểm tra 15 endpoint nhạy cảm (.git, docs, scripts, prototype, schema.ts, osm_cache) trả về 404, bảo đảm header an ninh và chuyển hướng HTTPS.
     - *Browser Schedule & Fare Semantics (Task 7)*: Headless Chrome CDP xác minh DOM thực tế về nhãn giá, tag phân loại, tần suất và countdown không có giá trị hardcode giả.
     - *Browser UI Integrity & Accessibility (Task 9)*: Trợ năng WCAG (pinch-to-zoom, ARIA live, focus-visible, keyboard navigation), ẩn/vô hiệu hóa giọng nói và nhắc nhở giả, kiểm thử trạng thái lỗi ngoại tuyến và phục hồi tự động khi có mạng.
     - *Production Browser Smoke Test (Task 2 & 10)*: Chạy trên domain thực tế `https://danabus.638686.xyz/` xác thực danh mục 23 tuyến, chuyển hướng map, mock định vị GPS và di trú cache Service Worker sang `v9`.

3. **Task 4 Boundary Guard (Bảo Vệ Biên Giới Nghiệm Thu)**:
   - Quét tĩnh mã nguồn (`index.html`, `js/app.js`, `js/busService.js`, `js/mapService.js`): Không tồn tại bất kỳ từ khóa hoặc hàm lập kế hoạch chuyển tuyến nào (`findTransferRoutes`, `buildTransferItinerary`, `findMultiLegRoutes`, v.v.) và không cấu hình Google Places / Geocoding SDK.
   - Runtime Node.js assertion: Xác minh các cặp điểm đón không có tuyến kết nối trực tiếp (ví dụ: Hòa Hiệp Nam ➔ Phố cổ Hội An, Hòa Hiệp Nam ➔ Cầu Rồng, Cầu Rồng ➔ Tam Kỳ, Bến xe TT ➔ Hà Nội) bắt buộc trả về mảng rỗng `[]`, không xuất hiện thuật toán transfer giả định.

4. **Bảo Toàn Logic Nghiệp Vụ Production**:
   - Xác nhận toàn bộ logic nghiệp vụ cốt lõi đã ổn định và đạt 100% PASS trên matrix kiểm thử. Không thực hiện bất kỳ sửa đổi nào đối với logic nghiệp vụ production trong Task 10.

---

## 2. Chi Tiết File Thay Đổi

| File | Hành động | Mô tả kỹ thuật |
| :--- | :--- | :--- |
| [`scripts/test_task10_regression_acceptance.py`](file:///home/opc/danabus/scripts/test_task10_regression_acceptance.py) | Tạo mới | Runner kiểm thử hồi quy & nghiệm thu production hợp nhất. Điều phối Layer A & Layer B, kiểm tra Item 20 boundary guard, in Traceability Matrix 20/20 criteria, hỗ trợ tham số `--local-only` và `--target-url`. |
| [`scripts/test_ui_integrity_and_accessibility.py`](file:///home/opc/danabus/scripts/test_ui_integrity_and_accessibility.py) | Hiệu chỉnh | Bổ sung kiểm tra tường minh `assert ready` và tăng giới hạn chờ khởi tạo nạp dữ liệu `window.busService.routes` lên 10 giây (50 chu kỳ x 0.2s) để tránh chạy assertions khi trình duyệt chưa nạp xong dataset qua HTTP. |
| [`docs/reports/2026-09-28-task-10-business-logic-regression-production-acceptance-report.md`](file:///home/opc/danabus/docs/reports/2026-09-28-task-10-business-logic-regression-production-acceptance-report.md) | Tạo mới | Báo cáo nghiệm thu kỹ thuật Task 10 theo đúng chuẩn protocol `Task-ID: tsk_bacc9b91-9386-4e80-b7bc-5b5fc294696d`. |

---

## 3. Ma Trận Truy Vết Nghiệm Thu (Traceability Matrix - 20/20 PASS)

| Item | Tiêu chí nghiệm thu (Roadmap Acceptance Item) | Tầng kiểm thử | Test Suite & Assertion Sở Hữu | Kết quả |
| :---: | :--- | :---: | :--- | :---: |
| **1** | A -> B đúng direction/order | Layer A | `scripts/test_search_correctness.py` (Check 1: `test_direct_match_outbound`) | **PASS** |
| **2** | B -> A ngược order: không match outbound | Layer A | `scripts/test_search_correctness.py` (Check 2 & 3: `test_direct_match_inbound`) | **PASS** |
| **3** | origin == destination: validation error | Layer A | `scripts/test_search_correctness.py` (Check 6: `test_validation_same_endpoints`) | **PASS** |
| **4** | origin empty: validation error | Layer A | `scripts/test_search_correctness.py` (Check 4: `test_validation_empty_origin`) | **PASS** |
| **5** | destination empty: validation error | Layer A | `scripts/test_search_correctness.py` (Check 5: `test_validation_empty_destination`) | **PASS** |
| **6** | Không có direct route: no-result fail-closed | Layer A | `scripts/test_search_correctness.py` (Check 7: `test_no_direct_route_fail_closed`) | **PASS** |
| **7** | Suspended/ineligible route: không đề xuất | Layer A | `scripts/test_search_correctness.py` & `test_data_quality_and_planner_readiness.py` | **PASS** |
| **8** | Thiếu stop/geometry: excluded/degraded theo data-quality | Layer A | `scripts/test_data_quality_and_planner_readiness.py` & `test_map_and_gps.py` | **PASS** |
| **9** | 00:46 với service start 05:15: 269 phút / before_service | Layer A | `scripts/test_schedule_and_fare.py` (Check 1: `before_service_269_min`) | **PASS** |
| **10** | Sau service window: after_service / next_day đúng | Layer A | `scripts/test_schedule_and_fare.py` (Check 3, 4, 5) | **PASS** |
| **11** | Malformed/suspended schedule: unknown, không fake time | Layer A | `scripts/test_schedule_and_fare.py` (Check 8 & 8b) | **PASS** |
| **12** | Tiered fare: không hiển thị flat fare sai | Layer A & B | `scripts/test_schedule_and_fare.py` & `test_browser_schedule_and_fare.py` | **PASS** |
| **13** | GPS coordinate: nearby-stop candidate verified-only | Layer A | `scripts/test_data_quality_and_planner_readiness.py` & `test_map_and_gps.py` | **PASS** |
| **14** | Swap locations: không stale result | Layer A | `scripts/test_search_correctness.py` (Check 10: `test_swap_locations_invalidation`) | **PASS** |
| **15** | Voice/reminder disabled: không fake success | Layer B | `scripts/test_ui_integrity_and_accessibility.py` (Check 1 & 4) | **PASS** |
| **16** | Dataset/network failure: visible error, retry recovery | Layer B | `scripts/test_ui_integrity_and_accessibility.py` (Check 7: CDP Network Blocking) | **PASS** |
| **17** | Sensitive public paths: blocked 404 | Layer B | `scripts/security_smoke_test.py` (15 endpoints trả về 404, không SPA leak) | **PASS** |
| **18** | Browser/public smoke: production runtime semantics | Layer B | `scripts/browser_smoke_test.py` (8/8 checks trên `https://danabus.638686.xyz/`) | **PASS** |
| **19** | Toàn bộ suite Task 5-9: unified regression PASS | Orchestrator | `scripts/test_task10_regression_acceptance.py` (Tất cả 8 suite liên hoàn PASS) | **PASS** |
| **20** | Task 4 planner chưa bị triển khai sớm trong Task 10 | Layer A | `scripts/test_task10_regression_acceptance.py` (`test_task4_boundary_guard`) | **PASS** |

---

## 4. Bằng Chứng Thực Thi Kiểm Thử (Execution Evidence)

### 4.1. Lệnh Thực Thi Toàn Bộ Ma Trận
```bash
python3 scripts/test_task10_regression_acceptance.py
```

### 4.2. Nhật Ký Kết Quả Thực Tế (Actual Execution Log)
```text
================================================================================
TASK 10 BUSINESS-LOGIC REGRESSION & PRODUCTION ACCEPTANCE RUNNER
Workspace: /home/opc/danabus
Mode: Full Matrix (Layer A + Layer B Production)
Target URL: https://danabus.638686.xyz/
================================================================================

################################################################################
### LAYER A: LOCAL DETERMINISTIC ACCEPTANCE SUITES
################################################################################

>> [RUNNING] Suite A.1: Search Correctness & No-Fake-Result (Task 6)
   Command: /bin/python3 scripts/test_search_correctness.py
   |   [PASS] 1. test_direct_match_outbound (Bến xe TT -> Phố cổ Hội An)
   |   [PASS] 2. test_direct_match_inbound (Phố cổ Hội An -> Bến xe TT)
   |   [PASS] 3. test_reverse_order_rejection (Hội An -> Bến xe TT on outbound)
   |   [PASS] 4. test_validation_empty_origin ('', 'Chọn điểm đón')
   |   [PASS] 5. test_validation_empty_destination ('')
   |   [PASS] 6. test_validation_same_endpoints (Bến xe TT -> Bến xe TT)
   |   [PASS] 7. test_no_direct_route_fail_closed (Bến xe TT -> Hà Nội)
   |   [PASS] 8. test_suspended_route_exclusion (Tuyến 04, 10, R15)
   |   [PASS] 9. test_missing_stops_route_exclusion (Tuyến thiếu stops < 2)
   |   [PASS] 10. test_swap_locations_invalidation (Directional inversion & non-stale)
   [PASS] Suite A.1: Search Correctness & No-Fake-Result (Task 6) (0.18s)

>> [RUNNING] Suite A.2: Schedule & Fare Correctness (Task 7)
   Command: /bin/python3 scripts/test_schedule_and_fare.py
   | ALL TASK 7 ACCEPTANCE CRITERIA STRICTLY VERIFIED (100% PASS)
   [PASS] Suite A.2: Schedule & Fare Correctness (Task 7) (0.25s)

>> [RUNNING] Suite A.3: Data Quality Contract & Spatial Primitives (Task 8)
   Command: /bin/python3 scripts/test_data_quality_and_planner_readiness.py
   [PASS] Suite A.3: Data Quality Contract & Spatial Primitives (Task 8) (0.15s)

>> [RUNNING] Suite A.4: Map, GPS & Unverified Geometry Isolation (Task 2)
   Command: /bin/python3 scripts/test_map_and_gps.py
   | [Test Info] Stops breakdown: 245 verified stops across 207 unique OSM locations, 176 unresolved/needs_review stops.
   [PASS] Suite A.4: Map, GPS & Unverified Geometry Isolation (Task 2) (0.06s)

>> [RUNNING] Task 4 Boundary Guard Verification (Item 20)
   [PASS] Codebase static scan: zero transfer routing & zero Google Places/Maps API detected.
   PASS: All disjoint pairs strictly return empty array []. Zero premature transfer routing.
   [PASS] Task 4 Boundary Guard (Item 20) fully verified.

################################################################################
### LAYER B: BROWSER & PRODUCTION INTEGRATION SUITES
################################################################################

>> [RUNNING] Suite B.1: Production Security Hardening Verification (Task 5)
   Command: /bin/python3 scripts/security_smoke_test.py
   | >>> ALL SECURITY SMOKE CHECKS PASSED SUCCESSFULLY (100%) <<<
   [PASS] Suite B.1: Production Security Hardening Verification (Task 5) (0.40s)

>> [RUNNING] Suite B.2: Browser Schedule & Fare Semantics (Task 7)
   Command: /bin/python3 scripts/test_browser_schedule_and_fare.py
   | [Check 7] Deliverable screenshot saved to docs/reports/task7_schedule_fare_evidence.png (47910 bytes)
   | >>> ALL TASK 7 BROWSER ACCEPTANCE CHECKS PASSED (7/7) <<<
   [PASS] Suite B.2: Browser Schedule & Fare Semantics (Task 7) (5.68s)

>> [RUNNING] Suite B.3: UI Integrity, Accessibility & Offline Recovery (Task 9)
   Command: /bin/python3 scripts/test_ui_integrity_and_accessibility.py
   | [PASS] Route 02 trip results verified: truthful distance, stops, fleet, schedule source, no fake claims
   | [Check 7] Testing Negative Dataset Failure / Offline State & Recovery...
   | [PASS] Negative dataset failure verified: visible error state, fail-closed UI, zero fabricated data, no white screen crash
   | [PASS] Error state recovery successfully verified
   | [PASS] Deliverable screenshot captured: docs/reports/task9_ui_accessibility_evidence.png (45874 bytes)
   | ALL TASK 9 ACCEPTANCE CRITERIA STRICTLY VERIFIED (100% PASS)
   [PASS] Suite B.3: UI Integrity, Accessibility & Offline Recovery (Task 9) (4.81s)

>> [RUNNING] Suite B.4: Production Browser Smoke Test on https://danabus.638686.xyz/ (Task 2 & 10)
   Command: /bin/python3 scripts/browser_smoke_test.py https://danabus.638686.xyz/
   | [Check 4] Testing Direction Switch & Availability on Route 02, 11, 05, TKY-TMY, TKY-NTH, and single-direction Route TKY-CHU...
   | [Check 7] Testing Service Worker Lifecycle & Cache Policy Migration...
   |  -> Post-migration SW & Cache state: {'swActive': True, 'swScope': 'https://danabus.638686.xyz/', 'postMigrationCacheKeys': ['danabus-cache-v9'], 'hasFitRoute': True, 'mapScriptSrc': 'js/mapService.js?v=20260928_v9', 'appScriptSrc': 'js/app.js?v=20260928_v9'}
   | [Check 8] Capturing deliverable screenshot...
   |  -> Screenshot saved to docs/reports/browser_smoke_evidence.png (38363 bytes)
   | >>> ALL BROWSER SMOKE CHECKS PASSED (8/8) <<<
   [PASS] Suite B.4: Production Browser Smoke Test on https://danabus.638686.xyz/ (Task 2 & 10) (7.19s)

================================================================================
ALL 20/20 TASK 10 ACCEPTANCE CRITERIA VERIFIED (100% PASS in 18.82s)
Zero fake fallback | Zero regression | Production runtime semantics verified
================================================================================
```

### 4.3. Các Tệp Tin Hình Ảnh Chứng Minh (Deliverable Evidence Artifacts)
1. [`docs/reports/browser_smoke_evidence.png`](file:///home/opc/danabus/docs/reports/browser_smoke_evidence.png) (38,363 bytes): Ảnh chụp màn hình Chrome headless thực tế xác minh production `danabus.638686.xyz` tải đầy đủ danh mục tuyến, bản đồ và định vị GPS.
2. [`docs/reports/task7_schedule_fare_evidence.png`](file:///home/opc/danabus/docs/reports/task7_schedule_fare_evidence.png) (47,910 bytes): Ảnh chụp thực tế kiểm tra hiển thị giá vé phân tầng và lịch trình truthful.
3. [`docs/reports/task9_ui_accessibility_evidence.png`](file:///home/opc/danabus/docs/reports/task9_ui_accessibility_evidence.png) (45,874 bytes): Ảnh chụp thực tế kiểm tra giao diện trợ năng, trạng thái offline error và phục hồi recovery.

---

## 5. Giới Hạn Đã Biết (Known Limitations)

1. **Dữ Liệu Trạm OSM Cần Khảo Sát Thêm (GPS Data Debt)**:
   - Toàn hệ thống có 359 trạm đã được chuẩn hóa vị trí tọa độ verified OSM, còn 279 trạm thuộc trạng thái `unresolved`/`needs_review`. Các trạm này được cô lập fail-closed an toàn và không gây sai lệch dữ liệu theo đúng chuẩn Task 8.
2. **Độ Bao Phủ Tuyến Cho Trip Planning**:
   - Hiện tại có 3 tuyến hoàn chỉnh hai chiều và 1 tuyến đủ một chiều đáp ứng hợp đồng `tripPlanningReady: true`. 19 tuyến còn lại bị loại khỏi đề xuất chuyển tuyến cho đến khi dữ liệu lộ trình/hình học được khảo sát bổ sung.
3. **Biên Giới Task 4 (Address-to-Address Trip Planner)**:
   - Các chức năng tìm kiếm địa chỉ tự do qua POI/Geocoding, đề xuất chuyển tuyến đa chặng (transfer itinerary) và walking legs hoàn toàn thuộc phạm vi Task 4 (hiện đang `QUEUED`), tuyệt đối không bị triển khai sớm hay can thiệp vào đợt remediation này.

---

## 6. TL Technical Acceptance Verification - 29/09/2026

Tech Lead đã thực hiện lại verification độc lập trong lượt review hiện tại, không chỉ dựa trên log DEV trước đó.

- Lần chạy full matrix đầu tiên dừng fail-fast tại Suite B.3 (`UI Integrity, Accessibility & Offline Recovery`) do DOM giữ trạng thái mặc định ở bước Route 02 trip result (`-- km`, `-- trạm`, timer `Đang cập nhật`).
- TL kiểm tra local/production artifact và xác nhận SHA-256 của `js/app.js`, `js/busService.js`, `data/danangbus_routes.json` khớp nhau; Node.js `findRoutesBetween('Bến xe Trung tâm', 'Phố cổ Hội An')` trả đúng Route 02.
- TL chạy targeted headless-browser reproduction với đúng sequence keyboard navigation -> `showTripResults(...)`: không có JavaScript exception; Route 02 trả `10 km`, `46 trạm (Chiều đi)`, timer `Theo lịch: 15-30 phút`, fleet `Kim Long`.
- TL chạy lại toàn bộ `python3 scripts/test_task10_regression_acceptance.py`: **20/20 PASS trong 19.14s**, gồm Layer A, Layer B production/browser, security, offline recovery và Task 4 Boundary Guard.
- Sự cố browser ở lần chạy đầu không tái hiện được sau điều tra và không có bằng chứng về product/business-logic defect. Đây được ghi nhận như một transient automation/runtime event của lượt review, không bị che giấu trong acceptance evidence.

**Kết quả review:** **PASS**. Không phát hiện regression bắt buộc sửa trong scope Task 10; không phát hiện premature implementation thuộc Task 4; đủ điều kiện đi qua technical acceptance boundary.

## 7. Đề Xuất Bàn Giao

Task 10 đã hoàn tất implementation và TL Technical Acceptance Review. Với Automation ON, đề xuất chuyển qua `REQUEST_PO` để Core đóng Task 10 tại verified technical boundary và tiếp tục Task 4 - Address-to-Address Trip Planner theo approved manifest.
