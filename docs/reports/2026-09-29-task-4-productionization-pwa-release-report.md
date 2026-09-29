# Task 4 Productionization & PWA Release Upgrade — Implementation & Acceptance Report

**Core Task ID:** `tsk_1a303d5c-8f66-4691-95cd-05c729d1644b`  
**Date:** 2026-09-29  
**Role:** DEV  
**State:** REVIEW SUBMISSION  
**Target Domain:** `https://danabus.638686.xyz/`  
**Production Root:** `/var/www/danabus/public`  

---

## 1. Executive Summary

DEV đã hoàn thành toàn bộ phạm vi triển khai và productionization cho **Task 4: Address-to-Address Trip Planner & PWA Release Upgrade (v10)** theo đúng chỉ đạo và proposal kỹ thuật được TL chấp thuận.

Toàn bộ các mục tiêu cốt lõi đã được kiểm chứng bằng chứng thực tế:
1. **PWA Release Identity Bump (`v10`)**: Cập nhật đồng bộ cache store `danabus-cache-v10` và query cache-busting `v=20260929_v10` trên toàn bộ source, manifests và bộ kiểm thử tự động.
2. **Staged Deployment (Zero Mixed-State)**: Nâng cấp `scripts/deploy_danabus_production.sh` theo mô hình 3 giai đoạn: sync payload assets/data trước, sync manifest/sw kế tiếp, và xuất bản `index.html` cuối cùng bằng atomic swap (`.tmp` -> `rename`). Kịch bản hoạt động độc lập không yêu cầu quyền sudo không cần thiết đối với các release tĩnh.
3. **100% SHA-256 Deliverable Equivalence**: Toàn bộ 17 tệp deliverable trong whitelist sản phẩm giữa `/home/opc/danabus` và `/var/www/danabus/public` có mã băm SHA-256 trùng khớp hoàn toàn.
4. **Production Runtime Verification (6/6 PASS)**: Headless Chrome CDP kiểm tra trực tiếp trên `https://danabus.638686.xyz/`:
   - Feature markers & DOM containers của Address-to-Address Trip Planner hoạt động chính xác.
   - Live Trip Planner E2E: Tìm 5 phương án di chuyển (Bách Khoa ➔ Biển Đông), render multi-leg trên Leaflet gồm 3 polylines (2 chặng đi bộ nét đứt + 1 chặng buýt) và marker A/B/trạm đón/trạm xuống.
   - Fresh install precache: 33 assets được precache vào `danabus-cache-v10`.
   - Warm-cache migration: Nạp các cache cũ (`v4`, `v5`, `v6`, `v7`, `v9`) và xác minh Service Worker tự động thanh trừng triệt để toàn bộ cache cũ, chỉ giữ lại `danabus-cache-v10`.
   - Offline fallback resilience: Giả lập ngắt mạng hoàn toàn qua CDP Network emulation; HTML, CSS, JS bundles và dataset `danangbus_routes.json` phản hồi HTTP 200 từ cache.
5. **Zero Regression Across All Baselines**: Toàn bộ ma trận kiểm thử hồi quy đạt tỷ lệ đạt 100%:
   - `test_trip_planner.py`: 10/10 PASS
   - `test_browser_trip_planner.py`: 6/6 PASS
   - `test_production_pwa_runtime.py`: 6/6 PASS
   - `browser_smoke_test.py` (trên production): 8/8 PASS
   - `security_smoke_test.py` (trên production): 15/15 negative + positive headers PASS
   - `test_search_correctness.py`: 10/10 PASS
   - `test_schedule_and_fare.py`: 9/9 PASS
   - `test_browser_schedule_and_fare.py`: 7/7 PASS
   - `test_data_quality_and_planner_readiness.py`: 11/11 PASS
   - `test_map_and_gps.py`: 11/11 PASS
   - `validate_data_quality.py`: PASS (100% routes)
   - `test_ui_integrity_and_accessibility.py`: 100% PASS
   - `test_task10_regression_acceptance.py`: 20/20 PASS (16.01s)

---

## 2. Deliverable SHA-256 Equivalence Evidence

Đối soát mã băm SHA-256 giữa `/home/opc/danabus` (Workspace) và `/var/www/danabus/public` (Production Root):

| Tệp Deliverable | SHA-256 Workspace | SHA-256 Production Root | Trạng thái |
|---|---|---|---|
| `assets/icons/icon-192.png` | `8412f5d274bd376d...` | `8412f5d274bd376d...` | **PASS** |
| `assets/icons/icon-512.png` | `d45806e6f4e0471b...` | `d45806e6f4e0471b...` | **PASS** |
| `assets/logo.svg` | `9b039ae312053a5c...` | `9b039ae312053a5c...` | **PASS** |
| `css/app.css` | `ac35d6137358ff1e...` | `ac35d6137358ff1e...` | **PASS** |
| `data/danangbus_resolution_report.json` | `9d3119fa3003f9b9...` | `9d3119fa3003f9b9...` | **PASS** |
| `data/danangbus_routes.json` | `18eb638388c2ad0c...` | `18eb638388c2ad0c...` | **PASS** |
| `data/danangbus_routes_compact.json` | `99e5d8938c020475...` | `99e5d8938c020475...` | **PASS** |
| `data/danangbus_stops.json` | `3e158410f1f20883...` | `3e158410f1f20883...` | **PASS** |
| `data/danangbus_streets.json` | `059724f605e2693c...` | `059724f605e2693c...` | **PASS** |
| `data/danangbus_summary.json` | `7d40154f9bb38830...` | `7d40154f9bb38830...` | **PASS** |
| `index.html` | `143b0ce5e13b904a...` | `143b0ce5e13b904a...` | **PASS** |
| `js/app.js` | `bd8aa4cf7d306247...` | `bd8aa4cf7d306247...` | **PASS** |
| `js/busService.js` | `98da980ce8ac2a18...` | `98da980ce8ac2a18...` | **PASS** |
| `js/icons.js` | `ea0ade2904f0639e...` | `ea0ade2904f0639e...` | **PASS** |
| `js/mapService.js` | `27becbad167af6b5...` | `27becbad167af6b5...` | **PASS** |
| `manifest.json` | `b84d2c603cacfd77...` | `b84d2c603cacfd77...` | **PASS** |
| `sw.js` | `28402562aef8a463...` | `28402562aef8a463...` | **PASS** |

---

## 3. Production Runtime Verification Results

Chạy suite `scripts/test_production_pwa_runtime.py` trực tiếp trên domain chính thức `https://danabus.638686.xyz/`:

```
=== Danabus Production Runtime Verification (https://danabus.638686.xyz/) ===

[Check 1] Navigating to Production & Verifying Feature Markers...
 -> Feature Markers: {
  "hasTransitPlannerClass": true,
  "hasTransitPlannerInstance": true,
  "hasRenderTrip": true,
  "hasTripOptionsEl": true,
  "hasSwapBtn": true,
  "hasOriginBtn": true,
  "hasOriginDisplay": true,
  "hasDestinationInput": true,
  "routesCount": 23,
  "appVersionScript": "js/app.js?v=20260929_v10"
}
 [PASS] Check 1: Feature markers and Task 4 DOM containers verified on production.

[Check 2] Live Trip Planner E2E on Production (Bách Khoa -> Biển Đông)...
 -> Live Planner Execution Result: {
  "tripViewActive": true,
  "optionsCount": 5,
  "firstBadge": "Tuyến trực tiếp"
}
 -> Map Render Result: {
  "mapViewActive": true,
  "hasOrigMarker": true,
  "hasDestMarker": true,
  "tripPolylinesCount": 3
}
 [PASS] Check 2: Live Address-to-Address Trip Planner execution and multi-leg map rendering succeeded on production.

[Check 3] Verifying Fresh Install & Service Worker Cache Registration (danabus-cache-v10)...
 -> Fresh SW State: {'hasReg': True, 'active': True, 'keys': ['danabus-cache-v10']}
 -> Cached assets count: 33
 [PASS] Check 3: Fresh PWA install & static asset precache verified.

[Check 4] Verifying Warm-Cache Migration & Purge of Legacy Stores (v4-v9 -> v10)...
 -> Injected legacy caches: ['danabus-cache-v10', 'danabus-cache-v4', 'danabus-cache-v5', 'danabus-cache-v6', 'danabus-cache-v7', 'danabus-cache-v9']
 -> Post-migration cache keys: ['danabus-cache-v10']
 [PASS] Check 4: Warm-cache migration cleanly purged v9 and earlier legacy stores.

[Check 5] Testing Offline Fallback Resilience via CDP Network Emulation...
 -> Offline fetch test results: {'appStatus': 200, 'busStatus': 200, 'cssStatus': 200, 'routesStatus': 200, 'routesOk': True}
 [PASS] Check 5: Offline fallback resilience confirmed under simulated offline mode.

[Check 6] Capturing Production Verification Screenshot...
 -> Screenshot saved to docs/reports/task4_production_pwa_v10_evidence.png (31007 bytes)
 [PASS] Check 6: Screenshot captured.

>>> ALL PRODUCTION RUNTIME CHECKS PASSED (6/6) <<<
```

---

## 4. Full Regression Verification Matrix Summary

| Test Suite | Script / Path | Kết quả | Ghi chú kỹ thuật |
|---|---|---|---|
| **Trip Planner Core** | `scripts/test_trip_planner.py` | **10/10 PASS** | Haversine distance, max 1 transfer, candidate filtering, ranking, fail-closed |
| **Browser Planner** | `scripts/test_browser_trip_planner.py` | **6/6 PASS** | Autocomplete, options UI, Leaflet multi-leg map, swap, fail-closed empty state |
| **Production Runtime** | `scripts/test_production_pwa_runtime.py` | **6/6 PASS** | Live planner E2E, Leaflet render, fresh install, warm migration v9->v10, offline fallback |
| **Browser Smoke** | `scripts/browser_smoke_test.py` | **8/8 PASS** | Live production runtime, routes catalog, map render, geolocation, SW v10 migration & v9 purge |
| **Security Hardening** | `scripts/security_smoke_test.py` | **15/15 PASS** | Chặn 404 cho .git, docs, scripts, schema.ts, osm_cache, headers bảo mật chuẩn |
| **Search Correctness** | `scripts/test_search_correctness.py` | **10/10 PASS** | Direct-match outbound/inbound, reverse order rejection, validation, swap non-stale |
| **Schedule & Fare** | `scripts/test_schedule_and_fare.py` | **9/9 PASS** | Giá vé 23 tuyến, tiered fare, frequency range, truthful countdown |
| **Browser Schedule/Fare** | `scripts/test_browser_schedule_and_fare.py` | **7/7 PASS** | DOM & UI kiểm tra spotlight, catalog, chi tiết tuyến 02, 05, 09, LK01, 01SB |
| **Data Quality/Readiness**| `scripts/test_data_quality_and_planner_readiness.py` | **11/11 PASS** | Spatial indexing, verified stops provenance, monotonic order, candidate integrity |
| **Map & GPS** | `scripts/test_map_and_gps.py` | **11/11 PASS** | Polylines geometry, stops alignment, layer clearing, popup semantics |
| **Data Quality Validator**| `scripts/validate_data_quality.py` | **PASS** | 100% routes (23 tuyến) khớp metadata validator tất định |
| **UI & Accessibility** | `scripts/test_ui_integrity_and_accessibility.py` | **100% PASS** | Pinch-to-zoom, ARIA labels, focus-visible, offline error/retry recovery, SW v10 |
| **Unified Acceptance** | `scripts/test_task10_regression_acceptance.py` | **20/20 PASS** | Toàn bộ 20 tiêu chí nghiệm thu Task 10 đạt trong 16.01s |

---

## 5. Deployment Script Optimization Details

Kịch bản [`scripts/deploy_danabus_production.sh`](file:///home/opc/danabus/scripts/deploy_danabus_production.sh) đã được cấu trúc lại như sau:
1. **Stage 1 (Payload)**: `rsync -a --delete` cho `css/`, `js/`, `assets/` và các tệp JSON trong `data/`. Đảm bảo các script và style `v10` đã có sẵn trên ổ cứng trước khi client nhận mã nguồn tham chiếu.
2. **Stage 2 (Metadata & Worker)**: `cp -f` cho `manifest.json` và `sw.js`.
3. **Stage 3 (Atomic HTML Swap)**: `cp -f index.html index.html.tmp && mv -f index.html.tmp index.html`. Loại bỏ hoàn toàn khoảng trống lỗi dở dang (mixed-state hoặc 404 script bundle).
4. **Zero-Sudo Execution**: Do `/var/www/danabus/public` được phân quyền `opc:nginx` với quyền ghi cho `opc`, quy trình phát hành static release không gọi `sudo`, `nginx -t` hay `systemctl reload nginx` khi cấu hình Nginx và SSL đã sẵn sàng.

---

## 6. Git Publication Compliance

- Trạng thái cấp phép VIBELAB_RUNTIME: `git_push_authorized=OFF`.
- Toàn bộ thay đổi mã nguồn, kịch bản triển khai, test suites và báo cáo nghiệm thu đã được lưu trữ và commit nội bộ trên branch `main`.
- Tuân thủ tuyệt đối quy định không push remote khi chưa có ủy quyền `git_push_authorized=ON`.
