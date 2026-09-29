# Danabus Project Context

**Updated:** 2026-09-29  
**Authoritative workspace:** `/home/opc/danabus`  
**Current VibeLab project phase:** PLANNING  
**Current consolidated plan:** `docs/plans/2026-09-29-danabus-consolidated-roadmap-v2-plan.md`  
**Latest full re-audit:** `docs/reports/2026-09-29-danabus-full-project-reaudit-report.md`

## Product

Danabus là PWA tra cứu tuyến xe buýt Đà Nẵng/Hội An, gồm catalog tuyến, lịch trình/giá vé, bản đồ/GPS người dùng và trip planning.

## Historical Task Baseline

- Task 1: production/HTTPS/PWA baseline hoàn tất.
- Task 2: route map, stop resolver, GPS và fail-closed geometry baseline hoàn tất.
- Task 3: realtime vehicle/ETA CLOSED/DEFERRED; chưa có authorized public provider.
- Task 4: Address-to-Address Trip Planner đã **LOCAL TECHNICAL PASS**, nhưng **chưa deploy lên production hiện tại**.
- Task 5: production security hardening PASS.
- Task 6: search correctness/no-fake-result PASS.
- Task 7: schedule/fare correctness PASS.
- Task 8: data-quality/planner-readiness contract PASS.
- Task 9: UI integrity/accessibility implementation PASS nhưng browser acceptance có flaky first-run failure.
- Task 10: regression matrix có thể PASS 20/20 nhưng chưa deterministic vì re-audit ghi nhận first-run FAIL rồi rerun PASS.

## Verified Re-Audit Facts

- Task 4 unit: 10/10 PASS.
- Task 4 browser local: 6/6 PASS.
- Full Task 10 re-audit run #1: FAIL tại Task 9 Suite B.3.
- Task 9 standalone rerun: PASS.
- Full Task 10 rerun: 20/20 PASS.
- Production security smoke: PASS.
- Production browser smoke: 8/8 PASS.

## Git State At Re-Audit

- Local `main`: `ef6c341`.
- `origin/main`: `e569ff4`.
- Local main ahead origin 9 commits.
- Task 7-10/Task 4 source, tests và reports còn nhiều modified/untracked files.
- Repository hiện chưa phải source of truth hoàn chỉnh cho accepted workspace state.

## Production Drift

Production root `/var/www/danabus/public` không byte-identical với workspace cho:

- `index.html`
- `js/app.js`
- `js/busService.js`
- `js/mapService.js`

Production hiện không có các Task 4 markers chính như `TransitPlanner`, `LocationManager`, `WalkingRouter`, `tryRunPlanner`, `renderTripOptions`.

Do đó không được mô tả Task 4 là production-complete cho tới khi Roadmap V2 productionization PASS.

## Data Quality Baseline

- 23 routes: 20 active, 3 suspended.
- `tripPlanningReady` cả hai chiều: 3 routes (`05`, `TKY-TMY`, `TKY-NTH`).
- Ready một chiều: `TKY-CHU` inbound.
- 19 routes chưa planner-ready.
- 638 stop-direction records: 359 verified, 279 unresolved.

Fail-closed là invariant bắt buộc: không tự tạo tọa độ, geometry, fare, ETA hoặc realtime data.

## Current Architecture Constraints

- Trip planner dùng dataset Danabus.
- Direct + tối đa 1 transfer.
- Walking hiện là Haversine estimate, `geometry: null`.
- Local curated location/POI provider; chưa bật Google Places.
- Transit duration là deterministic estimate, không phải realtime ETA.
- Realtime chỉ được mở lại bằng Task mới khi có official/authorized provider.
- Production security phải giữ explicit public root và deny internal artifacts.

## Current Risks To Resolve

1. Accepted source chưa được commit/push đầy đủ.
2. Browser acceptance/release gate flaky.
3. Task 4 chưa productionized.
4. PWA release identity vẫn `danabus-cache-v9` / `v=20260928_v9` dù local Task 4 thay đổi mutable assets.
5. Planner coverage còn thấp do data debt.

## Roadmap V2

Task mới đề xuất, không tạo lại Task 1-10:

1. Repository & Project Context Reconciliation.
2. Deterministic Browser Acceptance & Release Gate Stabilization.
3. Task 4 Productionization & PWA Release Upgrade.
4. Planner Data Coverage Expansion.
5. Production Release Acceptance & Project Closure Gate.

External geocoding/walking road provider và realtime vehicle/ETA là conditional future scope, không nằm trong mandatory manifest hiện tại.

## Operating Rule For Next Session

Trước khi ra quyết định project-level, đọc file này và Roadmap V2. Source/test hiện tại quan trọng hơn report lịch sử nếu có mâu thuẫn. Core `VIBELAB_RUNTIME` vẫn là authority cho workflow state/allowed controls; file context này chỉ là authority cho product/project technical state.
