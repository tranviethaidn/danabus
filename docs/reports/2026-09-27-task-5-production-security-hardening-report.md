# Báo Cáo Triển Khai & Kiểm Chứng Task 5: Production Security Hardening

- **Dự án**: Danabus PWA (`danabus.638686.xyz`)
- **Task ID**: `tsk_01416cc8-0c2d-49c8-a8fc-6552743c741a` (Sequence 5, P0)
- **Người thực hiện**: Developer (DEV)
- **Người bàn giao / Nghiệm thu**: Tech Lead (TL)
- **Thời gian hoàn tất**: 2026-09-27 07:56:00 +07:00
- **Trạng thái**: **HOÀN THÀNH - TOÀN BỘ KIỂM THỬ ĐẠT 100% (PASS)**

---

## 1. Mục Tiêu & Phạm Vi Triển Khai

Khắc phục triệt để lỗ hổng nghiêm trọng (P0) đã được phát hiện trong đợt full audit ngày 2026-09-27:
1. **Khóa Public Exposure của Workspace**: Tách rời hoàn toàn web root production khỏi workspace phát triển `/home/opc/danabus`.
2. **Whitelist Deployment**: Chỉ đưa các artifact PWA cần thiết ra production public root `/var/www/danabus/public`.
3. **Áp dụng Nguyên Tắc Least Privilege**: Loại bỏ hoàn toàn quyền đọc/duyệt của người dùng khác (`others`) trên workspace.
4. **Phòng Thủ Chiều Sâu (Defense-in-depth)**: Cấu hình Nginx chặn đứng dotfiles (`.git`), thư mục nội bộ (`docs/`, `scripts/`, `stitch_bus_route_finder_pwa/`, `osm_cache/`) và các file mã nguồn/cấu hình/tài liệu (`.md`, `.txt`, `.sh`, `.py`, `.conf`, `.ts`, `.bak`, `.log`).
5. **Khắc phục SPA Fallback Che Giấu Lỗi**: Các request static assets và data JSON không tồn tại phải fail-closed với HTTP `404 Not Found`, không được fallback trả về `index.html`.
6. **Bảo Toàn Khả Năng Vận Hành PWA & Bảo Mật Toàn Diện**: Giữ vững HTTP-to-HTTPS redirect (301), ACME Let's Encrypt challenge, Service Worker, Web App Manifest, Cache-Control chính xác và đầy đủ 4 Security Headers trên mọi endpoint.

---

## 2. Chi Tiết Các Thay Đổi Kiến Trúc & Cấu Hình

### A. Tách rời Web Root & Thiết lập Whitelist Deliverables
- **Web Root mới**: `/var/www/danabus/public`.
- **Cơ chế đồng bộ**: Kịch bản [`scripts/deploy_danabus_production.sh`](file:///home/opc/danabus/scripts/deploy_danabus_production.sh) thực hiện rsync/cp chỉ các artifact hợp lệ:
  - App shell & meta: `index.html`, `manifest.json`, `sw.js`.
  - Thư mục styles & scripts: `css/app.css`, `js/*.js`.
  - Tài nguyên đồ họa: `assets/logo.svg`, `assets/icons/*.png`.
  - Dữ liệu tuyến/trạm: `data/*.json` (bao gồm `danangbus_routes.json`, `danangbus_stops.json`, `danangbus_streets.json`, `danangbus_summary.json`, `danangbus_routes_compact.json`, `danangbus_resolution_report.json`).
  - **Loại trừ tuyệt đối**: `.git/`, `docs/`, `scripts/`, `stitch_bus_route_finder_pwa/`, `README.md`, `requirements.txt`, `data/schema.ts`, `data/osm_cache/`.

### B. Siết chặt phân quyền Workspace
- Xóa bỏ hoàn toàn lệnh `chmod -R o+rX "$WORKSPACE"` và `chmod o+x /home/opc`.
- Thiết lập quyền workspace `/home/opc/danabus` về `750` (`chmod 750` và `chmod -R o-rwx "$WORKSPACE"`).
- User `nginx` thuộc group `nginx` không có quyền truy cập vào `/home/opc/danabus`.

### C. Nâng cấp cấu hình Nginx ([`scripts/danabus.conf`](file:///home/opc/danabus/scripts/danabus.conf))
1. **Root**: `root /var/www/danabus/public;`
2. **Defense-in-depth Rules**:
   - `location ~ /\.(?!well-known).* { return 404; }`
   - `location ~* (^/(?:\.git|docs|scripts|stitch_bus_route_finder_pwa)|osm_cache)(?:/|$) { return 404; }`
   - `location ~* \.(?:md|txt|sh|py|conf|ts|bak|log)$ { return 404; }`
3. **Fail-closed Static & Data Endpoints**:
   - `location /data/` bổ sung `try_files $uri =404;`
   - `location ~* \.(?:css|js)$` bổ sung `try_files $uri =404;`
   - `location ~* \.(?:png|jpg|jpeg|gif|svg|ico|woff|woff2)$` bổ sung `try_files $uri =404;`
4. **Bảo toàn Security Headers trên toàn bộ location**:
   - Khắc phục đặc tính Nginx (khi location có `add_header Cache-Control` sẽ vô hiệu hóa việc kế thừa `add_header` từ `server` block) bằng cách khai báo đầy đủ 4 security headers (`X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`) trong tất cả các location block.

---

## 3. Bằng Chứng Thực Nghiệm & Test Matrix

Bộ kiểm thử tự động [`scripts/security_smoke_test.py`](file:///home/opc/danabus/scripts/security_smoke_test.py) và [`scripts/browser_smoke_test.py`](file:///home/opc/danabus/scripts/browser_smoke_test.py) đã được thực thi trực tiếp trên máy chủ và qua domain internet công khai (`danabus.638686.xyz`).

### A. Negative Security Tests (15/15 ĐẠT - Trả về HTTP 404, không rò rỉ mã nguồn/HTML)

| STT | Endpoint Kiểm Tra | Kết Quả HTTP | Đánh Giá |
|:---:|---|:---:|:---:|
| 1 | `GET /.git/config` | **404 Not Found** | PASS (Chặn truy cập Git repo) |
| 2 | `GET /.git/HEAD` | **404 Not Found** | PASS (Chặn truy cập Git ref) |
| 3 | `GET /docs/plans/2026-09-24-address-to-address-trip-planner-plan.md` | **404 Not Found** | PASS (Chặn tài liệu kế hoạch) |
| 4 | `GET /docs/reports/2026-09-27-danabus-full-project-audit-report.md` | **404 Not Found** | PASS (Chặn báo cáo audit) |
| 5 | `GET /scripts/danabus.conf` | **404 Not Found** | PASS (Chặn file cấu hình Nginx) |
| 6 | `GET /scripts/deploy_danabus_production.sh` | **404 Not Found** | PASS (Chặn kịch bản triển khai) |
| 7 | `GET /README.md` | **404 Not Found** | PASS (Chặn tài liệu nội bộ) |
| 8 | `GET /requirements.txt` | **404 Not Found** | PASS (Chặn thông tin phụ thuộc) |
| 9 | `GET /stitch_bus_route_finder_pwa/` | **404 Not Found** | PASS (Chặn prototype dev) |
| 10 | `GET /data/schema.ts` | **404 Not Found** | PASS (Chặn file TypeScript schema) |
| 11 | `GET /data/osm_cache/` | **404 Not Found** | PASS (Chặn cache dữ liệu OSM thô) |
| 12 | `GET /data/osm_cache/transit.json` | **404 Not Found** | PASS (Chặn file cache OSM) |
| 13 | `GET /data/nonexistent_file.json` | **404 Not Found** | PASS (Fail-closed, không fallback HTML) |
| 14 | `GET /js/nonexistent_file.js` | **404 Not Found** | PASS (Fail-closed, không fallback HTML) |
| 15 | `GET /assets/nonexistent_image.png` | **404 Not Found** | PASS (Fail-closed, không fallback HTML) |

### B. Positive Functional & Header Tests (10/10 ĐẠT - Trả về HTTP 200, đúng MIME & đầy đủ Security Headers)

| STT | Endpoint | HTTP Status | MIME Type | Cache-Control | Security Headers |
|:---:|---|:---:|---|---|:---:|
| 1 | `GET /` | **200 OK** | `text/html` | Server default | Đầy đủ 4 headers |
| 2 | `GET /index.html` | **200 OK** | `text/html` | Server default | Đầy đủ 4 headers |
| 3 | `GET /manifest.json` | **200 OK** | `application/json` | `public, max-age=86400` | Đầy đủ 4 headers |
| 4 | `GET /sw.js` | **200 OK** | `application/javascript` | `no-store, no-cache, must-revalidate...` | Đầy đủ 4 headers |
| 5 | `GET /css/app.css` | **200 OK** | `text/css` | `no-cache, must-revalidate, max-age=0` | Đầy đủ 4 headers |
| 6 | `GET /js/app.js` | **200 OK** | `application/javascript` | `no-cache, must-revalidate, max-age=0` | Đầy đủ 4 headers |
| 7 | `GET /js/busService.js` | **200 OK** | `application/javascript` | `no-cache, must-revalidate, max-age=0` | Đầy đủ 4 headers |
| 8 | `GET /data/danangbus_routes.json` | **200 OK** | `application/json` | `no-cache, must-revalidate, max-age=0` | Đầy đủ 4 headers |
| 9 | `GET /data/danangbus_stops.json` | **200 OK** | `application/json` | `no-cache, must-revalidate, max-age=0` | Đầy đủ 4 headers |
| 10 | `GET /assets/logo.svg` | **200 OK** | `image/svg+xml` | `public, max-age=604800` | Đầy đủ 4 headers |

*Chi tiết 4 Security Headers đã được xác minh trên từng response:*
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

### C. Network & Redirect Tests
- `curl -I -H "Host: danabus.638686.xyz" http://127.0.0.1/` $\rightarrow$ **HTTP/1.1 301 Moved Permanently**, `Location: https://danabus.638686.xyz/` (PASS).
- Let's Encrypt ACME Challenge: Thư mục `/var/www/html` tồn tại với quyền 755; vị trí `/.well-known/acme-challenge/` sẵn sàng phục vụ gia hạn SSL tự động.

### D. PWA Browser Smoke Test (Headless Chrome CDP)
Chạy kịch bản [`scripts/browser_smoke_test.py`](file:///home/opc/danabus/scripts/browser_smoke_test.py):
- **Boot & DOM State**: ĐẠT (khởi tạo thành công 23 tuyến xe buýt).
- **Route Detail & Map View**: Tuyến 02, 05, 11, TKY-TMY, TKY-NTH, 01DL, 01SB render đúng bản đồ, marker và polyline.
- **Direction Switching**: Chuyển chiều đi/về mượt mà, không để lại layer rác.
- **Geolocation API**: Mock vị trí và xử lý lỗi quyền vị trí hoạt động chính xác.
- **Service Worker Lifecycle**: Đăng ký thành công, cache v7 hoạt động, purge cache cũ thành công.
- **Ảnh bằng chứng kiểm thử**: Đã xuất ảnh chụp màn hình thực tế tại [`docs/reports/browser_smoke_evidence.png`](file:///home/opc/danabus/docs/reports/browser_smoke_evidence.png).

---

## 4. Kết Luận & Đề Xuất Chuyển Bước

1. Toàn bộ yêu cầu của **Task 5 (Production Security Hardening)** đã hoàn thành và được kiểm chứng độc lập trên cả môi trường cục bộ và production internet.
2. Không còn bất kỳ rủi ro rò rỉ mã nguồn, cấu hình hay tài liệu nội bộ nào trên production.
3. Không làm ảnh hưởng đến hiệu năng, trải nghiệm người dùng hoặc khả năng offline của PWA.
4. Đề xuất Tech Lead (TL) tiến hành nghiệm thu Task 5 và kích hoạt Task tiếp theo trong lộ trình remediation: **Task 6 (Search Correctness & No-Fake-Result)**.
