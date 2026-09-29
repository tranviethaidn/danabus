# Báo Cáo Re-Audit Toàn Dự Án Danabus

**Ngày:** 2026-09-29  
**Vai trò:** Tech Lead (TL)  
**Workspace:** `/home/opc/danabus`  
**Production:** `https://danabus.638686.xyz/`  
**Phạm vi:** Đối chiếu source hiện tại, Task 1-10, test suites, Git state và production runtime. Không triển khai feature mới trong lượt audit này.

## 1. Kết luận điều hành

Project không bị mất implementation chính. Phần lớn remediation Task 1-10 hiện vẫn tồn tại trong workspace và các business contract quan trọng vẫn hoạt động.

Tuy nhiên trạng thái "đã hoàn tất toàn bộ" từ các report cũ không còn đủ chính xác để dùng làm project context mới. Re-audit phát hiện 3 vấn đề vận hành cần xử lý trước mọi feature mở rộng:

1. **Git/repository chưa phản ánh source hiện tại.**
   - `HEAD main = ef6c341`, mới đến acceptance Task 6.
   - `origin/main = e569ff4`.
   - Local `main` đang đi trước origin 9 commits.
   - Task 7-10, Task 4 và nhiều artifact/test hiện vẫn là modified/untracked working tree.

2. **Acceptance browser không deterministic.**
   - Lần chạy đầu của `scripts/test_task10_regression_acceptance.py` trong re-audit FAIL tại Suite B.3 Task 9.
   - DOM nhận `-- km`, `-- trạm`, timer `Đang cập nhật`.
   - Chạy lại riêng Task 9 PASS; chạy lại full matrix sau đó PASS 20/20.
   - Vì lỗi đã tái xuất hiện giống sự cố từng ghi là "transient", cần coi đây là flaky/race/test-isolation defect cho đến khi chứng minh được deterministic.
   - Root cause cụ thể chưa được chứng minh trong lượt audit; không được gán nguyên nhân chắc chắn khi chưa có evidence.

3. **Task 4 mới chỉ đạt local technical acceptance, chưa có trên production runtime hiện tại.**
   - SHA-256 của local và `/var/www/danabus/public` khác nhau cho `index.html`, `js/app.js`, `js/busService.js`, `js/mapService.js`.
   - Dataset `data/danangbus_routes.json` khớp.
   - Production `busService.js` không có `TransitPlanner`, `LocationManager`, `WalkingRouter`.
   - Production `app.js` không có `tryRunPlanner`, `renderTripOptions`, `openPlannedTripMap`.
   - Vì vậy Task 4 phải được mô tả là **LOCAL TECHNICAL PASS / PRODUCTION NOT DEPLOYED**.

## 2. Trạng thái hợp nhất Task 1-10

| Task | Trạng thái sau re-audit | Ghi chú |
|---|---|---|
| Task 1 - Workspace + Production Baseline | Baseline hoàn tất | HTTPS/PWA production đang hoạt động. Security root cũ đã được Task 5 thay thế. |
| Task 2 - Route Map + GPS + Geometry | Implementation baseline PASS | Fail-closed geometry/GPS còn hiệu lực; coverage dữ liệu vẫn chưa đầy đủ. |
| Task 3 - Realtime Bus / Vehicle GPS / ETA | CLOSED / DEFERRED | Chưa có public/authorized realtime vehicle API đủ điều kiện production. |
| Task 4 - Address-to-Address Trip Planner | LOCAL TECHNICAL PASS, PRODUCTION NOT DEPLOYED | Unit 10/10, browser local 6/6 PASS; production hiện thiếu planner implementation. |
| Task 5 - Production Security Hardening | PASS | Production security smoke vẫn PASS. |
| Task 6 - Search Correctness & No-Fake-Result | PASS | Direction/order validation và fail-closed search vẫn PASS. |
| Task 7 - Schedule & Fare Correctness | PASS | Schedule/fare regression và browser semantics PASS. |
| Task 8 - Data Quality & Planner Readiness | PASS contract, còn data debt | Contract hoạt động; coverage planner còn hạn chế. |
| Task 9 - UI Integrity / Accessibility | Implementation PASS, acceptance flaky | Standalone rerun PASS nhưng full acceptance có first-run failure tái hiện. |
| Task 10 - Regression & Production Acceptance | Functional matrix PASS nhưng chưa deterministic | First run FAIL B.3; rerun full matrix PASS 20/20. Chưa đủ để gọi release gate là ổn định tuyệt đối. |

## 3. Verification thực tế trong lượt audit

### Task 4 local

- `python3 scripts/test_trip_planner.py`: **10/10 PASS**.
- `python3 scripts/test_browser_trip_planner.py`: **6/6 PASS**.
- Browser local xác nhận autocomplete, trip options, multi-leg map, swap và fail-closed empty state.

### Full regression

**Lần 1:**

- Layer A Task 2/6/7/8 và Task 4 boundary: PASS.
- Production Security Task 5: PASS.
- Browser Schedule/Fare Task 7: PASS.
- **Task 9 Suite B.3: FAIL** tại truthful trip result render.
- Full runner dừng fail-fast.

**Rerun:**

- `python3 scripts/test_ui_integrity_and_accessibility.py`: PASS toàn bộ.
- `python3 scripts/test_task10_regression_acceptance.py`: **20/20 PASS trong 19.41s**.
- Production browser smoke: **8/8 PASS**.

**Kết luận:** business logic chưa cho thấy regression cố định, nhưng release verification hiện có tính flaky và cần được ổn định trước khi dùng làm bằng chứng "100% stable".

## 4. Data quality hiện tại

Theo `docs/reports/task-8-data-quality-coverage.json`:

- 23 tuyến tổng cộng.
- 20 active, 3 suspended.
- 3 tuyến `tripPlanningReady: true` cả hai chiều: `05`, `TKY-TMY`, `TKY-NTH`.
- 1 tuyến chỉ đủ một chiều: `TKY-CHU` inbound.
- 19 tuyến chưa đủ planner readiness.
- 638 stop-direction records.
- 359 verified (56.27%).
- 279 unresolved (43.73%).

Nguyên tắc fail-closed đang đúng và phải giữ. Data debt không được xử lý bằng tọa độ/geometry giả.

## 5. Git và release state

Observed state:

- `main` local: `ef6c341`.
- `origin/main`: `e569ff4`.
- Local main ahead origin: **9 commits**.
- Working tree còn thay đổi lớn tại source, dataset, schema, PWA và browser tests.
- Nhiều plan/report/test của Task 7-10 và Task 4 chưa được tracked/committed.

Đây là rủi ro recovery/auditability: source đang có giá trị nhưng repository chưa lưu đầy đủ trạng thái đã được nghiệm thu.

## 6. PWA / Service Worker finding

Current workspace vẫn dùng:

- `CACHE_NAME = 'danabus-cache-v9'`
- asset query `v=20260928_v9`

trong khi Task 4 được triển khai local ngày 29/09 và thay đổi các mutable JS chính.

Same-origin fetch strategy hiện là **network-first**, vì vậy không có đủ evidence để kết luận cache v9 chính là nguyên nhân của flaky Task 9. Tuy nhiên release identity vẫn stale so với Task 4 và chưa có acceptance riêng cho:

- fresh install;
- warm cache upgrade;
- offline fallback sau release mới;
- controller change/reload sau Task 4;
- đảm bảo client cũ không giữ artifact không đồng bộ.

Roadmap mới phải bump release identity và kiểm thử đầy đủ cache migration cho post-Task-4 release.

## 7. Những phần không nên mở lại

Không tạo lại Task 1-10 chỉ để khớp lịch sử Core.

Giữ các task cũ làm **historical baseline**:

- Task 1, 2, 5, 6, 7, 8: accepted baseline.
- Task 3: closed/deferred.
- Task 9, 10: implementation baseline nhưng cần stabilization/revalidation.
- Task 4: local implementation baseline, cần productionization.

Các vấn đề mới phải đi thành Task mới, có scope rõ ràng, thay vì sửa lịch sử Task cũ bằng tay.

## 8. Kết luận TL

Source hiện tại có giá trị và không cần rebuild lại từ đầu.

Ưu tiên đúng là:

1. khóa lại repository/context thành một baseline có thể phục hồi;
2. loại bỏ flaky release gate;
3. productionize Task 4 với release/PWA version mới;
4. mở rộng data coverage sau khi release hiện tại ổn định;
5. chỉ mở external provider/realtime khi có dependency hợp lệ.

Roadmap chi tiết mới: `docs/plans/2026-09-29-danabus-consolidated-roadmap-v2-plan.md`.
