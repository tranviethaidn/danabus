#!/bin/bash
set -e

DOMAIN="danabus.638686.xyz"
WORKSPACE="/home/opc/danabus"
CONF_FILE="/etc/nginx/conf.d/danabus.conf"
EMAIL="admin@638686.xyz"

echo "=== 1. Thiết lập quyền truy cập thư mục cho Nginx worker ==="
chmod o+x /home/opc
chmod -R o+rX "$WORKSPACE"
find "$WORKSPACE" -type d -exec chmod o+x {} +

sudo mkdir -p /var/www/html
sudo chmod -R 755 /var/www/html

echo "=== 2. Tạo cấu hình Nginx ban đầu cho ACME challenge ==="
cat << 'EOF' > /tmp/danabus_http.conf
server {
    listen 80;
    listen [::]:80;
    server_name danabus.638686.xyz;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        root /home/opc/danabus;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
}
EOF
sudo cp /tmp/danabus_http.conf "$CONF_FILE"
rm -f /tmp/danabus_http.conf

echo "=== 3. Kiểm tra Nginx và reload ==="
sudo nginx -t
sudo systemctl reload nginx

echo "=== 4. Xin cấp chứng chỉ SSL Let's Encrypt ==="
sudo certbot certonly --webroot -w /var/www/html -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" || echo "Certbot webroot failed, trying standalone/existing"

echo "=== 5. Tạo cấu hình Nginx chính thức đầy đủ (HTTPS + HTTP redirect + PWA optimize) ==="
cat << 'EOF' > /tmp/danabus_full.conf
server {
    server_name danabus.638686.xyz;

    root /home/opc/danabus;
    index index.html;

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/x-javascript application/json application/manifest+json image/svg+xml;

    # Security Headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Service Worker & Manifest
    location = /sw.js {
        expires -1;
        add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0";
    }

    location = /manifest.json {
        expires 1d;
        add_header Cache-Control "public, max-age=86400";
    }

    # Data files (Network-first / fresh validation dataset)
    location /data/ {
        expires -1;
        add_header Cache-Control "no-cache, must-revalidate, max-age=0";
    }

    # Static Assets & Images Cache
    location ~* \.(?:css|js|png|jpg|jpeg|gif|svg|ico|woff|woff2)$ {
        expires 7d;
        add_header Cache-Control "public, max-age=604800, immutable";
    }

    # SPA Routing Fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    listen [::]:443 ssl http2;
    listen 443 ssl http2;
    ssl_certificate /etc/letsencrypt/live/danabus.638686.xyz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/danabus.638686.xyz/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

server {
    if ($host = danabus.638686.xyz) {
        return 301 https://$host$request_uri;
    }

    listen 80;
    listen [::]:80;
    server_name danabus.638686.xyz;
    return 404;
}
EOF

sudo cp /tmp/danabus_full.conf "$CONF_FILE"
rm -f /tmp/danabus_full.conf

echo "=== 6. Kiểm tra Nginx configuration và reload ==="
sudo nginx -t
sudo systemctl reload nginx

echo "=== 7. Kiểm tra trạng thái SSL và Certificates ==="
sudo certbot certificates

echo "=== HOÀN TẤT TRIỂN KHAI ==="
