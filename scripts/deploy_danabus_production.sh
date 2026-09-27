#!/bin/bash
set -e

DOMAIN="danabus.638686.xyz"
WORKSPACE="/home/opc/danabus"
PUBLIC_DIR="/var/www/danabus/public"
CONF_FILE="/etc/nginx/conf.d/danabus.conf"
EMAIL="admin@638686.xyz"

echo "=== 1. Chuẩn bị thư mục Public Root độc lập (/var/www/danabus/public) ==="
sudo mkdir -p "$PUBLIC_DIR"
sudo chown -R opc:nginx /var/www/danabus
sudo chmod 755 /var/www/danabus "$PUBLIC_DIR"

sudo mkdir -p /var/www/html
sudo chmod -R 755 /var/www/html

echo "=== 2. Đồng bộ Whitelist Deliverables sang Public Root ==="
# Tuyệt đối không copy .git, docs, scripts, README, requirements.txt hay prototype
cp -f "$WORKSPACE"/index.html "$PUBLIC_DIR/"
cp -f "$WORKSPACE"/manifest.json "$PUBLIC_DIR/"
cp -f "$WORKSPACE"/sw.js "$PUBLIC_DIR/"

mkdir -p "$PUBLIC_DIR"/css "$PUBLIC_DIR"/js "$PUBLIC_DIR"/assets "$PUBLIC_DIR"/data
rsync -a --delete "$WORKSPACE"/css/ "$PUBLIC_DIR"/css/
rsync -a --delete "$WORKSPACE"/js/ "$PUBLIC_DIR"/js/
rsync -a --delete "$WORKSPACE"/assets/ "$PUBLIC_DIR"/assets/

# Data: chỉ sync các file JSON dữ liệu tuyến/trạm/báo cáo, loại bỏ schema.ts và osm_cache/
rsync -a --delete --include="*.json" --exclude="*" "$WORKSPACE"/data/ "$PUBLIC_DIR"/data/

# Phân quyền chuẩn cho web deliverables (chủ sở hữu opc:nginx, người dùng khác chỉ đọc)
chmod -R u=rwX,go=rX "$PUBLIC_DIR"

echo "=== 3. Khóa quyền truy cập Workspace (/home/opc/danabus) theo Least Privilege ==="
# Loại bỏ hoàn toàn quyền đọc/duyệt của others (bao gồm user nginx) trên workspace
chmod 750 "$WORKSPACE"
chmod -R o-rwx "$WORKSPACE"

echo "=== 4. Kiểm tra chứng chỉ SSL Let's Encrypt ==="
if [ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo "Chưa tìm thấy chứng chỉ SSL, khởi tạo cấu hình tạm thời cho ACME challenge..."
    cat << 'EOF' > /tmp/danabus_bootstrap.conf
server {
    listen 80;
    listen [::]:80;
    server_name danabus.638686.xyz;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        root /var/www/danabus/public;
        index index.html;
    }
}
EOF
    sudo cp /tmp/danabus_bootstrap.conf "$CONF_FILE"
    rm -f /tmp/danabus_bootstrap.conf
    sudo nginx -t
    sudo systemctl reload nginx
    sudo certbot certonly --webroot -w /var/www/html -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" || echo "Certbot webroot failed, trying standalone/existing"
fi

echo "=== 5. Triển khai cấu hình Nginx Hardened chính thức ==="
sudo cp "$WORKSPACE/scripts/danabus.conf" "$CONF_FILE"

echo "=== 6. Kiểm tra cú pháp Nginx và Reload dịch vụ ==="
sudo nginx -t
sudo systemctl reload nginx

echo "=== 7. Kiểm tra trạng thái SSL và Certificates ==="
sudo certbot certificates || true

echo "=== HOÀN TẤT TRIỂN KHAI TASK 5 (PRODUCTION SECURITY HARDENING) ==="
