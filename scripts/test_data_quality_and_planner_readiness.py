#!/usr/bin/env python3
"""
Task 8 Automated Acceptance Test Suite: Data Quality Contract & Planner Readiness
Verifies:
1. dataQuality contract on all 23 routes in data/danangbus_routes.json (6 route-level fields + direction readiness + stop metrics)
2. Strict fail-closed logic: unresolved stops, < 2 verified stops, non-monotonic stops, invalid/unverified geometry, suspended routes, unknown/invalid fares
3. Zero drift validation and drift-detection sensitivity
4. Direction-level readiness isolation (e.g. TKY-CHU inbound eligible while outbound ineligible)
5. Coverage report reproducibility and consistency with dataset
6. Haversine distance accuracy and fail-closed edge cases
7. findNearbyStops spatial query: verified-only filter, maxDistanceMeters, limit, ascending distance sort
8. Node.js BusService integration with spatial primitives and planning readiness methods
"""

import unittest
import json
import os
import sys
import subprocess
import copy
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from validate_data_quality import (
    compute_data_quality,
    evaluate_direction_stops,
    evaluate_direction_geometry,
    evaluate_fare_model,
    run_validation,
    generate_coverage_report,
    clean_data_quality_for_comparison,
    is_finite_number,
    is_valid_coordinate
)

ROUTES_PATH = "data/danangbus_routes.json"
COVERAGE_REPORT_PATH = "docs/reports/task-8-data-quality-coverage.json"

class TestDataQualityAndPlannerReadiness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(ROUTES_PATH, "r", encoding="utf-8") as f:
            cls.routes = json.load(f)

    # -------------------------------------------------------------------------
    # 1. Route Data Quality Contract Verification
    # -------------------------------------------------------------------------
    def test_all_23_routes_have_canonical_data_quality(self):
        """All 23 routes must have the complete dataQuality contract matching schema.ts."""
        self.assertEqual(len(self.routes), 23, "Dataset must contain exactly 23 routes.")
        
        required_route_fields = [
            "hasOutboundStops",
            "hasInboundStops",
            "hasOutboundGeometry",
            "hasInboundGeometry",
            "hasFareModel",
            "tripPlanningReady",
            "directions",
            "stopMetrics"
        ]
        
        for r in self.routes:
            rid = r.get("id")
            dq = r.get("dataQuality")
            self.assertIsNotNone(dq, f"Tuyến {rid} thiếu trường dataQuality")
            
            for field in required_route_fields:
                self.assertIn(field, dq, f"Tuyến {rid} thiếu trường {field} trong dataQuality")
                
            # Direction structure verification
            self.assertIn("outbound", dq["directions"])
            self.assertIn("inbound", dq["directions"])
            for dir_key in ["outbound", "inbound"]:
                dir_dq = dq["directions"][dir_key]
                self.assertIn("stopsReady", dir_dq)
                self.assertIn("geometryReady", dir_dq)
                self.assertIn("eligibleForPlanning", dir_dq)
                self.assertIsInstance(dir_dq["stopsReady"], bool)
                self.assertIsInstance(dir_dq["geometryReady"], bool)
                self.assertIsInstance(dir_dq["eligibleForPlanning"], bool)
                
            # Stop metrics structure verification
            self.assertIn("outbound", dq["stopMetrics"])
            self.assertIn("inbound", dq["stopMetrics"])
            for dir_key in ["outbound", "inbound"]:
                m = dq["stopMetrics"][dir_key]
                self.assertIn("total", m)
                self.assertIn("verified", m)
                self.assertIn("unresolved", m)
                self.assertEqual(m["total"], m["verified"] + m["unresolved"],
                                 f"Tuyến {rid} chiều {dir_key}: total != verified + unresolved")

    def test_zero_drift_on_current_dataset(self):
        """Metadata in data/danangbus_routes.json must strictly match deterministic validator output."""
        drift_count, errors = run_validation(self.routes, strict_check=True)
        self.assertEqual(drift_count, 0, f"Detected metadata drift on {drift_count} routes: {errors}")

    def test_drift_detection_fail_closed(self):
        """Validator must detect any metadata drift or unauthorized tampering."""
        tampered_routes = copy.deepcopy(self.routes)
        # Illegally set route 21 to tripPlanningReady=True
        r21 = next(r for r in tampered_routes if r["id"] == "21")
        r21["dataQuality"]["tripPlanningReady"] = True
        
        drift_count, errors = run_validation(tampered_routes, strict_check=True)
        self.assertGreater(drift_count, 0, "Validator must detect tampered tripPlanningReady")
        self.assertTrue(any("Tuyến 21" in e for e in errors))

    # -------------------------------------------------------------------------
    # 2. Strict Negative Cases (Fail-Closed Gates)
    # -------------------------------------------------------------------------
    def test_negative_case_unresolved_and_insufficient_stops(self):
        """Direction with < 2 verified stops or non-monotonic stops must fail stopsReady."""
        # Case A: 0 verified stops
        ready, metrics, err = evaluate_direction_stops([
            {"order": 1, "name": "Stop 1", "status": "unresolved"},
            {"order": 2, "name": "Stop 2", "status": "unresolved"}
        ])
        self.assertFalse(ready)
        self.assertEqual(metrics["verified"], 0)
        self.assertEqual(metrics["unresolved"], 2)
        self.assertIn("Chỉ có 0/2 trạm verified", err)
        
        # Case B: 1 verified stop (insufficient for line segment)
        ready, metrics, err = evaluate_direction_stops([
            {"order": 1, "name": "Stop 1", "status": "verified", "lat": 16.0, "lng": 108.0},
            {"order": 2, "name": "Stop 2", "status": "unresolved"}
        ])
        self.assertFalse(ready)
        self.assertEqual(metrics["verified"], 1)
        self.assertIn("Chỉ có 1/2 trạm verified", err)
        
        # Case C: Non-monotonic stop order (order 5 then 3)
        ready, metrics, err = evaluate_direction_stops([
            {"order": 5, "name": "Stop A", "status": "verified", "lat": 16.0, "lng": 108.0},
            {"order": 3, "name": "Stop B", "status": "verified", "lat": 16.1, "lng": 108.1}
        ])
        self.assertFalse(ready)
        self.assertIn("không tăng đơn điệu", err)

        # Case D: Out-of-range GPS coordinates (lat > 90 or < -90, lng > 180 or < -180, NaN, Inf, string)
        ready, metrics, err = evaluate_direction_stops([
            {"order": 1, "name": "Stop 1", "status": "verified", "lat": 95.0, "lng": 108.0},
            {"order": 2, "name": "Stop 2", "status": "verified", "lat": 16.0, "lng": 108.0}
        ])
        self.assertFalse(ready)
        self.assertEqual(metrics["verified"], 1, "Stop with lat 95.0 must not count as verified")
        self.assertIn("Chỉ có 1/2 trạm verified", err)

        # lat < -90
        ready, metrics, err = evaluate_direction_stops([
            {"order": 1, "name": "Stop 1", "status": "verified", "lat": -95.0, "lng": 108.0},
            {"order": 2, "name": "Stop 2", "status": "verified", "lat": -96.0, "lng": 108.0}
        ])
        self.assertFalse(ready)
        self.assertEqual(metrics["verified"], 0, "Stops with lat < -90 must not count as verified")

        # lng > 180 and lng < -180
        ready, metrics, err = evaluate_direction_stops([
            {"order": 1, "name": "Stop 1", "status": "verified", "lat": 16.0, "lng": 185.0},
            {"order": 2, "name": "Stop 2", "status": "verified", "lat": 16.0, "lng": -185.0}
        ])
        self.assertFalse(ready)
        self.assertEqual(metrics["verified"], 0, "Stops with lng outside [-180, 180] must not count as verified")

        # NaN, Inf, string coordinates
        ready, metrics, err = evaluate_direction_stops([
            {"order": 1, "name": "Stop 1", "status": "verified", "lat": float("nan"), "lng": 108.0},
            {"order": 2, "name": "Stop 2", "status": "verified", "lat": 16.0, "lng": float("inf")},
            {"order": 3, "name": "Stop 3", "status": "verified", "lat": "16.0", "lng": "108.0"}
        ])
        self.assertFalse(ready)
        self.assertEqual(metrics["verified"], 0, "NaN, Inf, or string coordinates must not count as verified")

        # Case E: Boolean coordinates (lat=True/False, lng=True/False) must be rejected
        ready, metrics, err = evaluate_direction_stops([
            {"order": 1, "name": "Stop 1", "status": "verified", "lat": True, "lng": 108.0},
            {"order": 2, "name": "Stop 2", "status": "verified", "lat": 16.0, "lng": False},
            {"order": 3, "name": "Stop 3", "status": "verified", "lat": False, "lng": True}
        ])
        self.assertFalse(ready)
        self.assertEqual(metrics["verified"], 0, "Boolean lat/lng coordinates must not count as verified")

    def test_negative_case_invalid_unverified_geometry(self):
        """Missing, insufficient points, unverified provenance, or out-of-range coords must fail geometryReady."""
        # Case A: null/empty geometry
        ready, err = evaluate_direction_geometry({"geometry": None}, "outbound")
        self.assertFalse(ready)
        
        # Case B: points < 2
        ready, err = evaluate_direction_geometry({
            "geometry": {"outbound": [[16.0, 108.0]], "provenance": {"outbound": {"verified": True}}}
        }, "outbound")
        self.assertFalse(ready)
        self.assertIn("points < 2", err)
        
        # Case C: provenance.verified != True
        ready, err = evaluate_direction_geometry({
            "geometry": {
                "outbound": [[16.0, 108.0], [16.1, 108.1]],
                "provenance": {"outbound": {"verified": False}}
            }
        }, "outbound")
        self.assertFalse(ready)
        self.assertIn("chưa được xác minh", err)

        # Case D: non-finite coordinates in points
        ready, err = evaluate_direction_geometry({
            "geometry": {
                "outbound": [[16.0, 108.0], [None, 108.1]],
                "provenance": {"outbound": {"verified": True}}
            }
        }, "outbound")
        self.assertFalse(ready)
        self.assertIn("Tọa độ polyline không hợp lệ", err)

        # Case E: out-of-range GPS coordinates (latitude 95.0/96.0, < -90, or longitude > 180, < -180)
        ready, err = evaluate_direction_geometry({
            "geometry": {
                "outbound": [[95.0, 108.0], [96.0, 108.1]],
                "provenance": {"outbound": {"verified": True}}
            }
        }, "outbound")
        self.assertFalse(ready)
        self.assertIn("ngoài phạm vi địa lý", err)

        # lat < -90
        ready, err = evaluate_direction_geometry({
            "geometry": {
                "outbound": [[-95.0, 108.0], [-96.0, 108.1]],
                "provenance": {"outbound": {"verified": True}}
            }
        }, "outbound")
        self.assertFalse(ready)
        self.assertIn("ngoài phạm vi địa lý", err)

        # lng > 180
        ready, err = evaluate_direction_geometry({
            "geometry": {
                "outbound": [[16.0, 185.0], [16.1, 108.1]],
                "provenance": {"outbound": {"verified": True}}
            }
        }, "outbound")
        self.assertFalse(ready)
        self.assertIn("ngoài phạm vi địa lý", err)

        # lng < -180
        ready, err = evaluate_direction_geometry({
            "geometry": {
                "outbound": [[16.0, -185.0], [16.1, 108.1]],
                "provenance": {"outbound": {"verified": True}}
            }
        }, "outbound")
        self.assertFalse(ready)
        self.assertIn("ngoài phạm vi địa lý", err)

        # NaN or Inf in points
        ready, err = evaluate_direction_geometry({
            "geometry": {
                "outbound": [[float("nan"), 108.0], [16.1, 108.1]],
                "provenance": {"outbound": {"verified": True}}
            }
        }, "outbound")
        self.assertFalse(ready)
        self.assertIn("Tọa độ polyline không hợp lệ", err)

        # Case F: Boolean coordinates in points ([True, 108.0] or [16.0, False])
        ready, err = evaluate_direction_geometry({
            "geometry": {
                "outbound": [[True, 108.0], [16.1, 108.1]],
                "provenance": {"outbound": {"verified": True}}
            }
        }, "outbound")
        self.assertFalse(ready)
        self.assertIn("Tọa độ polyline không hợp lệ", err)

        ready, err = evaluate_direction_geometry({
            "geometry": {
                "outbound": [[16.0, 108.0], [16.1, False]],
                "provenance": {"outbound": {"verified": True}}
            }
        }, "outbound")
        self.assertFalse(ready)
        self.assertIn("Tọa độ polyline không hợp lệ", err)

    def test_negative_case_suspended_route(self):
        """Suspended routes (04, 10, 15) must fail tripPlanningReady and eligibleForPlanning."""
        suspended_ids = ["04", "10", "15"]
        for sid in suspended_ids:
            r = next((x for x in self.routes if x["id"] == sid), None)
            self.assertIsNotNone(r, f"Route {sid} must exist")
            self.assertEqual(r["status"], "suspended")
            dq = r["dataQuality"]
            self.assertFalse(dq["tripPlanningReady"])
            self.assertFalse(dq["directions"]["outbound"]["eligibleForPlanning"])
            self.assertFalse(dq["directions"]["inbound"]["eligibleForPlanning"])
            self.assertTrue(any("tạm ngừng" in reason for reason in dq["ineligibilityReasons"]))

    def test_negative_case_invalid_and_unknown_fare(self):
        """Routes with unknown fare, contradictory flat price or malformed distance_tiered tiers must fail."""
        # Routes 09 and 13 have type: unknown
        for rid in ["09", "13"]:
            r = next(x for x in self.routes if x["id"] == rid)
            self.assertEqual(r["fares"]["type"], "unknown")
            dq = r["dataQuality"]
            self.assertFalse(dq["hasFareModel"])
            self.assertFalse(dq["tripPlanningReady"])
            self.assertFalse(dq["directions"]["outbound"]["eligibleForPlanning"])
            self.assertFalse(dq["directions"]["inbound"]["eligibleForPlanning"])
            
        # Synthetic case 1: tiered fare with contradictory singleTicket flat fare
        mock_route = {
            "status": "active",
            "fares": {
                "type": "distance_tiered",
                "minPrice": 8000,
                "maxPrice": 16000,
                "singleTicket": 8000 # Forbidden flat price on tiered
            }
        }
        ready, err = evaluate_fare_model(mock_route)
        self.assertFalse(ready)
        self.assertIn("vi phạm cấm flat singleTicket", err)

        # Synthetic case 2: distance_tiered with tiers=[None] (vacuous truth prevention)
        mock_route_none_tier = {
            "status": "active",
            "fares": {
                "type": "distance_tiered",
                "tiers": [None]
            }
        }
        ready, err = evaluate_fare_model(mock_route_none_tier)
        self.assertFalse(ready)
        self.assertIn("chứa phần tử không phải object", err)

        # Synthetic case 3: distance_tiered with tiers=['bad']
        mock_route_bad_tier = {
            "status": "active",
            "fares": {
                "type": "distance_tiered",
                "tiers": ["bad"]
            }
        }
        ready, err = evaluate_fare_model(mock_route_bad_tier)
        self.assertFalse(ready)
        self.assertIn("chứa phần tử không phải object", err)

        # Synthetic case 4: distance_tiered with mixed malformed tiers [{'price': 8000}, None]
        mock_route_mixed_tier = {
            "status": "active",
            "fares": {
                "type": "distance_tiered",
                "tiers": [{"price": 8000}, None]
            }
        }
        ready, err = evaluate_fare_model(mock_route_mixed_tier)
        self.assertFalse(ready)
        self.assertIn("chứa phần tử không phải object", err)

        # Synthetic case 5: distance_tiered with invalid tier prices
        mock_route_invalid_price = {
            "status": "active",
            "fares": {
                "type": "distance_tiered",
                "tiers": [{"price": -100}]
            }
        }
        ready, err = evaluate_fare_model(mock_route_invalid_price)
        self.assertFalse(ready)
        self.assertIn("chứa giá vé không hợp lệ", err)

        # Synthetic case 6: distance_tiered with empty tiers list
        mock_route_empty_tiers = {
            "status": "active",
            "fares": {
                "type": "distance_tiered",
                "tiers": []
            }
        }
        ready, err = evaluate_fare_model(mock_route_empty_tiers)
        self.assertFalse(ready)
        self.assertIn("phải là danh sách không rỗng", err)

        # Synthetic case 7: minPrice/maxPrice valid BUT malformed tiers=[None] present -> must reject!
        mock_route_minmax_with_bad_tiers = {
            "status": "active",
            "fares": {
                "type": "distance_tiered",
                "minPrice": 8000,
                "maxPrice": 16000,
                "tiers": [None]
            }
        }
        ready, err = evaluate_fare_model(mock_route_minmax_with_bad_tiers)
        self.assertFalse(ready, "Must not allow malformed tiers even if minPrice/maxPrice is set")
        self.assertIn("chứa phần tử không phải object", err)

        # Synthetic case 8: Leading None in mixed tiers [None, {"price": 8000}]
        mock_route_leading_none = {
            "status": "active",
            "fares": {
                "type": "distance_tiered",
                "tiers": [None, {"price": 8000}]
            }
        }
        ready, err = evaluate_fare_model(mock_route_leading_none)
        self.assertFalse(ready)
        self.assertIn("chứa phần tử không phải object", err)

        # Synthetic case 9: String element in mixed tiers [{"price": 8000}, "bad"]
        mock_route_mixed_str = {
            "status": "active",
            "fares": {
                "type": "distance_tiered",
                "tiers": [{"price": 8000}, "bad"]
            }
        }
        ready, err = evaluate_fare_model(mock_route_mixed_str)
        self.assertFalse(ready)
        self.assertIn("chứa phần tử không phải object", err)

        # Synthetic case 10: Numeric element in tiers [123]
        mock_route_num_tier = {
            "status": "active",
            "fares": {
                "type": "distance_tiered",
                "tiers": [123]
            }
        }
        ready, err = evaluate_fare_model(mock_route_num_tier)
        self.assertFalse(ready)
        self.assertIn("chứa phần tử không phải object", err)

        # Synthetic case 11: Non-list tiers (e.g. string "invalid")
        mock_route_str_tiers = {
            "status": "active",
            "fares": {
                "type": "distance_tiered",
                "tiers": "invalid_tiers_string"
            }
        }
        ready, err = evaluate_fare_model(mock_route_str_tiers)
        self.assertFalse(ready)
        self.assertIn("phải là danh sách không rỗng", err)

        # Synthetic case 12: Zero, None, string, or negative prices in tier
        for bad_p in [0, -5000, "8000", None, float("nan"), float("inf")]:
            mock_bad_price = {
                "status": "active",
                "fares": {
                    "type": "distance_tiered",
                    "tiers": [{"price": bad_p}]
                }
            }
            ready, err = evaluate_fare_model(mock_bad_price)
            self.assertFalse(ready, f"Price {bad_p} must be rejected")
            self.assertIn("chứa giá vé không hợp lệ", err)

        # Synthetic case 13: Invalid distanceMaxKm in tier
        for bad_dist in [-10, 0, "10km", float("nan")]:
            mock_bad_dist = {
                "status": "active",
                "fares": {
                    "type": "distance_tiered",
                    "tiers": [{"price": 8000, "distanceMaxKm": bad_dist}]
                }
            }
            ready, err = evaluate_fare_model(mock_bad_dist)
            self.assertFalse(ready, f"distanceMaxKm {bad_dist} must be rejected")
            self.assertIn("distanceMaxKm không hợp lệ", err)

        # Synthetic case 14: Valid minPrice/maxPrice but malformed tiers=['bad'] or empty tiers=[]
        for bad_t in [["bad"], [{"price": 8000}, None], []]:
            mock_minmax_bad = {
                "status": "active",
                "fares": {
                    "type": "distance_tiered",
                    "minPrice": 8000,
                    "maxPrice": 16000,
                    "tiers": bad_t
                }
            }
            ready, err = evaluate_fare_model(mock_minmax_bad)
            self.assertFalse(ready, f"minPrice/maxPrice must not bypass malformed tiers {bad_t}")

        # Synthetic case 15: Boolean flatPrice and singleTicket (True/False)
        for bool_val in [True, False]:
            mock_flat_bool = {
                "status": "active",
                "fares": {
                    "type": "flat",
                    "flatPrice": bool_val
                }
            }
            ready, err = evaluate_fare_model(mock_flat_bool)
            self.assertFalse(ready, f"Boolean flatPrice={bool_val} must be rejected")
            self.assertIn("không hợp lệ", err)

            mock_single_bool = {
                "status": "active",
                "fares": {
                    "type": "flat",
                    "singleTicket": bool_val
                }
            }
            ready, err = evaluate_fare_model(mock_single_bool)
            self.assertFalse(ready, f"Boolean singleTicket={bool_val} must be rejected")
            self.assertIn("không hợp lệ", err)

        # Synthetic case 16: Boolean minPrice and maxPrice in distance_tiered
        for bool_val in [True, False]:
            mock_min_bool = {
                "status": "active",
                "fares": {
                    "type": "distance_tiered",
                    "minPrice": bool_val,
                    "maxPrice": 16000
                }
            }
            ready, err = evaluate_fare_model(mock_min_bool)
            self.assertFalse(ready, f"Boolean minPrice={bool_val} must be rejected")
            self.assertIn("không hợp lệ", err)

            mock_max_bool = {
                "status": "active",
                "fares": {
                    "type": "distance_tiered",
                    "minPrice": 8000,
                    "maxPrice": bool_val
                }
            }
            ready, err = evaluate_fare_model(mock_max_bool)
            self.assertFalse(ready, f"Boolean maxPrice={bool_val} must be rejected")
            self.assertIn("không hợp lệ", err)

            mock_both_bool = {
                "status": "active",
                "fares": {
                    "type": "distance_tiered",
                    "minPrice": bool_val,
                    "maxPrice": bool_val
                }
            }
            ready, err = evaluate_fare_model(mock_both_bool)
            self.assertFalse(ready, f"Boolean minPrice/maxPrice={bool_val} must be rejected")
            self.assertIn("không hợp lệ", err)

        # Synthetic case 17: Boolean tier price and distanceMaxKm
        for bool_val in [True, False]:
            mock_tier_price_bool = {
                "status": "active",
                "fares": {
                    "type": "distance_tiered",
                    "tiers": [{"price": bool_val}]
                }
            }
            ready, err = evaluate_fare_model(mock_tier_price_bool)
            self.assertFalse(ready, f"Boolean tier price={bool_val} must be rejected")
            self.assertIn("chứa giá vé không hợp lệ", err)

            mock_tier_dist_bool = {
                "status": "active",
                "fares": {
                    "type": "distance_tiered",
                    "tiers": [{"price": 8000, "distanceMaxKm": bool_val}]
                }
            }
            ready, err = evaluate_fare_model(mock_tier_dist_bool)
            self.assertFalse(ready, f"Boolean tier distanceMaxKm={bool_val} must be rejected")
            self.assertIn("distanceMaxKm không hợp lệ", err)

    def test_numeric_primitive_type_safety_boolean_rejection(self):
        """Primitive functions is_finite_number and is_valid_coordinate must reject booleans."""
        self.assertFalse(is_finite_number(True), "is_finite_number(True) must return False")
        self.assertFalse(is_finite_number(False), "is_finite_number(False) must return False")
        self.assertFalse(is_valid_coordinate(True, 108.0), "is_valid_coordinate(True, 108.0) must return False")
        self.assertFalse(is_valid_coordinate(16.0, False), "is_valid_coordinate(16.0, False) must return False")
        self.assertFalse(is_valid_coordinate(True, False), "is_valid_coordinate(True, False) must return False")
        self.assertFalse(is_valid_coordinate(False, True), "is_valid_coordinate(False, True) must return False")
        
        # Valid numbers must continue to pass
        self.assertTrue(is_finite_number(16.05))
        self.assertTrue(is_finite_number(108))
        self.assertTrue(is_valid_coordinate(16.05, 108.20))

    # -------------------------------------------------------------------------
    # 3. Direction-Level Readiness & Two-Direction Expansion (02 & TKY-CHU)
    # -------------------------------------------------------------------------
    def test_direction_level_eligibility_and_expanded_coverage_02_and_tky_chu(self):
        """Route 02 and TKY-CHU now have verified geometry in both directions and are tripPlanningReady."""
        # Route 02
        r02 = next(x for x in self.routes if x["id"] == "02")
        dq02 = r02["dataQuality"]
        self.assertTrue(dq02["hasOutboundGeometry"])
        self.assertTrue(dq02["hasInboundGeometry"])
        self.assertTrue(dq02["directions"]["outbound"]["eligibleForPlanning"])
        self.assertTrue(dq02["directions"]["inbound"]["eligibleForPlanning"])
        self.assertTrue(dq02["tripPlanningReady"])

        # Route TKY-CHU
        rtky = next(x for x in self.routes if x["id"] == "TKY-CHU")
        dqtky = rtky["dataQuality"]
        self.assertTrue(dqtky["hasOutboundGeometry"])
        self.assertTrue(dqtky["hasInboundGeometry"])
        self.assertTrue(dqtky["directions"]["outbound"]["eligibleForPlanning"])
        self.assertTrue(dqtky["directions"]["inbound"]["eligibleForPlanning"])
        self.assertTrue(dqtky["tripPlanningReady"])

    def test_direction_level_isolation_partial_route_lk02_and_21(self):
        """Routes with verified stops but unverified geometry must fail geometryReady and eligibleForPlanning."""
        r21 = next(x for x in self.routes if x["id"] == "21")
        dq21 = r21["dataQuality"]
        self.assertTrue(dq21["directions"]["outbound"]["stopsReady"])
        self.assertFalse(dq21["directions"]["outbound"]["geometryReady"])
        self.assertFalse(dq21["directions"]["outbound"]["eligibleForPlanning"])
        self.assertFalse(dq21["tripPlanningReady"])

    def test_fare_threshold_as_distance_parser_bug_regression(self):
        """Fare-tier threshold strings must never be parsed as route distance metadata."""
        def clean(text):
            return re.sub(r'\s+', ' ', text.replace('\xa0', ' ')).strip()

        dist_pattern = r'(?:^|\n)\s*(?:(?:\d+\.|\b[a-z]\))\s*)?Cự ly(?!\s+di\s+chuyển)(?:\s+tuyến|\s+toàn\s+tuyến|\s*\(.*?\))?\s*:\s*([^\n\r]+)'

        fare_chunk = """
        - Giá vé lượt áp dụng đối với hành khách (trừ học sinh, sinh viên) có cự ly di chuyển:
        + Từ 10 km trở xuống: 8.000 đồng/hành khách/lượt.
        + Trên 10km - 25km: 20.000 đồng/hành khách/lượt.
        """
        # Ensure pattern does NOT match "cự ly di chuyển"
        matches = list(re.finditer(dist_pattern, fare_chunk, re.IGNORECASE))
        self.assertEqual(len(matches), 0, "Fare-tier 'cự ly di chuyển' must not match route distance pattern")

        # Test line with fare keyword is rejected
        line_with_fare = "Cự ly: 10 km trở xuống: 8.000 đồng"
        dm = re.search(dist_pattern, line_with_fare, re.IGNORECASE)
        if dm:
            candidate = clean(dm.group(1))
            is_fare = any(kw in candidate.lower() for kw in ['đồng', 'hành khách', 'giá vé', 'vé lượt', 'trở xuống', 'trở lên'])
            self.assertTrue(is_fare, "Line containing 'đồng' or 'trở xuống' must be recognized as fare text and ignored")

        # Ensure Route 02 distanceKm remains null/unknown without independent evidence
        r02 = next(x for x in self.routes if x["id"] == "02")
        self.assertIsNone(r02["distanceKm"]["average"])
        self.assertIsNone(r02["distanceKm"]["outbound"])
        self.assertIsNone(r02["distanceKm"]["inbound"])

    def test_resolver_chua_dao_nguyen_and_locality_provenance(self):
        """Chùa Đạo Nguyên must resolve to node 11898042384 with Quang Nam locality, and 463 PBC must be isolated."""
        from scripts.build_gps_dataset import StopResolver

        resolver = StopResolver()
        stop_cdn = {"name": "140 Phan Bội Châu (Chùa Đạo Nguyên)", "street": "Phan Bội Châu – Bàn Thạch"}
        res, status, _ = resolver.resolve(stop_cdn)
        self.assertEqual(status, "verified")
        self.assertEqual(res["osm_id"], 11898042384)
        self.assertIn("Quảng Nam", res["display_name"])
        self.assertNotIn("Đà Nẵng", res["display_name"], "Tam Kỳ stop must not have hardcoded Đà Nẵng locality")

        # Isolation of 463 Phan Bội Châu from 63 Phan Bội Châu
        stop_463 = {"name": "463 Phan Bội Châu (Kho bạc cũ)", "street": "Phan Bội Châu – Bàn Thạch"}
        res_463, status_463, _ = resolver.resolve(stop_463)
        self.assertEqual(status_463, "unresolved", "463 Phan Bội Châu must not match 63 Phan Bội Châu")
        self.assertIsNone(res_463)

    # -------------------------------------------------------------------------
    # 4. Coverage Report Verification
    # -------------------------------------------------------------------------
    def test_coverage_report_consistency(self):
        """Generated coverage report must exist and match dataset summary exactly."""
        self.assertTrue(os.path.exists(COVERAGE_REPORT_PATH), "Coverage report must exist")
        with open(COVERAGE_REPORT_PATH, "r", encoding="utf-8") as f:
            rep = json.load(f)
            
        summary = rep.get("summary", {})
        self.assertEqual(summary["totalRoutes"], 23)
        self.assertEqual(summary["activeRoutes"], 20)
        self.assertEqual(summary["suspendedRoutes"], 3)
        self.assertEqual(summary["tripPlanningReadyCount"], 5)
        self.assertEqual(summary["tripPlanningReadyRoutes"], ["05", "02", "TKY-TMY", "TKY-NTH", "TKY-CHU"])
        self.assertEqual(summary["inboundOnlyReadyRoutes"], [])
        self.assertEqual(summary["neitherReadyCount"], 18)
        self.assertGreater(summary["stops"]["total"], 0)
        self.assertGreater(summary["stops"]["verified"], 0)
        self.assertGreater(summary["stops"]["verifiedPercentage"], 56.5)

    # -------------------------------------------------------------------------
    # 5. Spatial Primitives & BusService Integration (Node.js Execution)
    # -------------------------------------------------------------------------
    def test_haversine_distance_and_find_nearby_stops_nodejs(self):
        """Execute comprehensive spatial tests in Node.js runtime against js/busService.js."""
        js_test = """
        const { BusService, findNearbyStops, haversineDistance } = require('./js/busService.js');
        const fs = require('fs');
        const assert = require('assert');

        const results = {};

        // 1. Haversine distance accuracy
        // Da Nang Airport (16.0544, 108.2022) to Dragon Bridge (16.0610, 108.2212) ~2.16 km
        const dAirportDragon = haversineDistance(16.0544, 108.2022, 16.0610, 108.2212);
        assert(dAirportDragon > 2100 && dAirportDragon < 2200, `Distance out of expected range: ${dAirportDragon}`);
        results.haversineAccuracy = true;

        // Identical points -> 0 meters
        assert.strictEqual(haversineDistance(16.0544, 108.2022, 16.0544, 108.2022), 0);
        results.haversineZero = true;

        // Fail-closed invalid coordinates -> null
        assert.strictEqual(haversineDistance(null, 108.0, 16.0, 108.0), null);
        assert.strictEqual(haversineDistance(16.0, undefined, 16.0, 108.0), null);
        assert.strictEqual(haversineDistance(NaN, 108.0, 16.0, 108.0), null);
        assert.strictEqual(haversineDistance(16.0, 108.0, '16.0', 108.0), null);
        assert.strictEqual(haversineDistance(95.0, 108.0, 16.0, 108.0), null); // Lat out of bounds
        assert.strictEqual(haversineDistance(16.0, 185.0, 16.0, 108.0), null); // Lon out of bounds
        results.haversineFailClosed = true;

        // 2. findNearbyStops filtering & fail-closed
        const mockStops = [
            { id: 's1', name: 'Trạm A (Verified gần)', status: 'verified', lat: 16.0550, lng: 108.2025 }, // ~73m
            { id: 's2', name: 'Trạm B (Unresolved gần)', status: 'unresolved', lat: 16.0548, lng: 108.2024 }, // ~50m, BUT unresolved!
            { id: 's3', name: 'Trạm C (Verified xa 1.2km)', status: 'verified', lat: 16.0650, lng: 108.2025 }, // ~1180m
            { id: 's4', name: 'Trạm D (Verified vừa 400m)', status: 'verified', lat: 16.0580, lng: 108.2025 }, // ~400m
            { id: 's5', name: 'Trạm E (Verified null coords)', status: 'verified', lat: null, lng: 108.2025 }
        ];

        // Query with default radius 1000m from (16.0544, 108.2022)
        const nearby1 = findNearbyStops(mockStops, 16.0544, 108.2022, { maxDistanceMeters: 1000 });
        
        // S2 (unresolved) must NEVER be included
        assert(!nearby1.some(s => s.id === 's2'), 'Unresolved stop must not be returned');
        // S5 (null coords) must NEVER be included
        assert(!nearby1.some(s => s.id === 's5'), 'Null coord stop must not be returned');
        // S3 (1.2km) is beyond 1000m radius -> excluded
        assert(!nearby1.some(s => s.id === 's3'), 'Beyond radius stop must not be returned');
        // S1 and S4 must be returned
        assert.strictEqual(nearby1.length, 2);
        assert.strictEqual(nearby1[0].id, 's1'); // Closer
        assert.strictEqual(nearby1[1].id, 's4'); // Further
        assert(nearby1[0].distanceMeters <= nearby1[1].distanceMeters, 'Results must be sorted ascending by distance');
        results.nearbyStopsFilterAndSort = true;

        // Test limit option
        const nearbyLimit = findNearbyStops(mockStops, 16.0544, 108.2022, { maxDistanceMeters: 2000, limit: 1 });
        assert.strictEqual(nearbyLimit.length, 1);
        assert.strictEqual(nearbyLimit[0].id, 's1');
        results.nearbyLimit = true;

        // 3. BusService class wrapper integration
        const bs = new BusService();
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        bs.routes = routes;
        bs.stops = stops;

        // Planning readiness methods
        const r05 = bs.getRouteById('05');
        const r02 = bs.getRouteById('02');
        const r21 = bs.getRouteById('21');
        assert.strictEqual(bs.isRoutePlanningReady(r05), true);
        assert.strictEqual(bs.isRoutePlanningReady(r02), true);
        assert.strictEqual(bs.isRoutePlanningReady(r21), false);

        const rTkyChu = bs.getRouteById('TKY-CHU');
        assert.strictEqual(bs.isDirectionPlanningReady(rTkyChu, 'outbound'), true);
        assert.strictEqual(bs.isDirectionPlanningReady(rTkyChu, 'inbound'), true);
        assert.strictEqual(bs.isRoutePlanningReady(rTkyChu), true);

        const readyRoutes = bs.getPlanningReadyRoutes();
        assert.deepStrictEqual(readyRoutes.map(r => r.id), ['05', '02', 'TKY-TMY', 'TKY-NTH', 'TKY-CHU']);
        results.busServiceReadinessMethods = true;

        // bs.findNearbyStops on real dataset
        // Central Da Nang: Han Market (16.0682, 108.2244)
        const realNearby = bs.findNearbyStops(16.0682, 108.2244, { maxDistanceMeters: 800, limit: 5 });
        assert(realNearby.length > 0, 'Must find nearby stops in central Da Nang');
        assert(realNearby.length <= 5, 'Must respect limit');
        assert(realNearby.every(s => s.status === 'verified'), 'All real stops must be verified');
        assert(realNearby.every(s => s.distanceMeters <= 800), 'All real stops must be within 800m');
        for (let i = 0; i < realNearby.length - 1; i++) {
            assert(realNearby[i].distanceMeters <= realNearby[i + 1].distanceMeters, 'Stops must be strictly sorted by distance');
        }
        results.realDatasetNearbyQuery = true;

        console.log(JSON.stringify(results));
        """
        proc = subprocess.run(["node", "-e", js_test], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            self.fail(f"Node.js spatial test failed with error:\n{proc.stderr}")
            
        res = json.loads(proc.stdout.strip())
        for k, v in res.items():
            self.assertTrue(v, f"Check failed for {k}")

if __name__ == "__main__":
    unittest.main()
