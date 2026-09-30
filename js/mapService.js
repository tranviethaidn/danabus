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
    this.currentRoute = null;
    this.currentDirection = 'outbound';
    this.defaultCenter = [16.0544, 108.2022]; // Da Nang Center
    this.tripPolylines = [];
    this.pinMarker = null;
    this.isPinSelectionMode = false;
    this.onPinSelectedCallback = null;
    this._mapPinClickHandler = null;
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

  fitRoute() {
    if (!this.map) return;
    if (this.routeLine) {
      this.map.fitBounds(this.routeLine.getBounds(), { padding: [30, 30] });
    } else if (this.tripPolylines && this.tripPolylines.length > 0) {
      const group = L.featureGroup(this.tripPolylines);
      this.map.fitBounds(group.getBounds(), { padding: [30, 30] });
    } else if (this.currentRoute) {
      const stops = (this.currentRoute.stops?.[this.currentDirection] || []).filter(
        s => s && typeof s.lat === 'number' && typeof s.lng === 'number' && !isNaN(s.lat) && !isNaN(s.lng)
      );
      if (stops.length > 1) {
        const stopBounds = L.latLngBounds(stops.map(s => [s.lat, s.lng]));
        this.map.fitBounds(stopBounds, { padding: [30, 30] });
      } else if (stops.length === 1) {
        this.map.setView([stops[0].lat, stops[0].lng], 13);
      } else {
        this.map.setView(this.defaultCenter, 12);
      }
    } else {
      this.map.setView(this.defaultCenter, 12);
    }
  }

  renderRoute(route, direction = 'outbound') {
    if (!this.map || !route) return;
    this.currentRoute = route;
    this.currentDirection = direction;
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

    // Re-render user marker if active
    if (this.userLocation && typeof this.userLocation.lat === 'number' && typeof this.userLocation.lng === 'number') {
      this.renderUserLocationMarker(this.userLocation.lat, this.userLocation.lng, this.userLocation.accuracy);
    }
  }

  renderUserLocationMarker(latitude, longitude, accuracy) {
    if (!this.map) return;
    if (this.userMarker) {
      this.map.removeLayer(this.userMarker);
      this.userMarker = null;
    }
    if (this.accuracyCircle) {
      this.map.removeLayer(this.accuracyCircle);
      this.accuracyCircle = null;
    }

    if (accuracy && accuracy > 0) {
      this.accuracyCircle = L.circle([latitude, longitude], {
        radius: accuracy,
        color: '#2563eb',
        weight: 1.5,
        fillColor: '#3b82f6',
        fillOpacity: 0.15
      }).addTo(this.map);
    }

    const userHtml = `
      <div class="relative flex items-center justify-center">
        <span class="absolute w-8 h-8 rounded-full bg-blue-500 opacity-30 animate-ping"></span>
        <div class="w-6 h-6 rounded-full bg-blue-600 ring-4 ring-white shadow-lg flex items-center justify-center text-white">
          <svg viewBox="0 0 24 24" fill="currentColor" class="w-3.5 h-3.5 text-white"><circle cx="12" cy="12" r="6"/></svg>
        </div>
      </div>
    `;
    const icon = L.divIcon({ html: userHtml, className: 'user-loc-icon', iconSize: [24, 24], iconAnchor: [12, 12] });
    this.userMarker = L.marker([latitude, longitude], { icon, zIndexOffset: 1000 }).addTo(this.map);

    const popupHtml = `
      <div class="p-1.5 font-['Be_Vietnam_Pro'] text-[12px] max-w-[220px]">
        <div class="flex items-center gap-1.5 text-blue-600 font-bold">
          <span class="w-2 h-2 rounded-full bg-blue-600 animate-pulse"></span>
          <span>Vị trí hiện tại của bạn</span>
        </div>
        <p class="text-slate-500 text-[11px] mt-1">Tọa độ GPS thiết bị (±${Math.round(accuracy || 0)}m)</p>
        <p class="text-slate-400 text-[10px] mt-0.5 italic">Không phải trạm dừng xe buýt</p>
      </div>
    `;
    this.userMarker.bindPopup(popupHtml);
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
            this.renderUserLocationMarker(latitude, longitude, accuracy);

            // Context-aware Viewport: Keep route context while showing user location
            if (this.routeLine) {
              const routeBounds = this.routeLine.getBounds();
              // Check if user location is within reasonable Da Nang / Quang Nam region
              if (latitude >= 15.2 && latitude <= 16.5 && longitude >= 107.8 && longitude <= 108.8) {
                const combinedBounds = L.latLngBounds(routeBounds).extend([latitude, longitude]);
                this.map.fitBounds(combinedBounds, { padding: [40, 40], maxZoom: 15 });
              } else {
                this.map.fitBounds(routeBounds, { padding: [30, 30] });
              }
            } else if (this.currentRoute) {
              const stops = (this.currentRoute.stops?.[this.currentDirection] || []).filter(
                s => s && typeof s.lat === 'number' && typeof s.lng === 'number' && !isNaN(s.lat) && !isNaN(s.lng)
              );
              if (stops.length > 0) {
                const stopBounds = L.latLngBounds(stops.map(s => [s.lat, s.lng]));
                if (latitude >= 15.2 && latitude <= 16.5 && longitude >= 107.8 && longitude <= 108.8) {
                  const combined = L.latLngBounds(stopBounds).extend([latitude, longitude]);
                  this.map.fitBounds(combined, { padding: [40, 40], maxZoom: 15 });
                } else {
                  this.map.fitBounds(stopBounds, { padding: [30, 30] });
                }
              } else {
                this.map.setView([latitude, longitude], Math.max(this.map.getZoom(), 14));
              }
            } else {
              this.map.setView([latitude, longitude], Math.max(this.map.getZoom(), 14));
            }
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
    if (this.pinMarker && this.map) {
      this.map.removeLayer(this.pinMarker);
      this.pinMarker = null;
    }
    this.clearTripLayers();
    this.removeInfoOverlay();
  }

  enableMapPinSelection(onPinSelected) {
    if (!this.map) return;
    this.isPinSelectionMode = true;
    this.onPinSelectedCallback = onPinSelected;

    this.showInfoOverlay('Nhấp vào vị trí bất kỳ trên bản đồ để ghim điểm.');

    if (!this._mapPinClickHandler) {
      this._mapPinClickHandler = (e) => {
        if (!this.isPinSelectionMode) return;
        const { lat, lng } = e.latlng;
        this.renderMapPinMarker(lat, lng);
        this.removeInfoOverlay();
        this.isPinSelectionMode = false;
        if (typeof this.onPinSelectedCallback === 'function') {
          this.onPinSelectedCallback({ lat, lng });
        }
      };
      this.map.on('click', this._mapPinClickHandler);
    }
  }

  disableMapPinSelection() {
    this.isPinSelectionMode = false;
    this.removeInfoOverlay();
  }

  renderMapPinMarker(lat, lng) {
    if (!this.map) return;
    if (this.pinMarker) {
      this.map.removeLayer(this.pinMarker);
      this.pinMarker = null;
    }
    const pinHtml = `
      <div class="relative flex items-center justify-center">
        <span class="absolute w-8 h-8 rounded-full bg-emerald-500 opacity-40 animate-ping"></span>
        <div class="w-7 h-7 rounded-full bg-emerald-700 ring-4 ring-white shadow-lg flex items-center justify-center text-white font-bold text-[12px]">
          📍
        </div>
      </div>
    `;
    const icon = L.divIcon({ html: pinHtml, className: 'map-pin-icon', iconSize: [28, 28], iconAnchor: [14, 28] });
    this.pinMarker = L.marker([lat, lng], { icon, zIndexOffset: 2500 }).addTo(this.map);
  }

  clearTripLayers() {
    if (this.tripPolylines && Array.isArray(this.tripPolylines)) {
      this.tripPolylines.forEach(layer => {
        if (this.map && layer) this.map.removeLayer(layer);
      });
    }
    this.tripPolylines = [];
  }

  renderTrip(trip) {
    if (!this.map || !trip || !Array.isArray(trip.legs)) return;
    this.clear();
    this.clearTripLayers();

    const allPoints = [];

    // Render each leg
    trip.legs.forEach((leg, legIdx) => {
      if (leg.type === 'walking') {
        if (Array.isArray(leg.fromCoords) && Array.isArray(leg.toCoords)) {
          allPoints.push(leg.fromCoords);
          allPoints.push(leg.toCoords);

          // Dashed gray line indicating estimated walking (straight line reference, not road geometry)
          const walkLine = L.polyline([leg.fromCoords, leg.toCoords], {
            color: '#64748b',
            weight: 3,
            dashArray: '6, 8',
            opacity: 0.8
          }).addTo(this.map);
          walkLine.bindPopup(`
            <div class="p-1 font-['Be_Vietnam_Pro'] text-[12px]">
              <span class="font-bold text-slate-700">Đoạn đi bộ ước tính</span>
              <p class="text-slate-500 text-[11px] mt-0.5">${leg.summary || 'Khoảng cách ước tính'}</p>
              <p class="text-slate-400 text-[10px] mt-0.5 italic">Đường thẳng tham khảo, không phải lộ trình đường bộ thực tế</p>
            </div>
          `);
          this.tripPolylines.push(walkLine);
        }
      } else if (leg.type === 'transit') {
        const routeColor = legIdx === 1 ? '#059669' : '#2563eb';
        if (Array.isArray(leg.geometry) && leg.geometry.length > 1) {
          leg.geometry.forEach(p => allPoints.push(p));
          const busLine = L.polyline(leg.geometry, {
            color: routeColor,
            weight: 5,
            opacity: 0.9,
            lineCap: 'round',
            lineJoin: 'round'
          }).addTo(this.map);
          busLine.bindPopup(`
            <div class="p-1 font-['Be_Vietnam_Pro'] text-[12px]">
              <span class="font-bold text-slate-900">Tuyến ${leg.routeNumber || ''}</span>
              <p class="text-slate-600 text-[11px] mt-0.5">${leg.routeName || ''}</p>
              <p class="text-slate-400 text-[10px] mt-0.5">${leg.stopsCount || 0} trạm dừng (~${leg.durationMinutes || 0} phút)</p>
            </div>
          `);
          this.tripPolylines.push(busLine);
        } else {
          // If geometry missing for transit leg
          if (leg.boardingStop?.lat && leg.alightingStop?.lat) {
            allPoints.push([leg.boardingStop.lat, leg.boardingStop.lng]);
            allPoints.push([leg.alightingStop.lat, leg.alightingStop.lng]);
          }
        }
      }
    });

    // Render distinct Origin (A) and Destination (B) markers
    const originLeg = trip.legs[0];
    const destLeg = trip.legs[trip.legs.length - 1];

    if (originLeg && Array.isArray(originLeg.fromCoords)) {
      const origHtml = `
        <div class="relative flex items-center justify-center cursor-pointer">
          <div class="w-8 h-8 rounded-full bg-[#059669] text-white shadow-lg ring-4 ring-emerald-200 flex items-center justify-center font-extrabold text-[13px]">
            A
          </div>
        </div>
      `;
      const origIcon = L.divIcon({ html: origHtml, className: 'trip-origin-marker', iconSize: [32, 32], iconAnchor: [16, 16] });
      const origMarker = L.marker(originLeg.fromCoords, { icon: origIcon, zIndexOffset: 2000 }).addTo(this.markersLayer);
      origMarker.bindPopup(`
        <div class="p-1 font-['Be_Vietnam_Pro'] text-[12px]">
          <span class="font-bold text-emerald-700">Điểm đón (A)</span>
          <p class="text-slate-800 font-medium text-[12px] mt-0.5">${originLeg.fromLabel || 'Điểm đón'}</p>
        </div>
      `);
    }

    if (destLeg && Array.isArray(destLeg.toCoords)) {
      const destHtml = `
        <div class="relative flex items-center justify-center cursor-pointer">
          <div class="w-8 h-8 rounded-full bg-[#dc2626] text-white shadow-lg ring-4 ring-red-200 flex items-center justify-center font-extrabold text-[13px]">
            B
          </div>
        </div>
      `;
      const destIcon = L.divIcon({ html: destHtml, className: 'trip-dest-marker', iconSize: [32, 32], iconAnchor: [16, 16] });
      const destMarker = L.marker(destLeg.toCoords, { icon: destIcon, zIndexOffset: 2000 }).addTo(this.markersLayer);
      destMarker.bindPopup(`
        <div class="p-1 font-['Be_Vietnam_Pro'] text-[12px]">
          <span class="font-bold text-red-600">Điểm đến (B)</span>
          <p class="text-slate-800 font-medium text-[12px] mt-0.5">${destLeg.toLabel || 'Điểm đến'}</p>
        </div>
      `);
    }

    // Render transit boarding, transfer, alighting stops
    trip.legs.forEach((leg, idx) => {
      if (leg.type === 'transit') {
        const bStop = leg.boardingStop;
        const aStop = leg.alightingStop;

        if (bStop && typeof bStop.lat === 'number') {
          const bIcon = L.divIcon({
            html: `<div class="w-6 h-6 rounded-full bg-white text-emerald-700 border-2 border-emerald-600 shadow-md flex items-center justify-center font-bold text-[11px]">🚏</div>`,
            className: 'trip-stop-board',
            iconSize: [24, 24],
            iconAnchor: [12, 12]
          });
          const bMarker = L.marker([bStop.lat, bStop.lng], { icon: bIcon, zIndexOffset: 1500 }).addTo(this.markersLayer);
          bMarker.bindPopup(`
            <div class="p-1 font-['Be_Vietnam_Pro'] text-[12px]">
              <span class="font-bold text-emerald-700">Lên xe: Tuyến ${leg.routeNumber || ''}</span>
              <p class="text-slate-800 font-medium text-[12px] mt-0.5">${bStop.name || 'Trạm đón'}</p>
            </div>
          `);
        }

        if (aStop && typeof aStop.lat === 'number') {
          const isTransfer = idx < trip.legs.length - 2;
          const aIcon = L.divIcon({
            html: `<div class="w-6 h-6 rounded-full ${isTransfer ? 'bg-amber-500 text-white' : 'bg-white text-red-600 border-2 border-red-500'} shadow-md flex items-center justify-center font-bold text-[11px]">${isTransfer ? '🔄' : '🚏'}</div>`,
            className: isTransfer ? 'trip-stop-transfer' : 'trip-stop-alight',
            iconSize: [24, 24],
            iconAnchor: [12, 12]
          });
          const aMarker = L.marker([aStop.lat, aStop.lng], { icon: aIcon, zIndexOffset: 1500 }).addTo(this.markersLayer);
          aMarker.bindPopup(`
            <div class="p-1 font-['Be_Vietnam_Pro'] text-[12px]">
              <span class="font-bold ${isTransfer ? 'text-amber-600' : 'text-red-600'}">${isTransfer ? 'Trạm chuyển tuyến' : 'Xuống xe'}</span>
              <p class="text-slate-800 font-medium text-[12px] mt-0.5">${aStop.name || 'Trạm xuống'}</p>
            </div>
          `);
        }
      }
    });

    // Fit map bounds to trip points
    if (allPoints.length > 1) {
      const bounds = L.latLngBounds(allPoints);
      this.map.fitBounds(bounds, { padding: [40, 40] });
    } else if (allPoints.length === 1) {
      this.map.setView(allPoints[0], 14);
    }
  }
}

window.mapService = new MapService();
