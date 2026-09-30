# Báo cáo Nghiệm thu Kỹ thuật Task 009: Hoàn thiện Coverage Tuyến Active, GPS & Dữ liệu Lộ trình

## 1. Tổng quan & Mục tiêu

- **Task-ID**: `tsk_8ace3733-97c4-4e4e-8201-469cb6158a26`
- **Tiêu đề**: Active Route GPS, Stop & Shape Coverage Completion
- **Phạm vi thực hiện**:
  1. Điều tra và xử lý triệt để nguyên nhân gốc khiến tuyến `21` bị từ chối geometry do giá trị `distanceKm=10.0` bị phân tích sai từ khung giá vé (`+ Từ 10 km trở xuống: 8.000 đồng/hành khách/lượt`).
  2. Tái tạo lộ trình GPS/geometry xác thực cho tuyến `21` ở cả hai chiều đi và về (Outbound / Inbound) bằng các điểm dừng neo xác thực hiện hữu, tuân thủ nghiêm ngặt validator fail-closed.
  3. Tính toán lại toàn diện tỷ lệ phủ (coverage) trên mạng lưới tuyến đang hoạt động (active network) sau khi thực hiện đối chiếu theo thời gian (temporal reconciliation).
  4. Khảo sát khả năng mở rộng của tuyến `01SB` theo các mốc tọa độ thực tế và bằng chứng tin cậy.
  5. Xác lập và chứng minh trần dữ liệu (data ceiling) hiện hữu của hệ thống dữ liệu xe buýt chính thức, ghi nhận rõ ràng rào cản tính sẵn sàng dữ liệu (data availability blocker) đối với các chỉ tiêu ban đầu.

---

## 2. Nguyên nhân gốc & Giải pháp kỹ thuật cho Tuyến 21

### 2.1. Phân tích nguyên nhân gốc (Root Cause)
- **Hiện tượng**: Tuyến 21 (Bến xe Trung tâm Đà Nẵng – Cầu Tam Kỳ, cự ly thực tế ~78–80 km) có đầy đủ 89 điểm dừng chiều đi (45 mốc xác thực) và 80 điểm dừng chiều về (33 mốc xác thực). Khi OSRM sinh lộ trình chính xác đạt độ lệch dừng cực đại chỉ 34.8m (ngưỡng cho phép <= 350m), validator hình học (`validate_route_geometry`) vẫn đánh rớt cả hai chiều với lý do:
  - Outbound: `Total length 80.33km deviates from expected 10.0km`
  - Inbound: `Total length 78.71km deviates from expected 10.0km`
- **Nguyên nhân cốt lõi**: Bộ bóc tách dữ liệu văn bản ban đầu đọc nhầm dòng đầu tiên trong biểu giá chặng của tuyến 21 (`+ Từ 10 km trở xuống: 8.000 đồng/hành khách/lượt`) và gán nhầm giá trị số `10.0` vào trường metadata cự ly tuyến `distanceKm.average = 10.0`. Khi so sánh cự ly OSRM (~80km) với ngưỡng 10km (cho phép từ 6km đến 18km), hệ thống kích hoạt cơ chế fail-closed từ chối polyline.

### 2.2. Biện pháp khắc phục triệt để
1. **Chuẩn hóa parser & cấu hình nguồn**:
   - Bổ sung ghi đè chính thức trong `scripts/generate_all_danabus_data.py`: tuyến `21` có cự ly `distanceKm = {"average": None, "outbound": None, "inbound": None, "raw": ""}` khi chưa có văn bản công bố cự ly hành chính độc lập, đồng bộ với tiền lệ chuẩn của tuyến `02`.
   - Tuyệt đối không dùng chiều dài OSRM để gán ngược làm cự ly pháp lý chính thức.
2. **Cập nhật dataset chuẩn hóa**:
   - `data/danangbus_routes.json`: Đặt `distanceKm.average = null`, `outbound = null`, `inbound = null`, `raw = ""`.
   - `data/danangbus_routes_compact.json`: Đồng bộ `distanceKm = null`.
3. **Tái tạo và kiểm chứng Geometry**:
   - Chạy pipeline `scripts/build_gps_dataset.py`:
     - Chiều đi (`outbound`): **PASS** (45 anchors, 1.582 tọa độ polyline, cự ly 80.33km, khoảng cách trạm tối đa 34.8m <= 350m, độ tăng tiến đơn điệu 100%).
     - Chiều về (`inbound`): **PASS** (33 anchors, 1.580 tọa độ polyline, cự ly 78.71km, khoảng cách trạm tối đa 34.8m <= 350m, độ tăng tiến đơn điệu 100%).
     - Ghi nhận `provenance.source = "osm_osrm_verified"`, `verified = true`.
4. **Cập nhật hợp đồng chất lượng dữ liệu (`dataQuality`)**:
   - Tuyến 21 chuyển trạng thái: `tripPlanningReady = true`, cả hai chiều `eligibleForPlanning = true`, `geometryReady = true`, `stopsReady = true`.

---

## 3. Khảo sát Tuyến 01SB & Duy trì Fail-Closed

- Tuyến `01SB` (Cảng HKQT Đà Nẵng – Bến tàu Cửa Đại, Hội An):
  - Chiều đi (`outbound`): Chỉ có 4 điểm dừng theo công bố chính thức, trong đó chỉ có 3 mốc xác thực. Con số này không đạt yêu cầu tối thiểu 5 mốc xác thực (`anchors >= 5`) theo quy định của `validate_route_geometry`.
  - Chiều về (`inbound`): Có 7 điểm dừng, 5 mốc xác thực. Tuy nhiên, mốc Sân bay Đà Nẵng nằm lệch 380.2m so với polyline trục giao thông đường Nguyễn Văn Linh / Duy Tân (vượt ngưỡng sai số cho phép 350m).
- **Kết luận khảo sát**: Đúng theo chỉ đạo nghiệm thu của TL, không nới lỏng ngưỡng 350m và không bịa đặt thêm điểm dừng cho chiều đi. Tuyến `01SB` tiếp tục được duy trì trạng thái **fail-closed** an toàn (`geometry = null`, `eligibleForPlanning = false`).

---

## 4. Báo cáo Độ phủ Mạng lưới Active (Coverage Matrix)

Mẫu số release của Task 009 được xác định chuẩn xác sau đối chiếu thời gian (18 tuyến active, 36 chiều di chuyển):
- Tuyến active (18 tuyến): `05`, `07`, `08`, `11`, `12`, `02`, `03`, `06`, `09`, `13`, `14`, `21`, `TKY-TMY`, `TKY-NTH`, `TKY-CHU`, `LK01`, `01DL`, `01SB`.
- Tuyến sáp nhập (2 tuyến): `LK02` (sáp nhập vào `02`), `LK21` (sáp nhập vào `21`).
- Tuyến dừng hoạt động (3 tuyến): `04`, `10`, `15`.

### Bảng đối chiếu Before / After trên 36 chiều di chuyển active:

| Tiêu chí | Trước Task 009 (Baseline) | Sau Task 009 | Chênh lệch | Đạt chuẩn |
| :--- | :--- | :--- | :--- | :--- |
| **Chiều có Shape xác thực (Verified Shape)** | 10 / 36 (27.78%) | **12 / 36 (33.33%)** | +2 chiều (Tuyến 21 đi & về) | PASS |
| **Chiều có Điểm dừng xác thực (Verified Stop-Dir)** | 16 / 36 (44.44%) | **16 / 36 (44.44%)** | Giữ nguyên (Trạm 21 đã có từ baseline) | PASS |
| **Chiều sẵn sàng lập lộ trình (Planner-Ready)** | 10 / 36 (27.78%) | **12 / 36 (33.33%)** | +2 chiều (Tuyến 21 đi & về) | PASS |
| **Tuyến sẵn sàng lập lộ trình (tripPlanningReady)** | 5 / 18 (27.78%) | **6 / 18 (33.33%)** | +1 tuyến (Tuyến 21) | PASS |
| **Số trạm xác thực trên mạng active** | 274 / 470 trạm (58.30%) | **274 / 470 trạm (58.30%)** | Không fabricate trạm mới | PASS |
| **Số trạm xác thực toàn mạng (23 tuyến)** | 363 / 638 trạm (56.90%) | **363 / 638 trạm (56.90%)** | Bảo toàn tính toàn vẹn dữ liệu | PASS |

### Danh sách các tuyến và trạng thái chi tiết sau nghiệm thu:
1. `05` (Hòa Hiệp Nam – CV Biển Đông): **tripPlanningReady = true** (2 chiều đạt chuẩn).
2. `02` (Bến xe Trung tâm – ĐH Việt Hàn – Hội An): **tripPlanningReady = true** (2 chiều đạt chuẩn).
3. `21` (Bến xe Trung tâm – Cầu Tam Kỳ): **tripPlanningReady = true** (2 chiều đạt chuẩn MỚI).
4. `TKY-TMY` (Tam Kỳ – Trà My): **tripPlanningReady = true** (2 chiều đạt chuẩn).
5. `TKY-NTH` (Tam Kỳ – Hiệp Đức): **tripPlanningReady = true** (2 chiều đạt chuẩn).
6. `TKY-CHU` (Tam Kỳ – Sân bay Chu Lai): **tripPlanningReady = true** (2 chiều đạt chuẩn).
7. `01SB`, `01DL`: Điểm dừng hợp lệ nhưng hình học chưa đủ điều kiện -> fail-closed.
8. `07`, `08`, `11`, `12`, `03`, `06`, `09`, `13`, `14`, `LK01`: Chưa có bảng điểm dừng chính thức -> fail-closed.

---

## 5. Bằng chứng Rào cản Dữ liệu Khả dụng (Data Availability Blocker)

- **Mục tiêu đề ra ban đầu**: `>=90% active directions có verified shape` (cần >= 33/36 directions) và `>=85% active stop-direction` (cần >= 31/36 directions).
- **Thực tế dữ liệu nguồn**:
  - Cổng thông tin chính thức Datramac (`danangbus.vn/lo-trinh-tuyen.html`) chỉ cung cấp bảng danh mục điểm dừng dạng bảng HTML cho đúng **8 tuyến** trong số 18 tuyến active (`05`, `02`, `21`, `TKY-TMY`, `TKY-NTH`, `TKY-CHU`, `01SB`, `01DL`).
  - **10 tuyến active còn lại** (`07, 08, 11, 12, 03, 06, 09, 13, 14, LK01`) hoàn toàn không có danh sách điểm dừng tabular. Các tuyến này chỉ có lộ trình tên đường khái quát hoặc sơ đồ vector dạng hình vẽ không có tọa độ.
- **Trần giới hạn kỹ thuật (Data Ceiling)**:
  - Trần tối đa cho Verified Stop-Direction: **16 / 36 chiều (44.44%)**.
  - Trần tối đa cho Verified Shape: **12 / 36 chiều (33.33%)**.
- **Kết luận**:
  - Không thể đạt chỉ tiêu 90% shape và 85% stops nếu không tự ý bịa đặt dữ liệu (fabrication).
  - Tuân thủ nguyên tắc cốt lõi: **Bảo vệ tính trung thực và an toàn của Journey Planner**, giữ toàn bộ các khoảng trống chưa có bằng chứng ở trạng thái fail-closed. Sự thiếu hụt dữ liệu nguồn này được chính thức ghi nhận là **Data Availability Blocker**.

---

## 6. Kết quả Kiểm thử & Xác minh Toàn diện (Verification Results)

Toàn bộ các bộ kiểm thử tự động từ tầng đơn vị, tầng tích hợp không gian đến kiểm thử hồi quy hệ thống đều đạt tỷ lệ vượt qua tuyệt đối (100% PASS):

1. `python3 scripts/reconcile_official_routes.py --check`:
   - Kết quả: **PASS**. 100% (23/23) tuyến có nguồn gốc chứng minh rõ ràng. 0 evidence gap, zero drift.
2. `python3 scripts/validate_data_quality.py --check`:
   - Kết quả: **PASS**. 100% metadata `dataQuality` trong dataset khớp hoàn toàn với validator tất định. Zero drift.
3. `python3 scripts/validate_data_quality.py --coverage`:
   - Kết quả: **PASS**. Xuất báo cáo coverage máy đọc được ra `docs/reports/task-8-data-quality-coverage.json`. Tuyến `tripPlanningReady`: 6/23, trạm verified: 363/638.
4. `python3 scripts/test_data_quality_and_planner_readiness.py`:
   - Kết quả: **PASS** (14/14 tests trong 0.16s). Xác minh đầy đủ hợp đồng chất lượng dữ liệu, phát hiện can thiệp giả mạo, kiểm thử không gian Node.js.
5. `python3 scripts/test_map_and_gps.py`:
   - Kết quả: **PASS** (11/11 tests trong 0.02s). Xác minh hình học xác thực tuyến 05, 02, 21; cô lập các tuyến fail-closed; kiểm tra báo cáo giải quyết 421 trạm.
6. `python3 scripts/test_trip_planner.py`:
   - Kết quả: **PASS** (27/27 tests trong 3.53s). Kiểm thử đầy đủ thuật toán tìm kiếm đường đi đa chặng (direct, 1 chuyển tiếp, 2 chuyển tiếp), tích hợp mượt mà tuyến 21 trên trục Đà Nẵng – Tam Kỳ.
7. `python3 scripts/test_temporal_route_service.py`:
   - Kết quả: **PASS** (23/23 tests trong 1.21s). Xác minh mô hình dịch vụ tuyến theo thời gian.
8. `python3 scripts/test_task10_regression_acceptance.py`:
   - Kết quả: **PASS** (20/20 hạng mục ma trận truy xuất nguồn gốc, cả Layer A Deterministic và Layer B Production Browser Smoke trên môi trường thật).

---

## 7. Danh mục Tệp thay đổi

- `scripts/build_gps_dataset.py`: Sắp xếp danh sách đường chuẩn hóa đảm bảo tính tất định khi tạo dữ liệu.
- `scripts/generate_all_danabus_data.py`: Khai báo ghi đè `distanceKm = null` cho tuyến 21 trong cấu hình parser.
- `data/danangbus_routes.json`: Cập nhật `distanceKm` null, nạp 1.582 tọa độ polyline chiều đi và 1.580 tọa độ chiều về cho tuyến 21, cập nhật `dataQuality` sẵn sàng cho trip planning.
- `data/danangbus_routes_compact.json`: Đồng bộ metadata compact cho tuyến 21 (`distanceKm = null`, `hasGeometry.outbound = true`, `hasGeometry.inbound = true`).
- `data/danangbus_resolution_report.json`: Ghi nhận kết quả xác thực geometry PASS cho tuyến 21.
- `docs/reports/task-8-data-quality-coverage.json`: Cập nhật báo cáo độ phủ máy đọc được (6 tuyến sẵn sàng lập kế hoạch, 18 tuyến active).
- `scripts/test_data_quality_and_planner_readiness.py`: Cập nhật bộ kiểm thử hợp đồng dữ liệu cho tuyến 21 và kiểm tra fail-closed cho tuyến 01SB.
- `scripts/test_map_and_gps.py`: Cập nhật assertion xác minh hình học tuyến 21.
- `scripts/test_trip_planner.py`: Điều chỉnh điểm đón thử nghiệm chuyển tiếp tại Tam Kỳ tránh trùng lặp tuyến trực tiếp của tuyến 21.
