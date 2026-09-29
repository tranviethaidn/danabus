# Task 8 - Data Quality Contract & Planner Readiness

## Mục tiêu

Biến data debt hiện tại thành contract có thể kiểm tra tự động để Task 4 chỉ consume route/stop đủ tin cậy, fail-closed khi dữ liệu thiếu hoặc chưa xác minh.

## Baseline đã quan sát

- Approved roadmap yêu cầu `dataQuality.hasOutboundStops`, `hasInboundStops`, `hasOutboundGeometry`, `hasInboundGeometry`, `hasFareModel`, `tripPlanningReady`.
- `data/schema.ts` chưa có `DataQuality` contract.
- `danangbus_routes.json` đã có stop status/confidence và geometry provenance `verified` từ GPS pipeline.
- `BusService` chưa có spatial nearby-stop primitive.
- GPS pipeline đã có nguyên tắc fail-closed: geometry invalid/không đủ verified anchors thì để `null` và `verified=false`.
- Task 7 đang có thay đổi chưa commit trong worktree; Task 8 không được sửa chen scope schedule/fare của Task 7.

## Thiết kế đã chốt sau TL -> DEV -> TL

### 1. Route data-quality metadata

Mỗi route có `dataQuality` được sinh bằng validator deterministic, không hard-code theo route id:

```text
hasOutboundStops
hasInboundStops
hasOutboundGeometry
hasInboundGeometry
hasFareModel
tripPlanningReady
```

Bổ sung direction-level readiness để Task 4 có thể consume đúng hướng mà không hạ thấp route-level contract:

```text
directions.outbound.stopsReady
directions.outbound.geometryReady
directions.outbound.eligibleForPlanning
directions.inbound.stopsReady
directions.inbound.geometryReady
directions.inbound.eligibleForPlanning
```

Bổ sung `stopMetrics` cho mỗi direction để phản ánh data debt thay vì che giấu unresolved stops.

Quy tắc fail-closed đã chốt:

- `hasOutboundStops` / `hasInboundStops` dùng verified subset: direction phải có ít nhất 2 stop `status=verified`, tọa độ finite và order tăng nghiêm ngặt.
- Planner và nearby-stop candidate chỉ được snap vào stop `verified`; stop `unresolved` tuyệt đối không được dùng làm điểm đón/trả.
- `has*Geometry=true` chỉ khi geometry tồn tại và provenance direction tương ứng `verified=true`.
- `hasFareModel=true` chỉ khi fare có `type` canonical và đủ thông tin cần thiết cho type đó; `unknown` hoặc dữ liệu mâu thuẫn thì false.
- `directions[dir].eligibleForPlanning=true` chỉ khi route `active`, direction đó có stopsReady + geometryReady và route có fare model hợp lệ.
- `tripPlanningReady=true` chỉ khi route `active`, cả hai direction eligible và `hasFareModel=true`. Không suy diễn từ text/raw fallback.

### 2. Validator và coverage report

- Enrich trực tiếp `dataQuality` vào `data/danangbus_routes.json` để giữ file này là single source of truth cho runtime.
- Thêm `scripts/validate_data_quality.py` với logic deterministic dùng chung cho enrich/check.
- Chế độ check phải tính lại contract và fail exit code khác 0 nếu metadata trong dataset bị drift.
- Chế độ enrich cập nhật lại `dataQuality` từ dữ liệu gốc, không fabricate stop/geometry/fare để tăng coverage.
- Sinh coverage machine-readable tại `docs/reports/task-8-data-quality-coverage.json` từ cùng logic validator.
- Coverage phải theo route/direction và chứa stop readiness, geometry readiness, fare readiness, planner eligibility và lý do fail.

### 3. Nearby-stop foundation

Giữ spatial primitive trong `js/busService.js` để phù hợp kiến trúc vanilla hiện tại, nhưng triển khai dưới dạng pure functions exportable:

- `haversineDistance(lat1, lon1, lat2, lon2)` trả khoảng cách mét.
- `findNearbyStops(stops, lat, lng, options)` chỉ nhận stop `verified` có tọa độ finite, lọc theo `maxDistanceMeters`, sort tăng dần và giới hạn `limit`.
- `BusService.findNearbyStops(lat, lng, options)` chỉ là instance wrapper gọi pure function trên `this.stops`.
- Node export gồm `BusService`, `findNearbyStops`, `haversineDistance` để test độc lập.
- Kết quả candidate chỉ là nearby stop foundation; không tạo `Trip[]`, không transfer routing, không address/POI resolution.

## Phân tách scope

Trong Task 8:

- Schema/dataQuality contract, direction readiness và stop metrics.
- Enrich + validator chống drift + reproducible coverage.
- Fail-closed route/direction eligibility.
- Nearby-stop spatial primitive/candidate query.
- Unit/regression tests trực tiếp cho các contract trên.

Ngoài Task 8:

- UI wording/accessibility/voice/reminder: Task 9.
- Full cross-feature production regression matrix: Task 10.
- Address/POI geocoding, walking legs, direct/1-transfer planner, ranking/map trip rendering: Task 4.

## Verification yêu cầu

- Validator PASS trên dataset hiện tại và coverage đúng tổng 23 route.
- Negative cases: unresolved stop, thiếu verified stop tối thiểu, missing direction, invalid/unverified geometry, suspended route, unknown/invalid fare đều fail-closed.
- Nearby-stop query không trả stop unresolved/null coordinate; khoảng cách/sort/radius/limit đúng.
- Metadata drift phải làm validator fail.
- Các suite Task 5/6/7 liên quan không bị regression.
- Không sửa unrelated UI và không triển khai planner Task 4 sớm.

## Kết luận discussion

TL chấp thuận 4 đề xuất kỹ thuật của DEV: verified subset >= 2 stop cho direction readiness; bổ sung direction-level eligibility; enrich trực tiếp `danangbus_routes.json` kèm validator chống drift; đặt spatial primitive trong `BusService` dưới dạng pure functions exportable. Discussion round hoàn tất và đủ điều kiện chuyển sang implementation.
