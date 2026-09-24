/**
 * Danabus Interactive Map Service using Leaflet.js
 * Renders verified route polylines and stop GPS coordinates.
 * Independent outbound/inbound geometries without fake simulations.
 */

class MapService {
  constructor() {
    this.map = null;
    this.markersLayer = null;
    this.routeLine = null;
    this.userMarker = null;
    this.accuracyCircle = null;
    this.infoOverlay = null;
    this.userLocation = null;
    this.defaultCenter = [16.0544, 108.2022]; // Da Nang Center
  }

  init(containerId = 'map-container') {
    const el = document.getElementById(containerId);
    if (!el || typeof L === 'undefined') return;

    if (this.map) {
      this.map.remove();
      this.map = null;
      this.markersLayer = null;
      this.routeLine = null;
      this.userMarker = null;
      this.accuracyCircle = null;
      this.infoOverlay = null;
    }
    this.removeInfoOverlay();

    this.map = L.map(containerId, {
      center: this.defaultCenter,
      zoom: 12,
      zoomControl: false
    });

    // Clean OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap'
    }).addTo(this.map);

    this.markersLayer = L.layerGroup().addTo(this.map);
  }

  renderRoute(route, direction = 'outbound') {
    if (!this.map || !route) return;
    this.clear();

    const geometry = route.geometry?.[direction];
    const stops = (route.stops?.[direction] || []).filter(s => s && typeof s.lat === 'number' && typeof s.lng === 'number' && !isNaN(s.lat) && !isNaN(s.lng));
    const hasGeometry = Array.isArray(geometry) && geometry.length > 1;

    // Remove any previous info message overlay
    this.removeInfoOverlay();

    if (hasGeometry) {
      // Render verified road polyline
      this.routeLine = L.polyline(geometry, {
        color: '#059669',
        weight: 5,
        opacity: 0.9,
        lineCap: 'round',
        lineJoin: 'round'
      }).addTo(this.map);

      this.map.fitBounds(this.routeLine.getBounds(), { padding: [30, 30] });
    } else {
      // Geometry is unverified / null for this direction -> show no-data overlay
      this.showInfoOverlay('Chưa có dữ liệu bản đồ cho tuyến này');

      if (stops.length > 1) {
        // Fit bounds to stops if available
        const stopBounds = L.latLngBounds(stops.map(s => [s.lat, s.lng]));
        this.map.fitBounds(stopBounds, { padding: [30, 30] });
      } else if (stops.length === 1) {
        this.map.setView([stops[0].lat, stops[0].lng], 13);
      } else {
        this.map.setView(this.defaultCenter, 12);
      }
    }

    // Render verified stop markers
    stops.forEach((stop, idx) => {
      const isStart = idx === 0;
      const isEnd = idx === stops.length - 1;
      const stopNum = stop.order || (idx + 1);

      let markerBgClass = 'bg-white text-[#059669] border-2 border-[#059669]';
      if (isStart) {
        markerBgClass = 'bg-[#059669] text-white ring-4 ring-emerald-100';
      } else if (isEnd) {
        markerBgClass = 'bg-[#dc2626] text-white ring-4 ring-red-100';
      }

      const markerHtml = `
        <div class="relative flex items-center justify-center cursor-pointer group">
          <div class="w-7 h-7 rounded-full ${markerBgClass} shadow-md flex items-center justify-center font-bold text-[12px]">
            ${stopNum}
          </div>
        </div>
      `;

      const icon = L.divIcon({
        html: markerHtml,
        className: 'custom-bus-stop-icon',
        iconSize: [28, 28],
        iconAnchor: [14, 14]
      });

      const marker = L.marker([stop.lat, stop.lng], { icon }).addTo(this.markersLayer);

      const statusBadge = stop.confidence === 'high' ? '<span class="text-[9px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 font-medium">Đã xác minh</span>' : '';

      const popupContent = `
        <div class="p-1 font-['Be_Vietnam_Pro'] max-w-[220px]">
          <div class="flex items-center gap-1.5 font-bold text-[13px] text-slate-900">
            <span class="w-5 h-5 rounded-full ${isStart ? 'bg-[#059669]' : (isEnd ? 'bg-[#dc2626]' : 'bg-slate-700')} text-white text-[11px] flex items-center justify-center font-extrabold shrink-0">${stopNum}</span>
            <span class="truncate">${stop.name || 'Trạm xe buýt'}</span>
          </div>
          ${stop.street ? `<p class="text-[11px] text-slate-600 mt-1 font-medium">Đường ${stop.street}</p>` : ''}
          <div class="flex items-center justify-between mt-1.5 pt-1 border-t border-slate-100 text-[10px] text-slate-400">
            <span>Tuyến ${route.routeNumber}</span>
            ${statusBadge}
          </div>
        </div>
      `;
      marker.bindPopup(popupContent);
    });
  }

  showInfoOverlay(message) {
    if (!this.map) return;
    this.removeInfoOverlay();
    
    const container = this.map.getContainer();
    const overlay = document.createElement('div');
    overlay.id = 'map-info-overlay';
    overlay.className = 'absolute top-4 left-4 right-4 z-[1000] bg-amber-50 border border-amber-200 text-amber-800 px-3.5 py-2.5 rounded-xl shadow-md text-[12px] font-medium flex items-center gap-2 animate-fade-in pointer-events-auto';
    overlay.innerHTML = `
      <svg class="w-4 h-4 text-amber-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>${message}</span>
    `;
    container.appendChild(overlay);
    this.infoOverlay = overlay;
  }

  removeInfoOverlay() {
    if (this.infoOverlay && this.infoOverlay.parentNode) {
      this.infoOverlay.parentNode.removeChild(this.infoOverlay);
    }
    document.querySelectorAll('#map-info-overlay').forEach(el => {
      if (el.parentNode) {
        el.parentNode.removeChild(el);
      }
    });
    this.infoOverlay = null;
  }

  async locateUser() {
    if (!navigator.geolocation) {
      const err = { code: 0, message: 'Trình duyệt không hỗ trợ định vị GPS.' };
      return { success: false, error: err.message };
    }

    return new Promise((resolve) => {
      const options = {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 30000
      };

      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const { latitude, longitude, accuracy } = pos.coords;
          const timestamp = pos.timestamp;
          this.userLocation = { lat: latitude, lng: longitude, accuracy, timestamp };

          if (this.map) {
            // Remove previous user layer
            if (this.userMarker) {
              this.map.removeLayer(this.userMarker);
              this.userMarker = null;
            }
            if (this.accuracyCircle) {
              this.map.removeLayer(this.accuracyCircle);
              this.accuracyCircle = null;
            }

            // Draw accuracy circle
            if (accuracy && accuracy > 0) {
              this.accuracyCircle = L.circle([latitude, longitude], {
                radius: accuracy,
                color: '#3b82f6',
                weight: 1,
                fillColor: '#3b82f6',
                fillOpacity: 0.15
              }).addTo(this.map);
            }

            // Draw user marker
            const userHtml = `
              <div class="relative flex items-center justify-center">
                <span class="absolute w-8 h-8 rounded-full bg-blue-500 opacity-30 animate-ping"></span>
                <div class="w-6 h-6 rounded-full bg-blue-600 ring-4 ring-white shadow-lg flex items-center justify-center text-white">
                  <svg viewBox="0 0 24 24" fill="currentColor" class="w-3.5 h-3.5 text-white"><circle cx="12" cy="12" r="6"/></svg>
                </div>
              </div>
            `;
            const icon = L.divIcon({ html: userHtml, className: 'user-loc-icon', iconSize: [24, 24], iconAnchor: [12, 12] });
            this.userMarker = L.marker([latitude, longitude], { icon }).addTo(this.map);

            this.userMarker.bindPopup(`
              <div class="p-1 font-['Be_Vietnam_Pro'] text-[12px]">
                <strong class="text-slate-900">Vị trí của bạn</strong>
                <p class="text-slate-500 text-[10px] mt-0.5">Độ chính xác: ±${Math.round(accuracy || 0)}m</p>
              </div>
            `);

            this.map.setView([latitude, longitude], Math.max(this.map.getZoom(), 14));
          }

          resolve({
            success: true,
            coords: { latitude, longitude, accuracy, timestamp }
          });
        },
        (err) => {
          let userMsg = 'Không thể lấy vị trí hiện tại.';
          if (err.code === 1) {
            userMsg = 'Quyền truy cập vị trí đã bị từ chối.';
          } else if (err.code === 2) {
            userMsg = 'Vị trí hiện không khả dụng.';
          } else if (err.code === 3) {
            userMsg = 'Quá thời gian yêu cầu vị trí GPS.';
          }
          console.warn('[MapService] Geolocation error:', userMsg, err.message);
          resolve({
            success: false,
            error: userMsg,
            code: err.code
          });
        },
        options
      );
    });
  }

  clear() {
    if (this.markersLayer) {
      this.markersLayer.clearLayers();
    }
    if (this.routeLine && this.map) {
      this.map.removeLayer(this.routeLine);
      this.routeLine = null;
    }
    this.removeInfoOverlay();
  }
}

window.mapService = new MapService();
