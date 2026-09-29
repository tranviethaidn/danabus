# Task 4: Address-to-Address Trip Planner — Technical Acceptance Report

Task-ID: tsk_d205b183-c014-4305-b1ba-8c639e633fe9
Date: 2026-09-29
Review Result: PASS — TL Technical Acceptance

## Scope
Task 4 triển khai Address-to-Address Trip Planner theo plan `docs/plans/2026-09-24-address-to-address-trip-planner-plan.md`:
- address/POI resolution và Current Location;
- multiple nearby-stop candidates;
- direct route và tối đa 1 transfer;
- walking legs, ranking và Leaflet multi-leg rendering;
- TransitPlanner độc lập Google/realtime và dùng dataset Danabus.

## Implementation Evidence
- `js/busService.js`: `ResolvedLocation`, `LocationSearchProvider`, `LocalLocationProvider`, `LocationManager`, `WalkingRouter`, `TransitPlanner`.
- `TransitPlanner` chỉ dùng direction có `eligibleForPlanning: true`, direct + max 1 transfer, transfer walk <= 400m, `detour ratio <= 1.8`, fail-closed khi dữ liệu không đủ.
- Walking estimate giữ `isEstimated: true`, `geometry: null`; không giả straight-line thành road geometry.
- `js/mapService.js`: `renderTrip()`, multi-leg rendering, estimated walking dashed reference, verified bus geometry, origin/destination/boarding/transfer/alighting markers.
- `js/app.js` + `index.html`: location picker, POI/address search, Current Location, non-stale swap, trip option list và map handoff.
- Legacy `BusService.findRoutesBetween()` vẫn direct-only/backward-compatible.
- Không hardcode Google Places/Maps SDK hoặc API key.

## TL Verification — Current Review Run
1. `python3 scripts/test_trip_planner.py`
   - PASS 10/10.
2. `python3 scripts/test_browser_trip_planner.py`
   - PASS 6/6.
   - Xác minh autocomplete, trip options, multi-leg map, non-stale swap, fail-closed empty state và screenshot.
3. `python3 scripts/test_task10_regression_acceptance.py`
   - PASS 20/20 trong 20.29s.
   - Item 20 đã được sửa sang post-Task-4 boundary semantics:
     - legacy `findRoutesBetween()` direct-only;
     - zero hardcoded Google Places/Maps SDK/credentials;
     - walking estimate không fake geometry;
     - disconnected planner query fail-closed.
   - Layer B production/browser, security, accessibility, offline recovery, GPS và service-worker regression đều PASS.

## Review Finding Resolved
Trong review trước, Item 20 của Task 10 vẫn mô tả legacy boundary “Task 4 chưa triển khai”. DEV đã sửa test/traceability để phản ánh đúng trạng thái post-Task-4. TL đã chạy lại toàn bộ acceptance matrix và xác nhận PASS.

## Known Limitations
- Location search hiện dựa trên local curated POI/address/stop provider; Google Places production integration chưa bật vì không có provider key/billing trong scope hiện tại.
- Walking leg hiện là Haversine estimate, được ghi nhãn rõ là ước tính và không có road geometry thực (`geometry: null`).
- Transit duration hiện là deterministic estimate theo số trạm, không phải realtime ETA.
- MVP giới hạn tối đa 1 transfer theo approved scope.

## Conclusion
Task 4 đạt technical acceptance. Không còn implementation defect bắt buộc sửa trong scope hiện tại. Có thể chuyển PO acceptance/close boundary.
