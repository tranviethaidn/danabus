# Báo cáo nghiệm thu Task 008 - Multi-Transfer Transit Graph Planner

Task-ID: tsk_7c3ac549-f57e-4c72-9667-a10fead0a526

## Phạm vi

Task 008 nâng planner từ direct + tối đa 1 transfer thành graph planner hỗ trợ:

- direct;
- 1 transfer;
- tối đa 2 transfers mặc định;
- node theo route + direction + stop index;
- transfer walk có giới hạn;
- minimum transfer buffer;
- chống loop, route reuse và backtrack;
- loại route/direction không đủ điều kiện;
- fail-closed với transfer stop chưa verified;
- ranking deterministic;
- giữ tương thích output `walking`/`transit` cho UI và map.

## Bằng chứng triển khai

Các commit local của Task 008:

- `83ed60c feat(planner): implement multi-transfer transit graph planner and regression tests (Task 008)`
- `6e30ee7 fix(planner): enforce verified status on transfer stops fail-closed (Task 008)`

Các thay đổi chính:

- `js/busService.js`: bổ sung `TransitGraphRouter`, bounded layered search direct -> 1 -> 2 transfers, transfer index, lazy geometry materialization, transfer buffer 5 phút/lần chuyển tuyến và fail-closed.
- `js/app.js`: hiển thị đúng số lần chuyển tuyến thay vì hard-code 1 transfer.
- `scripts/test_trip_planner.py`: mở rộng regression cho 2-transfer, anti-loop, unready/inactive route, unresolved/non-verified transfer stop, deterministic ranking và performance.

TL đã review trực tiếp diff fix `83ed60c..6e30ee7`. Defect review trước đó đã được sửa bằng `_isStopVerified(stop)`, bắt buộc `status === 'verified'` cùng tọa độ hữu hạn hợp lệ ở transfer index và search pipeline.

## Kiểm tra và kết quả

### Planner regression

`python3 scripts/test_trip_planner.py`

Kết quả: **27/27 PASS**.

Bao gồm regression mới xác minh stop có tọa độ nhưng `status: 'needs_review'` không thể làm transfer stop.

### Reproducer defect fail-closed

TL chạy lại fixture đã từng tái hiện defect:

- transfer stop có numeric `lat/lng`;
- `status: 'needs_review'`;
- route/direction được mock usable/planning-ready để cô lập hành vi.

Kết quả sau fix:

- `count: 0`
- `error: NO_VIABLE_ROUTE`

Kết luận: fail-closed đúng yêu cầu.

### Dataset thật - 2 transfers

TL xác minh trực tiếp trên `data/danangbus_routes.json` và `data/danangbus_stops.json` với hai endpoint verified:

- Origin: `VNPT Quảng Nam`
- Destination: `531 Phan Châu Trinh`

Graph router tìm được hành trình 2-transfer:

- `02 (Quảng Nam) -> 05 (Quảng Nam) -> 12 (Quảng Nam)`
- `transfers: 2`
- `legs: 7`
- transfer walking: `0m`, `51m`
- transfer buffer: `10 phút`
- elapsed search sau index: **32.204 ms**

Kết quả đạt mục tiêu compute local <250 ms.

Lưu ý: public `planTrip()` có thể ưu tiên direct hoặc ít-transfer hơn nếu candidate radius tìm được phương án tốt hơn. Đây là đúng ranking contract, không phải lỗi.

### Regression liên quan

- `python3 scripts/test_temporal_route_service.py`: **23/23 PASS**
- `python3 scripts/test_data_quality_and_planner_readiness.py`: **14/14 PASS**
- `python3 scripts/test_schedule_and_fare.py`: **9/9 PASS**
- `python3 scripts/test_search_correctness.py`: **10/10 PASS**
- `python3 scripts/test_task10_regression_acceptance.py`: **20/20 PASS**

Full production/browser regression không phát hiện regression mới.

## Kết quả review

**PASS technical acceptance.**

Các tiêu chí chính đã đạt:

- direct, 1-transfer và 2-transfer được hỗ trợ;
- 2-transfer có 7 legs đúng contract;
- route reuse/loop/backtrack bị chặn;
- route/direction không usable hoặc không planning-ready bị loại;
- transfer stop unresolved hoặc non-verified bị fail-closed;
- ranking deterministic;
- UI không còn hard-code mọi connecting trip thành 1 transfer;
- performance dưới ngưỡng 250 ms;
- regression hiện hữu vẫn PASS.

## Giới hạn đã biết

- Planner vẫn phụ thuộc dữ liệu verified/planner-ready hiện có; direction hoặc stop chưa đủ độ tin cậy tiếp tục fail-closed.
- Transfer buffer 5 phút/lần chỉ là planning buffer, không phải realtime waiting prediction.
- Production hiện có thể chưa phản ánh commit local Task 008 cho đến khi PO cho phép publication.
- `git_push_authorized=OFF` trong runtime hiện tại; không push remote và đây không phải acceptance blocker.

## Trạng thái cuối

Task 008 đủ điều kiện chuyển PO review/acceptance.
