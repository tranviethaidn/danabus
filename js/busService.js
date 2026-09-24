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
  }

  async init() {
    if (this.isLoaded) return;
    try {
      const [routesRes, stopsRes, streetsRes, summaryRes] = await Promise.all([
        fetch('data/danangbus_routes.json', { cache: 'no-cache' }),
        fetch('data/danangbus_stops.json', { cache: 'no-cache' }),
        fetch('data/danangbus_streets.json', { cache: 'no-cache' }),
        fetch('data/danangbus_summary.json', { cache: 'no-cache' })
      ]);

      this.routes = await routesRes.json();
      this.stops = await stopsRes.json();
      this.streetsIndex = await streetsRes.json();
      this.summary = await summaryRes.json();
      this.isLoaded = true;
      console.log(`[BusService] Loaded ${this.routes.length} routes and ${this.stops.length} stops.`);
    } catch (err) {
      console.error('[BusService] Error loading data:', err);
    }
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
        matchCat = (r.vehicleInfo && r.vehicleInfo.toLowerCase().includes('điện')) || ['02', '03', '09', '13', '14', '21'].includes(r.id);
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

  findRoutesBetween(originText = '', destinationText = '') {
    const o = this.normalize(originText);
    const d = this.normalize(destinationText);

    if (!o && !d) return [];

    return this.routes.filter(r => {
      const allText = this.normalize(
        `${r.name} ${r.shortName} ${r.terminals?.origin} ${r.terminals?.destination} ` +
        (r.routePaths?.outbound?.text || '') + ' ' +
        (r.routePaths?.inbound?.text || '')
      );

      const hasOrigin = !o || allText.includes(o) || (r.stops?.outbound || []).some(s => this.normalize(s.name).includes(o) || this.normalize(s.street).includes(o));
      const hasDest = !d || allText.includes(d) || (r.stops?.outbound || []).some(s => this.normalize(s.name).includes(d) || this.normalize(s.street).includes(d));

      return hasOrigin && hasDest;
    });
  }

  calculateNextDeparture(route) {
    if (!route || !route.operatingHours) {
      return { timeStr: '08:30', minutesLeft: 6, isOperating: true };
    }

    const now = new Date();
    const currentHour = now.getHours();
    const currentMinute = now.getMinutes();
    const currentMinutesSinceMidnight = currentHour * 60 + currentMinute;

    const [startH, startM] = (route.operatingHours.start || '05:30').split(':').map(Number);
    const [endH, endM] = (route.operatingHours.end || '19:00').split(':').map(Number);

    const startTotal = (startH || 5) * 60 + (startM || 30);
    const endTotal = (endH || 19) * 60 + (endM || 0);

    const isOperating = currentMinutesSinceMidnight >= startTotal && currentMinutesSinceMidnight <= endTotal;

    const interval = route.frequency?.peakMinutes || 15;
    let nextDepartureTotal = startTotal;
    
    if (currentMinutesSinceMidnight < startTotal) {
      nextDepartureTotal = startTotal;
    } else if (currentMinutesSinceMidnight > endTotal) {
      nextDepartureTotal = startTotal; // Next day
    } else {
      const elapsed = currentMinutesSinceMidnight - startTotal;
      const count = Math.ceil(elapsed / interval);
      nextDepartureTotal = startTotal + (count * interval);
      if (nextDepartureTotal <= currentMinutesSinceMidnight) {
        nextDepartureTotal += interval;
      }
    }

    const nextH = Math.floor(nextDepartureTotal / 60) % 24;
    const nextM = nextDepartureTotal % 60;
    const timeStr = `${String(nextH).padStart(2, '0')}:${String(nextM).padStart(2, '0')}`;
    let minutesLeft = nextDepartureTotal - currentMinutesSinceMidnight;
    if (minutesLeft < 1) minutesLeft = interval;
    if (minutesLeft > interval) minutesLeft = minutesLeft % interval || interval;

    return {
      timeStr,
      minutesLeft,
      isOperating,
      nextTripTime: timeStr
    };
  }

  formatFare(val) {
    if (!val && val !== 0) return 'Đang cập nhật';
    return `${Number(val).toLocaleString('vi-VN')}đ`;
  }
}

// Global singleton instance
window.busService = new BusService();
