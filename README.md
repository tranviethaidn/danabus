# Danabus - Tra Cứu Tuyến Xe Buýt Đà Nẵng

Ứng dụng web tiến bộ (PWA) hỗ trợ tra cứu tuyến xe buýt, lộ trình, điểm dừng, tìm đường và thông tin vận hành xe buýt tại khu vực Đà Nẵng & Hội An.

## ✨ Tính Năng Nổi Bật

- 🚌 **Tra cứu tuyến xe:** Danh sách toàn bộ các tuyến xe buýt nội thành và liên tỉnh (Đà Nẵng - Hội An, Tam Kỳ...).
- 🗺️ **Bản đồ tương tác trực quan:** Hiển thị trực quan lộ trình đi/về (chiều đi - chiều về) và hệ thống trạm dừng xe buýt trên nền OpenStreetMap / Leaflet.
- 🔍 **Tìm đường thông minh:** Tìm tuyến xe tối ưu giữa hai điểm xuất phát và đích đến.
- 📱 **Progressive Web App (PWA):** Cài đặt trực tiếp lên điện thoại hoặc máy tính, hỗ trợ Service Worker hoạt động mượt mà và lưu trữ dữ liệu offline.
- ⚡ **Giao diện hiện đại & tối ưu:** Thiết kế trực quan, thân thiện cho thiết bị di động, tốc độ tải nhanh.

## 🛠️ Công Nghệ Sử Dụng

- **Frontend:** Vanilla HTML5, CSS3, JavaScript (ES6+)
- **Bản đồ:** Leaflet.js / OpenStreetMap
- **PWA:** Web App Manifest & Service Worker (`sw.js`)
- **Dữ liệu:** JSON cấu trúc chi tiết các trạm dừng, tuyến đường và tọa độ GPS

## 🚀 Hướng Dẫn Chạy Cục Bộ

1. Clone repository về máy:
   ```bash
   git clone https://github.com/tranviethaidn/danabus.git
   cd danabus
   ```

2. Chạy ứng dụng thông qua bất kỳ web server tĩnh nào (ví dụ: Live Server trong VS Code, Python HTTP server hoặc `npx serve`):
   ```bash
   # Sử dụng Python:
   python -m http.server 8000
   ```

3. Mở trình duyệt và truy cập `http://localhost:8000`.

## 📄 Bản Quyền & Giấy Phép

Dự án được xây dựng phục vụ cộng đồng và người dân sử dụng phương tiện công cộng tại Đà Nẵng.
