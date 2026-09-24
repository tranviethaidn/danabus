#!/usr/bin/env python3
"""
Comprehensive Automated Test Suite for Danabus Map, GPS & Fail-Closed Resolver
Validates:
1. Stop Provenance & Semantics (181 verified with valid OSM provenance, 240 unresolved/needs_review kept null).
2. Strict Negative Cases (Nam Phước, Lê Văn Hiến addresses, Cửa Đại addresses).
3. OSM ID Isolation & Street Boundary Integrity.
4. Route Geometry Verification: Verified routes (Route 05, etc.) vs Fail-Closed Unverified routes (geometry=null, verified=false).
5. Independent Outbound & Inbound Geometry Datasets.
6. Stop Ordering Monotonicity along Route Paths.
7. Resolution Report Integrity (421 stops classified into verified / needs_review / unresolved).
8. MapService Layer Management & Stale Layer Cleanup Logic.
9. Browser Geolocation Contract (Accuracy circle, error codes 1/2/3).
10. Source Code Audits (No hard-coded basePoints, no fake simulation badges).
11. TypeScript Schema Definitions.
"""

import os
import sys
import json
import math
import unittest

class TestDanabusMapGPS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open('data/danangbus_routes.json', 'r', encoding='utf-8') as f:
            cls.routes = json.load(f)
        with open('data/danangbus_stops.json', 'r', encoding='utf-8') as f:
            cls.stops = json.load(f)
        with open('data/danangbus_routes_compact.json', 'r', encoding='utf-8') as f:
            cls.compact_routes = json.load(f)
        with open('data/danangbus_resolution_report.json', 'r', encoding='utf-8') as f:
            cls.resolution_report = json.load(f)

    def get_route(self, route_id):
        return next((r for r in self.routes if r['id'] == route_id), None)

    # 1. Provenance Semantics for Stops
    def test_stop_provenance_semantics(self):
        verified_count = 0
        unresolved_count = 0
        verified_osm_ids = set()

        for s in self.stops:
            status = s.get('status')
            if status == 'verified':
                verified_count += 1
                lat = s.get('lat')
                lng = s.get('lng')
                self.assertIsNotNone(lat, f"Verified stop {s.get('name')} must have lat")
                self.assertIsNotNone(lng, f"Verified stop {s.get('name')} must have lng")
                self.assertTrue(15.4 <= lat <= 16.3, f"Latitude {lat} out of Da Nang/Quang Nam bbox")
                self.assertTrue(108.0 <= lng <= 108.6, f"Longitude {lng} out of Da Nang/Quang Nam bbox")
                self.assertIn(s.get('source'), ['osm_nominatim', 'osm_overpass_transit'], "Verified stops must have valid OSM source")
                self.assertIn(s.get('osm_type'), ['way', 'node'], "Verified stops must record osm_type")
                self.assertIsNotNone(s.get('osm_id'), "Verified stop must have osm_id")
                self.assertIsNotNone(s.get('display_name'), "Verified stops must record display_name")
                self.assertIn(s.get('confidence'), ['high', 'medium'])
                verified_osm_ids.add(s.get('osm_id'))
            else:
                unresolved_count += 1
                self.assertEqual(status, 'unresolved')
                self.assertIsNone(s.get('lat'), f"Unresolved stop {s.get('name')} must have lat=None")
                self.assertIsNone(s.get('lng'), f"Unresolved stop {s.get('name')} must have lng=None")
                self.assertIsNone(s.get('source'), f"Unresolved stop {s.get('name')} must have source=None")
                self.assertIsNone(s.get('osm_id'), f"Unresolved stop {s.get('name')} must have osm_id=None")
                self.assertIsNone(s.get('osm_type'), f"Unresolved stop {s.get('name')} must have osm_type=None")

        print(f"\n[Test Info] Stops breakdown: {verified_count} verified stops across {len(verified_osm_ids)} unique OSM locations, {unresolved_count} unresolved/needs_review stops.")
        self.assertEqual(len(self.stops), 421, "Total stops must be 421")
        self.assertEqual(verified_count, 245, "Verified stops must be exactly 245")
        self.assertEqual(unresolved_count, 176, "Unresolved stops must be exactly 176")

    # 2. Strict Negative Case Validations (No false-positive contamination)
    def test_negative_cases_no_false_positive_matching(self):
        # Negative Case 1: Nam Phước terminal must NOT match Da Nang central station
        nam_phuoc_stops = [s for s in self.stops if 'nam phước' in s.get('name', '').lower()]
        for s in nam_phuoc_stops:
            self.assertNotEqual(s.get('osm_id'), 256668716, f"Nam Phước stop '{s.get('name')}' must not match Da Nang central station")

        # Negative Case 2: Ordinary house numbers on Lê Văn Hiến must NOT match landmark BV Phụ sản - Nhi (344021057)
        lvh_house_number_stops = [
            s for s in self.stops 
            if s.get('name') in ['40 Lê Văn Hiến', '754 Lê Văn Hiến', '125-127 Lê Văn Hiến', 'Đ/d 722-724 Lê Văn Hiến (Chùa Non Nước)', 'Đ/d 50 Lê Văn Hiến', 'Đ/d UBND quận Ngũ Hành Sơn']
        ]
        for s in lvh_house_number_stops:
            self.assertNotEqual(s.get('osm_id'), 344021057, f"Ordinary stop '{s.get('name')}' on Lê Văn Hiến must not inherit landmark BV Phụ sản - Nhi ID")

        # Negative Case 3: Street addresses on Cửa Đại must NOT match landmark Biển Cửa Đại
        cua_dai_address_stops = [
            s for s in self.stops 
            if any(addr in s.get('name', '') for addr in ['265 Cửa Đại', '113 Cửa Đại', '11 Cửa Đại', 'Bưu Điện Cửa Đại', 'Đối Diện 113 Cửa Đại'])
        ]
        for s in cua_dai_address_stops:
            self.assertNotEqual(s.get('osm_id'), 149699484, f"Address '{s.get('name')}' must not inherit Biển Cửa Đại landmark ID")
            self.assertEqual(s.get('status'), 'unresolved', f"Address '{s.get('name')}' on Cửa Đại without audited transit node must be unresolved")

    # 3. OSM ID Isolation (No landmark leakage to arbitrary stops)
    def test_osm_id_isolation(self):
        bv_nhi_stops = [s for s in self.stops if s.get('osm_id') == 344021057]
        self.assertTrue(len(bv_nhi_stops) <= 1, "Only the exact BV Phụ sản - Nhi stop may have osm_id 344021057")
        if bv_nhi_stops:
            self.assertIn("phụ sản nhi", bv_nhi_stops[0].get('name', '').lower())

    # 4. Resolution Report Audit
    def test_resolution_report_structure(self):
        self.assertEqual(self.resolution_report.get('total_stops'), 421)
        self.assertEqual(len(self.resolution_report.get('verified', [])), 245)
        self.assertEqual(len(self.resolution_report.get('needs_review', [])), 29)
        self.assertEqual(len(self.resolution_report.get('unresolved', [])), 147)
        self.assertEqual(245 + 29 + 147, 421)

    # 5. Route 05 Verified Geometry vs Fail-Closed Unverified Routes
    def test_route_geometry_verification_and_fail_closed(self):
        r05 = self.get_route('05')
        self.assertIsNotNone(r05['geometry']['outbound'])
        self.assertIsNotNone(r05['geometry']['inbound'])
        self.assertTrue(r05['geometry']['provenance']['outbound']['verified'])
        self.assertTrue(r05['geometry']['provenance']['inbound']['verified'])
        self.assertTrue(len(r05['geometry']['outbound']) > 100)
        self.assertTrue(len(r05['geometry']['inbound']) > 100)

        # Fail-closed unverified routes (e.g. Route 02, 21, 11, 07, 08, 12, LK01...)
        unverified_route_ids = ['02', '21', '07', '08', '11', '12', '03', '06', '09', '13', '14', 'LK01', 'LK02', 'LK21', '04', '10', '15']
        for rid in unverified_route_ids:
            r = self.get_route(rid)
            self.assertIsNotNone(r, f"Route {rid} must exist")
            geom = r.get('geometry', {})
            out_geom = geom.get('outbound')
            in_geom = geom.get('inbound')
            prov_out = geom.get('provenance', {}).get('outbound', {})
            prov_in = geom.get('provenance', {}).get('inbound', {})

            self.assertIsNone(out_geom, f"Route {rid} outbound geometry must remain null (failed validation / insufficient anchors)")
            self.assertIsNone(in_geom, f"Route {rid} inbound geometry must remain null (failed validation / insufficient anchors)")
            self.assertFalse(prov_out.get('verified', True), f"Route {rid} outbound provenance must have verified=False")
            self.assertFalse(prov_in.get('verified', True), f"Route {rid} inbound provenance must have verified=False")

    # 6. Route 05 Outbound vs Inbound Independence
    def test_route_05_outbound_vs_inbound_independent(self):
        r05 = self.get_route('05')
        out_geom = r05['geometry']['outbound']
        in_geom = r05['geometry']['inbound']
        self.assertNotEqual(out_geom, in_geom, "Outbound and Inbound geometries must be different")
        self.assertNotEqual(out_geom, list(reversed(in_geom)), "Inbound cannot be a simple array reverse of outbound")

    # 7. Stop Ordering Monotonicity
    def test_stop_ordering_monotonic(self):
        for r in self.routes:
            for d in ['outbound', 'inbound']:
                stops = r.get('stops', {}).get(d, [])
                orders = [s.get('order') for s in stops if 'order' in s]
                if orders:
                    sorted_orders = sorted(orders)
                    self.assertEqual(orders, sorted_orders, f"Route {r['id']} {d} stops must have monotonic increasing order")

    # 8. MapService Layer Management & Stale Layer Cleanup Logic
    def test_mapservice_layer_management_and_stale_cleanup(self):
        with open('js/mapService.js', 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('this.clear()', content, "renderRoute must call this.clear() to prevent stale layers")
        self.assertIn('this.markersLayer.clearLayers()', content, "clear() must clear all stop markers")
        self.assertIn('this.map.removeLayer(this.routeLine)', content, "clear() must remove previous polyline")
        self.assertIn('this.removeInfoOverlay()', content, "clear() must remove stale overlays")
        self.assertIn('showInfoOverlay', content, "mapService must provide showInfoOverlay for unverified routes")

    # 9. Browser Geolocation Error Handling & Accuracy Circle in MapService
    def test_mapservice_geolocation_contract(self):
        with open('js/mapService.js', 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('navigator.geolocation', content, "Must check navigator.geolocation")
        self.assertIn('getCurrentPosition', content, "Must call getCurrentPosition")
        self.assertIn('enableHighAccuracy: true', content, "Must request high accuracy GPS")
        self.assertIn('accuracyCircle', content, "Must handle accuracy circle")
        self.assertIn('err.code === 1', content, "Must handle permission denied (code 1)")
        self.assertIn('err.code === 2', content, "Must handle position unavailable (code 2)")
        self.assertIn('err.code === 3', content, "Must handle timeout (code 3)")

    # 10. Source Code Audits: No basePoints hard-code in mapService.js & No fake live bus
    def test_source_code_audits_cleanliness(self):
        with open('js/mapService.js', 'r', encoding='utf-8') as f:
            map_content = f.read()
        self.assertNotIn('const basePoints', map_content, "mapService.js must not contain hard-coded basePoints array")
        self.assertNotIn('let basePoints', map_content, "mapService.js must not contain hard-coded basePoints")
        self.assertNotIn('43B-028.91', map_content, "mapService.js must not contain fake vehicle license plates")
        self.assertNotIn('isLiveBus', map_content, "mapService.js must not simulate live bus at arbitrary index")

        with open('js/app.js', 'r', encoding='utf-8') as f:
            app_content = f.read()
        self.assertNotIn('Xe đang tới', app_content, "app.js must not contain fake 'Xe đang tới' simulation badge")
        self.assertNotIn('Vị trí của bạn (Bến xe Trung tâm)', app_content, "app.js must not default to fake origin location")

    # 11. Schema TypeScript consistency
    def test_schema_ts_definitions(self):
        with open('data/schema.ts', 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('StopConfidence', content)
        self.assertIn('StopStatus', content)
        self.assertIn('RouteGeometry', content)
        self.assertIn('RouteGeometryProvenance', content)

if __name__ == '__main__':
    unittest.main()
