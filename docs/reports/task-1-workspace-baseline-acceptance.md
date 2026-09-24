# Báo cáo nghiệm thu Task 1 - Thiết lập workspace danabus

## Phạm vi
- Thiết lập workspace tại `/home/opc/danabus`.
- Đồng bộ source từ repository `tranviethaidn/danabus` và cấu hình SSH deploy key riêng.
- Đưa Danabus PWA lên production tại `danabus.638686.xyz` qua Nginx + HTTPS.
- Không push hoặc thay đổi source ứng dụng ngoài artifact phục vụ triển khai.

## Bằng chứng triển khai
- Git branch `main` tracking `origin/main`, HEAD đã xác minh: `e569ff4`.
- Remote: `git@github.com:tranviethaidn/danabus.git`.
- Deploy key public fingerprint: `SHA256:xXuvYaBCqjYjFedtuCnipJSvflZZGxGS+UIXQrJr82M`; private key không được đưa vào báo cáo/chat.
- Nginx vhost: `/etc/nginx/conf.d/danabus.conf`, document root `/home/opc/danabus`.
- Certbot renewal config và Nginx đều tham chiếu certificate `/etc/letsencrypt/live/danabus.638686.xyz/fullchain.pem` và private key tương ứng.
- Live TLS certificate: CN/SAN `danabus.638686.xyz`, issuer Let's Encrypt YE1, hiệu lực 24/09/2026 đến 23/12/2026.

## Kiểm tra / xác minh
- HTTP local redirect sang HTTPS: PASS (301).
- HTTPS local: root, `manifest.json`, `sw.js`, CSS, JS, JSON data và SPA fallback: PASS (200).
- Public `https://danabus.638686.xyz/`: PASS (200, `text/html`).
- Live TLS handshake qua SNI: PASS; certificate đúng domain.
- `nginx -t` không thể được TL chạy trực tiếp dưới user hiện tại do quyền đọc certificate; lệnh privileged bị policy của môi trường TL chặn. Runtime Nginx đang phục vụ HTTPS thành công và DEV đã cung cấp evidence privileged.

## Kết quả review
- PASS. Domain production, HTTPS và PWA endpoints đã hoạt động thực tế.
- Sai lệch trước đó về việc TL thấy certificate “không tồn tại” được giải thích bởi quyền traversal của Certbot; live TLS, renewal config và Nginx config đã xác nhận certificate đúng.

## Giới hạn đã biết
- `docs/` và các deployment artifact trong `scripts/` hiện là artifact VibeLab/deployment chưa được yêu cầu commit vào application repository.
- TL không trực tiếp thực thi được privileged `nginx -t` do policy runtime; đây không phải lỗi production.
