# Kế hoạch Task 010 - Simple Consumer UX Redesign

**Task-ID:** `tsk_d45190c7-1380-48e0-9dc7-5239307f5a4b`  
**Ngày:** 2026-10-01  
**Trạng thái:** Sẵn sàng triển khai

## 1. Mục tiêu

Đơn giản hóa Danabus thành trải nghiệm consumer-first với một luồng chính duy nhất: chọn A, chọn B, dùng GPS khi cần, đổi chiều và bấm `Tìm đường`. Sau khi tìm, mặc định chỉ ưu tiên một hành trình tốt nhất ở dạng timeline dễ đọc; bản đồ, phương án khác, danh sách trạm và chi tiết kỹ thuật trở thành hành động phụ.

## 2. Quyết định sau discussion

- Giữ nguyên business logic planner/search/map đã có; không rewrite thuật toán.
- Giữ các ID DOM đang được regression tests sử dụng để tránh phá baseline, nhưng các khối legacy không còn là primary UI.
- Ẩn destination chips, route spotlight và eco notice khỏi primary Home; có thể giữ trong DOM nếu test còn phụ thuộc.
- Đổi CTA Home từ `Tìm xe` thành `Tìm đường`.
- Tạo một Journey ViewModel dùng chung cho direct route và planner multi-leg để timeline chỉ có một renderer.
- Mặc định hiển thị phương án đầu tiên/tốt nhất. Phương án còn lại chỉ mở khi người dùng yêu cầu.
- Map, intermediate stops và details là secondary actions.
- Không hiển thị metadata thuật toán/ranking ở primary UI.
- Không tạo realtime/ETA giả.

## 3. Semantics dữ liệu bắt buộc

### Theo lịch

Chỉ dùng cho dữ liệu lịch công bố như giờ xuất bến, service window và tần suất. Ví dụ: `Theo lịch: 05:30`, `Theo lịch: Còn 15 phút`.

### Ước tính

Dùng cho dữ liệu tính toán như tổng thời gian planner, quãng đi bộ Haversine và thời gian đi bộ suy ra. Ví dụ: `Ước tính: ~35 phút`.

### Không có dữ liệu

Khi source không cung cấp giá trị xác thực, phải hiển thị `Chưa có dữ liệu` hoặc ẩn trường. Không fallback hard-code.

Đặc biệt phải sửa semantics planner hiện tại:

- Không dùng `#trip-stat-km` để chứa phút.
- Không dùng `#trip-stat-stops` để chứa ranking category.
- Không gán `Xe buýt Danabus` làm vehicle info khi không có source xác thực.
- Không đưa `rankingCategory` như metadata thuật toán ra primary UI.

## 4. Luồng UI mục tiêu

### Home

- Origin.
- Destination.
- GPS trong location picker.
- Swap.
- CTA `Tìm đường`.
- Error validation rõ ràng.
- Không để spotlight/chips/banner cạnh tranh với CTA chính.

### Journey recommendation

Mặc định hiển thị một timeline theo thứ tự:

1. Điểm A và walking leg nếu có.
2. Trạm lên xe và tuyến.
3. Hành trình trên xe, số trạm nếu có dữ liệu.
4. Chuyển tuyến/walking transfer nếu có.
5. Trạm xuống xe.
6. Walking leg tới điểm B nếu có.

Timeline phải dùng semantic HTML phù hợp, ưu tiên `<ol>`.

### Secondary actions

- `Xem trên bản đồ`.
- `Xem thêm phương án khác (N)`.
- `Xem các trạm trung gian`.
- `Chi tiết tuyến` khi có route tương ứng.

Accordion/toggle phải có `aria-expanded`, keyboard focus và label rõ ràng.

## 5. Thay đổi kỹ thuật

- `index.html`: tối giản Home, thêm khu vực journey timeline, khu vực secondary actions, giữ selector compatibility cần thiết.
- `css/app.css`: styling timeline/mobile-first/focus, không phụ thuộc hover.
- `js/app.js`:
  - chuẩn hóa direct route và planner trip thành Journey ViewModel;
  - render một default recommendation;
  - quản lý selected journey và expand/collapse state;
  - preserve fail-closed;
  - không render metadata kỹ thuật như ranking ra primary UI.
- `js/busService.js`: chỉ sửa nếu cần helper thuần dữ liệu, không thay đổi thuật toán planner/search nếu không cần.
- `js/mapService.js`: reuse hiện có; chỉ wiring secondary action nếu cần.

## 6. Acceptance

- Home primary flow chỉ còn A→B, GPS, swap, `Tìm đường`.
- Direct route và planner multi-leg đều render qua cùng journey timeline.
- Chỉ một recommendation hiển thị mặc định.
- Alternatives/map/stops/details không chiếm primary surface.
- `Theo lịch`, `Ước tính`, `Chưa có dữ liệu` được dùng đúng nguồn dữ liệu.
- Không fake realtime, duration, fleet, fare, distance hoặc stops.
- Empty/fail-closed state vẫn hoạt động.
- Keyboard navigation, focus-visible và ARIA của toggle/accordion PASS.
- Các selector legacy cần cho regression vẫn tồn tại hoặc tests được cập nhật tương ứng mà không làm yếu acceptance.

## 7. Verification

Chạy ít nhất:

- `python scripts/test_search_correctness.py`
- `python scripts/test_schedule_and_fare.py`
- `python scripts/test_data_quality_and_planner_readiness.py`
- `python scripts/test_browser_trip_planner.py`
- `python scripts/test_ui_integrity_and_accessibility.py`
- `python scripts/test_task10_regression_acceptance.py --local-only`

Nếu browser/full acceptance cần chạy lâu, chạy nền và poll log theo policy timeout.

## 8. Git

Được phép commit local sau khi verification PASS. Không push vì runtime hiện tại `git_push_authorized=OFF`.
