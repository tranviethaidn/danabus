# Báo Cáo Nghiệm Thu Kỹ Thuật: Task 6 - Search Correctness & No-Fake-Result

- **Dự án:** Danabus (`danabus.638686.xyz`)
- **Mã Task:** `tsk_4a770fbf-10f1-4376-abe3-79abc1d47436` (Task 6)
- **Người thực hiện:** Developer (DEV)
- **Người nhận bàn giao:** Tech Lead (TL)
- **Ngày hoàn thành:** 27/09/2026
- **Trạng thái:** Hoàn tất triển khai & Verification 10/10 PASS

---

## 1. Tóm Tắt Mục Tiêu & Phạm Vi Triển Khai

Task 6 tập trung giải quyết triệt để các khiếm khuyết cốt lõi về tính chính xác của tìm kiếm chuyến đi trực tiếp, loại bỏ hoàn toàn các cơ chế fake/fallback giả định, và bảo đảm tính trung thực dữ liệu (truthfulness & data integrity) theo đúng roadmap đã được phê duyệt:

1. **Monotonic Directional Search:** So khớp điểm đón và điểm đến độc lập theo từng chiều (`outbound` và `inbound`), bắt buộc thỏa mãn điều kiện đơn điệu `originIndex < destinationIndex`.
2. **Loại bỏ Tuyệt đối Fake Fallback & Hardcoded Defaults:**
   - Xóa bỏ việc ép gán Tuyến 02 khi không tìm thấy chuyến (`matchedRoutes.length === 0`).
   - Xóa bỏ việc tự ý gán `Bến xe TT` và `Phố cổ Hội An` khi người dùng bấm tìm kiếm mà chưa nhập dữ liệu.
3. **Fail-Closed No-Result State:** Khi không có tuyến đi thẳng hoặc truy vấn không hợp lệ, hệ thống hiển thị màn hình rỗng minh bạch, không giả định hành trình.
4. **Input Validation:** Xác thực dữ liệu đầu vào với các mã lỗi rõ ràng: `EMPTY_ORIGIN`, `EMPTY_DESTINATION`, `SAME_ORIGIN_DESTINATION`.
5. **Non-Stale Swap Handling:** Khi đảo chiều điểm đón/đến, UI tự động hủy/re-evaluate kết quả tìm kiếm, không giữ dữ liệu chiều cũ.
6. **Đồng bộ Matched Direction:** Đồng bộ `matchedDirection` sang Route Detail và Map View khi người dùng chọn xem lộ trình từ kết quả tìm kiếm.
7. **Bảo toàn Ranh giới (Scope Boundaries):** Không can thiệp sang logic lịch trình/giá vé (Task 7), spatial/contract (Task 8), hay multi-leg routing (Task 4).

---

## 2. Chi Tiết Các Thay Đổi Mã Nguồn

### A. [`js/busService.js`](file:///home/opc/danabus/js/busService.js)
- Thêm hàm `validateSearchQuery(originText, destinationText)`:
  - Kiểm tra `EMPTY_ORIGIN`: bắt lỗi khi để trống, hoặc giữ placeholder `"Chọn điểm đón"`.
  - Kiểm tra `EMPTY_DESTINATION`: bắt lỗi khi để trống điểm đến.
  - Kiểm tra `SAME_ORIGIN_DESTINATION`: bắt lỗi khi điểm đón và điểm đến trùng nhau sau khi chuẩn hóa.
- Thêm hàm `resolveSearchTokens(queryNorm)`:
  - Phân giải các từ khóa địa danh phổ biến (`Phố cổ Hội An`, `Bến xe TT`, `Cầu Rồng`, `Cửa Đại`, `Sân bay`, `Bà Nà`, `Ngũ Hành Sơn`, `Phụ sản Nhi`).
- Thêm hàm `stopMatchesQuery(stop, queryNorm, tokens, isFirst, isLast, terminals, dir)`:
  - So khớp chính xác theo tên trạm, tên đường, tên hiển thị và điểm đầu/cuối bến bãi theo từng chiều di chuyển.
- Tái cấu trúc toàn diện `findRoutesBetween(originText, destinationText)`:
  - Bỏ qua các tuyến `status === 'suspended'` hoặc `isActive === false`.
  - Bỏ qua chiều di chuyển có `stops.length < 2`.
  - Tìm tập chỉ số trạm đón `origIndices` và trạm trả `destIndices`.
  - Kiểm tra nghiệm hợp lệ: tìm cặp `(oi, di)` đầu tiên thỏa mãn `oi < di`.
  - Trả về đối tượng kết quả chuẩn hóa gồm: `route`, `matchedDirection`, `originIndex`, `destinationIndex`, `originStop`, `destinationStop`, `stopCount`.

### B. [`js/app.js`](file:///home/opc/danabus/js/app.js)
- **Quản lý trạng thái tìm kiếm:** Bổ sung `lastSearchQuery` và `matchedDirection`.
- **Validation UI Banner:** Bổ sung `showSearchValidationError()` và `clearSearchValidationError()`. Tự động xóa lỗi khi người dùng chọn trạm từ picker hoặc chip gợi ý.
- **Loại bỏ Default Fake Inputs:** Tại `#btn-home-search`, đọc trực tiếp giá trị thực từ giao diện, chạy qua `validateSearchQuery`. Nếu không hợp lệ, kích hoạt banner cảnh báo và dừng xử lý, tuyệt đối không gán chuỗi giả định.
- **Tái cấu trúc `showTripResults(originText, destinationText)`:**
  - Nếu `matchedRoutes.length === 0`: chuyển sang trạng thái Fail-Closed Empty State, ẩn countdown, cước phí và bản đồ giả định.
  - Nếu có kết quả: hiển thị thông tin chuyến, số trạm đi qua trên đúng chiều `matchedDirection`.
- **Cải tiến `openRouteDetail(routeId, direction)`:** Tiếp nhận tham số `direction`, giúp đồng bộ chiều di chuyển tìm được sang màn hình chi tiết lộ trình và bản đồ GPS.
- **Xử lý Nút Đảo chiều (Swap Locations) Không Stale:**
  - Tại trang chủ: Hoán đổi điểm đón/đến; nếu đang ở màn hình kết quả, tự động tính toán lại theo chiều mới.
  - Tại màn hình kết quả: Thêm nút `#btn-trip-swap` cho phép đổi chiều tức thì và cập nhật lại giao diện.

### C. [`index.html`](file:///home/opc/danabus/index.html)
- Bổ sung khối thông báo lỗi `#home-search-error` trên thẻ tìm kiếm trang chủ.
- Tách `#view-trip-results` thành 2 container độc lập:
  - `#trip-content-success`: Hiển thị chuyến xe sắp chạy, thống kê, cước phí và CTA xem lộ trình khi tìm thấy tuyến.
  - `#trip-content-empty`: Hiển thị thông báo *"Không tìm thấy tuyến buýt đi thẳng"*, kèm 2 nút hành động dẫn tới danh mục tuyến hoặc quay lại trang chủ.
- Bổ sung nút `#btn-trip-swap` tại thanh tiêu đề kết quả tìm chuyến.

---

## 3. Bằng Chứng Kiểm Thử Tự Động (Verification Evidence)

Đã xây dựng bộ kiểm thử tự động tại [`scripts/test_search_correctness.py`](file:///home/opc/danabus/scripts/test_search_correctness.py), kiểm tra đồng thời trên Python logic và Node.js thực thi trực tiếp file [`js/busService.js`](file:///home/opc/danabus/js/busService.js) cùng dữ liệu thực tế:

```text
======================================================================
TASK 6 AUTOMATED ACCEPTANCE TEST SUITE: SEARCH CORRECTNESS
======================================================================
Loaded 23 routes from dataset.

Executing Node.js direct verification of js/busService.js...
PASS: All 21 Node.js checks passed successfully.

Detailed Test Matrix Summary:
  [PASS] 1. test_direct_match_outbound (Bến xe TT -> Phố cổ Hội An)
  [PASS] 2. test_direct_match_inbound (Phố cổ Hội An -> Bến xe TT)
  [PASS] 3. test_reverse_order_rejection (Hội An -> Bến xe TT on outbound)
  [PASS] 4. test_validation_empty_origin ('', 'Chọn điểm đón')
  [PASS] 5. test_validation_empty_destination ('')
  [PASS] 6. test_validation_same_endpoints (Bến xe TT -> Bến xe TT)
  [PASS] 7. test_no_direct_route_fail_closed (Bến xe TT -> Hà Nội)
  [PASS] 8. test_suspended_route_exclusion (Tuyến 04, 10, R15)
  [PASS] 9. test_missing_stops_route_exclusion (Tuyến thiếu stops < 2)
  [PASS] 10. test_swap_locations_invalidation (Directional inversion & non-stale)

======================================================================
ALL 10/10 ACCEPTANCE TEST CASES PASSED STRICTLY.
Zero fake fallback detected. Monotonic direction verified.
======================================================================
```

### Kiểm Tra Hồi Quy (Regression Tests)
1. **Browser Smoke Test (`scripts/browser_smoke_test.py`):**
   - 8/8 checks PASS (Khởi động ứng dụng, danh mục 23 tuyến, render bản đồ Tuyến 02/05/11/TKY, chuyển chiều không rò rỉ layer, geolocation mock, Service Worker cache v7).
2. **Production Security Smoke Test (`scripts/security_smoke_test.py`):**
   - 15/15 negative security checks PASS (khóa hoàn toàn `.git`, `docs`, `scripts`, source/config nội bộ).
   - 10/10 positive functional checks PASS (200 OK + MIME đúng chuẩn + cache headers).

---

## 4. Trạng Thái Triển Khai Production

- Mã nguồn đã được đồng bộ vào `/var/www/danabus/public` với quyền phân bổ `opc:nginx` chuẩn xác (644/755).
- Nginx phục vụ trực tiếp tại domain `https://danabus.638686.xyz`.
- Đã kiểm tra cú pháp và tính toàn vẹn qua curl Nginx nội bộ: HTTP 200 OK.
- Git commit hash: `9cb23dd4209637477be97096c5b2afcd11a24de6`.

---

## 5. Kết Luận & Đề Xuất Bàn Giao

Task 6 - Search Correctness & No-Fake-Result đã hoàn thành toàn bộ tiêu chí kỹ thuật và acceptance criteria được giao. DEV kính đề xuất Tech Lead (TL) tiến hành nghiệm thu và kích hoạt Task tiếp theo trong approved roadmap (Task 7: Schedule & Fare Correctness).
