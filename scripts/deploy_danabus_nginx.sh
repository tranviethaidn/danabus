#!/bin/bash
# ==============================================================================
# SCRIPT TRIỂN KHAI & CẤU HÌNH NGINX CHO DANABUS PWA (danabus.638686.xyz)
# ==============================================================================

set -e

DOMAIN="danabus.638686.xyz"
WORKSPACE="/home/opc/danabus"
CONF_SRC="$WORKSPACE/scripts/danabus.conf"
CONF_DEST="/etc/nginx/conf.d/danabus.conf"
EMAIL="admin@638686.xyz"

echo "======================================================================"
echo "🚀 BẮT ĐẦU TRIỂN KHAI DOMAIN $DOMAIN CHO DANABUS PWA"
echo "======================================================================"

# 1. Đảm bảo quyền truy cập thư mục cho Nginx worker (nginx user)
echo "⚙️ Thiết lập quyền truy cập thư mục workspace..."
chmod o+x /home/opc
chmod -R o+r "$WORKSPACE"
find "$WORKSPACE" -type d -exec chmod o+x {} +

# 2. Tạo cấu hình Nginx ban đầu (HTTP trước để cấp chứng chỉ SSL)
echo "⚙️ Cài đặt cấu hình Nginx tạm thời cho bước xác thực Certbot..."
sudo tee "$CONF_DEST" > /dev/null << 'EOF'
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

# 3. Kiểm tra cú pháp Nginx và reload
echo "🔍 Kiểm tra cú pháp Nginx..."
sudo nginx -t
sudo systemctl reload nginx

# 4. Đăng ký chứng chỉ SSL Let's Encrypt qua Certbot
echo "🔒 Đăng ký cấp chứng chỉ SSL Let's Encrypt cho $DOMAIN..."
if ! sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect; then
    echo "⚠️ Certbot tự động cấu hình thất bại hoặc SSL do Cloudflare quản lý. Cài đặt file cấu hình đầy đủ..."
    sudo cp "$CONF_SRC" "$CONF_DEST"
    sudo nginx -t && sudo systemctl reload nginx
fi

# 5. Cài đặt cấu hình tối ưu PWA hoàn chỉnh
echo "⚡ Cập nhật cấu hình Nginx tối ưu PWA, Gzip, Caching..."
sudo cp "$CONF_SRC" "$CONF_DEST"
sudo nginx -t
sudo systemctl reload nginx

echo "======================================================================"
echo "🎉 TRIỂN KHAI HOÀN TẤT!"
echo "🌐 URL: https://$DOMAIN"
echo "📁 Root: $WORKSPACE"
echo "======================================================================"
