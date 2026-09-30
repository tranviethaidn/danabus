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

  /**
   * Helper to parse ISO timestamp or date-only string with explicit ICT (+07:00) timezone handling.
   * Avoids JavaScript date-only UTC parsing ambiguity.
   */
  parseIsoTimestamp(val, isEndOfDay = false) {
    if (val == null) return NaN;
    if (val instanceof Date) {
      const ms = val.getTime();
      return isNaN(ms) ? NaN : ms;
    }
    if (typeof val === 'number') {
      return isFinite(val) ? val : NaN;
    }
    if (typeof val !== 'string') return NaN;
    const s = val.trim();
    if (!s) return NaN;

    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
      const timePart = isEndOfDay ? '23:59:59.999+07:00' : '00:00:00.000+07:00';
      return new Date(`${s}T${timePart}`).getTime();
    }
    const d = new Date(s);
    return d.getTime();
  }

  /**
   * Resolves a route identifier token (canonical ID, routeNumber, formerCode, or alias)
   * with deterministic precedence and unambiguous conflict handling.
   *
   * Precedence:
   * 1. Canonical ID exact match (r.id === cleanToken).
   * 2. Public route number exact match (r.routeNumber === cleanToken).
   *    If > 1 match, fails closed (returns status: 'ambiguous', candidates).
   * 3. Former codes or search aliases exact match.
   *    If > 1 match, fails closed (returns status: 'ambiguous', candidates).
   */
  resolveRouteIdentifier(token, options = {}) {
    if (!token && token !== 0) {
      return { route: null, status: 'not_found', candidates: [], reason: 'Token không hợp lệ' };
    }
    const cleanToken = String(token).trim();
    if (!cleanToken) {
      return { route: null, status: 'not_found', candidates: [], reason: 'Token rỗng' };
    }

    // Priority 1: Exact Canonical ID
    const exactIdMatch = this.routes.find(r => r.id === cleanToken);
    if (exactIdMatch) {
      return this._handleResolvedRoute(exactIdMatch, 'exact_id', [exactIdMatch], options);
    }

    // Priority 2: Exact Route Number
    const routeNumberMatches = this.routes.filter(r => r.routeNumber === cleanToken);
    if (routeNumberMatches.length === 1) {
      return this._handleResolvedRoute(routeNumberMatches[0], 'route_number', routeNumberMatches, options);
    } else if (routeNumberMatches.length > 1) {
      return {
        route: null,
        status: 'ambiguous',
        candidates: routeNumberMatches,
        reason: `Số hiệu tuyến '${cleanToken}' trùng khớp nhiều bản ghi (${routeNumberMatches.map(r => r.id).join(', ')})`
      };
    }

    // Priority 3: Former Codes & Aliases
    const codeMatches = this.routes.filter(r => 
      (Array.isArray(r.formerCodes) && r.formerCodes.includes(cleanToken)) ||
      (Array.isArray(r.aliases) && r.aliases.includes(cleanToken))
    );
    if (codeMatches.length === 1) {
      const match = codeMatches[0];
      const isFormer = Array.isArray(match.formerCodes) && match.formerCodes.includes(cleanToken);
      const matchedVia = isFormer ? 'former_code' : 'alias';
      return this._handleResolvedRoute(match, matchedVia, codeMatches, options);
    } else if (codeMatches.length > 1) {
      return {
        route: null,
        status: 'ambiguous',
        candidates: codeMatches,
        reason: `Mã cũ/alias '${cleanToken}' trùng khớp nhiều bản ghi (${codeMatches.map(r => r.id).join(', ')})`
      };
    }

    return { route: null, status: 'not_found', candidates: [], reason: `Không tìm thấy tuyến cho '${cleanToken}'` };
  }

  _handleResolvedRoute(route, matchedVia, candidates, options = {}) {
    if (!options.followSuccessor) {
      return {
        route,
        status: matchedVia,
        candidates,
        matchedVia,
        followedSuccessor: false
      };
    }

    // Explicit successor traversal with cycle detection
    const visited = new Set([route.id]);
    let curr = route;
    let followed = false;
    let hops = 0;
    const maxHops = 10;

    while (curr.supersededBy || curr.mergedInto) {
      const nextId = curr.supersededBy || curr.mergedInto;
      if (visited.has(nextId)) {
        return {
          route: null,
          status: 'cycle_detected',
          candidates,
          reason: `Phát hiện vòng lặp kế thừa tuyến (${Array.from(visited).join(' -> ')} -> ${nextId})`
        };
      }
      hops++;
      if (hops > maxHops) {
        return {
          route: null,
          status: 'max_hops_exceeded',
          candidates,
          reason: 'Vượt quá số bước kế thừa tối đa'
        };
      }
      visited.add(nextId);
      const nextRoute = this.routes.find(r => r.id === nextId);
      if (!nextRoute) {
        return {
          route: null,
          status: 'broken_successor_reference',
          candidates,
          reason: `Không tìm thấy tuyến kế thừa '${nextId}'`
        };
      }
      curr = nextRoute;
      followed = true;
    }

    return {
      route: curr,
      status: matchedVia,
      candidates,
      matchedVia,
      followedSuccessor: followed,
      originalRoute: route
    };
  }

  getRouteById(id, options = {}) {
    if (!id && id !== 0) return null;
    const result = this.resolveRouteIdentifier(id, options);
    return result.route || null;
  }

  /**
   * Resolves the temporal validity and operational service state of a route at queryTime T.
   * Single deterministic source of truth for planner, search, and schedule.
   *
   * @param {Object} route BusRoute entity
   * @param {Date|string|number} queryTime Time to evaluate (defaults to new Date())
   * @param {'outbound'|'inbound'|null} direction Direction to check (null = whole route)
   * @returns {Object} { isUsable: boolean, status: string, effectiveStatus: string, activeOverride: Object|null, reason: string|null }
   */
  getServiceTemporalState(route, queryTime = new Date(), direction = null) {
    // 1. Validate queryTime
    if (queryTime == null) {
      return { isUsable: false, status: 'invalid_time', effectiveStatus: 'invalid_time', activeOverride: null, reason: 'Thời gian truy vấn không hợp lệ' };
    }
    const tMs = this.parseIsoTimestamp(queryTime);
    if (isNaN(tMs)) {
      return { isUsable: false, status: 'invalid_time', effectiveStatus: 'invalid_time', activeOverride: null, reason: 'Thời gian truy vấn không hợp lệ' };
    }

    // 2. Validate route existence & required provenance
    if (!route || typeof route !== 'object') {
      return { isUsable: false, status: 'unknown', effectiveStatus: 'unknown', activeOverride: null, reason: 'Không có dữ liệu tuyến' };
    }
    if (!route.sourceUrl || typeof route.sourceUrl !== 'string' || !route.sourceUrl.startsWith('http') || !route.lastVerifiedAt) {
      return { isUsable: false, status: 'unverified', effectiveStatus: 'unverified', activeOverride: null, reason: 'Tuyến thiếu thông tin nguồn chính thức (provenance)' };
    }
    if (route.verificationStatus !== 'verified') {
      return { isUsable: false, status: 'unverified', effectiveStatus: 'unverified', activeOverride: null, reason: 'Tuyến chưa được xác minh nguồn chính thức (verificationStatus !== "verified")' };
    }

    // 3. Base lifecycle status
    if (route.status === 'retired') {
      return { isUsable: false, status: 'retired', effectiveStatus: 'retired', activeOverride: null, reason: route.statusNote || 'Tuyến đã ngừng khai thác vĩnh viễn' };
    }
    if (route.status === 'merged') {
      if (route.effectiveTo) {
        const toMs = this.parseIsoTimestamp(route.effectiveTo, true);
        if (!isNaN(toMs) && tMs <= toMs) {
          // Predecessor record remains usable prior to the merger effective date
        } else {
          return { isUsable: false, status: 'merged', effectiveStatus: 'merged', activeOverride: null, reason: route.statusNote || `Tuyến đã sáp nhập vào tuyến ${route.mergedInto || ''}`.trim() };
        }
      } else {
        return { isUsable: false, status: 'merged', effectiveStatus: 'merged', activeOverride: null, reason: route.statusNote || `Tuyến đã sáp nhập vào tuyến ${route.mergedInto || ''}`.trim() };
      }
    }
    if (route.status === 'suspended' || route.isActive === false) {
      return { isUsable: false, status: 'suspended', effectiveStatus: 'suspended', activeOverride: null, reason: route.statusNote || 'Tuyến đang tạm dừng hoạt động' };
    }
    if (route.status !== 'active' && route.status !== 'merged') {
      return { isUsable: false, status: route.status || 'unknown', effectiveStatus: route.status || 'unknown', activeOverride: null, reason: 'Trạng thái tuyến không hoạt động' };
    }

    // 4. Permanent temporal bounds
    if (route.effectiveFrom) {
      const fromMs = this.parseIsoTimestamp(route.effectiveFrom, false);
      if (!isNaN(fromMs) && tMs < fromMs) {
        return { isUsable: false, status: 'future', effectiveStatus: 'future', activeOverride: null, reason: 'Tuyến chưa đến ngày bắt đầu khai thác' };
      }
    }
    if (route.effectiveTo) {
      const toMs = this.parseIsoTimestamp(route.effectiveTo, true);
      if (!isNaN(toMs) && tMs > toMs) {
        return { isUsable: false, status: 'expired', effectiveStatus: 'expired', activeOverride: null, reason: 'Tuyến đã hết hạn thời gian khai thác' };
      }
    }

    // 5. Temporary overrides evaluation
    const overrides = Array.isArray(route.temporaryOverrides) ? route.temporaryOverrides : [];
    let activeOverride = null;

    for (const ovr of overrides) {
      if (!ovr || typeof ovr !== 'object') continue;
      
      const ovrFrom = this.parseIsoTimestamp(ovr.effectiveFrom, false);
      const ovrTo = this.parseIsoTimestamp(ovr.effectiveTo, true);
      
      const isMalformed = isNaN(ovrFrom) || isNaN(ovrTo) || ovrFrom > ovrTo;
      if (isMalformed) {
        return {
          isUsable: false,
          status: 'malformed_override',
          effectiveStatus: 'malformed_override',
          activeOverride: ovr,
          reason: 'Thông báo tạm thời của tuyến không hợp lệ hoặc thiếu khung giờ hiệu lực'
        };
      }

      // Check if current time falls within override window
      if (tMs >= ovrFrom && tMs <= ovrTo) {
        const affectsDirection = !direction || 
          !Array.isArray(ovr.affectedDirections) || 
          ovr.affectedDirections.length === 0 || 
          ovr.affectedDirections.includes(direction);

        if (!affectsDirection) {
          continue;
        }

        const hasValidProvenance = Boolean(
          ovr.sourceUrl &&
          typeof ovr.sourceUrl === 'string' &&
          ovr.sourceUrl.startsWith('http') &&
          ovr.lastVerifiedAt &&
          ovr.verificationStatus === 'verified'
        );

        if (!hasValidProvenance) {
          return {
            isUsable: false,
            status: 'unverified_override',
            effectiveStatus: 'unverified_override',
            activeOverride: ovr,
            reason: 'Thông báo tạm thời của tuyến thiếu nguồn chính thức hoặc chưa được xác minh (unverified override)'
          };
        }

        // Temporary suspension
        if (ovr.type === 'suspension' || ovr.statusOverride === 'suspended') {
          return {
            isUsable: false,
            status: 'active',
            effectiveStatus: 'suspended',
            activeOverride: ovr,
            reason: ovr.reason || 'Tuyến tạm dừng hoạt động theo thông báo tạm thời'
          };
        }

        // Active detour without verified replacement truth
        if (ovr.type === 'detour') {
          if (!ovr.hasReplacementTruth) {
            return {
              isUsable: false,
              status: 'active',
              effectiveStatus: 'detour_unverified',
              activeOverride: ovr,
              reason: ovr.reason || 'Tuyến đang điều chỉnh lộ trình tạm thời nhưng chưa có dữ liệu trạm/hình học thay thế đã xác minh'
            };
          }
        }

        activeOverride = ovr;
      }
    }

    return {
      isUsable: true,
      status: 'active',
      effectiveStatus: 'active',
      activeOverride,
      reason: null
    };
  }

  isServiceUsable(route, queryTime = new Date(), direction = null) {
    return this.getServiceTemporalState(route, queryTime, direction).isUsable;
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

  findRoutesBetween(originText = '', destinationText = '', options = {}) {
    const o = this.normalize(originText);
    const d = this.normalize(destinationText);

    if (!o || !d || o === d) return [];

    const queryTime = (options && options.queryTime) ? options.queryTime : ((options && options.now) ? options.now : new Date());

    const oTokens = this.resolveSearchTokens(o);
    const dTokens = this.resolveSearchTokens(d);

    const matches = [];

    for (const r of this.routes) {
      if (!this.isServiceUsable(r, queryTime)) {
        continue;
      }

      for (const dir of ['outbound', 'inbound']) {
        if (!this.isServiceUsable(r, queryTime, dir)) {
          continue;
        }

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

    // Temporal service validity evaluation
    let queryTime = options.queryTime || options.now;
    if (!queryTime) {
      if (typeof options.currentTime === 'object' && options.currentTime instanceof Date) {
        queryTime = options.currentTime;
      } else {
        queryTime = new Date();
      }
    }
    const direction = (options.direction === 'inbound') ? 'inbound' : 'outbound';
    const temporalState = this.getServiceTemporalState(route, queryTime, direction);
    if (!temporalState.isUsable) {
      return unknownResult(temporalState.reason || 'Tuyến không khả dụng theo trạng thái thời gian/xác minh');
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
  constructor({ displayName, address, lat, lng, provider = 'local', providerId = null, type = 'poi', dataConfidence = null }) {
    this.displayName = displayName || 'Vị trí';
    this.address = address || displayName || '';
    this.lat = typeof lat === 'number' && Number.isFinite(lat) ? lat : null;
    this.lng = typeof lng === 'number' && Number.isFinite(lng) ? lng : null;
    this.provider = provider;
    this.providerId = providerId || `${provider}_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
    this.type = type; // 'poi' | 'address' | 'stop' | 'gps' | 'pin'
    this.dataConfidence = dataConfidence;
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

const SERVICE_AREA_BOUNDS = {
  minLat: 15.40,
  maxLat: 16.35,
  minLng: 107.90,
  maxLng: 108.65
};

function isWithinServiceArea(lat, lng) {
  if (typeof lat !== 'number' || typeof lng !== 'number' || !Number.isFinite(lat) || !Number.isFinite(lng)) {
    return false;
  }
  return (
    lat >= SERVICE_AREA_BOUNDS.minLat &&
    lat <= SERVICE_AREA_BOUNDS.maxLat &&
    lng >= SERVICE_AREA_BOUNDS.minLng &&
    lng <= SERVICE_AREA_BOUNDS.maxLng
  );
}

class LocationSearchProvider {
  constructor(name = 'base') {
    this.name = name;
  }
  async search(query, options = {}) { throw new Error('Not implemented'); }
  async resolve(providerId, item = null) { throw new Error('Not implemented'); }
  async reverseGeocode(lat, lng) { throw new Error('Not implemented'); }
}

class GoogleLocationProvider extends LocationSearchProvider {
  constructor(options = {}) {
    super('google');
    // Public browser runtime key (HTTP Referrer / website restricted in Google Cloud Console), NEVER a server secret
    this.apiKey = options.apiKey || (typeof window !== 'undefined' && window.DANABUS_CONFIG?.googlePlacesApiKey) || null;
    this.sessionToken = null;
    this.timeoutMs = options.timeoutMs || 3000;
    this.languageCode = options.languageCode || 'vi';
    this.bounds = options.bounds || {
      low: { latitude: SERVICE_AREA_BOUNDS.minLat, longitude: SERVICE_AREA_BOUNDS.minLng },
      high: { latitude: SERVICE_AREA_BOUNDS.maxLat, longitude: SERVICE_AREA_BOUNDS.maxLng }
    };
    this._searchSeq = 0;
    this._scriptLoaded = false;
    this._scriptLoadingPromise = null;
    this._sessionPredictions = new Map(); // placeId -> PlacePrediction
  }

  isConfigured() {
    return typeof this.apiKey === 'string' && this.apiKey.trim().length > 0;
  }

  getPlacesLibrary() {
    if (typeof window !== 'undefined' && window.google?.maps?.places) {
      return window.google.maps.places;
    }
    if (typeof global !== 'undefined' && global.google?.maps?.places) {
      return global.google.maps.places;
    }
    return null;
  }

  getOrCreateSessionToken(placesLib = null) {
    if (!this.sessionToken) {
      const lib = placesLib || this.getPlacesLibrary();
      if (lib && typeof lib.AutocompleteSessionToken === 'function') {
        this.sessionToken = new lib.AutocompleteSessionToken();
      } else {
        this.sessionToken = { _token: 'token_' + Date.now() + '_' + Math.random().toString(36).substring(2, 10) };
      }
    }
    return this.sessionToken;
  }

  resetSessionToken() {
    this.sessionToken = null;
    this._sessionPredictions.clear();
  }

  loadClientScript() {
    if (this._scriptLoadingPromise) return this._scriptLoadingPromise;

    const placesLib = this.getPlacesLibrary();
    if (placesLib) {
      this._scriptLoaded = true;
      return Promise.resolve(true);
    }

    if (typeof window === 'undefined' || typeof document === 'undefined') {
      return Promise.resolve(false);
    }

    if (!this.isConfigured()) {
      return Promise.resolve(false);
    }

    this._scriptLoadingPromise = new Promise((resolve) => {
      let settled = false;
      let timer = null;

      const finish = (success, reason = null) => {
        if (settled) return;
        settled = true;
        if (timer) {
          clearTimeout(timer);
          timer = null;
        }
        this._scriptLoaded = success;
        if (!success) {
          if (reason) console.warn('[GoogleLocationProvider] Google Maps Places client SDK script load failed:', reason);
          this._scriptLoadingPromise = null;
        }
        resolve(success);
      };

      timer = setTimeout(() => {
        finish(false, 'timeout');
      }, this.timeoutMs);

      const existingScript = typeof document.querySelector === 'function' ? document.querySelector('script[src*="maps.googleapis.com/maps/api/js"]') : null;
      if (existingScript) {
        if (this.getPlacesLibrary()) {
          return finish(true);
        }
        if (typeof existingScript.addEventListener === 'function') {
          existingScript.addEventListener('load', () => finish(!!this.getPlacesLibrary()), { once: true });
          existingScript.addEventListener('error', () => finish(false, 'script error'), { once: true });
        } else {
          const prevLoad = existingScript.onload;
          const prevErr = existingScript.onerror;
          existingScript.onload = (ev) => {
            if (typeof prevLoad === 'function') prevLoad(ev);
            finish(!!this.getPlacesLibrary());
          };
          existingScript.onerror = (ev) => {
            if (typeof prevErr === 'function') prevErr(ev);
            finish(false, 'script error');
          };
        }
        return;
      }

      const script = document.createElement('script');
      script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(this.apiKey)}&libraries=places&v=weekly&loading=async`;
      script.async = true;
      script.onload = () => finish(!!this.getPlacesLibrary());
      script.onerror = () => finish(false, 'script error');
      const target = document.head || document.body || document.documentElement;
      if (target && typeof target.appendChild === 'function') {
        target.appendChild(script);
      }
    });

    return this._scriptLoadingPromise;
  }

  async ensureClientSdk() {
    let placesLib = this.getPlacesLibrary();
    if (placesLib) return placesLib;

    const loaded = await this.loadClientScript();
    if (!loaded) {
      this._scriptLoadingPromise = null;
      return null;
    }

    placesLib = this.getPlacesLibrary();
    if (!placesLib) {
      const gMaps = (typeof window !== 'undefined' && window.google?.maps) ||
                    (typeof global !== 'undefined' && global.google?.maps);
      if (gMaps && typeof gMaps.importLibrary === 'function') {
        let timeoutId;
        try {
          const timeoutP = new Promise((_, reject) => {
            timeoutId = setTimeout(() => reject(new Error('importLibrary timeout')), this.timeoutMs);
          });
          placesLib = await Promise.race([gMaps.importLibrary('places'), timeoutP]);
        } catch (e) {
          console.warn('[GoogleLocationProvider] importLibrary("places") failed:', e.message);
        } finally {
          if (timeoutId) clearTimeout(timeoutId);
        }
      }
    }
    return placesLib || null;
  }

  async search(query, options = {}) {
    const trimmed = (query || '').trim();
    if (!trimmed || trimmed.length < 2) return [];
    if (!this.isConfigured()) return [];

    const seq = ++this._searchSeq;

    // Actively load / ensure Places client SDK
    const placesLib = await this.ensureClientSdk();
    if (!placesLib) {
      // SDK failed to load, timeout or unavailable: fail closed safely to local fallback
      return [];
    }

    if (seq !== this._searchSeq) return [];

    const sessionToken = this.getOrCreateSessionToken(placesLib);

    let timeoutId;
    const timeoutPromise = new Promise((_, reject) => {
      timeoutId = setTimeout(() => {
        const err = new Error('Google Places client SDK search timeout');
        err.name = 'AbortError';
        reject(err);
      }, this.timeoutMs);
    });

    try {
      let fetchPromise;
      if (placesLib.AutocompleteSuggestion && typeof placesLib.AutocompleteSuggestion.fetchAutocompleteSuggestions === 'function') {
        fetchPromise = placesLib.AutocompleteSuggestion.fetchAutocompleteSuggestions({
          input: trimmed,
          includedRegionCodes: ['vn'],
          locationRestriction: {
            west: this.bounds.low.longitude,
            north: this.bounds.high.latitude,
            east: this.bounds.high.longitude,
            south: this.bounds.low.latitude
          },
          language: this.languageCode,
          sessionToken
        }).then(res => (res && res.suggestions) || []);
      } else if (placesLib.AutocompleteService) {
        const service = new placesLib.AutocompleteService();
        fetchPromise = new Promise((resolve) => {
          service.getPlacePredictions({
            input: trimmed,
            componentRestrictions: { country: 'vn' },
            sessionToken
          }, (predictions) => {
            if (predictions && Array.isArray(predictions)) {
              resolve(predictions.map(p => ({
                placePrediction: {
                  placeId: p.place_id,
                  text: { text: p.description },
                  structuredFormat: {
                    mainText: { text: p.structured_formatting?.main_text || p.description },
                    secondaryText: { text: p.structured_formatting?.secondary_text || '' }
                  }
                }
              })));
            } else {
              resolve([]);
            }
          });
        });
      } else {
        fetchPromise = Promise.resolve([]);
      }

      const suggestions = await Promise.race([fetchPromise, timeoutPromise]);
      clearTimeout(timeoutId);

      // Stale response suppression
      if (seq !== this._searchSeq) return [];

      const results = [];
      for (const item of (suggestions || [])) {
        const pred = item.placePrediction || item;
        const placeId = pred.placeId || pred.place_id;
        if (!placeId) continue;

        // Maintain session prediction mapping for session-associated Place.fetchFields()
        this._sessionPredictions.set(placeId, pred);

        const mainText = pred.structuredFormat?.mainText?.text || pred.text?.text || trimmed;
        const secondaryText = pred.structuredFormat?.secondaryText?.text || 'Đà Nẵng, Việt Nam';
        results.push({
          id: placeId,
          placeId: placeId,
          displayName: mainText,
          address: secondaryText ? `${mainText}, ${secondaryText}` : mainText,
          lat: null,
          lng: null,
          type: 'address',
          provider: 'google',
          _placePrediction: pred
        });
      }
      return results;
    } catch (err) {
      clearTimeout(timeoutId);
      console.warn('[GoogleLocationProvider] Client SDK search failed gracefully:', err.message);
      return [];
    }
  }

  async resolve(providerId, item = null) {
    if (item && typeof item.lat === 'number' && typeof item.lng === 'number' && Number.isFinite(item.lat) && Number.isFinite(item.lng)) {
      return new ResolvedLocation(item);
    }
    const placeId = providerId || item?.placeId || item?.id;
    if (!placeId) return null;
    if (!this.isConfigured()) return null;

    // Actively load / ensure Places client SDK
    const placesLib = await this.ensureClientSdk();
    if (!placesLib) {
      return null;
    }

    const pred = item?._placePrediction || this._sessionPredictions.get(placeId) || null;
    const sessionToken = this.sessionToken;

    // Reset session token & predictions after selection resolve attempt
    this.resetSessionToken();

    let timeoutId;
    const timeoutPromise = new Promise((_, reject) => {
      timeoutId = setTimeout(() => {
        const err = new Error('Google Places client SDK resolve timeout');
        err.name = 'AbortError';
        reject(err);
      }, this.timeoutMs);
    });

    try {
      let detailsPromise;
      if (pred && typeof pred.toPlace === 'function') {
        const place = pred.toPlace();
        detailsPromise = place.fetchFields({
          fields: ['displayName', 'formattedAddress', 'location']
        }).then((res) => {
          const target = res?.place || res || place;
          const loc = target.location || place.location;
          const lat = typeof loc?.lat === 'function' ? loc.lat() : loc?.latitude ?? loc?.lat;
          const lng = typeof loc?.lng === 'function' ? loc.lng() : loc?.longitude ?? loc?.lng;
          return {
            displayName: target.displayName?.text || target.displayName || place.displayName?.text || place.displayName || item?.displayName || 'Địa điểm',
            formattedAddress: target.formattedAddress || place.formattedAddress || item?.address,
            location: { latitude: lat, longitude: lng }
          };
        });
      } else if (placesLib.Place) {
        const place = new placesLib.Place({ id: placeId });
        detailsPromise = place.fetchFields({
          fields: ['displayName', 'formattedAddress', 'location']
        }).then((res) => {
          const target = res?.place || res || place;
          const loc = target.location || place.location;
          const lat = typeof loc?.lat === 'function' ? loc.lat() : loc?.latitude ?? loc?.lat;
          const lng = typeof loc?.lng === 'function' ? loc.lng() : loc?.longitude ?? loc?.lng;
          return {
            displayName: target.displayName?.text || target.displayName || place.displayName?.text || place.displayName || item?.displayName || 'Địa điểm',
            formattedAddress: target.formattedAddress || place.formattedAddress || item?.address,
            location: { latitude: lat, longitude: lng }
          };
        });
      } else if (placesLib.PlacesService) {
        const div = (typeof document !== 'undefined') ? document.createElement('div') : null;
        const service = new placesLib.PlacesService(div || {});
        detailsPromise = new Promise((resolve) => {
          service.getDetails({
            placeId,
            fields: ['name', 'formatted_address', 'geometry'],
            sessionToken: sessionToken || undefined
          }, (res) => {
            if (res && res.geometry && res.geometry.location) {
              const lat = typeof res.geometry.location.lat === 'function' ? res.geometry.location.lat() : res.geometry.location.lat;
              const lng = typeof res.geometry.location.lng === 'function' ? res.geometry.location.lng() : res.geometry.location.lng;
              resolve({
                displayName: res.name || item?.displayName || 'Địa điểm',
                formattedAddress: res.formatted_address || item?.address,
                location: { latitude: lat, longitude: lng }
              });
            } else {
              resolve(null);
            }
          });
        });
      } else {
        detailsPromise = Promise.resolve(null);
      }

      const data = await Promise.race([detailsPromise, timeoutPromise]);
      clearTimeout(timeoutId);

      if (!data || !data.location) return null;
      const lat = data.location.latitude;
      const lng = data.location.longitude;
      if (typeof lat !== 'number' || typeof lng !== 'number' || !Number.isFinite(lat) || !Number.isFinite(lng)) {
        return null;
      }

      return new ResolvedLocation({
        displayName: data.displayName || item?.displayName || 'Địa điểm',
        address: data.formattedAddress || item?.address || data.displayName,
        lat,
        lng,
        provider: 'google',
        providerId: placeId,
        type: 'address'
      });
    } catch (err) {
      clearTimeout(timeoutId);
      console.warn('[GoogleLocationProvider] Client SDK resolve failed gracefully:', err.message);
      return null;
    }
  }

  async reverseGeocode(lat, lng) {
    return null;
  }
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
      },
      {
        id: 'addr_tran_phu_dn',
        displayName: 'Trần Phú, Hải Châu',
        address: '119 Trần Phú, Hải Châu 1, Hải Châu, Đà Nẵng',
        lat: 16.0682,
        lng: 108.2245,
        type: 'address',
        keywords: ['tran phu', 'hai chau', 'da nang']
      },
      {
        id: 'addr_tran_phu_ha',
        displayName: 'Trần Phú, Hội An',
        address: 'Trần Phú, Phường Minh An, TP. Hội An, Quảng Nam',
        lat: 15.8775,
        lng: 108.3290,
        type: 'address',
        keywords: ['tran phu', 'hoi an', 'quang nam']
      },
      {
        id: 'addr_hung_vuong_dn',
        displayName: 'Hùng Vương, Hải Châu',
        address: '290 Hùng Vương, Vĩnh Trung, Hải Châu, Đà Nẵng',
        lat: 16.0688,
        lng: 108.2148,
        type: 'address',
        keywords: ['hung vuong', 'vinh trung', 'da nang']
      },
      {
        id: 'addr_hung_vuong_tk',
        displayName: 'Hùng Vương, Tam Kỳ',
        address: 'Hùng Vương, Phường An Sơn, TP. Tam Kỳ, Quảng Nam',
        lat: 15.5684,
        lng: 108.4816,
        type: 'address',
        keywords: ['hung vuong', 'tam ky', 'quang nam']
      },
      {
        id: 'addr_pct_dn',
        displayName: 'Phan Châu Trinh, Hải Châu',
        address: 'Phan Châu Trinh, Phước Ninh, Hải Châu, Đà Nẵng',
        lat: 16.0635,
        lng: 108.2205,
        type: 'address',
        keywords: ['phan chau trinh', 'hai chau', 'da nang']
      },
      {
        id: 'addr_pct_tk',
        displayName: 'Phan Châu Trinh, Tam Kỳ',
        address: '954 Phan Châu Trinh, An Sơn, Tam Kỳ, Quảng Nam',
        lat: 15.555436,
        lng: 108.5059009,
        type: 'address',
        keywords: ['phan chau trinh', 'tam ky', 'quang nam']
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
  constructor(busService = null, options = {}) {
    this.localProvider = new LocalLocationProvider(busService);
    this.googleProvider = new GoogleLocationProvider(options.google || {});
    this.activeProvider = this.googleProvider.isConfigured() ? this.googleProvider : this.localProvider;
    this.cache = new Map();
    this._searchSeq = 0;
  }

  setBusService(busService) {
    this.localProvider.busService = busService;
  }

  setGoogleApiKey(apiKey) {
    this.googleProvider.apiKey = apiKey;
    this.activeProvider = this.googleProvider.isConfigured() ? this.googleProvider : this.localProvider;
  }

  isWithinServiceArea(lat, lng) {
    return isWithinServiceArea(lat, lng);
  }

  async search(query, options = {}) {
    const trimmed = (query || '').trim();
    if (!trimmed || trimmed.length < 2) return [];

    const seq = ++this._searchSeq;
    const cacheKey = `search_${trimmed}`;
    if (this.cache.has(cacheKey)) return this.cache.get(cacheKey);

    let results = [];
    if (this.googleProvider.isConfigured()) {
      try {
        const gRes = await this.googleProvider.search(trimmed, options);
        // Stale check after Google search: if a newer search started, discard immediately
        if (seq !== this._searchSeq) {
          return [];
        }
        if (Array.isArray(gRes) && gRes.length > 0) {
          results = gRes;
        }
      } catch (err) {
        console.warn('[LocationManager] Google search error, falling back to local:', err.message);
      }
    }

    // Stale check before local fallback: obsolete requests must never fall back to local
    if (seq !== this._searchSeq) {
      return [];
    }

    if (results.length === 0) {
      results = await this.localProvider.search(trimmed, options);
    }

    // Stale check before caching and returning
    if (seq !== this._searchSeq) {
      return [];
    }

    this.cache.set(cacheKey, results);
    return results;
  }

  async resolve(providerId, item = null) {
    if (item && typeof item.lat === 'number' && typeof item.lng === 'number' && Number.isFinite(item.lat) && Number.isFinite(item.lng)) {
      return new ResolvedLocation(item);
    }
    if (item?.provider === 'google' || (item?.placeId && this.googleProvider.isConfigured())) {
      const res = await this.googleProvider.resolve(providerId, item);
      if (res && res.isValid()) return res;
      // Google details failed: fallback ONLY if a real local candidate with valid coordinates exists
      const localMatch = this.localProvider.localPOIs.find(p => p.id === providerId || (p.displayName && p.displayName.toLowerCase() === (item?.displayName || '').toLowerCase()));
      if (localMatch && typeof localMatch.lat === 'number' && typeof localMatch.lng === 'number' && Number.isFinite(localMatch.lat) && Number.isFinite(localMatch.lng)) {
        return new ResolvedLocation(localMatch);
      }
      return null; // Never return null coordinates or invalid endpoint
    }
    return this.localProvider.resolve(providerId, item);
  }

  resolveFromCoordinates(lat, lng, displayName = 'Vị trí đã chọn', type = 'gps') {
    return new ResolvedLocation({
      displayName,
      address: displayName,
      lat,
      lng,
      provider: type === 'pin' ? 'map_pin' : 'gps',
      type: type === 'pin' ? 'pin' : 'gps'
    });
  }

  resolveFromMapPin(lat, lng, label = null) {
    if (typeof lat !== 'number' || typeof lng !== 'number' || !Number.isFinite(lat) || !Number.isFinite(lng)) {
      return null;
    }
    const displayName = label || `Ghim trên bản đồ (${lat.toFixed(4)}, ${lng.toFixed(4)})`;
    return new ResolvedLocation({
      displayName,
      address: displayName, // STRICT: Never fabricate an address
      lat,
      lng,
      provider: 'map_pin',
      type: 'pin'
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

  createWalkingLeg(fromLabel, toLabel, fromCoords, toCoords, walkingRole = null) {
    const r = this.route(fromCoords, toCoords);
    if (!r) return null;
    const leg = {
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
    if (walkingRole) {
      leg.walkingRole = walkingRole;
    }
    return leg;
  }
}

/**
 * TransitGraphRouter
 * Internal graph and topological routing engine.
 * Direction planner-ready indexing, transfer adjacency caching,
 * bounded layered search (direct -> 1 transfer -> 2 transfers),
 * anti-loop/backtrack, monotonic stop ordering, and lazy geometry materialization.
 */
class TransitGraphRouter {
  constructor(busService, walkingRouter = null, options = {}) {
    this.busService = busService;
    this.walkingRouter = walkingRouter || new WalkingRouter();
    this.MAX_TRANSFER_WALK_METERS = options.maxTransferWalkMeters || 400;
    this.MAX_DETOUR_RATIO = options.maxDetourRatio || 1.8;
    this.MIN_TRANSFER_TIME_MINUTES = options.minTransferTimeMinutes || 5;
    this.calculateConfidencePenalty = options.calculateConfidencePenalty || ((r, dir) => 0);

    this._cachedRoutes = null;
    this._spatialTransferByFromKey = null;
  }

  clearCache() {
    this._cachedRoutes = null;
    this._spatialTransferByFromKey = null;
  }

  _isStopVerified(stop) {
    return Boolean(
      stop &&
      typeof stop === 'object' &&
      stop.status === 'verified' &&
      typeof stop.lat === 'number' &&
      typeof stop.lng === 'number' &&
      Number.isFinite(stop.lat) &&
      Number.isFinite(stop.lng)
    );
  }

  _ensureTransferIndex() {
    const currentRoutes = this.busService?.routes || [];
    if (this._cachedRoutes === currentRoutes && this._spatialTransferByFromKey) {
      return this._spatialTransferByFromKey;
    }

    const transferByFromKey = new Map();

    for (const rA of currentRoutes) {
      for (const dirA of ['outbound', 'inbound']) {
        const stopsA = rA.stops?.[dirA] || [];
        if (stopsA.length < 2) continue;

        for (const rB of currentRoutes) {
          if (rA.id === rB.id) continue;

          for (const dirB of ['outbound', 'inbound']) {
            const stopsB = rB.stops?.[dirB] || [];
            if (stopsB.length < 2) continue;

            const fromKey = `${rA.id}_${dirA}`;
            for (let iA = 0; iA < stopsA.length; iA++) {
              const sA = stopsA[iA];
              if (!this._isStopVerified(sA)) {
                continue; // Stop without verified status or valid coordinates cannot be a transfer stop
              }

              for (let iB = 0; iB < stopsB.length; iB++) {
                const sB = stopsB[iB];
                if (!this._isStopVerified(sB)) {
                  continue; // Stop without verified status or valid coordinates cannot be a transfer stop
                }

                const walkDist = haversineDistance(sA.lat, sA.lng, sB.lat, sB.lng);
                if (walkDist !== null && walkDist <= this.MAX_TRANSFER_WALK_METERS) {
                  const edge = {
                    fromRouteId: rA.id,
                    fromDir: dirA,
                    fromStopIndex: iA,
                    fromStop: sA,
                    toRouteId: rB.id,
                    toDir: dirB,
                    toStopIndex: iB,
                    toStop: sB,
                    walkDist: Math.round(walkDist)
                  };
                  if (!transferByFromKey.has(fromKey)) {
                    transferByFromKey.set(fromKey, []);
                  }
                  transferByFromKey.get(fromKey).push(edge);
                }
              }
            }
          }
        }
      }
    }

    this._cachedRoutes = currentRoutes;
    this._spatialTransferByFromKey = transferByFromKey;
    return transferByFromKey;
  }

  _matchCandidate(stop, candidate) {
    if (!stop || !candidate) return false;
    if (stop.status !== 'verified') return false; // Strictly require verified stop
    if (stop.name && candidate.name && stop.name === candidate.name) return true;
    if (typeof stop.lat === 'number' && typeof candidate.lat === 'number' &&
        typeof stop.lng === 'number' && typeof candidate.lng === 'number') {
      return Math.abs(stop.lat - candidate.lat) < 0.0001 && Math.abs(stop.lng - candidate.lng) < 0.0001;
    }
    return false;
  }

  _compareTrips(a, b) {
    if (a.transfers !== b.transfers) {
      return a.transfers - b.transfers;
    }
    if (Math.abs(a.cost - b.cost) > 0.001) {
      return a.cost - b.cost;
    }
    if (a.totalWalkingMeters !== b.totalWalkingMeters) {
      return a.totalWalkingMeters - b.totalWalkingMeters;
    }
    if (a.totalDurationMinutes !== b.totalDurationMinutes) {
      return a.totalDurationMinutes - b.totalDurationMinutes;
    }
    const idA = a.id || '';
    const idB = b.id || '';
    return idA.localeCompare(idB);
  }

  findNearestGeomIndex(points, stop) {
    if (!Array.isArray(points) || !stop || typeof stop.lat !== 'number' || typeof stop.lng !== 'number') return 0;
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

  searchJourneys(originLocation, destLocation, originCandidates, destCandidates, queryTime, straightDist, options = {}) {
    const maxTransfers = options.maxTransfers !== undefined ? options.maxTransfers : 2;
    const transferMap = this._ensureTransferIndex();

    // Filter active, planning-ready routes and directions
    const readyDirections = new Map();
    const allRoutes = this.busService?.routes || [];
    for (const r of allRoutes) {
      for (const dir of ['outbound', 'inbound']) {
        if (!this.busService.isServiceUsable(r, queryTime, dir)) continue;
        if (!this.busService.isDirectionPlanningReady(r, dir)) continue;
        const stops = r.stops?.[dir] || [];
        if (stops.length < 2) continue;
        readyDirections.set(`${r.id}_${dir}`, { route: r, direction: dir, stops });
      }
    }

    const candidateTrips = [];
    const walkSpeed = this.walkingRouter.walkingSpeedMetersPerMinute || 75;
    const calcWalkMin = (meters) => Math.max(1, Math.round(meters / walkSpeed));

    // LAYER 0: Direct trips (0 transfers)
    for (const [keyA, dirInfoA] of readyDirections.entries()) {
      const { route: r, direction: dir, stops } = dirInfoA;

      for (const oCand of originCandidates) {
        const oi = stops.findIndex(s => this._matchCandidate(s, oCand));
        if (oi < 0) continue;
        const boardStop = stops[oi];
        if (!this._isStopVerified(boardStop)) continue;

        for (const dCand of destCandidates) {
          const di = stops.findIndex(s => this._matchCandidate(s, dCand));
          if (di < 0 || oi >= di) continue; // Monotonic order strictly enforced
          const alightStop = stops[di];
          if (!this._isStopVerified(alightStop)) continue;

          const stopsCount = di - oi;
          const transitMinutes = Math.max(stopsCount * 2, 5);

          const oWalkDist = typeof oCand.distanceMeters === 'number' ? oCand.distanceMeters :
            Math.round(haversineDistance(originLocation.lat, originLocation.lng, boardStop.lat, boardStop.lng) || 0);
          const dWalkDist = typeof dCand.distanceMeters === 'number' ? dCand.distanceMeters :
            Math.round(haversineDistance(alightStop.lat, alightStop.lng, destLocation.lat, destLocation.lng) || 0);

          const oWalkMin = calcWalkMin(oWalkDist);
          const dWalkMin = calcWalkMin(dWalkDist);
          const totalWalkMeters = oWalkDist + dWalkDist;
          const totalDuration = oWalkMin + transitMinutes + dWalkMin;

          const confidencePenalty = this.calculateConfidencePenalty(r, dir);
          const cost = (oWalkMin + dWalkMin) * 1.5 + transitMinutes + confidencePenalty;

          candidateTrips.push({
            type: 'direct',
            transfers: 0,
            badge: 'Tuyến trực tiếp',
            route: r,
            routes: [r],
            direction: dir,
            boardIndex: oi,
            alightIndex: di,
            boardStop,
            alightStop,
            stopsCount,
            transitDurationMinutes: transitMinutes,
            oWalkDist,
            dWalkDist,
            oWalkMin,
            dWalkMin,
            transferBufferMinutes: 0,
            totalDurationMinutes: totalDuration,
            totalWalkingMeters: totalWalkMeters,
            confidencePenalty,
            cost,
            id: `direct_${r.id}_${dir}_${oi}_${di}`
          });
        }
      }
    }

    // LAYER 1: 1-transfer trips
    if (maxTransfers >= 1) {
      for (const [keyA, dirInfoA] of readyDirections.entries()) {
        const { route: rA, direction: dirA, stops: stopsA } = dirInfoA;
        const outEdgesA = transferMap.get(keyA) || [];
        if (outEdgesA.length === 0) continue;

        for (const oCand of originCandidates) {
          const oiA = stopsA.findIndex(s => this._matchCandidate(s, oCand));
          if (oiA < 0 || oiA >= stopsA.length - 1) continue;
          const boardA = stopsA[oiA];
          if (!this._isStopVerified(boardA)) continue;

          const oWalkDist = typeof oCand.distanceMeters === 'number' ? oCand.distanceMeters :
            Math.round(haversineDistance(originLocation.lat, originLocation.lng, boardA.lat, boardA.lng) || 0);
          const oWalkMin = calcWalkMin(oWalkDist);

          for (const edge of outEdgesA) {
            const tiA = edge.fromStopIndex;
            if (tiA <= oiA) continue; // Monotonic on Route A

            const keyB = `${edge.toRouteId}_${edge.toDir}`;
            const dirInfoB = readyDirections.get(keyB);
            if (!dirInfoB) continue;
            if (dirInfoB.route.id === rA.id) continue; // Anti-route-reuse

            const { route: rB, direction: dirB, stops: stopsB } = dirInfoB;
            const tiB = edge.toStopIndex;
            const tStopA = edge.fromStop;
            const tStopB = edge.toStop;
            if (!this._isStopVerified(tStopA) || !this._isStopVerified(tStopB)) continue;

            const tWalkDist = edge.walkDist;
            const tWalkMin = calcWalkMin(tWalkDist);

            const legAEstMeters = haversineDistance(boardA.lat, boardA.lng, tStopA.lat, tStopA.lng) || 0;

            for (const dCand of destCandidates) {
              const diB = stopsB.findIndex(s => this._matchCandidate(s, dCand));
              if (diB <= tiB) continue; // Monotonic on Route B
              const alightB = stopsB[diB];
              if (!this._isStopVerified(alightB)) continue;

              const dWalkDist = typeof dCand.distanceMeters === 'number' ? dCand.distanceMeters :
                Math.round(haversineDistance(alightB.lat, alightB.lng, destLocation.lat, destLocation.lng) || 0);
              const legBEstMeters = haversineDistance(tStopB.lat, tStopB.lng, alightB.lat, alightB.lng) || 0;

              // Detour ratio check
              const totalTripDist = oWalkDist + legAEstMeters + tWalkDist + legBEstMeters + dWalkDist;
              if (totalTripDist / straightDist > this.MAX_DETOUR_RATIO) {
                continue;
              }

              const dWalkMin = calcWalkMin(dWalkDist);
              const stopsCountA = tiA - oiA;
              const stopsCountB = diB - tiB;
              const durA = Math.max(stopsCountA * 2, 4);
              const durB = Math.max(stopsCountB * 2, 4);

              const transferBufferMinutes = this.MIN_TRANSFER_TIME_MINUTES; // 5 mins
              const totalDuration = oWalkMin + durA + tWalkMin + durB + dWalkMin + transferBufferMinutes;
              const totalWalkMeters = oWalkDist + tWalkDist + dWalkDist;

              const confA = this.calculateConfidencePenalty(rA, dirA);
              const confB = this.calculateConfidencePenalty(rB, dirB);
              const totalConfidencePenalty = confA + confB;
              const cost = (oWalkMin + tWalkMin + dWalkMin) * 1.5 + durA + durB + 12 + transferBufferMinutes + totalConfidencePenalty;

              candidateTrips.push({
                type: 'connecting',
                transfers: 1,
                badge: 'Chuyển tuyến 1 lần',
                routeA: rA,
                routeB: rB,
                routes: [rA, rB],
                dirA,
                dirB,
                oiA,
                tiA,
                tiB,
                diB,
                boardA,
                tStopA,
                tStopB,
                alightB,
                stopsCountA,
                stopsCountB,
                durA,
                durB,
                oWalkDist,
                dWalkDist,
                tWalkDist,
                oWalkMin,
                dWalkMin,
                tWalkMin,
                transferBufferMinutes,
                transferBufferNote: 'Thời gian đệm chuyển tuyến ước tính (không phải dự báo realtime)',
                totalDurationMinutes: totalDuration,
                totalWalkingMeters: totalWalkMeters,
                confidencePenalty: totalConfidencePenalty,
                confidencePenaltyA: confA,
                confidencePenaltyB: confB,
                cost,
                id: `transfer_${rA.id}_${rB.id}_${oiA}_${tiA}_${tiB}_${diB}`
              });
            }
          }
        }
      }
    }

    // LAYER 2: 2-transfer trips (3 distinct routes: rA -> rB -> rC)
    if (maxTransfers >= 2) {
      for (const [keyA, dirInfoA] of readyDirections.entries()) {
        const { route: rA, direction: dirA, stops: stopsA } = dirInfoA;
        const outEdgesA = transferMap.get(keyA) || [];
        if (outEdgesA.length === 0) continue;

        for (const oCand of originCandidates) {
          const oiA = stopsA.findIndex(s => this._matchCandidate(s, oCand));
          if (oiA < 0 || oiA >= stopsA.length - 1) continue;
          const boardA = stopsA[oiA];
          if (!this._isStopVerified(boardA)) continue;

          const oWalkDist = typeof oCand.distanceMeters === 'number' ? oCand.distanceMeters :
            Math.round(haversineDistance(originLocation.lat, originLocation.lng, boardA.lat, boardA.lng) || 0);
          const oWalkMin = calcWalkMin(oWalkDist);

          for (const edge1 of outEdgesA) {
            const tiA = edge1.fromStopIndex;
            if (tiA <= oiA) continue; // Monotonic on Route A

            const keyB = `${edge1.toRouteId}_${edge1.toDir}`;
            const dirInfoB = readyDirections.get(keyB);
            if (!dirInfoB) continue;
            if (dirInfoB.route.id === rA.id) continue; // Anti-route-reuse

            const { route: rB, direction: dirB, stops: stopsB } = dirInfoB;
            const tiB1 = edge1.toStopIndex;
            const tStopA = edge1.fromStop;
            const tStopB1 = edge1.toStop;
            if (!this._isStopVerified(tStopA) || !this._isStopVerified(tStopB1)) continue;

            const tWalkDist1 = edge1.walkDist;
            const tWalkMin1 = calcWalkMin(tWalkDist1);

            const outEdgesB = transferMap.get(keyB) || [];
            if (outEdgesB.length === 0) continue;

            const legAEstMeters = haversineDistance(boardA.lat, boardA.lng, tStopA.lat, tStopA.lng) || 0;

            for (const edge2 of outEdgesB) {
              const tiB2 = edge2.fromStopIndex;
              if (tiB2 <= tiB1) continue; // Monotonic on Route B

              const keyC = `${edge2.toRouteId}_${edge2.toDir}`;
              const dirInfoC = readyDirections.get(keyC);
              if (!dirInfoC) continue;

              const { route: rC, direction: dirC, stops: stopsC } = dirInfoC;
              // Anti-route-reuse: All 3 routes must be distinct!
              if (rC.id === rA.id || rC.id === rB.id) continue;

              const tiC = edge2.toStopIndex;
              const tStopB2 = edge2.fromStop;
              const tStopC = edge2.toStop;
              if (!this._isStopVerified(tStopB2) || !this._isStopVerified(tStopC)) continue;

              const tWalkDist2 = edge2.walkDist;
              const tWalkMin2 = calcWalkMin(tWalkDist2);

              const legBEstMeters = haversineDistance(tStopB1.lat, tStopB1.lng, tStopB2.lat, tStopB2.lng) || 0;

              // Early detour pruning
              const partialDist = oWalkDist + legAEstMeters + tWalkDist1 + legBEstMeters + tWalkDist2;
              if (partialDist / straightDist > this.MAX_DETOUR_RATIO) {
                continue;
              }

              for (const dCand of destCandidates) {
                const diC = stopsC.findIndex(s => this._matchCandidate(s, dCand));
                if (diC <= tiC) continue; // Monotonic on Route C
                const alightC = stopsC[diC];
                if (!this._isStopVerified(alightC)) continue;

                const dWalkDist = typeof dCand.distanceMeters === 'number' ? dCand.distanceMeters :
                  Math.round(haversineDistance(alightC.lat, alightC.lng, destLocation.lat, destLocation.lng) || 0);
                const legCEstMeters = haversineDistance(tStopC.lat, tStopC.lng, alightC.lat, alightC.lng) || 0;

                const totalTripDist = partialDist + legCEstMeters + dWalkDist;
                if (totalTripDist / straightDist > this.MAX_DETOUR_RATIO) {
                  continue;
                }

                const dWalkMin = calcWalkMin(dWalkDist);
                const stopsCountA = tiA - oiA;
                const stopsCountB = tiB2 - tiB1;
                const stopsCountC = diC - tiC;
                const durA = Math.max(stopsCountA * 2, 4);
                const durB = Math.max(stopsCountB * 2, 4);
                const durC = Math.max(stopsCountC * 2, 4);

                const transferBufferMinutes = this.MIN_TRANSFER_TIME_MINUTES * 2; // 10 mins (5 * 2)
                const totalDuration = oWalkMin + durA + tWalkMin1 + durB + tWalkMin2 + durC + dWalkMin + transferBufferMinutes;
                const totalWalkMeters = oWalkDist + tWalkDist1 + tWalkDist2 + dWalkDist;

                const confA = this.calculateConfidencePenalty(rA, dirA);
                const confB = this.calculateConfidencePenalty(rB, dirB);
                const confC = this.calculateConfidencePenalty(rC, dirC);
                const totalConfidencePenalty = confA + confB + confC;

                const transferPenalty = 24; // 12 * 2
                const cost = (oWalkMin + tWalkMin1 + tWalkMin2 + dWalkMin) * 1.5 + durA + durB + durC + transferPenalty + transferBufferMinutes + totalConfidencePenalty;

                candidateTrips.push({
                  type: 'connecting',
                  transfers: 2,
                  badge: 'Chuyển tuyến 2 lần',
                  routeA: rA,
                  routeB: rB,
                  routeC: rC,
                  routes: [rA, rB, rC],
                  dirA,
                  dirB,
                  dirC,
                  oiA,
                  tiA,
                  tiB1,
                  tiB2,
                  tiC,
                  diC,
                  boardA,
                  tStopA,
                  tStopB1,
                  tStopB2,
                  tStopC,
                  alightC,
                  stopsCountA,
                  stopsCountB,
                  stopsCountC,
                  durA,
                  durB,
                  durC,
                  oWalkDist,
                  tWalkDist1,
                  tWalkDist2,
                  dWalkDist,
                  oWalkMin,
                  tWalkMin1,
                  tWalkMin2,
                  dWalkMin,
                  transferBufferMinutes,
                  transferBufferNote: 'Thời gian đệm chuyển tuyến ước tính (không phải dự báo realtime)',
                  totalDurationMinutes: totalDuration,
                  totalWalkingMeters: totalWalkMeters,
                  confidencePenalty: totalConfidencePenalty,
                  confidencePenaltyA: confA,
                  confidencePenaltyB: confB,
                  confidencePenaltyC: confC,
                  cost,
                  id: `transfer2_${rA.id}_${dirA}_${oiA}_${tiA}_${rB.id}_${dirB}_${tiB1}_${tiB2}_${rC.id}_${dirC}_${tiC}_${diC}`
                });
              }
            }
          }
        }
      }
    }

    if (candidateTrips.length === 0) return [];

    // Sort candidates deterministically
    candidateTrips.sort((a, b) => this._compareTrips(a, b));

    // Deduplicate similar candidates
    const finalists = [];
    const seenSignatures = new Set();
    for (const c of candidateTrips) {
      let sig = '';
      if (c.type === 'direct') {
        sig = `direct_${c.route.id}_${c.direction}_${c.boardStop.name}_${c.alightStop.name}`;
      } else if (c.transfers === 1) {
        sig = `transfer_${c.routeA.id}_${c.routeB.id}_${c.boardA.name}_${c.tStopA.name}_${c.alightB.name}`;
      } else {
        const routeKey = c.routes ? c.routes.map(r => r.id).join('_') : `${c.routeA?.id}_${c.routeB?.id}_${c.routeC?.id}`;
        sig = `transfer2_${routeKey}_${c.boardA.name}_${c.tStopA.name}_${c.tStopB2.name}_${c.alightC.name}`;
      }
      if (!seenSignatures.has(sig)) {
        seenSignatures.add(sig);
        finalists.push(c);
        if (finalists.length >= 5) break;
      }
    }

    // Materialize legs & lazy slice geometry for finalists only
    const materializedTrips = finalists.map(c => this._materializeTrip(c, originLocation, destLocation));
    return materializedTrips;
  }

  _materializeTrip(c, originLocation, destLocation) {
    if (c.type === 'direct') {
      const walkOrigin = this.walkingRouter.createWalkingLeg(
        originLocation.displayName,
        c.boardStop.name,
        [originLocation.lat, originLocation.lng],
        [c.boardStop.lat, c.boardStop.lng],
        'origin'
      );
      if (walkOrigin) walkOrigin.walkingRole = 'origin';

      const walkDest = this.walkingRouter.createWalkingLeg(
        c.alightStop.name,
        destLocation.displayName,
        [c.alightStop.lat, c.alightStop.lng],
        [destLocation.lat, destLocation.lng],
        'destination'
      );
      if (walkDest) walkDest.walkingRole = 'destination';

      const routeGeom = c.route.geometry?.[c.direction] || [];
      let slicedGeom = null;
      if (Array.isArray(routeGeom) && routeGeom.length > 1) {
        const startIdx = this.findNearestGeomIndex(routeGeom, c.boardStop);
        const endIdx = this.findNearestGeomIndex(routeGeom, c.alightStop);
        if (startIdx <= endIdx) {
          slicedGeom = routeGeom.slice(startIdx, endIdx + 1);
        }
      }

      return {
        id: c.id,
        type: 'direct',
        transfers: 0,
        badge: 'Tuyến trực tiếp',
        route: c.route,
        routes: [c.route],
        direction: c.direction,
        totalDurationMinutes: c.totalDurationMinutes,
        totalWalkingMeters: c.totalWalkingMeters,
        transitDurationMinutes: c.transitDurationMinutes,
        fareText: this.busService.formatRouteFare(c.route),
        confidencePenalty: c.confidencePenalty,
        dataConfidenceScore: c.route.dataQuality?.stopMetrics?.[c.direction]?.total ?
          Math.round(((c.route.dataQuality.stopMetrics[c.direction].verified || 0) / c.route.dataQuality.stopMetrics[c.direction].total) * 100) / 100 : 1.0,
        cost: c.cost,
        transferBufferMinutes: 0,
        legs: [
          walkOrigin,
          {
            type: 'transit',
            routeId: c.route.id,
            routeNumber: c.route.routeNumber,
            routeName: c.route.shortName || c.route.name,
            direction: c.direction,
            boardingStop: c.boardStop,
            alightingStop: c.alightStop,
            stopsCount: c.stopsCount,
            durationMinutes: c.transitDurationMinutes,
            geometry: slicedGeom
          },
          walkDest
        ]
      };
    }

    if (c.transfers === 1) {
      const walkOrigin = this.walkingRouter.createWalkingLeg(
        originLocation.displayName,
        c.boardA.name,
        [originLocation.lat, originLocation.lng],
        [c.boardA.lat, c.boardA.lng],
        'origin'
      );
      if (walkOrigin) walkOrigin.walkingRole = 'origin';

      const walkTransfer = this.walkingRouter.createWalkingLeg(
        c.tStopA.name,
        c.tStopB.name,
        [c.tStopA.lat, c.tStopA.lng],
        [c.tStopB.lat, c.tStopB.lng],
        'transfer'
      );
      if (walkTransfer) walkTransfer.walkingRole = 'transfer';

      const walkDest = this.walkingRouter.createWalkingLeg(
        c.alightB.name,
        destLocation.displayName,
        [c.alightB.lat, c.alightB.lng],
        [destLocation.lat, destLocation.lng],
        'destination'
      );
      if (walkDest) walkDest.walkingRole = 'destination';

      const geomA = c.routeA.geometry?.[c.dirA] || [];
      const geomB = c.routeB.geometry?.[c.dirB] || [];
      let slicedGeomA = null;
      let slicedGeomB = null;
      if (Array.isArray(geomA) && geomA.length > 1) {
        const sIdx = this.findNearestGeomIndex(geomA, c.boardA);
        const eIdx = this.findNearestGeomIndex(geomA, c.tStopA);
        if (sIdx <= eIdx) slicedGeomA = geomA.slice(sIdx, eIdx + 1);
      }
      if (Array.isArray(geomB) && geomB.length > 1) {
        const sIdx = this.findNearestGeomIndex(geomB, c.tStopB);
        const eIdx = this.findNearestGeomIndex(geomB, c.alightB);
        if (sIdx <= eIdx) slicedGeomB = geomB.slice(sIdx, eIdx + 1);
      }

      const fareA = this.busService.formatRouteFare(c.routeA);
      const fareB = this.busService.formatRouteFare(c.routeB);
      const fareText = `${fareA} + ${fareB}`;

      return {
        id: c.id,
        type: 'connecting',
        transfers: 1,
        badge: 'Chuyển tuyến 1 lần',
        routeA: c.routeA,
        routeB: c.routeB,
        routes: [c.routeA, c.routeB],
        totalDurationMinutes: c.totalDurationMinutes,
        totalWalkingMeters: c.totalWalkingMeters,
        transitDurationMinutes: c.durA + c.durB,
        fareText,
        confidencePenalty: c.confidencePenalty,
        confidencePenaltyA: c.confidencePenaltyA,
        confidencePenaltyB: c.confidencePenaltyB,
        cost: c.cost,
        transferBufferMinutes: c.transferBufferMinutes,
        transferBufferNote: c.transferBufferNote,
        legs: [
          walkOrigin,
          {
            type: 'transit',
            routeId: c.routeA.id,
            routeNumber: c.routeA.routeNumber,
            routeName: c.routeA.shortName || c.routeA.name,
            direction: c.dirA,
            boardingStop: c.boardA,
            alightingStop: c.tStopA,
            stopsCount: c.stopsCountA,
            durationMinutes: c.durA,
            geometry: slicedGeomA
          },
          walkTransfer,
          {
            type: 'transit',
            routeId: c.routeB.id,
            routeNumber: c.routeB.routeNumber,
            routeName: c.routeB.shortName || c.routeB.name,
            direction: c.dirB,
            boardingStop: c.tStopB,
            alightingStop: c.alightB,
            stopsCount: c.stopsCountB,
            durationMinutes: c.durB,
            geometry: slicedGeomB
          },
          walkDest
        ]
      };
    }

    if (c.transfers === 2) {
      const walkOrigin = this.walkingRouter.createWalkingLeg(
        originLocation.displayName,
        c.boardA.name,
        [originLocation.lat, originLocation.lng],
        [c.boardA.lat, c.boardA.lng],
        'origin'
      );
      if (walkOrigin) walkOrigin.walkingRole = 'origin';

      const walkTransfer1 = this.walkingRouter.createWalkingLeg(
        c.tStopA.name,
        c.tStopB1.name,
        [c.tStopA.lat, c.tStopA.lng],
        [c.tStopB1.lat, c.tStopB1.lng],
        'transfer'
      );
      if (walkTransfer1) walkTransfer1.walkingRole = 'transfer';

      const walkTransfer2 = this.walkingRouter.createWalkingLeg(
        c.tStopB2.name,
        c.tStopC.name,
        [c.tStopB2.lat, c.tStopB2.lng],
        [c.tStopC.lat, c.tStopC.lng],
        'transfer'
      );
      if (walkTransfer2) walkTransfer2.walkingRole = 'transfer';

      const walkDest = this.walkingRouter.createWalkingLeg(
        c.alightC.name,
        destLocation.displayName,
        [c.alightC.lat, c.alightC.lng],
        [destLocation.lat, destLocation.lng],
        'destination'
      );
      if (walkDest) walkDest.walkingRole = 'destination';

      const geomA = c.routeA.geometry?.[c.dirA] || [];
      const geomB = c.routeB.geometry?.[c.dirB] || [];
      const geomC = c.routeC.geometry?.[c.dirC] || [];
      let slicedGeomA = null;
      let slicedGeomB = null;
      let slicedGeomC = null;
      if (Array.isArray(geomA) && geomA.length > 1) {
        const sIdx = this.findNearestGeomIndex(geomA, c.boardA);
        const eIdx = this.findNearestGeomIndex(geomA, c.tStopA);
        if (sIdx <= eIdx) slicedGeomA = geomA.slice(sIdx, eIdx + 1);
      }
      if (Array.isArray(geomB) && geomB.length > 1) {
        const sIdx = this.findNearestGeomIndex(geomB, c.tStopB1);
        const eIdx = this.findNearestGeomIndex(geomB, c.tStopB2);
        if (sIdx <= eIdx) slicedGeomB = geomB.slice(sIdx, eIdx + 1);
      }
      if (Array.isArray(geomC) && geomC.length > 1) {
        const sIdx = this.findNearestGeomIndex(geomC, c.tStopC);
        const eIdx = this.findNearestGeomIndex(geomC, c.alightC);
        if (sIdx <= eIdx) slicedGeomC = geomC.slice(sIdx, eIdx + 1);
      }

      const fareA = this.busService.formatRouteFare(c.routeA);
      const fareB = this.busService.formatRouteFare(c.routeB);
      const fareC = this.busService.formatRouteFare(c.routeC);
      const fareText = `${fareA} + ${fareB} + ${fareC}`;

      return {
        id: c.id,
        type: 'connecting',
        transfers: 2,
        badge: 'Chuyển tuyến 2 lần',
        routeA: c.routeA,
        routeB: c.routeB,
        routeC: c.routeC,
        routes: [c.routeA, c.routeB, c.routeC],
        totalDurationMinutes: c.totalDurationMinutes,
        totalWalkingMeters: c.totalWalkingMeters,
        transitDurationMinutes: c.durA + c.durB + c.durC,
        fareText,
        confidencePenalty: c.confidencePenalty,
        confidencePenaltyA: c.confidencePenaltyA,
        confidencePenaltyB: c.confidencePenaltyB,
        confidencePenaltyC: c.confidencePenaltyC,
        cost: c.cost,
        transferBufferMinutes: c.transferBufferMinutes,
        transferBufferNote: c.transferBufferNote,
        legs: [
          walkOrigin,
          {
            type: 'transit',
            routeId: c.routeA.id,
            routeNumber: c.routeA.routeNumber,
            routeName: c.routeA.shortName || c.routeA.name,
            direction: c.dirA,
            boardingStop: c.boardA,
            alightingStop: c.tStopA,
            stopsCount: c.stopsCountA,
            durationMinutes: c.durA,
            geometry: slicedGeomA
          },
          walkTransfer1,
          {
            type: 'transit',
            routeId: c.routeB.id,
            routeNumber: c.routeB.routeNumber,
            routeName: c.routeB.shortName || c.routeB.name,
            direction: c.dirB,
            boardingStop: c.tStopB1,
            alightingStop: c.tStopB2,
            stopsCount: c.stopsCountB,
            durationMinutes: c.durB,
            geometry: slicedGeomB
          },
          walkTransfer2,
          {
            type: 'transit',
            routeId: c.routeC.id,
            routeNumber: c.routeC.routeNumber,
            routeName: c.routeC.shortName || c.routeC.name,
            direction: c.dirC,
            boardingStop: c.tStopC,
            alightingStop: c.alightC,
            stopsCount: c.stopsCountC,
            durationMinutes: c.durC,
            geometry: slicedGeomC
          },
          walkDest
        ]
      };
    }

    return null;
  }
}

/**
 * BestStopResolver
 * Multi-candidate evaluation boundary for boarding and alighting stops.
 * Controlled radius expansion: 800m -> 1500m.
 * Multi-factor ranking: walking cost, transit cost, transfer penalty, service validity, and data confidence.
 * Strict rejection of wrong-direction, inactive, or disconnected candidates.
 */
class BestStopResolver {
  constructor(busService, walkingRouter = null, options = {}) {
    this.busService = busService;
    this.walkingRouter = walkingRouter || new WalkingRouter();
    this.INITIAL_RADIUS_METERS = options.initialRadiusMeters || 800;
    this.MAX_RADIUS_METERS = options.maxRadiusMeters || 1500;
    this.MAX_TRANSFER_WALK_METERS = options.maxTransferWalkMeters || 400;
    this.MAX_DETOUR_RATIO = options.maxDetourRatio || 1.8;
    this.MIN_TRANSFER_TIME_MINUTES = options.minTransferTimeMinutes || 5;
    this.graphRouter = options.graphRouter || new TransitGraphRouter(this.busService, this.walkingRouter, {
      maxTransferWalkMeters: this.MAX_TRANSFER_WALK_METERS,
      maxDetourRatio: this.MAX_DETOUR_RATIO,
      minTransferTimeMinutes: this.MIN_TRANSFER_TIME_MINUTES,
      calculateConfidencePenalty: (r, dir) => this.calculateConfidencePenalty(r, dir)
    });
  }

  isWithinServiceArea(lat, lng) {
    return isWithinServiceArea(lat, lng);
  }

  calculateConfidencePenalty(route, direction) {
    if (!route || !direction) return 0;
    const metrics = route.dataQuality?.stopMetrics?.[direction];
    if (!metrics || typeof metrics.total !== 'number' || metrics.total <= 0) {
      return 0;
    }
    const verified = typeof metrics.verified === 'number' ? metrics.verified : 0;
    const verifiedRatio = verified / metrics.total;
    // Deterministic confidence penalty derived from existing route.dataQuality.stopMetrics:
    // High confidence (>= 80% stops verified): 0 penalty
    // Moderate confidence (60% <= ratio < 80%): 2.5 penalty
    // Lower confidence (< 60% stops verified): 5.0 penalty
    if (verifiedRatio >= 0.80) return 0;
    if (verifiedRatio >= 0.60) return 2.5;
    return 5.0;
  }

  findCandidateStops(lat, lng, radiusMeters) {
    if (!this.busService || typeof this.busService.findNearbyStops !== 'function') return [];
    return this.busService.findNearbyStops(lat, lng, {
      maxDistanceMeters: radiusMeters,
      limit: 15
    }).filter(s => s && s.status === 'verified');
  }

  resolveBestJourneys(originLocation, destLocation, options = {}) {
    if (!originLocation || !destLocation || !originLocation.isValid || !destLocation.isValid) {
      return { trips: [], error: 'INVALID_ENDPOINTS', message: 'Điểm đón hoặc điểm đến không hợp lệ' };
    }
    if (!originLocation.isValid() || !destLocation.isValid()) {
      return { trips: [], error: 'INVALID_COORDINATES', message: 'Tọa độ điểm đi/đến không hợp lệ' };
    }

    if (!this.isWithinServiceArea(originLocation.lat, originLocation.lng) ||
        !this.isWithinServiceArea(destLocation.lat, destLocation.lng)) {
      return {
        trips: [],
        error: 'OUT_OF_SERVICE_AREA',
        message: 'Điểm đón hoặc điểm đến nằm ngoài phạm vi phục vụ của mạng lưới xe buýt Đà Nẵng - Quảng Nam.'
      };
    }

    const straightDist = haversineDistance(originLocation.lat, originLocation.lng, destLocation.lat, destLocation.lng);
    if (straightDist === null) {
      return { trips: [], error: 'COORDINATE_ERROR', message: 'Lỗi tính toán khoảng cách' };
    }
    if (straightDist < 50) {
      return { trips: [], error: 'SAME_LOCATION', message: 'Điểm đón và điểm đến quá gần nhau' };
    }

    const queryTime = options.queryTime || options.now || new Date();

    // Stage 1: Try initial candidate radius (800m)
    let currentRadius = this.INITIAL_RADIUS_METERS;
    let isExpandedRadius = false;
    let oCandidates = this.findCandidateStops(originLocation.lat, originLocation.lng, currentRadius);
    let dCandidates = this.findCandidateStops(destLocation.lat, destLocation.lng, currentRadius);

    let trips = [];
    if (oCandidates.length > 0 && dCandidates.length > 0) {
      trips = this._evaluateJourneys(originLocation, destLocation, oCandidates, dCandidates, queryTime, straightDist);
    }

    // Stage 2: Controlled radius expansion up to 1500m when initial candidates yield no valid journeys
    if (trips.length === 0) {
      currentRadius = this.MAX_RADIUS_METERS;
      isExpandedRadius = true;
      oCandidates = this.findCandidateStops(originLocation.lat, originLocation.lng, currentRadius);
      dCandidates = this.findCandidateStops(destLocation.lat, destLocation.lng, currentRadius);

      if (oCandidates.length === 0 || dCandidates.length === 0) {
        return {
          trips: [],
          error: 'NO_NEARBY_STOPS',
          message: 'Không tìm thấy trạm dừng xe buýt nào gần điểm đón hoặc điểm đến trong bán kính đi bộ tối đa (1.5km)',
          searchRadiusMeters: currentRadius,
          isExpandedRadius: true
        };
      }

      trips = this._evaluateJourneys(originLocation, destLocation, oCandidates, dCandidates, queryTime, straightDist);
    }

    if (trips.length === 0) {
      return {
        trips: [],
        error: 'NO_VIABLE_ROUTE',
        message: 'Không tìm thấy hành trình phù hợp kết nối 2 vị trí này theo dữ liệu tuyến hợp lệ',
        searchRadiusMeters: currentRadius,
        isExpandedRadius
      };
    }

    // Attach search radius disclosure metadata to every trip
    trips.forEach(t => {
      t.isExpandedRadius = isExpandedRadius;
      t.searchRadiusMeters = currentRadius;
    });

    // Multi-factor ranking & deterministic tie-breaking
    trips.sort((a, b) => this._compareTrips(a, b));

    // Deduplicate similar trips (same routes & boarding/alighting stops)
    const dedupedTrips = [];
    const seenTripSignatures = new Set();
    for (const t of trips) {
      let sig = '';
      if (t.type === 'direct') {
        sig = `direct_${t.route.id}_${t.direction}_${t.legs[1].boardingStop.name}_${t.legs[1].alightingStop.name}`;
      } else if (t.transfers === 1) {
        sig = `transfer_${t.routeA.id}_${t.routeB.id}_${t.legs[1].boardingStop.name}_${t.legs[1].alightingStop.name}_${t.legs[3].alightingStop.name}`;
      } else {
        const routeKey = t.routes ? t.routes.map(r => r.id).join('_') : `${t.routeA?.id}_${t.routeB?.id}_${t.routeC?.id}`;
        sig = `transfer2_${routeKey}_${t.legs[1].boardingStop.name}_${t.legs[1].alightingStop.name}_${t.legs[3].alightingStop.name}_${t.legs[5].alightingStop.name}`;
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

    return {
      trips: dedupedTrips,
      totalOptions: dedupedTrips.length,
      isExpandedRadius,
      searchRadiusMeters: currentRadius
    };
  }

  _compareTrips(a, b) {
    // 1. Transfers ascending (direct before 1 transfer)
    if (a.transfers !== b.transfers) {
      return a.transfers - b.transfers;
    }
    // 2. Cost ascending
    if (Math.abs(a.cost - b.cost) > 0.001) {
      return a.cost - b.cost;
    }
    // 3. Total walking meters ascending
    if (a.totalWalkingMeters !== b.totalWalkingMeters) {
      return a.totalWalkingMeters - b.totalWalkingMeters;
    }
    // 4. Total duration minutes ascending
    if (a.totalDurationMinutes !== b.totalDurationMinutes) {
      return a.totalDurationMinutes - b.totalDurationMinutes;
    }
    // 5. Deterministic tie-breaker on stable identifiers
    const idA = a.id || '';
    const idB = b.id || '';
    return idA.localeCompare(idB);
  }

  findNearestGeomIndex(points, stop) {
    return this.graphRouter.findNearestGeomIndex(points, stop);
  }

  _evaluateJourneys(originLocation, destLocation, originCandidates, destCandidates, queryTime, straightDist, options = {}) {
    return this.graphRouter.searchJourneys(originLocation, destLocation, originCandidates, destCandidates, queryTime, straightDist, options);
  }
}

/**
 * TransitPlanner
 * Uses BestStopResolver and TransitGraphRouter for multi-candidate evaluation,
 * controlled radius expansion, and bounded multi-transfer routing (direct, 1, 2 transfers).
 * Detour ratio <= 1.8, fail-closed on unverified geometry or ineligible directions.
 */
class TransitPlanner {
  constructor(busService, walkingRouter = null) {
    this.busService = busService;
    this.walkingRouter = walkingRouter || new WalkingRouter();
    this.MAX_WALK_METERS = 1200;
    this.MAX_TRANSFER_WALK_METERS = 400;
    this.MAX_DETOUR_RATIO = 1.8; // STRICT: <= 1.8 per TL decision
    this.MIN_TRANSFER_TIME_MINUTES = 5;
    this.graphRouter = new TransitGraphRouter(this.busService, this.walkingRouter, {
      maxTransferWalkMeters: this.MAX_TRANSFER_WALK_METERS,
      maxDetourRatio: this.MAX_DETOUR_RATIO,
      minTransferTimeMinutes: this.MIN_TRANSFER_TIME_MINUTES
    });
    this.bestStopResolver = new BestStopResolver(this.busService, this.walkingRouter, {
      initialRadiusMeters: 800,
      maxRadiusMeters: 1500,
      maxTransferWalkMeters: this.MAX_TRANSFER_WALK_METERS,
      maxDetourRatio: this.MAX_DETOUR_RATIO,
      minTransferTimeMinutes: this.MIN_TRANSFER_TIME_MINUTES,
      graphRouter: this.graphRouter
    });
    this.graphRouter.calculateConfidencePenalty = (r, dir) => this.bestStopResolver.calculateConfidencePenalty(r, dir);
  }

  planTrip(originLocation, destLocation, options = {}) {
    return this.bestStopResolver.resolveBestJourneys(originLocation, destLocation, options);
  }

  findNearestGeomIndex(points, stop) {
    return this.bestStopResolver.findNearestGeomIndex(points, stop);
  }
}

// Global browser registration
if (typeof window !== 'undefined') {
  window.ResolvedLocation = ResolvedLocation;
  window.LocationSearchProvider = LocationSearchProvider;
  window.GoogleLocationProvider = GoogleLocationProvider;
  window.LocalLocationProvider = LocalLocationProvider;
  window.LocationManager = LocationManager;
  window.locationManager = new LocationManager(window.busService);
  window.WalkingRouter = WalkingRouter;
  window.walkingRouter = new WalkingRouter();
  window.TransitGraphRouter = TransitGraphRouter;
  window.BestStopResolver = BestStopResolver;
  window.TransitPlanner = TransitPlanner;
  window.transitPlanner = new TransitPlanner(window.busService, window.walkingRouter);
  window.isWithinServiceArea = isWithinServiceArea;
  window.SERVICE_AREA_BOUNDS = SERVICE_AREA_BOUNDS;
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    BusService,
    findNearbyStops,
    haversineDistance,
    ResolvedLocation,
    LocationSearchProvider,
    GoogleLocationProvider,
    LocalLocationProvider,
    LocationManager,
    WalkingRouter,
    TransitGraphRouter,
    BestStopResolver,
    TransitPlanner,
    isWithinServiceArea,
    SERVICE_AREA_BOUNDS
  };
}
