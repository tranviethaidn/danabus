# Báo cáo Nghiệm thu Kỹ thuật Task 009: Hoàn thiện Coverage Tuyến Active, GPS & Dữ liệu Lộ trình

Task-ID: tsk_8ace3733-97c4-4e4e-8201-469cb6158a26

## 1. Tổng quan & Mục tiêu

- **Tiêu đề**: Active Route GPS, Stop & Shape Coverage Completion
- **Phạm vi thực hiện**:
  1. Điều tra và xử lý triệt để nguyên nhân gốc khiến tuyến `21` bị từ chối geometry do giá trị `distanceKm=10.0` bị phân tích sai từ khung giá vé (`+ Từ 10 km trở xuống: 8.000 đồng/hành khách/lượt`).
  2. Tái tạo lộ trình GPS/geometry xác thực cho tuyến `21` ở cả hai chiều đi và về (Outbound / Inbound) bằng các điểm dừng neo xác thực hiện hữu, tuân thủ nghiêm ngặt validator fail-closed.
  3. Tính toán lại toàn diện tỷ lệ phủ (coverage) trên mạng lưới tuyến đang hoạt động (active network) sau khi thực hiện đối chiếu theo thời gian (temporal reconciliation).
  4. Khảo sát khả năng mở rộng của tuyến `01SB` theo các mốc tọa độ thực tế và bằng chứng tin cậy.
  5. Khai thác kiệt cùng (exhaust) toàn bộ 6 tệp PDF sơ đồ hình xương cá chính thức (`07`, `08`, `11`, `12`, `09`, `13`) và chứng minh trần dữ liệu (data ceiling) bằng bằng chứng kỹ thuật cụ thể.
  6. Phân định minh bạch kết quả nghiệm thu giữa Implementation Slice (PASS) và Release Targets (NOT MET / BLOCKED do rào cản dữ liệu nguồn).

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

### Bảng đối chiếu Phân định Implementation Slice vs Release Target:

| Tiêu chí | Baseline | Hiện tại (Task 009) | Thay đổi | Implementation Slice | Release Target (Chỉ tiêu) | Trạng thái Release Target |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Verified Shape** | 10 / 36 (27.78%) | **12 / 36 (33.33%)** | +2 chiều (Tuyến 21 đi & về) | **PASS** | >= 33 / 36 (90.0%) | **NOT MET / BLOCKED** |
| **Verified Stop-Direction** | 16 / 36 (44.44%) | **16 / 36 (44.44%)** | 0 (Trạm 21 đã có từ baseline) | **PASS** | >= 31 / 36 (85.0%) | **NOT MET / BLOCKED** |
| **Planner-Ready (eligibleForPlanning)** | 10 / 36 (27.78%) | **12 / 36 (33.33%)** | +2 chiều (Tuyến 21 đi & về) | **PASS** | >= 31 / 36 (85.0%) | **NOT MET / BLOCKED** |
| **Tuyến tripPlanningReady** | 5 / 18 (27.78%) | **6 / 18 (33.33%)** | +1 tuyến (Tuyến 21) | **PASS** | 100% active routes | **NOT MET / BLOCKED** |
| **Trạm verified trên mạng active** | 274 / 470 (58.30%) | **274 / 470 (58.30%)** | 0 (Không fabricate trạm mới) | **PASS** | Bảo toàn tính toàn vẹn | **PASS** |
| **Trạm verified toàn mạng (23 tuyến)** | 363 / 638 (56.90%) | **363 / 638 (56.90%)** | 0 (Bảo toàn dữ liệu kiểm toán) | **PASS** | Bảo toàn tính toàn vẹn | **PASS** |

### Danh sách các tuyến và trạng thái chi tiết sau nghiệm thu:
1. `05` (Hòa Hiệp Nam – CV Biển Đông): **tripPlanningReady = true** (2 chiều đạt chuẩn).
2. `02` (Bến xe Trung tâm – ĐH Việt Hàn – Hội An): **tripPlanningReady = true** (2 chiều đạt chuẩn).
3. `21` (Bến xe Trung tâm – Cầu Tam Kỳ): **tripPlanningReady = true** (2 chiều đạt chuẩn MỚI).
4. `TKY-TMY` (Tam Kỳ – Trà My): **tripPlanningReady = true** (2 chiều đạt chuẩn).
5. `TKY-NTH` (Tam Kỳ – Hiệp Đức): **tripPlanningReady = true** (2 chiều đạt chuẩn).
6. `TKY-CHU` (Tam Kỳ – Sân bay Chu Lai): **tripPlanningReady = true** (2 chiều đạt chuẩn).
7. `01SB`, `01DL`: Điểm dừng hợp lệ nhưng hình học chưa đủ điều kiện -> fail-closed.
8. `07`, `08`, `11`, `12`, `03`, `06`, `09`, `13`, `14`, `LK01`: Chưa đủ điều kiện dữ liệu an toàn để đưa vào Journey Planner -> duy trì fail-closed.

---

## 5. Bằng chứng Kỹ thuật Khai thác Kiệt cùng Dữ liệu PDF & Trần Dữ liệu (Data Ceiling)

Thực hiện chỉ đạo của TL tại Turn 005 và Turn 006, DEV đã xây dựng công cụ kiểm chứng tự động `scripts/exhaust_official_pdf_evidence.py` và xuất báo cáo máy đọc được `docs/reports/task-009-pdf-evidence-exhaustion-report.json`. Toàn bộ 6 tệp PDF sơ đồ hình xương cá chính thức đã được phân tích bóc tách và đối chiếu toàn diện:

### 5.1. Kết quả Bóc tách và Thẩm định Kỹ thuật từng Tuyến

1. **Tuyến 08 (BXB Bùi Dương Lịch >> BXB Phạm Hùng - `08.pdf`)**:
   - Bóc tách được: 30 trạm chiều đi, 31 trạm chiều về.
   - Đối chiếu OSM cache (`data/osm_cache/transit.json`):
     - Chiều đi: 17 trạm verified, 13 trạm unresolved (tỷ lệ thiếu **43.3%**).
     - Chiều về: 17 trạm verified, 14 trạm unresolved (tỷ lệ thiếu **45.2%**).
   - Kiểm chứng OSRM: Hình học qua 17 mốc xác thực PASS validator (max stop dist: 12.2m đi, 8.9m về).
   - **Rào cản kỹ thuật cốt lõi chặn promote**:
     - Cả hai trạm đầu cuối là *Bến xe buýt Bùi Dương Lịch* và *Bến xe buýt Phạm Hùng* hoàn toàn không có tọa độ trong OSM cache.
     - Các điểm dừng trung chuyển quan trọng (*Trung tâm Y tế Sơn Trà*, *Ban Tang Lễ*, *Dệt may Hòa Thọ*, *THPT Hòa Vang*, *Tổng Công ty EVNGENCO2*) không có tọa độ kiểm toán.
     - Vi phạm trực tiếp tiêu chí bắt buộc của Journey Planner: **"Không có unresolved boarding/alighting stop"**.

2. **Tuyến 11 (BXB Xuân Diệu >> BV Phụ Sản Nhi - `11.pdf`)**:
   - Bóc tách được: 28 trạm chiều đi, 29 trạm chiều về.
   - Đối chiếu OSM cache:
     - Chiều đi: 19 trạm verified, 9 trạm unresolved (tỷ lệ thiếu **32.1%**).
     - Chiều về: 22 trạm verified, 7 trạm unresolved (tỷ lệ thiếu **24.1%**).
   - Kiểm chứng OSRM: Hình học qua các mốc xác thực PASS validator (12.95km đi, 13.90km về, max stop dist: 136.7m <= 350m).
   - **Rào cản kỹ thuật cốt lõi chặn promote**:
     - Bến đầu tuyến *Bến xe buýt Xuân Diệu* không có tọa độ trong dữ liệu kiểm toán.
     - Các trạm *Chân Cầu Tiên Sơn*, *Lotte*, *Số 06-08 Ông Ích Khiêm* không có tọa độ.
     - Vi phạm tiêu chí không có unresolved stop tại bến đầu tuyến; đồng thời production runtime test suite (`scripts/browser_smoke_test.py`) có kiểm thử hồi quy kiểm tra overlay fail-closed cho Tuyến 11 khi chưa phát hành chính thức.

3. **Tuyến 07 (BX Xuân Diệu >> BX Phía Nam - `07.pdf`)**:
   - Bóc tách được: 34 trạm chiều đi, 34 trạm chiều về.
   - Đối chiếu OSM cache:
     - Chiều đi: 21 trạm verified, 13 trạm unresolved (tỷ lệ thiếu **38.2%**).
     - Chiều về: 22 trạm verified, 12 trạm unresolved (tỷ lệ thiếu **35.3%**).
   - Kiểm chứng OSRM: Hình học qua các mốc xác thực PASS validator (17.27km đi, 18.30km về, max stop dist: 12.3m).
   - **Rào cản kỹ thuật cốt lõi chặn promote**:
     - Bến xuất phát *Bến xe buýt Xuân Diệu* không có tọa độ xác thực.
     - Sơ đồ xương cá của tuyến 07 tách nhánh song song (chiều đi qua Trần Phú - Lê Lợi - Phan Châu Trinh, chiều về qua Bạch Đằng - Quang Trung - Nguyễn Chí Thanh). Phần lớn điểm dừng chỉ ghi số nhà đơn lẻ (như "Số 49", "Số 06", "Số 128", "Số 154", "Số 92"), không có tên đường đi kèm trên nhãn text, chỉ dựa vào màu nền trục xương cá đồ họa. Việc gán tọa độ tự động cho các số nhà này có độ rủi ro nhầm lẫn cao giữa các tuyến đường lân cận trong lõi đô thị.

4. **Tuyến 12 (BXB Xuân Diệu >> BXB Phạm Hùng - `12.pdf`)**:
   - Bóc tách được: 29 trạm chiều đi (17 verified), 25 trạm chiều về (15 verified).
   - **Rào cản kỹ thuật không thể vượt qua**:
     - Kiểm chứng hình học thất bại ở cả hai chiều: `Stop 'Sân bay Đà Nẵng' is too far from polyline (380.2m > 350m)`.
     - Lý do: Mốc xác thực nhà ga hành khách Sân bay Đà Nẵng (OSM way 344018314) nằm sâu trong sân đỗ nội bộ, cách trục đường giao thông chính Nguyễn Tri Phương / Duy Tân 380.2m, vượt quá ngưỡng dung sai 350m của validator.
     - Theo chỉ đạo của TL: *Tuyệt đối không nới lỏng ngưỡng 350m*. Do đó Tuyến 12 bắt buộc phải giữ **fail-closed** về mặt hình học (`geometry = null`).
     - Ngoài ra, bến *Bến xe buýt Xuân Diệu* cũng thiếu tọa độ kiểm toán.

5. **Tuyến 09 (Cảng Sông Hàn >> Hòa Khương - `09.pdf` số hiệu 17 cũ)**:
   - Bóc tách được: 30 trạm chiều đi từ sơ đồ số hiệu 17 cũ.
   - Đối chiếu OSM cache: Chỉ có 11 trạm verified, có tới 19 trạm unresolved (tỷ lệ thiếu lên tới **63.3%**).
   - Kiểm chứng hình học thất bại: Cự ly OSRM chỉ đạt 12.92km, lệch xa so với cự ly thực tế công bố 25.8km (`Total length 12.92km deviates from expected 25.8km`). Toàn bộ đoạn ngoại thành phía nam dọc QL14B đi Hòa Khương hoàn toàn không có mốc dừng nào trong OSM cache.

6. **Tuyến 13 (Kim Liên >> ĐH Việt Hàn - `13.pdf` số hiệu 16 cũ)**:
   - Sơ đồ dạng gấp khúc chữ S phức tạp với nhiều điểm chuyển trục không liên tục.
   - Chỉ có 4 mốc xác thực (< 5 mốc tối thiểu), không đủ điều kiện kỹ thuật để sinh lộ trình OSRM.

7. **Các tuyến hoàn toàn thiếu dữ liệu nguồn (`03`, `06`, `14`, `LK01`)**:
   - Cổng thông tin chính thức của Datramac và Sở GTVT hoàn toàn không công bố sơ đồ trạm PDF cũng như danh mục điểm dừng dạng bảng. Đây là khoảng trống dữ liệu nguồn tuyệt đối từ cơ quan quản lý.

### 5.2. Kết luận Xác lập Trần Dữ liệu (Data Ceiling) & Rào cản Dữ liệu Khả dụng

- **Trần dữ liệu hình học (Verified Shape Ceiling)**: Tối đa **12 / 36 chiều (33.33%)**.
- **Trần dữ liệu điểm dừng (Verified Stop-Direction Ceiling)**: Tối đa **16 / 36 chiều (44.44%)**.
- **Kết luận nghiệm thu**:
  - Không thể đạt release targets `>=90% verified shape` (>=33/36) và `>=85% verified stop-direction` (>=31/36) trên dữ liệu chính thức hiện hữu mà không vi phạm nguyên tắc cốt lõi: *Cấm bịa đặt tọa độ (fabrication)*, *Cấm hạ ngưỡng validator*, và *Cấm đưa các trạm thiếu tọa độ vào hành trình Journey Planner*.
  - Khoảng cách giữa trần dữ liệu (33.33% / 44.44%) và chỉ tiêu release (90% / 85%) là do **nguồn dữ liệu chính thức chưa đầy đủ**, không phải do hạn chế của pipeline kỹ thuật.
  - Tình trạng này được xác nhận chính thức là **Data Availability Blocker** (Rào cản Khả dụng Dữ liệu) của Task 009, trình TL và PO xem xét phê duyệt phụ thuộc dữ liệu hoặc điều chỉnh phạm vi release cho các giai đoạn tiếp theo.

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
9. `python3 scripts/exhaust_official_pdf_evidence.py`:
   - Kết quả: **PASS**. Xuất báo cáo kiểm chứng toàn bộ 6 PDF xương cá ra `docs/reports/task-009-pdf-evidence-exhaustion-report.json`.

---

## 7. Danh mục Tệp thay đổi

- `scripts/build_gps_dataset.py`: Sắp xếp danh sách đường chuẩn hóa đảm bảo tính tất định khi tạo dữ liệu.
- `scripts/generate_all_danabus_data.py`: Khai báo ghi đè `distanceKm = null` cho tuyến 21 trong cấu hình parser.
- `data/danangbus_routes.json`: Cập nhật `distanceKm` null, nạp 1.582 tọa độ polyline chiều đi và 1.580 tọa độ chiều về cho tuyến 21, cập nhật `dataQuality` sẵn sàng cho trip planning.
- `data/danangbus_routes_compact.json`: Đồng bộ metadata compact cho tuyến 21 (`distanceKm = null`, `hasGeometry.outbound = true`, `hasGeometry.inbound = true`).
- `data/danangbus_resolution_report.json`: Ghi nhận kết quả xác thực geometry PASS cho tuyến 21.
- `docs/reports/task-8-data-quality-coverage.json`: Cập nhật báo cáo độ phủ máy đọc được (6 tuyến sẵn sàng lập kế hoạch, 18 tuyến active).
- `scripts/exhaust_official_pdf_evidence.py`: Công cụ tự động khai thác và kiểm chứng bằng chứng kỹ thuật từ 6 tệp PDF xương cá chính thức.
- `docs/reports/task-009-pdf-evidence-exhaustion-report.json`: Báo cáo máy đọc được chi tiết tỷ lệ trạm thiếu, rào cản trạm đầu cuối và lỗi thẩm định hình học của từng tuyến PDF.
- `docs/reports/2026-09-30-task-009-active-route-coverage-completion-report.md`: Báo cáo nghiệm thu hoàn thiện, sửa exact `Task-ID:`, phân định minh bạch Implementation Slice PASS và Release Targets NOT MET / BLOCKED.
- `scripts/test_data_quality_and_planner_readiness.py`: Cập nhật bộ kiểm thử hợp đồng dữ liệu cho tuyến 21 và kiểm tra fail-closed cho tuyến 01SB.
- `scripts/test_map_and_gps.py`: Cập nhật assertion xác minh hình học tuyến 21.
- `scripts/test_trip_planner.py`: Điều chỉnh điểm đón thử nghiệm chuyển tiếp tại Tam Kỳ tránh trùng lặp tuyến trực tiếp của tuyến 21.
