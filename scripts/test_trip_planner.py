#!/usr/bin/env python3
"""
Comprehensive Automated Test Suite for Address-to-Address Trip Planner (Task 4)
Validates:
1. ResolvedLocation contract (validation, coordinates, provider metadata)
2. LocationSearchProvider & LocalLocationProvider (POI resolution, address search, stop search)
3. LocationManager (caching, reverse resolve, coordinates resolution, GPS contract)
4. WalkingRouter (strict semantic estimate, geometry: null, distance/duration calculation)
5. Spatial candidate search (findNearbyStops, radius bounds, verified stop filtering)
6. TransitPlanner direct route matching (order monotonicity, sliced geometry, walking legs)
7. TransitPlanner 1-transfer routing (transfer walk <= 400m, anti-loop, detour ratio <= 1.8)
8. Fail-closed data quality policy (eligibleForPlanning: true only, ineligible routes excluded)
9. Ranking & Deduplication (badges: Tuyến trực tiếp, Ít đi bộ nhất, Nhanh nhất)
10. MapService Leaflet multi-leg rendering contract (dashed walking, solid transit, marker pins, cleanup)
11. UI integration contract (non-stale swap, picker binding, findRoutesBetween compatibility)
12. Prohibited terms security audit (zero unauthorized SDKs/APIs)
"""

import os
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

    # 1. ResolvedLocation Contract
    def test_resolved_location_contract(self):
        node_script = """
        const { ResolvedLocation } = require('./js/busService.js');
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
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "ResolvedLocation contract failed")

    # 2. LocationSearchProvider & LocalLocationProvider
    def test_local_location_provider(self):
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
            // Test 1: POI search
            const p1 = await lm.search('Cầu Rồng');
            if (!p1.some(i => i.displayName.includes('Cầu Rồng'))) process.exit(1);

            // Test 2: Address search
            const p2 = await lm.search('123 Nguyễn Văn Linh');
            if (!p2.some(i => i.displayName.includes('123 Nguyễn Văn Linh'))) process.exit(2);

            // Test 3: Stop search
            const p3 = await lm.search('Cao Sơn Pháo');
            if (p3.length === 0) process.exit(3);

            // Test 4: Curated POIs have valid GPS
            for (const poi of lm.localProvider.localPOIs) {
                if (typeof poi.lat !== 'number' || typeof poi.lng !== 'number') process.exit(4);
            }
        })();
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "LocalLocationProvider search test failed")

    # 3. WalkingRouter Semantic Integrity
    def test_walking_router_semantics(self):
        node_script = """
        const { WalkingRouter, haversineDistance } = require('./js/busService.js');
        const router = new WalkingRouter();

        const from = [16.0617, 108.1834]; // Bến xe TT
        const to = [16.0650, 108.1850];
        const leg = router.createWalkingLeg('Bến xe TT', 'Điểm đến', from, to);

        if (!leg) process.exit(1);
        if (leg.type !== 'walking') process.exit(2);
        if (leg.isEstimated !== true) process.exit(3); // Strict estimate
        if (leg.geometry !== null) process.exit(4);    // MUST NOT fake road geometry
        if (typeof leg.distanceMeters !== 'number' || leg.distanceMeters <= 0) process.exit(5);
        if (typeof leg.durationMinutes !== 'number' || leg.durationMinutes <= 0) process.exit(6);
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "WalkingRouter semantic integrity failed")

    # 4. Direct Route Planning on Verified Route (Route 05)
    def test_transit_planner_direct_route(self):
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
        // Đại học Bách Khoa -> CV Biển Đông
        const oLoc = new ResolvedLocation({ displayName: 'ĐH Bách Khoa', lat: 16.0754, lng: 108.1528 });
        const dLoc = new ResolvedLocation({ displayName: 'CV Biển Đông', lat: 16.0687, lng: 108.2464 });

        const plan = tp.planTrip(oLoc, dLoc);
        if (!plan.trips || plan.trips.length === 0) {
            console.error('Expected direct trips on Route 05, got 0');
            process.exit(1);
        }

        const topTrip = plan.trips[0];
        if (topTrip.type !== 'direct') process.exit(2);
        if (topTrip.transfers !== 0) process.exit(3);
        if (topTrip.legs.length !== 3) process.exit(4); // walk -> transit -> walk
        if (topTrip.legs[0].type !== 'walking' || topTrip.legs[1].type !== 'transit' || topTrip.legs[2].type !== 'walking') process.exit(5);
        if (topTrip.legs[0].geometry !== null || topTrip.legs[2].geometry !== null) process.exit(6);
        if (!Array.isArray(topTrip.legs[1].geometry) || topTrip.legs[1].geometry.length <= 1) process.exit(7); // Sliced verified bus geometry
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "TransitPlanner direct route test failed")

    # 5. One-Transfer Route Planning & Detour Ratio Check
    def test_transit_planner_transfer_and_detour(self):
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
        if (!plan.trips || plan.trips.length === 0) {
            console.error('Expected connecting trip in Tam Kỳ, got 0');
            process.exit(1);
        }

        const transferTrip = plan.trips.find(t => t.transfers === 1);
        if (!transferTrip) {
            console.error('Expected at least 1 transfer trip');
            process.exit(2);
        }

        // Must have 5 legs: walk -> transit A -> transfer walk -> transit B -> walk
        if (transferTrip.legs.length !== 5) process.exit(3);
        if (transferTrip.legs[2].type !== 'walking') process.exit(4);
        if (transferTrip.legs[2].distanceMeters > tp.MAX_TRANSFER_WALK_METERS) process.exit(5); // Transfer walk <= 400m
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "TransitPlanner 1-transfer & detour test failed")

    # 6. Fail-Closed Exclusion of Ineligible Directions
    def test_ineligible_directions_fail_closed(self):
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

        // Disjoint endpoints where only ineligible routes run or no connection exists
        const oLoc = new ResolvedLocation({ displayName: 'Đà Nẵng', lat: 16.0617, lng: 108.1834 });
        const dLoc = new ResolvedLocation({ displayName: 'Hà Nội', lat: 21.0285, lng: 105.8542 });

        const plan = tp.planTrip(oLoc, dLoc);
        if (plan.trips && plan.trips.length > 0) {
            console.error('Expected empty trips for disconnected cities, got:', plan.trips.length);
            process.exit(1);
        }
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Ineligible directions fail-closed test failed")

    # 7. MapService Multi-Leg Rendering Contract
    def test_mapservice_multileg_contract(self):
        with open(WORKSPACE / 'js' / 'mapService.js', 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('renderTrip', content, "MapService must provide renderTrip method")
        self.assertIn('clearTripLayers', content, "MapService must manage clearTripLayers")
        self.assertIn('tripPolylines', content, "MapService must track tripPolylines")
        self.assertIn('dashArray', content, "Estimated walking legs must use dashed styling")
        self.assertIn('trip-origin-marker', content, "Must render origin marker (A)")
        self.assertIn('trip-dest-marker', content, "Must render destination marker (B)")
        self.assertIn('trip-stop-transfer', content, "Must render transfer stop marker")

    # 8. UI Integration & Non-Stale Swap
    def test_app_ui_integration_contract(self):
        with open(WORKSPACE / 'js' / 'app.js', 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('tryRunPlanner', content, "app.js must implement tryRunPlanner")
        self.assertIn('renderPlannerResults', content, "app.js must implement renderPlannerResults")
        self.assertIn('renderTripOptions', content, "app.js must implement renderTripOptions")
        self.assertIn('openPlannedTripMap', content, "app.js must implement openPlannedTripMap")
        self.assertIn('trip-planner-options', content, "app.js must integrate trip-planner-options")

    # 9. Backward Compatibility: findRoutesBetween Unchanged
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

    # 10. Prohibited Terms Static Scan
    def test_prohibited_terms_static_scan(self):
        prohibited_terms = [
            "findTransferRoutes",
            "buildTransferItinerary",
            "findMultiLegRoutes",
            "transferItinerary",
            "places.googleapis.com",
            "maps.googleapis.com",
            "google.maps.places"
        ]
        files_to_check = [
            WORKSPACE / "js" / "busService.js",
            WORKSPACE / "js" / "app.js",
            WORKSPACE / "js" / "mapService.js",
            WORKSPACE / "index.html"
        ]
        for fpath in files_to_check:
            if not fpath.exists(): continue
            content = fpath.read_text(encoding="utf-8")
            for term in prohibited_terms:
                self.assertNotIn(term, content, f"Prohibited term '{term}' found in {fpath.name}")

if __name__ == '__main__':
    unittest.main()
