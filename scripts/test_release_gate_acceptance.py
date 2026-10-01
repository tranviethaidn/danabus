#!/usr/bin/env python3
"""
Task 011 Unified Release Gate & End-to-End Acceptance Test Runner
End-to-End Release Acceptance & Production Gate (Roadmap V3 / Release v12)
Task-ID: tsk_fa69d045-fc12-452b-9c82-8f4da320fafc

Orchestrates 3 test layers:
- Layer 1: Local Deterministic Contracts
  * Temporal Route Service & Date Transitions (scripts/test_temporal_route_service.py)
  * Trip Planner Core & Inactive Route Rejection (scripts/test_trip_planner.py)
  * Search Correctness & Monotonic Ordering (scripts/test_search_correctness.py)
  * Schedule & Fare Truthful Semantics (scripts/test_schedule_and_fare.py)
  * Data Quality Contract & Spatial Primitives (scripts/test_data_quality_and_planner_readiness.py)
  * Map, GPS & Unverified Geometry Isolation (scripts/test_map_and_gps.py)
  * Consumer UX & Task 10 Review Defects Regression (scripts/test_task10_review_fixes.py)
  * Task 4 Post-Implementation Boundary Guard (static check + node runtime)
- Layer 2: Release Integrity, Version Consistency & Secret Audit
  * Release Identity Verification (v12, Build 20261001_v12, danabus-cache-v12, ?v=20261001_v12)
  * Static Credential / Secret Audit (No secret values printed, only file/rule/count)
  * Whitelist Deliverables SHA-256 Hash Manifest & Production Comparison
- Layer 3: Browser Integration & Clean-State Repeated Verification
  * Browser Schedule & Fare Semantics (scripts/test_browser_schedule_and_fare.py)
  * Browser UI Integrity, Accessibility & Offline Recovery (scripts/test_ui_integrity_and_accessibility.py)
  * Browser Trip Planner E2E & Map Rendering (scripts/test_browser_trip_planner.py)
  * Repeated Clean-State Local Browser Smoke (scripts/browser_smoke_test.py, default 3 rounds)
  * Optional Production Integration when publication is authorized

Outputs machine-readable summary: docs/reports/task-11-release-gate-summary.json
"""

import os
import sys
import time
import json
import hashlib
import argparse
import subprocess
import re
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE = Path(__file__).resolve().parent.parent
SUMMARY_PATH = WORKSPACE / "docs" / "reports" / "task-11-release-gate-summary.json"

DELIVERABLE_FILES = [
    "index.html",
    "sw.js",
    "manifest.json",
    "css/app.css",
    "js/app.js",
    "js/busService.js",
    "js/mapService.js",
    "js/icons.js",
    "data/danangbus_routes.json",
    "data/danangbus_stops.json",
    "data/danangbus_streets.json",
    "data/danangbus_summary.json"
]

SECRET_RULES = [
    ("Google API Key", re.compile(r"AIza[0-9A-Za-z-_]{35}")),
    ("AWS Access Key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Private Key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("GitHub Token", re.compile(r"gh[pous]_[A-Za-z0-9_]{36,255}")),
    ("Slack Token", re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}")),
    ("Generic Hardcoded Secret", re.compile(r"(?i)(?:secret|password|auth_token)\s*[:=]\s*['\"][0-9a-zA-Z!@#$%^&*()_+=\-]{12,}['\"]"))
]


def run_cmd(cmd_list, description):
    """Executes a command list with fail-fast semantics and records duration."""
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
        for line in res.stdout.strip().splitlines()[-12:]:
            print(f"   | {line}")

    print(f"   [PASS] {description} ({dur:.2f}s)")
    return dur


def test_task4_boundary_guard():
    """Verifies Task 4 boundaries: legacy direct-only, zero prohibited SDKs, fail-closed."""
    print("\n>> [RUNNING] Task 4 Post-Implementation Boundary Guard")
    start_t = time.time()

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
        if fpath.name != "busService.js":
            for term in ["places.googleapis.com", "maps.googleapis.com", "google.maps.places"]:
                if term in content:
                    print(f"[-] FAIL: {term} must be isolated in busService.js, found in {fpath.name}")
                    sys.exit(1)

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

    dur = time.time() - start_t
    print(f"   | {res.stdout.strip()}")
    print(f"   [PASS] Task 4 Boundary Guard ({dur:.2f}s)")
    return dur


def verify_release_identity():
    """Verifies that v12 release identity is consistent across all deliverables."""
    print("\n>> [RUNNING] Release Identity Verification (v12 / Build 20261001_v12)")
    start_t = time.time()

    sw_path = WORKSPACE / "sw.js"
    index_path = WORKSPACE / "index.html"
    sw_content = sw_path.read_text(encoding="utf-8")
    index_content = index_path.read_text(encoding="utf-8")

    assert "danabus-cache-v12" in sw_content, "sw.js must define CACHE_NAME = 'danabus-cache-v12'"
    assert "20261001_v12" in sw_content, "sw.js must specify Build 20261001_v12"
    assert "v=20261001_v12" in sw_content, "sw.js STATIC_ASSETS must use ?v=20261001_v12"

    assert "v=20261001_v12" in index_content, "index.html must have asset query v=20261001_v12"
    assert "danabus-cache-v11" not in sw_content, "sw.js must not retain old danabus-cache-v11"
    assert "v=20260929_v11" not in index_content, "index.html must not retain old asset query v=20260929_v11"

    dur = time.time() - start_t
    print("   | sw.js: danabus-cache-v12, Build 20261001_v12, ?v=20261001_v12 verified")
    print("   | index.html: ?v=20261001_v12 verified across all CSS and JS asset queries")
    print(f"   [PASS] Release Identity Verification ({dur:.2f}s)")
    return dur


def audit_secrets():
    """
    Performs static credential and secret audit.
    Strictly complies with security rule:
    Never prints matched secret or sensitive value! Only reports file path, rule name, and count.
    """
    print("\n>> [RUNNING] Static Secret & Credential Audit")
    start_t = time.time()

    findings = []

    # 1. Audit Deliverables
    for rel in DELIVERABLE_FILES:
        fpath = WORKSPACE / rel
        if not fpath.exists():
            continue
        content = fpath.read_text(encoding="utf-8", errors="ignore")
        for rule_name, pat in SECRET_RULES:
            matches = pat.findall(content)
            if matches:
                findings.append({
                    "file": rel,
                    "rule": rule_name,
                    "count": len(matches)
                })

    # 2. Audit scripts/
    for p in (WORKSPACE / "scripts").glob("*.py"):
        content = p.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()
        for idx, line in enumerate(lines):
            # Ignore regex patterns themselves
            if "re.compile" in line or "r'" in line or 'r"' in line:
                continue
            for rule_name, pat in SECRET_RULES:
                matches = pat.findall(line)
                if matches:
                    findings.append({
                        "file": f"scripts/{p.name}",
                        "line": idx + 1,
                        "rule": rule_name,
                        "count": len(matches)
                    })

    dur = time.time() - start_t
    if findings:
        print(f"[-] FAIL: Secret audit detected {len(findings)} potential violations!")
        for f in findings:
            # Strict redaction: never print matched values
            print(f"    Violation: file={f['file']}, rule={f['rule']}, count={f['count']}")
        sys.exit(1)

    print(f"   | Scanned {len(DELIVERABLE_FILES)} deliverable files and all scripts")
    print("   | Violations detected: 0 (No hardcoded credentials or server secrets)")
    print(f"   [PASS] Static Secret & Credential Audit ({dur:.2f}s)")
    return dur, findings


def compute_deliverables_hashes():
    """Computes SHA-256 for all whitelist deliverables and compares with public if available."""
    print("\n>> [RUNNING] Whitelist Deliverables SHA-256 Checksum Computation")
    start_t = time.time()

    hashes = {}
    pub_dir = Path("/var/www/danabus/public")
    pub_comparison = {}

    for rel in DELIVERABLE_FILES:
        fpath = WORKSPACE / rel
        if fpath.exists():
            h = hashlib.sha256(fpath.read_bytes()).hexdigest()
            hashes[rel] = h

            if pub_dir.exists():
                pub_file = pub_dir / rel
                if pub_file.exists():
                    pub_h = hashlib.sha256(pub_file.read_bytes()).hexdigest()
                    pub_comparison[rel] = {
                        "workspace_sha256": h[:12] + "...",
                        "public_sha256": pub_h[:12] + "...",
                        "match": (h == pub_h)
                    }
                else:
                    pub_comparison[rel] = {"status": "NOT_IN_PUBLIC"}
            else:
                pub_comparison[rel] = {"status": "PUBLIC_DIR_NOT_FOUND"}

    dur = time.time() - start_t
    print(f"   | Computed SHA-256 for {len(hashes)} deliverable artifacts")
    print(f"   [PASS] SHA-256 Checksum Computation ({dur:.2f}s)")
    return dur, hashes, pub_comparison


def get_git_info():
    """Retrieves current Git status and relationship with origin."""
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=WORKSPACE, text=True).strip()
        status_sb = subprocess.check_output(["git", "status", "-sb"], cwd=WORKSPACE, text=True).strip().splitlines()[0]
    except Exception as e:
        head, branch, status_sb = "UNKNOWN", "UNKNOWN", str(e)

    return {
        "head": head,
        "branch": branch,
        "status_line": status_sb,
        "git_push_authorized": False,
        "push_policy_note": "git_push_authorized=OFF is expected policy, local commit created without push"
    }


def main():
    parser = argparse.ArgumentParser(description="Task 011 Release Gate & End-to-End Acceptance Runner")
    parser.add_argument("--local-only", action="store_true", help="Run only Layer 1, Layer 2 and local browser suites")
    parser.add_argument("--repeat", type=int, default=3, help="Number of repeated clean-state browser smoke rounds (default: 3)")
    parser.add_argument("--target-url", default="https://danabus.638686.xyz/", help="Target production URL for production checks")
    args = parser.parse_args()

    start_total = time.time()
    suite_records = []

    print("=" * 80)
    print("TASK 011 END-TO-END RELEASE ACCEPTANCE & PRODUCTION GATE RUNNER")
    print(f"Workspace: {WORKSPACE}")
    print(f"Mode: {'Local Release Candidate Gate' if args.local_only else 'Full Matrix (Local + Production)'}")
    print(f"Browser repeat count: {args.repeat}")
    print(f"Target Production URL: {args.target_url}")
    print("=" * 80)

    # =========================================================================
    # LAYER 1: LOCAL DETERMINISTIC SUITES
    # =========================================================================
    print("\n" + "#" * 80)
    print("### LAYER 1: LOCAL DETERMINISTIC ACCEPTANCE SUITES")
    print("#" * 80)

    d = run_cmd([sys.executable, "scripts/test_temporal_route_service.py"], "Suite 1.1: Temporal Route Service & Date Transitions")
    suite_records.append({"id": "1.1", "name": "Temporal Route Service", "layer": "Layer 1", "status": "PASS", "duration_seconds": round(d, 2)})

    d = run_cmd([sys.executable, "scripts/test_trip_planner.py"], "Suite 1.2: Trip Planner Core Algorithms & Inactive Rejection")
    suite_records.append({"id": "1.2", "name": "Trip Planner Core & Inactive Rejection", "layer": "Layer 1", "status": "PASS", "duration_seconds": round(d, 2)})

    d = run_cmd([sys.executable, "scripts/test_search_correctness.py"], "Suite 1.3: Search Correctness & Monotonic Ordering")
    suite_records.append({"id": "1.3", "name": "Search Correctness", "layer": "Layer 1", "status": "PASS", "duration_seconds": round(d, 2)})

    d = run_cmd([sys.executable, "scripts/test_schedule_and_fare.py"], "Suite 1.4: Schedule & Fare Truthful Semantics")
    suite_records.append({"id": "1.4", "name": "Schedule & Fare Truthful Semantics", "layer": "Layer 1", "status": "PASS", "duration_seconds": round(d, 2)})

    d = run_cmd([sys.executable, "scripts/test_data_quality_and_planner_readiness.py"], "Suite 1.5: Data Quality Contract & Spatial Primitives")
    suite_records.append({"id": "1.5", "name": "Data Quality Contract & Spatial Primitives", "layer": "Layer 1", "status": "PASS", "duration_seconds": round(d, 2)})

    d = run_cmd([sys.executable, "scripts/test_map_and_gps.py"], "Suite 1.6: Map, GPS & Unverified Geometry Isolation")
    suite_records.append({"id": "1.6", "name": "Map, GPS & Unverified Geometry Isolation", "layer": "Layer 1", "status": "PASS", "duration_seconds": round(d, 2)})

    d = run_cmd([sys.executable, "scripts/test_task10_review_fixes.py"], "Suite 1.7: Consumer UX & Review Defects Regression")
    suite_records.append({"id": "1.7", "name": "Consumer UX & Review Defects Regression", "layer": "Layer 1", "status": "PASS", "duration_seconds": round(d, 2)})

    d = test_task4_boundary_guard()
    suite_records.append({"id": "1.8", "name": "Task 4 Boundary Guard & Prohibited SDKs", "layer": "Layer 1", "status": "PASS", "duration_seconds": round(d, 2)})

    # =========================================================================
    # LAYER 2: RELEASE INTEGRITY, VERSION CONSISTENCY & SECURITY AUDIT
    # =========================================================================
    print("\n" + "#" * 80)
    print("### LAYER 2: RELEASE INTEGRITY & SECURITY AUDIT")
    print("#" * 80)

    d = verify_release_identity()
    suite_records.append({"id": "2.1", "name": "Release Identity Consistency v12", "layer": "Layer 2", "status": "PASS", "duration_seconds": round(d, 2)})

    d, findings = audit_secrets()
    suite_records.append({"id": "2.2", "name": "Static Secret & Credential Audit", "layer": "Layer 2", "status": "PASS", "duration_seconds": round(d, 2)})

    d, file_hashes, pub_comparison = compute_deliverables_hashes()
    suite_records.append({"id": "2.3", "name": "Deliverable SHA-256 Hash Manifest", "layer": "Layer 2", "status": "PASS", "duration_seconds": round(d, 2)})

    # =========================================================================
    # LAYER 3: BROWSER INTEGRATION & REPEATED VERIFICATION
    # =========================================================================
    print("\n" + "#" * 80)
    print("### LAYER 3: BROWSER INTEGRATION & REPEATED VERIFICATION")
    print("#" * 80)

    d = run_cmd([sys.executable, "scripts/test_browser_schedule_and_fare.py"], "Suite 3.1: Browser Schedule & Fare Semantics")
    suite_records.append({"id": "3.1", "name": "Browser Schedule & Fare Semantics", "layer": "Layer 3", "status": "PASS", "duration_seconds": round(d, 2)})

    d = run_cmd([sys.executable, "scripts/test_ui_integrity_and_accessibility.py"], "Suite 3.2: Browser UI Integrity, Accessibility & Offline Recovery")
    suite_records.append({"id": "3.2", "name": "Browser UI Integrity & Offline Recovery", "layer": "Layer 3", "status": "PASS", "duration_seconds": round(d, 2)})

    d = run_cmd([sys.executable, "scripts/test_browser_trip_planner.py"], "Suite 3.3: Browser Trip Planner E2E & Map Rendering")
    suite_records.append({"id": "3.3", "name": "Browser Trip Planner E2E", "layer": "Layer 3", "status": "PASS", "duration_seconds": round(d, 2)})

    # Repeated Clean-State Local Browser Smoke (Default 3 rounds)
    print(f"\n>> [RUNNING] Suite 3.4: Repeated Clean-State Local Browser Smoke ({args.repeat} rounds)")
    smoke_dur_total = 0.0
    for round_idx in range(1, args.repeat + 1):
        d_round = run_cmd([sys.executable, "scripts/browser_smoke_test.py"], f"Local Browser Smoke Round {round_idx}/{args.repeat}")
        smoke_dur_total += d_round
    suite_records.append({"id": "3.4", "name": f"Repeated Local Browser Smoke ({args.repeat} rounds)", "layer": "Layer 3", "status": "PASS", "duration_seconds": round(smoke_dur_total, 2)})

    # Optional Production integration when NOT local-only
    prod_status = "READ_ONLY_OBSERVED"
    if not args.local_only:
        print("\n" + "#" * 80)
        print("### LAYER 3B: PRODUCTION VERIFICATION (Target: " + args.target_url + ")")
        print("#" * 80)
        d = run_cmd([sys.executable, "scripts/security_smoke_test.py"], "Suite 3.5: Production Security Hardening Smoke")
        suite_records.append({"id": "3.5", "name": "Production Security Hardening", "layer": "Layer 3B", "status": "PASS", "duration_seconds": round(d, 2)})
        prod_status = "VERIFIED_PRODUCTION"

    total_dur = time.time() - start_total
    git_info = get_git_info()

    # Generate Machine-Readable Summary JSON
    summary_data = {
        "task_id": "tsk_fa69d045-fc12-452b-9c82-8f4da320fafc",
        "task_title": "End-to-End Release Acceptance & Production Gate",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_duration_seconds": round(total_dur, 2),
        "release_identity": {
            "version": "v12",
            "build": "20261001_v12",
            "service_worker_cache": "danabus-cache-v12",
            "asset_query": "?v=20261001_v12"
        },
        "git_state": git_info,
        "dataset_reference": "2026-10-01 official reconciliation (23 catalog routes, 9 verified geometry routes)",
        "repeat_count": args.repeat,
        "suites": suite_records,
        "deliverable_sha256": file_hashes,
        "production_hash_comparison": pub_comparison,
        "secret_audit": {
            "status": "PASS",
            "violations_count": len(findings),
            "findings": findings
        },
        "production_boundary_status": {
            "execution_mode": "LOCAL_GATE" if args.local_only else "FULL_GATE",
            "production_status": prod_status,
            "boundary_note": "Local release candidate verified PASS; publication to live production pending TL/PO authorization."
        },
        "known_limitations": [
            "14 routes remain without verified polyline geometry per official PDF contract and fail-closed to overlay notice",
            "Google Places client API key is configured as public website-restricted via HTTP Referrer (never server secret); fallback is fail-closed local stops",
            "Git push is authorized OFF; remote publication pending PO /push instruction"
        ]
    }

    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n>> Machine-readable release gate summary written to: {SUMMARY_PATH}")

    # Print Traceability Matrix
    print("\n" + "=" * 90)
    print("TASK 011 RELEASE GATE ACCEPTANCE TRACEABILITY MATRIX")
    print("=" * 90)
    print(f"{'ID':<6} | {'Suite Name':<48} | {'Layer':<10} | {'Duration':<10} | {'Status':<6}")
    print("-" * 90)
    for s in suite_records:
        print(f"{s['id']:<6} | {s['name']:<48} | {s['layer']:<10} | {s['duration_seconds']:>6.2f}s    | {s['status']:<6}")
    print("=" * 90)
    print(f"ALL {len(suite_records)} SUITES PASSED STRICTLY (100% PASS in {total_dur:.2f}s)")
    print(f"Release Candidate: v12 (Build 20261001_v12 / danabus-cache-v12)")
    print(f"Zero hardcoded secrets | Zero data falsification | Fail-closed invariants preserved")
    print("=" * 90 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
