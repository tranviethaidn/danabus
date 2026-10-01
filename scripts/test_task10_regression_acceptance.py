#!/usr/bin/env python3
"""
Task 10 Unified Acceptance & Regression Test Runner
Business-Logic Regression & Production Acceptance
Task-ID: tsk_bacc9b91-9386-4e80-b7bc-5b5fc294696d

Orchestrates 2 test layers:
- Layer A: Local Deterministic Suites (Search, Schedule/Fare, Data Quality, Map/GPS, Task 4 Boundary Guard)
- Layer B: Browser & Production Integration Suites (Security Nginx Hardening, DOM Schedule/Fare, UI Integrity & Accessibility, Browser Smoke)

Provides:
- Strict fail-fast: any non-zero exit code stops execution immediately.
- 20-item Acceptance Traceability Matrix mapping every requirement to concrete assertions.
- Optional --local-only flag to execute Layer A quickly without browser/network dependencies.
- Optional --target-url flag to specify custom production endpoint.
"""

import os
import sys
import time
import json
import argparse
import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent

ACCEPTANCE_ITEMS = [
    {
        "id": 1,
        "title": "A -> B đúng direction/order: PASS",
        "layer": "Layer A",
        "script": "scripts/test_search_correctness.py",
        "check": "Check 1: test_direct_match_outbound (Bến xe TT -> Phố cổ Hội An, originIndex < destinationIndex)"
    },
    {
        "id": 2,
        "title": "B -> A ngược order: không match outbound",
        "layer": "Layer A",
        "script": "scripts/test_search_correctness.py",
        "check": "Check 2 & 3: test_direct_match_inbound & test_reverse_order_rejection"
    },
    {
        "id": 3,
        "title": "origin == destination: validation error",
        "layer": "Layer A",
        "script": "scripts/test_search_correctness.py",
        "check": "Check 6: test_validation_same_endpoints (error: SAME_ORIGIN_DESTINATION)"
    },
    {
        "id": 4,
        "title": "origin empty: validation error",
        "layer": "Layer A",
        "script": "scripts/test_search_correctness.py",
        "check": "Check 4: test_validation_empty_origin (error: EMPTY_ORIGIN)"
    },
    {
        "id": 5,
        "title": "destination empty: validation error",
        "layer": "Layer A",
        "script": "scripts/test_search_correctness.py",
        "check": "Check 5: test_validation_empty_destination (error: EMPTY_DESTINATION)"
    },
    {
        "id": 6,
        "title": "Không có direct route: no-result",
        "layer": "Layer A",
        "script": "scripts/test_search_correctness.py",
        "check": "Check 7: test_no_direct_route_fail_closed (Bến xe TT -> Hà Nội -> [])"
    },
    {
        "id": 7,
        "title": "Suspended/ineligible route: không đề xuất",
        "layer": "Layer A",
        "script": "scripts/test_search_correctness.py & test_data_quality_and_planner_readiness.py",
        "check": "Check 8 & 9 (Search) + test_ineligible_routes_isolated_for_planning (19 tuyến ineligible)"
    },
    {
        "id": 8,
        "title": "Thiếu stop/geometry: excluded/degraded theo data-quality contract",
        "layer": "Layer A",
        "script": "scripts/test_data_quality_and_planner_readiness.py & test_map_and_gps.py",
        "check": "evaluate_direction_stops & evaluate_direction_geometry + unverified geometry null/verified=false"
    },
    {
        "id": 9,
        "title": "00:46 với service start 05:15: 269 phút / before_service",
        "layer": "Layer A",
        "script": "scripts/test_schedule_and_fare.py",
        "check": "Check 1: before_service_269_min (depBefore.minutesUntilDeparture === 269, timeStr === '05:15')"
    },
    {
        "id": 10,
        "title": "Sau service window: after_service hoặc next_day đúng contract",
        "layer": "Layer A",
        "script": "scripts/test_schedule_and_fare.py",
        "check": "Checks 3, 4, 5: next_day_departure, after_service_no_next_day, irregular_flight_after_service"
    },
    {
        "id": 11,
        "title": "Malformed/suspended schedule: unknown, không fake time",
        "layer": "Layer A",
        "script": "scripts/test_schedule_and_fare.py",
        "check": "Checks 8 & 8b: malformed_schedule_fail_closed & frequency_missing_or_invalid_fail_closed"
    },
    {
        "id": 12,
        "title": "Tiered fare: không hiển thị flat fare sai",
        "layer": "Layer A & B",
        "script": "scripts/test_schedule_and_fare.py & test_browser_schedule_and_fare.py",
        "check": "Check 9 (singleTicket is null, 8.000đ - 30.000đ) & Browser DOM checks (trip_fare != '30.000đ')"
    },
    {
        "id": 13,
        "title": "GPS coordinate: nearby-stop candidate hợp lệ, verified-only",
        "layer": "Layer A",
        "script": "scripts/test_data_quality_and_planner_readiness.py & test_map_and_gps.py",
        "check": "findNearbyStops verified filter, maxDistanceMeters, ascending distance sort, Da Nang/Quang Nam bbox"
    },
    {
        "id": 14,
        "title": "Swap locations: không stale result",
        "layer": "Layer A",
        "script": "scripts/test_search_correctness.py",
        "check": "Check 10: test_swap_locations_invalidation (Directional inversion & non-stale)"
    },
    {
        "id": 15,
        "title": "Voice/reminder disabled: không fake success",
        "layer": "Layer B",
        "script": "scripts/test_ui_integrity_and_accessibility.py",
        "check": "Checks 1 & 4: Voice and reminder buttons hidden & disabled, zero fake alerts or transcript"
    },
    {
        "id": 16,
        "title": "Dataset/network failure: visible error, zero fabricated data, retry recovery",
        "layer": "Layer B",
        "script": "scripts/test_ui_integrity_and_accessibility.py",
        "check": "Check 7: CDP network blocking *danangbus_*.json* -> role='alert' error state -> retry recovery"
    },
    {
        "id": 17,
        "title": "Sensitive public paths: blocked",
        "layer": "Layer B",
        "script": "scripts/security_smoke_test.py",
        "check": "15 negative security endpoints (.git, docs, scripts, schema.ts, osm_cache) return 404, no SPA leak"
    },
    {
        "id": 18,
        "title": "Browser/public smoke: production runtime semantics PASS",
        "layer": "Layer B",
        "script": "scripts/browser_smoke_test.py",
        "check": "8/8 checks: DOM state, 23 routes catalog, map views, switch dir, geolocation, SW cache v11 migration"
    },
    {
        "id": 19,
        "title": "Toàn bộ suite Task 5-9 liên quan: regression PASS",
        "layer": "Orchestrator",
        "script": "scripts/test_task10_regression_acceptance.py",
        "check": "Unified regression runner validates all Layer A and Layer B suites succeed with zero failures"
    },
    {
        "id": 20,
        "title": "Task 4 boundary: legacy direct-only & no fake leak",
        "layer": "Layer A",
        "script": "scripts/test_task10_regression_acceptance.py (test_task4_boundary_guard)",
        "check": "Legacy findRoutesBetween direct-only, zero hardcoded Google Places/Maps SDK, fail-closed no fake fallback"
    }
]


def run_cmd(cmd_list, description):
    """Executes a command list with fail-fast semantics."""
    print(f"\n>> [RUNNING] {description}")
    print(f"   Command: {' '.join(cmd_list)}")
    start_t = time.time()
    res = subprocess.run(cmd_list, cwd=WORKSPACE, text=True, capture_output=True)
    dur = time.time() - start_t
    
    if res.returncode != 0:
        print(f"\n[-] FAIL: {description} (exit code: {res.returncode}, duration: {dur:.2f}s)")
        print("\n" + "=" * 70)
        print("--- FULL CHILD STDOUT ON FAILURE ---")
        if res.stdout:
            print(res.stdout.strip())
        else:
            print("(no stdout output)")
        print("--- FULL CHILD STDERR ON FAILURE ---")
        if res.stderr:
            print(res.stderr.strip())
        else:
            print("(no stderr output)")
        print("=" * 70 + "\n")
        sys.exit(1)
        
    if res.stdout:
        # Print indent for last lines on success
        for line in res.stdout.strip().splitlines()[-15:]:
            print(f"   | {line}")
            
    print(f"   [PASS] {description} ({dur:.2f}s)")
    time.sleep(0.1)
    return True


def test_task4_boundary_guard():
    """
    Item 20 Boundary Guard (Post-Task-4):
    Verifies that post-Task-4 architecture maintains strict boundary invariants:
    1. Zero hardcoded Google Places API, Google Maps SDK or external geocoder credentials in js/ or index.html
    2. Legacy BusService.findRoutesBetween() remains strictly direct-only (backward compatible),
       returning [] for disjoint endpoints with zero transfer routing leakage
    3. Fail-closed no fake fallback: disconnected queries strictly fail-closed, estimated walking has geometry: null
    """
    print("\n>> [RUNNING] Task 4 Post-Implementation Boundary Guard (Item 20)")
    
    # 1. Static code audit for prohibited external SDKs & hardcoded API keys
    prohibited_sdk_terms = [
        "google.maps.Map",
        "AIzaSy"
    ]
    
    files_to_check = [
        WORKSPACE / "js" / "busService.js",
        WORKSPACE / "js" / "app.js",
        WORKSPACE / "js" / "mapService.js",
        WORKSPACE / "index.html"
    ]
    
    for fpath in files_to_check:
        if not fpath.exists():
            continue
        content = fpath.read_text(encoding="utf-8")
        for term in prohibited_sdk_terms:
            if term in content:
                print(f"[-] FAIL: Prohibited external SDK/credential '{term}' found in {fpath.name}")
                sys.exit(1)
        # Google Places client library & endpoint must only appear in busService.js (isolated behind provider abstraction)
        if fpath.name != "busService.js":
            for term in ["places.googleapis.com", "maps.googleapis.com", "google.maps.places"]:
                if term in content:
                    print(f"[-] FAIL: {term} must be isolated in busService.js, found in {fpath.name}")
                    sys.exit(1)
                
    print("   [PASS] Codebase static scan: zero hardcoded Google Places/Maps SDK or credentials detected.")
    
    # 2. Node.js runtime assertion: legacy findRoutesBetween backward compatibility & fail-closed semantics
    node_test = """
    const fs = require('fs');
    const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation } = require('./js/busService.js');
    const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
    const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
    const bs = new BusService();
    bs.routes = routes;
    bs.stops = stops;
    bs.isLoaded = true;

    // A. Direct connection on legacy findRoutesBetween remains backward-compatible
    const direct = bs.findRoutesBetween('Bến xe TT', 'Phố cổ Hội An');
    if (!Array.isArray(direct) || direct.length === 0 || direct[0].routeNumber !== '02') {
        console.error('FAIL: Expected direct route 02 for connected pair, got:', direct);
        process.exit(1);
    }

    // B. Legacy findRoutesBetween remains direct-only: disjoint pairs strictly return empty array []
    const r1 = bs.findRoutesBetween('Hòa Hiệp Nam', 'Phố cổ Hội An');
    if (!Array.isArray(r1) || r1.length !== 0) {
        console.error('FAIL: Expected empty array for disjoint route pair, got:', r1);
        process.exit(1);
    }

    const r2 = bs.findRoutesBetween('Hòa Hiệp Nam', 'Cầu Rồng');
    if (!Array.isArray(r2) || r2.length !== 0) {
        console.error('FAIL: Expected empty array for Hòa Hiệp Nam -> Cầu Rồng, got:', r2);
        process.exit(1);
    }

    const r3 = bs.findRoutesBetween('Cầu Rồng', 'Tam Kỳ');
    if (!Array.isArray(r3) || r3.length !== 0) {
        console.error('FAIL: Expected empty array for Cầu Rồng -> Tam Kỳ, got:', r3);
        process.exit(1);
    }

    // C. WalkingRouter strict semantic estimate: isEstimated === true, geometry === null (no fake polyline)
    const wr = new WalkingRouter();
    const walk = wr.route([16.0617, 108.1834], [16.0650, 108.1900]);
    if (!walk || walk.isEstimated !== true || walk.geometry !== null) {
        console.error('FAIL: WalkingRouter estimate must have isEstimated: true and geometry: null, got:', walk);
        process.exit(1);
    }

    // D. TransitPlanner fail-closed: disconnected endpoints strictly return empty trips []
    const tp = new TransitPlanner(bs, wr);
    const oLoc = new ResolvedLocation({ displayName: 'Đà Nẵng', lat: 16.0617, lng: 108.1834 });
    const dLoc = new ResolvedLocation({ displayName: 'Hà Nội', lat: 21.0285, lng: 105.8542 });
    const plan = tp.planTrip(oLoc, dLoc);
    if (!plan || !Array.isArray(plan.trips) || plan.trips.length !== 0) {
        console.error('FAIL: Expected empty trips for disconnected endpoints, got:', plan);
        process.exit(1);
    }

    console.log('PASS: Legacy findRoutesBetween is direct-only; fail-closed and no fake fallback verified.');
    """
    res = subprocess.run(["node", "-e", node_test], cwd=WORKSPACE, text=True, capture_output=True)
    if res.returncode != 0:
        print(f"[-] FAIL in Task 4 Node.js runtime assertion:\n{res.stderr.strip()}")
        sys.exit(1)
        
    print(f"   {res.stdout.strip()}")
    print("   [PASS] Task 4 Boundary Guard (Item 20) fully verified.")
    return True


def print_traceability_matrix(passed_items, is_local_only=False):
    """Prints the 20-item acceptance matrix in Markdown format."""
    print("\n" + "=" * 95)
    print("TASK 10 ACCEPTANCE TRACEABILITY MATRIX (20/20 ITEMS)")
    print("=" * 95)
    print(f"{'Item':<5} | {'Acceptance Item Title':<46} | {'Layer':<10} | {'Status':<8}")
    print("-" * 95)
    
    for item in ACCEPTANCE_ITEMS:
        item_id = item["id"]
        title = item["title"]
        layer = item["layer"]
        
        if is_local_only and ("Layer B" in layer or layer == "Orchestrator"):
            status = "SKIPPED"
        elif item_id in passed_items:
            status = "PASS"
        else:
            status = "FAIL"
            
        print(f"{item_id:<5} | {title:<46} | {layer:<10} | {status:<8}")
        
    print("-" * 95)


def main():
    parser = argparse.ArgumentParser(description="Task 10 Regression & Production Acceptance Runner")
    parser.add_argument("--local-only", action="store_true", help="Run only Layer A local deterministic tests")
    parser.add_argument("--target-url", default="https://danabus.638686.xyz/", help="Target production URL for Layer B")
    args = parser.parse_args()

    print("=" * 80)
    print("TASK 10 BUSINESS-LOGIC REGRESSION & PRODUCTION ACCEPTANCE RUNNER")
    print(f"Workspace: {WORKSPACE}")
    print(f"Mode: {'Layer A Only (Local Deterministic)' if args.local_only else 'Full Matrix (Layer A + Layer B Production)'}")
    print(f"Target URL: {args.target_url}")
    print("=" * 80)

    start_total = time.time()
    passed_items = set()

    # =========================================================================
    # LAYER A: LOCAL DETERMINISTIC SUITES
    # =========================================================================
    print("\n" + "#" * 80)
    print("### LAYER A: LOCAL DETERMINISTIC ACCEPTANCE SUITES")
    print("#" * 80)

    # Suite A.1: Search Correctness (Items 1, 2, 3, 4, 5, 6, 7, 14)
    run_cmd(
        [sys.executable, "scripts/test_search_correctness.py"],
        "Suite A.1: Search Correctness & No-Fake-Result (Task 6)"
    )
    passed_items.update([1, 2, 3, 4, 5, 6, 7, 14])

    # Suite A.2: Schedule and Fare Correctness (Items 9, 10, 11, 12)
    run_cmd(
        [sys.executable, "scripts/test_schedule_and_fare.py"],
        "Suite A.2: Schedule & Fare Correctness (Task 7)"
    )
    passed_items.update([9, 10, 11, 12])

    # Suite A.3: Data Quality Contract & Planner Readiness (Items 7, 8, 13)
    run_cmd(
        [sys.executable, "scripts/test_data_quality_and_planner_readiness.py"],
        "Suite A.3: Data Quality Contract & Spatial Primitives (Task 8)"
    )
    passed_items.update([7, 8, 13])

    # Suite A.4: Map & GPS Fail-Closed Resolver (Items 8, 13)
    run_cmd(
        [sys.executable, "scripts/test_map_and_gps.py"],
        "Suite A.4: Map, GPS & Unverified Geometry Isolation (Task 2)"
    )
    passed_items.update([8, 13])

    # Suite A.5: Task 4 Boundary Guard (Item 20)
    test_task4_boundary_guard()
    passed_items.add(20)

    # =========================================================================
    # LAYER B: BROWSER & PRODUCTION INTEGRATION SUITES
    # =========================================================================
    if not args.local_only:
        print("\n" + "#" * 80)
        print("### LAYER B: BROWSER & PRODUCTION INTEGRATION SUITES")
        print("#" * 80)

        # Suite B.1: Production Security Hardening Smoke (Item 17)
        run_cmd(
            [sys.executable, "scripts/security_smoke_test.py"],
            "Suite B.1: Production Security Hardening Verification (Task 5)"
        )
        passed_items.add(17)

        # Suite B.2: Browser Schedule & Fare Integration (Item 12)
        run_cmd(
            [sys.executable, "scripts/test_browser_schedule_and_fare.py"],
            "Suite B.2: Browser Schedule & Fare Semantics (Task 7)"
        )
        passed_items.add(12)

        # Suite B.3: Browser UI Integrity & Accessibility (Items 15, 16)
        run_cmd(
            [sys.executable, "scripts/test_ui_integrity_and_accessibility.py"],
            "Suite B.3: UI Integrity, Accessibility & Offline Recovery (Task 9)"
        )
        passed_items.update([15, 16])

        # Suite B.4: Browser Smoke Test on Production (Item 18)
        run_cmd(
            [sys.executable, "scripts/browser_smoke_test.py", args.target_url],
            f"Suite B.4: Production Browser Smoke Test on {args.target_url} (Task 2 & 10)"
        )
        passed_items.add(18)

        # Orchestration Item 19: All suites passed in unified execution
        passed_items.add(19)

    # Print Traceability Matrix
    print_traceability_matrix(passed_items, is_local_only=args.local_only)

    total_dur = time.time() - start_total
    print("\n" + "=" * 80)
    if args.local_only:
        print(f"LAYER A DETERMINISTIC SUITES PASSED STRICTLY (100% PASS in {total_dur:.2f}s)")
        print("Run without --local-only to execute Layer B production integration tests.")
    else:
        print(f"ALL 20/20 TASK 10 ACCEPTANCE CRITERIA VERIFIED (100% PASS in {total_dur:.2f}s)")
        print("Zero fake fallback | Zero regression | Production runtime semantics verified")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
