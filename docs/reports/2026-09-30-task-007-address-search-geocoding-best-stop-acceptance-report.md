# Báo cáo nghiệm thu Task 007 - Address Search, Geocoding & Best Boarding/Alighting Stop

Task-ID: tsk_d92a4fab-8d37-40c9-8271-7d1ffcd0f6bf

## Phạm vi nghiệm thu

Task 007 triển khai luồng nhập điểm đón/điểm đến bằng địa chỉ, địa điểm, GPS, map pin và đổi A/B qua provider abstraction; tích hợp Google Places client-side theo cấu hình runtime an toàn; đồng thời thay nearest-stop-only bằng Best Stop Resolver xét nhiều trạm verified theo hướng tuyến, khả dụng dịch vụ, kết nối, chi phí đi bộ/chuyển tuyến/thời gian trên xe và chất lượng dữ liệu.

Task giữ nguyên Leaflet/OpenStreetMap để hiển thị bản đồ và không mở rộng sang multi-transfer graph của các Task tiếp theo.

## Bằng chứng triển khai

Các commit chính đã được TL review:

- `2ba81f019487aa40925ddd0f38291a13e366111c`: triển khai provider abstraction, Google provider ban đầu, map pin, Best Stop Resolver, radius expansion và explainable failures.
- `d8994e1`: sửa stale search, invalid endpoint guard, data-confidence ranking và timeout coverage.
- `6e8bd21`: chuyển Google Places sang client SDK lifecycle, loại bỏ direct REST browser fallback, dùng `AutocompleteSessionToken` và `PlacePrediction.toPlace().fetchFields()`.
- `406274d06e8b39191c295ca5a665f72eae021726`: bổ sung bounded timeout cho SDK loader/import và fail-safe fallback khi script bị treo.

Các file chính được thay đổi gồm `js/busService.js`, `js/app.js`, `js/mapService.js`, `index.html`, `scripts/test_trip_planner.py` và các regression guard liên quan.

## Kết quả review kỹ thuật

TL đã kiểm tra trực tiếp implementation và xác nhận các điều kiện nghiệm thu chính:

- Google Places chạy sau `LocationSearchProvider`; không hardcode key thật hoặc server secret.
- Runtime browser key, nếu cấu hình, được coi là public website-restricted credential; Leaflet/OSM vẫn là map renderer.
- Không còn direct browser REST call tới `places.googleapis.com/v1`.
- Client SDK được chủ động load; session dùng `AutocompleteSessionToken`; selected prediction resolve qua `toPlace().fetchFields()`.
- SDK load/import, search và details đều có bounded timeout/fail-safe; khi Google lỗi hoặc chưa cấu hình, local/GPS/map-pin vẫn hoạt động.
- Stale async request không còn ghi đè query mới ở cả provider/manager/UI render layer.
- Không lưu endpoint không có tọa độ hợp lệ khi Place Details thất bại.
- Best Stop Resolver dùng verified stops, kiểm tra service/direction/connectivity, radius khoảng 800 m và mở rộng có kiểm soát tới khoảng 1.500 m.
- Ranking có penalty chất lượng dữ liệu suy ra từ `route.dataQuality.stopMetrics` hiện có thay vì field giả lập.
- Direct route + tối đa 1 transfer được giữ nguyên; không hấp thụ scope graph multi-transfer.
- Các trạng thái `OUT_OF_SERVICE_AREA`, `NO_NEARBY_STOPS`, `NO_VIABLE_ROUTE` trả về hợp đồng giải thích được bằng tiếng Việt.

## Kiểm thử và xác minh

TL chạy lại độc lập trong lượt nghiệm thu hiện tại:

- `python3 scripts/test_trip_planner.py -v`: **20/20 PASS**.
- `python3 scripts/test_browser_trip_planner.py`: **6/6 PASS**.
- `python3 scripts/test_task10_regression_acceptance.py`: **20/20 PASS**.
- Reproduction riêng cho lỗi SDK loader bị treo:
  - provider `timeoutMs=20`;
  - script không phát `load` hoặc `error`;
  - `gp.search('Cầu Rồng')` settle sau khoảng **22 ms**, trả về mảng rỗng và không treo.
- Regression matrix xác nhận zero fake fallback và không phát sinh regression ở search, schedule/fare, data-quality, map/GPS, security và UI/offline recovery.

## Kết quả nghiệm thu

**PASS - Technical Acceptance.**

Task 007 đạt phạm vi kỹ thuật đã chốt sau ba vòng review-fix. Không còn defect bắt buộc sửa được phát hiện trong phạm vi Task.

## Giới hạn đã biết

- Repository không chứa Google API key thật. Google Places thực tế chỉ hoạt động khi deployment cấp một browser key được giới hạn đúng domain/API; khi chưa có key, hệ thống chủ động dùng local/GPS/map-pin fallback.
- Production browser smoke trong regression matrix xác minh phiên bản production hiện hành và regression tổng thể; nó không phải bằng chứng rằng commit Task 007 đã được publish/deploy.
- `git_push_authorized=OFF`, vì vậy toàn bộ commit hiện vẫn local và việc chưa push không phải blocker theo policy.
- Walking leg vẫn là Haversine estimate theo contract hiện tại, không giả lập road-routing geometry.
