# Plan sửa bản đồ Route + GPS Danabus

## 1. Mục tiêu

Sửa đúng từ tầng dữ liệu, không vá thêm tọa độ hard-code. Sau khi hoàn tất:

- Mỗi tuyến có geometry riêng.
- Chiều đi và chiều về có dữ liệu độc lập.
- Bản đồ hiển thị đúng lộ trình thực tế thay vì dùng chung route mẫu.
- GPS người dùng phản ánh vị trí thiết bị thực tế và có thông tin accuracy/error.
- UI không thể hiện dữ liệu mô phỏng như dữ liệu realtime.
- Dataset và map rendering có automated validation.

## 2. Hiện trạng đã audit

### 2.1 Route trên map bị giống nhau

`js/mapService.js` hiện dùng một mảng `basePoints` hard-code để tạo polyline cho mọi route. `route` được truyền vào nhưng geometry thực tế không được lấy từ dữ liệu route.

Hệ quả:

- Các tuyến khác nhau vẫn có cùng hình polyline.
- Đổi route chủ yếu chỉ đổi metadata hiển thị.
- Chiều về chỉ đảo ngược cùng geometry, không phản ánh lộ trình chiều về thực tế.

### 2.2 Dataset thiếu dữ liệu GPS cần thiết

`data/danangbus_routes.json` có `routePaths`, stops, streets và mô tả lộ trình nhưng chưa có route geometry bằng tọa độ.

`data/danangbus_stops.json` có route, direction, stopOrder, tên trạm và tên đường nhưng chưa có `lat/lng` cho từng stop.

Hiện project biết:

```text
Route -> direction -> stop/street -> order
```

Nhưng thiếu:

```text
Stop -> latitude/longitude
Route + direction -> geometry/polyline
```

### 2.3 Current Location chưa đồng nhất với GPS thật

`locateUser()` đã dùng Browser Geolocation API nhưng chưa xử lý đầy đủ accuracy, permission, timeout và trạng thái lỗi.

Location picker hiện có luồng chỉ gán chuỗi `Vị trí hiện tại (Đà Nẵng)` mà không lấy GPS thật. Home cũng có nội dung mặc định dễ khiến người dùng hiểu là vị trí GPS đã được xác định.

### 2.4 Simulation gây hiểu nhầm

Map/timeline hiện có marker/trạng thái xe mô phỏng nhưng trình bày giống dữ liệu live. Nếu chưa có backend realtime thì cần bỏ hoặc ghi rõ là mô phỏng.

## 3. Kiến trúc dữ liệu mục tiêu

```text
Route
├── id / routeNumber
├── outbound
│   ├── stops[]
│   │   ├── stopId
│   │   ├── order
│   │   ├── lat
│   │   └── lng
│   └── geometry[]
│       └── [lat, lng]
└── inbound
    ├── stops[]
    └── geometry[]
```

Giữ `routePaths` và dữ liệu text hiện có nếu UI còn sử dụng để tránh regression không cần thiết.

## 4. Phase 1 - Chuẩn hóa data model

- Bổ sung tọa độ chuẩn cho stop.
- Bổ sung geometry cho từng route và từng direction.
- Không dùng `reverse()` như nguồn dữ liệu chiều về.
- Xác định schema rõ ràng cho geometry và stop coordinates.
- Không ghi dữ liệu tọa độ ước lượng như dữ liệu xác thực.
- Có metadata nguồn/chất lượng nếu dữ liệu được tổng hợp từ nhiều nguồn.
- Giữ compatibility với phần UI hiện tại cần `routePaths`, stops và streets.

## 5. Phase 2 - Xây dựng GPS dataset

Pipeline:

```text
route
  -> direction
     -> ordered stops
        -> xác định tọa độ stop
           -> xác định đường thực tế
              -> tạo route geometry
```

Validation tối thiểu:

- Điểm đầu và cuối đúng tuyến.
- Stop order đúng theo direction.
- Tọa độ hợp lệ, không có `[0,0]`, NaN hoặc giá trị ngoài phạm vi.
- Stop nằm hợp lý gần route geometry.
- Geometry không có bước nhảy tọa độ bất thường.
- Outbound/inbound không bị tráo.
- Route khác nhau không vô tình dùng cùng geometry do fallback.

Nếu source hiện tại không đủ tọa độ, cần xây pipeline bổ sung từ nguồn bản đồ/routing phù hợp. Không tự đoán tọa độ bằng tay để đưa vào production dataset.

## 6. Phase 3 - Refactor MapService

Loại bỏ hoàn toàn `basePoints` hard-code trong `js/mapService.js`.

Luồng mục tiêu:

```text
renderRoute(route, direction)
        |
        +-> getRouteGeometry()
        |
        +-> getDirectionStops()
        |
        +-> renderPolyline()
        |
        +-> renderStopMarkers()
        |
        +-> fitBounds()
```

Mapping phải đúng theo route và direction:

```text
Route 05 + outbound -> geometry 05/outbound
Route 05 + inbound  -> geometry 05/inbound
Route 07 + outbound -> geometry 07/outbound
Route 07 + inbound  -> geometry 07/inbound
```

Nếu route thiếu geometry:

- Không fallback sang route 02 hoặc route mẫu.
- Không vẽ geometry giả.
- UI hiển thị trạng thái rõ ràng: `Chưa có dữ liệu bản đồ cho tuyến này`.

Khi switch route/direction:

- Xóa layer cũ.
- Render đúng geometry mới.
- Render đúng stop markers mới.
- Fit bounds theo route mới.
- Không để stale marker/polyline từ route trước.

## 7. Phase 4 - GPS người dùng

Tách user location khỏi route rendering.

Luồng:

```text
Browser Geolocation API
        |
        +-> permission
        +-> latitude / longitude
        +-> accuracy
        +-> timestamp
        |
        v
UserLocation state
        |
        +-> user marker
        +-> accuracy circle
        +-> map center
```

Cấu hình dự kiến:

```js
{
  enableHighAccuracy: true,
  timeout: 10000,
  maximumAge: 30000
}
```

Xử lý đầy đủ:

- Permission denied.
- Position unavailable.
- Timeout.
- Browser không hỗ trợ.
- Secure-context requirement trên production.
- Accuracy thấp.
- GPS result cũ từ cache.

Không coi tọa độ trả về là chính xác tuyệt đối; UI cần có khả năng biểu diễn sai số bằng accuracy circle hoặc thông tin tương đương.

Chỉ dùng `watchPosition` nếu sản phẩm thực sự cần tracking liên tục; không bật tracking nền mặc định.

## 8. Phase 5 - Current Location trong UI

Hiện trạng cần loại bỏ:

```text
Vị trí hiện tại (Đà Nẵng)
Vị trí của bạn (Bến xe Trung tâm)
```

khi chưa thực sự lấy GPS.

Luồng mới:

```text
User nhấn Vị trí hiện tại
          |
          v
navigator.geolocation
          |
     +----+----+
     |         |
 success     error
     |         |
 lat/lng    UI báo lỗi
     |
     v
Location state
```

Trạng thái ban đầu nên là `Chọn điểm đón`.

Chỉ sau khi lấy GPS thành công mới hiển thị `Vị trí hiện tại` và giữ tọa độ thật trong application state để các chức năng tìm tuyến có thể sử dụng.

## 9. Phase 6 - Simulation/realtime

Audit và xử lý các trạng thái mô phỏng hiện có:

- Marker xe đang chạy trên map.
- Timeline `Xe đang tới`.

Nếu chưa có backend realtime:

- Bỏ trạng thái live giả; hoặc
- Gắn nhãn rõ ràng `Mô phỏng`.

Không trình bày dữ liệu simulation như dữ liệu realtime.

## 10. Phase 7 - Chuẩn bị route search theo vị trí

Không bắt buộc gộp toàn bộ routing engine vào bản sửa đầu tiên, nhưng data model mới phải hỗ trợ bước tiếp theo:

```text
Origin GPS
   |
nearest stops
   |
routes serving origin
   |
direct route / transfer candidates
   |
routes serving destination
   |
rank
   |
Trip options
```

Mục tiêu dài hạn là giảm phụ thuộc vào text matching trong `findRoutesBetween()` và chuyển sang spatial matching dựa trên tọa độ stop/origin/destination.

## 11. Phase 8 - Validation và test

Automated validation tối thiểu:

| Test | Acceptance |
|---|---|
| Route 05 vs 07 | Geometry khác nhau |
| Route 02 vs 05 | Geometry khác nhau |
| Outbound vs inbound | Đọc đúng dataset từng chiều |
| Missing geometry | Không render route giả |
| Stop coordinates | Tọa độ hợp lệ |
| Stop ordering | Đúng theo direction |
| GPS success | Marker dùng coordinate trả về |
| GPS denied | UI xử lý rõ, không crash |
| GPS timeout | UI xử lý rõ, không crash |
| GPS accuracy | Có thể biểu diễn sai số |
| Switch direction | Polyline và markers cập nhật |
| Switch route | Không giữ geometry/layer cũ |

Ngoài automated tests cần browser smoke test trên nhiều tuyến thực tế và cả hai direction.

## 12. Acceptance Criteria

Chỉ PASS khi đạt đồng thời:

```text
[ ] Không còn basePoints hard-code
[ ] Không route nào mượn geometry route khác
[ ] Outbound/inbound có dữ liệu độc lập
[ ] Stop GPS có validation
[ ] Route geometry có validation
[ ] Map bám đúng khu vực/lộ trình thực tế
[ ] Current Location dùng GPS thật
[ ] Có accuracy và error handling
[ ] Không thể hiện simulation như realtime
[ ] Switch route/direction không stale
[ ] Dataset validator PASS
[ ] Automated tests PASS
[ ] Browser smoke test PASS
```

## 13. Trình tự triển khai

Triển khai trong một Task nhưng chia milestone:

```text
Milestone 1: Data model + GPS dataset
        |
        v
Milestone 2: Map renderer
        |
        v
Milestone 3: User GPS + Current Location
        |
        v
Milestone 4: Simulation cleanup
        |
        v
Milestone 5: Validation + automated tests
        |
        v
Milestone 6: Browser smoke test + TL review
```

Không triển khai riêng `mapService.js` trước khi xác định data contract vì đây chính là nguyên nhân khiến implementation hiện tại phải dùng geometry hard-code.

## 14. Phạm vi chưa triển khai trong plan này

- Backend realtime vehicle tracking thực sự.
- ETA realtime.
- Full multimodal/transit routing engine.
- Tracking vị trí người dùng liên tục nếu chưa có requirement cụ thể.

Các phần này có thể phát triển sau trên data model GPS đã chuẩn hóa.
