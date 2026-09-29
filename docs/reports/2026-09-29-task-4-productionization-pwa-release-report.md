# Task 4 Productionization & PWA Release Upgrade — Implementation & Acceptance Report

Task-ID: tsk_1a303d5c-8f66-4691-95cd-05c729d1644b

**Core Task ID:** `tsk_1a303d5c-8f66-4691-95cd-05c729d1644b`  
**Date:** 2026-09-29  
**Role:** DEV implementation + TL verification  
**State:** TL VERIFIED TECHNICAL ACCEPTANCE
**Target Domain:** `https://danabus.638686.xyz/`  
**Production Root:** `/var/www/danabus/public`  

---

## 1. Executive Summary

DEV đã hoàn thành việc sửa chữa và kiểm chứng 2 release-gate defects theo yêu cầu của TL Review:
1. **Defect 1: Deterministic Controllerchange Verification & Bounded Predicates**
   - Nâng cấp [`scripts/test_production_pwa_runtime.py`](file:///home/opc/danabus/scripts/test_production_pwa_runtime.py) tích hợp cơ chế settled-state barrier từ `test_ui_integrity_and_accessibility.py`.
   - Bắt trọn vẹn và xác nhận vòng đời first-install Service Worker takeover, sự kiện `controllerchange`, và reload tự động của trình duyệt (`navType === 'reload'`, `controllerActive === true`, `appState === 'ready'`).
   - Loại bỏ hoàn toàn các lệnh `time.sleep` cố định tại Check 2 (bây giờ là Check 3), thay thế bằng bounded predicate `wait_for_condition` cho kết quả tìm chuyến và Leaflet multi-leg map rendering.
   - Hỗ trợ cờ `--repeat N` và kiểm thử ổn định 3 lần liên tiếp từ 3 browser profile cô lập hoàn toàn (3/3 runs 100% PASS).
2. **Defect 2: Staged Deploy Order Invariant (Triệt tiêu v10-Worker / v9-Index Cache Race)**
   - Tái cấu trúc [`scripts/deploy_danabus_production.sh`](file:///home/opc/danabus/scripts/deploy_danabus_production.sh) theo thứ tự xuất bản nghiêm ngặt:
     - **Stage 2.1**: Payload assets phụ thuộc (`css/`, `js/`, `assets/`, `data/`) được rsync đầy đủ lên disk trước.
     - **Stage 2.2**: Metadata `manifest.json`.
     - **Stage 2.3**: Xuất bản `index.html` bằng atomic swap (`index.html.tmp` -> `index.html`).
     - **Stage 2.4**: Xuất bản `sw.js` **CUỐI CÙNG** bằng atomic swap (`sw.js.tmp` -> `sw.js`).
     - *Bảo đảm tuyệt đối*: Khi client hoặc browser phát hiện `sw.js` v10 và kích hoạt precache (`./` và `./index.html`), `index.html` v10 và toàn bộ assets v10 đã hiện diện hoàn chỉnh trên disk, triệt tiêu 100% nguy cơ worker v10 precache nhầm HTML v9.
   - Thêm automated static deploy-order assertion vào cả `scripts/test_production_pwa_runtime.py` (Check 0) và `scripts/test_ui_integrity_and_accessibility.py` (Check 8).
3. **100% SHA-256 Deliverable Equivalence**: Tái triển khai và đối soát 17/17 tệp deliverable trong whitelist sản phẩm giữa `/home/opc/danabus` và `/var/www/danabus/public`: 100% trùng khớp mã băm SHA-256.
4. **Unified Regression Acceptance**: Toàn bộ 20/20 tiêu chí nghiệm thu Task 10 đạt 100% PASS trong 13.57s.

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

## 3. Production Runtime Verification Results (Repeated Fresh Profiles)

Kết quả chạy `python3 scripts/test_production_pwa_runtime.py --repeat 3` trực tiếp trên domain chính thức `https://danabus.638686.xyz/`:

```
=== Starting Production Runtime Test Suite (Total runs: 3) ===

[RUN 1/3] === Danabus Production Runtime Verification (https://danabus.638686.xyz/) ===
[RUN 1/3] [Check 0] Verifying Staged Deploy Order Invariant (zero mixed-state cache race)...
[RUN 1/3]  [PASS] Check 0: Deploy script publishes payload -> manifest -> index.html (atomic) -> sw.js (atomic, last).
[RUN 1/3] [Check 1] Verifying First-Install Service Worker Takeover & Controllerchange Lifecycle...
[RUN 1/3]  -> Settled Lifecycle: {
  "navType": "reload",
  "controllerActive": true,
  "controllerScriptURL": "https://danabus.638686.xyz/sw.js",
  "appState": "ready",
  "routesCount": 23,
  "stopsCount": 421
}
[RUN 1/3]  [PASS] Check 1: Controllerchange reload settled cleanly with active Service Worker.
[RUN 1/3] [Check 2] Verifying Production Feature Markers & DOM Elements...
[RUN 1/3]  -> Feature Markers: {
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
[RUN 1/3]  [PASS] Check 2: Feature markers and Task 4 DOM containers verified on production.
[RUN 1/3] [Check 3] Live Trip Planner E2E on Production (Bách Khoa -> Biển Đông)...
[RUN 1/3]  -> Live Planner Execution Result: {
  "tripViewActive": true,
  "optionsCount": 5,
  "firstBadge": "Tuyến trực tiếp"
}
[RUN 1/3]  -> Map Render Result: {
  "mapViewActive": true,
  "hasOrigMarker": true,
  "hasDestMarker": true,
  "tripPolylinesCount": 3
}
[RUN 1/3]  [PASS] Check 3: Live Address-to-Address Trip Planner execution and multi-leg map rendering succeeded on production.
[RUN 1/3] [Check 4] Verifying Fresh Install & Service Worker Cache Registration (danabus-cache-v10)...
[RUN 1/3]  -> Fresh SW State: {'hasReg': True, 'active': True, 'keys': ['danabus-cache-v10']}
[RUN 1/3]  -> Cached assets count: 33
[RUN 1/3]  [PASS] Check 4: Fresh PWA install & static asset precache verified.
[RUN 1/3] [Check 5] Verifying Warm-Cache Migration & Purge of Legacy Stores (v4-v9 -> v10)...
[RUN 1/3]  -> Injected legacy caches: ['danabus-cache-v10', 'danabus-cache-v4', 'danabus-cache-v5', 'danabus-cache-v6', 'danabus-cache-v7', 'danabus-cache-v9']
[RUN 1/3]  -> Post-migration cache keys: ['danabus-cache-v10']
[RUN 1/3]  [PASS] Check 5: Warm-cache migration cleanly purged v9 and earlier legacy stores.
[RUN 1/3] [Check 6] Testing Offline Fallback Resilience via CDP Network Emulation...
[RUN 1/3]  -> Offline fetch test results: {'appStatus': 200, 'busStatus': 200, 'cssStatus': 200, 'routesStatus': 200, 'routesOk': True}
[RUN 1/3]  [PASS] Check 6: Offline fallback resilience confirmed under simulated offline mode.
[RUN 1/3] [Check 7] Capturing Production Verification Screenshot...
[RUN 1/3]  -> Screenshot saved to /home/opc/danabus/docs/reports/task4_production_pwa_v10_evidence.png (38363 bytes)
[RUN 1/3]  [PASS] Check 7: Screenshot captured.
[RUN 1/3] >>> ALL PRODUCTION RUNTIME CHECKS PASSED (8/8) <<<
--- Completed run 1/3 in 6.00s ---

[RUN 2/3] === Danabus Production Runtime Verification (https://danabus.638686.xyz/) ===
[RUN 2/3] [PASS] Check 0 through Check 7 (8/8 PASS)
--- Completed run 2/3 in 5.42s ---

[RUN 3/3] === Danabus Production Runtime Verification (https://danabus.638686.xyz/) ===
[RUN 3/3] [PASS] Check 0 through Check 7 (8/8 PASS)
--- Completed run 3/3 in 5.05s ---

============================================================
ALL 3 FRESH-PROFILE RUNS COMPLETED SUCCESSFULLY (100% PASS)
============================================================
```

---

## 4. Full Regression Verification Matrix Summary

| Test Suite | Script / Path | Kết quả | Ghi chú kỹ thuật |
|---|---|---|---|
| **Deploy Invariant** | `scripts/deploy_danabus_production.sh` | **PASS** | Payload -> manifest -> index.html (atomic) -> sw.js (atomic, last) |
| **Trip Planner Core** | `scripts/test_trip_planner.py` | **10/10 PASS** | Haversine distance, max 1 transfer, candidate filtering, ranking, fail-closed |
| **Browser Planner** | `scripts/test_browser_trip_planner.py` | **6/6 PASS** | Autocomplete, options UI, Leaflet multi-leg map, swap, fail-closed empty state |
| **Production Runtime** | `scripts/test_production_pwa_runtime.py` | **8/8 PASS (x3)** | Settled lifecycle, live planner, map render, precache v10, warm migration, offline |
| **Browser Smoke** | `scripts/browser_smoke_test.py` | **8/8 PASS** | Live production runtime, routes catalog, map render, geolocation, SW v10 migration & v9 purge |
| **Security Hardening** | `scripts/security_smoke_test.py` | **15/15 PASS** | Chặn 404 cho .git, docs, scripts, schema.ts, osm_cache, headers bảo mật chuẩn |
| **Search Correctness** | `scripts/test_search_correctness.py` | **10/10 PASS** | Direct-match outbound/inbound, reverse order rejection, validation, swap non-stale |
| **Schedule & Fare** | `scripts/test_schedule_and_fare.py` | **9/9 PASS** | Giá vé 23 tuyến, tiered fare, frequency range, truthful countdown |
| **Browser Schedule/Fare** | `scripts/test_browser_schedule_and_fare.py` | **7/7 PASS** | DOM & UI kiểm tra spotlight, catalog, chi tiết tuyến 02, 05, 09, LK01, 01SB |
| **Data Quality/Readiness**| `scripts/test_data_quality_and_planner_readiness.py` | **11/11 PASS** | Spatial indexing, verified stops provenance, monotonic order, candidate integrity |
| **Map & GPS** | `scripts/test_map_and_gps.py` | **11/11 PASS** | Polylines geometry, stops alignment, layer clearing, popup semantics |
| **Data Quality Validator**| `scripts/validate_data_quality.py` | **PASS** | 100% routes (23 tuyến) khớp metadata validator tất định |
| **UI & Accessibility** | `scripts/test_ui_integrity_and_accessibility.py` | **100% PASS** | Deploy order invariant, pinch-to-zoom, ARIA labels, focus-visible, offline recovery |
| **Unified Acceptance** | `scripts/test_task10_regression_acceptance.py` | **20/20 PASS** | Toàn bộ 20 tiêu chí nghiệm thu Task 10 đạt trong 13.57s |

---

## 5. Deployment Script Optimization Details

Kịch bản [`scripts/deploy_danabus_production.sh`](file:///home/opc/danabus/scripts/deploy_danabus_production.sh) đã được cấu trúc lại như sau:
1. **Stage 2.1 (Payload Assets)**: `rsync -a --delete` cho `css/`, `js/`, `assets/` và các tệp JSON trong `data/`. Đảm bảo các script và style `v10` đã có sẵn trên ổ cứng trước khi client nhận mã nguồn tham chiếu.
2. **Stage 2.2 (Web App Manifest)**: `cp -f` cho `manifest.json`.
3. **Stage 2.3 (Atomic index.html Swap)**: `cp -f index.html index.html.tmp && mv -f index.html.tmp index.html`. Bảo đảm client mới chỉ tải `index.html` khi payload assets đã hiện diện 100% trên disk.
4. **Stage 2.4 (Atomic sw.js Swap Last)**: `cp -f sw.js sw.js.tmp && mv -f sw.js.tmp sw.js`. Triệt tiêu hoàn toàn race condition: worker v10 chỉ precache khi `index.html` v10 đã có trên disk.
5. **Zero-Sudo Execution**: Do `/var/www/danabus/public` được phân quyền `opc:nginx` với quyền ghi cho `opc`, quy trình phát hành static release không gọi `sudo`, `nginx -t` hay `systemctl reload nginx` khi cấu hình Nginx và SSL đã sẵn sàng.

---

## 6. Git Publication Compliance

- Trạng thái cấp phép VIBELAB_RUNTIME: `git_push_authorized=OFF`.
- Toàn bộ thay đổi mã nguồn, kịch bản triển khai, test suites và báo cáo nghiệm thu đã được lưu trữ và commit nội bộ trên branch `main`.
- Tuân thủ tuyệt đối quy định không push remote khi chưa có ủy quyền `git_push_authorized=ON`.

---

## 7. TL Technical Acceptance - Current Review Run

### Scope

TL xác minh đúng phạm vi Task hiện tại: đưa Address-to-Address Trip Planner đã local technical PASS lên production, bump PWA/cache release identity sang `v10`, kiểm thử fresh/warm/offline upgrade, loại mixed-state deploy race, và chứng minh production artifact khớp release source. Không bật Google API, external walking provider hoặc realtime vehicle provider.

### Independent Verification Evidence

- `python3 scripts/test_production_pwa_runtime.py --repeat 3`: **3/3 fresh-profile runs PASS**, mỗi run **8/8 checks PASS**; xác minh real Service Worker takeover/controllerchange reload, planner E2E, multi-leg map, fresh install, `v9 -> v10` migration và offline fallback.
- `python3 scripts/test_task10_regression_acceptance.py`: **20/20 PASS**; security, search, schedule/fare, data-quality, map/GPS, accessibility/UI và production browser smoke đều không regression.
- SHA-256 workspace vs `/var/www/danabus/public`: **17/17 public whitelist deliverables equivalent**, 0 mismatch.
- Live HTTP markers: production trả `danabus-cache-v10`, `v=20260929_v10` và `class TransitPlanner`.
- Deploy-order invariant được xác minh: payload -> manifest -> atomic `index.html` -> atomic `sw.js` cuối cùng.

### Review Result

**PASS - TL VERIFIED TECHNICAL ACCEPTANCE.** Hai release-gate defects phát hiện ở review trước đã được sửa và tái kiểm chứng ổn định. Task đạt acceptance kỹ thuật để chuyển PO boundary.

### Known Limitations

- Location resolution vẫn dùng local curated POI/address/stop provider; chưa bật Google Places hoặc external geocoding provider theo scope.
- Walking legs vẫn là Haversine estimate, không phải road-routing geometry thực.
- Planner MVP giới hạn tối đa 1 transfer; coverage phụ thuộc các route/direction đạt `eligibleForPlanning` và data-quality contract.
- Realtime vehicle/ETA không thuộc mandatory scope hiện tại.
- `git_push_authorized=OFF`; local commits chưa push không phải acceptance blocker theo policy hiện hành.
