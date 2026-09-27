# Báo Cáo Audit Toàn Dự Án Danabus

**Ngày audit:** 27/09/2026  
**Vai trò thực hiện:** Tech Lead (TL)  
**Dự án:** Danabus PWA (`/home/opc/danabus`)  
**Loại báo cáo:** Full-project audit, không thay đổi source  
**Mục tiêu:** Đánh giá mức sẵn sàng production, độ tin cậy của tìm chuyến, dữ liệu tuyến/trạm, tính đúng của schedule/fare, UI semantics, accessibility và coverage kiểm thử.

---

## 1. Executive Summary

Danabus hiện có nền tảng UI/PWA khá hoàn chỉnh cho use case tra cứu tuyến, bản đồ và hiển thị thông tin. Tuy nhiên, audit cho thấy hệ thống chưa nên được xem là một transit planner đáng tin cậy ở production.

Ba rủi ro cần xử lý trước tiên:

1. **Production exposure:** static hosting có nguy cơ public cả workspace như `.git`, `docs`, `scripts` và source nội bộ.
2. **Search correctness:** logic tìm tuyến hiện có thể trả kết quả không hợp lệ theo direction/stop order và còn fallback kết quả giả.
3. **Schedule correctness:** phép tính chuyến kế tiếp ngoài giờ hoạt động có thể trả thời gian sai đáng kể.

Các nhóm tiếp theo cần xử lý gồm data completeness, fare schema, phân biệt schedule với realtime, GPS-to-stop spatial search, business-logic test coverage, voice/reminder integrity và accessibility.

---

## 2. Production Exposure

### Mức độ

**P0 / Critical**

### Phát hiện

Ứng dụng hiện mang đặc trưng static web app và nếu production phục vụ trực tiếp workspace root thì có nguy cơ expose các nội dung không dành cho public như:

```text
.git/
docs/
scripts/
source nội bộ
các artifact phát triển
```

Điều này tạo rủi ro lộ lịch sử repository, tài liệu nội bộ, scripts và implementation details.

### Hướng xử lý

Production nên chỉ publish explicit public artifact, ví dụ:

```text
public/
dist/
build/
```

và có deny rules cho các path nội bộ nếu hạ tầng không hỗ trợ isolated document root.

Nguyên tắc:

```text
workspace != public web root
```

---

## 3. Search Có Fallback Kết Quả Giả

### Mức độ

**P0 / Critical**

### Phát hiện

Search hiện có fallback về một tuyến mẫu, đặc biệt Tuyến 02, khi không tìm được kết quả phù hợp.

Hành vi dạng:

```text
Không match được query
        ↓
fallback Tuyến 02
        ↓
UI vẫn hiển thị như kết quả thật
```

là không an toàn cho ứng dụng giao thông vì tạo **fabricated certainty**.

### Yêu cầu đúng

Nếu không có route hợp lệ:

```text
Không có direct route phù hợp
```

hoặc:

```text
Chưa đủ dữ liệu để đề xuất tuyến
```

Không được trả một tuyến mẫu chỉ để UI luôn có kết quả.

---

## 4. `findRoutesBetween` Chưa Validate Direction Và Stop Order

### Mức độ

**P0 / Critical**

### Phát hiện

Logic hiện tại chủ yếu kiểm tra origin và destination có nằm trong danh sách stop của một route hay không, nhưng chưa bảo đảm:

```text
origin index < destination index
```

trên cùng direction.

Ví dụ:

```text
Outbound stops:
A → B → C → D

Query:
C → A
```

Nếu chỉ kiểm tra membership:

```text
C exists = true
A exists = true
→ route match
```

nhưng kết quả thực tế là sai chiều.

### Logic cần có

```text
for each route:
    for each direction:
        originIndex = index(origin)
        destinationIndex = index(destination)

        valid only when:
            originIndex >= 0
            destinationIndex >= 0
            originIndex < destinationIndex
```

Nếu direction ngược có dữ liệu riêng thì phải kiểm tra độc lập trên direction đó.

---

## 5. Next Departure Ngoài Giờ Hoạt Động Có Thể Sai

### Mức độ

**P0 / Critical**

### Phát hiện

Schedule math hiện có dấu hiệu suy diễn chuyến kế tiếp bằng headway mà chưa xử lý đầy đủ trạng thái trước giờ mở tuyến hoặc sau giờ đóng tuyến.

Ví dụ:

```text
Thời điểm hiện tại: 00:46
Tuyến bắt đầu:      05:15
```

Khoảng cách đúng là:

```text
269 phút
```

Hệ thống không nên áp headway lặp vô hạn từ đầu ngày hoặc biểu diễn như xe sắp đến.

### State cần phân biệt

```text
before_service
in_service
after_service
next_day
unknown
```

### Contract đề xuất

```js
{
  status: "before_service",
  nextDeparture: "05:15",
  minutesUntilDeparture: 269,
  source: "schedule"
}
```

---

## 6. GPS Hiện Chưa Đi Vào Transit Planning

### Mức độ

**P1 / High**

### Phát hiện

GPS hiện chủ yếu phục vụ:

```text
GPS
 ↓
lat/lng
 ↓
hiển thị "Vị trí hiện tại"
```

nhưng planner vẫn thiên về xử lý text.

Khoảng trống chính là chưa có bước:

```text
lat/lng
 ↓
findNearbyStops()
 ↓
candidate boarding stops
 ↓
TransitPlanner
```

### Kiến trúc cần hướng tới

```text
GPS / Address
      |
      v
   lat/lng
      |
      v
Spatial stop search
      |
      v
Candidate stops
      |
      v
Transit graph / planner
```

---

## 7. Spatial Data Chưa Đủ Cho Planner/Map Đáng Tin Cậy

### Mức độ

**P1 / High**

### Phát hiện

Dataset hiện có:

```text
23 routes
```

Nhưng coverage geometry được audit:

```text
Có geometry:     4 routes
Không geometry: 19 routes
```

Các route có geometry hiện tại:

```text
05
TKY-TMY
TKY-NTH
TKY-CHU
```

Có **13 tuyến không có stop ở cả hai direction**:

```text
07
08
11
12
03
06
09
13
14
LK01
04
10
15
```

Trong đó **10 tuyến vẫn mang status `active`**:

```text
07
08
11
12
03
06
09
13
14
LK01
```

Hai tuyến chỉ có stop một direction:

```text
LK02
LK21
```

### Hệ quả

Catalog có thể hiển thị:

```text
23 tuyến
```

nhưng điều đó không đồng nghĩa:

```text
23 tuyến có thể route đầy đủ
```

### Contract đề xuất

```json
{
  "dataQuality": {
    "hasOutboundStops": true,
    "hasInboundStops": true,
    "hasOutboundGeometry": true,
    "hasInboundGeometry": true,
    "tripPlanningReady": true
  }
}
```

Planner chỉ nên sử dụng route đạt contract cần thiết.

---

## 8. Fare Đang Được Mô Hình Hóa Quá Đơn Giản

### Mức độ

**P1 / High**

### Phát hiện

Schema hiện có `singleTicket`, nhưng raw source cho thấy có tuyến áp dụng giá theo cự ly.

Ví dụ Tuyến 02:

```text
≤ 10 km      → 8.000đ
10–25 km     → 20.000đ
...
```

Trong dataset:

```text
singleTicket = 8000
```

Nếu UI hiển thị:

```text
Giá vé: 8.000đ
```

người dùng có thể hiểu sai đây là giá cho toàn tuyến.

Một trường hợp đáng chú ý khác là Tuyến 06 hiện có:

```text
singleTicket = 8000
```

trong khi `rawSummary` chứa thông tin:

```text
≤ 1/2 cự ly tuyến (≤10,65 km): 15.000đ
```

Điều này cho thấy cần audit lại extraction/schema trước khi dùng `singleTicket` như canonical flat fare.

### Schema phù hợp hơn

```json
{
  "fareType": "distance_tiered",
  "tiers": [
    {
      "maxDistanceKm": 10,
      "price": 8000
    },
    {
      "maxDistanceKm": 25,
      "price": 20000
    }
  ]
}
```

Khi Trip Planner biết boarding/alighting stop thì mới có thể xác định fare phù hợp.

---

## 9. Một Số Chức Năng UI Hiện Thiên Về Demo

### Mức độ

**P1-P2 / Medium-High**

### Voice Search

Voice button hiện chưa tương ứng với một flow voice-recognition hoàn chỉnh.

Flow production hợp lý:

```text
Web Speech API / provider
        ↓
permission
        ↓
listening
        ↓
transcript
        ↓
location search
```

Nếu chưa có capability thật thì nên ẩn hoặc disable thay vì tạo cảm giác đã hỗ trợ.

### “Nhắc tôi”

`Nhắc tôi` hiện thiên về feedback/alert, chưa phải notification scheduling thực sự.

Reminder đúng nghĩa cần:

```text
permission
↓
persist reminder
↓
service worker / notification mechanism
↓
trigger
↓
cancel/update
```

Nếu chưa có thì wording nên phản ánh đúng hành vi thực tế.

### Realtime

Các wording như:

```text
chuyến tới
còn X phút
đang chạy
Live GPS
```

phải phân biệt rõ:

```text
schedule-derived
```

với:

```text
realtime-derived
```

Nếu chưa có realtime provider hợp lệ, UI không nên khiến người dùng hiểu schedule estimate là realtime ETA/location.

---

## 10. Route Detail Còn Assumption/Hard-Code

### Mức độ

**P2 / Medium**

Một số thuộc tính route detail có dấu hiệu được thiết kế từ route mẫu rồi áp dụng rộng:

```text
loại phương tiện
tình trạng
tiện nghi
ETA
seat/vehicle state
```

Chỉ nên render khi dataset/provider thật sự cung cấp.

Nguyên tắc:

```text
Data có
→ render

Data không có
→ "Chưa có dữ liệu"

Không được:
Data không có
→ đoán/default đẹp cho UI
```

Đối với transit app, **unknown tốt hơn fabricated certainty**.

---

## 11. Automated Tests PASS Nhưng Chưa Cover Đúng Rủi Ro Nghiệp Vụ

### Mức độ

**P1 / High**

### Checks hiện có

Các syntax check đã từng được xác nhận pass:

```text
node --check js/app.js
node --check js/busService.js
node --check js/mapService.js
node --check sw.js
python3 -m py_compile scripts/*.py
```

Browser smoke hiện kiểm tra các phần như:

```text
app boot
23 route cards render
route navigation
map initialization
markers/polyline
GPS/map behavior
```

Đây là regression baseline tốt, nhưng chưa đủ để chứng minh transit logic đúng.

### Khoảng trống coverage

Audit không thấy coverage trực tiếp cho các interaction/business logic quan trọng:

```text
showTripResults
findRoutesBetween
home voice
picker voice
remind trip
swap locations
search validation
trip direction/order
no-result behavior
```

Vì vậy:

```text
Tests PASS
```

không đồng nghĩa:

```text
Transit logic đúng
```

### Test matrix cần bổ sung

| Case | Expected |
|---|---|
| A → B cùng direction, đúng order | PASS |
| B → A ngược order | Không match outbound |
| origin == destination | Validation error |
| origin empty | Validation error |
| destination empty | Validation error |
| Không có direct route | No-result |
| Suspended route | Không đề xuất |
| Route thiếu stop | Excluded/degraded |
| 00:46, service starts 05:15 | 269 phút / before-service |
| Sau giờ kết thúc | tomorrow/closed |
| Tiered fare | Không hiển thị flat fare sai |
| GPS | Nearby stop candidates |

---

## 12. Accessibility Cần Chỉnh

### Mức độ

**P2 / Medium**

`index.html` hiện có cấu hình viewport dạng:

```html
maximum-scale=1.0
user-scalable=no
```

Điều này khóa pinch-to-zoom và không phù hợp accessibility, đặc biệt với người dùng lớn tuổi.

Ngoài ra có các vùng click dạng:

```html
<div onclick="...">
```

nhưng không phải tất cả đều có đầy đủ:

```text
button semantics
keyboard behavior
aria label
focus state
```

Nên ưu tiên native:

```html
<button>
```

cho các action tương tác.

---

## 13. Vấn Đề Kiến Trúc Gốc

Trạng thái hiện tại gần với:

```text
                DANABUS HIỆN TẠI
                       |
        +--------------+--------------+
        |              |              |
        v              v              v
      UI tốt       Route catalog    Map
                       |
                       v
                Static dataset
                       |
             +---------+---------+
             |                   |
             v                   v
       Text matching        Schedule math
             |                   |
             +---------+---------+
                       |
                       v
                "Trip result"
```

Trong khi transit planner đúng nghĩa cần:

```text
                    User intent
                        |
           +------------+------------+
           |                         |
           v                         v
      Origin GPS/address      Destination address
           |                         |
           +------------+------------+
                        |
                        v
                  lat/lng pair
                        |
                        v
                Spatial stop search
                 /              \
                /                \
        origin candidates    destination candidates
                \                /
                 +------+-------+
                        |
                        v
                 Transit graph
                        |
          +-------------+-------------+
          |                           |
          v                           v
       direct                    one transfer
          |                           |
          +-------------+-------------+
                        |
                        v
            direction/order validation
                        |
                        v
                     ranking
                        |
                        v
                     Trip[]
```

Task 2 đang xây nền GPS + geometry; Task 4 nên là nơi biến nền này thành planner thực sự.

---

## 14. Thứ Tự Xử Lý Đề Xuất

| Ưu tiên | Hạng mục | Lý do |
|---|---|---|
| **P0** | Khóa public access `.git`, `docs`, `scripts`, source nội bộ | Security production |
| **P0** | Bỏ fallback Tuyến 02 / địa điểm giả | Ngăn kết quả giả |
| **P0** | Sửa `findRoutesBetween` direction + stop order | Ngăn chỉ đường sai |
| **P0** | Sửa next-departure ngoài giờ | Tránh sai thời gian hàng giờ |
| **P1** | Audit fare schema | Tránh báo giá vé sai |
| **P1** | Data completeness contract | 19/23 tuyến chưa có geometry |
| **P1** | Phân biệt schedule và realtime | Tránh misleading UX |
| **P1** | GPS → spatial stop search | Vị trí hiện tại mới hữu dụng cho planner |
| **P1** | Bổ sung business-logic test matrix | Ngăn regression |
| **P2** | Voice/reminder hoàn chỉnh hoặc disable | UI integrity |
| **P2** | Accessibility | Zoom, keyboard, semantics |
| **P2** | Chuẩn hóa empty/error/offline state | UX production |

---

## 15. Quan Hệ Với Roadmap Hiện Tại

Không nên nhét toàn bộ remediation vào Task 4.

Boundary phù hợp hơn:

```text
Task 2
GPS + route geometry + stop data
        |
        v
Spatial foundation
        |
        +----------------------+
        |                      |
        v                      v
Task 4                    Task 3
Trip Planner              Realtime
        |                      |
        +----------+-----------+
                   |
                   v
          Realtime Trip Planner
```

Các lỗi audit hiện tại nên có remediation scope riêng:

```text
Audit remediation
├── Production exposure
├── Existing search correctness
├── Schedule calculation
├── Fare correctness
├── Misleading UI states
├── Accessibility
└── Regression tests
```

Cách chia này tránh để Task 4 vừa xây planner mới vừa xử lý toàn bộ technical debt cũ.

---

## 16. Kết Luận

Danabus hiện **đủ tốt ở mức prototype/catalog PWA và có nền UI khá đầy đủ**, nhưng chức năng “tìm chuyến” chưa nên được xem là một transit planner production đáng tin cậy.

Ba vấn đề cần ưu tiên cao nhất:

```text
1. Production đang có nguy cơ expose workspace/.git
2. Search có thể trả tuyến không hợp lệ và fallback kết quả giả
3. Departure/time logic có lỗi ngoài giờ hoạt động
```

Sau đó mới đến data completeness, fare, realtime semantics, GPS spatial integration, test coverage và UX/accessibility polish.

### Khuyến nghị delivery

Tạo **một Task remediation riêng** cho P0/P1 thay vì trộn vào Task 4. Scope remediation nên xử lý correctness/security trước, sau đó mới tiếp tục mở rộng planner capability.

---

## 17. Trạng Thái Audit

```text
Source code modified: NO
DEV delegated:       NO
Production changed:  NO
Audit report:        READY
```

Báo cáo này chỉ ghi nhận và cấu trúc lại kết quả audit. Chưa có implementation side effect nào được thực hiện.
