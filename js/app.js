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
    this.matchedDirection = null;       // matched direction from search
    this.lastSearchQuery = null;        // { originText, destinationText }
    this.pickerTarget = 'destination'; // 'origin' | 'destination'
    this.pickerActiveTab = 'popular';  // 'popular' | 'stops'
    this.currentFilter = 'all';
    this.countdownInterval = null;
    this.userLocation = null;
    this.originLocation = null;
    this.destinationLocation = null;
    this.currentPlannedTrip = null;
    this.currentPlannedTrips = [];
    this.loadState = 'idle';           // 'idle' | 'loading' | 'ready' | 'error'
    this.loadError = null;
    this.eventsBound = false;
    this._pickerRenderSeq = 0;
  }

  showSearchValidationError(message, errorType = null) {
    const errorEl = document.getElementById('home-search-error');
    const textEl = document.getElementById('home-search-error-text');
    if (errorEl && textEl) {
      textEl.textContent = message || 'Vui lòng kiểm tra lại điểm đón và điểm đến.';
      errorEl.classList.remove('hidden');
    } else {
      alert(message);
    }
  }

  clearSearchValidationError() {
    const errorEl = document.getElementById('home-search-error');
    if (errorEl) {
      errorEl.classList.add('hidden');
    }
  }

  showLoadingState() {
    this.loadState = 'loading';
    const loadingEl = document.getElementById('app-loading-state');
    if (loadingEl) {
      loadingEl.classList.remove('hidden');
      loadingEl.classList.add('flex');
    }
  }

  hideLoadingState() {
    const loadingEl = document.getElementById('app-loading-state');
    if (loadingEl) {
      loadingEl.classList.add('hidden');
      loadingEl.classList.remove('flex');
    }
  }

  showErrorState(err) {
    this.loadState = 'error';
    this.loadError = err;

    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
      this.countdownInterval = null;
    }

    // Fail-closed UI: hide view screens so no fake or incomplete data is displayed
    document.querySelectorAll('.view-screen').forEach(el => {
      el.classList.remove('active');
      el.classList.add('hidden');
    });

    const errorEl = document.getElementById('app-error-state');
    const descEl = document.getElementById('app-error-desc');
    if (errorEl) {
      errorEl.classList.remove('hidden');
      errorEl.classList.add('flex');
      if (descEl) {
        const isOffline = (typeof navigator !== 'undefined' && !navigator.onLine) ||
          (err && err.message && (err.message.includes('fetch') || err.message.includes('network') || err.message.includes('Failed')));
        descEl.textContent = isOffline
          ? 'Không thể kết nối mạng hoặc thiết bị đang ngoại tuyến. Vui lòng kiểm tra kết nối và thử lại.'
          : `Không thể tải danh mục xe buýt (${err?.message || 'Lỗi kết nối'}). Vui lòng thử lại.`;
      }
    }

    // Fail-closed counters and spotlight texts
    const countLabel = document.getElementById('route-count-label');
    if (countLabel) countLabel.textContent = 'Chưa có dữ liệu';
    const spotlightEl = document.getElementById('spotlight-countdown');
    if (spotlightEl) spotlightEl.textContent = 'Chưa có thông tin lịch';
    const spotlightFare = document.getElementById('spotlight-fare');
    if (spotlightFare) spotlightFare.textContent = 'Chưa có dữ liệu';
    const spotlightSchedule = document.getElementById('spotlight-schedule');
    if (spotlightSchedule) spotlightSchedule.textContent = 'Đang cập nhật';
  }

  hideErrorState() {
    this.loadState = 'ready';
    this.loadError = null;

    const errorEl = document.getElementById('app-error-state');
    if (errorEl) {
      errorEl.classList.add('hidden');
      errorEl.classList.remove('flex');
    }

    document.querySelectorAll('.view-screen').forEach(el => {
      el.classList.remove('hidden');
    });
    this.navigateTo(this.currentView || 'home', false);
  }

  async loadDataAndRender() {
    this.showLoadingState();
    try {
      await window.busService.init();
      this.hideLoadingState();
      this.hideErrorState();
      this.renderHome();
      this.renderRoutesList();
      this.startSpotlightTicker();
      console.log('[DanabusApp] Ready!');
    } catch (err) {
      console.error('[DanabusApp] Init failed due to data load error:', err);
      this.hideLoadingState();
      this.showErrorState(err);
    }
  }

  async retryLoad() {
    console.log('[DanabusApp] Retrying data load...');
    if (window.busService) {
      window.busService.isLoaded = false;
      window.busService.isLoading = false;
      window.busService.loadError = null;
    }
    await this.loadDataAndRender();
  }

  async init() {
    console.log('[DanabusApp] Initializing app...');
    if (!this.eventsBound) {
      this.bindEvents();
      this.eventsBound = true;
    }
    await this.loadDataAndRender();
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
        subDesc.textContent = 'Lộ trình & trạm dừng GPS';
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
    if (viewId === 'map') {
      if (this.mapInitTimeout) {
        clearTimeout(this.mapInitTimeout);
      }
      this.mapInitTimeout = setTimeout(() => {
        window.mapService.init('map-container');
        if (this.currentPlannedTrip) {
          window.mapService.renderTrip(this.currentPlannedTrip);
        } else if (this.selectedRoute) {
          window.mapService.renderRoute(this.selectedRoute, this.currentDirection);
        }
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
        this.clearSearchValidationError();
      });
    });
  }

  startSpotlightTicker() {
    const route02 = window.busService.getRouteById('02');
    const spotlightEl = document.getElementById('spotlight-countdown');
    const spotlightFareEl = document.getElementById('spotlight-fare');
    const spotlightScheduleEl = document.getElementById('spotlight-schedule');
    if (!route02 || !spotlightEl) return;

    if (spotlightFareEl) {
      spotlightFareEl.textContent = window.busService.formatRouteFare(route02);
    }

    if (spotlightScheduleEl) {
      const freqText = window.busService.formatRouteFrequency(route02);
      const hoursText = window.busService.formatRouteOperatingHours ? window.busService.formatRouteOperatingHours(route02) : 'Đang cập nhật';
      spotlightScheduleEl.textContent = `Tần suất ${freqText} • ${hoursText}`;
    }

    const updateTime = () => {
      const dep = window.busService.calculateNextDeparture(route02);
      if (dep.status === 'in_service') {
        if (dep.timeStr && dep.minutesUntilDeparture != null) {
          spotlightEl.textContent = `Theo lịch: Chuyến tới ${dep.timeStr} (sau ${dep.minutesUntilDeparture}p)`;
        } else {
          spotlightEl.textContent = `Theo lịch: Đang hoạt động (${window.busService.formatRouteFrequency(route02)})`;
        }
      } else if (dep.status === 'before_service') {
        if (dep.timeStr && dep.minutesUntilDeparture != null) {
          spotlightEl.textContent = `Theo lịch: Chuyến đầu ${dep.timeStr} (sau ${dep.minutesUntilDeparture}p)`;
        } else {
          spotlightEl.textContent = dep.message ? `Theo lịch: ${dep.message}` : 'Chưa đến giờ chạy theo lịch';
        }
      } else if (dep.status === 'next_day') {
        spotlightEl.textContent = `Theo lịch: Chuyến mai ${dep.timeStr} (sau ${dep.minutesUntilDeparture}p)`;
      } else if (dep.status === 'after_service') {
        spotlightEl.textContent = `Theo lịch: Hết chuyến hôm nay`;
      } else {
        spotlightEl.textContent = `Chưa có thông tin lịch`;
      }
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
      const isElectric = Boolean(r.vehicleInfo && r.vehicleInfo.toLowerCase().includes('điện'));
      const isSuspended = r.status === 'suspended';

      const fareText = window.busService.formatRouteFare(r);
      const badgeColor = isSuspended ? 'bg-slate-400' : (isSubsidized ? 'bg-emerald-600' : 'bg-teal-700');

      return `
        <div role="button" tabindex="0" aria-label="Tuyến ${r.routeNumber}: ${r.shortName}" class="route-card bg-white rounded-2xl p-3.5 shadow-xs border border-slate-100 flex items-center justify-between active:scale-[0.99] transition-all cursor-pointer hover:border-emerald-200" data-route-id="${r.id}">
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
                <span>${(() => {
                  const fText = window.busService.formatRouteFrequency ? window.busService.formatRouteFrequency(r, true) : 'Đang cập nhật';
                  if (fText === 'Đang cập nhật') return 'Đang cập nhật';
                  return fText.endsWith('p') ? `${fText}/chuyến` : fText;
                })()}</span>
                <span>•</span>
                ${isElectric ? `<span class="text-emerald-700 font-medium flex items-center gap-0.5">${window.renderIcon('bolt', 'w-3 h-3 text-emerald-600')}Xe điện</span>` : `<span>${(r.operatingHours?.start && r.operatingHours?.end) ? `${r.operatingHours.start} - ${r.operatingHours.end}` : 'Đang cập nhật'}</span>`}
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
  openRouteDetail(routeId, direction = 'outbound') {
    const route = window.busService.getRouteById(routeId);
    if (!route) return;

    this.selectedRoute = route;
    this.currentDirection = direction || 'outbound';

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
      statusBadge.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-emerald-950"></span> Đang hoạt động (theo lịch)';
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
    document.getElementById('detail-stat-hours').textContent = window.busService.formatRouteOperatingHours ? window.busService.formatRouteOperatingHours(route) : 'Đang cập nhật';
    document.getElementById('detail-stat-freq').textContent = window.busService.formatRouteFrequency ? window.busService.formatRouteFrequency(route) : 'Đang cập nhật';
    document.getElementById('detail-stat-distance').textContent = route.distanceKm?.average ? `${route.distanceKm.average} km` : (route.distanceKm?.outbound ? `${route.distanceKm.outbound} km` : 'Đang cập nhật');

    // Fares
    const fareSingle = window.busService.formatRouteFare(route);
    document.getElementById('detail-fare-single').textContent = `Vé lượt: ${fareSingle}`;

    let fareTag = 'Thông tin vé';
    if (route.fares?.type === 'flat') {
      fareTag = route.category === 'subsidized' ? 'Trợ giá' : 'Đồng giá';
    } else if (route.fares?.type === 'distance_tiered') {
      fareTag = 'Theo chặng';
    } else if (route.fares?.type === 'unknown') {
      fareTag = 'Đang cập nhật';
    }
    document.getElementById('detail-fare-tag').textContent = fareTag;

    const noteEl = document.getElementById('detail-fare-note');
    if (noteEl) {
      if (route.fares?.studentPrice) {
        noteEl.textContent = `Học sinh, SV: ${Number(route.fares.studentPrice).toLocaleString('vi-VN')}đ • Áp dụng theo chặng`;
      } else if (route.fares?.type === 'flat' && route.category === 'subsidized') {
        noteEl.textContent = 'Áp dụng thẻ vé tháng và ưu tiên học sinh sinh viên';
      } else if (route.fares?.type === 'unknown') {
        noteEl.textContent = 'Chưa có thông tin biểu giá chính thức';
      } else {
        noteEl.textContent = 'Áp dụng theo quy định của đơn vị vận hành';
      }
    }

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
    this.currentPlannedTrip = null;
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
    this.lastSearchQuery = { originText, destinationText };

    // Find matching routes
    const matchedRoutes = window.busService.findRoutesBetween(originText, destinationText);

    const titleEl = document.getElementById('trip-header-title');
    if (titleEl) {
      titleEl.textContent = `${originText} ➔ ${destinationText}`;
    }

    const contentSuccess = document.getElementById('trip-content-success');
    const contentEmpty = document.getElementById('trip-content-empty');
    const statsStrip = document.getElementById('trip-stats-strip');
    const busTag = document.getElementById('trip-bus-tag');
    const headerIndicator = document.getElementById('trip-header-indicator');

    if (matchedRoutes.length === 0) {
      // Check if Address-to-Address Trip Planner finds connecting trips or address-to-address trips
      const planned = this.tryRunPlanner(originText, destinationText);
      if (planned && planned.trips && planned.trips.length > 0) {
        this.renderPlannerResults(planned.trips, planned);
        this.navigateTo('trip-results');
        return;
      }

      // FAIL-CLOSED: No fake fallback!
      this.selectedRoute = null;
      this.matchedDirection = null;
      this.currentPlannedTrip = null;

      if (contentSuccess) contentSuccess.classList.add('hidden');
      if (contentEmpty) contentEmpty.classList.remove('hidden');
      if (statsStrip) statsStrip.classList.add('hidden');
      if (busTag) {
        busTag.className = 'px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200 text-[11px] font-bold flex items-center gap-1';
        busTag.textContent = 'Không có kết quả';
      }
      if (headerIndicator) {
        headerIndicator.className = 'w-2.5 h-2.5 rounded-full bg-slate-400 shrink-0';
      }

      const emptyTitle = document.getElementById('trip-empty-title');
      const emptyDesc = document.getElementById('trip-empty-desc');
      if (planned?.error === 'OUT_OF_SERVICE_AREA') {
        if (emptyTitle) emptyTitle.textContent = 'Ngoài vùng phục vụ Danabus';
        if (emptyDesc) emptyDesc.textContent = 'Điểm đón hoặc điểm đến nằm ngoài mạng lưới xe buýt Đà Nẵng - Quảng Nam (chỉ áp dụng khu vực Đà Nẵng, Hội An, Tam Kỳ).';
      } else if (planned?.error === 'NO_NEARBY_STOPS') {
        if (emptyTitle) emptyTitle.textContent = 'Không có trạm dừng lân cận';
        if (emptyDesc) emptyDesc.textContent = 'Không tìm thấy trạm dừng xe buýt nào gần điểm đi hoặc điểm đến trong bán kính đi bộ tối đa (1.5km).';
      } else if (planned?.error === 'NO_VIABLE_ROUTE') {
        if (emptyTitle) emptyTitle.textContent = 'Không tìm thấy lộ trình phù hợp';
        if (emptyDesc) emptyDesc.textContent = 'Hiện chưa có tuyến xe buýt trực tiếp hoặc chuyển tiếp phù hợp kết nối 2 điểm này theo dữ liệu vận hành hợp lệ.';
      } else {
        if (emptyTitle) emptyTitle.textContent = 'Không tìm thấy tuyến buýt phù hợp';
        if (emptyDesc) emptyDesc.textContent = 'Hiện tại chưa có tuyến buýt phù hợp kết nối 2 điểm này. Vui lòng kiểm tra lại điểm đón/đến hoặc tra cứu toàn bộ danh mục tuyến xe.';
      }

      const optionsContainer = document.getElementById('trip-planner-options');
      if (optionsContainer) optionsContainer.innerHTML = '';

      this.navigateTo('trip-results');
      return;
    }

    // Success State
    if (contentSuccess) contentSuccess.classList.remove('hidden');
    if (contentEmpty) contentEmpty.classList.add('hidden');
    if (statsStrip) statsStrip.classList.remove('hidden');
    if (headerIndicator) {
      headerIndicator.className = 'w-2.5 h-2.5 rounded-full bg-emerald-600 shrink-0';
    }

    const match = matchedRoutes[0];
    const route = match.route || match;
    this.selectedRoute = route;
    this.matchedDirection = match.matchedDirection || 'outbound';
    this.currentDirection = this.matchedDirection;

    if (busTag) {
      const isElec = Boolean(route.vehicleInfo && route.vehicleInfo.toLowerCase().includes('điện'));
      busTag.className = 'px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-100 text-[11px] font-bold flex items-center gap-1';
      busTag.innerHTML = `
        <span class="w-3.5 h-3.5"><svg viewBox="0 0 24 24" fill="currentColor" class="w-full h-full"><path d="M11 21h-1l1-7H7.5c-.58 0-.57-.32-.38-.66.19-.34.05-.08.07-.12C8.48 10.94 10.42 7.54 13 3h1l-1 7h3.5c.49 0 .56.33.47.51l-.07.15C12.9 17.55 11 21 11 21z"/></svg></span>
        ${isElec ? 'Xe buýt điện' : (route.category === 'subsidized' ? 'Buýt trợ giá' : 'Danabus')}
      `;
    }

    document.getElementById('trip-route-badge').textContent = `TUYẾN ${route.routeNumber}`;
    const kmVal = route.distanceKm?.average || route.distanceKm?.[this.matchedDirection] || route.distanceKm?.outbound || null;
    document.getElementById('trip-stat-km').textContent = kmVal ? `${kmVal} km` : 'Chưa có dữ liệu';
    const totalStops = match.stopCount || (route.stops?.[this.matchedDirection]?.length) || null;
    document.getElementById('trip-stat-stops').textContent = totalStops ? `${totalStops} trạm (${this.matchedDirection === 'outbound' ? 'Chiều đi' : 'Chiều về'})` : 'Chưa có dữ liệu';

    // Trip duration: truthfully render if in source, otherwise fail-closed / hide
    const timeElStrip = document.getElementById('trip-stat-time');
    const timeDotStrip = document.getElementById('trip-stat-time-dot');
    const routeDuration = route.durationMinutes || route.duration || null;
    if (routeDuration) {
      if (timeElStrip) {
        timeElStrip.textContent = `~${routeDuration} phút`;
        timeElStrip.classList.remove('hidden');
      }
      if (timeDotStrip) timeDotStrip.classList.remove('hidden');
    } else {
      if (timeElStrip) {
        timeElStrip.textContent = 'Chưa có dữ liệu';
        timeElStrip.classList.add('hidden');
      }
      if (timeDotStrip) timeDotStrip.classList.add('hidden');
    }

    const dep = window.busService.calculateNextDeparture(route, { direction: this.matchedDirection });
    const timeEl = document.getElementById('trip-countdown-time');
    const timerEl = document.getElementById('trip-countdown-timer');
    const depLabel = document.getElementById('trip-departure-label');
    const directTransferDesc = document.getElementById('trip-direct-transfer-desc');
    const directTransferText = document.getElementById('trip-direct-transfer-text');

    if (directTransferDesc) directTransferDesc.classList.remove('hidden');
    if (directTransferText) directTransferText.textContent = 'Đi thẳng suốt tuyến không đổi xe';

    if (dep.status === 'in_service') {
      if (depLabel) depLabel.textContent = 'Chuyến dự kiến theo lịch';
      if (dep.timeStr && dep.minutesUntilDeparture != null) {
        timeEl.textContent = dep.timeStr;
        timerEl.textContent = `Theo lịch: Còn ${dep.minutesUntilDeparture} phút`;
      } else {
        timeEl.textContent = '--:--';
        timerEl.textContent = window.busService.formatRouteFrequency ? `Theo lịch: ${window.busService.formatRouteFrequency(route)}` : 'Hoạt động theo lịch';
      }
    } else if (dep.status === 'before_service') {
      if (depLabel) depLabel.textContent = 'Chuyến dự kiến theo lịch';
      timeEl.textContent = dep.timeStr || '--:--';
      timerEl.textContent = (dep.minutesUntilDeparture != null)
        ? `Theo lịch: Chuyến đầu (sau ${dep.minutesUntilDeparture}p)`
        : `Chưa mở tuyến (${route.operatingHours?.start || '--:--'})`;
    } else if (dep.status === 'next_day') {
      if (depLabel) depLabel.textContent = 'Chuyến dự kiến theo lịch';
      timeEl.textContent = dep.timeStr || '--:--';
      timerEl.textContent = (dep.minutesUntilDeparture != null)
        ? `Theo lịch: Ngày mai (sau ${dep.minutesUntilDeparture}p)`
        : 'Chưa mở tuyến';
    } else if (dep.status === 'after_service') {
      if (depLabel) depLabel.textContent = 'Chuyến dự kiến theo lịch';
      timeEl.textContent = '--:--';
      timerEl.textContent = 'Theo lịch: Hết chuyến';
    } else {
      if (depLabel) depLabel.textContent = 'Chưa có dữ liệu';
      timeEl.textContent = '--:--';
      timerEl.textContent = 'Chưa có dữ liệu';
    }

    const singleFare = window.busService.formatRouteFare(route);
    document.getElementById('trip-fare-value').textContent = singleFare;
    document.getElementById('trip-freq-value').textContent = window.busService.formatRouteFrequency ? window.busService.formatRouteFrequency(route, true) : 'Đang cập nhật';

    // Fleet / Vehicle info: sourced from vehicleInfo, fail-closed
    const fleetInfo = window.busService.formatRouteVehicleInfo ? window.busService.formatRouteVehicleInfo(route) : { brand: 'Chưa có dữ liệu', description: 'Phương tiện' };
    const fleetValEl = document.getElementById('trip-fleet-value');
    const fleetDescEl = document.getElementById('trip-fleet-desc');
    if (fleetValEl) fleetValEl.textContent = fleetInfo.brand || 'Chưa có dữ liệu';
    if (fleetDescEl) fleetDescEl.textContent = fleetInfo.description || 'Phương tiện';

    // Later note: truthful schedule wording
    const laterNoteEl = document.getElementById('trip-later-note');
    const laterTimeEl = document.getElementById('trip-later-time');
    const laterDiffEl = document.getElementById('trip-later-diff');

    // Next trip calculation
    if (dep.isOperating) {
      if (laterNoteEl) laterNoteEl.textContent = 'Xuất bến theo lịch trình công bố';
      if (dep.timeStr) {
        const parts = dep.timeStr.split(':');
        let interval = null;
        if (typeof route.frequency?.peakMinutes === 'number' && Number.isFinite(route.frequency.peakMinutes) && route.frequency.peakMinutes > 0) {
          interval = route.frequency.peakMinutes;
        } else if (typeof route.frequency?.offPeakMinutes === 'number' && Number.isFinite(route.frequency.offPeakMinutes) && route.frequency.offPeakMinutes > 0) {
          interval = route.frequency.offPeakMinutes;
        }
        if (interval) {
          const laterM = parseInt(parts[1], 10) + interval;
          const laterH = parseInt(parts[0], 10) + Math.floor(laterM / 60);
          const laterStr = `${String(laterH % 24).padStart(2, '0')}:${String(laterM % 60).padStart(2, '0')}`;
          if (laterTimeEl) laterTimeEl.textContent = `Chuyến sau: ${laterStr}`;
          if (laterDiffEl) laterDiffEl.textContent = `(sau ${interval} phút)`;
        } else {
          if (laterTimeEl) laterTimeEl.textContent = dep.message ? `Theo lịch: ${dep.message}` : 'Đang hoạt động theo lịch';
          if (laterDiffEl) laterDiffEl.textContent = '';
        }
      } else {
        const freqText = window.busService.formatRouteFrequency ? window.busService.formatRouteFrequency(route) : '';
        if (laterTimeEl) laterTimeEl.textContent = (freqText && freqText !== 'Đang cập nhật') ? `Tần suất: ${freqText}` : (dep.message ? `Theo lịch: ${dep.message}` : 'Đang hoạt động theo lịch');
        if (laterDiffEl) laterDiffEl.textContent = '';
      }
    } else if (dep.message && dep.status !== 'unknown') {
      if (laterNoteEl) laterNoteEl.textContent = 'Xuất bến theo lịch trình công bố';
      if (laterTimeEl) laterTimeEl.textContent = `Theo lịch: ${dep.message}`;
      if (laterDiffEl) laterDiffEl.textContent = '';
    } else {
      if (laterNoteEl) laterNoteEl.textContent = 'Chưa có dữ liệu';
      if (laterTimeEl) laterTimeEl.textContent = 'Chưa có dữ liệu';
      if (laterDiffEl) laterDiffEl.textContent = '';
    }

    // Also run trip planner if available to populate detailed options below direct route
    const planned = this.tryRunPlanner(originText, destinationText);
    if (planned && planned.trips && planned.trips.length > 0) {
      this.renderTripOptions(planned.trips);
    } else {
      const optionsContainer = document.getElementById('trip-planner-options');
      if (optionsContainer) {
        optionsContainer.innerHTML = '';
        optionsContainer.classList.add('hidden');
      }
      const btnAlt = document.getElementById('btn-toggle-alternatives');
      if (btnAlt) btnAlt.setAttribute('aria-expanded', 'false');
    }

    // Build and render unified Journey Recommendation Timeline (Consumer-First)
    const journey = this.buildJourneyViewModelFromDirect(match, originText, destinationText);
    this.currentJourney = journey;
    this.currentPlannedTrip = planned?.trips?.[0] || null;
    this.renderJourneyRecommendation(journey, planned?.trips || []);

    this.navigateTo('trip-results');
  }

  // =========================================================================
  // TASK 10: UNIFIED JOURNEY VIEWMODEL BUILDERS & RENDERER
  // =========================================================================
  buildJourneyViewModelFromDirect(match, originText, destinationText) {
    const route = match.route || match;
    const direction = match.matchedDirection || 'outbound';
    const dep = window.busService.calculateNextDeparture(route, { direction });
    const fare = window.busService.formatRouteFare(route);
    let freqText = null;
    if (window.busService.formatRouteFrequency) {
      const formatted = window.busService.formatRouteFrequency(route, true);
      if (formatted && formatted !== 'Đang cập nhật') {
        freqText = formatted;
      }
    }
    const fleet = window.busService.formatRouteVehicleInfo ? window.busService.formatRouteVehicleInfo(route) : { brand: 'Chưa có dữ liệu', description: 'Phương tiện' };
    const kmVal = route.distanceKm?.average || route.distanceKm?.[direction] || route.distanceKm?.outbound || null;
    const totalStops = match.stopCount || (route.stops?.[direction]?.length) || null;
    const routeDuration = route.durationMinutes || route.duration || null;

    let intermediateStops = [];
    if (Array.isArray(route.stops?.[direction])) {
      const stopsList = route.stops[direction];
      const oName = typeof match.originStop === 'string' ? match.originStop : (match.originStop?.name || originText);
      const dName = typeof match.destinationStop === 'string' ? match.destinationStop : (match.destinationStop?.name || destinationText);
      const oIdx = match.originIndex != null ? match.originIndex : stopsList.findIndex(s => (s.name || s) === oName);
      const dIdx = match.destinationIndex != null ? match.destinationIndex : stopsList.findIndex(s => (s.name || s) === dName);
      if (oIdx >= 0 && dIdx > oIdx) {
        intermediateStops = stopsList.slice(oIdx + 1, dIdx).map(s => typeof s === 'string' ? s : s.name);
      }
    }

    const originStopName = typeof match.originStop === 'string' ? match.originStop : (match.originStop?.name || originText);
    const destinationStopName = typeof match.destinationStop === 'string' ? match.destinationStop : (match.destinationStop?.name || destinationText);

    return {
      sourceType: 'direct',
      isDirect: true,
      route,
      direction,
      originName: originText,
      destinationName: destinationText,
      boardingStopName: originStopName,
      alightingStopName: destinationStopName,
      durationMinutes: routeDuration,
      durationSemantics: routeDuration ? 'Ước tính' : null,
      distanceKm: kmVal,
      totalStops: totalStops,
      fareText: fare,
      fareSemantics: 'Theo lịch',
      frequencyText: freqText,
      departure: dep,
      fleetInfo: fleet,
      intermediateStops,
      transfers: 0,
      legs: [
        {
          type: 'transit',
          route,
          routeNumber: route.routeNumber,
          direction,
          boardingStop: { name: originStopName },
          alightingStop: { name: destinationStopName },
          stopsCount: totalStops,
          intermediateStops,
          departure: dep,
          fareText: fare,
          fleetInfo: fleet
        }
      ]
    };
  }

  buildJourneyViewModelFromPlanned(trip, originText, destinationText) {
    const isDirect = trip.type === 'direct';
    const legs = trip.legs || [];
    const transitLegs = legs.filter(l => l.type === 'transit');
    const firstTransit = transitLegs[0] || null;
    const primaryRoute = firstTransit?.route || trip.route || null;
    const primaryDirection = firstTransit?.direction || 'outbound';

    const dep = primaryRoute ? window.busService.calculateNextDeparture(primaryRoute, { direction: primaryDirection }) : null;
    const fleet = primaryRoute && window.busService.formatRouteVehicleInfo ? window.busService.formatRouteVehicleInfo(primaryRoute) : { brand: 'Chưa có dữ liệu', description: 'Phương tiện' };

    const totalStops = transitLegs.reduce((sum, l) => sum + (l.stopsCount || (l.intermediateStops ? l.intermediateStops.length + 1 : 1)), 0);

    // Defect 6 Fix: Only use verified segment distances, never full-route distance!
    let totalKm = null;
    const hasValidSegmentDistances = transitLegs.length > 0 && transitLegs.every(l => typeof l.segmentDistanceKm === 'number' && Number.isFinite(l.segmentDistanceKm) && l.segmentDistanceKm > 0);
    if (hasValidSegmentDistances) {
      const kmSum = transitLegs.reduce((sum, l) => sum + l.segmentDistanceKm, 0);
      if (kmSum > 0 && Number.isFinite(kmSum)) {
        totalKm = Math.round(kmSum * 10) / 10;
      }
    }

    // Defect 4 Fix: Frequency only contains real frequency data, never transfer counts or strings!
    let freqText = null;
    if (isDirect && primaryRoute && window.busService.formatRouteFrequency) {
      const formatted = window.busService.formatRouteFrequency(primaryRoute, true);
      if (formatted && formatted !== 'Đang cập nhật') {
        freqText = formatted;
      }
    }

    return {
      sourceType: 'planner',
      isDirect,
      rawTrip: trip,
      route: primaryRoute,
      direction: primaryDirection,
      originName: trip.legs[0]?.fromLabel || originText,
      destinationName: trip.legs[trip.legs.length - 1]?.toLabel || destinationText,
      durationMinutes: trip.totalDurationMinutes,
      durationSemantics: 'Ước tính',
      totalWalkingMeters: trip.totalWalkingMeters,
      walkingSemantics: 'Ước tính',
      distanceKm: totalKm,
      totalStops: totalStops > 0 ? totalStops : null,
      fareText: trip.fareText || '--',
      fareSemantics: 'Theo lịch',
      frequencyText: freqText,
      departure: dep,
      fleetInfo: fleet,
      transfers: trip.transfers || 0,
      legs: legs
    };
  }

  renderJourneyRecommendation(journey, allTrips = []) {
    const card = document.getElementById('journey-recommendation-card');
    if (!card) return;

    const escapeHtml = (str) => {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    };

    // 1. Badge
    const badgeEl = document.getElementById('journey-type-badge');
    if (badgeEl) {
      if (journey.isDirect) {
        badgeEl.textContent = 'Tuyến trực tiếp';
        badgeEl.className = 'px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-bold text-[11px] border border-emerald-100';
      } else {
        badgeEl.textContent = `${journey.transfers} lần chuyển tuyến`;
        badgeEl.className = 'px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 font-bold text-[11px] border border-blue-100';
      }
    }

    // 2. Summary Metrics (Truthful Semantics: Ước tính / Theo lịch / Chưa có dữ liệu)
    const metricsEl = document.getElementById('journey-summary-metrics');
    if (metricsEl) {
      let durationHtml = '';
      if (journey.durationMinutes) {
        durationHtml = `
          <div>
            <span class="text-[11px] text-slate-400 font-medium block">Thời gian</span>
            <span class="text-[13px] font-bold text-slate-800">Ước tính: ~${journey.durationMinutes} phút</span>
          </div>
        `;
      } else {
        durationHtml = `
          <div>
            <span class="text-[11px] text-slate-400 font-medium block">Thời gian</span>
            <span class="text-[13px] font-bold text-slate-500">Chưa có dữ liệu</span>
          </div>
        `;
      }

      const fareHtml = `
        <div>
          <span class="text-[11px] text-slate-400 font-medium block">Vé lượt</span>
          <span class="text-[13px] font-bold text-slate-800">${escapeHtml(journey.fareText || 'Chưa có dữ liệu')}</span>
        </div>
      `;

      let extraHtml = '';
      if (journey.totalWalkingMeters) {
        extraHtml = `
          <div>
            <span class="text-[11px] text-slate-400 font-medium block">Đi bộ</span>
            <span class="text-[13px] font-bold text-slate-800">Ước tính: ~${journey.totalWalkingMeters}m</span>
          </div>
        `;
      } else if (journey.departure?.status === 'in_service' && journey.departure.minutesUntilDeparture != null) {
        extraHtml = `
          <div>
            <span class="text-[11px] text-slate-400 font-medium block">Theo lịch</span>
            <span class="text-[13px] font-bold text-emerald-700">Còn ${journey.departure.minutesUntilDeparture}p (${journey.departure.timeStr || ''})</span>
          </div>
        `;
      } else if (journey.frequencyText && journey.frequencyText !== 'Đang cập nhật' && journey.frequencyText !== 'Chưa có dữ liệu') {
        extraHtml = `
          <div>
            <span class="text-[11px] text-slate-400 font-medium block">Tần suất</span>
            <span class="text-[13px] font-bold text-slate-800">Theo lịch: ${escapeHtml(journey.frequencyText)}</span>
          </div>
        `;
      } else {
        extraHtml = `
          <div>
            <span class="text-[11px] text-slate-400 font-medium block">Lịch trình</span>
            <span class="text-[13px] font-bold text-slate-500">Chưa có dữ liệu</span>
          </div>
        `;
      }

      metricsEl.innerHTML = `${durationHtml}${fareHtml}${extraHtml}`;
    }

    // 3. Timeline Stepper (<ol>)
    const timelineEl = document.getElementById('journey-timeline');
    if (timelineEl) {
      let timelineStepsHtml = '';

      // Step 1: Start point
      const firstLeg = journey.legs[0];
      const isFirstWalk = firstLeg && firstLeg.type === 'walking';
      timelineStepsHtml += `
        <li class="timeline-step timeline-step-start">
          <div class="timeline-marker bg-emerald-600 text-white font-bold">
            <svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="10" fill-opacity="0.3"/></svg>
          </div>
          <div class="timeline-content">
            <p class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Điểm xuất phát</p>
            <p class="text-[14px] font-bold text-slate-900">${escapeHtml(journey.originName)}</p>
            ${isFirstWalk && firstLeg.distanceMeters > 0 ? `
              <p class="text-[12px] text-slate-500 mt-0.5">Đi bộ ước tính: ~${firstLeg.distanceMeters}m (~${firstLeg.durationMinutes || 1} phút) đến trạm ${escapeHtml(firstLeg.toLabel || '')}</p>
            ` : `
              <p class="text-[12px] text-slate-500 mt-0.5">Đón xe tại trạm buýt</p>
            `}
          </div>
        </li>
      `;

      // Intermediate legs
      journey.legs.forEach((leg, legIdx) => {
        if (leg.type === 'transit') {
          const stopsCount = leg.stopsCount || (leg.intermediateStops ? leg.intermediateStops.length + 1 : 1);
          const hasIntermediate = Array.isArray(leg.intermediateStops) && leg.intermediateStops.length > 0;
          
          let depText = '';
          if (leg.departure?.status === 'in_service') {
            if (leg.departure.minutesUntilDeparture != null) {
              depText = `Theo lịch: Còn ${leg.departure.minutesUntilDeparture} phút (${leg.departure.timeStr || ''})`;
            } else {
              depText = 'Theo lịch: Hoạt động theo lịch';
            }
          } else if (leg.departure?.status === 'before_service' || leg.departure?.status === 'after_service' || leg.departure?.status === 'next_day') {
            depText = `Theo lịch: ${leg.departure.message}`;
          } else if (leg.departure?.message && leg.departure?.status !== 'unknown') {
            depText = leg.departure.message;
          }

          timelineStepsHtml += `
            <li class="timeline-step timeline-step-transit">
              <div class="timeline-marker bg-emerald-600 text-white font-bold">
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M4 16c0 .88.39 1.67 1 2.22V20c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h8v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4s-8 .5-8 4v10zm3.5 1c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm9 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm1.5-6H6V6h12v5z"/></svg>
              </div>
              <div class="timeline-content flex flex-col gap-1.5">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="px-2 py-0.5 rounded-md bg-emerald-600 text-white font-extrabold text-[11px] shadow-xs">TUYẾN ${escapeHtml(leg.routeNumber || journey.route?.routeNumber || '')}</span>
                  <span class="text-[13px] font-bold text-slate-900">Lên xe: ${escapeHtml(leg.boardingStop?.name || journey.boardingStopName || '')}</span>
                </div>
                ${depText ? `<p class="text-[12px] text-emerald-700 font-semibold">${escapeHtml(depText)}</p>` : ''}
                
                <div class="mt-1.5 p-2.5 rounded-xl bg-slate-50 border border-slate-100">
                  <div class="flex items-center justify-between text-[12px] text-slate-600 font-medium">
                    <span>Di chuyển qua ${stopsCount} trạm</span>
                    ${leg.durationMinutes ? `<span>Ước tính: ~${leg.durationMinutes} phút</span>` : ''}
                  </div>
                  ${hasIntermediate ? `
                    <button type="button" class="btn-toggle-intermediate text-[11px] font-semibold text-emerald-700 hover:text-emerald-800 flex items-center gap-1 mt-1.5 pt-1.5 border-t border-slate-200/60 transition-colors" aria-expanded="false" aria-controls="stops-list-${legIdx}">
                      <span>Xem ${leg.intermediateStops.length} trạm trung gian</span>
                      <svg class="w-3.5 h-3.5 chevron-icon transition-transform" viewBox="0 0 24 24" fill="currentColor"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/></svg>
                    </button>
                    <ul id="stops-list-${legIdx}" class="intermediate-stops-list hidden pl-3 py-1.5 mt-1 border-l-2 border-emerald-300 text-[11px] text-slate-500 flex flex-col gap-1">
                      ${leg.intermediateStops.map(s => `<li>• ${escapeHtml(typeof s === 'string' ? s : s.name)}</li>`).join('')}
                    </ul>
                  ` : ''}
                </div>

                <div class="flex items-center gap-2 text-[13px] font-bold text-slate-900 mt-1">
                  <span class="w-2 h-2 rounded-full bg-rose-500 shrink-0"></span>
                  <span>Xuống xe: ${escapeHtml(leg.alightingStop?.name || journey.alightingStopName || '')}</span>
                </div>
              </div>
            </li>
          `;
        } else if (leg.type === 'walking' && legIdx > 0 && legIdx < journey.legs.length - 1) {
          // Transfer walking leg
          timelineStepsHtml += `
            <li class="timeline-step timeline-step-transfer">
              <div class="timeline-marker bg-amber-500 text-white font-bold">
                <svg viewBox="0 0 24 24" fill="currentColor"><path d="M13.5 5.5c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zM9.8 8.9L7 23h2.1l1.8-8 2.1 2v6h2v-7.5l-2.1-2 .6-3C14.8 12 16.8 13 19 13v-2c-1.9 0-3.5-1-4.3-2.4l-1-1.6c-.4-.6-1-1-1.7-1-.3 0-.5.1-.8.1L6 8.3V13h2V9.6l1.8-.7"/></svg>
              </div>
              <div class="timeline-content">
                <p class="text-[12px] font-bold text-slate-800">Chuyển tuyến</p>
                <p class="text-[12px] text-slate-500">Đi bộ ước tính: ~${leg.distanceMeters}m (~${leg.durationMinutes || 1} phút) sang trạm kế tiếp</p>
              </div>
            </li>
          `;
        }
      });

      // Step Final: Destination point
      const lastLeg = journey.legs[journey.legs.length - 1];
      const isLastWalk = lastLeg && lastLeg.type === 'walking' && journey.legs.length > 1;
      timelineStepsHtml += `
        <li class="timeline-step timeline-step-end">
          <div class="timeline-marker bg-rose-600 text-white font-bold">
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 0 1 0-5 2.5 2.5 0 0 1 0 5z"/></svg>
          </div>
          <div class="timeline-content">
            <p class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Điểm đến</p>
            <p class="text-[14px] font-bold text-slate-900">${escapeHtml(journey.destinationName)}</p>
            ${isLastWalk && lastLeg.distanceMeters > 0 ? `
              <p class="text-[12px] text-slate-500 mt-0.5">Đi bộ ước tính: ~${lastLeg.distanceMeters}m (~${lastLeg.durationMinutes || 1} phút) đến điểm đích</p>
            ` : `
              <p class="text-[12px] text-slate-500 mt-0.5">Đến nơi</p>
            `}
          </div>
        </li>
      `;

      timelineEl.innerHTML = timelineStepsHtml;

      // Attach accordion toggle listeners for intermediate stops
      timelineEl.querySelectorAll('.btn-toggle-intermediate').forEach(btn => {
        btn.addEventListener('click', () => {
          const targetId = btn.getAttribute('aria-controls');
          const targetEl = document.getElementById(targetId);
          if (!targetEl) return;
          const isHidden = targetEl.classList.contains('hidden');
          if (isHidden) {
            targetEl.classList.remove('hidden');
            btn.setAttribute('aria-expanded', 'true');
          } else {
            targetEl.classList.add('hidden');
            btn.setAttribute('aria-expanded', 'false');
          }
        });
      });
    }

    // 4. Secondary Actions toolbar
    const btnAlt = document.getElementById('btn-toggle-alternatives');
    if (btnAlt) {
      btnAlt.setAttribute('aria-expanded', 'false');
      if (allTrips && allTrips.length > 1) {
        btnAlt.classList.remove('hidden');
        const altLabel = document.getElementById('label-toggle-alternatives');
        if (altLabel) altLabel.textContent = `Xem thêm ${allTrips.length - 1} phương án khác (${allTrips.length} phương án)`;
      } else {
        btnAlt.classList.add('hidden');
      }
    }

    const btnRouteDetail = document.getElementById('btn-journey-route-detail');
    if (btnRouteDetail) {
      if (journey.route) {
        btnRouteDetail.classList.remove('hidden');
      } else {
        btnRouteDetail.classList.add('hidden');
      }
    }
  }

  // =========================================================================
  // TASK 4: ADDRESS-TO-ADDRESS TRIP PLANNER INTEGRATION
  // =========================================================================
  resolveLocationFromText(text) {
    if (!text || !window.busService) return null;
    const norm = (str) => window.busService.normalize(str);
    const q = norm(text);
    if (!q || q.length < 2) return null;

    // Check curated POIs in LocalLocationProvider
    const pois = window.locationManager?.localProvider?.localPOIs || [];
    for (const p of pois) {
      const pName = norm(p.displayName);
      const pAddr = norm(p.address);
      const pKw = (p.keywords || []).map(k => norm(k));
      if (pName.includes(q) || q.includes(pName) || pAddr.includes(q) || pKw.some(k => k.includes(q) || q.includes(k))) {
        return new window.ResolvedLocation(p);
      }
    }

    // Check verified bus stops
    const stops = window.busService.stops || [];
    for (const s of stops) {
      if (s.status !== 'verified' || !s.lat || !s.lng) continue;
      const sName = norm(s.name);
      if (sName === q || sName.includes(q) || q.includes(sName)) {
        return new window.ResolvedLocation({
          displayName: s.name,
          address: s.street ? `Đường ${s.street}, Đà Nẵng` : 'Trạm xe buýt Đà Nẵng',
          lat: s.lat,
          lng: s.lng,
          type: 'stop'
        });
      }
    }
    return null;
  }

  tryRunPlanner(originText, destinationText) {
    if (!window.transitPlanner) return null;

    let oLoc = this.originLocation;
    let dLoc = this.destinationLocation;

    if (!oLoc || !oLoc.isValid || !oLoc.isValid()) {
      oLoc = this.resolveLocationFromText(originText);
    }
    if (!dLoc || !dLoc.isValid || !dLoc.isValid()) {
      dLoc = this.resolveLocationFromText(destinationText);
    }

    if (!oLoc || !dLoc || !oLoc.isValid || !dLoc.isValid || !oLoc.isValid() || !dLoc.isValid()) {
      return null;
    }

    return window.transitPlanner.planTrip(oLoc, dLoc);
  }

  renderPlannerResults(trips, planMetadata = null) {
    const contentSuccess = document.getElementById('trip-content-success');
    const contentEmpty = document.getElementById('trip-content-empty');
    const statsStrip = document.getElementById('trip-stats-strip');
    const busTag = document.getElementById('trip-bus-tag');
    const headerIndicator = document.getElementById('trip-header-indicator');

    if (!trips || trips.length === 0) return;
    const bestTrip = trips[0];
    this.currentPlannedTrip = bestTrip;
    this.selectedRoute = bestTrip.route || bestTrip.legs[1]?.route || null;

    if (contentSuccess) contentSuccess.classList.remove('hidden');
    if (contentEmpty) contentEmpty.classList.add('hidden');
    if (statsStrip) statsStrip.classList.remove('hidden');
    if (headerIndicator) headerIndicator.className = 'w-2.5 h-2.5 rounded-full bg-emerald-600 shrink-0';

    if (busTag) {
      busTag.className = 'px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-100 text-[11px] font-bold flex items-center gap-1';
      busTag.textContent = bestTrip.type === 'direct' ? 'Tuyến trực tiếp' : `Chuyển tuyến (${bestTrip.transfers || 1} lần)`;
    }

    const origText = this.lastSearchQuery?.originText || '';
    const destText = this.lastSearchQuery?.destinationText || '';
    const journey = this.buildJourneyViewModelFromPlanned(bestTrip, origText, destText);
    this.currentJourney = journey;
    this.matchedDirection = journey.direction;
    this.currentDirection = journey.direction;

    // Reset alternatives container and toggle button
    const optionsContainer = document.getElementById('trip-planner-options');
    if (optionsContainer) optionsContainer.classList.add('hidden');
    const btnAlt = document.getElementById('btn-toggle-alternatives');
    if (btnAlt) btnAlt.setAttribute('aria-expanded', 'false');

    // Update secondary technical details card and reset legacy schedule fields
    this.updateSecondaryTechDetails(journey, bestTrip, planMetadata);

    // Render unified Journey Recommendation Timeline
    this.renderJourneyRecommendation(journey, trips);

    // Render Alternative Trip Options
    this.renderTripOptions(trips, planMetadata);
  }

  updateSecondaryTechDetails(journey, trip, planMetadata = null) {
    const isDirect = trip.type === 'direct';

    const badgeEl = document.getElementById('trip-route-badge');
    if (badgeEl) badgeEl.textContent = isDirect ? `TUYẾN ${trip.route?.routeNumber || ''}` : 'KẾT HỢP';

    // Truthful Semantics Fix: Distance in km, never minutes!
    const kmEl = document.getElementById('trip-stat-km');
    if (kmEl) kmEl.textContent = journey.distanceKm ? `${journey.distanceKm} km` : 'Chưa có dữ liệu';

    // Truthful Semantics Fix: Stops count, never ranking category!
    const stopsEl = document.getElementById('trip-stat-stops');
    if (stopsEl) stopsEl.textContent = journey.totalStops ? `${journey.totalStops} trạm` : 'Chưa có dữ liệu';

    const timeElStrip = document.getElementById('trip-stat-time');
    const timeDotStrip = document.getElementById('trip-stat-time-dot');
    if (timeElStrip) {
      const isExpanded = trip.isExpandedRadius || planMetadata?.isExpandedRadius;
      timeElStrip.textContent = `Đi bộ ước tính ~${trip.totalWalkingMeters}m${isExpanded ? ' (Bán kính 1.5km)' : ''}`;
      timeElStrip.classList.remove('hidden');
    }
    if (timeDotStrip) timeDotStrip.classList.remove('hidden');

    // Truthful Semantics Fix: Planner total duration heading
    const depLabel = document.getElementById('trip-departure-label');
    if (depLabel) {
      depLabel.textContent = 'Ước tính thời gian hành trình';
    }

    // Direct vs connecting transfer description
    const directTransferDesc = document.getElementById('trip-direct-transfer-desc');
    const directTransferText = document.getElementById('trip-direct-transfer-text');
    if (isDirect) {
      if (directTransferDesc) directTransferDesc.classList.remove('hidden');
      if (directTransferText) directTransferText.textContent = 'Đi thẳng suốt tuyến không đổi xe';
    } else {
      if (directTransferDesc) directTransferDesc.classList.add('hidden');
      if (directTransferText) directTransferText.textContent = '';
    }

    // Planner duration and departure schedule status pill
    const timeEl = document.getElementById('trip-countdown-time');
    const timerEl = document.getElementById('trip-countdown-timer');
    if (timeEl) timeEl.textContent = `~${trip.totalDurationMinutes}p`;
    if (timerEl) {
      if (isDirect && journey.departure?.status === 'in_service' && journey.departure.minutesUntilDeparture != null) {
        timerEl.textContent = `Theo lịch: Còn ${journey.departure.minutesUntilDeparture} phút`;
      } else if (isDirect && (journey.departure?.status === 'before_service' || journey.departure?.status === 'after_service' || journey.departure?.status === 'next_day')) {
        timerEl.textContent = `Theo lịch: ${journey.departure.message}`;
      } else if (isDirect && journey.departure?.message && journey.departure?.status !== 'unknown') {
        timerEl.textContent = `Theo lịch: ${journey.departure.message}`;
      } else {
        timerEl.textContent = 'Chưa có dữ liệu';
      }
    }

    const fareEl = document.getElementById('trip-fare-value');
    if (fareEl) fareEl.textContent = trip.fareText || '--';

    const freqEl = document.getElementById('trip-freq-value');
    if (freqEl) freqEl.textContent = journey.frequencyText || 'Chưa có dữ liệu';

    // Fleet: Truthful provenance, never hardcoded "Xe buýt Danabus"
    const fleetEl = document.getElementById('trip-fleet-value');
    const fleetDescEl = document.getElementById('trip-fleet-desc');
    if (fleetEl) fleetEl.textContent = journey.fleetInfo?.brand || 'Chưa có dữ liệu';
    if (fleetDescEl) fleetDescEl.textContent = journey.fleetInfo?.description || 'Phương tiện';

    // Reset legacy schedule fields (trip-later-*) so prior direct search never leaks!
    const laterTimeEl = document.getElementById('trip-later-time');
    const laterDiffEl = document.getElementById('trip-later-diff');
    const laterNoteEl = document.getElementById('trip-later-note');

    if (isDirect && journey.departure?.isOperating) {
      if (journey.departure.timeStr) {
        const parts = journey.departure.timeStr.split(':');
        let interval = null;
        const r = trip.route;
        if (typeof r?.frequency?.peakMinutes === 'number' && Number.isFinite(r.frequency.peakMinutes) && r.frequency.peakMinutes > 0) {
          interval = r.frequency.peakMinutes;
        } else if (typeof r?.frequency?.offPeakMinutes === 'number' && Number.isFinite(r.frequency.offPeakMinutes) && r.frequency.offPeakMinutes > 0) {
          interval = r.frequency.offPeakMinutes;
        }
        if (interval) {
          const laterM = parseInt(parts[1], 10) + interval;
          const laterH = parseInt(parts[0], 10) + Math.floor(laterM / 60);
          const laterStr = `${String(laterH % 24).padStart(2, '0')}:${String(laterM % 60).padStart(2, '0')}`;
          if (laterTimeEl) laterTimeEl.textContent = `Chuyến sau: ${laterStr}`;
          if (laterDiffEl) laterDiffEl.textContent = `(sau ${interval} phút)`;
          if (laterNoteEl) laterNoteEl.textContent = 'Xuất bến theo lịch trình công bố';
        } else {
          if (laterTimeEl) laterTimeEl.textContent = journey.departure.message ? `Theo lịch: ${journey.departure.message}` : 'Đang hoạt động theo lịch';
          if (laterDiffEl) laterDiffEl.textContent = '';
          if (laterNoteEl) laterNoteEl.textContent = 'Xuất bến theo lịch trình công bố';
        }
      } else {
        const freqText = journey.frequencyText;
        if (laterTimeEl) laterTimeEl.textContent = (freqText && freqText !== 'Chưa có dữ liệu') ? `Tần suất: ${freqText}` : (journey.departure.message ? `Theo lịch: ${journey.departure.message}` : 'Đang hoạt động theo lịch');
        if (laterDiffEl) laterDiffEl.textContent = '';
        if (laterNoteEl) laterNoteEl.textContent = 'Xuất bến theo lịch trình công bố';
      }
    } else if (isDirect && journey.departure?.message && journey.departure.status !== 'unknown') {
      if (laterTimeEl) laterTimeEl.textContent = `Theo lịch: ${journey.departure.message}`;
      if (laterDiffEl) laterDiffEl.textContent = '';
      if (laterNoteEl) laterNoteEl.textContent = 'Xuất bến theo lịch trình công bố';
    } else {
      // Connecting trip OR direct trip without operating schedule fail-closed
      if (laterTimeEl) laterTimeEl.textContent = 'Chưa có dữ liệu';
      if (laterDiffEl) laterDiffEl.textContent = '';
      if (laterNoteEl) laterNoteEl.textContent = 'Chưa có dữ liệu';
    }
  }

  renderTripOptions(trips, planMetadata = null) {
    const container = document.getElementById('trip-planner-options');
    if (!container) return;
    this.currentPlannedTrips = trips;
    if (!trips || trips.length === 0) {
      container.innerHTML = '';
      container.classList.add('hidden');
      return;
    }

    // Alternatives must be collapsed by default after every render/search
    container.classList.add('hidden');
    const btnAlt = document.getElementById('btn-toggle-alternatives');
    if (btnAlt) btnAlt.setAttribute('aria-expanded', 'false');

    const hasExpanded = trips.some(t => t.isExpandedRadius) || planMetadata?.isExpandedRadius;

    container.innerHTML = `
      ${hasExpanded ? `
        <div class="bg-amber-50 border border-amber-200 text-amber-900 px-3 py-2 rounded-xl text-[12px] flex items-center gap-2 mt-2">
          <span class="text-amber-600 font-bold shrink-0">ℹ️</span>
          <span>Đã mở rộng bán kính tìm trạm đi bộ lên <b>1.500m</b> do không tìm thấy tuyến trong bán kính 800m.</span>
        </div>
      ` : ''}
      <div class="flex items-center justify-between mt-2 pt-2 border-t border-slate-200/60">
        <h4 class="font-bold text-[13px] text-slate-800">Phương án di chuyển (${trips.length})</h4>
        <span class="text-[11px] text-slate-500">Đã xếp hạng</span>
      </div>
      ${trips.map((t, idx) => `
        <div class="bg-white rounded-2xl p-3.5 shadow-sm border border-slate-100 flex flex-col gap-2.5">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="px-2.5 py-0.5 rounded-full ${t.type === 'direct' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-blue-50 text-blue-700 border border-blue-200'} text-[11px] font-bold">
                ${t.rankingCategory}
              </span>
              <span class="text-[12px] font-bold text-slate-800">
                ${t.type === 'direct' ? `Tuyến ${t.route?.routeNumber}` : `${t.transfers} lần chuyển tuyến`}
              </span>
            </div>
            <span class="text-[13px] font-extrabold text-emerald-700">~${t.totalDurationMinutes} phút</span>
          </div>

          <div class="flex flex-col gap-1.5 text-[12px] bg-slate-50 p-2.5 rounded-xl border border-slate-100">
            ${t.legs.map((leg) => {
              if (leg.type === 'walking') {
                return `
                  <div class="flex items-center gap-2 text-slate-600">
                    <span class="w-4 h-4 text-slate-400 shrink-0">🚶</span>
                    <span class="truncate">${leg.summary}</span>
                  </div>
                `;
              } else {
                return `
                  <div class="flex items-center gap-2 text-slate-900 font-medium">
                    <span class="w-5 h-5 rounded bg-emerald-600 text-white font-bold text-[10px] flex items-center justify-center shrink-0">${leg.routeNumber}</span>
                    <span class="truncate">Tuyến ${leg.routeNumber}: ${leg.boardingStop?.name} ➔ ${leg.alightingStop?.name} (${leg.stopsCount} trạm)</span>
                  </div>
                `;
              }
            }).join('')}
          </div>

          <div class="flex items-center justify-between pt-1">
            <div class="flex items-center gap-2 text-[11px] text-slate-500">
              <span>Đi bộ: <b>~${t.totalWalkingMeters}m</b></span>
              <span>•</span>
              <span>Vé: <b>${t.fareText || '--'}</b></span>
            </div>
            <div class="flex items-center gap-2">
              <button type="button" class="btn-select-trip px-3 py-1 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-[11px] active:scale-95 transition-all" data-trip-index="${idx}">
                <span>Chọn</span>
              </button>
              <button type="button" class="btn-view-planned-map px-3 py-1 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[11px] flex items-center gap-1 active:scale-95 transition-all" data-trip-index="${idx}">
                <span>Bản đồ</span>
                <svg viewBox="0 0 24 24" fill="currentColor" class="w-3 h-3"><path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"/></svg>
              </button>
            </div>
          </div>
        </div>
      `).join('')}
    `;

    container.querySelectorAll('.btn-view-planned-map').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const idx = parseInt(btn.getAttribute('data-trip-index'), 10);
        const trip = this.currentPlannedTrips[idx];
        if (trip) {
          this.openPlannedTripMap(trip);
        }
      });
    });

    container.querySelectorAll('.btn-select-trip').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const idx = parseInt(btn.getAttribute('data-trip-index'), 10);
        const trip = this.currentPlannedTrips[idx];
        if (trip) {
          this.currentPlannedTrip = trip;
          this.selectedRoute = trip.route || trip.legs?.find(l => l.route)?.route || null;
          const origText = this.lastSearchQuery?.originText || '';
          const destText = this.lastSearchQuery?.destinationText || '';
          const journey = this.buildJourneyViewModelFromPlanned(trip, origText, destText);
          this.currentJourney = journey;
          this.matchedDirection = journey.direction;
          this.currentDirection = journey.direction;

          // Collapse alternatives on select and reset toggle
          container.classList.add('hidden');
          const btnAlt = document.getElementById('btn-toggle-alternatives');
          if (btnAlt) btnAlt.setAttribute('aria-expanded', 'false');

          this.updateSecondaryTechDetails(journey, trip);
          this.renderJourneyRecommendation(journey, this.currentPlannedTrips);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }
      });
    });
  }

  openPlannedTripMap(trip) {
    if (!trip || !window.mapService) return;
    this.currentPlannedTrip = trip;
    const badgeEl = document.getElementById('map-route-badge');
    const titleEl = document.getElementById('map-route-title');
    const dirEl = document.getElementById('map-route-dir');
    if (badgeEl) badgeEl.textContent = trip.type === 'direct' ? (trip.route?.routeNumber || 'BUÝT') : 'KẾT HỢP';
    if (titleEl) titleEl.textContent = `${trip.legs[0]?.fromLabel || 'Điểm đón'} ➔ ${trip.legs[trip.legs.length - 1]?.toLabel || 'Điểm đến'}`;
    if (dirEl) dirEl.textContent = `${trip.rankingCategory} • Tổng thời gian ~${trip.totalDurationMinutes} phút`;
    window.mapService.renderTrip(trip);
    this.navigateTo('map');
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

  async renderPickerResults(query = '') {
    const container = document.getElementById('picker-results-container');
    if (!container) return;

    const currentRenderSeq = ++this._pickerRenderSeq;

    if (this.pickerActiveTab === 'popular' && !query) {
      const popular = window.busService.getPopularDestinations();
      container.innerHTML = popular.map((p, idx) => `
        <button type="button" class="picker-item text-left w-full bg-white rounded-xl p-3 shadow-xs border border-slate-100 active:bg-slate-50 flex items-center justify-between cursor-pointer" data-name="${p.name}" data-idx="${idx}" aria-label="${p.name}">
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
        </button>
      `).join('');

      container.querySelectorAll('.picker-item').forEach(item => {
        item.addEventListener('click', () => {
          const idx = parseInt(item.getAttribute('data-idx'), 10);
          const p = popular[idx];
          const resolved = p ? new window.ResolvedLocation({ displayName: p.name, address: p.subtext, lat: p.lat, lng: p.lng, type: 'poi' }) : null;
          this.selectLocation(p ? p.name : item.getAttribute('data-name'), resolved);
        });
      });
    } else {
      let results = [];
      if (window.locationManager) {
        results = await window.locationManager.search(query);
      }

      // Generation sequence check: drop obsolete responses immediately
      if (currentRenderSeq !== this._pickerRenderSeq) {
        return;
      }

      if (!results || results.length === 0) {
        const stops = window.busService.searchStops(query);
        results = stops.map(s => ({
          displayName: s.name,
          address: s.street ? `Đường ${s.street}` : 'Trạm xe buýt Đà Nẵng',
          type: 'stop',
          lat: s.lat,
          lng: s.lng,
          routes: s.routes
        }));
      }

      const hasGoogleResults = Array.isArray(results) && results.some(item => item.provider === 'google');

      let resultsHtml = results.map((item, idx) => `
        <button type="button" class="picker-item text-left w-full bg-white rounded-xl p-3 shadow-xs border border-slate-100 active:bg-slate-50 flex items-center justify-between cursor-pointer" data-name="${item.displayName}" data-idx="${idx}" aria-label="${item.displayName}">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-9 h-9 rounded-xl ${item.type === 'poi' ? 'bg-amber-50 text-amber-600' : (item.type === 'address' ? 'bg-blue-50 text-blue-600' : (item.type === 'pin' ? 'bg-purple-50 text-purple-600' : 'bg-slate-100 text-slate-600'))} flex items-center justify-center shrink-0">
              ${window.renderIcon(item.type === 'poi' ? 'place' : (item.type === 'address' ? 'home' : (item.type === 'pin' ? 'place' : 'directions_bus')), 'w-4 h-4')}
            </div>
            <div class="min-w-0">
              <h4 class="font-bold text-[13px] text-slate-900 truncate">${item.displayName}</h4>
              <p class="text-[11px] text-slate-400 truncate mt-0.5">${item.address || 'Đà Nẵng'}</p>
              ${item.routes?.length > 0 ? `
                <div class="flex items-center gap-1 mt-1 flex-wrap">
                  <span class="text-[10px] text-slate-400">Tuyến:</span>
                  ${item.routes.map(r => `<span class="bg-emerald-600 text-white text-[9px] font-bold px-1.5 py-0.2 rounded">${typeof r === 'object' ? r.routeNumber : r}</span>`).join('')}
                </div>
              ` : ''}
            </div>
          </div>
          ${window.renderIcon('chevron_right', 'w-4 h-4 text-slate-300')}
        </button>
      `).join('');

      // Places API Policy Attribution: show "Powered by Google" when Google-sourced results are rendered
      if (hasGoogleResults) {
        resultsHtml += `
          <div class="google-attribution flex items-center justify-center gap-1.5 py-2.5 text-slate-400 text-[11px] border-t border-slate-100 mt-2">
            <span>Tìm kiếm địa điểm hỗ trợ bởi</span>
            <span class="font-semibold text-slate-600">Google</span>
          </div>
        `;
      }

      container.innerHTML = resultsHtml;

      container.querySelectorAll('.picker-item').forEach(btn => {
        btn.addEventListener('click', async () => {
          const idx = parseInt(btn.getAttribute('data-idx'), 10);
          const resItem = results[idx];
          if (!resItem) return;

          let resolved = null;
          if (window.locationManager) {
            resolved = await window.locationManager.resolve(resItem.id || resItem.placeId, resItem);
          }
          if ((!resolved || !resolved.isValid()) && typeof resItem.lat === 'number' && typeof resItem.lng === 'number' && Number.isFinite(resItem.lat) && Number.isFinite(resItem.lng)) {
            resolved = new window.ResolvedLocation(resItem);
          }

          if (!resolved || !resolved.isValid()) {
            console.warn('[DanabusApp] Place details unavailable for:', resItem.displayName);
            alert('Không thể lấy tọa độ chi tiết cho địa điểm này. Vui lòng chọn địa điểm khác hoặc thử lại.');
            return;
          }

          this.selectLocation(resItem.displayName || btn.getAttribute('data-name'), resolved);
        });
      });
    }
  }

  selectLocation(name, resolvedLoc = null) {
    let loc = resolvedLoc;
    if (!loc || typeof loc.isValid !== 'function' || !loc.isValid()) {
      loc = this.resolveLocationFromText(name);
    }
    if (!loc || typeof loc.isValid !== 'function' || !loc.isValid()) {
      console.warn('[DanabusApp] selectLocation rejected invalid location:', name, loc);
      return false;
    }
    if (this.pickerTarget === 'origin') {
      const el = document.getElementById('home-origin-display');
      if (el) el.textContent = name;
      this.originLocation = loc;
    } else {
      const el = document.getElementById('home-destination-input');
      if (el) el.value = name;
      this.destinationLocation = loc;
    }
    this.clearSearchValidationError();
    this.closeLocationPicker();
    return true;
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

      if ((origVal === 'Chọn điểm đón' || !origVal) && !destVal) return;

      const newOrig = destVal || 'Chọn điểm đón';
      const newDest = (origVal === 'Chọn điểm đón' || origVal === 'Vị trí hiện tại') ? '' : origVal;

      origEl.textContent = newOrig;
      destEl.value = newDest;

      const tempLoc = this.originLocation;
      this.originLocation = this.destinationLocation;
      this.destinationLocation = tempLoc;

      this.clearSearchValidationError();

      // If user is currently on trip-results screen, immediately re-run search with swapped values to prevent stale display
      if (this.currentView === 'trip-results') {
        const val = window.busService.validateSearchQuery(newOrig, newDest);
        if (val.valid) {
          this.showTripResults(newOrig, newDest);
        } else {
          this.showTripResults(newOrig, newDest); // Fail-closed empty state
        }
      }
    });

    // Home Voice Search: capability disabled/hidden (no fake simulation)
    const voiceBtn = document.getElementById('home-voice-btn');
    if (voiceBtn) {
      voiceBtn.disabled = true;
      voiceBtn.classList.add('hidden');
    }

    // Home Search CTA
    document.getElementById('btn-home-search')?.addEventListener('click', () => {
      const origText = document.getElementById('home-origin-display')?.textContent.trim() || '';
      const destText = document.getElementById('home-destination-input')?.value.trim() || '';

      const validation = window.busService.validateSearchQuery(origText, destText);
      if (!validation.valid) {
        this.showSearchValidationError(validation.message, validation.error);
        return;
      }

      this.clearSearchValidationError();
      this.showTripResults(origText, destText);
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
    document.getElementById('btn-map-fit-route')?.addEventListener('click', () => {
      window.mapService.fitRoute();
    });
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
        const gpsLoc = window.locationManager ? window.locationManager.resolveFromCoordinates(res.coords.latitude, res.coords.longitude, 'Vị trí hiện tại') : null;
        this.selectLocation('Vị trí hiện tại', gpsLoc);
      } else {
        alert(`Không thể xác định vị trí GPS: ${res.error}`);
      }
    });

    // Map Pin Picker CTA
    document.getElementById('btn-picker-map-pin')?.addEventListener('click', () => {
      this.closeLocationPicker();
      this.navigateTo('map');
      if (window.mapService) {
        window.mapService.enableMapPinSelection(({ lat, lng }) => {
          const pinLoc = window.locationManager
            ? window.locationManager.resolveFromMapPin(lat, lng)
            : new window.ResolvedLocation({ displayName: `Ghim (${lat.toFixed(4)}, ${lng.toFixed(4)})`, address: `Ghim (${lat.toFixed(4)}, ${lng.toFixed(4)})`, lat, lng, type: 'pin', provider: 'map_pin' });
          this.selectLocation(pinLoc.displayName, pinLoc);
          this.navigateTo('home');
        });
      }
    });

    const pickerSearchInput = document.getElementById('picker-search-input');
    let searchDebounceTimer = null;
    pickerSearchInput?.addEventListener('input', e => {
      clearTimeout(searchDebounceTimer);
      searchDebounceTimer = setTimeout(() => {
        this.renderPickerResults(e.target.value);
      }, 300);
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
        const direction = this.currentJourney?.direction || this.matchedDirection || 'outbound';
        this.openRouteDetail(this.selectedRoute.id, direction);
      } else if (this.currentPlannedTrip) {
        this.openPlannedTripMap(this.currentPlannedTrip);
      }
    });

    // Journey Recommendation Actions (Task 10)
    document.getElementById('btn-journey-map')?.addEventListener('click', () => {
      if (this.currentPlannedTrip) {
        this.openPlannedTripMap(this.currentPlannedTrip);
      } else if (this.selectedRoute) {
        this.openMapView();
      }
    });

    document.getElementById('btn-journey-route-detail')?.addEventListener('click', () => {
      const journey = this.currentJourney;
      const route = journey?.route || this.selectedRoute || this.currentPlannedTrip?.route || this.currentPlannedTrip?.legs?.find(l => l.route)?.route;
      const direction = journey?.direction || this.matchedDirection || 'outbound';
      if (route) {
        this.openRouteDetail(route.id, direction);
      }
    });

    document.getElementById('btn-toggle-alternatives')?.addEventListener('click', () => {
      const optionsContainer = document.getElementById('trip-planner-options');
      const btn = document.getElementById('btn-toggle-alternatives');
      if (!optionsContainer || !btn) return;
      const isHidden = optionsContainer.classList.contains('hidden');
      if (isHidden) {
        optionsContainer.classList.remove('hidden');
        btn.setAttribute('aria-expanded', 'true');
      } else {
        optionsContainer.classList.add('hidden');
        btn.setAttribute('aria-expanded', 'false');
      }
    });

    document.getElementById('btn-toggle-tech-details')?.addEventListener('click', () => {
      const card = document.getElementById('trip-secondary-details-card');
      const btn = document.getElementById('btn-toggle-tech-details');
      if (!card || !btn) return;
      const isHidden = card.classList.contains('hidden');
      if (isHidden) {
        card.classList.remove('hidden');
        btn.setAttribute('aria-expanded', 'true');
      } else {
        card.classList.add('hidden');
        btn.setAttribute('aria-expanded', 'false');
      }
    });

    // Trip Swap Button (Direct swap from results screen)
    document.getElementById('btn-trip-swap')?.addEventListener('click', () => {
      if (!this.lastSearchQuery) return;
      const { originText, destinationText } = this.lastSearchQuery;
      const origEl = document.getElementById('home-origin-display');
      const destEl = document.getElementById('home-destination-input');
      if (origEl) origEl.textContent = destinationText;
      if (destEl) destEl.value = originText;
      const tempLoc = this.originLocation;
      this.originLocation = this.destinationLocation;
      this.destinationLocation = tempLoc;
      this.showTripResults(destinationText, originText);
    });

    // Empty state CTA buttons
    document.getElementById('btn-empty-routes')?.addEventListener('click', () => {
      this.navigateTo('routes');
    });

    document.getElementById('btn-empty-back-home')?.addEventListener('click', () => {
      this.navigateTo('home');
    });

    // Reminder: capability disabled/hidden (no fake alert)
    const remindBtn = document.getElementById('btn-remind-trip');
    if (remindBtn) {
      remindBtn.disabled = true;
      remindBtn.classList.add('hidden');
    }

    // App Error State: Retry button
    document.getElementById('btn-retry-load')?.addEventListener('click', () => {
      this.retryLoad();
    });

    // Auto-retry when network connection restored
    window.addEventListener('online', () => {
      console.log('[DanabusApp] Network back online, attempting data reload...');
      if (this.loadState === 'error') {
        this.retryLoad();
      }
    });

    // Accessibility Keyboard Support: Enter & Space trigger click on [role="button"][tabindex="0"]
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        const target = e.target.closest('[role="button"][tabindex="0"]');
        if (target && target.tagName !== 'BUTTON' && target.tagName !== 'INPUT' && target.tagName !== 'A') {
          e.preventDefault();
          target.click();
        }
      }
    });
  }
}

// Instantiate and start on DOM loaded
window.app = new DanabusApp();
document.addEventListener('DOMContentLoaded', () => {
  window.app.init();
});
