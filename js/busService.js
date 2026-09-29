/**
 * Danabus Data & Search Service
 * Handles loading, querying, and searching of routes, stops, and schedules.
 */

class BusService {
  constructor() {
    this.routes = [];
    this.stops = [];
    this.streetsIndex = {};
    this.summary = {};
    this.isLoaded = false;
    this.isLoading = false;
    this.loadError = null;
  }

  async init() {
    if (this.isLoaded) return;
    this.isLoading = true;
    this.loadError = null;
    try {
      const [routesRes, stopsRes, streetsRes, summaryRes] = await Promise.all([
        fetch('data/danangbus_routes.json', { cache: 'no-cache' }),
        fetch('data/danangbus_stops.json', { cache: 'no-cache' }),
        fetch('data/danangbus_streets.json', { cache: 'no-cache' }),
        fetch('data/danangbus_summary.json', { cache: 'no-cache' })
      ]);

      if (!routesRes.ok || !stopsRes.ok || !streetsRes.ok || !summaryRes.ok) {
        throw new Error(`HTTP error loading datasets: routes=${routesRes.status}, stops=${stopsRes.status}`);
      }

      this.routes = await routesRes.json();
      this.stops = await stopsRes.json();
      this.streetsIndex = await streetsRes.json();
      this.summary = await summaryRes.json();
      this.isLoaded = true;
      this.isLoading = false;
      this.loadError = null;
      console.log(`[BusService] Loaded ${this.routes.length} routes and ${this.stops.length} stops.`);
    } catch (err) {
      this.isLoaded = false;
      this.isLoading = false;
      this.loadError = err;
      this.routes = [];
      this.stops = [];
      this.streetsIndex = {};
      this.summary = {};
      console.error('[BusService] Error loading data:', err);
      throw err;
    }
  }

  getLoadStatus() {
    return {
      isLoaded: this.isLoaded,
      isLoading: this.isLoading,
      error: this.loadError ? (this.loadError.message || String(this.loadError)) : null
    };
  }

  normalize(str) {
    return (str || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/đ/g, 'd')
      .trim();
  }

  getAllRoutes(category = 'all', query = '') {
    const q = this.normalize(query);
    return this.routes.filter(r => {
      // Category filter
      let matchCat = true;
      if (category === 'interprovincial') {
        matchCat = r.category === 'interprovincial' || r.shortName.includes('Hội An') || r.shortName.includes('Huế') || r.shortName.includes('Tam Kỳ');
      } else if (category === 'urban') {
        matchCat = r.category === 'subsidized' || (r.category === 'non_subsidized' && !r.shortName.includes('Tam Kỳ'));
      } else if (category === 'electric') {
        matchCat = Boolean(r.vehicleInfo && r.vehicleInfo.toLowerCase().includes('điện'));
      } else if (category === 'subsidized') {
        matchCat = r.category === 'subsidized';
      } else if (category === 'non_subsidized') {
        matchCat = r.category === 'non_subsidized';
      } else if (category === 'tourist') {
        matchCat = r.category === 'tourist';
      }

      if (!matchCat) return false;
      if (!q) return true;

      // Text search
      const numNorm = this.normalize(r.routeNumber);
      const nameNorm = this.normalize(r.name);
      const shortNorm = this.normalize(r.shortName);
      const origNorm = this.normalize(r.terminals?.origin);
      const destNorm = this.normalize(r.terminals?.destination);
      const formerNorm = this.normalize(r.formerName);
      const aliasesNorm = (r.aliases || []).map(a => this.normalize(a));

      // Match street names along route
      const streetsOut = (r.routePaths?.outbound?.streets || []).map(s => this.normalize(s));
      const streetsIn = (r.routePaths?.inbound?.streets || []).map(s => this.normalize(s));
      const matchStreet = [...streetsOut, ...streetsIn].some(st => st.includes(q));

      return (
        numNorm.includes(q) ||
        nameNorm.includes(q) ||
        shortNorm.includes(q) ||
        origNorm.includes(q) ||
        destNorm.includes(q) ||
        formerNorm.includes(q) ||
        aliasesNorm.some(a => a.includes(q)) ||
        matchStreet
      );
    });
  }

  getRouteById(id) {
    if (!id) return null;
    const cleanId = String(id).trim();
    return this.routes.find(r => 
      r.id === cleanId || 
      r.routeNumber === cleanId || 
      (r.aliases && r.aliases.includes(cleanId))
    );
  }

  getAllStops() {
    return this.stops;
  }

  searchStops(query = '') {
    const q = this.normalize(query);
    if (!q) return this.stops.slice(0, 30);

    return this.stops.filter(s => {
      const nameNorm = this.normalize(s.name);
      const streetNorm = this.normalize(s.street);
      const matchRoute = (s.routes || []).some(r => this.normalize(r.routeNumber).includes(q));
      return nameNorm.includes(q) || streetNorm.includes(q) || matchRoute;
    }).slice(0, 50);
  }

  getPopularDestinations() {
    return [
      {
        id: 'dest_hoian',
        name: 'Phố cổ Hội An',
        subtext: 'Bến xe buýt Hội An, Quảng Nam',
        icon: 'temple_buddhist',
        routes: ['02', 'LK02', '01SB', '01DL'],
        lat: 15.8794,
        lng: 108.335
      },
      {
        id: 'dest_cuadai',
        name: 'Bãi biển Cửa Đại',
        subtext: 'Bến tàu Cửa Đại, Hội An',
        icon: 'waves',
        routes: ['02', 'LK02', '01SB'],
        lat: 15.8942,
        lng: 108.3758
      },
      {
        id: 'dest_nguhanhson',
        name: 'Ngũ Hành Sơn (Marble Mountains)',
        subtext: 'Lê Văn Hiến, Q. Ngũ Hành Sơn',
        icon: 'landscape',
        routes: ['02', '11', '06', 'LK02'],
        lat: 16.0041,
        lng: 108.2618
      },
      {
        id: 'dest_caurong',
        name: 'Cầu Rồng & Công viên APEC',
        subtext: 'Nguyễn Văn Linh • Đường 2/9',
        icon: 'tour',
        routes: ['02', '06', '11', '07'],
        lat: 16.061,
        lng: 108.2235
      },
      {
        id: 'dest_sanbay',
        name: 'Sân bay Quốc tế Đà Nẵng',
        subtext: 'Ga Quốc nội T1 & Quốc tế T2',
        icon: 'flight',
        routes: ['03', '06', '12', '01SB'],
        lat: 16.0538,
        lng: 108.2022
      },
      {
        id: 'dest_banahills',
        name: 'Khu du lịch Bà Nà Hills',
        subtext: 'Khu du lịch Sun World Bà Nà',
        icon: 'attractions',
        routes: ['03'],
        lat: 15.9988,
        lng: 107.9947
      },
      {
        id: 'dest_benxett',
        name: 'Bến xe Trung tâm Đà Nẵng',
        subtext: '97-99 Cao Sơn Pháo, Hòa An',
        icon: 'directions_bus',
        routes: ['02', '05', '14', '21', 'LK01'],
        lat: 16.0628,
        lng: 108.1725
      },
      {
        id: 'dest_bvphusannhi',
        name: 'Bệnh viện Phụ sản - Nhi Đà Nẵng',
        subtext: 'Lê Văn Hiến, Q. Ngũ Hành Sơn',
        icon: 'local_hospital',
        routes: ['11', '02'],
        lat: 16.0275,
        lng: 108.243
      }
    ];
  }

  validateSearchQuery(originText = '', destinationText = '') {
    const oRaw = (originText || '').trim();
    const dRaw = (destinationText || '').trim();

    if (!oRaw || oRaw === 'Chọn điểm đón' || oRaw === 'Vị trí hiện tại') {
      return { valid: false, error: 'EMPTY_ORIGIN', message: 'Vui lòng chọn hoặc nhập điểm đón.' };
    }
    if (!dRaw) {
      return { valid: false, error: 'EMPTY_DESTINATION', message: 'Vui lòng chọn hoặc nhập điểm đến.' };
    }
    if (this.normalize(oRaw) === this.normalize(dRaw)) {
      return { valid: false, error: 'SAME_ORIGIN_DESTINATION', message: 'Điểm đón và điểm đến không được trùng nhau.' };
    }
    return { valid: true, error: null, message: '' };
  }

  resolveSearchTokens(queryNorm = '') {
    const q = this.normalize(queryNorm);
    if (!q) return [];

    const tokens = [q];
    if (q.includes('pho co hoi an') || q === 'hoi an') {
      tokens.push('pho co hoi an', 'hoi an');
    } else if (q.includes('ben xe tt') || q.includes('ben xe trung tam')) {
      tokens.push('ben xe tt', 'ben xe trung tam');
    } else if (q.includes('cau rong')) {
      tokens.push('cau rong');
    } else if (q.includes('cua dai')) {
      tokens.push('cua dai');
    } else if (q.includes('san bay')) {
      tokens.push('san bay');
    } else if (q.includes('ba na')) {
      tokens.push('ba na');
    } else if (q.includes('ngu hanh son')) {
      tokens.push('ngu hanh son');
    } else if (q.includes('phu san nhi')) {
      tokens.push('phu san nhi');
    }
    return Array.from(new Set(tokens.filter(t => t && t.length >= 2)));
  }

  stopMatchesQuery(stop, queryNorm, tokens, isFirst, isLast, terminals, dir) {
    if (!stop) return false;
    const nameNorm = this.normalize(stop.name || '');
    const streetNorm = this.normalize(stop.street || '');
    const displayNorm = this.normalize(stop.display_name || '');
    const fullText = `${nameNorm} ${streetNorm} ${displayNorm}`;

    for (const t of tokens) {
      if (t.length >= 2 && fullText.includes(t)) {
        return true;
      }
      if (nameNorm.length >= 3 && t.includes(nameNorm)) {
        return true;
      }
    }

    // Terminal matching at endpoints
    const termOrigin = this.normalize(terminals?.origin || '');
    const termDest = this.normalize(terminals?.destination || '');

    if (dir === 'outbound') {
      if (isFirst && tokens.some(t => termOrigin.includes(t))) return true;
      if (isLast && tokens.some(t => termDest.includes(t))) return true;
    } else if (dir === 'inbound') {
      if (isFirst && tokens.some(t => termDest.includes(t))) return true;
      if (isLast && tokens.some(t => termOrigin.includes(t))) return true;
    }

    return false;
  }

  findRoutesBetween(originText = '', destinationText = '') {
    const o = this.normalize(originText);
    const d = this.normalize(destinationText);

    if (!o || !d || o === d) return [];

    const oTokens = this.resolveSearchTokens(o);
    const dTokens = this.resolveSearchTokens(d);

    const matches = [];

    for (const r of this.routes) {
      if (r.status === 'suspended' || r.isActive === false) {
        continue;
      }

      for (const dir of ['outbound', 'inbound']) {
        const stops = r.stops?.[dir] || [];
        if (stops.length < 2) {
          continue;
        }

        const terminals = r.terminals || {};
        const nStops = stops.length;

        const origIndices = [];
        const destIndices = [];

        for (let i = 0; i < nStops; i++) {
          const s = stops[i];
          if (this.stopMatchesQuery(s, o, oTokens, i === 0, i === nStops - 1, terminals, dir)) {
            origIndices.push(i);
          }
          if (this.stopMatchesQuery(s, d, dTokens, i === 0, i === nStops - 1, terminals, dir)) {
            destIndices.push(i);
          }
        }

        // Monotonic check: originIndex < destinationIndex
        let validPair = null;
        for (const oi of origIndices) {
          for (const di of destIndices) {
            if (oi < di) {
              validPair = [oi, di];
              break;
            }
          }
          if (validPair) break;
        }

        if (validPair) {
          const [oi, di] = validPair;
          matches.push({
            ...r,
            route: r,
            matchedDirection: dir,
            originIndex: oi,
            destinationIndex: di,
            originStop: stops[oi],
            destinationStop: stops[di],
            stopCount: di - oi + 1
          });
        }
      }
    }

    return matches;
  }

  calculateNextDeparture(route, options = {}) {
    const pad = (n) => String(n).padStart(2, '0');
    const toTimeStr = (totalMin) => `${pad(Math.floor(totalMin / 60) % 24)}:${pad(totalMin % 60)}`;

    const unknownResult = (message = 'Chưa có thông tin lịch chạy') => ({
      status: 'unknown',
      timeStr: null,
      minutesUntilDeparture: null,
      minutesLeft: null,
      isOperating: false,
      isNextDay: false,
      source: 'unknown',
      message,
      trip: null
    });

    if (!route || typeof route !== 'object') {
      return unknownResult('Không tìm thấy thông tin tuyến');
    }

    if (route.status === 'suspended' || route.isActive === false) {
      return unknownResult('Tuyến đang tạm ngưng hoạt động');
    }

    // Parse options.currentTime
    let currentMinutes = 0;
    const ct = options.currentTime;
    if (typeof ct === 'number') {
      currentMinutes = Math.floor(ct);
      if (isNaN(currentMinutes) || currentMinutes < 0 || currentMinutes >= 1440) {
        currentMinutes = 0;
      }
    } else if (typeof ct === 'string') {
      const match = ct.trim().match(/^(\d{1,2}):(\d{2})$/);
      if (!match) return unknownResult('Thời gian chỉ định không hợp lệ');
      const h = parseInt(match[1], 10);
      const m = parseInt(match[2], 10);
      if (h < 0 || h > 23 || m < 0 || m > 59) return unknownResult('Thời gian chỉ định không hợp lệ');
      currentMinutes = h * 60 + m;
    } else if (ct instanceof Date) {
      currentMinutes = ct.getHours() * 60 + ct.getMinutes();
    } else {
      const now = new Date();
      currentMinutes = now.getHours() * 60 + now.getMinutes();
    }

    const direction = (options.direction === 'inbound') ? 'inbound' : 'outbound';
    const allowNextDay = (options.allowNextDay !== false);

    // 1. Timetable Priority
    const timetableTrips = (route.timetable && Array.isArray(route.timetable[direction])) ? route.timetable[direction] : null;
    if (timetableTrips && timetableTrips.length > 0) {
      const validTrips = [];
      for (const t of timetableTrips) {
        if (!t || typeof t.departureTime !== 'string') continue;
        const m = t.departureTime.trim().match(/^(\d{1,2}):(\d{2})$/);
        if (!m) continue;
        const hh = parseInt(m[1], 10);
        const mm = parseInt(m[2], 10);
        if (hh < 0 || hh > 23 || mm < 0 || mm > 59) continue;
        validTrips.push({
          timeStr: `${pad(hh)}:${pad(mm)}`,
          totalMinutes: hh * 60 + mm,
          trip: t
        });
      }

      if (validTrips.length > 0) {
        validTrips.sort((a, b) => a.totalMinutes - b.totalMinutes);
        const firstTrip = validTrips[0];

        // Before service window today
        if (currentMinutes < firstTrip.totalMinutes) {
          const diff = firstTrip.totalMinutes - currentMinutes;
          return {
            status: 'before_service',
            timeStr: firstTrip.timeStr,
            minutesUntilDeparture: diff,
            minutesLeft: diff,
            isOperating: false,
            isNextDay: false,
            source: 'timetable',
            message: `Chưa đến giờ hoạt động (chuyến đầu: ${firstTrip.timeStr})`,
            trip: firstTrip.trip
          };
        }

        // In service window today
        const nextTrip = validTrips.find(t => t.totalMinutes >= currentMinutes);
        if (nextTrip) {
          const diff = nextTrip.totalMinutes - currentMinutes;
          return {
            status: 'in_service',
            timeStr: nextTrip.timeStr,
            minutesUntilDeparture: diff,
            minutesLeft: diff,
            isOperating: true,
            isNextDay: false,
            source: 'timetable',
            message: `Đang hoạt động (chuyến tới: ${nextTrip.timeStr})`,
            trip: nextTrip.trip
          };
        }

        // After service window today
        if (allowNextDay) {
          const diff = (1440 - currentMinutes) + firstTrip.totalMinutes;
          return {
            status: 'next_day',
            timeStr: firstTrip.timeStr,
            minutesUntilDeparture: diff,
            minutesLeft: diff,
            isOperating: false,
            isNextDay: true,
            source: 'timetable',
            message: `Chuyến kế tiếp vào ngày mai (${firstTrip.timeStr})`,
            trip: firstTrip.trip
          };
        } else {
          return {
            status: 'after_service',
            timeStr: null,
            minutesUntilDeparture: null,
            minutesLeft: null,
            isOperating: false,
            isNextDay: false,
            source: 'timetable',
            message: 'Đã hết chuyến hôm nay',
            trip: null
          };
        }
      }
    }

    // 2. Frequency & Operating Hours
    if (!route.operatingHours || typeof route.operatingHours !== 'object') {
      return unknownResult('Thiếu thông tin giờ hoạt động');
    }

    const startStr = typeof route.operatingHours.start === 'string' ? route.operatingHours.start.trim() : '';
    const endStr = typeof route.operatingHours.end === 'string' ? route.operatingHours.end.trim() : '';
    const startMatch = startStr.match(/^(\d{1,2}):(\d{2})$/);
    const endMatch = endStr.match(/^(\d{1,2}):(\d{2})$/);

    if (!startMatch || !endMatch) {
      return unknownResult('Giờ hoạt động không hợp lệ');
    }

    const startH = parseInt(startMatch[1], 10);
    const startM = parseInt(startMatch[2], 10);
    const endH = parseInt(endMatch[1], 10);
    const endM = parseInt(endMatch[2], 10);

    if (startH < 0 || startH > 23 || startM < 0 || startM > 59 ||
        endH < 0 || endH > 23 || endM < 0 || endM > 59) {
      return unknownResult('Giờ hoạt động không hợp lệ');
    }

    const startTotal = startH * 60 + startM;
    const endTotal = endH * 60 + endM;

    if (startTotal >= endTotal) {
      return unknownResult('Khung giờ hoạt động không hợp lệ');
    }

    const formattedStart = `${pad(startH)}:${pad(startM)}`;
    const rawLower = (route.operatingHours.raw || '').toLowerCase();

    if (!route.frequency || typeof route.frequency !== 'object') {
      return unknownResult('Thiếu thông tin tần suất chạy xe');
    }

    const freq = route.frequency;
    const isIrregular = route.operatingHours.irregular === true ||
                        freq.type === 'irregular' ||
                        rawLower.includes('chuyến bay') ||
                        rawLower.includes('giờ bay');

    const min = (typeof freq.minMinutes === 'number' && Number.isFinite(freq.minMinutes) && freq.minMinutes > 0) ? freq.minMinutes : null;
    const max = (typeof freq.maxMinutes === 'number' && Number.isFinite(freq.maxMinutes) && freq.maxMinutes > 0) ? freq.maxMinutes : null;
    const peak = (typeof freq.peakMinutes === 'number' && Number.isFinite(freq.peakMinutes) && freq.peakMinutes > 0) ? freq.peakMinutes : null;
    const offPeak = (typeof freq.offPeakMinutes === 'number' && Number.isFinite(freq.offPeakMinutes) && freq.offPeakMinutes > 0) ? freq.offPeakMinutes : null;

    if (!isIrregular && min == null && max == null && peak == null && offPeak == null) {
      return unknownResult('Tần suất chạy xe không hợp lệ hoặc chưa xác định');
    }

    // Case 1: Before service
    if (currentMinutes < startTotal) {
      if (isIrregular) {
        return {
          status: 'before_service',
          timeStr: null,
          minutesUntilDeparture: null,
          minutesLeft: null,
          isOperating: false,
          isNextDay: false,
          source: 'frequency',
          message: `Chưa đến khung giờ hoạt động (mở tuyến: ${formattedStart})`,
          trip: null
        };
      }

      const diff = startTotal - currentMinutes;
      return {
        status: 'before_service',
        timeStr: formattedStart,
        minutesUntilDeparture: diff,
        minutesLeft: diff,
        isOperating: false,
        isNextDay: false,
        source: 'frequency',
        message: `Chưa đến giờ hoạt động (chuyến đầu: ${formattedStart})`,
        trip: null
      };
    }

    // Case 2: During service
    if (currentMinutes <= endTotal) {
      if (isIrregular) {
        return {
          status: 'in_service',
          timeStr: null,
          minutesUntilDeparture: null,
          minutesLeft: null,
          isOperating: true,
          isNextDay: false,
          source: 'frequency',
          message: `Đang hoạt động (${this.formatRouteFrequency(route)})`,
          trip: null
        };
      }

      const isRange = freq.type === 'range';
      const hasExactHeadway = (freq.exactHeadway === true) ||
                              (freq.type === 'fixed') ||
                              (!isRange && peak != null && offPeak != null && peak === offPeak);

      if (hasExactHeadway) {
        const interval = peak ?? offPeak ?? min ?? max;
        if (interval && interval > 0) {
          const elapsed = currentMinutes - startTotal;
          const count = Math.ceil(elapsed / interval);
          const nextDepartureTotal = startTotal + (count * interval);

          if (nextDepartureTotal <= endTotal) {
            const diff = nextDepartureTotal - currentMinutes;
            const timeStr = toTimeStr(nextDepartureTotal);
            return {
              status: 'in_service',
              timeStr: timeStr,
              minutesUntilDeparture: diff,
              minutesLeft: diff,
              isOperating: true,
              isNextDay: false,
              source: 'frequency',
              message: `Đang hoạt động (chuyến tới: ${timeStr})`,
              trip: null
            };
          }
          // If nextDepartureTotal > endTotal, all departures within service window have passed
        }
      } else {
        // Range frequency without exact peak/off-peak operating window:
        // Do not fabricate exact headway departure times to avoid false precision.
        return {
          status: 'in_service',
          timeStr: null,
          minutesUntilDeparture: null,
          minutesLeft: null,
          isOperating: true,
          isNextDay: false,
          source: 'frequency',
          message: `Đang hoạt động (tần suất ${this.formatRouteFrequency(route)})`,
          trip: null
        };
      }
    }

    // Case 3: After service / Next day
    if (allowNextDay && !isIrregular) {
      const diff = (1440 - currentMinutes) + startTotal;
      return {
        status: 'next_day',
        timeStr: formattedStart,
        minutesUntilDeparture: diff,
        minutesLeft: diff,
        isOperating: false,
        isNextDay: true,
        source: 'frequency',
        message: `Chuyến kế tiếp vào ngày mai (${formattedStart})`,
        trip: null
      };
    } else {
      return {
        status: 'after_service',
        timeStr: null,
        minutesUntilDeparture: null,
        minutesLeft: null,
        isOperating: false,
        isNextDay: false,
        source: 'frequency',
        message: 'Đã hết chuyến hôm nay',
        trip: null
      };
    }
  }

  formatRouteFare(route) {
    if (!route || !route.fares) return 'Đang cập nhật';
    const f = route.fares;
    if (f.type === 'flat') {
      const price = f.flatPrice ?? f.singleTicket;
      if (price != null) {
        return `${Number(price).toLocaleString('vi-VN')}đ`;
      }
      return 'Đang cập nhật';
    }
    if (f.type === 'distance_tiered') {
      if (f.minPrice != null && f.maxPrice != null) {
        if (f.minPrice === f.maxPrice) {
          return `${Number(f.minPrice).toLocaleString('vi-VN')}đ`;
        }
        return `${Number(f.minPrice).toLocaleString('vi-VN')}đ - ${Number(f.maxPrice).toLocaleString('vi-VN')}đ`;
      }
      if (f.minPrice != null) {
        return `Từ ${Number(f.minPrice).toLocaleString('vi-VN')}đ`;
      }
      return 'Theo chặng';
    }
    if (f.type === 'unknown') {
      return 'Đang cập nhật';
    }
    if (f.singleTicket != null) {
      return `${Number(f.singleTicket).toLocaleString('vi-VN')}đ`;
    }
    return 'Đang cập nhật';
  }

  formatRouteFrequency(route, short = false) {
    if (!route || !route.frequency || typeof route.frequency !== 'object') {
      return 'Đang cập nhật';
    }
    const f = route.frequency;
    const unit = short ? 'p' : ' phút';

    if (f.type === 'irregular') {
      if (typeof f.raw === 'string' && f.raw.trim()) {
        const rawLower = f.raw.toLowerCase();
        if (rawLower.includes('lịch bay') || rawLower.includes('chuyến bay')) {
          return short ? 'Lịch bay' : 'Theo lịch bay';
        }
        if (rawLower.includes('du lịch') || rawLower.includes('tham quan')) {
          return short ? 'Du lịch' : 'Theo tour du lịch';
        }
        return f.raw.trim();
      }
      return 'Đang cập nhật';
    }

    const min = (typeof f.minMinutes === 'number' && Number.isFinite(f.minMinutes) && f.minMinutes > 0) ? f.minMinutes : null;
    const max = (typeof f.maxMinutes === 'number' && Number.isFinite(f.maxMinutes) && f.maxMinutes > 0) ? f.maxMinutes : null;
    const peak = (typeof f.peakMinutes === 'number' && Number.isFinite(f.peakMinutes) && f.peakMinutes > 0) ? f.peakMinutes : null;
    const offPeak = (typeof f.offPeakMinutes === 'number' && Number.isFinite(f.offPeakMinutes) && f.offPeakMinutes > 0) ? f.offPeakMinutes : null;

    const lower = min ?? peak;
    const upper = max ?? offPeak;

    if (lower != null && upper != null) {
      if (lower === upper) {
        return `${lower}${unit}`;
      }
      return `${lower}-${upper}${unit}`;
    }
    if (lower != null) {
      return `${lower}${unit}`;
    }
    if (upper != null) {
      return `${upper}${unit}`;
    }
    if (typeof f.raw === 'string' && f.raw.trim()) {
      return f.raw.trim();
    }
    return 'Đang cập nhật';
  }

  formatRouteOperatingHours(route) {
    if (!route || !route.operatingHours || typeof route.operatingHours !== 'object') {
      return 'Đang cập nhật';
    }
    const { start, end } = route.operatingHours;
    if (!start || !end) return 'Đang cập nhật';
    const padTime = (t) => {
      const parts = String(t).trim().split(':');
      if (parts.length === 2) {
        return `${parts[0].padStart(2, '0')}:${parts[1].padStart(2, '0')}`;
      }
      return t;
    };
    return `${padTime(start)} - ${padTime(end)}`;
  }

  formatFare(val) {
    if (val == null || val === '') return 'Đang cập nhật';
    return `${Number(val).toLocaleString('vi-VN')}đ`;
  }

  formatRouteVehicleInfo(route) {
    if (!route || !route.vehicleInfo || typeof route.vehicleInfo !== 'string' || !route.vehicleInfo.trim()) {
      return {
        brand: 'Chưa có dữ liệu',
        capacity: '',
        description: 'Phương tiện'
      };
    }
    const raw = route.vehicleInfo;
    let brand = null;
    const brandMatch = raw.match(/(?:Nhãn hiệu|Nhãn hiệu):\s*([^;\n]+)/i);
    if (brandMatch) {
      brand = brandMatch[1].trim();
    } else if (raw.trim().startsWith('GAZ')) {
      brand = 'GAZ';
    }

    let capacity = '';
    const capMatch = raw.match(/(?:Sức chứa|sức chứa):\s*([^;\n]+)/i);
    if (capMatch) {
      capacity = capMatch[1].trim();
    }

    const isElectric = raw.toLowerCase().includes('điện');

    return {
      brand: brand || (isElectric ? 'Xe buýt điện' : 'Chưa có dữ liệu'),
      capacity: capacity,
      description: capacity || (isElectric ? 'Xe buýt điện' : 'Xe buýt')
    };
  }

  isRoutePlanningReady(route) {
    if (!route || !route.dataQuality) return false;
    return Boolean(route.dataQuality.tripPlanningReady);
  }

  isDirectionPlanningReady(route, direction) {
    if (!route || !route.dataQuality || !route.dataQuality.directions) return false;
    return Boolean(route.dataQuality.directions[direction]?.eligibleForPlanning);
  }

  getPlanningReadyRoutes() {
    return this.routes.filter(r => this.isRoutePlanningReady(r));
  }

  findNearbyStops(lat, lng, options) {
    return findNearbyStops(this.stops, lat, lng, options);
  }
}

/**
 * Haversine formula to compute great-circle distance between two GPS coordinates in meters.
 * Fail-closed: returns null if any coordinate is invalid, non-numeric, non-finite, or out of range.
 * @param {number} lat1 
 * @param {number} lon1 
 * @param {number} lat2 
 * @param {number} lon2 
 * @returns {number|null} distance in meters, or null on invalid coordinates
 */
function haversineDistance(lat1, lon1, lat2, lon2) {
  if (
    lat1 == null || lon1 == null || lat2 == null || lon2 == null ||
    typeof lat1 !== 'number' || typeof lon1 !== 'number' ||
    typeof lat2 !== 'number' || typeof lon2 !== 'number' ||
    !Number.isFinite(lat1) || !Number.isFinite(lon1) ||
    !Number.isFinite(lat2) || !Number.isFinite(lon2)
  ) {
    return null;
  }

  if (lat1 < -90 || lat1 > 90 || lat2 < -90 || lat2 > 90 ||
      lon1 < -180 || lon1 > 180 || lon2 < -180 || lon2 > 180) {
    return null;
  }

  const R = 6371000; // Mean Earth radius in meters
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const radLat1 = lat1 * Math.PI / 180;
  const radLat2 = lat2 * Math.PI / 180;

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(radLat1) * Math.cos(radLat2) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  const d = R * c;

  return Math.round(d * 10) / 10;
}

/**
 * Spatial query for nearby bus stops within a maximum distance.
 * Fail-closed guarantees:
 * - Only verified stops with valid finite coordinates are considered.
 * - Stops with status !== 'verified' (e.g. unresolved) are strictly excluded.
 * - Candidates are sorted ascending by distanceMeters.
 * - Results are sliced to limit.
 * 
 * @param {Array<Object>} stops - List of stops to search
 * @param {number} lat - Query latitude
 * @param {number} lng - Query longitude
 * @param {Object} [options] - Search options
 * @param {number} [options.maxDistanceMeters=1000] - Search radius in meters
 * @param {number} [options.limit=10] - Maximum number of candidates to return
 * @returns {Array<Object>} List of candidate stops with distanceMeters property
 */
function findNearbyStops(stops, lat, lng, options = {}) {
  if (
    !Array.isArray(stops) ||
    lat == null || lng == null ||
    typeof lat !== 'number' || typeof lng !== 'number' ||
    !Number.isFinite(lat) || !Number.isFinite(lng)
  ) {
    return [];
  }

  if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
    return [];
  }

  const maxDistance = (options && typeof options.maxDistanceMeters === 'number' && Number.isFinite(options.maxDistanceMeters) && options.maxDistanceMeters >= 0)
    ? options.maxDistanceMeters
    : 1000;

  const limit = (options && typeof options.limit === 'number' && Number.isFinite(options.limit) && options.limit > 0)
    ? options.limit
    : 10;

  const candidates = [];

  for (const stop of stops) {
    if (!stop || typeof stop !== 'object') continue;

    // Strict fail-closed: only verified stops with valid finite coordinates
    if (stop.status !== 'verified') continue;
    if (
      stop.lat == null || stop.lng == null ||
      typeof stop.lat !== 'number' || typeof stop.lng !== 'number' ||
      !Number.isFinite(stop.lat) || !Number.isFinite(stop.lng)
    ) {
      continue;
    }
    if (stop.lat < -90 || stop.lat > 90 || stop.lng < -180 || stop.lng > 180) {
      continue;
    }

    const dist = haversineDistance(lat, lng, stop.lat, stop.lng);
    if (dist === null || dist > maxDistance) continue;

    candidates.push({
      ...stop,
      distanceMeters: dist
    });
  }

  candidates.sort((a, b) => a.distanceMeters - b.distanceMeters);

  return candidates.slice(0, limit);
}

// Global singleton instance
if (typeof window !== 'undefined') {
  window.BusService = BusService;
  window.busService = new BusService();
  window.haversineDistance = haversineDistance;
  window.findNearbyStops = findNearbyStops;
}

/**
 * =========================================================================
 * TASK 4: ADDRESS-TO-ADDRESS TRIP PLANNER MODULES
 * - ResolvedLocation
 * - LocationSearchProvider / LocalLocationProvider / LocationManager
 * - WalkingRouter (strictly estimated semantics with geometry=null when estimated)
 * - TransitPlanner (independent, eligibleForPlanning fail-closed, direct + max 1 transfer, detour ratio <= 1.8)
 * =========================================================================
 */

class ResolvedLocation {
  constructor({ displayName, address, lat, lng, provider = 'local', providerId = null, type = 'poi' }) {
    this.displayName = displayName || 'Vị trí';
    this.address = address || displayName || '';
    this.lat = typeof lat === 'number' && Number.isFinite(lat) ? lat : null;
    this.lng = typeof lng === 'number' && Number.isFinite(lng) ? lng : null;
    this.provider = provider;
    this.providerId = providerId || `${provider}_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
    this.type = type; // 'poi' | 'address' | 'stop' | 'gps'
  }

  isValid() {
    return (
      typeof this.lat === 'number' &&
      typeof this.lng === 'number' &&
      Number.isFinite(this.lat) &&
      Number.isFinite(this.lng) &&
      this.lat >= -90 && this.lat <= 90 &&
      this.lng >= -180 && this.lng <= 180
    );
  }
}

class LocationSearchProvider {
  constructor(name = 'base') {
    this.name = name;
  }
  async search(query, options = {}) { throw new Error('Not implemented'); }
  async resolve(providerId, item = null) { throw new Error('Not implemented'); }
  async reverseGeocode(lat, lng) { throw new Error('Not implemented'); }
}

class LocalLocationProvider extends LocationSearchProvider {
  constructor(busService = null) {
    super('local');
    this.busService = busService;
    this.localPOIs = [
      {
        id: 'poi_bx_tt',
        displayName: 'Bến xe Trung tâm Đà Nẵng',
        address: 'Tôn Đức Thắng, Hòa Minh, Liên Chiểu, Đà Nẵng',
        lat: 16.0617,
        lng: 108.1834,
        type: 'poi',
        keywords: ['ben xe', 'trung tam', 'ton duc thang', 'lien chieu']
      },
      {
        id: 'poi_hoi_an',
        displayName: 'Phố cổ Hội An',
        address: 'Phường Minh An, TP. Hội An, Quảng Nam',
        lat: 15.8778,
        lng: 108.3283,
        type: 'poi',
        keywords: ['pho co', 'hoi an', 'chua cau', 'tran phu']
      },
      {
        id: 'poi_cau_rong',
        displayName: 'Cầu Rồng Đà Nẵng',
        address: 'Nguyễn Văn Linh - Võ Văn Kiệt, Hải Châu, Đà Nẵng',
        lat: 16.0612,
        lng: 108.2272,
        type: 'poi',
        keywords: ['cau rong', 'dragon bridge', 'nguyen van linh']
      },
      {
        id: 'poi_san_bay',
        displayName: 'Sân bay Quốc tế Đà Nẵng',
        address: 'Duy Tân, Hòa Thuận Tây, Hải Châu, Đà Nẵng',
        lat: 16.0538,
        lng: 108.1995,
        type: 'poi',
        keywords: ['san bay', 'airport', 'duy tan']
      },
      {
        id: 'poi_bv_danang',
        displayName: 'Bệnh viện Đa khoa Đà Nẵng',
        address: '124 Hải Phòng, Thạch Thang, Hải Châu, Đà Nẵng',
        lat: 16.0734,
        lng: 108.2163,
        type: 'poi',
        keywords: ['benh vien da khoa', 'hai phong', 'bv da nang']
      },
      {
        id: 'poi_bv_psn',
        displayName: 'Bệnh viện Phụ sản - Nhi Đà Nẵng',
        address: '402 Lê Văn Hiến, Khuê Mỹ, Ngũ Hành Sơn, Đà Nẵng',
        lat: 16.0305,
        lng: 108.2435,
        type: 'poi',
        keywords: ['benh vien phu san nhi', 'le van hien']
      },
      {
        id: 'poi_dh_bachkhoa',
        displayName: 'Trường Đại học Bách Khoa - ĐHĐN',
        address: '54 Nguyễn Lương Bằng, Hòa Khánh Bắc, Liên Chiểu, Đà Nẵng',
        lat: 16.0754,
        lng: 108.1528,
        type: 'poi',
        keywords: ['dai hoc bach khoa', 'nguyen luong bang', 'hoa khanh']
      },
      {
        id: 'poi_cho_han',
        displayName: 'Chợ Hàn Đà Nẵng',
        address: '119 Trần Phú, Hải Châu 1, Hải Châu, Đà Nẵng',
        lat: 16.0682,
        lng: 108.2245,
        type: 'poi',
        keywords: ['cho han', 'tran phu']
      },
      {
        id: 'poi_cho_con',
        displayName: 'Chợ Cồn Đà Nẵng',
        address: '290 Hùng Vương, Vĩnh Trung, Hải Châu, Đà Nẵng',
        lat: 16.0688,
        lng: 108.2148,
        type: 'poi',
        keywords: ['cho con', 'hung vuong']
      },
      {
        id: 'poi_cv_biendong',
        displayName: 'Công viên Biển Đông',
        address: 'Võ Nguyên Giáp, Phước Mỹ, Sơn Trà, Đà Nẵng',
        lat: 16.0687,
        lng: 108.2464,
        type: 'poi',
        keywords: ['cong vien bien dong', 'vo nguyen giap', 'my khe']
      },
      {
        id: 'poi_ngu_hanh_son',
        displayName: 'Danh thắng Ngũ Hành Sơn',
        address: '81 Huyền Trân Công Chúa, Hòa Hải, Ngũ Hành Sơn, Đà Nẵng',
        lat: 16.0044,
        lng: 108.2636,
        type: 'poi',
        keywords: ['ngu hanh son', 'marble mountains']
      },
      {
        id: 'poi_hoa_hiep_nam',
        displayName: 'Khu chung cư Hoà Hiệp Nam',
        address: 'Đường Hướng Dương 2, Hòa Hiệp Nam, Liên Chiểu, Đà Nẵng',
        lat: 16.1084,
        lng: 108.1322,
        type: 'poi',
        keywords: ['hoa hiep nam', 'chung cu']
      },
      {
        id: 'poi_bx_tamky',
        displayName: 'Bến xe Thành phố Tam Kỳ',
        address: 'Hùng Vương, An Sơn, Tam Kỳ, Quảng Nam',
        lat: 15.5684,
        lng: 108.4816,
        type: 'poi',
        keywords: ['ben xe tam ky', 'tam ky', 'hung vuong']
      },
      {
        id: 'poi_my_khe',
        displayName: 'Bãi biển Mỹ Khê',
        address: 'Võ Nguyên Giáp, Phước Mỹ, Sơn Trà, Đà Nẵng',
        lat: 16.0592,
        lng: 108.2458,
        type: 'poi',
        keywords: ['bai bien my khe', 'my khe']
      },
      {
        id: 'addr_123_nvl',
        displayName: '123 Nguyễn Văn Linh',
        address: '123 Nguyễn Văn Linh, Nam Dương, Hải Châu, Đà Nẵng',
        lat: 16.0615,
        lng: 108.2195,
        type: 'address',
        keywords: ['123 nguyen van linh']
      },
      {
        id: 'addr_817_nlb',
        displayName: '817 Nguyễn Lương Bằng',
        address: '817 Nguyễn Lương Bằng, Hòa Hiệp Nam, Liên Chiểu, Đà Nẵng',
        lat: 16.1050,
        lng: 108.1328,
        type: 'address',
        keywords: ['817 nguyen luong bang']
      },
      {
        id: 'addr_456_ld',
        displayName: '456 Lê Duẩn',
        address: '456 Lê Duẩn, Chính Gián, Thanh Khê, Đà Nẵng',
        lat: 16.0695,
        lng: 108.2110,
        type: 'address',
        keywords: ['456 le duan']
      },
      {
        id: 'poi_bv_ung_buou',
        displayName: 'Bệnh viện Ung Bướu Đà Nẵng',
        address: 'Hoàng Thị Loan, Hòa Minh, Liên Chiểu, Đà Nẵng',
        lat: 16.0792,
        lng: 108.1631,
        type: 'poi',
        keywords: ['benh vien ung buou', 'ung buou']
      }
    ];
  }

  normalize(str) {
    return (str || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/đ/g, 'd')
      .trim();
  }

  async search(query, options = {}) {
    const q = this.normalize(query);
    if (!q || q.length < 2) return [];

    const limit = options.limit || 8;
    const matches = [];

    // Search Curated POIs
    for (const item of this.localPOIs) {
      const nameNorm = this.normalize(item.displayName);
      const addrNorm = this.normalize(item.address);
      const kwNorm = (item.keywords || []).map(k => this.normalize(k));

      if (nameNorm.includes(q) || addrNorm.includes(q) || kwNorm.some(k => k.includes(q) || q.includes(k))) {
        matches.push({
          id: item.id,
          displayName: item.displayName,
          address: item.address,
          lat: item.lat,
          lng: item.lng,
          type: item.type,
          provider: 'local',
          score: nameNorm.startsWith(q) ? 100 : (nameNorm.includes(q) ? 80 : 50)
        });
      }
    }

    // Search Verified Bus Stops
    const bs = this.busService || (typeof window !== 'undefined' ? window.busService : null);
    if (bs && Array.isArray(bs.stops)) {
      for (const stop of bs.stops) {
        if (stop.status !== 'verified' || !stop.lat || !stop.lng) continue;
        const sNameNorm = this.normalize(stop.name);
        const sStreetNorm = this.normalize(stop.street);
        if (sNameNorm.includes(q) || sStreetNorm.includes(q)) {
          matches.push({
            id: `stop_${stop.stopId || stop.osm_id || Math.random()}`,
            displayName: stop.name,
            address: stop.street ? `Đường ${stop.street}, Đà Nẵng` : 'Trạm xe buýt Đà Nẵng',
            lat: stop.lat,
            lng: stop.lng,
            type: 'stop',
            provider: 'local',
            score: sNameNorm.startsWith(q) ? 90 : 60
          });
        }
      }
    }

    matches.sort((a, b) => b.score - a.score);
    const deduped = [];
    const seen = new Set();
    for (const m of matches) {
      const key = `${m.lat.toFixed(4)},${m.lng.toFixed(4)}`;
      if (!seen.has(key)) {
        seen.add(key);
        deduped.push(m);
        if (deduped.length >= limit) break;
      }
    }
    return deduped;
  }

  async resolve(providerId, item = null) {
    if (item && typeof item.lat === 'number' && typeof item.lng === 'number') {
      return new ResolvedLocation(item);
    }
    const found = this.localPOIs.find(p => p.id === providerId);
    if (found) return new ResolvedLocation(found);
    return null;
  }
}

class LocationManager {
  constructor(busService = null) {
    this.localProvider = new LocalLocationProvider(busService);
    this.activeProvider = this.localProvider;
    this.cache = new Map();
  }

  setBusService(busService) {
    this.localProvider.busService = busService;
  }

  async search(query, options = {}) {
    const trimmed = (query || '').trim();
    if (!trimmed || trimmed.length < 2) return [];
    const cacheKey = `search_${trimmed}`;
    if (this.cache.has(cacheKey)) return this.cache.get(cacheKey);

    const results = await this.localProvider.search(trimmed, options);
    this.cache.set(cacheKey, results);
    return results;
  }

  async resolve(providerId, item = null) {
    return this.localProvider.resolve(providerId, item);
  }

  resolveFromCoordinates(lat, lng, displayName = 'Vị trí đã chọn') {
    return new ResolvedLocation({
      displayName,
      address: displayName,
      lat,
      lng,
      provider: 'gps',
      type: 'gps'
    });
  }

  async getCurrentLocation() {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      return { success: false, error: 'Trình duyệt không hỗ trợ định vị GPS.' };
    }
    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = pos.coords.latitude;
          const lng = pos.coords.longitude;
          const accuracy = pos.coords.accuracy;
          resolve({
            success: true,
            location: new ResolvedLocation({
              displayName: 'Vị trí hiện tại',
              address: `Tọa độ GPS (±${Math.round(accuracy)}m)`,
              lat,
              lng,
              provider: 'gps',
              type: 'gps'
            }),
            coords: { latitude: lat, longitude: lng, accuracy }
          });
        },
        (err) => {
          let msg = 'Không thể xác định vị trí hiện tại.';
          if (err.code === 1) msg = 'Quyền truy cập vị trí đã bị từ chối.';
          else if (err.code === 2) msg = 'Vị trí hiện không khả dụng.';
          else if (err.code === 3) msg = 'Quá thời gian yêu cầu vị trí GPS.';
          resolve({ success: false, error: msg, code: err.code });
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 }
      );
    });
  }
}

/**
 * WalkingRouter
 * Strict semantic separation:
 * When routing via straight-line Haversine, distance is marked as estimated with geometry=null.
 * NEVER masquerades straight line as real road walking geometry.
 */
class WalkingRouter {
  constructor(options = {}) {
    this.walkingSpeedMetersPerMinute = options.walkingSpeedMetersPerMinute || 75; // ~4.5 km/h
  }

  route(fromCoords, toCoords) {
    if (!Array.isArray(fromCoords) || !Array.isArray(toCoords) || fromCoords.length < 2 || toCoords.length < 2) {
      return null;
    }
    const [lat1, lng1] = fromCoords;
    const [lat2, lng2] = toCoords;
    const dist = haversineDistance(lat1, lng1, lat2, lng2);
    if (dist === null) return null;

    const roundedDist = Math.round(dist);
    const durationMinutes = Math.max(1, Math.round(roundedDist / this.walkingSpeedMetersPerMinute));

    return {
      distanceMeters: roundedDist,
      durationMinutes,
      isEstimated: true,
      geometry: null, // STRICT: geometry is null for estimated walking
      method: 'haversine_estimate',
      fromCoords: [lat1, lng1],
      toCoords: [lat2, lng2]
    };
  }

  createWalkingLeg(fromLabel, toLabel, fromCoords, toCoords) {
    const r = this.route(fromCoords, toCoords);
    if (!r) return null;
    return {
      type: 'walking',
      fromLabel,
      toLabel,
      distanceMeters: r.distanceMeters,
      durationMinutes: r.durationMinutes,
      isEstimated: true,
      geometry: null,
      fromCoords,
      toCoords,
      summary: `Đi bộ ước tính ~${r.distanceMeters}m (${r.durationMinutes} phút)`
    };
  }
}

/**
 * TransitPlanner
 * Independent from Google and realtime.
 * Direct + maximum 1 transfer routing, detour ratio <= 1.8,
 * fail-closed on unverified geometry or ineligible directions.
 */
class TransitPlanner {
  constructor(busService, walkingRouter = null) {
    this.busService = busService;
    this.walkingRouter = walkingRouter || new WalkingRouter();
    this.MAX_WALK_METERS = 1200;
    this.MAX_TRANSFER_WALK_METERS = 400;
    this.MAX_DETOUR_RATIO = 1.8; // STRICT: <= 1.8 per TL decision
  }

  planTrip(originLocation, destLocation, options = {}) {
    if (!originLocation || !destLocation || !originLocation.isValid || !destLocation.isValid) {
      return { trips: [], error: 'INVALID_ENDPOINTS', message: 'Điểm đón hoặc điểm đến không hợp lệ' };
    }
    if (!originLocation.isValid() || !destLocation.isValid()) {
      return { trips: [], error: 'INVALID_COORDINATES', message: 'Tọa độ điểm đi/đến không hợp lệ' };
    }

    const straightDist = haversineDistance(originLocation.lat, originLocation.lng, destLocation.lat, destLocation.lng);
    if (straightDist === null) {
      return { trips: [], error: 'COORDINATE_ERROR', message: 'Lỗi tính toán khoảng cách' };
    }
    if (straightDist < 50) {
      return { trips: [], error: 'SAME_LOCATION', message: 'Điểm đón và điểm đến quá gần nhau' };
    }

    // Step 1: Spatial candidate search
    const originCandidates = this.busService.findNearbyStops(originLocation.lat, originLocation.lng, {
      maxDistanceMeters: this.MAX_WALK_METERS,
      limit: 10
    });
    const destCandidates = this.busService.findNearbyStops(destLocation.lat, destLocation.lng, {
      maxDistanceMeters: this.MAX_WALK_METERS,
      limit: 10
    });

    if (originCandidates.length === 0 || destCandidates.length === 0) {
      return {
        trips: [],
        error: 'NO_NEARBY_STOPS',
        message: 'Không tìm thấy trạm dừng xe buýt nào gần điểm đón hoặc điểm đến trong bán kính đi bộ'
      };
    }

    const eligibleRoutes = this.busService.routes.filter(r => r.status === 'active' && r.isActive !== false);
    const trips = [];

    // Step 2: Direct Trip Search
    for (const r of eligibleRoutes) {
      for (const dir of ['outbound', 'inbound']) {
        if (!this.busService.isDirectionPlanningReady(r, dir)) {
          continue; // Fail-closed on ineligible directions
        }

        const stops = r.stops?.[dir] || [];
        if (stops.length < 2) continue;

        // Match origin and dest candidates along this route direction
        for (const oCand of originCandidates) {
          const oi = stops.findIndex(s => s.name === oCand.name || (s.lat && oCand.lat && Math.abs(s.lat - oCand.lat) < 0.0001 && Math.abs(s.lng - oCand.lng) < 0.0001));
          if (oi < 0) continue;

          for (const dCand of destCandidates) {
            const di = stops.findIndex(s => s.name === dCand.name || (s.lat && dCand.lat && Math.abs(s.lat - dCand.lat) < 0.0001 && Math.abs(s.lng - dCand.lng) < 0.0001));
            if (di < 0 || oi >= di) continue; // Monotonic order: oi < di

            const boardStop = stops[oi];
            const alightStop = stops[di];
            const stopsCount = di - oi;

            // Sliced geometry from verified route
            const routeGeom = r.geometry?.[dir] || [];
            let slicedGeom = null;
            if (Array.isArray(routeGeom) && routeGeom.length > 1) {
              const startIdx = this.findNearestGeomIndex(routeGeom, boardStop);
              const endIdx = this.findNearestGeomIndex(routeGeom, alightStop);
              if (startIdx <= endIdx) {
                slicedGeom = routeGeom.slice(startIdx, endIdx + 1);
              }
            }

            const walkOrigin = this.walkingRouter.createWalkingLeg(
              originLocation.displayName,
              boardStop.name,
              [originLocation.lat, originLocation.lng],
              [boardStop.lat, boardStop.lng]
            );
            const walkDest = this.walkingRouter.createWalkingLeg(
              alightStop.name,
              destLocation.displayName,
              [alightStop.lat, alightStop.lng],
              [destLocation.lat, destLocation.lng]
            );

            if (!walkOrigin || !walkDest) continue;

            const transitMinutes = Math.max(stopsCount * 2, 5);
            const totalDuration = walkOrigin.durationMinutes + transitMinutes + walkDest.durationMinutes;
            const totalWalkingMeters = walkOrigin.distanceMeters + walkDest.distanceMeters;

            trips.push({
              id: `direct_${r.id}_${dir}_${oi}_${di}`,
              type: 'direct',
              transfers: 0,
              badge: 'Tuyến trực tiếp',
              route: r,
              direction: dir,
              totalDurationMinutes: totalDuration,
              totalWalkingMeters,
              transitDurationMinutes: transitMinutes,
              fareText: this.busService.formatRouteFare(r),
              cost: (walkOrigin.durationMinutes + walkDest.durationMinutes) * 1.5 + transitMinutes,
              legs: [
                walkOrigin,
                {
                  type: 'transit',
                  routeId: r.id,
                  routeNumber: r.routeNumber,
                  routeName: r.shortName || r.name,
                  direction: dir,
                  boardingStop: boardStop,
                  alightingStop: alightStop,
                  stopsCount,
                  durationMinutes: transitMinutes,
                  geometry: slicedGeom
                },
                walkDest
              ]
            });
          }
        }
      }
    }

    // Step 3: Connecting Trips Search (Max 1 transfer)
    for (const rA of eligibleRoutes) {
      for (const dirA of ['outbound', 'inbound']) {
        if (!this.busService.isDirectionPlanningReady(rA, dirA)) continue;
        const stopsA = rA.stops?.[dirA] || [];
        if (stopsA.length < 2) continue;

        for (const rB of eligibleRoutes) {
          if (rA.id === rB.id) continue; // Anti-loop: no transfer on same route

          for (const dirB of ['outbound', 'inbound']) {
            if (!this.busService.isDirectionPlanningReady(rB, dirB)) continue;
            const stopsB = rB.stops?.[dirB] || [];
            if (stopsB.length < 2) continue;

            // Match origin candidate on Route A
            for (const oCand of originCandidates) {
              const oiA = stopsA.findIndex(s => s.name === oCand.name || (s.lat && oCand.lat && Math.abs(s.lat - oCand.lat) < 0.0001 && Math.abs(s.lng - oCand.lng) < 0.0001));
              if (oiA < 0 || oiA >= stopsA.length - 1) continue;

              // Match destination candidate on Route B
              for (const dCand of destCandidates) {
                const diB = stopsB.findIndex(s => s.name === dCand.name || (s.lat && dCand.lat && Math.abs(s.lat - dCand.lat) < 0.0001 && Math.abs(s.lng - dCand.lng) < 0.0001));
                if (diB <= 0) continue;

                // Search transfer connecting points between stopsA[oiA+1..] and stopsB[..diB-1]
                for (let tiA = oiA + 1; tiA < stopsA.length; tiA++) {
                  const tStopA = stopsA[tiA];
                  if (!tStopA.lat || !tStopA.lng) continue;

                  for (let tiB = 0; tiB < diB; tiB++) {
                    const tStopB = stopsB[tiB];
                    if (!tStopB.lat || !tStopB.lng) continue;

                    const transferWalkDist = haversineDistance(tStopA.lat, tStopA.lng, tStopB.lat, tStopB.lng);
                    if (transferWalkDist === null || transferWalkDist > this.MAX_TRANSFER_WALK_METERS) {
                      continue; // Transfer walking must be <= 400m
                    }

                    // Detour ratio check
                    const boardA = stopsA[oiA];
                    const alightB = stopsB[diB];
                    const legAEstMeters = haversineDistance(boardA.lat, boardA.lng, tStopA.lat, tStopA.lng) || 0;
                    const legBEstMeters = haversineDistance(tStopB.lat, tStopB.lng, alightB.lat, alightB.lng) || 0;
                    const walkOriginDist = oCand.distanceMeters || 0;
                    const walkDestDist = dCand.distanceMeters || 0;

                    const totalTripDist = walkOriginDist + legAEstMeters + transferWalkDist + legBEstMeters + walkDestDist;
                    if (totalTripDist / straightDist > this.MAX_DETOUR_RATIO) {
                      continue; // Detour penalty: reject excessive circuity (detour ratio <= 1.8)
                    }

                    const walkOrigin = this.walkingRouter.createWalkingLeg(
                      originLocation.displayName,
                      boardA.name,
                      [originLocation.lat, originLocation.lng],
                      [boardA.lat, boardA.lng]
                    );
                    const walkTransfer = this.walkingRouter.createWalkingLeg(
                      tStopA.name,
                      tStopB.name,
                      [tStopA.lat, tStopA.lng],
                      [tStopB.lat, tStopB.lng]
                    );
                    const walkDest = this.walkingRouter.createWalkingLeg(
                      alightB.name,
                      destLocation.displayName,
                      [alightB.lat, alightB.lng],
                      [destLocation.lat, destLocation.lng]
                    );

                    if (!walkOrigin || !walkTransfer || !walkDest) continue;

                    const stopsCountA = tiA - oiA;
                    const stopsCountB = diB - tiB;
                    const durA = Math.max(stopsCountA * 2, 4);
                    const durB = Math.max(stopsCountB * 2, 4);
                    const totalDur = walkOrigin.durationMinutes + durA + walkTransfer.durationMinutes + durB + walkDest.durationMinutes;
                    const totalWalk = walkOrigin.distanceMeters + walkTransfer.distanceMeters + walkDest.distanceMeters;

                    // Sliced geometries
                    const geomA = rA.geometry?.[dirA] || [];
                    const geomB = rB.geometry?.[dirB] || [];
                    let slicedGeomA = null;
                    let slicedGeomB = null;
                    if (Array.isArray(geomA) && geomA.length > 1) {
                      const sIdx = this.findNearestGeomIndex(geomA, boardA);
                      const eIdx = this.findNearestGeomIndex(geomA, tStopA);
                      if (sIdx <= eIdx) slicedGeomA = geomA.slice(sIdx, eIdx + 1);
                    }
                    if (Array.isArray(geomB) && geomB.length > 1) {
                      const sIdx = this.findNearestGeomIndex(geomB, tStopB);
                      const eIdx = this.findNearestGeomIndex(geomB, alightB);
                      if (sIdx <= eIdx) slicedGeomB = geomB.slice(sIdx, eIdx + 1);
                    }

                    // Combined fare text
                    const fareA = this.busService.formatRouteFare(rA);
                    const fareB = this.busService.formatRouteFare(rB);
                    const fareText = `${fareA} + ${fareB}`;

                    trips.push({
                      id: `transfer_${rA.id}_${rB.id}_${oiA}_${tiA}_${tiB}_${diB}`,
                      type: 'connecting',
                      transfers: 1,
                      badge: 'Chuyển tuyến 1 lần',
                      routeA: rA,
                      routeB: rB,
                      totalDurationMinutes: totalDur,
                      totalWalkingMeters: totalWalk,
                      transitDurationMinutes: durA + durB,
                      fareText,
                      cost: (walkOrigin.durationMinutes + walkTransfer.durationMinutes + walkDest.durationMinutes) * 1.5 + durA + durB + 12,
                      legs: [
                        walkOrigin,
                        {
                          type: 'transit',
                          routeId: rA.id,
                          routeNumber: rA.routeNumber,
                          routeName: rA.shortName || rA.name,
                          direction: dirA,
                          boardingStop: boardA,
                          alightingStop: tStopA,
                          stopsCount: stopsCountA,
                          durationMinutes: durA,
                          geometry: slicedGeomA
                        },
                        walkTransfer,
                        {
                          type: 'transit',
                          routeId: rB.id,
                          routeNumber: rB.routeNumber,
                          routeName: rB.shortName || rB.name,
                          direction: dirB,
                          boardingStop: tStopB,
                          alightingStop: alightB,
                          stopsCount: stopsCountB,
                          durationMinutes: durB,
                          geometry: slicedGeomB
                        },
                        walkDest
                      ]
                    });
                  }
                }
              }
            }
          }
        }
      }
    }

    if (trips.length === 0) {
      return {
        trips: [],
        error: 'NO_VIABLE_ROUTE',
        message: 'Không tìm thấy hành trình phù hợp kết nối 2 vị trí này theo dữ liệu tuyến hợp lệ'
      };
    }

    // Step 4: Ranking & Deduplication
    trips.sort((a, b) => a.cost - b.cost);

    // Deduplicate similar trips (same routes & transfer stop)
    const dedupedTrips = [];
    const seenTripSignatures = new Set();
    for (const t of trips) {
      let sig = '';
      if (t.type === 'direct') {
        sig = `direct_${t.route.id}_${t.direction}_${t.legs[1].boardingStop.name}_${t.legs[1].alightingStop.name}`;
      } else {
        sig = `transfer_${t.routeA.id}_${t.routeB.id}_${t.legs[1].boardingStop.name}_${t.legs[1].alightingStop.name}_${t.legs[3].alightingStop.name}`;
      }
      if (!seenTripSignatures.has(sig)) {
        seenTripSignatures.add(sig);
        dedupedTrips.push(t);
        if (dedupedTrips.length >= 5) break;
      }
    }

    // Assign ranking badges
    let minWalkTrip = dedupedTrips[0];
    let fastestTrip = dedupedTrips[0];
    for (const t of dedupedTrips) {
      if (t.totalWalkingMeters < minWalkTrip.totalWalkingMeters) minWalkTrip = t;
      if (t.totalDurationMinutes < fastestTrip.totalDurationMinutes) fastestTrip = t;
    }

    dedupedTrips.forEach((t, i) => {
      if (t.type === 'direct') {
        t.rankingCategory = 'Tuyến trực tiếp';
      } else if (t === minWalkTrip) {
        t.rankingCategory = 'Ít đi bộ nhất';
      } else if (t === fastestTrip) {
        t.rankingCategory = 'Nhanh nhất';
      } else {
        t.rankingCategory = `Lựa chọn ${i + 1}`;
      }
    });

    return { trips: dedupedTrips, totalOptions: dedupedTrips.length };
  }

  findNearestGeomIndex(points, stop) {
    if (!Array.isArray(points) || !stop || typeof stop.lat !== 'number') return 0;
    let bestIdx = 0;
    let minD = Infinity;
    for (let i = 0; i < points.length; i++) {
      const p = points[i];
      const d = (p[0] - stop.lat) ** 2 + (p[1] - stop.lng) ** 2;
      if (d < minD) {
        minD = d;
        bestIdx = i;
      }
    }
    return bestIdx;
  }
}

// Global browser registration for Task 4
if (typeof window !== 'undefined') {
  window.ResolvedLocation = ResolvedLocation;
  window.LocationSearchProvider = LocationSearchProvider;
  window.LocalLocationProvider = LocalLocationProvider;
  window.LocationManager = LocationManager;
  window.locationManager = new LocationManager(window.busService);
  window.WalkingRouter = WalkingRouter;
  window.walkingRouter = new WalkingRouter();
  window.TransitPlanner = TransitPlanner;
  window.transitPlanner = new TransitPlanner(window.busService, window.walkingRouter);
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    BusService,
    findNearbyStops,
    haversineDistance,
    ResolvedLocation,
    LocationSearchProvider,
    LocalLocationProvider,
    LocationManager,
    WalkingRouter,
    TransitPlanner
  };
}
