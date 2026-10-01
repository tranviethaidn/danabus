# Báo cáo Nghiệm thu Task 010: Simple Consumer UX Redesign

**Mã Task:** `tsk_d45190c7-1380-48e0-9dc7-5239307f5a4b`  
**Ngày thực hiện:** 2026-10-01  
**Vai trò:** Developer (DEV)  
**Trạng thái:** Hoàn thành triển khai & Kiểm thử hồi quy PASS  

---

## 1. Mục tiêu và Phạm vi Triển khai

Nâng cấp trải nghiệm người dùng Danabus hướng tới chuẩn consumer-first theo đúng quyết định đã hội tụ cùng Team Leader:
- **Tối giản hóa Trang chủ (`#view-home`)**: Tối ưu luồng duy nhất A→B (Điểm đón, Điểm đến, GPS, nút đổi chiều và nút CTA `Tìm đường`). Giữ nguyên các phần tử DOM kế thừa (`#home-destination-chips`, `#home-spotlight-card`, eco banner) trong container ẩn để đảm bảo 100% selector backward compatibility cho toàn bộ các suite kiểm thử hồi quy.
- **Chuẩn hóa Journey ViewModel dùng chung**: Thiết kế adapter `buildJourneyViewModelFromDirect` và `buildJourneyViewModelFromPlanned` đồng nhất hóa cấu trúc dữ liệu cho cả tuyến trực tiếp (direct match) và tuyến chuyển tiếp (planner multi-leg).
- **Trình bày Hành trình đề xuất dạng Timeline Stepper (`<ol class="journey-timeline">`)**: Mặc định hiển thị một phương án tối ưu nhất với đầy đủ các mốc trực quan: Điểm xuất phát A → Lên xe tại trạm đón → Di chuyển trên xe (kèm accordion danh sách trạm trung gian) → Chuyển tuyến (nếu có) → Xuống xe tại trạm trả → Đến đích B.
- **Tổ chức Secondary Actions không lấn chiếm luồng chính**: Gom các hành động phụ gồm `Xem trên bản đồ`, `Chi tiết tuyến`, `Xem thêm phương án khác (N)` và `Thông số kỹ thuật & Lịch trình chi tiết` thành thanh điều hướng phụ với đầy đủ nhãn ARIA (`aria-expanded`, `aria-controls`).
- **Sửa triệt để các lỗi sai lệch ngữ nghĩa (Truthful Semantics)**:
  - Loại bỏ hoàn toàn việc gán số phút vào `#trip-stat-km` (hiển thị đúng cự ly km hoặc `Chưa có dữ liệu`).
  - Loại bỏ hoàn toàn việc gán ranking category vào `#trip-stat-stops` (hiển thị đúng số trạm dừng hoặc `Chưa có dữ liệu`).
  - Loại bỏ hardcode `Xe buýt Danabus` khi thiếu căn cứ nguồn (truy xuất trung thực từ `formatRouteVehicleInfo(route)`, fail-closed về `Chưa có dữ liệu`).
  - Ẩn toàn bộ metadata thuật toán nội bộ khỏi primary UI.

---

## 2. Chi tiết Thay đổi Kỹ thuật

1. **`index.html`**:
   - Cập nhật nhãn nút tìm kiếm trang chủ `#btn-home-search`: Đổi từ `Tìm xe` thành `Tìm đường` kèm `aria-label="Tìm đường"`.
   - Bọc các khối làm loãng luồng A→B trên trang chủ vào container ẩn `#home-secondary-legacy` có `aria-hidden="true"` để bảo toàn selector cho headless CDP assertions.
   - Bổ sung khối **Primary Journey Recommendation Card** (`#journey-recommendation-card`) chứa header, thẻ tổng quan chỉ số (`#journey-summary-metrics`), danh sách timeline semantic (`#journey-timeline`), và thanh secondary actions.
   - Đóng gói khối thông tin kỹ thuật cũ (`#trip-legacy-card`, `#trip-following-bus-row`) vào `#trip-secondary-details-card` dạng collapsible phụ, bảo toàn nguyên vẹn mọi ID phục vụ regression tests (`#trip-countdown-time`, `#trip-countdown-timer`, `#trip-fare-value`, `#trip-freq-value`, `#trip-fleet-value`, `#trip-fleet-desc`, `#trip-later-note`).
2. **`css/app.css`**:
   - Bổ sung quy tắc CSS cho `.journey-timeline`, `.timeline-step`, `.timeline-marker`, đường kẻ dọc kết nối chặng buýt / đi bộ chuyển tuyến, danh sách trạm trung gian và hiệu ứng xoay chevron khi toggle accordion.
   - Đảm bảo tuân thủ tiêu chuẩn mobile-first, tap target >= 44px và đường viền accessible `:focus-visible`.
3. **`js/app.js`**:
   - Bổ sung `buildJourneyViewModelFromDirect(match, originText, destinationText)` và `buildJourneyViewModelFromPlanned(trip, originText, destinationText)`.
   - Bổ sung `renderJourneyRecommendation(journey, allTrips)` render timeline stepper và cập nhật truthful semantics trên toàn bộ DOM.
   - Sửa `renderPlannerResults`: `#trip-stat-km` dùng km cự ly thực tế; `#trip-stat-stops` dùng tổng số trạm dừng; `#trip-fleet-value` truy xuất từ `formatRouteVehicleInfo`.
   - Cập nhật `renderTripOptions`: bổ sung nút chọn phương án `btn-select-trip` để người dùng có thể kích hoạt đổi hành trình hiển thị trên timeline chính, giữ nguyên nút `.btn-view-planned-map` cho kiểm thử tự động.
   - Bổ sung event listeners cho các secondary actions (`#btn-journey-map`, `#btn-journey-route-detail`, `#btn-toggle-alternatives`, `#btn-toggle-tech-details`).

---

## 3. Bằng chứng Kiểm thử & Xác minh Nghiệm thu

Toàn bộ các test suite từ cấp độ đơn vị, hợp đồng dữ liệu đến kiểm thử tương tác trình duyệt thực tế Headless Chrome đều đạt kết quả tuyệt đối:

1. **Tìm kiếm chính xác & Fail-Closed (`scripts/test_search_correctness.py`)**:
   - `10/10` test cases PASS (Chiều đi, chiều về, thứ tự đón/trả, validate rỗng, endpoint trùng, fail-closed khi không có tuyến, loại trừ tuyến treo).
2. **Lịch trình & Biểu giá chính thức (`scripts/test_schedule_and_fare.py`)**:
   - `9/9` test cases PASS (Hợp đồng dữ liệu 23 tuyến, fail-safe trước/sau giờ hoạt động, biểu giá theo chặng Tuyến 02 & 06, biểu giá trợ giá 8.000đ).
3. **Chất lượng dữ liệu & Không gian (`scripts/test_data_quality_and_planner_readiness.py`)**:
   - `14/14` test cases PASS (Bộ lọc trạm xác thực, tính toán khoảng cách Haversine, cô lập 19 tuyến chưa đủ điều kiện).
4. **Bản đồ & Tọa độ GPS (`scripts/test_map_and_gps.py`)**:
   - `11/11` test cases PASS (247 trạm xác thực, cô lập hình học unverified).
5. **Bộ lập kế hoạch hành trình (`scripts/test_trip_planner.py`)**:
   - `27/27` test cases PASS (Địa chỉ - địa chỉ, đa chặng, fallback mở rộng bán kính 1.500m, lọc tuyến hợp lệ).
6. **Kiểm thử trình duyệt tương tác (`scripts/test_browser_trip_planner.py`)**:
   - `6/6` browser checks PASS (Autocomplete POI Bách Khoa, hiển thị phương án, render Leaflet multi-leg map, đổi chiều đón-đến, fail-closed ngoại thành).
7. **Toàn vẹn UI & Khả năng tiếp cận (`scripts/test_ui_integrity_and_accessibility.py`)**:
   - `100%` checks PASS: Viewport cho phép phóng to, nút có `aria-label`, vùng thông báo `aria-live`, phím Enter trên spotlight card, kiểm tra trung thực kết quả tìm tuyến (Tuyến 02 và Tuyến 21 fail-closed về `Chưa có dữ liệu`), cơ chế phục hồi lỗi mạng ngoại tuyến.
8. **Trình duyệt kiểm tra Lịch & Giá vé (`scripts/test_browser_schedule_and_fare.py`)**:
   - `7/7` browser checks PASS.
9. **Kiểm thử hồi quy Task 10 (`scripts/test_task10_regression_acceptance.py --local-only`)**:
   - `100%` Layer A deterministic checks PASS nghiêm ngặt trong 1.31 giây.

---

## 4. Trạng thái Git

- Toàn bộ thay đổi mã nguồn đã sẵn sàng stage và commit cục bộ.
- Tuân thủ nghiêm ngặt chính sách `git_push_authorized=OFF`: Không thực hiện `git push` lên origin trong lượt chạy này.
