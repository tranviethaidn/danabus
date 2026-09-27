# Plan Address-to-Address Trip Planner cho Danabus

Ngày: 2026-09-24  
Trạng thái: **APPROVED bởi PO để triển khai**. Dùng Task 4 hiện có; bắt đầu sau khi các dependency remediation về search, schedule/fare và data quality đạt acceptance.

## 1. Mục tiêu

Thay cơ chế chọn điểm đi/đến cố định theo bus stop bằng trải nghiệm:
- User nhập địa chỉ/POI cụ thể hoặc dùng GPS hiện tại.
- Hệ thống chuyển địa chỉ thành tọa độ.
- Tìm nhiều bus stop phù hợp quanh origin/destination.
- Tìm tuyến trực tiếp; sau đó mở rộng một lần chuyển tuyến.
- Xếp hạng hành trình theo walking + bus + transfer, không chỉ theo stop gần nhất.
- Hiển thị đầy đủ walking legs + transit legs trên map.

## 2. Quyết định nguồn map

Không cần thay Leaflet hiện tại bằng Google Maps chỉ để làm tính năng này.

Đề xuất tách provider theo chức năng:

1. **Basemap/rendering:** giữ Leaflet. Tile provider cấu hình riêng; OSM standard tile chỉ phù hợp theo policy/traffic, production nên dùng tile provider có SLA hoặc self-host phù hợp.
2. **Address/POI search + geocoding:** ưu tiên Google Places API (New) + Place Details/Geocoding nếu PO chấp nhận billing/API key. Google có dữ liệu địa chỉ/POI và autocomplete tốt, phù hợp UX nhập địa chỉ.
3. **Transit planner:** dùng dataset Danabus của project, không giao toàn bộ logic cho Google. Lý do: project cần kiểm soát route/stop/direction đã chuẩn hóa ở Task 2; realtime nếu có sau này là capability độc lập, không phải dependency của planner.
4. **Walking route:** abstraction WalkingRouter; có thể dùng Google Routes hoặc provider khác sau khi kiểm tra chi phí/license.
5. **Realtime bus:** ngoài MVP hiện tại. Task 3 đã CLOSED; nếu sau này cần realtime, mở scope/Task riêng với provider hợp lệ.

Không dùng public Nominatim của OSM làm production autocomplete: policy của public service cấm client-side autocomplete và giới hạn tải.

## 3. Kiến trúc

```text
User input / Current GPS
          |
          v
LocationSearchProvider
          |
          v
ResolvedLocation {label, lat, lng, providerId}
          |
          +---------------------+
          |                     |
          v                     v
Nearby origin stops      Nearby destination stops
          |                     |
          +----------+----------+
                     |
                     v
              TransitPlanner
                     |
             +-------+-------+
             |               |
          Direct          1 transfer
             |               |
             +-------+-------+
                     |
                     v
                 Ranker
                     |
                     v
                   Trip[]
                     |
            +--------+--------+
            |                 |
            v                 v
       WalkingRouter      Map Renderer
```

## 4. Provider abstraction

### LocationSearchProvider
- autocomplete(query, bias)
- resolve(providerPlaceId)
- reverseGeocode(lat,lng) nếu cần

Không để API key unrestricted trong frontend. Với web provider phải áp dụng restriction phù hợp; server-side API nên qua backend/proxy nếu provider khuyến nghị.

### WalkingRouter
- route(origin, destination)
- trả geometry, distance, duration

### RealtimeProvider
Không thuộc MVP Task 4 hiện tại. Task 3 đã CLOSED; nếu sau này mở realtime bằng Task/scope mới thì capability đó sở hữu:
- vehicle positions
- ETA/trip updates
- freshness

TransitPlanner chỉ consume normalized contract và không phụ thuộc realtime để hoạt động.

## 5. Search flow

### Origin
Cho phép:
- nhập địa chỉ
- nhập POI
- dùng Current Location

### Destination
Cho phép:
- nhập địa chỉ
- nhập POI

Autocomplete ưu tiên bias quanh Đà Nẵng/Hội An theo phạm vi service, nhưng không tự biến text chưa chọn thành tọa độ không chắc chắn.

Sau khi user chọn suggestion, lưu:
```text
ResolvedLocation
- displayName
- address
- lat
- lng
- provider
- providerId
```

## 6. Nearby stop search

Không chỉ chọn một stop gần nhất.

Với mỗi endpoint:
1. Query stop trong radius ban đầu, ví dụ 500–800m.
2. Nếu quá ít candidate có thể mở rộng có giới hạn.
3. Tính walking distance thực nếu WalkingRouter khả dụng; Haversine chỉ dùng pre-filter.
4. Giữ top N candidate hợp lý.

Candidate:
```text
StopCandidate
- stopId
- lat/lng
- straightDistance
- walkingDistance
- walkingDuration
- servedRoutes[]
```

## 7. Direct route

Một direct candidate hợp lệ khi:
- boarding và alighting stop cùng route;
- cùng direction;
- boarding.stopOrder < alighting.stopOrder theo direction;
- geometry/dataset hợp lệ;
- không dùng route fallback giả.

Cost ban đầu:
```text
originWalk
+ estimatedBusCost
+ destinationWalk
+ penalties
```

Không chọn chỉ theo stop gần nhất.

## 8. One-transfer route

Nếu không có direct route tốt:
- Route A từ origin candidate.
- Tìm transfer stop/cluster có Route B.
- Route B đi đến destination candidate.
- Kiểm tra direction/order của cả hai legs.
- Giới hạn walking transfer.
- Loại loop, quay đầu vô lý, route lặp và hành trình quá vòng.

Bản đầu chỉ hỗ trợ tối đa 1 transfer để kiểm soát complexity.

## 9. Ranking

Các thành phần:
- walking distance/time đầu hành trình;
- số lần transfer;
- transit distance/time;
- walking cuối hành trình;
- transfer walking;
- detour penalty;
- data confidence.

Khi sau này có realtime provider hợp lệ qua một Task/scope riêng:
- wait ETA;
- transfer wait ETA;
- vehicle freshness.

UI nên đưa vài phương án có ý nghĩa thay vì chỉ một “best route” không giải thích.

Ví dụ:
- Ít đi bộ nhất
- Ít chuyển tuyến
- Tổng thời gian thấp nhất (khi đủ dữ liệu)

## 10. Map rendering

Hiển thị các leg khác kiểu:
- walking origin -> boarding stop;
- bus geometry;
- transfer walking nếu có;
- bus leg 2 nếu có;
- walking alighting stop -> destination.

Markers:
- origin
- boarding
- transfer
- alighting
- destination

Không dùng straight line để giả walking route nếu UI gọi đó là “đường đi bộ thực tế”.

## 11. UX

Home:
```text
Điểm đi
[ Nhập địa chỉ hoặc địa điểm... ] [Vị trí hiện tại]

Điểm đến
[ Nhập địa chỉ hoặc địa điểm... ]

[Tìm chuyến]
```

Autocomplete phải debounce và dùng session token nếu provider hỗ trợ.

Trip result:
```text
123 Nguyễn Văn Linh
  ↓ đi bộ 4 phút / 280m
Trạm A
  ↓ Tuyến 05 · chiều ...
Trạm B
  ↓ đi bộ 3 phút / 190m
Bệnh viện C

Tổng: ...
Đi bộ: ...
Chuyển tuyến: 0
```

## 12. Google hay OSM?

### Google Places/Geocoding
Ưu:
- autocomplete địa chỉ/POI mạnh;
- Place ID;
- tọa độ và metadata có cấu trúc;
- production service/quota.

Nhược:
- cần billing/API key;
- chi phí theo usage;
- phải tuân thủ Google Maps Platform terms, storage/display restrictions và key security.

### Public Nominatim
Không chọn cho production autocomplete:
- public endpoint có giới hạn nghiêm ngặt;
- maximum 1 request/second;
- policy cấm autocomplete;
- không phù hợp app production có traffic.

Có thể self-host Nominatim hoặc mua OSM-based commercial geocoder nếu muốn stack mở.

### Kết luận provider
Cho MVP production có UX nhập địa chỉ tốt: **Google Places API (New) cho autocomplete + place resolution**, nhưng giữ **Leaflet + Danabus dataset + TransitPlanner riêng**. Không cần migrate toàn bộ map sang Google Maps.

Thiết kế provider abstraction để sau này đổi Google sang Map4D/OSM commercial provider mà không rewrite planner.

## 13. Backend/API đề xuất

Nếu project hiện là static PWA, cần cân nhắc một lightweight backend/proxy cho provider secrets, rate limit và cache.

Endpoints nội bộ gợi ý:
- GET /api/location/autocomplete?q=
- GET /api/location/resolve?id=
- POST /api/trips/plan
- POST /api/walking/route

Không log địa chỉ/GPS người dùng không cần thiết. Không cache dữ liệu cá nhân theo user nếu không có mục đích rõ.

## 14. Dependency với Task 2 và realtime tương lai

Task 2 phải cung cấp:
- stop lat/lng đáng tin cậy;
- route/direction geometry;
- stop order;
- no fake fallback.

Task 4 planner có thể bắt đầu sau khi contract Task 2 ổn định.

Realtime trong tương lai có thể bổ sung qua một Task/scope riêng:
- realtime vehicle;
- ETA;
- freshness.

Planner không được phụ thuộc realtime để hoạt động ở chế độ static; Task 3 hiện đã CLOSED.

## 15. Milestone triển khai

1. Provider contract + location search UI.
2. Address/POI resolution + Current Location.
3. Spatial stop index + nearby candidates.
4. Direct route planner.
5. Walking legs + map rendering.
6. One-transfer planner.
7. Ranking + result UX.
8. Automated tests + browser smoke.
9. Sau này, nếu PO mở scope mới: realtime/ETA integration với provider hợp lệ.

## 16. Test/acceptance

- Địa chỉ hợp lệ resolve đúng tọa độ.
- POI resolve được.
- Current Location dùng GPS thật.
- Không dùng một bus stop cố định.
- Nearby search xét nhiều candidate.
- Direct route đúng route/direction/stopOrder.
- Không đề xuất đi ngược chiều.
- Không đề xuất route không phục vụ destination.
- One-transfer không loop.
- Walking legs có distance/duration hợp lệ.
- Missing provider/API failure có UI error/fallback rõ.
- Switch origin/destination không giữ stale result.
- Dataset thiếu geometry không tạo fake route.
- Provider key không bị expose sai cách.
- Automated tests PASS.
- Browser smoke trên nhiều cặp địa chỉ Đà Nẵng PASS.

## 17. Không làm trong MVP

- Multi-transfer > 1.
- Realtime ETA trong MVP Task 4 hiện tại; Task 3 đã CLOSED.
- Machine-learning ranking.
- Tự thu thập/lưu lịch sử vị trí user.
- Reverse-engineer private mapping/transit APIs.

## 18. Điều kiện cần PO quyết định trước implementation

Nếu chọn Google Places/Geocoding production, cần Google Cloud project/API key + billing do PO/owner quản lý. Nếu chưa muốn phát sinh billing, implementation vẫn có thể xây provider interface/mock và chọn một OSM-based commercial/self-host provider sau, nhưng không dùng public Nominatim autocomplete như production dependency.
