# Báo cáo nghiên cứu API định vị xe buýt realtime cho Danabus

Ngày: 2026-09-24  
Phạm vi: nghiên cứu nguồn dữ liệu/API có thể dùng để hiển thị vị trí xe buýt theo thời gian thực cho project Danabus. Đây là báo cáo nghiên cứu, chưa triển khai integration.

## 1. Kết luận

DanaBus chính thức đang có khả năng theo dõi xe buýt theo thời gian thực. Tài liệu/hướng dẫn chính thức của DanaBus nêu ứng dụng cho phép theo dõi vị trí xe và các chuyến sắp đến trạm; bài giới thiệu năm 2026 nói dữ liệu đến từ hệ thống giám sát hành trình GPS lắp trên phương tiện.

Tuy nhiên, qua nguồn công khai đã kiểm tra, chưa xác nhận được một public API/documented endpoint dành cho bên thứ ba để lấy trực tiếp Vehicle Position realtime của DanaBus.

Hướng ưu tiên cho project:

1. Tìm và xin quyền sử dụng API chính thức từ hệ thống DanaBus/Trung tâm Điều hành giao thông thông minh Đà Nẵng.
2. Kiểm tra catalog/đặc tả API của dữ liệu mở Đà Nẵng. Danh mục dữ liệu mở xác nhận dữ liệu mạng lưới tuyến/trạm/giá vé được chia sẻ bằng API, nhưng phần mô tả công khai chưa xác nhận Vehicle GPS realtime.
3. Thiết kế Danabus theo adapter trung gian để nếu nguồn chính thức cung cấp GPS proprietary thì vẫn chuẩn hóa được sang internal realtime model hoặc GTFS-Realtime.
4. Không phụ thuộc vào reverse-engineering private API của ứng dụng DanaBus cho production.

## 2. Bằng chứng DanaBus có realtime GPS

Nguồn DanaBus chính thức:
- Hướng dẫn DanaBus: https://www.danangbus.vn/tin-tuc/tin-tuc/huong-dan-su-dung-ung-dung-danabus-1128.html
- Giới thiệu DanaBus 2026: https://www.danangbus.vn/tin-tuc/tin-tuc/danabus--nguoi-ban-dong-hanh-thong-minh-cua-hanh-khach-xe-buyt-da-nang-5727.html
- Trang tính năng DanaBus 2026: https://www.danangbus.vn/tin-tuc/tin-tuc/ung-dung-danabus-5584.html

Các nguồn này xác nhận các chức năng:
- Theo dõi vị trí xe buýt theo thời gian thực.
- Hiển thị xe trên bản đồ.
- Theo dõi xe chuẩn bị đến trạm.
- Dữ liệu realtime được mô tả là đến từ hệ thống giám sát hành trình GPS trên phương tiện.

Do đó bài toán của project không phải tự tạo hệ thống GPS từ đầu; vấn đề chính là tìm kênh truy cập dữ liệu được phép sử dụng.

## 3. Dữ liệu mở Đà Nẵng

Danh mục dữ liệu mở giao thông của Đà Nẵng có mục “Dữ liệu mạng lưới tuyến, biểu đồ chạy xe trên tuyến, giá vé xe buýt trên địa bàn”, định dạng chia sẻ API. Mô tả công khai bao gồm tuyến xe buýt, trạm dừng và giá vé.

Nguồn tham khảo:
- https://investdanang.gov.vn/documents/20121/46199/962%2Bqd.signed-1.pdf/7c934c8c-5d04-cbb8-19c2-789f67c26355?t=1709282502293

Điểm cần lưu ý: tài liệu này chứng minh có API cho dữ liệu bus tĩnh/operational nói trên, nhưng không đủ để kết luận API công khai có latitude/longitude realtime của từng xe.

## 4. Map4D

Có bằng chứng năm 2026 Trung tâm Điều hành giao thông thông minh Đà Nẵng có kế hoạch thuê dịch vụ nền tảng bản đồ Map4D thông qua API trên App DanaBus.

Nguồn tham khảo:
- https://dauthau.asia/kehoach/luachon-nhathau/thue-dich-vu-nen-tang-ban-do-map4d-thong-qua-api-tren-app-danabus-2247887.html

Điều này cho thấy Map4D là một thành phần bản đồ của hệ sinh thái DanaBus, nhưng không chứng minh Map4D là nguồn Vehicle GPS. Cần phân biệt:
- Map provider: tiles, geocoding, routing, map visualization.
- Fleet/GPS source: vị trí thực tế của phương tiện.

Không nên mua/map API rồi kỳ vọng tự động có vị trí xe DanaBus.

## 5. GTFS-Realtime

Nếu có quyền truy cập GPS phương tiện, kiến trúc nên tương thích GTFS-Realtime.

Các entity phù hợp:
- VehiclePositions: vị trí phương tiện.
- TripUpdates: tiến độ chuyến/ETA.
- ServiceAlerts: cảnh báo dịch vụ.

Internal model đề xuất:

```text
RealtimeVehicle
├── vehicleId
├── routeId
├── tripId
├── latitude
├── longitude
├── bearing
├── speed
├── timestamp
├── source
└── freshness
```

Frontend không nên đọc trực tiếp API proprietary. Nên đi qua adapter:

```text
Official DanaBus GPS/API
          |
          v
Realtime Provider Adapter
          |
          +-- normalize vehicle/route/trip IDs
          +-- validate coordinates
          +-- freshness/stale detection
          +-- retry/rate-limit/cache
          |
          v
Danabus Realtime API
          |
          v
Leaflet realtime layer
```

## 6. Tiêu chuẩn freshness

Vị trí realtime phải có timestamp. Client/backend phải phân biệt:
- LIVE: dữ liệu còn mới.
- STALE: dữ liệu quá cũ.
- OFFLINE/UNKNOWN: không có dữ liệu đủ tin cậy.

Không được giữ marker cũ trên bản đồ rồi tiếp tục trình bày như xe đang ở vị trí đó.

Nếu provider hỗ trợ cập nhật nhanh, có thể polling/WebSocket/SSE tùy contract. Không nên chọn cadence trước khi biết rate limit và đặc tả nguồn.

## 7. Những phương án không nên nhầm là Vehicle GPS API

### OpenStreetMap / Leaflet
Dùng cho bản đồ và dữ liệu địa lý, không cung cấp vị trí realtime của xe DanaBus.

### Routing API
Có thể tính đường giữa các điểm nhưng không biết xe thực tế đang ở đâu.

### Browser Geolocation
Chỉ xác định vị trí người dùng, không phải vị trí xe.

### Map4D
Có thể là nền tảng bản đồ đang dùng bởi DanaBus, nhưng bằng chứng hiện có chưa chứng minh đây là nguồn GPS phương tiện.

## 8. Rủi ro reverse-engineering

Có thể về mặt kỹ thuật ứng dụng mobile gọi endpoint nội bộ để nhận vị trí xe. Tuy nhiên không nên lấy endpoint private làm production dependency nếu chưa có quyền sử dụng, vì:
- contract không công khai;
- endpoint/token có thể thay đổi;
- có thể có authentication/device binding;
- rate limit không rõ;
- điều khoản sử dụng dữ liệu không rõ;
- thay đổi app có thể làm integration hỏng bất kỳ lúc nào.

Reverse-engineering chỉ nên được xem là hoạt động khảo sát kỹ thuật khi có quyền phù hợp, không phải nền tảng production mặc định.

## 9. Đề xuất bước tiếp theo

### Ưu tiên A — Official API
Liên hệ/tra catalog API của cơ quan vận hành DanaBus để hỏi cụ thể:
- Có Vehicle Position API hay không?
- Có Trip/ETA API hay không?
- Authentication/API key?
- Rate limit?
- Update frequency?
- Route/trip/vehicle ID mapping?
- Terms/license?
- Sandbox/test endpoint?
- Có WebSocket/SSE hay chỉ REST polling?

### Ưu tiên B — Chuẩn bị adapter
Không chờ provider mới thiết kế code. Có thể định nghĩa interface provider độc lập để Task realtime sau này chỉ cần cắm nguồn hợp lệ.

### Ưu tiên C — GTFS-Realtime compatibility
Nếu provider không xuất GTFS-RT nhưng cho phép dùng GPS, backend Danabus có thể normalize dữ liệu về model tương thích GTFS-RT/internal contract.

## 10. Quan hệ với Task GPS/geometry hiện tại

Task “Sửa bản đồ Route và GPS Danabus” vẫn phải hoàn thành route geometry, stop coordinates và GPS người dùng độc lập với realtime vehicle tracking.

Kiến trúc cuối:

```text
STATIC / SEMI-STATIC
Route geometry + Stops
          |
          v
       Base Map
          ^
          |
REALTIME  |
Vehicle GPS Adapter
          |
          +--> moving bus markers
          +--> freshness
          +--> ETA (nếu có dữ liệu)
```

Nếu realtime API lỗi, route/stops vẫn hoạt động bình thường.

## 11. Kết luận cho PO

Có cơ sở chắc chắn rằng hệ thống DanaBus thật có GPS realtime. Hiện chưa có đủ bằng chứng công khai để khẳng định tồn tại public Vehicle Position API mà project có thể gọi ngay.

Giải pháp production nên ưu tiên API chính thức/có cấp quyền, đặt một adapter ở giữa và chuẩn hóa dữ liệu realtime. GTFS-Realtime là mô hình tham chiếu tốt cho VehiclePositions/TripUpdates, nhưng việc dùng được realtime Đà Nẵng phụ thuộc quyền truy cập nguồn GPS thực tế.

Không nên biến API map/routing thành “GPS realtime”, và không nên đưa private endpoint reverse-engineered vào production khi chưa xác minh quyền sử dụng.
