# Kế hoạch triển khai Audit Remediation & Roadmap Danabus

**Ngày:** 27/09/2026  
**Nguồn audit:** `docs/reports/2026-09-27-danabus-full-project-audit-report.md`  
**Phạm vi:** Hợp nhất 4 Task hiện có với các Task vá/cải tiến mới từ full-project audit.  
**Trạng thái:** PO đã phê duyệt triển khai toàn bộ roadmap. Task 3 được xác nhận CLOSED; Task 4 được phép triển khai. Chưa thay đổi source/production trong bước đồng bộ plan này.

---

## 1. Mục tiêu

Đưa Danabus từ trạng thái prototype/catalog PWA có một số chức năng tìm chuyến sang nền tảng có các contract rõ ràng về security, search correctness, schedule/fare correctness, data quality, UI truthfulness và regression coverage.

Nguyên tắc triển khai:

- Xử lý security và correctness trước khi mở rộng capability.
- Không fabricate route, ETA, fare, geometry, vehicle state hoặc dữ liệu realtime.
- Giữ boundary của các Task hiện có; remediation không được âm thầm biến thành Task 4.
- Task 4 đã được PO xác nhận triển khai; thực thi sau các dependency correctness/data-quality bắt buộc.
- Task 3 đã được PO xác nhận CLOSED; không mở lại trong roadmap này.
- Mỗi Task implementation phải có automated checks phù hợp và TL review trước khi nghiệm thu.

---

## 2. Danh sách 10 Task tổng thể

| # | Task | Nguồn | Trạng thái trong plan | Ưu tiên |
|---|---|---|---|---|
| **1** | Thiết lập workspace + deploy production `danabus.638686.xyz` | Existing | **[x] XONG** | Baseline |
| **2** | Route Map + GPS + stop coordinates + route geometry | Existing | Đã có implementation/verification baseline; giữ giới hạn dữ liệu fail-closed | Foundation |
| **3** | Realtime Bus / Vehicle GPS / ETA | Existing | **[x] CLOSED theo xác nhận PO** | Capability |
| **4** | Address-to-Address Trip Planner | Existing | **[APPROVED] PO ĐÃ XÁC NHẬN TRIỂN KHAI** | Capability |
| **5** | Production Security Hardening | New audit remediation | Chưa triển khai | **P0** |
| **6** | Search Correctness & No-Fake-Result | New audit remediation | Chưa triển khai | **P0** |
| **7** | Schedule & Fare Correctness | New audit remediation | Chưa triển khai | **P0/P1** |
| **8** | Data Quality Contract & Planner Readiness | New audit remediation | Chưa triển khai | **P1** |
| **9** | UI Integrity, Realtime Semantics & Accessibility | New audit remediation | Chưa triển khai | **P1/P2** |
| **10** | Business-Logic Regression & Production Acceptance | New audit remediation | Chưa triển khai | **P1** |

---

## 3. Task 1 - Workspace + Production Baseline

**Trạng thái:** **[x] XONG**

Artifact nghiệm thu hiện có:

- `docs/reports/task-1-workspace-baseline-acceptance.md`
- Workspace `/home/opc/danabus`.
- Production domain `danabus.638686.xyz`.
- HTTPS/PWA baseline đã được nghiệm thu.

Task 1 không mở lại. Các vấn đề production exposure phát hiện sau đó được xử lý trong Task 5 để giữ lịch sử nghiệm thu của Task 1 rõ ràng.

---

## 4. Task 2 - Route Map + GPS + Geometry

**Trạng thái:** Existing baseline đã triển khai và có verification; không mở rộng scope sang Trip Planner.

Artifact:

- `docs/plans/2026-09-24-danabus-map-gps-route-fix-plan.md`
- `docs/reports/2026-09-24-danabus-map-gps-verification-report.md`

Baseline đã có:

- Browser Geolocation thật cho user.
- Stop resolver fail-closed.
- Route geometry validator.
- Outbound/inbound độc lập khi dữ liệu đủ.
- Không dùng geometry giả cho route thiếu dữ liệu.

Giới hạn cần được xử lý ở Task 8 thay vì nhồi lại vào Task 2:

- Coverage geometry chưa đủ cho toàn bộ 23 routes.
- Nhiều route chưa có stop ở cả hai direction.
- Cần contract `tripPlanningReady` rõ ràng.

---

## 5. Task 3 - Realtime Bus / Vehicle GPS / ETA

**Trạng thái:** **[x] CLOSED theo xác nhận PO**. Research artifact được giữ làm lịch sử; không triển khai thêm trong roadmap hiện tại.

Artifact:

- `docs/reports/2026-09-24-danabus-realtime-bus-api-research.md`

Scope giữ nguyên:

- Realtime Provider Adapter.
- Vehicle position normalization.
- Trip/ETA updates nếu provider hỗ trợ.
- Timestamp/freshness: `LIVE`, `STALE`, `OFFLINE/UNKNOWN`.
- Không reverse-engineer private endpoint làm production dependency.

Điều kiện triển khai integration thật:

- Có official/authorized Vehicle Position API hoặc nguồn tương đương được phép sử dụng.
- Biết authentication, rate limit, update frequency, ID mapping và license/terms.

Dù Task 3 đã CLOSED, Task 9 vẫn phải bảo đảm UI không gọi schedule-derived data là realtime. Nếu sau này có provider hợp lệ, realtime integration phải được mở bằng scope/Task mới thay vì âm thầm mở lại Task 3.

---

## 6. Task 4 - Address-to-Address Trip Planner

**Trạng thái:** **[APPROVED] PO ĐÃ XÁC NHẬN TRIỂN KHAI**

Artifact:

- `docs/plans/2026-09-24-address-to-address-trip-planner-plan.md`

Task 4 đã được PO xác nhận triển khai. Không tạo thread trùng; dùng Task 4 hiện có và chỉ bắt đầu implementation khi các dependency Task 6, Task 7 và Task 8 đã đạt acceptance.

Scope đã định nghĩa:

- Address/POI resolution.
- Current GPS -> origin coordinate.
- Nearby stop candidate search.
- Direct route theo đúng direction/stop order.
- Tối đa 1 transfer cho MVP.
- Walking legs.
- Ranking nhiều phương án.
- Map rendering đầy đủ các legs.

Dependency trước khi Task 4 nên chạy:

- Task 2 baseline ổn định.
- Task 6 loại bỏ search sai/fake result.
- Task 7 chuẩn hóa schedule/fare semantics.
- Task 8 cung cấp data-quality eligibility contract.
- PO xác nhận provider/cost nếu dùng Google Places/Geocoding production.

---

## 7. Task 5 - Production Security Hardening

**Ưu tiên:** **P0 / Critical**

### Mục tiêu

Loại bỏ khả năng production phục vụ trực tiếp workspace/development artifacts.

### Scope

- Xác minh document root và static serving thực tế của Nginx.
- Không để `.git/`, `docs/`, `scripts/` hoặc artifact nội bộ truy cập public.
- Chuyển production sang explicit public artifact/document root nếu cần.
- Thêm deny rules cho path nhạy cảm nếu hạ tầng vẫn cần giữ workspace layout hiện tại.
- Kiểm tra SPA fallback không vô tình trả `index.html` cho path nhạy cảm.
- Kiểm tra cache/CDN không giữ bản đã từng expose.

### Acceptance

- Request tới `.git`, `docs`, `scripts` và path nội bộ trả deny/not-found phù hợp.
- Root app, manifest, service worker, CSS/JS/data public cần thiết vẫn hoạt động.
- HTTPS và PWA không regression.
- Có automated/public smoke evidence cho security paths.

---

## 8. Task 6 - Search Correctness & No-Fake-Result

**Ưu tiên:** **P0 / Critical**

### Mục tiêu

Không trả kết quả tuyến giả hoặc tuyến sai chiều.

### Scope

- Xóa fallback Tuyến 02 hoặc mọi fallback route mẫu khi không match.
- Audit và sửa `findRoutesBetween` theo từng direction.
- Bắt buộc `originIndex < destinationIndex` trên cùng direction.
- Không match route thiếu stop/direction cần thiết.
- Không đề xuất route suspended/ineligible.
- Chuẩn hóa no-result state thay vì trả result giả.
- Xử lý validation: origin trống, destination trống, origin == destination.
- Swap origin/destination không giữ stale result.

### Acceptance

- `A -> B` đúng order: match.
- `B -> A` không được match outbound `A -> B`.
- Không direct route: trả no-result rõ ràng.
- Route thiếu dữ liệu: exclude/degraded theo contract, không fabricate.
- Không còn hard-coded route fallback dùng như kết quả thật.

---

## 9. Task 7 - Schedule & Fare Correctness

**Ưu tiên:** **P0/P1**

### Mục tiêu

Làm đúng semantics thời gian vận hành và giá vé trước khi planner dựa vào các dữ liệu này.

### Scope Schedule

- Tách trạng thái `before_service`, `in_service`, `after_service`, `next_day`, `unknown`.
- Không áp headway vô hạn ngoài service window.
- Tính đúng `minutesUntilDeparture` trước giờ mở tuyến.
- Xử lý sau giờ kết thúc và ngày kế tiếp.
- Tách `schedule-derived` khỏi realtime ETA.

### Scope Fare

- Audit lại extraction/schema của fare.
- Không coi `singleTicket` là flat fare nếu nguồn là distance-tiered.
- Bổ sung `fareType`, `tiers`, provenance/source khi cần.
- Khi chưa đủ dữ liệu, UI hiển thị unknown/range/ghi chú phù hợp thay vì giá chắc chắn sai.

### Acceptance

- Case `00:46`, service starts `05:15` -> `before_service`, 269 phút.
- Sau giờ kết thúc -> trạng thái closed/next-day đúng contract.
- Tiered fare không hiển thị như flat fare.
- Route thiếu fare canonical -> không tự điền giá mặc định.

---

## 10. Task 8 - Data Quality Contract & Planner Readiness

**Ưu tiên:** **P1 / High**

### Mục tiêu

Biến tình trạng dữ liệu hiện tại thành contract có thể kiểm tra tự động, để planner chỉ dùng dữ liệu đủ tin cậy.

### Scope

- Bổ sung/chuẩn hóa metadata:

```text
dataQuality.hasOutboundStops
dataQuality.hasInboundStops
dataQuality.hasOutboundGeometry
dataQuality.hasInboundGeometry
dataQuality.hasFareModel
dataQuality.tripPlanningReady
```

- Xây validator xác định route đủ/không đủ điều kiện planner.
- Giữ fail-closed cho stop unresolved, geometry invalid và direction thiếu dữ liệu.
- Lập coverage report theo route/direction.
- Chuẩn bị spatial stop index/candidate contract để Task 4 có thể consume, nhưng không triển khai full address-to-address planner trong Task này.
- GPS -> nearby stop foundation chỉ dừng ở primitive/index/candidate query, không tạo `Trip[]` hay transfer routing.

### Acceptance

- Mỗi route có data-quality state rõ ràng.
- Planner eligibility không dựa vào phỏng đoán.
- Route chưa đủ dữ liệu bị loại khỏi planner nhưng catalog vẫn có thể hiển thị với trạng thái phù hợp.
- Coverage report reproducible bằng automated validator.

---

## 11. Task 9 - UI Integrity, Realtime Semantics & Accessibility

**Ưu tiên:** **P1/P2**

### Mục tiêu

UI chỉ hứa những capability hệ thống thực sự có và đáp ứng accessibility cơ bản.

### Scope UI truthfulness

- Phân biệt rõ schedule vs realtime.
- Không hiển thị `Live GPS`, `đang chạy`, `còn X phút` như realtime nếu nguồn chỉ là schedule.
- Route detail chỉ render vehicle type, amenities, seat/vehicle state, ETA khi dataset/provider thật sự có.
- Data không có -> `Chưa có dữ liệu` hoặc state tương đương.
- Chuẩn hóa loading/empty/error/offline state.

### Scope Voice/Reminder

- Voice: hoặc triển khai flow permission -> listening -> transcript -> location search, hoặc disable/hide capability demo.
- Reminder: hoặc có persistence + trigger + cancel/update + notification mechanism, hoặc đổi wording/disable để không giả scheduling.

### Scope Accessibility

- Bỏ khóa pinch-to-zoom (`user-scalable=no`, `maximum-scale=1.0`) nếu không có lý do accessibility hợp lệ.
- Chuyển action phù hợp sang native `<button>`.
- Keyboard behavior, focus state, accessible name/ARIA khi cần.

### Acceptance

- Không còn wording realtime sai nguồn.
- Không có action demo giả thành feature hoàn chỉnh.
- Keyboard interaction cho các action chính PASS.
- Zoom/accessibility baseline PASS.

---

## 12. Task 10 - Business-Logic Regression & Production Acceptance

**Ưu tiên:** **P1 / High**

### Mục tiêu

Biến các phát hiện audit thành regression guard để `tests PASS` phản ánh đúng rủi ro nghiệp vụ quan trọng.

### Test matrix bắt buộc

| Case | Expected |
|---|---|
| A -> B cùng direction, đúng order | PASS |
| B -> A ngược order | Không match outbound |
| origin == destination | Validation error |
| origin empty | Validation error |
| destination empty | Validation error |
| Không có direct route | No-result |
| Suspended/ineligible route | Không đề xuất |
| Route thiếu stop/geometry | Excluded/degraded |
| 00:46, service starts 05:15 | 269 phút / before-service |
| Sau giờ kết thúc | Closed/next-day đúng contract |
| Tiered fare | Không hiển thị flat fare sai |
| GPS coordinate | Nearby stop candidates hợp lệ |
| Swap locations | Không stale result |
| Voice/reminder disabled | Không tạo fake success |
| Sensitive public paths | Bị chặn |

### Verification layers

- Syntax/static checks hiện có.
- Unit/business-logic tests.
- Dataset/data-quality validator.
- Browser interaction tests.
- Public production smoke tests.
- Negative/error/offline cases.

### Acceptance

- Tất cả P0/P1 remediation trước đó có regression coverage tương ứng.
- Test failure phải fail closed, không bị che bằng fallback UI.
- Production smoke xác nhận security + search + schedule + UI semantics.
- TL review và acceptance report hoàn tất trước PO nghiệm thu.

---

## 13. Thứ tự triển khai đề xuất

Thứ tự ưu tiên thực thi không phụ thuộc hoàn toàn vào số Task: Task 3 đã CLOSED, còn Task 4 đã được PO duyệt nhưng phải chờ các dependency correctness/data-quality bắt buộc.

```text
Task 1 [DONE]
   |
   v
Task 2 [existing spatial baseline]
   |
   +------------------------------+
   |                              |
   v                              v
Task 5 P0 Security           Task 6 P0 Search
   |                              |
   +--------------+---------------+
                  |
                  v
             Task 7 Schedule/Fare
                  |
                  v
             Task 8 Data Quality
                  |
                  v
             Task 9 UI/A11y
                  |
                  v
             Task 10 Regression
                  |
                  v
        Task 4 [APPROVED]
                  |
                  v
       Production-grade Trip Planner

Task 3 [CLOSED] - không nằm trong execution hiện tại
```

### Execution policy

1. Task 5-7 xử lý P0/correctness trước.
2. Task 8 chuẩn hóa eligibility/data quality cho planner.
3. Task 9 làm sạch semantics/UX/accessibility dựa trên contract đã ổn định.
4. Task 10 khóa regression và kiểm tra production cho remediation wave.
5. Task 4 đã được PO phê duyệt và được triển khai sau remediation wave, dùng Task thread hiện có, không tạo trùng.
6. Task 3 đã CLOSED theo xác nhận PO; không triển khai thêm trong roadmap hiện tại.

---

## 14. Boundary để tránh chồng scope

| Hạng mục | Task sở hữu |
|---|---|
| Nginx/public exposure | Task 5 |
| Fake route fallback, direction/order | Task 6 |
| Service window/headway | Task 7 |
| Fare schema/tier | Task 7 |
| Route data-quality eligibility | Task 8 |
| Spatial primitive / nearby-stop candidate foundation | Task 8 |
| Address/POI -> Trip[] direct/transfer/walking/ranking | Task 4 |
| Schedule-vs-realtime wording | Task 9 |
| Voice/reminder integrity | Task 9 |
| Accessibility | Task 9 |
| Vehicle position/ETA thật | Task 3 |
| Cross-cutting business regression/public smoke | Task 10 |

---

## 15. Definition of Done cho remediation wave

Remediation wave Task 5-10 chỉ được xem là hoàn tất khi:

```text
[ ] Production không expose workspace/development artifacts
[ ] Không còn fake route fallback
[ ] Search validate direction + stop order
[ ] Schedule trước/sau service window đúng contract
[ ] Fare không bị biểu diễn sai thành flat fare
[ ] Route có data-quality/tripPlanningReady contract
[ ] UI không gọi schedule là realtime
[ ] Voice/reminder không giả capability
[ ] Accessibility baseline được sửa
[ ] Business-logic regression matrix PASS
[ ] Public production smoke PASS
[ ] TL review PASS
[ ] Acceptance report được tạo trong docs/reports/
```

Task 4 không nằm trong Definition of Done của remediation wave vì có acceptance riêng và đã được PO phê duyệt để triển khai sau wave này.

Task 3 đã CLOSED theo xác nhận PO, nên realtime integration không còn là điều kiện của roadmap hiện tại; yêu cầu bắt buộc vẫn là UI phải trung thực về việc chưa có realtime.

---

## 16. Task threads mới cần tạo sau khi PO duyệt plan

Plan này đề xuất **6 Task mới** từ audit, theo thứ tự:

1. `Production Security Hardening`
2. `Search Correctness & No-Fake-Result`
3. `Schedule & Fare Correctness`
4. `Data Quality Contract & Planner Readiness`
5. `UI Integrity, Realtime Semantics & Accessibility`
6. `Business-Logic Regression & Production Acceptance`

4 Task cũ vẫn được giữ trong roadmap để nhìn toàn cảnh, nhưng không tạo lại thread trùng.

PO đã phê duyệt toàn bộ execution scope. Tạo đúng 6 Task thread remediation mới theo danh sách trên; không tạo lại 4 Task cũ. Task 4 dùng thread hiện có và được triển khai sau remediation wave; Task 3 giữ CLOSED.
