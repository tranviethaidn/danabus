#!/bin/bash
set -e

DOMAIN="danabus.638686.xyz"
WORKSPACE="/home/opc/danabus"
PUBLIC_DIR="/var/www/danabus/public"
CONF_FILE="/etc/nginx/conf.d/danabus.conf"
EMAIL="admin@638686.xyz"

echo "=== 1. Chuẩn bị thư mục Public Root độc lập (/var/www/danabus/public) ==="
mkdir -p "$PUBLIC_DIR"
if [ "$(id -u)" -eq 0 ]; then
    chown -R opc:nginx /var/www/danabus
    chmod 755 /var/www/danabus "$PUBLIC_DIR"
    mkdir -p /var/www/html
    chmod -R 755 /var/www/html
fi

echo "=== 2. Đồng bộ Whitelist Deliverables sang Public Root (Staged Deploy) ==="
# Tuyệt đối không copy .git, docs, scripts, README, requirements.txt hay prototype

# Stage 2.1: Đồng bộ payload tài nguyên phụ thuộc trước (css, js, assets, data)
# Đảm bảo mọi script và style v10 đã hiện diện trên disk trước khi client nhận HTML/SW mới
mkdir -p "$PUBLIC_DIR"/css "$PUBLIC_DIR"/js "$PUBLIC_DIR"/assets "$PUBLIC_DIR"/data
rsync -a --delete "$WORKSPACE"/css/ "$PUBLIC_DIR"/css/
rsync -a --delete "$WORKSPACE"/js/ "$PUBLIC_DIR"/js/
rsync -a --delete "$WORKSPACE"/assets/ "$PUBLIC_DIR"/assets/

# Data: chỉ sync các file JSON dữ liệu tuyến/trạm/báo cáo, loại bỏ schema.ts và osm_cache/
rsync -a --delete --include="*.json" --exclude="*" "$WORKSPACE"/data/ "$PUBLIC_DIR"/data/

# Stage 2.2: Đồng bộ Web App Manifest sau khi payload assets đã sẵn sàng
cp -f "$WORKSPACE"/manifest.json "$PUBLIC_DIR/manifest.json"

# Stage 2.3: Xuất bản index.html bằng cơ chế atomic swap (temp file + rename)
# Đảm bảo index.html chỉ tham chiếu tới payload assets đã hiện diện đầy đủ trên disk
cp -f "$WORKSPACE"/index.html "$PUBLIC_DIR/index.html.tmp"
mv -f "$PUBLIC_DIR/index.html.tmp" "$PUBLIC_DIR/index.html"

# Stage 2.4: Xuất bản Service Worker sw.js CUỐI CÙNG bằng cơ chế atomic swap (temp file + rename)
# sw.js v10 precache cả './' và './index.html'. Bằng việc xuất bản sw.js sau khi index.html v10
# đã hiện diện an toàn trên disk, ta triệt tiêu hoàn toàn race condition v10-worker precache v9-index.
cp -f "$WORKSPACE"/sw.js "$PUBLIC_DIR/sw.js.tmp"
mv -f "$PUBLIC_DIR/sw.js.tmp" "$PUBLIC_DIR/sw.js"

# Phân quyền chuẩn cho web deliverables (chủ sở hữu opc:nginx, người dùng khác chỉ đọc)
chmod -R u=rwX,go=rX "$PUBLIC_DIR"

echo "=== 3. Khóa quyền truy cập Workspace (/home/opc/danabus) theo Least Privilege ==="
chmod 750 "$WORKSPACE"
chmod -R o-rwx "$WORKSPACE"

echo "=== 4. Kiểm tra cấu hình và chứng chỉ Nginx (Bỏ qua sudo nếu đã hợp lệ) ==="
# Đối với release tĩnh định kỳ, Nginx đã trỏ vào public root và reload là không bắt buộc
if [ "$1" == "--full" ] || [ ! -f "$CONF_FILE" ]; then
    if command -v sudo >/dev/null 2>&1 && [ "$(id -u)" -ne 0 ]; then
        SUDO_CMD="sudo"
    else
        SUDO_CMD=""
    fi
    if [ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
        echo "Cần chứng chỉ SSL, vui lòng chạy certbot..."
    fi
    $SUDO_CMD cp "$WORKSPACE/scripts/danabus.conf" "$CONF_FILE"
    $SUDO_CMD nginx -t
    $SUDO_CMD systemctl reload nginx
else
    echo "Nginx conf và SSL đã sẵn sàng tại $CONF_FILE. Deliverables tĩnh được áp dụng tức thì."
fi

echo "=== HOÀN TẤT TRIỂN KHAI PRODUCTION (DANABUS PWA RELEASE UPGRADE) ==="
