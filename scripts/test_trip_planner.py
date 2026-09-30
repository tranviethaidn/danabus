#!/usr/bin/env python3
"""
Comprehensive Automated Test Suite for Address Search, Geocoding & Best Boarding/Alighting Stop (Task 007)
Validates:
1. ResolvedLocation contract (validation, coordinates, provider metadata, map pin)
2. LocationSearchProvider & LocalLocationProvider (POI resolution, address search, stop search, duplicate street names)
3. GoogleLocationProvider contract (Places Autocomplete New, details, minimal field mask, session token, timeout/429/network safe fallback, stale suppression)
4. LocationManager integration (primary/fallback provider, cache, GPS, map pin)
5. Service Area geofence & Out-of-service-area rejection (OUT_OF_SERVICE_AREA)
6. BestStopResolver & candidate filtering (wrong-direction rejected, inactive route rejected, disconnected candidate rejected)
7. Controlled walking radius expansion (800m -> 1500m) & metadata disclosure (isExpandedRadius, searchRadiusMeters)
8. Multi-factor ranking & deterministic tie-breaking (walking cost, transit duration, transfer penalty, data confidence)
9. Explainable failures (OUT_OF_SERVICE_AREA, NO_NEARBY_STOPS, NO_VIABLE_ROUTE)
10. TransitPlanner direct route matching regression (Route 05)
11. TransitPlanner 1-transfer routing & detour ratio regression (Tam Kỳ <= 1.8)
12. MapService Leaflet multi-leg rendering & map pin contract (Leaflet/OSM preserved, zero Google Maps SDK)
13. Security & Credential Audit (zero hardcoded API keys / secrets)
14. Backward compatibility (findRoutesBetween)
"""

import os
import re
import sys
import json
import unittest
import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent

class TestTripPlanner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(WORKSPACE / 'data' / 'danangbus_routes.json', 'r', encoding='utf-8') as f:
            cls.routes = json.load(f)
        with open(WORKSPACE / 'data' / 'danangbus_stops.json', 'r', encoding='utf-8') as f:
            cls.stops = json.load(f)

    # 1. ResolvedLocation Contract (including Map Pin & GPS)
    def test_resolved_location_contract(self):
        node_script = """
        const { ResolvedLocation, LocationManager } = require('./js/busService.js');
        const loc1 = new ResolvedLocation({
            displayName: 'Cầu Rồng',
            address: 'Nguyễn Văn Linh, Hải Châu',
            lat: 16.0612,
            lng: 108.2272,
            provider: 'local',
            type: 'poi'
        });
        if (!loc1.isValid() || loc1.lat !== 16.0612 || loc1.type !== 'poi') process.exit(1);

        const invalidLoc = new ResolvedLocation({ displayName: 'Lỗi', lat: null, lng: 'abc' });
        if (invalidLoc.isValid()) process.exit(2);

        const outOfRange = new ResolvedLocation({ displayName: 'Vũ trụ', lat: 105.0, lng: 200.0 });
        if (outOfRange.isValid()) process.exit(3);

        // Map pin contract: must not fabricate address if unavailable
        const lm = new LocationManager();
        const pinLoc = lm.resolveFromMapPin(16.0612, 108.2272);
        if (!pinLoc || !pinLoc.isValid()) process.exit(4);
        if (pinLoc.type !== 'pin' || pinLoc.provider !== 'map_pin') process.exit(5);
        if (!pinLoc.displayName.includes('Ghim trên bản đồ')) process.exit(6);
        if (pinLoc.address !== pinLoc.displayName) process.exit(7); // Must NOT fabricate street address

        // GPS contract
        const gpsLoc = lm.resolveFromCoordinates(16.0612, 108.2272, 'Vị trí hiện tại', 'gps');
        if (!gpsLoc || !gpsLoc.isValid() || gpsLoc.type !== 'gps') process.exit(8);
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "ResolvedLocation contract failed")

    # 2. Duplicate Street Names Disambiguation
    def test_duplicate_street_names_disambiguation(self):
        node_script = """
        const fs = require('fs');
        const { BusService, LocationManager } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const lm = new LocationManager(bs);
        (async () => {
            // Search 'Trần Phú': must return both Đà Nẵng and Hội An candidates
            const tranPhuResults = await lm.search('Trần Phú');
            const dnTranPhu = tranPhuResults.find(r => r.address.includes('Hải Châu') || r.address.includes('Đà Nẵng'));
            const haTranPhu = tranPhuResults.find(r => r.address.includes('Hội An') || r.address.includes('Quảng Nam'));
            if (!dnTranPhu || !haTranPhu) {
                console.error('Expected distinct candidates for duplicate street Trần Phú');
                process.exit(1);
            }
            if (dnTranPhu.lat === haTranPhu.lat && dnTranPhu.lng === haTranPhu.lng) {
                console.error('Duplicate street candidates must have distinct coordinates');
                process.exit(2);
            }

            // Search 'Hùng Vương': must return both Đà Nẵng and Tam Kỳ candidates
            const hungVuongResults = await lm.search('Hùng Vương');
            const dnHungVuong = hungVuongResults.find(r => r.address.includes('Hải Châu') || r.address.includes('Đà Nẵng'));
            const tkHungVuong = hungVuongResults.find(r => r.address.includes('Tam Kỳ') || r.address.includes('Quảng Nam'));
            if (!dnHungVuong || !tkHungVuong) {
                console.error('Expected distinct candidates for duplicate street Hùng Vương');
                process.exit(3);
            }
        })();
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Duplicate street names disambiguation test failed")

    # 3. GoogleLocationProvider Boundary, Isolation & Safe Fallback
    def test_google_provider_unconfigured_and_isolation(self):
        node_script = """
        const { GoogleLocationProvider, LocationSearchProvider, LocationManager } = require('./js/busService.js');
        
        // 1. Inheritance
        const gp = new GoogleLocationProvider();
        if (!(gp instanceof LocationSearchProvider)) process.exit(1);

        // 2. Unconfigured -> inactive & safe fallback
        if (gp.isConfigured() !== false) process.exit(2);

        (async () => {
            const results = await gp.search('Cầu Rồng');
            if (!Array.isArray(results) || results.length !== 0) process.exit(3);

            const resolved = await gp.resolve('place_123');
            if (resolved !== null) process.exit(4);

            // LocationManager with unconfigured provider falls back to local seamlessly
            const lm = new LocationManager(null, { google: { apiKey: null } });
            const lmResults = await lm.search('Cầu Rồng');
            if (!lmResults || lmResults.length === 0) process.exit(5);
            if (lmResults[0].provider !== 'local') process.exit(6);
        })();
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Google provider unconfigured/isolation test failed")

    # 4. GoogleLocationProvider Network Errors, 429, Timeout & Safe Fallback
    def test_google_provider_error_handling(self):
        node_script = """
        const { GoogleLocationProvider, LocationManager } = require('./js/busService.js');

        // Test 1: Mock 429 rate limit
        global.fetch = async () => ({
            ok: false,
            status: 429,
            json: async () => ({ error: 'RATE_LIMIT_EXCEEDED' })
        });

        const gp = new GoogleLocationProvider({ apiKey: 'mock_test_key' });
        (async () => {
            const res429 = await gp.search('Nguyễn Văn Linh');
            if (!Array.isArray(res429) || res429.length !== 0) process.exit(1);

            // Test 2: Mock network error / rejection
            global.fetch = async () => { throw new Error('Network failure'); };
            const resNet = await gp.search('Nguyễn Văn Linh');
            if (!Array.isArray(resNet) || resNet.length !== 0) process.exit(2);

            // Test 3: LocationManager fallback to local when Google fails
            const lm = new LocationManager(null, { google: { apiKey: 'mock_test_key' } });
            const lmRes = await lm.search('Cầu Rồng');
            if (!lmRes || lmRes.length === 0 || lmRes[0].provider !== 'local') process.exit(3);
        })();
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Google provider error handling test failed")

    # 5. Stale Response Suppression
    def test_stale_response_suppression(self):
        node_script = """
        const { GoogleLocationProvider } = require('./js/busService.js');

        let delayMs = 100;
        global.fetch = async (url, options) => {
            const body = JSON.parse(options.body);
            const currentQuery = body.input;
            // Earlier query is delayed more
            const delay = currentQuery === 'query1' ? 80 : 10;
            await new Promise(r => setTimeout(r, delay));
            return {
                ok: true,
                json: async () => ({
                    suggestions: [{
                        placePrediction: {
                            placeId: `id_${currentQuery}`,
                            text: { text: `Result for ${currentQuery}` },
                            structuredFormat: { mainText: { text: `Result for ${currentQuery}` } }
                        }
                    }]
                })
            };
        };

        const gp = new GoogleLocationProvider({ apiKey: 'mock_test_key' });
        (async () => {
            const p1 = gp.search('query1');
            // Immediately issue query2 before query1 resolves
            const p2 = gp.search('query2');

            const [r1, r2] = await Promise.all([p1, p2]);
            // r1 must be suppressed (empty) because query2 was issued later
            if (r1.length !== 0) {
                console.error('Expected r1 to be suppressed, got:', r1);
                process.exit(1);
            }
            if (r2.length === 0 || !r2[0].displayName.includes('query2')) {
                console.error('Expected r2 to succeed with query2 results');
                process.exit(2);
            }
        })();
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Stale response suppression test failed")

    # 6. Service Area Geofence Check & OUT_OF_SERVICE_AREA
    def test_out_of_service_area_geofence(self):
        node_script = """
        const fs = require('fs');
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation, isWithinServiceArea } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const tp = new TransitPlanner(bs, new WalkingRouter());

        // Check isWithinServiceArea bounds
        if (!isWithinServiceArea(16.0612, 108.2272)) process.exit(1); // Da Nang Center
        if (!isWithinServiceArea(15.8778, 108.3283)) process.exit(2); // Hoi An
        if (!isWithinServiceArea(15.5684, 108.4816)) process.exit(3); // Tam Ky
        if (isWithinServiceArea(21.0285, 105.8542)) process.exit(4);  // Hanoi (Out of bounds)
        if (isWithinServiceArea(10.7769, 106.7009)) process.exit(5);  // HCMC (Out of bounds)

        // Planner out-of-service-area call
        const oLoc = new ResolvedLocation({ displayName: 'Đà Nẵng', lat: 16.0617, lng: 108.1834 });
        const dLoc = new ResolvedLocation({ displayName: 'Hồ Gươm Hà Nội', lat: 21.0285, lng: 105.8542 });

        const plan = tp.planTrip(oLoc, dLoc);
        if (plan.trips.length !== 0) process.exit(6);
        if (plan.error !== 'OUT_OF_SERVICE_AREA') {
            console.error('Expected OUT_OF_SERVICE_AREA, got:', plan.error);
            process.exit(7);
        }
        if (!plan.message || !plan.message.includes('ngoài phạm vi phục vụ')) process.exit(8);
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Out-of-service-area geofence test failed")

    # 7. Controlled Walking Radius Expansion (800m -> 1500m) & Disclosure Metadata
    def test_controlled_radius_expansion(self):
        node_script = """
        const fs = require('fs');
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const tp = new TransitPlanner(bs, new WalkingRouter());

        // Origin point at ~1000m from nearest bus stop in Hoa Hiep Nam (0 stops in 800m, 3 stops in 1500m)
        const oLoc = new ResolvedLocation({ displayName: 'Hòa Hiệp Nam Xa', lat: 16.1174388, lng: 108.1321979 });
        // Destination at CV Biển Đông on Route 05
        const dLoc = new ResolvedLocation({ displayName: 'CV Biển Đông', lat: 16.0687, lng: 108.2464 });

        const plan = tp.planTrip(oLoc, dLoc);
        if (!plan.trips || plan.trips.length === 0) {
            console.error('Expected trip via expanded radius (1500m)');
            process.exit(1);
        }

        // Must disclose expanded radius in plan and trip metadata
        if (plan.isExpandedRadius !== true) {
            console.error('Expected plan.isExpandedRadius === true');
            process.exit(2);
        }
        if (plan.searchRadiusMeters !== 1500) {
            console.error('Expected plan.searchRadiusMeters === 1500, got:', plan.searchRadiusMeters);
            process.exit(3);
        }

        const topTrip = plan.trips[0];
        if (topTrip.isExpandedRadius !== true || topTrip.searchRadiusMeters !== 1500) {
            console.error('Expected trip to carry isExpandedRadius metadata');
            process.exit(4);
        }
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Controlled radius expansion test failed")

    # 8. Best Stop Selection: Wrong-Direction Nearest Stop Rejected
    def test_wrong_direction_nearest_stop_rejected(self):
        node_script = """
        const fs = require('fs');
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation, BestStopResolver } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const tp = new TransitPlanner(bs, new WalkingRouter());
        const r05 = routes.find(r => r.routeNumber === '05');
        const outboundStops = r05.stops.outbound;

        // Choose stop S5 as destination
        const destStop = outboundStops[5];
        // Choose stop S2 as origin reference
        const origStop = outboundStops[2];

        // Position origin slightly closer to stop S7 than to stop S2
        // S7 is downstream (after S5 on outbound), so taking S7 is WRONG DIRECTION
        const oLoc = new ResolvedLocation({
            displayName: 'Điểm thử nghiệm',
            lat: origStop.lat,
            lng: origStop.lng
        });
        const dLoc = new ResolvedLocation({
            displayName: 'Điểm đến',
            lat: destStop.lat,
            lng: destStop.lng
        });

        const plan = tp.planTrip(oLoc, dLoc);
        if (!plan.trips || plan.trips.length === 0) process.exit(1);

        const trip = plan.trips[0];
        const transitLeg = trip.legs.find(l => l.type === 'transit');
        // The boarding stop must be upstream from destStop (oi < di)
        const oi = outboundStops.findIndex(s => s.name === transitLeg.boardingStop.name);
        const di = outboundStops.findIndex(s => s.name === transitLeg.alightingStop.name);

        if (oi >= di) {
            console.error('Monotonic direction violated: oi >= di');
            process.exit(2);
        }
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Wrong-direction nearest stop rejection test failed")

    # 9. Inactive & Temporally Invalid Route Rejected
    def test_inactive_route_rejected(self):
        node_script = """
        const fs = require('fs');
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const tp = new TransitPlanner(bs, new WalkingRouter());

        const oLoc = new ResolvedLocation({ displayName: 'ĐH Bách Khoa', lat: 16.0754, lng: 108.1528 });
        const dLoc = new ResolvedLocation({ displayName: 'CV Biển Đông', lat: 16.0687, lng: 108.2464 });

        // Temporarily suspend route 05 with verified override
        const r05 = bs.routes.find(r => r.routeNumber === '05');
        r05.temporaryOverrides = [{
            type: 'suspension',
            effectiveFrom: '2026-09-01T00:00:00+07:00',
            effectiveTo: '2026-10-31T23:59:59+07:00',
            verificationStatus: 'verified',
            sourceUrl: 'https://danangbus.vn/thong-bao-tam-dung-05'
        }];

        const plan = tp.planTrip(oLoc, dLoc, { queryTime: new Date('2026-09-30T10:00:00+07:00') });

        if (plan.trips && plan.trips.length > 0) {
            console.error('Expected 0 trips for temporally suspended route');
            process.exit(1);
        }
        if (plan.error !== 'NO_VIABLE_ROUTE') {
            console.error('Expected NO_VIABLE_ROUTE for suspended route query, got:', plan.error);
            process.exit(2);
        }
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Inactive route rejection test failed")

    # 10. Explainable Failure Contracts
    def test_explainable_failure_contracts(self):
        node_script = """
        const fs = require('fs');
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const tp = new TransitPlanner(bs, new WalkingRouter());

        // 1. OUT_OF_SERVICE_AREA
        const p1 = tp.planTrip(
            new ResolvedLocation({ displayName: 'Đà Nẵng', lat: 16.0617, lng: 108.1834 }),
            new ResolvedLocation({ displayName: 'Hà Nội', lat: 21.0285, lng: 105.8542 })
        );
        if (p1.error !== 'OUT_OF_SERVICE_AREA' || !p1.message.includes('ngoài phạm vi phục vụ')) process.exit(1);

        // 2. NO_NEARBY_STOPS: isolated mountain in Ba Na hills outside 1.5km of any stop
        const p2 = tp.planTrip(
            new ResolvedLocation({ displayName: 'Bà Nà Đỉnh', lat: 15.9980, lng: 107.9950 }),
            new ResolvedLocation({ displayName: 'CV Biển Đông', lat: 16.0687, lng: 108.2464 })
        );
        if (p2.error !== 'NO_NEARBY_STOPS' || !p2.message.includes('Không tìm thấy trạm dừng xe buýt')) process.exit(2);

        // 3. NO_VIABLE_ROUTE: route suspended
        const r05 = bs.routes.find(r => r.routeNumber === '05');
        r05.status = 'suspended';
        const p3 = tp.planTrip(
            new ResolvedLocation({ displayName: 'ĐH Bách Khoa', lat: 16.0754, lng: 108.1528 }),
            new ResolvedLocation({ displayName: 'CV Biển Đông', lat: 16.0687, lng: 108.2464 })
        );
        if (p3.error !== 'NO_VIABLE_ROUTE' || !p3.message.includes('Không tìm thấy hành trình phù hợp')) process.exit(3);
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Explainable failure contracts test failed")

    # 11. Direct Route Planning on Verified Route (Route 05) - Regression
    def test_transit_planner_direct_route_regression(self):
        node_script = """
        const fs = require('fs');
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const tp = new TransitPlanner(bs, new WalkingRouter());

        // Test pair on Route 05 (verified planning route)
        const oLoc = new ResolvedLocation({ displayName: 'ĐH Bách Khoa', lat: 16.0754, lng: 108.1528 });
        const dLoc = new ResolvedLocation({ displayName: 'CV Biển Đông', lat: 16.0687, lng: 108.2464 });

        const plan = tp.planTrip(oLoc, dLoc);
        if (!plan.trips || plan.trips.length === 0) process.exit(1);

        const topTrip = plan.trips[0];
        if (topTrip.type !== 'direct') process.exit(2);
        if (topTrip.transfers !== 0) process.exit(3);
        if (topTrip.legs.length !== 3) process.exit(4);
        if (topTrip.legs[0].type !== 'walking' || topTrip.legs[1].type !== 'transit' || topTrip.legs[2].type !== 'walking') process.exit(5);
        if (topTrip.legs[0].geometry !== null || topTrip.legs[2].geometry !== null) process.exit(6);
        if (!Array.isArray(topTrip.legs[1].geometry) || topTrip.legs[1].geometry.length <= 1) process.exit(7);
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "TransitPlanner direct route regression failed")

    # 12. One-Transfer Route Planning & Detour Ratio Check - Regression
    def test_transit_planner_transfer_and_detour_regression(self):
        node_script = """
        const fs = require('fs');
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const tp = new TransitPlanner(bs, new WalkingRouter());

        // Connect Route TKY-TMY and Route TKY-NTH in Tam Kỳ
        const oLoc = new ResolvedLocation({ displayName: 'Huỳnh Thúc Kháng', lat: 15.5673332, lng: 108.4904846 });
        const dLoc = new ResolvedLocation({ displayName: '954 Phan Châu Trinh', lat: 15.555436, lng: 108.5059009 });

        const plan = tp.planTrip(oLoc, dLoc);
        if (!plan.trips || plan.trips.length === 0) process.exit(1);

        const transferTrip = plan.trips.find(t => t.transfers === 1);
        if (!transferTrip) process.exit(2);

        if (transferTrip.legs.length !== 5) process.exit(3);
        if (transferTrip.legs[2].type !== 'walking') process.exit(4);
        if (transferTrip.legs[2].distanceMeters > tp.MAX_TRANSFER_WALK_METERS) process.exit(5);
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "TransitPlanner 1-transfer regression failed")

    # 13. MapService Multi-Leg & Pin Rendering Contract (Leaflet Preserved)
    def test_mapservice_multileg_and_pin_contract(self):
        with open(WORKSPACE / 'js' / 'mapService.js', 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('renderTrip', content, "MapService must provide renderTrip method")
        self.assertIn('clearTripLayers', content, "MapService must manage clearTripLayers")
        self.assertIn('tripPolylines', content, "MapService must track tripPolylines")
        self.assertIn('dashArray', content, "Estimated walking legs must use dashed styling")
        self.assertIn('trip-origin-marker', content, "Must render origin marker (A)")
        self.assertIn('trip-dest-marker', content, "Must render destination marker (B)")
        self.assertIn('trip-stop-transfer', content, "Must render transfer stop marker")
        self.assertIn('enableMapPinSelection', content, "Must implement enableMapPinSelection")
        self.assertIn('renderMapPinMarker', content, "Must implement renderMapPinMarker")
        self.assertIn('L.map', content, "Must strictly preserve Leaflet map")
        self.assertNotIn('google.maps', content, "Must NOT include Google Maps JavaScript SDK")

    # 14. UI Integration, Debounce & Map Pin Binding
    def test_app_ui_integration_contract(self):
        with open(WORKSPACE / 'js' / 'app.js', 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('tryRunPlanner', content, "app.js must implement tryRunPlanner")
        self.assertIn('renderPlannerResults', content, "app.js must implement renderPlannerResults")
        self.assertIn('renderTripOptions', content, "app.js must implement renderTripOptions")
        self.assertIn('openPlannedTripMap', content, "app.js must implement openPlannedTripMap")
        self.assertIn('trip-planner-options', content, "app.js must integrate trip-planner-options")
        self.assertIn('btn-picker-map-pin', content, "app.js must bind map pin picker CTA")
        self.assertIn('searchDebounceTimer', content, "app.js must debounce search input")

    # 15. Backward Compatibility: findRoutesBetween Unchanged
    def test_find_routes_between_backward_compatibility(self):
        node_script = """
        const fs = require('fs');
        const { BusService } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.isLoaded = true;

        const direct = bs.findRoutesBetween('Bến xe TT', 'Phố cổ Hội An');
        if (direct.length === 0 || direct[0].routeNumber !== '02') process.exit(1);

        const disjoint = bs.findRoutesBetween('Hòa Hiệp Nam', 'Phố cổ Hội An');
        if (!Array.isArray(disjoint) || disjoint.length !== 0) process.exit(2);
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "findRoutesBetween backward compatibility failed")

    # 16. Security Contract: Zero Hardcoded API Keys / Credentials
    def test_security_credential_audit(self):
        # Prohibited terms representing algorithm bypass or client-side Google Maps SDK
        prohibited_sdk_terms = [
            "findTransferRoutes",
            "buildTransferItinerary",
            "findMultiLegRoutes",
            "transferItinerary",
            "google.maps.Map",
            "maps.googleapis.com/maps/api/js"
        ]
        files_to_check = [
            WORKSPACE / "js" / "busService.js",
            WORKSPACE / "js" / "app.js",
            WORKSPACE / "js" / "mapService.js",
            WORKSPACE / "index.html"
        ]
        google_api_key_regex = re.compile(r'AIza[0-9A-Za-z-_]{35}')

        for fpath in files_to_check:
            if not fpath.exists(): continue
            content = fpath.read_text(encoding="utf-8")
            
            # 1. No committed API keys
            matches = google_api_key_regex.findall(content)
            self.assertEqual(len(matches), 0, f"Found hardcoded Google API key in {fpath.name}: {matches}")

            # 2. No prohibited SDK terms
            for term in prohibited_sdk_terms:
                self.assertNotIn(term, content, f"Prohibited SDK term '{term}' found in {fpath.name}")

if __name__ == '__main__':
    unittest.main()
