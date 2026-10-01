# Báo cáo Nghiệm thu Phát hành Cuối cùng & Cổng Production Roadmap V3

Task-ID: tsk_fa69d045-fc12-452b-9c82-8f4da320fafc

- Mã công việc: `tsk_fa69d045-fc12-452b-9c82-8f4da320fafc` (Task 011)
- Ngày thực hiện: 01/10/2026
- Vai trò triển khai: DEV
- Vai trò thẩm định kỹ thuật cuối: TL
- Đối tượng: PO, TL
- Môi trường mục tiêu: Production (`https://danabus.638686.xyz/`) & Local Workspace (`/home/opc/danabus`)
- Trạng thái nghiệm thu kỹ thuật: **PASS TOÀN BỘ (19/19 Suites - 100%)**

---

## 1. Tóm tắt Định danh Phát hành (Release Identity)

Bản phát hành Release Candidate v12 đã được đóng gói, triển khai theo quy trình staged atomic deploy lên Production và vượt qua toàn bộ ma trận kiểm thử nghiêm ngặt:

- **Phiên bản ứng dụng**: `v12`
- **Mã Build**: `20261001_v12`
- **Bộ nhớ đệm Service Worker**: `danabus-cache-v12`
- **Truy vấn tài nguyên tĩnh**: `?v=20261001_v12`
- **Public Root Production**: `/var/www/danabus/public`
- **Git Commit HEAD kỹ thuật đã review**: `8c4c7873cc74c4a8a0a638f2deed2d7dc27fd976` (trên nhánh `main`)
- **Chính sách Git Push**: `git_push_authorized=OFF` (ghi nhận tuân thủ chính sách, không push khi chưa có lệnh PO)

---

## 2. Ma trận Truy vết Nghiệm thu (Traceability Matrix)

Toàn bộ 19 bộ kiểm thử thuộc 4 tầng kiểm định (Layer 1, Layer 2, Layer 3, Layer 3B) đã được TL chạy lại và PASS trong tổng thời gian 75.30 giây:

| STT | Tên Bộ Kiểm Thử (Suite) | Tầng (Layer) | Thời Gian | Kết Quả |
| :--- | :--- | :--- | :---: | :---: |
| 1.1 | Temporal Route Service & Date Transitions | Layer 1 | 1.29s | **PASS** |
| 1.2 | Trip Planner Core & Inactive Rejection | Layer 1 | 3.84s | **PASS** |
| 1.3 | Search Correctness & Monotonic Ordering | Layer 1 | 0.20s | **PASS** |
| 1.4 | Schedule & Fare Truthful Semantics | Layer 1 | 0.27s | **PASS** |
| 1.5 | Data Quality Contract & Spatial Primitives | Layer 1 | 0.24s | **PASS** |
| 1.6 | Map, GPS & Unverified Geometry Isolation | Layer 1 | 0.06s | **PASS** |
| 1.7 | Consumer UX & Review Defects Regression | Layer 1 | 4.63s | **PASS** |
| 1.8 | Task 4 Boundary Guard & Prohibited SDKs | Layer 1 | 0.10s | **PASS** |
| 2.1 | Release Identity Consistency v12 | Layer 2 | 0.00s | **PASS** |
| 2.2 | Static Secret Audit & Negative Probe (94 tệp) | Layer 2 | 0.25s | **PASS** |
| 2.3 | Production Public TLS & Certificate Validation | Layer 2 | 0.16s | **PASS** |
| 2.4 | Production 3-Way Deliverables Hash Equivalence | Layer 2 | 1.94s | **PASS** |
| 3.1 | Browser Schedule & Fare Semantics | Layer 3 | 3.17s | **PASS** |
| 3.2 | Browser UI Integrity & Offline Recovery | Layer 3 | 3.39s | **PASS** |
| 3.3 | Browser Trip Planner E2E & Map Rendering | Layer 3 | 6.45s | **PASS** |
| 3.4 | Repeated Local Browser Smoke (3 vòng cô lập) | Layer 3 | 18.70s | **PASS** |
| 3.5 | Production Security Hardening | Layer 3B | 0.50s | **PASS** |
| 3.6 | Production PWA Runtime v12 (3 hồ sơ độc lập) | Layer 3B | 14.42s | **PASS** |
| 3.7 | Repeated Production Browser Smoke (3 vòng trực tiếp) | Layer 3B | 15.67s | **PASS** |

---

## 3. Chi tiết Kết quả Kiểm định

### 3.1. Tầng 1: Các Hợp đồng Logic Xác định (Layer 1 Deterministic Contracts)
- **Temporal Route Service**: Tuyến bus và chuyển tiếp lịch trình tuân thủ ràng buộc thời gian; chuyển đổi ngày và trạng thái hoạt động chính xác.
- **Trip Planner Core**: Thuật toán tìm đường trực tiếp, 1 điểm chuyển tuyến, 2 điểm chuyển tuyến hoạt động tối ưu; loại trừ triệt để các tuyến ngừng hoạt động (inactive/suspended routes); ngăn ngừa lặp tuyến (anti-loop).
- **Tính Đúng đắn Tìm kiếm**: Thứ tự trạm đơn điệu theo chiều đi, xử lý biên không có đường đi trực tiếp thì fail-closed minh bạch, không suy đoán dữ liệu giả.
- **Ngữ nghĩa Lịch trình & Giá vé**: Tần suất, giờ khởi hành kế tiếp và bảng giá vé đúng công bố; không gán bừa giờ chạy khi chưa có dữ liệu thời gian thực.
- **Chất lượng Dữ liệu & Bản đồ**: 247 trạm được kiểm chứng, 9 tuyến có hình học polyline đầy đủ, 14 tuyến chưa có hình học chính thức được cách ly an toàn với thông báo phủ (overlay notice) fail-closed.
- **Hồi quy UX Task 010**: Kiểm chứng 7/7 lỗi review trước đó đã được khắc phục triệt để.

### 3.2. Tầng 2: Tính Toàn vẹn Bản phát hành, Bảo mật & Băm Đối chiếu
- **Tính Nhất quán Phiên bản**: `sw.js` và `index.html` đồng bộ chính xác phiên bản `v12` và chuỗi build `20261001_v12`.
- **Rà soát Bí mật (Secret Audit) & Probe Âm tính**:
- Quét toàn bộ 94 tệp tin mã nguồn, cấu hình, dữ liệu và tài liệu. Phát hiện 0 vi phạm (Repository hoàn toàn sạch).
  - Negative probe kiểm thử với các khóa RSA, PKCS8, EC giả định đều bị chặn và che giấu (redacted) nhật ký đúng quy định.
- **Bảo mật TLS Production**:
  - Giao thức: `TLSv1.3`, Bộ mã hóa: `TLS_AES_256_GCM_SHA384`.
  - Chứng chỉ số hợp lệ cho `638686.xyz` và `*.638686.xyz`, hạn dùng đến ngày 06/12/2026.
  - Kiểm tra chứng chỉ nghiêm ngặt (`CERT_REQUIRED` và xác minh hostname).
- **Đối chiếu Băm 3 Chiều (3-Way Hash Equivalence)**:
  Tất cả 12 tệp tin xuất bản (whitelist deliverables) đều khớp 100% mã băm SHA-256 giữa Workspace, Thư mục Public Root (`/var/www/danabus/public`) và Tải trọng tải trực tiếp từ HTTPS (`https://danabus.638686.xyz/`):
  - `index.html`: `5b1a06dd3876...` (Khớp tuyệt đối)
  - `sw.js`: `eb8cb4b0a4bc...` (Khớp tuyệt đối)
  - `manifest.json`: `b84d2c6081e2...` (Khớp tuyệt đối)
  - `css/app.css`: `cd09232caaa3...` (Khớp tuyệt đối)
  - `js/app.js`: `1fc601c555cb...` (Khớp tuyệt đối)
  - `js/busService.js`: `7252b0fbc6c4...` (Khớp tuyệt đối)
  - `js/mapService.js`: `d9d834ffbacb...` (Khớp tuyệt đối)
  - `js/icons.js`: `ea0ade2904f0...` (Khớp tuyệt đối)
  - `data/danangbus_routes.json`: `4c8060f58bcf...` (Khớp tuyệt đối)
  - `data/danangbus_stops.json`: `501eb164922c...` (Khớp tuyệt đối)
  - `data/danangbus_streets.json`: `059724f605e2...` (Khớp tuyệt đối)
  - `data/danangbus_summary.json`: `e2ab84e925d5...` (Khớp tuyệt đối)

### 3.3. Tầng 3 & 3B: Tích hợp Trình duyệt, PWA Runtime & Smoke Production
- **Vòng đời PWA v12**:
  - Cài đặt mới trên profile sạch: Service Worker kích hoạt tức thì, chiếm quyền điều khiển (`controllerchange`), nạp sẵn bộ nhớ đệm `danabus-cache-v12`.
  - Nâng cấp nóng (warm migration): Toàn bộ bộ nhớ đệm cũ từ `v4` đến `v11` được dọn sạch hoàn toàn, chỉ giữ lại `danabus-cache-v12`.
  - Dự phòng ngoại tuyến (offline fallback): Ứng dụng hoạt động mượt mà khi ngắt mạng đối với app shell, styles, scripts và dữ liệu đã nạp sẵn.
- **Kiểm thử Trình duyệt Trực tiếp trên Production (3 Vòng Lặp lại)**:
  - Khởi tạo ứng dụng, đổi chiều tuyến bus (chiều đi/chiều về) giữ sạch ngữ cảnh bản đồ và marker.
  - Định vị GPS và xử lý từ chối quyền định vị fail-closed chuẩn xác.
  - Tìm kiếm đường đi đa chặng kết xuất bản đồ Leaflet trơn tru, hiển thị đầy đủ chi tiết chặng và thông báo chuyển tuyến.

---

## 4. Bằng chứng Kiểm thử (Evidence Paths)

Các tệp bằng chứng thực thi được lưu trữ độc lập dưới thư mục `docs/reports/evidence/task-011/`:

1. `docs/reports/evidence/task-011/production_browser_smoke_evidence.png`: Ảnh chụp màn hình kiểm thử khói 3 vòng trên production.
2. `docs/reports/evidence/task-011/production_pwa_v12_evidence.png`: Ảnh chụp màn hình kiểm thử vòng đời PWA v12 và tìm đường trực tiếp trên production.
3. `docs/reports/evidence/task-011/browser_trip_planner_evidence.png`: Ảnh chụp kết xuất bản đồ và chỉ dẫn tìm đường đa chặng.
4. `docs/reports/evidence/task-011/browser_schedule_fare_evidence.png`: Ảnh chụp giao diện lịch trình và giá vé chân thực.
5. `docs/reports/evidence/task-011/browser_ui_accessibility_evidence.png`: Ảnh chụp kiểm thử trợ năng và tính toàn vẹn giao diện.
6. `docs/reports/evidence/task-011/browser_smoke_evidence.png`: Ảnh chụp kiểm thử khói trình duyệt local.
7. `docs/reports/task-11-release-gate-summary.json`: Tệp tổng hợp kết quả chi tiết dạng JSON phục vụ máy đọc và đối chiếu tự động.

---

## 5. Giới hạn Nhận biết & Ranh giới Fail-Closed (Known Limitations)

1. **Dữ liệu Hình học Tuyến**: Có 14 tuyến bus hiện tại theo tài liệu PDF công bố chính thức chưa có hình học polyline chi tiết; hệ thống áp dụng cơ chế fail-closed hiển thị thông báo lớp phủ thay vì tự ý vẽ đường chim bay hoặc giả mạo tọa độ.
2. **Khóa API Google Places**: Khóa API máy khách được bảo vệ chặt chẽ bằng ràng buộc tên miền HTTP Referrer (`danabus.638686.xyz`), tuyệt đối không chứa secret phía máy chủ; khi API gặp sự cố, hệ thống tự động chuyển sang cơ chế tìm kiếm trạm nội bộ fail-closed.
3. **Phát hành Mã nguồn Từ xa**: Cấu hình `git_push_authorized=OFF` được duy trì theo đúng chính sách; commit được lưu cục bộ và sẵn sàng để PO kích hoạt lệnh đẩy lên remote repo qua `/push`.

---

## 6. Thẩm định độc lập của TL

Trong lượt review cuối, TL đã xác minh trực tiếp bản vá readiness và production gate thay vì chỉ dựa trên báo cáo DEV:

- `scripts/test_task10_review_fixes.py` được chạy 5 lượt liên tiếp: **5/5 PASS**, không tái hiện race `window.app.showTripResults`.
- `python scripts/test_release_gate_acceptance.py --repeat 3 --target-url https://danabus.638686.xyz/`: **19/19 suites PASS**, tổng thời gian 75.30 giây.
- Full gate xác nhận lại release identity `v12`, strict TLS, repository secret audit, 3-way hash equivalence, PWA fresh/warm/offline, local browser smoke 3 vòng và production browser smoke 3 vòng.
- `docs/reports/task-11-release-gate-summary.json` được tái tạo trong lượt review TL với `repeat_count=3` và trạng thái production `VERIFIED_PRODUCTION`.
- Không phát hiện defect kỹ thuật còn mở trong phạm vi Task 011.

## 7. Kết luận & Đề xuất

TL xác nhận Task 011 đạt **technical acceptance** theo scope đã duyệt. Release v12 đang hoạt động trên production với full gate PASS và các giới hạn dữ liệu còn lại đều giữ fail-closed. Task sẵn sàng chuyển PO xem xét nghiệm thu theo workflow; `git_push_authorized=OFF` vẫn được tuân thủ và không phải blocker kỹ thuật.
