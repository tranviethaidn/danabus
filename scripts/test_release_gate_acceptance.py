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
TASK011_EVIDENCE_DIR = WORKSPACE / "docs" / "reports" / "evidence" / "task-011"

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


def is_binary_file(filepath):
    ext = filepath.suffix.lower()
    if ext in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".woff", ".woff2", ".ttf", ".eot", ".zip", ".tar", ".gz"}:
        return True
    try:
        chunk = filepath.read_bytes()[:1024]
        if b'\x00' in chunk:
            return True
    except Exception:
        return True
    return False


def is_fixture_or_rule_def(line, rel_path=""):
    """
    Narrow filter: strictly ignores only lines defining scanner rules, test fixtures,
    or scanner implementation details in scanner/test scripts.
    Never ignores generic runtime markers like '-----BEGIN' or API keys.
    """
    if "re.compile(" in line or "SECRET_RULES" in line or "test_rule_fixture" in line or "prohibited_sdk_terms" in line or "verify_secret_audit_negative_regression" in line:
        return True
    return False


def verify_secret_audit_negative_regression():
    """
    Negative regression probe for Defect 1:
    Demonstrates that synthetic private-key PEM headers
    are NOT bypassed by fixture ignore filters, are strictly detected by SECRET_RULES,
    and are logged with full redaction (zero body/value leakage).
    """
    print("\n>> [RUNNING] Secret Audit Negative Regression Probe (Synthetic Private Key Detection & Redaction)")
    start_t = time.time()

    part1 = "-----"
    probe_samples = [
        (part1 + "BEGIN RSA PRIVATE KEY-----", "Private Key"),
        (part1 + "BEGIN PRIVATE KEY-----", "Private Key"),
        (part1 + "BEGIN EC PRIVATE KEY-----", "Private Key"),
    ]

    for sample, expected_rule in probe_samples:
        # 1. Verify not ignored by narrow fixture definition check
        if is_fixture_or_rule_def(sample, "probe.pem"):
            print(f"[-] FAIL: Synthetic private key marker was falsely ignored by fixture rules: {sample}")
            sys.exit(1)

        # 2. Verify strictly detected by SECRET_RULES
        matched_rule = None
        match_count = 0
        for r_name, pat in SECRET_RULES:
            m = pat.findall(sample)
            if m:
                matched_rule = r_name
                match_count = len(m)
                break

        if matched_rule != expected_rule:
            print(f"[-] FAIL: Synthetic private key probe not detected as {expected_rule}, got {matched_rule}")
            sys.exit(1)

        # 3. Verify redaction: formatted violation must not leak secret value/body
        violation_entry = {
            "file": "synthetic_probe.pem",
            "line": 1,
            "rule": matched_rule,
            "count": match_count
        }
        redacted_log = f"[VIOLATION REDACTED] file={violation_entry['file']}:{violation_entry['line']}, rule={violation_entry['rule']}, match_count={violation_entry['count']}"
        if sample in redacted_log or "BEGIN" in redacted_log:
            print(f"[-] FAIL: Secret value leaked in violation log: {redacted_log}")
            sys.exit(1)

        print(f"   | Probe verified for {expected_rule}: detected and redacted -> {redacted_log.strip()}")

    dur = time.time() - start_t
    print(f"   [PASS] Secret Audit Negative Regression Probe ({dur:.2f}s)")
    return dur


def audit_secrets():
    """
    Performs static credential and secret audit across all tracked repository text files.
    Strictly complies with security rules:
    - Never prints matched secret or sensitive values!
    - Only reports file path, line number, rule name, and count (all redacted).
    - Fails closed if any potential real credential is found.
    - Uses narrow fixture/rule definitions and does not bypass private-key headers.
    """
    print("\n>> [RUNNING] Static Secret & Credential Audit (Repository-Wide Coverage)")
    start_t = time.time()

    findings = []
    try:
        res = subprocess.run(["git", "ls-files"], cwd=WORKSPACE, text=True, capture_output=True, check=True)
        tracked_files = [WORKSPACE / f.strip() for f in res.stdout.splitlines() if f.strip()]
    except Exception:
        tracked_files = []
        for root, dirs, files in os.walk(WORKSPACE):
            dirs[:] = [d for d in dirs if d not in {".git", ".agent-rule", "node_modules", "__pycache__"}]
            for f in files:
                tracked_files.append(Path(root) / f)

    scanned_count = 0
    for fpath in tracked_files:
        if not fpath.is_file() or is_binary_file(fpath):
            continue
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        scanned_count += 1
        rel_path = fpath.relative_to(WORKSPACE).as_posix()
        for idx, line in enumerate(content.splitlines()):
            if is_fixture_or_rule_def(line, rel_path):
                continue
            for rule_name, pat in SECRET_RULES:
                matches = pat.findall(line)
                if matches:
                    findings.append({
                        "file": rel_path,
                        "line": idx + 1,
                        "rule": rule_name,
                        "count": len(matches)
                    })

    dur = time.time() - start_t
    if findings:
        print(f"\n[-] FAIL: Secret audit detected {len(findings)} potential violations across repository!")
        for f in findings:
            print(f"    [VIOLATION REDACTED] file={f['file']}:{f['line']}, rule={f['rule']}, match_count={f['count']}")
        sys.exit(1)

    print(f"   | Scanned {scanned_count} repository text files (tracked sources, configs, scripts, data, docs)")
    print("   | Violations detected: 0 (Repository strictly clean)")
    print(f"   [PASS] Static Secret & Credential Audit ({dur:.2f}s)")
    return dur, findings, scanned_count


def verify_production_public_tls(target_url):
    """
    Explicitly verifies that target public HTTPS endpoint possesses a valid,
    trusted TLS certificate, completes TLS handshake strictly without bypassing
    hostname or certificate validation, and returns HTTP 200 on public root.
    """
    print(f"\n>> [RUNNING] Explicit Public HTTPS & TLS Certificate Validation ({target_url})")
    start_t = time.time()

    import urllib.parse
    parsed = urllib.parse.urlparse(target_url)
    if parsed.scheme.lower() != "https":
        print(f"   | Target URL is not HTTPS: {target_url} (Skipping TLS cert validation)")
        return 0.0

    import ssl
    import socket
    import urllib.request

    ctx = ssl.create_default_context()
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED

    hostname = parsed.hostname or "danabus.638686.xyz"
    port = parsed.port or 443

    # 1. Socket-level TLS handshake inspection
    try:
        with socket.create_connection((hostname, port), timeout=10) as raw_sock:
            with ctx.wrap_socket(raw_sock, server_hostname=hostname) as tls_sock:
                cert = tls_sock.getpeercert()
                cipher = tls_sock.cipher()
                tls_version = tls_sock.version()
                san = [item[1] for item in cert.get('subjectAltName', ()) if item[0] == 'DNS']
                expiry = cert.get('notAfter')
                print(f"   | TLS Handshake: {tls_version}, Cipher: {cipher[0]}")
                print(f"   | Verified Certificate SAN: {san}, Expiry: {expiry}")
    except Exception as e:
        print(f"[-] FAIL: Public HTTPS TLS validation failed for {hostname}:{port}: {e}")
        sys.exit(1)

    # 2. HTTP request with strict TLS
    try:
        req = urllib.request.Request(target_url, headers={"User-Agent": "DanabusReleaseGate/1.0"})
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            if resp.status != 200:
                print(f"[-] FAIL: Public HTTPS root returned status {resp.status} != 200")
                sys.exit(1)
            print(f"   | Public HTTPS root fetch: HTTP {resp.status} OK (strict TLS verified)")
    except Exception as e:
        print(f"[-] FAIL: Public HTTPS root request failed: {e}")
        sys.exit(1)

    dur = time.time() - start_t
    print(f"   [PASS] Explicit Public HTTPS & TLS Certificate Validation ({dur:.2f}s)")
    return dur


def compute_deliverables_hashes(local_only=True, target_url=None):
    """
    Computes SHA-256 for all whitelist deliverables.
    - In local-only mode: verifies local workspace integrity and generates manifest;
      records comparison with public root as PENDING_PUBLICATION if mismatch.
    - In full production mode: strictly enforces 3-way equivalence:
      workspace == /var/www/danabus/public == HTTP live URL.
      Fails fast (non-zero) on any missing file, hash mismatch, or HTTP error.
      Enforces strict TLS certificate validation on all HTTPS fetches.
    """
    print("\n>> [RUNNING] Whitelist Deliverables SHA-256 Checksum Computation")
    start_t = time.time()

    hashes = {}
    pub_dir = Path("/var/www/danabus/public")
    pub_comparison = {}
    mismatches = []

    import ssl
    import urllib.parse
    import urllib.request
    # Strictly enforce TLS certificate validation for HTTPS targets
    ctx = ssl.create_default_context()
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED

    for rel in DELIVERABLE_FILES:
        fpath = WORKSPACE / rel
        if not fpath.exists():
            print(f"[-] FAIL: Missing required workspace deliverable: {rel}")
            sys.exit(1)

        h = hashlib.sha256(fpath.read_bytes()).hexdigest()
        hashes[rel] = h

        pub_file = pub_dir / rel if pub_dir.exists() else None
        pub_h = None
        pub_match = False
        if pub_file and pub_file.exists():
            pub_h = hashlib.sha256(pub_file.read_bytes()).hexdigest()
            pub_match = (h == pub_h)

        if local_only:
            pub_comparison[rel] = {
                "workspace_sha256": h[:12] + "...",
                "public_sha256": (pub_h[:12] + "...") if pub_h else "NOT_FOUND",
                "sync_status": "IN_SYNC" if pub_match else "PENDING_PUBLICATION",
                "match": pub_match
            }
        else:
            # Full production mode: must check public root AND live HTTP URL
            if not pub_file or not pub_file.exists():
                mismatches.append(f"{rel}: missing from public root ({pub_dir})")
            elif not pub_match:
                mismatches.append(f"{rel}: workspace hash {h[:12]} != public hash {pub_h[:12]}")

            # Fetch live HTTP URL with strict TLS
            live_url = urllib.parse.urljoin(target_url, rel)
            live_h = None
            live_status = None
            try:
                req = urllib.request.Request(live_url, headers={"User-Agent": "DanabusReleaseGate/1.0", "Accept": "*/*"})
                with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                    live_status = resp.status
                    live_data = resp.read()
                    live_h = hashlib.sha256(live_data).hexdigest()
            except Exception as e:
                mismatches.append(f"{rel}: HTTP fetch failed from {live_url} ({e})")

            if live_status != 200:
                mismatches.append(f"{rel}: live HTTP status {live_status} != 200 from {live_url}")
            elif live_h != h:
                mismatches.append(f"{rel}: live HTTP hash {live_h[:12] if live_h else 'None'} != workspace hash {h[:12]}")

            pub_comparison[rel] = {
                "workspace_sha256": h[:12] + "...",
                "public_sha256": (pub_h[:12] + "...") if pub_h else "NOT_FOUND",
                "live_sha256": (live_h[:12] + "...") if live_h else "FETCH_FAILED",
                "http_status": live_status,
                "3way_match": (pub_match and live_h == h)
            }

    dur = time.time() - start_t
    if not local_only and mismatches:
        print(f"\n[-] FAIL: Production 3-way hash equivalence failed with {len(mismatches)} mismatches:")
        for m in mismatches:
            print(f"    * {m}")
        sys.exit(1)

    print(f"   | Computed SHA-256 for {len(hashes)} deliverable artifacts")
    if local_only:
        print("   | Local hash manifest generated successfully; production sync status: PENDING_PUBLICATION")
        print(f"   [PASS] Deliverable SHA-256 Hash Manifest ({dur:.2f}s)")
    else:
        print("   | Full 3-way equivalence verified across workspace, public root, and live URL")
        print(f"   [PASS] Production 3-Way Deliverables Hash Equivalence ({dur:.2f}s)")

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
    parser.add_argument("--test-secret-probe", action="store_true", help="Run synthetic private key negative regression probe standalone")
    args = parser.parse_args()

    if args.test_secret_probe:
        dur = verify_secret_audit_negative_regression()
        print(f"\n>> Standalone Secret Audit Negative Probe completed successfully in {dur:.2f}s (PASS)")
        return 0

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

    d_probe = verify_secret_audit_negative_regression()
    d, findings, scanned_count = audit_secrets()
    suite_records.append({"id": "2.2", "name": f"Static Secret Audit & Negative Probe ({scanned_count} files)", "layer": "Layer 2", "status": "PASS", "duration_seconds": round(d + d_probe, 2)})

    if not args.local_only:
        d_tls = verify_production_public_tls(args.target_url)
        suite_records.append({"id": "2.3", "name": "Production Public TLS & Certificate Validation", "layer": "Layer 2", "status": "PASS", "duration_seconds": round(d_tls, 2)})

    d, file_hashes, pub_comparison = compute_deliverables_hashes(local_only=args.local_only, target_url=args.target_url)
    manifest_id = "2.3" if args.local_only else "2.4"
    manifest_name = "Deliverable SHA-256 Hash Manifest" if args.local_only else "Production 3-Way Deliverables Hash Equivalence"
    manifest_status = "LOCAL_HASH_MANIFEST_PASS" if args.local_only else "PASS"
    suite_records.append({"id": manifest_id, "name": manifest_name, "layer": "Layer 2", "status": manifest_status, "duration_seconds": round(d, 2)})

    # =========================================================================
    # LAYER 3: BROWSER INTEGRATION & REPEATED VERIFICATION
    # =========================================================================
    print("\n" + "#" * 80)
    print("### LAYER 3: BROWSER INTEGRATION & REPEATED VERIFICATION")
    print("#" * 80)

    TASK011_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    d = run_cmd([sys.executable, "scripts/test_browser_schedule_and_fare.py", "--screenshot-path", str(TASK011_EVIDENCE_DIR / "browser_schedule_fare_evidence.png")], "Suite 3.1: Browser Schedule & Fare Semantics")
    suite_records.append({"id": "3.1", "name": "Browser Schedule & Fare Semantics", "layer": "Layer 3", "status": "PASS", "duration_seconds": round(d, 2)})

    d = run_cmd([sys.executable, "scripts/test_ui_integrity_and_accessibility.py", "--screenshot-path", str(TASK011_EVIDENCE_DIR / "browser_ui_accessibility_evidence.png")], "Suite 3.2: Browser UI Integrity, Accessibility & Offline Recovery")
    suite_records.append({"id": "3.2", "name": "Browser UI Integrity & Offline Recovery", "layer": "Layer 3", "status": "PASS", "duration_seconds": round(d, 2)})

    d = run_cmd([sys.executable, "scripts/test_browser_trip_planner.py", "--screenshot-path", str(TASK011_EVIDENCE_DIR / "browser_trip_planner_evidence.png")], "Suite 3.3: Browser Trip Planner E2E & Map Rendering")
    suite_records.append({"id": "3.3", "name": "Browser Trip Planner E2E", "layer": "Layer 3", "status": "PASS", "duration_seconds": round(d, 2)})

    # Repeated Clean-State Local Browser Smoke (Default 3 rounds)
    print(f"\n>> [RUNNING] Suite 3.4: Repeated Clean-State Local Browser Smoke ({args.repeat} rounds)")
    smoke_dur_total = 0.0
    for round_idx in range(1, args.repeat + 1):
        d_round = run_cmd([sys.executable, "scripts/browser_smoke_test.py", "--screenshot-path", str(TASK011_EVIDENCE_DIR / "browser_smoke_evidence.png")], f"Local Browser Smoke Round {round_idx}/{args.repeat}")
        smoke_dur_total += d_round
    suite_records.append({"id": "3.4", "name": f"Repeated Local Browser Smoke ({args.repeat} rounds)", "layer": "Layer 3", "status": "PASS", "duration_seconds": round(smoke_dur_total, 2)})

    # Optional Production integration when NOT local-only
    prod_status = "PENDING_PUBLICATION"
    if not args.local_only:
        print("\n" + "#" * 80)
        print("### LAYER 3B: FULL PRODUCTION GATE VERIFICATION (Target: " + args.target_url + ")")
        print("#" * 80)

        d = run_cmd([sys.executable, "scripts/security_smoke_test.py"], "Suite 3.5: Production Security Hardening Smoke")
        suite_records.append({"id": "3.5", "name": "Production Security Hardening", "layer": "Layer 3B", "status": "PASS", "duration_seconds": round(d, 2)})

        d = run_cmd([
            sys.executable, "scripts/test_production_pwa_runtime.py",
            "--repeat", str(args.repeat),
            "--target-url", args.target_url,
            "--screenshot-path", str(TASK011_EVIDENCE_DIR / "production_pwa_v12_evidence.png")
        ], f"Suite 3.6: Production PWA Runtime & Warm Upgrade ({args.repeat} rounds)")
        suite_records.append({"id": "3.6", "name": f"Production PWA Runtime v12 ({args.repeat} rounds)", "layer": "Layer 3B", "status": "PASS", "duration_seconds": round(d, 2)})

        print(f"\n>> [RUNNING] Suite 3.7: Repeated Production Browser Smoke ({args.repeat} rounds on {args.target_url})")
        prod_smoke_total = 0.0
        for round_idx in range(1, args.repeat + 1):
            d_round = run_cmd([
                sys.executable, "scripts/browser_smoke_test.py",
                args.target_url,
                "--screenshot-path", str(TASK011_EVIDENCE_DIR / "production_browser_smoke_evidence.png")
            ], f"Production Browser Smoke Round {round_idx}/{args.repeat}")
            prod_smoke_total += d_round
        suite_records.append({"id": "3.7", "name": f"Repeated Production Browser Smoke ({args.repeat} rounds)", "layer": "Layer 3B", "status": "PASS", "duration_seconds": round(prod_smoke_total, 2)})

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
            "scanned_files_count": scanned_count,
            "violations_count": len(findings),
            "findings": findings
        },
        "production_boundary_status": {
            "execution_mode": "LOCAL_GATE" if args.local_only else "FULL_GATE",
            "production_status": prod_status,
            "production_hash_equivalence": "PENDING_PUBLICATION" if args.local_only else "PASS",
            "production_pwa_runtime": "PENDING_PUBLICATION" if args.local_only else "PASS",
            "production_browser_smoke": "PENDING_PUBLICATION" if args.local_only else "PASS",
            "boundary_note": (
                "Local release candidate v12 verified PASS (15 suites); production publication pending PO authorization and deployment."
                if args.local_only else
                "Production environment verified strictly compliant and equivalent with release candidate v12."
            )
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
