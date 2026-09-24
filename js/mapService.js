/**
 * Danabus Interactive Map Service using Leaflet.js
 */

class MapService {
  constructor() {
    this.map = null;
    this.markersLayer = null;
    this.routeLine = null;
    this.busMarker = null;
    this.userMarker = null;
    this.defaultCenter = [16.0544, 108.2022]; // Da Nang Center
  }

  init(containerId = 'map-container') {
    const el = document.getElementById(containerId);
    if (!el || typeof L === 'undefined') return;

    if (this.map) {
      this.map.remove();
      this.map = null;
    }

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
    if (!this.map) return;
    this.clear();

    const stops = route.stops?.[direction] || [];
    const waypoints = [];

    // Realistic coordinates along Danabus corridor (Da Nang to Hoi An)
    // Starting from Ben Xe TT, through Thanh Khe, Hai Chau, Ngu Hanh Son to Hoi An/Cua Dai
    const basePoints = [
      { name: 'Bến xe TT Đà Nẵng', lat: 16.0628, lng: 108.1725 },
      { name: 'Nguyễn Tất Thành', lat: 16.0740, lng: 108.1880 },
      { name: 'Trần Phú / Chợ Hàn', lat: 16.0685, lng: 108.2240 },
      { name: 'Nhà thờ Con Gà', lat: 16.0660, lng: 108.2230 },
      { name: 'Cầu Rồng • CV APEC', lat: 16.0610, lng: 108.2235 },
      { name: 'Cầu Tiên Sơn', lat: 16.0350, lng: 108.2390 },
      { name: 'BV Phụ sản Nhi', lat: 16.0275, lng: 108.2430 },
      { name: 'Ngũ Hành Sơn', lat: 16.0041, lng: 108.2618 },
      { name: 'ĐH Việt - Hàn (VKU)', lat: 15.9750, lng: 108.2520 },
      { name: 'Bến xe Phố Cổ Hội An', lat: 15.8794, lng: 108.3350 },
      { name: 'Biển Cửa Đại', lat: 15.8942, lng: 108.3758 }
    ];

    // If reverse direction, invert base points
    const points = direction === 'outbound' ? basePoints : [...basePoints].reverse();

    points.forEach((pt, idx) => {
      waypoints.push([pt.lat, pt.lng]);

      // Custom stop marker
      const isStart = idx === 0;
      const isEnd = idx === points.length - 1;
      const isLiveBus = idx === 3; // Bus currently simulated at 4th stop

      const markerHtml = `
        <div class="relative flex items-center justify-center cursor-pointer group">
          ${isLiveBus ? `
            <span class="absolute w-10 h-10 rounded-full bg-emerald-400 opacity-40 animate-ping"></span>
            <span class="absolute w-7 h-7 rounded-full bg-emerald-500/30 animate-pulse"></span>
          ` : ''}
          <div class="w-7 h-7 rounded-full ${isStart || isEnd || isLiveBus ? 'bg-[#059669] text-white ring-4 ring-white' : 'bg-white text-[#059669] border-2 border-[#059669]'} shadow-md flex items-center justify-center font-bold text-[12px]">
            ${isLiveBus ? (window.renderIcon ? window.renderIcon('directions_bus', 'w-3.5 h-3.5 text-white') : '<svg viewBox="0 0 24 24" fill="currentColor" class="w-3.5 h-3.5 text-white"><path d="M4 16c0 .88.39 1.67 1 2.22V20c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h8v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4s-8 .5-8 4v10zm3.5 1c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm9 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm1.5-6H6V6h12v5z"/></svg>') : (idx + 1)}
          </div>
        </div>
      `;

      const icon = L.divIcon({
        html: markerHtml,
        className: 'custom-bus-stop-icon',
        iconSize: [28, 28],
        iconAnchor: [14, 14]
      });

      const marker = L.marker([pt.lat, pt.lng], { icon }).addTo(this.markersLayer);
      
      const popupContent = `
        <div class="p-1 font-['Be_Vietnam_Pro']">
          <div class="flex items-center gap-1.5 font-bold text-[13px] text-slate-900">
            <span class="w-5 h-5 rounded-full bg-[#059669] text-white text-[11px] flex items-center justify-center font-extrabold shrink-0">${idx + 1}</span>
            <span>${pt.name}</span>
          </div>
          ${isLiveBus ? `
            <div class="mt-1.5 px-2 py-1 rounded bg-[#ecfdf5] border border-emerald-200 text-[#047857] text-[11px] font-semibold flex items-center gap-1">
              <span class="w-1.5 h-1.5 rounded-full bg-[#059669] animate-ping"></span>
              Xe 43B-028.91 đang đón khách (dự kiến rời 2p)
            </div>
          ` : `
            <p class="text-[11px] text-slate-500 mt-1">Trạm dừng tuyến ${route.routeNumber}</p>
          `}
        </div>
      `;
      marker.bindPopup(popupContent);
    });

    // Draw route polyline
    if (waypoints.length > 1) {
      this.routeLine = L.polyline(waypoints, {
        color: '#059669',
        weight: 5,
        opacity: 0.85,
        lineCap: 'round',
        lineJoin: 'round'
      }).addTo(this.markersLayer);

      this.map.fitBounds(this.routeLine.getBounds(), { padding: [30, 30] });
    }
  }

  locateUser() {
    if (!navigator.geolocation || !this.map) return;
    navigator.geolocation.getCurrentPosition(pos => {
      const { latitude, longitude } = pos.coords;
      if (this.userMarker) {
        this.userMarker.setLatLng([latitude, longitude]);
      } else {
        const userHtml = `
          <div class="relative flex items-center justify-center">
            <span class="absolute w-8 h-8 rounded-full bg-blue-400 opacity-40 animate-ping"></span>
            <div class="w-5 h-5 rounded-full bg-blue-600 ring-4 ring-white shadow-md flex items-center justify-center text-white">
              ${window.renderIcon ? window.renderIcon('my_location', 'w-3.5 h-3.5 text-white') : '<svg viewBox="0 0 24 24" fill="currentColor" class="w-3.5 h-3.5 text-white"><circle cx="12" cy="12" r="8"/></svg>'}
            </div>
          </div>
        `;
        const icon = L.divIcon({ html: userHtml, iconSize: [20, 20], iconAnchor: [10, 10] });
        this.userMarker = L.marker([latitude, longitude], { icon }).addTo(this.map);
      }
      this.map.setView([latitude, longitude], 14);
    }, err => {
      console.warn('Geolocation error:', err.message);
    });
  }

  clear() {
    if (this.markersLayer) this.markersLayer.clearLayers();
    if (this.routeLine) {
      this.map.removeLayer(this.routeLine);
      this.routeLine = null;
    }
  }
}

window.mapService = new MapService();
