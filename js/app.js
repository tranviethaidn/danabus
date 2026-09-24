/**
 * Danabus PWA Application Controller
 * Handles View Routing, UI State, Event Listeners, and Data Binding
 */

class DanabusApp {
  constructor() {
    this.currentView = 'home';
    this.viewHistory = ['home'];
    this.selectedRoute = null;
    this.currentDirection = 'outbound'; // 'outbound' | 'inbound'
    this.pickerTarget = 'destination'; // 'origin' | 'destination'
    this.pickerActiveTab = 'popular';  // 'popular' | 'stops'
    this.currentFilter = 'all';
    this.countdownInterval = null;
    this.userLocation = null;
  }

  async init() {
    console.log('[DanabusApp] Initializing app...');
    await window.busService.init();

    this.bindEvents();
    this.renderHome();
    this.renderRoutesList();
    this.startSpotlightTicker();
    console.log('[DanabusApp] Ready!');
  }

  // =========================================================================
  // VIEW ROUTING
  // =========================================================================
  navigateTo(viewId, pushHistory = true) {
    if (pushHistory && this.currentView !== viewId) {
      this.viewHistory.push(viewId);
    }
    this.currentView = viewId;

    // Toggle active views
    document.querySelectorAll('.view-screen').forEach(el => {
      el.classList.remove('active');
    });

    const targetEl = document.getElementById(`view-${viewId}`);
    if (targetEl) {
      targetEl.classList.add('active');
      window.scrollTo(0, 0);
    }

    // Update Header state
    const brandHeader = document.getElementById('header-brand');
    const subHeader = document.getElementById('header-sub');
    const subTitle = document.getElementById('header-sub-title');
    const subDesc = document.getElementById('header-sub-desc');

    if (viewId === 'home') {
      brandHeader.classList.remove('hidden');
      brandHeader.classList.add('flex');
      subHeader.classList.add('hidden');
      subHeader.classList.remove('flex');
    } else {
      brandHeader.classList.add('hidden');
      brandHeader.classList.remove('flex');
      subHeader.classList.remove('hidden');
      subHeader.classList.add('flex');

      if (viewId === 'routes') {
        subTitle.textContent = 'Danh mục tuyến xe';
        subDesc.textContent = '23 tuyến buýt tại Đà Nẵng';
      } else if (viewId === 'route-detail') {
        subTitle.textContent = `Tuyến ${this.selectedRoute?.routeNumber || '02'}`;
        subDesc.textContent = this.selectedRoute?.shortName || 'Chi tiết lộ trình';
      } else if (viewId === 'map') {
        subTitle.textContent = `Bản đồ Tuyến ${this.selectedRoute?.routeNumber || '02'}`;
        subDesc.textContent = 'Định vị GPS trực tiếp';
      } else if (viewId === 'trip-results') {
        subTitle.textContent = 'Kết quả tìm chuyến';
        subDesc.textContent = 'Lựa chọn chuyến xe phù hợp';
      }
    }

    // Update Bottom Nav Tab Highlights
    document.querySelectorAll('.nav-tab').forEach(tab => {
      const tabView = tab.getAttribute('data-view');
      if (tabView === viewId || (viewId === 'home' && tabView === 'home') || (viewId === 'routes' && tabView === 'routes')) {
        tab.classList.add('active', 'text-emerald-600');
        tab.classList.remove('text-slate-500');
      } else {
        tab.classList.remove('active', 'text-emerald-600');
        tab.classList.add('text-slate-500');
      }
    });

    // Special view triggers
    if (viewId === 'map' && this.selectedRoute) {
      if (this.mapInitTimeout) {
        clearTimeout(this.mapInitTimeout);
      }
      this.mapInitTimeout = setTimeout(() => {
        window.mapService.init('map-container');
        window.mapService.renderRoute(this.selectedRoute, this.currentDirection);
      }, 50);
    }
  }

  goBack() {
    if (this.viewHistory.length > 1) {
      this.viewHistory.pop(); // pop current
      const prevView = this.viewHistory[this.viewHistory.length - 1];
      this.navigateTo(prevView, false);
    } else {
      this.navigateTo('home', false);
    }
  }

  // =========================================================================
  // VIEW 1: HOME SCREEN
  // =========================================================================
  renderHome() {
    // Render Popular Destination Chips
    const chipsContainer = document.getElementById('home-destination-chips');
    if (!chipsContainer) return;

    const popularDests = window.busService.getPopularDestinations().slice(0, 5);
    chipsContainer.innerHTML = popularDests.map(d => `
      <button type="button" class="home-dest-chip px-3.5 py-2 rounded-full bg-white border border-slate-200/80 hover:border-emerald-500 hover:text-emerald-700 text-slate-700 text-[13px] font-medium flex items-center gap-1.5 shadow-xs active:scale-95 transition-all" data-name="${d.name}">
        ${window.renderIcon(d.icon, 'w-4 h-4 text-emerald-600')}
        <span>${d.name}</span>
      </button>
    `).join('');

    chipsContainer.querySelectorAll('.home-dest-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        const destName = btn.getAttribute('data-name');
        document.getElementById('home-destination-input').value = destName;
      });
    });
  }

  startSpotlightTicker() {
    const route02 = window.busService.getRouteById('02');
    const spotlightEl = document.getElementById('spotlight-countdown');
    if (!route02 || !spotlightEl) return;

    const updateTime = () => {
      const dep = window.busService.calculateNextDeparture(route02);
      spotlightEl.textContent = `Chuyến tới: ${dep.minutesLeft} phút (${dep.timeStr})`;
    };

    updateTime();
    if (this.countdownInterval) clearInterval(this.countdownInterval);
    this.countdownInterval = setInterval(updateTime, 30000);
  }

  // =========================================================================
  // VIEW 2: ALL ROUTES DIRECTORY
  // =========================================================================
  renderRoutesList() {
    const container = document.getElementById('routes-list-container');
    const countLabel = document.getElementById('route-count-label');
    if (!container) return;

    const query = document.getElementById('route-search-input')?.value || '';
    const routes = window.busService.getAllRoutes(this.currentFilter, query);

    if (countLabel) {
      countLabel.textContent = `${routes.length} tuyến xe`;
    }

    if (routes.length === 0) {
      container.innerHTML = `
        <div class="py-12 text-center flex flex-col items-center justify-center">
          <div class="w-14 h-14 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mb-3">
            ${window.renderIcon('search_off', 'w-7 h-7 text-slate-400')}
          </div>
          <p class="font-bold text-[15px] text-slate-800">Không tìm thấy tuyến phù hợp</p>
          <p class="text-[12px] text-slate-500 mt-1 max-w-xs">Thử tìm theo số hiệu khác như 02, 05, LK01 hoặc tên đường Lê Duẩn, Nguyễn Văn Linh...</p>
        </div>
      `;
      return;
    }

    container.innerHTML = routes.map(r => {
      const isSubsidized = r.category === 'subsidized';
      const isElectric = (r.vehicleInfo && r.vehicleInfo.includes('Điện')) || ['02', '03', '09', '13', '14', '21'].includes(r.id);
      const isSuspended = r.status === 'suspended';

      const fareText = isSubsidized ? '8.000đ' : (r.fares?.singleTicket ? `${r.fares.singleTicket.toLocaleString('vi-VN')}đ` : '8k - 30k');
      const badgeColor = isSuspended ? 'bg-slate-400' : (isSubsidized ? 'bg-emerald-600' : 'bg-teal-700');

      return `
        <div class="route-card bg-white rounded-2xl p-3.5 shadow-xs border border-slate-100 flex items-center justify-between active:scale-[0.99] transition-all cursor-pointer hover:border-emerald-200" data-route-id="${r.id}">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-11 h-11 rounded-xl ${badgeColor} text-white flex items-center justify-center font-extrabold text-[16px] shrink-0 shadow-sm">
              ${r.routeNumber}
            </div>
            <div class="flex flex-col min-w-0">
              <div class="flex items-center gap-1.5">
                <span class="font-bold text-[14px] text-slate-900 truncate">${r.shortName}</span>
                ${isSuspended ? '<span class="px-1.5 py-0.5 rounded bg-rose-50 text-rose-600 font-bold text-[10px]">Tạm dừng</span>' : ''}
              </div>
              <div class="flex items-center gap-2 mt-1 text-[11px] text-slate-500">
                <span class="font-semibold text-emerald-700">${fareText}</span>
                <span>•</span>
                <span>${r.frequency?.peakMinutes ? `${r.frequency.peakMinutes}p/chuyến` : 'Định kỳ'}</span>
                <span>•</span>
                ${isElectric ? `<span class="text-emerald-700 font-medium flex items-center gap-0.5">${window.renderIcon('bolt', 'w-3 h-3 text-emerald-600')}Xe điện</span>` : `<span>${r.operatingHours?.start || '05:30'} - ${r.operatingHours?.end || '19:00'}</span>`}
              </div>
            </div>
          </div>
          ${window.renderIcon('chevron_right', 'w-5 h-5 text-slate-300 ml-1')}
        </div>
      `;
    }).join('');

    container.querySelectorAll('.route-card').forEach(card => {
      card.addEventListener('click', () => {
        const rid = card.getAttribute('data-route-id');
        this.openRouteDetail(rid);
      });
    });
  }

  // =========================================================================
  // VIEW 3: ROUTE DETAIL
  // =========================================================================
  openRouteDetail(routeId) {
    const route = window.busService.getRouteById(routeId);
    if (!route) return;

    this.selectedRoute = route;
    this.currentDirection = 'outbound';

    // Header info
    document.getElementById('detail-route-title').textContent = `${route.routeNumber}: ${route.shortName}`;
    document.getElementById('detail-route-operator').textContent = route.operator || 'Trung tâm Quản lý Vận tải Hành khách Công cộng Đà Nẵng';
    
    // Badges
    const catBadge = document.getElementById('detail-badge-category');
    const statusBadge = document.getElementById('detail-badge-status');

    if (route.status === 'suspended') {
      statusBadge.className = 'px-2.5 py-0.5 rounded-full bg-rose-400 text-rose-950 font-bold text-[11px]';
      statusBadge.textContent = 'Tạm dừng hoạt động';
    } else {
      statusBadge.className = 'px-2.5 py-0.5 rounded-full bg-emerald-400 text-emerald-950 font-bold text-[11px] flex items-center gap-1';
      statusBadge.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-emerald-950 animate-pulse"></span> Đang hoạt động';
    }

    if (route.category === 'subsidized') {
      catBadge.textContent = 'Xe buýt trợ giá';
    } else if (route.category === 'interprovincial') {
      catBadge.textContent = 'Buýt liền kề / Liên tỉnh';
    } else if (route.category === 'tourist') {
      catBadge.textContent = 'Tuyến du lịch';
    } else {
      catBadge.textContent = 'Buýt không trợ giá';
    }

    // Direction labels
    this.updateDirectionUI();

    // Stats
    document.getElementById('detail-stat-hours').textContent = `${route.operatingHours?.start || '05:30'} - ${route.operatingHours?.end || '19:00'}`;
    document.getElementById('detail-stat-freq').textContent = route.frequency?.peakMinutes ? `${route.frequency.peakMinutes}-${route.frequency.offPeakMinutes || 30} phút` : '15-30 phút';
    document.getElementById('detail-stat-distance').textContent = route.distanceKm?.average ? `${route.distanceKm.average} km` : '20+ km';

    // Fares
    const fareSingle = route.fares?.singleTicket ? `${route.fares.singleTicket.toLocaleString('vi-VN')}đ` : (route.category === 'subsidized' ? '8.000đ' : '8k - 30k');
    document.getElementById('detail-fare-single').textContent = `Vé lượt: ${fareSingle}`;
    document.getElementById('detail-fare-tag').textContent = route.category === 'subsidized' ? 'Trợ giá 8k' : 'Giá chuẩn';

    // PDF Link
    const pdfContainer = document.getElementById('detail-pdf-container');
    const pdfLink = document.getElementById('detail-pdf-link');
    if (route.pdfUrls && route.pdfUrls.length > 0) {
      pdfContainer.classList.remove('hidden');
      pdfLink.href = route.pdfUrls[0];
    } else {
      pdfContainer.classList.add('hidden');
    }

    // Render Stops Timeline
    this.renderStopsTimeline();

    this.navigateTo('route-detail');
  }

  updateDirectionUI() {
    if (!this.selectedRoute) return;
    const r = this.selectedRoute;
    const orig = r.terminals?.origin || 'Đầu tuyến';
    const dest = r.terminals?.destination || 'Cuối tuyến';

    const outBtn = document.getElementById('btn-dir-outbound');
    const inBtn = document.getElementById('btn-dir-inbound');
    const outLabel = document.getElementById('label-dir-outbound');
    const inLabel = document.getElementById('label-dir-inbound');

    outLabel.textContent = `Về ${dest.replace(/.*-/, '').trim() || dest}`;
    inLabel.textContent = `Về ${orig.replace(/.*-/, '').trim() || orig}`;

    if (this.currentDirection === 'outbound') {
      outBtn.className = 'flex-1 py-2 px-3 rounded-full bg-emerald-600 text-white font-semibold text-[13px] shadow-sm transition-all flex items-center justify-center gap-1.5 active:scale-95 truncate';
      inBtn.className = 'flex-1 py-2 px-3 rounded-full text-slate-600 hover:text-slate-900 font-medium text-[13px] transition-all flex items-center justify-center gap-1.5 active:scale-95 truncate';
    } else {
      inBtn.className = 'flex-1 py-2 px-3 rounded-full bg-emerald-600 text-white font-semibold text-[13px] shadow-sm transition-all flex items-center justify-center gap-1.5 active:scale-95 truncate';
      outBtn.className = 'flex-1 py-2 px-3 rounded-full text-slate-600 hover:text-slate-900 font-medium text-[13px] transition-all flex items-center justify-center gap-1.5 active:scale-95 truncate';
    }
  }

  renderStopsTimeline() {
    if (!this.selectedRoute) return;
    const r = this.selectedRoute;
    const container = document.getElementById('detail-stops-timeline');
    const badgeCount = document.getElementById('detail-stop-count-badge');
    if (!container) return;

    const stops = r.stops?.[this.currentDirection] || [];
    const streets = r.routePaths?.[this.currentDirection]?.streets || [];

    // If explicit stops table exists:
    if (stops.length > 0) {
      if (badgeCount) badgeCount.textContent = `${stops.length} trạm toàn tuyến`;

      container.innerHTML = `
        <div class="absolute left-[13px] top-3 bottom-3 w-[2px] bg-slate-200"></div>
        <div class="absolute left-[13px] top-3 h-32 w-[2px] bg-emerald-600"></div>
        ${stops.map((s, idx) => {
          const isStart = idx === 0;
          const isEnd = idx === stops.length - 1;

          return `
            <div class="relative flex items-start gap-3.5 pb-5">
              <div class="z-10 w-7 h-7 rounded-full ${isStart || isEnd ? 'bg-emerald-600 text-white ring-4 ring-white shadow-sm' : 'bg-white border-2 border-slate-300 text-slate-600'} flex items-center justify-center shrink-0">
                ${isStart ? window.renderIcon('trip_origin', 'w-3.5 h-3.5 text-white') : (isEnd ? window.renderIcon('location_on', 'w-3.5 h-3.5 text-white') : `<span class="text-[11px] font-bold">${idx + 1}</span>`)}
              </div>
              <div class="flex-1 min-w-0 pt-0.5">
                <div class="flex items-center justify-between">
                  <span class="text-[13px] text-slate-900 font-bold truncate">${s.name}</span>
                  ${isStart ? '<span class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-bold">Điểm đầu</span>' : (isEnd ? '<span class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-bold">Điểm cuối</span>' : '')}
                </div>
                <p class="text-[11px] text-slate-400 truncate mt-0.5">${s.street ? `Đường ${s.street}` : 'Trạm dừng xe buýt'}</p>
              </div>
            </div>
          `;
        }).join('')}
      `;
    } else {
      // If table doesn't exist, render sequential streets waypoints from route narrative!
      if (badgeCount) badgeCount.textContent = `${streets.length} trục đường chính`;

      container.innerHTML = `
        <div class="absolute left-[13px] top-3 bottom-3 w-[2px] bg-slate-200"></div>
        <div class="absolute left-[13px] top-3 h-32 w-[2px] bg-emerald-600"></div>
        ${streets.map((st, idx) => {
          const isStart = idx === 0;
          const isEnd = idx === streets.length - 1;

          return `
            <div class="relative flex items-start gap-3.5 pb-4">
              <div class="z-10 w-7 h-7 rounded-full ${isStart || isEnd ? 'bg-emerald-600 text-white ring-4 ring-white shadow-sm' : 'bg-white border-2 border-slate-300 text-slate-600'} flex items-center justify-center shrink-0">
                <span class="text-[11px] font-bold">${idx + 1}</span>
              </div>
              <div class="flex-1 min-w-0 pt-0.5">
                <p class="text-[13px] font-semibold text-slate-800">${st}</p>
              </div>
            </div>
          `;
        }).join('')}
      `;
    }
  }

  // =========================================================================
  // VIEW 4: MAP & GPS ROUTE
  // =========================================================================
  openMapView(routeId = null) {
    if (routeId) {
      this.selectedRoute = window.busService.getRouteById(routeId);
    }
    if (!this.selectedRoute) {
      this.selectedRoute = window.busService.getRouteById('02');
    }

    const r = this.selectedRoute;
    document.getElementById('map-route-badge').textContent = r.routeNumber;
    document.getElementById('map-route-title').textContent = r.shortName;
    document.getElementById('map-route-dir').textContent = this.currentDirection === 'outbound' ? `Chiều đi: Về ${r.terminals?.destination || 'Cuối tuyến'}` : `Chiều về: Về ${r.terminals?.origin || 'Đầu tuyến'}`;

    this.navigateTo('map');
  }

  // =========================================================================
  // VIEW 5: TRIP RESULTS
  // =========================================================================
  showTripResults(originText, destinationText) {
    // Find matching routes
    let matchedRoutes = window.busService.findRoutesBetween(originText, destinationText);
    if (matchedRoutes.length === 0) {
      // Fallback to route 02 if it's Hoi An / Cua Dai or route 05 for general
      matchedRoutes = [window.busService.getRouteById('02') || window.busService.routes[0]];
    }

    const route = matchedRoutes[0];
    this.selectedRoute = route;

    document.getElementById('trip-header-title').textContent = `${originText || 'Bến xe TT'} ➔ ${destinationText || 'Hội An'}`;
    document.getElementById('trip-route-badge').textContent = `TUYẾN ${route.routeNumber}`;
    document.getElementById('trip-stat-km').textContent = route.distanceKm?.average ? `${route.distanceKm.average} km` : '35 km';
    document.getElementById('trip-stat-stops').textContent = `${route.stops?.outbound?.length || 29} trạm dừng`;

    const dep = window.busService.calculateNextDeparture(route);
    document.getElementById('trip-countdown-time').textContent = dep.timeStr;
    document.getElementById('trip-countdown-timer').textContent = `Còn ${dep.minutesLeft} phút`;

    const singleFare = route.fares?.singleTicket ? `${route.fares.singleTicket.toLocaleString('vi-VN')}đ` : '30.000đ';
    document.getElementById('trip-fare-value').textContent = singleFare;
    document.getElementById('trip-freq-value').textContent = `${route.frequency?.peakMinutes || 15}-${route.frequency?.offPeakMinutes || 30}p`;

    // Next trip calculation
    const laterM = parseInt(dep.timeStr.split(':')[1]) + (route.frequency?.peakMinutes || 20);
    const laterH = parseInt(dep.timeStr.split(':')[0]) + Math.floor(laterM / 60);
    const laterStr = `${String(laterH % 24).padStart(2, '0')}:${String(laterM % 60).padStart(2, '0')}`;
    document.getElementById('trip-later-time').textContent = `Chuyến sau: ${laterStr}`;
    document.getElementById('trip-later-diff').textContent = `(sau ${route.frequency?.peakMinutes || 20} phút)`;

    this.navigateTo('trip-results');
  }

  // =========================================================================
  // LOCATION PICKER MODAL
  // =========================================================================
  openLocationPicker(target = 'destination') {
    this.pickerTarget = target;
    const modal = document.getElementById('modal-location-picker');
    const title = document.getElementById('modal-picker-title');
    const input = document.getElementById('picker-search-input');

    if (title) title.textContent = target === 'origin' ? 'Chọn Điểm Đón' : 'Chọn Điểm Đến';
    if (input) {
      input.value = '';
      input.placeholder = target === 'origin' ? 'Tìm điểm đón, trạm buýt...' : 'Tìm điểm đến (Hội An, Cầu Rồng, Bà Nà...)';
    }

    this.pickerActiveTab = 'popular';
    this.renderPickerResults();

    modal.classList.remove('modal-hidden');
    setTimeout(() => input?.focus(), 150);
  }

  closeLocationPicker() {
    const modal = document.getElementById('modal-location-picker');
    modal.classList.add('modal-hidden');
  }

  renderPickerResults(query = '') {
    const container = document.getElementById('picker-results-container');
    if (!container) return;

    if (this.pickerActiveTab === 'popular' && !query) {
      const popular = window.busService.getPopularDestinations();
      container.innerHTML = popular.map(p => `
        <div class="picker-item bg-white rounded-xl p-3 shadow-xs border border-slate-100 active:bg-slate-50 flex items-center justify-between cursor-pointer" data-name="${p.name}">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center shrink-0">
              ${window.renderIcon(p.icon, 'w-5 h-5 text-emerald-600')}
            </div>
            <div class="min-w-0">
              <h4 class="font-bold text-[13px] text-slate-900 truncate">${p.name}</h4>
              <p class="text-[11px] text-slate-400 truncate mt-0.5">${p.subtext}</p>
              <div class="flex items-center gap-1 mt-1">
                <span class="text-[10px] text-slate-400">Tuyến qua:</span>
                ${p.routes.map(rn => `<span class="bg-emerald-600 text-white text-[9px] font-bold px-1.5 py-0.2 rounded">${rn}</span>`).join('')}
              </div>
            </div>
          </div>
          ${window.renderIcon('chevron_right', 'w-4 h-4 text-slate-300')}
        </div>
      `).join('');
    } else {
      const stops = window.busService.searchStops(query);
      container.innerHTML = stops.map(s => `
        <div class="picker-item bg-white rounded-xl p-3 shadow-xs border border-slate-100 active:bg-slate-50 flex items-center justify-between cursor-pointer" data-name="${s.name}">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-9 h-9 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center shrink-0">
              ${window.renderIcon('directions_bus', 'w-4 h-4 text-slate-600')}
            </div>
            <div class="min-w-0">
              <h4 class="font-bold text-[13px] text-slate-900 truncate">${s.name}</h4>
              <p class="text-[11px] text-slate-400 truncate mt-0.5">${s.street ? `Đường ${s.street}` : 'Trạm xe buýt Đà Nẵng'}</p>
              <div class="flex items-center gap-1 mt-1 flex-wrap">
                <span class="text-[10px] text-slate-400">Tuyến:</span>
                ${(s.routes || []).map(r => `<span class="bg-emerald-600 text-white text-[9px] font-bold px-1.5 py-0.2 rounded">${r.routeNumber}</span>`).join('')}
              </div>
            </div>
          </div>
          ${window.renderIcon('chevron_right', 'w-4 h-4 text-slate-300')}
        </div>
      `).join('');
    }

    container.querySelectorAll('.picker-item').forEach(item => {
      item.addEventListener('click', () => {
        const locName = item.getAttribute('data-name');
        this.selectLocation(locName);
      });
    });
  }

  selectLocation(name) {
    if (this.pickerTarget === 'origin') {
      document.getElementById('home-origin-display').textContent = name;
    } else {
      document.getElementById('home-destination-input').value = name;
    }
    this.closeLocationPicker();
  }

  // =========================================================================
  // EVENT BINDINGS
  // =========================================================================
  bindEvents() {
    // Header Back
    document.getElementById('btn-header-back')?.addEventListener('click', () => this.goBack());

    // Bottom Navigation
    document.querySelectorAll('.nav-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        const view = tab.getAttribute('data-view');
        if (view) this.navigateTo(view);
      });
    });

    // Home Swap Locations
    document.getElementById('btn-swap-locations')?.addEventListener('click', () => {
      const origEl = document.getElementById('home-origin-display');
      const destEl = document.getElementById('home-destination-input');
      const origVal = origEl.textContent.trim();
      const destVal = destEl.value.trim();

      if (origVal === 'Chọn điểm đón' && !destVal) return;

      origEl.textContent = destVal || 'Chọn điểm đón';
      destEl.value = (origVal === 'Chọn điểm đón' || origVal === 'Vị trí hiện tại') ? '' : origVal;
    });

    // Home Voice Search Simulation
    document.getElementById('home-voice-btn')?.addEventListener('click', () => {
      const input = document.getElementById('home-destination-input');
      const origPlaceholder = input.placeholder;
      input.placeholder = "Đang lắng nghe...";
      setTimeout(() => {
        input.value = "Chùa Cầu, Phố cổ Hội An";
        input.placeholder = origPlaceholder;
      }, 1200);
    });

    // Home Search CTA
    document.getElementById('btn-home-search')?.addEventListener('click', () => {
      const origText = document.getElementById('home-origin-display').textContent.trim();
      const orig = (origText === 'Chọn điểm đón' || origText === 'Vị trí hiện tại') ? 'Bến xe TT' : origText;
      const dest = document.getElementById('home-destination-input').value.trim() || 'Phố cổ Hội An';
      this.showTripResults(orig, dest);
    });

    // Home Spotlight Card Click
    document.getElementById('home-spotlight-card')?.addEventListener('click', () => {
      this.openRouteDetail('02');
    });

    // Routes Screen Search Input
    const routeSearchInput = document.getElementById('route-search-input');
    const clearBtn = document.getElementById('btn-clear-route-search');
    routeSearchInput?.addEventListener('input', e => {
      const val = e.target.value;
      clearBtn?.classList.toggle('hidden', val.length === 0);
      this.renderRoutesList();
    });

    clearBtn?.addEventListener('click', () => {
      routeSearchInput.value = '';
      clearBtn.classList.add('hidden');
      this.renderRoutesList();
      routeSearchInput.focus();
    });

    // Route Category Filter Chips
    document.querySelectorAll('#route-filter-container .filter-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#route-filter-container .filter-chip').forEach(b => {
          b.className = 'filter-chip px-3.5 py-1.5 rounded-full text-[13px] font-medium whitespace-nowrap bg-white text-slate-600 border border-slate-200 transition-all';
        });
        btn.className = 'filter-chip px-3.5 py-1.5 rounded-full text-[13px] font-semibold whitespace-nowrap bg-emerald-600 text-white shadow-sm transition-all';
        this.currentFilter = btn.getAttribute('data-filter') || 'all';
        this.renderRoutesList();
      });
    });

    // Route Detail Direction Toggle
    document.getElementById('btn-dir-outbound')?.addEventListener('click', () => {
      this.currentDirection = 'outbound';
      this.updateDirectionUI();
      this.renderStopsTimeline();
    });
    document.getElementById('btn-dir-inbound')?.addEventListener('click', () => {
      this.currentDirection = 'inbound';
      this.updateDirectionUI();
      this.renderStopsTimeline();
    });

    // Route Detail Mode GPS / Diagram
    document.getElementById('btn-mode-gps')?.addEventListener('click', () => {
      this.openMapView();
    });
    document.getElementById('btn-floating-map')?.addEventListener('click', () => {
      this.openMapView();
    });

    // Map screen events
    document.getElementById('btn-map-locate')?.addEventListener('click', async () => {
      const btn = document.getElementById('btn-map-locate');
      btn?.classList.add('animate-spin');
      const res = await window.mapService.locateUser();
      btn?.classList.remove('animate-spin');
      if (!res.success) {
        alert(res.error || 'Không thể lấy vị trí hiện tại.');
      } else {
        this.userLocation = res.coords;
      }
    });
    document.getElementById('btn-map-switch-dir')?.addEventListener('click', () => {
      this.currentDirection = this.currentDirection === 'outbound' ? 'inbound' : 'outbound';
      document.getElementById('map-route-dir').textContent = this.currentDirection === 'outbound' ? `Chiều đi: Về ${this.selectedRoute?.terminals?.destination || 'Cuối tuyến'}` : `Chiều về: Về ${this.selectedRoute?.terminals?.origin || 'Đầu tuyến'}`;
      window.mapService.renderRoute(this.selectedRoute, this.currentDirection);
    });

    // Location Picker Modal Events
    document.getElementById('btn-close-picker')?.addEventListener('click', () => this.closeLocationPicker());
    document.getElementById('btn-picker-current-location')?.addEventListener('click', async () => {
      const statusSpan = document.getElementById('picker-current-location-status');
      const origText = statusSpan ? statusSpan.textContent : '';
      if (statusSpan) statusSpan.textContent = 'Đang định vị...';

      const res = await window.mapService.locateUser();
      if (statusSpan) statusSpan.textContent = origText;

      if (res.success) {
        this.userLocation = res.coords;
        this.selectLocation('Vị trí hiện tại');
      } else {
        alert(`Không thể xác định vị trí GPS: ${res.error}`);
      }
    });

    const pickerSearchInput = document.getElementById('picker-search-input');
    pickerSearchInput?.addEventListener('input', e => {
      this.renderPickerResults(e.target.value);
    });

    document.getElementById('picker-tab-popular')?.addEventListener('click', () => {
      this.pickerActiveTab = 'popular';
      document.getElementById('picker-tab-popular').className = 'flex-1 py-1.5 rounded-full text-[12px] font-bold bg-emerald-600 text-white shadow-xs';
      document.getElementById('picker-tab-stops').className = 'flex-1 py-1.5 rounded-full text-[12px] font-medium text-slate-600 hover:text-slate-900 bg-slate-100';
      this.renderPickerResults(pickerSearchInput.value);
    });

    document.getElementById('picker-tab-stops')?.addEventListener('click', () => {
      this.pickerActiveTab = 'stops';
      document.getElementById('picker-tab-stops').className = 'flex-1 py-1.5 rounded-full text-[12px] font-bold bg-emerald-600 text-white shadow-xs';
      document.getElementById('picker-tab-popular').className = 'flex-1 py-1.5 rounded-full text-[12px] font-medium text-slate-600 hover:text-slate-900 bg-slate-100';
      this.renderPickerResults(pickerSearchInput.value);
    });

    // Trip Results CTA
    document.getElementById('btn-trip-view-route')?.addEventListener('click', () => {
      if (this.selectedRoute) {
        this.openRouteDetail(this.selectedRoute.id);
      }
    });

    document.getElementById('btn-remind-trip')?.addEventListener('click', () => {
      alert('Đã bật chuông thông báo chuyến xe khởi hành trước 10 phút!');
    });
  }
}

// Instantiate and start on DOM loaded
window.app = new DanabusApp();
document.addEventListener('DOMContentLoaded', () => {
  window.app.init();
});
