# Danabus Production Release Acceptance & Project Closure Report

Task-ID: tsk_cf038225-0b52-4ef0-88d9-2592c965baed

**Task ID:** `tsk_cf038225-0b52-4ef0-88d9-2592c965baed`
**Title:** Production Release Acceptance & Project Closure Gate (Roadmap V2 Task 15)  
**Date:** 2026-09-29  
**Role:** DEV Implementation & Verification  
**Workflow State:** IMPLEMENTING -> SUBMIT_REVIEW  
**Release Identity:** `v11` / `Build 20260929_v11` / `danabus-cache-v11`  
**Target Domain:** `https://danabus.638686.xyz/`  
**Production Public Root:** `/var/www/danabus/public`  
**Technical Acceptance Status:** **PASS (100% Deterministic Verification)**  

---

## 1. Executive Summary

Báo cáo này thiết lập ranh giới nghiệm thu kỹ thuật cuối cùng (Final Release Acceptance & Project Closure Gate) cho dự án Danabus PWA sau khi hoàn thành toàn bộ lộ trình cải tiến **Roadmap V2** (Tasks 11 - 15).

DEV đã thực hiện trọn vẹn:
1. **Nâng cấp Release Identity `v11`**:
   - Bump Service Worker cache sang `danabus-cache-v11` trong [`sw.js`](file:///home/opc/danabus/sw.js).
   - Bump cache-busting asset query sang `v=20260929_v11` trong [`index.html`](file:///home/opc/danabus/index.html) và `STATIC_ASSETS` của `sw.js`.
   - Cập nhật toàn bộ các bộ test browser và production runtime để kiểm tra việc thanh trừng triệt để cache `v10` cũng như các cache cũ (`v4`-`v9`).
2. **Triển khai Production Staged Invariant**:
   - Xuất bản an toàn bộ dữ liệu mở rộng đã được nghiệm thu tại Task 4 sang production root `/var/www/danabus/public` thông qua [`scripts/deploy_danabus_production.sh`](file:///home/opc/danabus/scripts/deploy_danabus_production.sh).
   - Tuân thủ nghiêm ngặt thứ tự triển khai: `Payload assets (css/js/assets/data)` -> `manifest.json` -> `index.html (atomic swap)` -> `sw.js (atomic swap, LAST)`, triệt tiêu hoàn toàn race condition mixed-state cache.
3. **Chứng minh Tương đương Mã băm SHA-256 (17/17 deliverables)**:
   - 100% tệp trong deliverable whitelist đạt tính toàn vẹn tuyệt đối: `Workspace == Production Public Root == Live HTTPS Response`.
4. **Kiểm thử Toàn diện Ma trận Nghiệm thu (100% PASS)**:
   - Ma trận hồi quy Task 10: **20/20 tiêu chí PASS** (13.08s).
   - Production PWA Runtime: **3/3 fresh-profile runs PASS**, mỗi lượt **8/8 checks PASS**.
   - Browser Smoke Test: **8/8 PASS** trên cả môi trường local và live production `https://danabus.638686.xyz/`.
   - Bảo mật hardening: **15 negative endpoints 404 fail-closed**, zero SPA HTML leak.
   - Quá trình di trú cache warm-cache: thanh trừng sạch sẽ `v10`, `v9`, `v7`, `v6`, `v5`, `v4`.
   - Khả năng phục hồi ngoại tuyến (Offline fallback): 100% tài nguyên app shell và dữ liệu tuyến trả về HTTP 200 từ cache khi mất mạng hoàn toàn.

---

## 2. Release & Deliverable Traceability

### 2.1 Release Markers
- **Release Version**: `v11` (Build `20260929_v11`)
- **Service Worker Cache Name**: `danabus-cache-v11`
- **Asset Cache-Busting Query**: `?v=20260929_v11`
- **Application Script**: `js/app.js?v=20260929_v11`
- **Service Worker Controller**: `https://danabus.638686.xyz/sw.js`

### 2.2 100% SHA-256 Deliverable Equivalence Matrix
Đối soát mã băm SHA-256 giữa `/home/opc/danabus` (Workspace), `/var/www/danabus/public` (Production Root), và phản hồi trực tiếp từ máy chủ web qua `https://danabus.638686.xyz/`:

| Tệp Deliverable | SHA-256 Workspace | SHA-256 Production Root | SHA-256 Live HTTPS | Trạng thái |
|---|---|---|---|:---:|
| [`assets/icons/icon-192.png`](file:///home/opc/danabus/assets/icons/icon-192.png) | `8412f5d274bd376d...` | `8412f5d274bd376d...` | `8412f5d274bd376d...` | **PASS** |
| [`assets/icons/icon-512.png`](file:///home/opc/danabus/assets/icons/icon-512.png) | `d45806e6f4e0471b...` | `d45806e6f4e0471b...` | `d45806e6f4e0471b...` | **PASS** |
| [`assets/logo.svg`](file:///home/opc/danabus/assets/logo.svg) | `9b039ae312053a5c...` | `9b039ae312053a5c...` | `9b039ae312053a5c...` | **PASS** |
| [`css/app.css`](file:///home/opc/danabus/css/app.css) | `ac35d6137358ff1e...` | `ac35d6137358ff1e...` | `ac35d6137358ff1e...` | **PASS** |
| [`data/danangbus_resolution_report.json`](file:///home/opc/danabus/data/danangbus_resolution_report.json) | `937201e6466008cf...` | `937201e6466008cf...` | `937201e6466008cf...` | **PASS** |
| [`data/danangbus_routes.json`](file:///home/opc/danabus/data/danangbus_routes.json) | `3ead905088b95d2d...` | `3ead905088b95d2d...` | `3ead905088b95d2d...` | **PASS** |
| [`data/danangbus_routes_compact.json`](file:///home/opc/danabus/data/danangbus_routes_compact.json) | `60b6b2e74b5f71ed...` | `60b6b2e74b5f71ed...` | `60b6b2e74b5f71ed...` | **PASS** |
| [`data/danangbus_stops.json`](file:///home/opc/danabus/data/danangbus_stops.json) | `501eb164922cf95c...` | `501eb164922cf95c...` | `501eb164922cf95c...` | **PASS** |
| [`data/danangbus_streets.json`](file:///home/opc/danabus/data/danangbus_streets.json) | `059724f605e2693c...` | `059724f605e2693c...` | `059724f605e2693c...` | **PASS** |
| [`data/danangbus_summary.json`](file:///home/opc/danabus/data/danangbus_summary.json) | `7d40154f9bb38830...` | `7d40154f9bb38830...` | `7d40154f9bb38830...` | **PASS** |
| [`index.html`](file:///home/opc/danabus/index.html) | `ff9c7e38f48ebd8e...` | `ff9c7e38f48ebd8e...` | `ff9c7e38f48ebd8e...` | **PASS** |
| [`js/app.js`](file:///home/opc/danabus/js/app.js) | `bd8aa4cf7d306247...` | `bd8aa4cf7d306247...` | `bd8aa4cf7d306247...` | **PASS** |
| [`js/busService.js`](file:///home/opc/danabus/js/busService.js) | `98da980ce8ac2a18...` | `98da980ce8ac2a18...` | `98da980ce8ac2a18...` | **PASS** |
| [`js/icons.js`](file:///home/opc/danabus/js/icons.js) | `ea0ade2904f0639e...` | `ea0ade2904f0639e...` | `ea0ade2904f0639e...` | **PASS** |
| [`js/mapService.js`](file:///home/opc/danabus/js/mapService.js) | `27becbad167af6b5...` | `27becbad167af6b5...` | `27becbad167af6b5...` | **PASS** |
| [`manifest.json`](file:///home/opc/danabus/manifest.json) | `b84d2c603cacfd77...` | `b84d2c603cacfd77...` | `b84d2c603cacfd77...` | **PASS** |
| [`sw.js`](file:///home/opc/danabus/sw.js) | `dc766f7ad5d538e8...` | `dc766f7ad5d538e8...` | `dc766f7ad5d538e8...` | **PASS** |

---

## 3. Dataset Coverage & Data Quality Baseline

Bộ dữ liệu được triển khai lên Production tuân thủ nghiêm ngặt nguyên tắc **Trung thực Kỹ thuật (Technical Truthfulness)** và **Fail-Closed**:

| Chỉ số Coverage & Quality | Giá trị Nghiệm thu | Diễn giải & Minh chứng |
|---|---|---|
| **Tổng số tuyến (Total Routes)** | **23** | 20 tuyến đang hoạt động, 3 tuyến tạm ngừng (Tuyến 04, 10, 15) |
| **Tuyến sẵn sàng lập lịch (tripPlanningReady)** | **5** / 23 | Tuyến `05`, `02`, `TKY-TMY` (02 QN), `TKY-NTH` (05 QN), `TKY-CHU` (12 QN) |
| **Chiều di chuyển hợp lệ (eligibleForPlanning)** | **10** / 46 | Cả 2 chiều (outbound & inbound) của 5 tuyến trên đều đạt chuẩn |
| **Chiều bị cách ly an toàn (ineligibleForPlanning)** | **36** / 46 | 18 tuyến còn lại fail-closed hoàn toàn do thiếu anchors hoặc lộ trình chưa kiểm chứng |
| **Tổng số trạm dừng (Total Stops)** | **638** | Danh mục trạm chuẩn hóa của mạng lưới |
| **Trạm dừng đã kiểm chứng (Verified Stops)** | **363** (56.9%) | Tọa độ thực từ OpenStreetMap, confidence high/medium |
| **Trạm dừng chưa giải quyết (Unresolved Stops)** | **275** (43.1%) | Giữ `lat: null, lng: null`, tuyệt đối không fake tọa độ |
| **Độ lệch dữ liệu (Metadata Drift)** | **0% (Zero drift)** | Khớp 100% với validator tất định tại [`scripts/validate_data_quality.py`](file:///home/opc/danabus/scripts/validate_data_quality.py) |

---

## 4. Full Final Verification & Acceptance Evidence

### 4.1 Layer A: Local Deterministic Suites
Tất cả các bộ test đơn vị và hợp phần chạy nội bộ với kết quả thành công tuyệt đối:
- **`scripts/validate_data_quality.py`**: **PASS**. 100% routes có metadata dataQuality khớp validator, zero drift.
- **`scripts/test_data_quality_and_planner_readiness.py`**: **14/14 PASS** (0.15s). Kiểm tra hợp đồng `dataQuality`, tính cô lập chiều, và thuật toán tìm trạm lân cận `findNearbyStops`.
- **`scripts/test_search_correctness.py`**: **10/10 PASS** (0.24s). Kiểm tra thứ tự một chiều A -> B, loại bỏ B -> A trên outbound, fail-closed khi không có tuyến trực tiếp.
- **`scripts/test_schedule_and_fare.py`**: **9/9 PASS** (0.20s). Kiểm tra logic tính giờ khởi hành (00:46 -> 05:15: 269 phút), vé theo chặng (distance_tiered) Tuyến 02 & 06, vé đồng giá.
- **`scripts/test_map_and_gps.py`**: **11/11 PASS** (0.02s). Kiểm tra tính cô lập hình học chưa kiểm chứng, 247 trạm OSM nội thành + 116 trạm mở rộng.
- **`scripts/test_icons.py`**: **21/21 PASS** (0.01s). Toàn bộ icon SVG hợp lệ.
- **`scripts/test_trip_planner.py`**: **10/10 PASS** (0.50s). Kiểm tra hợp đồng `ResolvedLocation`, `LocalLocationProvider`, `WalkingRouter` (geometry=null, isEstimated=true), direct route, 1-transfer routing, anti-loop, detour ratio <= 1.8.
- **Task 4 Boundary Guard**: **PASS**. Quét tĩnh mã nguồn xác nhận 0 hardcoded Google Places/Maps SDK, BusService cũ vẫn giữ tính tương thích ngược và fail-closed.

### 4.2 Layer B: Browser & Production Integration Suites
- **`scripts/security_smoke_test.py`**: **100% PASS**.
  - **15 negative endpoints** (`/.git/config`, `/.git/HEAD`, `/docs/*`, `/scripts/*`, `/data/schema.ts`, `/data/osm_cache/*`,...) đều trả về **HTTP 404** chuẩn, triệt tiêu nguy cơ rò rỉ mã nguồn hay rơi vào SPA fallback.
  - **10 positive endpoints** trả về **HTTP 200** với MIME type chính xác và Cache-Control phù hợp.
  - Chuyển hướng tự động **HTTP 80 sang HTTPS 443** (HTTP 301).
- **`scripts/test_ui_integrity_and_accessibility.py`**: **100% PASS**.
  - Cho phép pinch-to-zoom (loại bỏ zoom lock).
  - Loại bỏ hoàn toàn từ ngữ gây hiểu nhầm về xe realtime.
  - Phím Tab và focus-visible tuân thủ WCAG.
  - Xử lý lỗi ngắt kết nối mạng an toàn (`role="alert"`, retry recovery).
- **`scripts/test_browser_schedule_and_fare.py`**: **7/7 PASS**. Xác nhận giao diện DOM hiển thị chính xác bảng giá, nhãn vé lượt và đếm ngược giờ xe chạy.
- **`scripts/test_browser_trip_planner.py`**: **6/6 PASS**. Kiểm thử CDP Headless Chrome cho luồng tìm chuyến từ Bách Khoa đến Biển Đông, hiển thị badge xếp hạng và vẽ đa chặng Leaflet.
- **`scripts/browser_smoke_test.py`**: **8/8 PASS** (Chạy trực tiếp trên `https://danabus.638686.xyz/`).
  - Kiểm tra nạp 23 tuyến, hiển thị bản đồ Tuyến 02, 05, TKY-TMY, TKY-NTH, chuyển hướng outbound/inbound, giả lập định vị người dùng, thanh trừng cache cũ sang `danabus-cache-v11`.
- **`scripts/test_task10_regression_acceptance.py`**: **20/20 PASS** (13.08s). Ma trận truy vết nghiệm thu toàn diện.
- **`scripts/test_production_pwa_runtime.py --repeat 3`**: **3/3 runs PASS** (Mỗi run 8/8 checks PASS).
  - Vòng đời Service Worker first-install và tự động reload (`controllerchange`) ổn định.
  - Fresh profile install kích hoạt precache vào `danabus-cache-v11`.
  - Warm migration từ `v10` (và `v9`, `v4`-`v7`) kích hoạt xóa sạch toàn bộ store cũ, chỉ giữ lại `danabus-cache-v11`.
  - Chế độ ngoại tuyến (Offline Emulation) tải mượt mà HTML, CSS, JS và dữ liệu JSON từ cache cục bộ.

---

## 5. Acceptance Traceability Matrix (Task 10 Core 20/20)

| STT | Hạng mục Nghiệm thu | Tầng Kiểm thử | Trạng thái |
|:---:|---|:---:|:---:|
| 1 | A -> B đúng direction/order: PASS | Layer A | **PASS** |
| 2 | B -> A ngược order: không match outbound | Layer A | **PASS** |
| 3 | origin == destination: validation error | Layer A | **PASS** |
| 4 | origin empty: validation error | Layer A | **PASS** |
| 5 | destination empty: validation error | Layer A | **PASS** |
| 6 | Không có direct route: no-result | Layer A | **PASS** |
| 7 | Suspended/ineligible route: không đề xuất | Layer A | **PASS** |
| 8 | Thiếu stop/geometry: excluded/degraded theo data-quality contract | Layer A | **PASS** |
| 9 | 00:46 với service start 05:15: 269 phút / before_service | Layer A | **PASS** |
| 10 | Sau service window: after_service hoặc next_day đúng contract | Layer A | **PASS** |
| 11 | Malformed/suspended schedule: unknown, không fake time | Layer A | **PASS** |
| 12 | Tiered fare: không hiển thị flat fare sai | Layer A & B | **PASS** |
| 13 | GPS coordinate: nearby-stop candidate hợp lệ, verified-only | Layer A | **PASS** |
| 14 | Swap locations: không stale result | Layer A | **PASS** |
| 15 | Voice/reminder disabled: không fake success | Layer B | **PASS** |
| 16 | Dataset/network failure: visible error, zero fabricated data, retry recovery | Layer B | **PASS** |
| 17 | Sensitive public paths: blocked (404 fail-closed) | Layer B | **PASS** |
| 18 | Browser/public smoke: production runtime semantics PASS (v11) | Layer B | **PASS** |
| 19 | Toàn bộ suite Task 5-9 liên quan: regression PASS | Orchestrator | **PASS** |
| 20 | Task 4 boundary: legacy direct-only & no fake leak | Layer A | **PASS** |

---

## 6. Known Non-Blocking Limitations & Safety Boundaries

Nhằm duy trì tính minh bạch kỹ thuật và bảo vệ an toàn sản phẩm, các giới hạn sau được ghi nhận rõ ràng:
1. **Tuyến 21 và các tuyến thiếu dữ liệu tiếp tục Fail-Closed**: Tuyến 21 chỉ có ít hơn 2 trạm có tọa độ hợp lệ, do đó hệ thống từ chối đề xuất lập lịch trình trên tuyến này cho đến khi có dữ liệu khảo sát thực địa.
2. **275 trạm chưa xác thực được bảo toàn giá trị Null**: 43.1% trạm dừng chưa tìm thấy vị trí nút chuẩn xác trên OSM không bị tự động suy diễn hay nội suy sai lệch.
3. **Ước tính đi bộ (Walking Estimation)**: Thuật toán tính cự ly đi bộ sử dụng công thức Haversine với `isEstimated: true` và `geometry: null`, tuyệt đối không giả lập đường đi bộ phi thực tế khi chưa tích hợp routing engine đi bộ chuyên dụng.
4. **Không tích hợp dịch vụ phụ thuộc ngoài**: Ứng dụng không sử dụng API Google Places trả phí hay API vị trí xe buýt thời gian thực (hiện Danabus chưa cung cấp công khai).
5. **Chính sách Git Publication**: Theo runtime `git_push_authorized=OFF`, các commit nghiệm thu được ghi nhận an toàn tại nhánh local `main` (ahead of origin) mà không đẩy lên remote trái phép, sẵn sàng chờ lệnh `/push` từ PO khi có yêu cầu.

---

## 7. Technical Acceptance Verdict & Recommendation

- **Đánh giá Kỹ thuật**: **PASS TOÀN DIỆN (100% CRITERIA SATISFIED)**.
- **Ranh giới Sản phẩm**: Bản phát hành `v11` hoạt động ổn định trên Production (`https://danabus.638686.xyz/`), không có lỗi hồi quy, dữ liệu trung thực, hiệu năng cao và bảo mật nghiêm ngặt.
- **Khuyến nghị cho PO (Product Owner)**: 
  - Toàn bộ các mục tiêu của Roadmap V2 đã hoàn thành trọn vẹn và được kiểm chứng độc lập.
  - Kính đề xuất PO nghiệm thu kỹ thuật và ra quyết định **Đóng dự án (Project Closure)** hoặc phê duyệt mở rộng phạm vi lộ trình mới nếu có nhu cầu khảo sát thực địa bổ sung.

---

## 8. TL Independent Review - Current REVIEW Run

TL đã kiểm tra implementation thực tế, không chỉ dựa vào DEV handoff, với kết quả:

- `python3 scripts/validate_data_quality.py --check`: PASS, zero drift.
- `python3 scripts/validate_data_quality.py --coverage`: PASS, 5/23 `tripPlanningReady`, 10/46 directions eligible, 363/638 verified stops.
- `python3 -m unittest discover -s scripts -p "test_*.py"`: 44/44 PASS.
- `python3 scripts/test_task10_regression_acceptance.py`: 20/20 PASS trên full local + production matrix.
- `python3 scripts/test_production_pwa_runtime.py --repeat 3`: 3/3 runs PASS, mỗi run 8/8 checks; xác nhận v11 markers, fresh install, purge v10 và cache cũ, controllerchange settled và offline fallback.
- Live planner CDP verification trên release `v11`:
  - Route `02` outbound và inbound đều trả direct trip hợp lệ với walking -> transit -> walking; walking legs `isEstimated=true`, `geometry=null`.
  - Route `TKY-CHU` outbound và inbound đều trả direct trip hợp lệ với cùng safety contract.
  - Transfer case Tam Kỳ trả connecting trip `TKY-CHU -> TKY-NTH`, đúng 1 transfer và 5 legs.
  - Endpoint ngoài vùng phục vụ trả 0 trips với `NO_NEARBY_STOPS`, giữ fail-closed.
- SHA-256 independent verification: 17/17 public deliverables khớp tuyệt đối giữa workspace, `/var/www/danabus/public` và live HTTPS response.
- Git state tại lúc bắt đầu review: local `main` ahead `origin/main` 22 commits; `git_push_authorized=OFF`, do đó không push và trạng thái ahead không phải blocker.

### TL Review Result

**PASS - TL VERIFIED TECHNICAL ACCEPTANCE.** Không phát hiện critical defect hoặc regression trong scope Task 005. Release `v11` đáp ứng final Production Release Acceptance & Project Closure Gate về data quality, planner, PWA migration/offline, security, deterministic browser acceptance và production traceability.

### TL Known Limitations

Giữ nguyên các limitation không chặn đã nêu ở Phần 6: coverage còn fail-closed cho dữ liệu chưa verified, walking chỉ là Haversine estimate, chưa có external geocoding/walking provider và chưa có authorized realtime vehicle/ETA provider. Remote Git publication không nằm trong technical acceptance gate của run này.
