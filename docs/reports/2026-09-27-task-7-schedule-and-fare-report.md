# Báo Cáo Triển Khai & Nghiệm Thu Kỹ Thuật: Task 7 - Schedule & Fare Correctness

Task-ID: tsk_5383b0dd-f368-4e3a-b104-a5fbb161f328

- **Dự án:** Danabus (`danabus.638686.xyz`)
- **Người thực hiện:** Developer (DEV)
- **Người nhận bàn giao:** Tech Lead (TL) / Project Owner (PO)
- **Ngày thực hiện:** 27/09/2026
- **Trạng thái:** HOÀN TẤT KHẮC PHỤC (Đã xử lý TL Re-review lần 3 - Sẵn sàng nghiệm thu)

---

## 1. Phạm Vi Triển Khai (Scope)

Triển khai đầy đủ và nghiêm ngặt Task 7 theo đúng kết luận discussion của Tech Lead, roadmap đã duyệt và các yêu cầu trong 2 đợt review của TL:
1. **Chuẩn hóa Contract `calculateNextDeparture` với đủ 5 trạng thái**:
   - `before_service`: Trước chuyến đầu tiên trong ngày (ví dụ Tuyến 02 tại `00:46` tính đến giờ mở tuyến `05:15` ra đúng **269 phút**, không modulo).
   - `in_service`: Trong khung giờ hoạt động và còn chuyến hợp lệ trong ngày; `isOperating = true`.
   - `after_service`: Khung giờ hôm nay đã kết thúc nhưng chưa có chuyến ngày mai đủ tin cậy (ví dụ tuyến theo lịch bay `01SB` sau 22:00, hoặc tùy chọn `allowNextDay: false`); `timeStr: null`, `minutesUntilDeparture: null`.
   - `next_day`: Đã xác định được chuyến đầu tiên ngày mai và tính toán chính xác `minutesUntilDeparture` qua mốc nửa đêm (1440 phút).
   - `unknown`: Tuyến tạm dừng (`suspended`), `isActive: false`, thiếu/sai định dạng khung giờ hoạt động, hoặc thiếu/sai tần suất chạy xe (`frequency`).
2. **Loại bỏ triệt để Headway Modulo, Giờ giả định & Mặc định Headway 15 phút**:
   - Xóa bỏ lỗi modulo khoảng cách (`minutesLeft % interval`) làm sai lệch thời gian khởi hành (trước đây biến 269 phút thành 14 phút).
   - Xóa bỏ hoàn toàn giá trị fallback giả lập `{ timeStr: '08:30', minutesLeft: 6 }` khi dữ liệu không hợp lệ; thay bằng fail-closed `unknown`.
   - **Xóa bỏ hoàn toàn headway mặc định 15 phút**: Khi không có `timetable` hợp lệ và `frequency` thiếu, rỗng `{}` hoặc giá trị `peakMinutes`/`offPeakMinutes` <= 0 hoặc không phải số (`NaN`, chuỗi...), hệ thống trả về `unknown`, tuyệt đối không bịa đặt lịch trình chuyến.
3. **Chống Tạo Exact Headway Gây False Precision Cho Các Tuyến Có Tần Suất Dạng Khoảng (Range)**:
   - Khi tuyến chỉ công bố tần suất dạng khoảng (ví dụ Tuyến 02 `15-30 phút/lượt`, Tuyến 06 `30-60 phút/chuyến`, Tuyến 13 `15-60 phút/lượt`, Tuyến 21 `05-30 phút/lượt`) mà không chỉ rõ khung giờ cao điểm / thấp điểm cụ thể:
   - Hệ thống **tuyệt đối không tự biến thành exact headway** để tạo giờ chuyến giả định (như `08:15` hay countdown cố định 15/30 phút).
   - Trong service window, hàm trả về fail-safe `status: 'in_service'`, `isOperating: true`, `timeStr: null`, `minutesUntilDeparture: null`, `message: 'Đang hoạt động (tần suất ...)'`.
   - Chỉ áp dụng tính toán bước nhảy giờ chính xác khi tuyến có `timetable` hoặc tần suất đồng nhất đã xác thực (`type: 'fixed'` / `exactHeadway: true`).
4. **Ưu tiên Biểu đồ giờ chi tiết (`timetable`) hơn tần suất giả định (`headway`)**:
   - Khi tuyến có biểu đồ giờ (`timetable`) hợp lệ (như `TKY-TMY`), hệ thống đọc trực tiếp danh sách chuyến thay vì suy diễn theo tần suất.
5. **Hỗ trợ Injectable `currentTime`**:
   - Nhận diện linh hoạt `Date`, chuỗi `'HH:mm'`, hoặc số phút tính từ 00:00 phục vụ kiểm thử đơn vị độc lập.
6. **Nâng cấp Schema & Phân loại Biểu giá (Fare)**:
   - Hỗ trợ `flat`, `distance_tiered`, `unknown`, `tiers`, `minPrice`, `maxPrice`, `studentPrice`, và `provenance`.
   - Giữ `singleTicket` chỉ dành cho các tuyến thực sự đồng giá (`flat`); các tuyến theo chặng (`distance_tiered`) và chưa rõ (`unknown`) bắt buộc gán `null`.
   - Phân loại 23 tuyến dựa trên bằng chứng thực tế từ `rawSummary`; tuyến 09 và 13 fail-closed sang `unknown`.
7. **Dọn sạch Fallback giá giả & Tần suất giả trên toàn bộ UI**:
   - Xóa bỏ hoàn toàn các chuỗi fallback cứng `'8.000đ'`, `'30.000đ'`, `'8k - 30k'`, `'15-30 phút'`, `'15-30p'`.
   - Gỡ bỏ hard-code trên Home Spotlight: thay thế chuỗi tĩnh `Tần suất 15 phút • 05:15 - 18:30` bằng phần tử `#spotlight-schedule` được render động từ canonical helpers `formatRouteFrequency` và `formatRouteOperatingHours`.
   - Đảm bảo tính nhất quán tuyệt đối giữa Home Spotlight, Danh mục tuyến (Catalog), Chi tiết tuyến (Detail), và Kết quả tìm chuyến (Trip Results) cùng bám sát nguồn dữ liệu gốc `raw`.

---

## 2. Bằng Chứng Triển Khai Chi Tiết (Implementation Evidence)

### A. [`data/schema.ts`](file:///home/opc/danabus/data/schema.ts)
- Bổ sung `FrequencyType = 'fixed' | 'range' | 'peak_offpeak' | 'irregular'`.
- Nâng cấp `Frequency`:
  ```typescript
  export interface Frequency {
    type?: FrequencyType;
    peakMinutes?: number | null;
    offPeakMinutes?: number | null;
    minMinutes?: number | null;
    maxMinutes?: number | null;
    exactHeadway?: boolean;
    raw: string;
  }
  ```
- Định nghĩa đầy đủ `ScheduleStatus`, `ScheduleDepartureResult`, `FareType`, `FareTier`, `FareProvenance`, `FareInfo`.

### B. [`data/danangbus_routes.json`](file:///home/opc/danabus/data/danangbus_routes.json)
Rà soát và chuẩn hóa dữ liệu 23 tuyến theo phân loại có căn cứ:
- **Tần suất Chạy xe (Frequency Reconciled)**:
  - **Tuyến 02**: `type: 'range'`, `minMinutes: 15`, `maxMinutes: 30`, `peakMinutes: 15`, `offPeakMinutes: 30`, `exactHeadway: false`, `raw: '15-30 phút/lượt.'`. Loại bỏ giá trị lệch lạc cũ (`peak: 30, offPeak: 30`).
  - **Tuyến 03, 06, 14, LK02, LK21**: `type: 'range'`, `exactHeadway: false`, min/max khớp đúng văn bản gốc `raw`.
  - **Tuyến 13**: `type: 'range'`, `minMinutes: 15`, `maxMinutes: 60`, `exactHeadway: false`, `raw: '15-60 phút/lượt.'` (trước đây bị gán ép 60/60).
  - **Tuyến 21**: `type: 'range'`, `minMinutes: 5`, `maxMinutes: 30`, `exactHeadway: false`, `raw: '05-30 phút/lượt.'` (trước đây bị gán ép 30/30).
  - **Tuyến LK01**: `type: 'range'`, `minMinutes: 14`, `maxMinutes: 15`, `exactHeadway: false`, `raw: '14 - 15 phút/chuyến'`.
  - **Tuyến 05, 07, 08, 11, 12, 09, 04**: `type: 'peak_offpeak'`, có chỉ định cao điểm / thấp điểm rõ ràng trong `raw`.
  - **Tuyến TKY-TMY, TKY-NTH, 10, 15**: `type: 'fixed'`, `exactHeadway: true`.
  - **Tuyến 01SB, 01DL, TKY-CHU**: `type: 'irregular'`, `exactHeadway: false`, `peakMinutes: null`, `offPeakMinutes: null` (loại bỏ hoàn toàn các con số giả định 30/60 hay 60/120).
- **Khung Giờ Hoạt Động (Operating Hours)**:
  - Chuẩn hóa định dạng `start` và `end` thành `HH:mm` đồng nhất trên toàn bộ 23 tuyến (ví dụ `05:15`, `04:45`, `05:00`, `06:00`).
- **Biểu Giá (Fare)**:
  - 10 tuyến `flat`: `singleTicket = flatPrice` (05, 07, 08, 11, 12, 04, 10, 15, LK01, 01SB).
  - 11 tuyến `distance_tiered`: `singleTicket: null`, khai báo đủ khoảng giá và tiers (02, 06, 03, 14, 21, TKY-TMY, TKY-NTH, TKY-CHU, 01DL, LK02, LK21).
  - 2 tuyến `unknown`: Tuyến 09 và 13 `singleTicket: null`, `type: 'unknown'`.

### C. [`js/busService.js`](file:///home/opc/danabus/js/busService.js)
- Cập nhật hàm `calculateNextDeparture(route, options)`:
  - Fail-closed khi tần suất thiếu, rỗng `{}` hoặc không hợp lệ.
  - Xử lý tuyến `irregular` (lịch bay / du lịch): trả về fail-safe không tạo giờ giả.
  - Phân biệt giữa tuyến `hasExactHeadway` (fixed/timetable) và tuyến `isRange`: với các tuyến range như Tuyến 02, trả về `in_service` với `timeStr: null`, `minutesUntilDeparture: null`, `message: 'Đang hoạt động (tần suất 15-30 phút)'`. Tuyệt đối không sinh departure giả `08:15`.
  - Tính toán chính xác thời điểm trước giờ chạy `before_service` (ví dụ `00:46 → 05:15 = 269 phút`) và qua ngày mai `next_day` (`20:00 → 05:15 = 555 phút`).
- Cập nhật helper `formatRouteFrequency(route, short = false)`:
  - Hỗ trợ đầy đủ các loại tần suất: `irregular` (`Theo lịch bay` / `Lịch bay`), `range` (`15-30 phút` / `15-30p`), `fixed` (`45 phút` / `45p`), fail-closed `Đang cập nhật`.
- Bổ sung helper `formatRouteOperatingHours(route)`:
  - Chuẩn hóa hiển thị giờ hoạt động có 2 chữ số (ví dụ `05:15 - 18:30`).
- Helper `formatRouteFare(route)`:
  - Trả về biểu giá chuẩn xác theo đúng loại vé.

### D. [`js/app.js`](file:///home/opc/danabus/js/app.js)
- `startSpotlightTicker()`:
  - Cập nhật động `#spotlight-schedule` qua `formatRouteFrequency(route02)` và `formatRouteOperatingHours(route02)` (loại bỏ hoàn toàn text tĩnh).
  - Cập nhật `#spotlight-countdown`: khi `in_service` không có exact timeStr, hiển thị `Đang hoạt động (15-30 phút)` trung thực.
- `renderRoutesList()`:
  - Thẻ danh mục hiển thị tần suất chuẩn qua `formatRouteFrequency(r, true)` (ví dụ `15-30p/chuyến`), giờ chạy qua `formatRouteOperatingHours(r)`.
- `openRouteDetail()`:
  - Hiển thị `#detail-stat-freq` qua `formatRouteFrequency(route)` (`15-30 phút`) và `#detail-stat-hours` qua `formatRouteOperatingHours(route)`.
- `showTripResults()`:
  - Khi `in_service` của tuyến range: `#trip-countdown-time` hiển thị `Đang chạy`, `#trip-countdown-timer` hiển thị `15-30 phút`, `#trip-freq-value` hiển thị `15-30p`, `#trip-later-time` hiển thị `Tần suất: 15-30 phút`.
  - Loại bỏ hoàn toàn fallback và false precision.

### E. [`index.html`](file:///home/opc/danabus/index.html)
- Cập nhật `#home-spotlight-card`: gán ID `#spotlight-schedule` cho phụ đề và thay thế placeholder thành `Tần suất 15-30 phút • 05:15 - 18:30`.
- Làm sạch các placeholder tĩnh trung tính trên toàn bộ trang.

### F. Đồng bộ Production Web Root (`/var/www/danabus/public`)
- Đã sao chép toàn bộ deliverables (`index.html`, `js/busService.js`, `js/app.js`, `data/danangbus_routes.json`) sang `/var/www/danabus/public`.
- Xác nhận khớp 100% (diff rỗng) và phân quyền file an toàn `644`.

---

## 3. Kết Quả Kiểm Thử (Checks & Tests Evidence)

### 1. Test Suite Chuyên Biệt Task 7: [`scripts/test_schedule_and_fare.py`](file:///home/opc/danabus/scripts/test_schedule_and_fare.py)
Chạy bộ kiểm thử tự động gồm 9 ca kiểm thử Python, bao gồm contract verification trực tiếp bằng Node.js:
- `test_before_service_269_min`: Tuyến 02 tại `00:46` → `status: before_service`, `timeStr: 05:15`, `minutesUntilDeparture: 269` (**PASS**, không modulo).
- `test_in_service_window_range_fail_safe`: **[MỚI]** Tuyến 02 tại `08:00` (range `15-30 phút/lượt`) → `status: in_service`, `isOperating: true`, `timeStr: null`, `minutesUntilDeparture: null`, message `Đang hoạt động (tần suất 15-30 phút)` (**PASS**, không tạo exact departure `08:15` gây false precision).
- `test_in_service_exact_headway`: **[MỚI]** Tuyến có exact headway (`type: 'fixed'`, interval 30m) tại `07:10` → `status: in_service`, `timeStr: 07:30`, `minutesUntilDeparture: 20` (**PASS**, tính toán exact headway hoạt động chính xác khi có căn cứ).
- `test_next_day_departure`: Tuyến 02 tại `20:00` → `status: next_day`, `timeStr: 05:15`, `minutesUntilDeparture: 555` (**PASS**).
- `test_after_service_no_next_day`: `allowNextDay: false` → `status: after_service`, `timeStr: null` (**PASS**).
- `test_after_service_no_next_day`: `allowNextDay: false` → `status: after_service`, `timeStr: null` (**PASS**).
- `test_irregular_flight_after_service`: Tuyến 01SB sau 22:00 → `status: after_service`, `timeStr: null` (**PASS**).
- `test_irregular_routes_before_service_fail_safe`: **[MỚI]** Tuyến `01SB`, `TKY-CHU`, `01DL` trước service window → `status: 'before_service'`, `timeStr: null`, `minutesUntilDeparture: null`, `isOperating: false`, message mô tả giờ mở tuyến, không bịa chuyến đầu (**PASS**).
- `test_timetable_priority_05_35`: Tuyến TKY-TMY tại `05:10` → lấy đúng trip timetable `05:35` (**PASS**).
- `test_service_cutoff_boundary`: Tuyến 02 tại `18:35` (sau giờ đóng tuyến 18:30) → chuyển sang `next_day` (**PASS**).
- `test_malformed_schedule_fail_closed`: Dữ liệu sai lệch / tạm ngưng → `status: unknown`, `timeStr: null` (**PASS**).
- `test_missing_and_invalid_frequency_fail_closed`: 8 trường hợp tần suất thiếu/sai → toàn bộ trả về `status: unknown`, `timeStr: null` (**PASS**, không default 15m).
- `test_format_route_frequency_helper`: Kiểm tra helper hiển thị cho range (Tuyến 02: `15-30 phút` / `15-30p`), fixed (Tuyến 10: `45 phút`), irregular (Tuyến 01SB: `Theo lịch bay` / `Lịch bay`), fail-closed `Đang cập nhật` (**PASS**).
- `test_route_02_frequency_and_views_consistency`: Khóa tính nhất quán của Tuyến 02: `raw = 15-30 phút/lượt.`, `type = range`, `minMinutes = 15`, `maxMinutes = 30`, `exactHeadway = false` (**PASS**).
- `test_tiered_fare_02_and_06`: Khoảng giá Tuyến 02 (`8.000đ - 30.000đ`) và Tuyến 06 (`15.000đ - 22.000đ`), `singleTicket: null` (**PASS**).
- `test_unknown_fare_routes_09_and_13`: Tuyến 09 và 13 trả về `Đang cập nhật`, không fake `'8k - 30k'` hay `'30.000đ'` (**PASS**).
- `test_subsidized_and_commercial_flat_fare_integrity`: Tuyến 05 (`8.000đ`), LK01 (`80.000đ`), 01SB (`120.000đ`) (**PASS**).

**Kết quả TL verify:** `Ran 9 tests in 0.203s - OK (100% PASS)`

### 2. Browser Integration Test: [`scripts/test_browser_schedule_and_fare.py`](file:///home/opc/danabus/scripts/test_browser_schedule_and_fare.py)
Kiểm tra DOM thực tế trên Headless Chrome qua giao thức CDP:
- `[Check 1]` Spotlight Fare: `8.000đ - 30.000đ`, Phụ đề lịch chạy: `Tần suất 15-30 phút • 05:15 - 18:30` (không còn hard-code `15 phút`), Countdown hợp lệ (**PASS**).
- `[Check 2]` Catalog Routes: Tuyến 02 hiển thị `15-30p/chuyến` và `8.000đ - 30.000đ`, Tuyến 06 `30-60p/chuyến`, Tuyến 05 `8.000đ`, Tuyến 09 & 13 `Đang cập nhật`, Tuyến LK01 `80.000đ`, Tuyến 01SB `120.000đ` và `Lịch bay` (**PASS**).
- `[Check 3]` Tuyến 02 Detail: `Vé lượt: 8.000đ - 30.000đ`, Tag: `Theo chặng`, Tần suất: `15-30 phút` (**PASS**).
- `[Check 4]` Tuyến 05 Detail: `Vé lượt: 8.000đ`, Tag: `Trợ giá` (**PASS**).
- `[Check 5]` Tuyến 09 Detail: `Vé lượt: Đang cập nhật`, Tag: `Đang cập nhật` (**PASS**).
- `[Check 6]` Trip Search Results: Tuyến 02 cước phí `8.000đ - 30.000đ`, tần suất `15-30p`, thời gian khởi hành hợp lệ và fail-closed `Đang cập nhật` khi frequency thiếu (**PASS**).
- `[Check 7]` Ảnh bằng chứng nghiệm thu giao diện: [`docs/reports/task7_schedule_fare_evidence.png`](file:///home/opc/danabus/docs/reports/task7_schedule_fare_evidence.png) (50.043 bytes sau lần TL verify độc lập) (**PASS**).

**Kết quả:** `ALL TASK 7 BROWSER ACCEPTANCE CHECKS PASSED (7/7)`

### 3. Toàn Bộ Bộ Kiểm Thử Hồi Quy (Cross-Cutting Regression)
- `scripts/security_smoke_test.py`: **26/26 PASS** (15 negative 404, 10 positive 200, HTTP→HTTPS redirect).
- `scripts/test_search_correctness.py`: **10/10 PASS** (21 Node checks PASS, monotonic direction, zero fake fallback).
- `scripts/test_map_and_gps.py`: **11/11 PASS** (Stops, GPS coordinates, layers integrity).
- `scripts/browser_smoke_test.py`: **8/8 PASS** (Boot, catalog, map rendering, GPS context, SW cache v7).

---

## 4. Kết Quả Nghiệm Thu (Review Result)

### Lịch sử Review & Sửa đổi
- **TL Review lần 1**: Phát hiện lỗi default 15m khi frequency thiếu/invalid → Đã sửa fail-closed `unknown`.
- **TL Re-review lần 2**: Phát hiện Tuyến 02 raw `15-30 phút` bị mất semantics thành exact headway 30 phút và Home Spotlight hard-code 15 phút → Đã reconcile Tuyến 02 về `range` 15-30 phút, loại bỏ exact headway giả lập và xóa bỏ hard-code trên Home.
- **TL Re-review lần 3**: Phát hiện false precision trên các tuyến `irregular` trước service window (`01SB`, `01DL`, `TKY-CHU` coi `operatingHours.start` là exact first departure với wording 'chuyến đầu').

### Khắc phục của DEV sau TL Re-review lần 3
1. **Xử lý triệt để false precision cho route `irregular` trước service window**:
   - Khi `isIrregular` là true (`frequency.type === 'irregular'`, hoặc ghi chú giờ bay/chuyến bay) và không có timetable chi tiết: trước service window (`currentMinutes < startTotal`), hàm `calculateNextDeparture` giữ `status: 'before_service'`, nhưng trả về `timeStr: null`, `minutesUntilDeparture: null`, `minutesLeft: null`, `isOperating: false`.
   - Message chuyển thành mô tả trung thực khung giờ mở tuyến: `Chưa đến khung giờ hoạt động (mở tuyến: HH:mm)`, tuyệt đối không sử dụng wording `chuyến đầu`.
   - Duy trì after-service fail-safe: sau giờ đóng tuyến trả về `status: 'after_service'`, `timeStr: null`, `minutesUntilDeparture: null`, không suy đoán chuyến ngày mai.
2. **Cập nhật giao diện `js/app.js`**:
   - `startSpotlightTicker` và `showTripResults` kiểm tra an toàn `dep.timeStr`: nếu null thì hiển thị trạng thái trung tính `Chưa mở tuyến (HH:mm)` thay vì ghép chuỗi `null`.
3. **Bổ sung Regression Tests khóa hành vi**:
   - Thêm `test_irregular_routes_before_service_fail_safe` trong `scripts/test_schedule_and_fare.py` kiểm tra cả 3 tuyến `01SB`, `TKY-CHU`, `01DL`.
   - Thêm kiểm tra `irregular_routes_before_service` trong `test_nodejs_busservice_contract`.
4. **Đồng bộ Production**:
   - Toàn bộ files deliverable (`index.html`, `js/app.js`, `js/busService.js`, `data/danangbus_routes.json`) đã đồng bộ 100% sang `/var/www/danabus/public`.
   - Đã kiểm tra diff hoàn toàn rỗng.
5. **Chạy lại toàn bộ 6 test suite**: Đạt **100% PASS** trên tất cả các kịch bản.

**Kết luận DEV:** Đã hoàn thành khắc phục toàn diện theo đúng yêu cầu của TL Re-review lần 3. Sẵn sàng bàn giao cho Tech Lead nghiệm thu.

### TL Final Verification - 2026-09-27
- TL đã đọc trực tiếp nhánh xử lý `irregular` trong `js/busService.js` và xác nhận trước service window trả `before_service` với `timeStr: null`, `minutesUntilDeparture: null`, không dùng wording `chuyến đầu`; sau service window tiếp tục fail-safe `after_service`.
- TL xác nhận production web root khớp workspace cho `index.html`, `js/busService.js`, `js/app.js`, `data/danangbus_routes.json` bằng `diff -q` rỗng.
- TL chạy lại độc lập toàn bộ 6 suite: Task 7 `9/9 PASS`, Browser Task 7 `7/7 PASS`, Security `26/26 PASS`, Search `10/10 PASS`, Map/GPS `11/11 PASS`, Browser smoke `8/8 PASS`.
- Không phát hiện regression hoặc false precision còn lại trong scope Task 7 ở vòng verify này.

**Kết quả TL:** PASS. Task 7 đạt technical acceptance và sẵn sàng chuyển PO review.

---

## 5. Giới Hạn Đã Biết (Known Limitations)

1. **Dữ liệu giá vé Tuyến 09 & 13**: Tài liệu gốc của đơn vị vận hành không công bố biểu giá số tiền cụ thể (chỉ có liên kết đăng ký thẻ trực tuyến). Hệ thống chủ động để trạng thái `unknown` (`Đang cập nhật`) theo đúng nguyên tắc bảo đảm tính trung thực dữ liệu, chờ tài liệu bổ sung từ đơn vị vận hành.
2. **Biểu đồ giờ chi tiết (`timetable`)**: Hiện tại chỉ có 2 tuyến Quảng Nam (`TKY-TMY` và `TKY-NTH`) có mốc giờ từng chuyến chi tiết. Các tuyến còn lại hoạt động theo tần suất (`frequency`) trong khung giờ vận hành cố định.
