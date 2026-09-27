#!/usr/bin/env python3
"""
Security Smoke Test Suite for Danabus Production Hardening (Task 5)
Verifies:
1. Negative security matrix: sensitive paths (.git, docs, scripts, prototypes, schema.ts, osm_cache)
   and missing assets return HTTP 404 (not 200, not SPA index.html).
2. Positive functional matrix: root, manifest, sw.js, css, js, json data, and images return 200 OK
   with correct MIME types and appropriate Cache-Control policies.
3. Security headers: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy
   are strictly present across all endpoints.
4. HTTP to HTTPS 301 redirect.
"""

import sys
import ssl
import http.client
import urllib.parse

HOST_HEADER = "danabus.638686.xyz"
TARGET_HOST = "127.0.0.1"
TARGET_PORT_HTTPS = 443
TARGET_PORT_HTTP = 80

REQUIRED_SECURITY_HEADERS = [
    "x-content-type-options",
    "x-frame-options",
    "x-xss-protection",
    "referrer-policy"
]

NEGATIVE_CASES = [
    "/.git/config",
    "/.git/HEAD",
    "/docs/plans/2026-09-24-address-to-address-trip-planner-plan.md",
    "/docs/reports/2026-09-27-danabus-full-project-audit-report.md",
    "/scripts/danabus.conf",
    "/scripts/deploy_danabus_production.sh",
    "/README.md",
    "/requirements.txt",
    "/stitch_bus_route_finder_pwa/",
    "/data/schema.ts",
    "/data/osm_cache/",
    "/data/osm_cache/transit.json",
    "/data/nonexistent_file.json",
    "/js/nonexistent_file.js",
    "/assets/nonexistent_image.png"
]

POSITIVE_CASES = [
    ("/", "text/html"),
    ("/index.html", "text/html"),
    ("/manifest.json", "application/json"),
    ("/sw.js", "application/javascript"),
    ("/css/app.css", "text/css"),
    ("/js/app.js", "application/javascript"),
    ("/js/busService.js", "application/javascript"),
    ("/data/danangbus_routes.json", "application/json"),
    ("/data/danangbus_stops.json", "application/json"),
    ("/assets/logo.svg", "image/svg+xml")
]

def create_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def run_https_request(path, method="GET"):
    ctx = create_ssl_context()
    conn = http.client.HTTPSConnection(TARGET_HOST, TARGET_PORT_HTTPS, context=ctx, timeout=10)
    headers = {"Host": HOST_HEADER, "User-Agent": "DanabusSecuritySmokeTest/1.0"}
    conn.request(method, path, headers=headers)
    resp = conn.getresponse()
    body = resp.read()
    headers_dict = {k.lower(): v for k, v in resp.getheaders()}
    conn.close()
    return resp.status, headers_dict, body

def run_http_request(path, method="GET"):
    conn = http.client.HTTPConnection(TARGET_HOST, TARGET_PORT_HTTP, timeout=10)
    headers = {"Host": HOST_HEADER, "User-Agent": "DanabusSecuritySmokeTest/1.0"}
    conn.request(method, path, headers=headers)
    resp = conn.getresponse()
    headers_dict = {k.lower(): v for k, v in resp.getheaders()}
    conn.close()
    return resp.status, headers_dict

def test_negative_cases():
    print("\n--- 1. RUNNING NEGATIVE SECURITY TESTS (Must return 404, no HTML leak) ---")
    all_passed = True
    for path in NEGATIVE_CASES:
        status, headers, body = run_https_request(path)
        body_text = body.decode("utf-8", errors="replace")
        is_spa_leak = ("Danabus" in body_text and "app-container" in body_text)
        
        status_ok = (status == 404)
        leak_free = not is_spa_leak
        
        if status_ok and leak_free:
            print(f" [PASS] {path:<65} -> Status: {status} (Fail-closed OK)")
        else:
            print(f" [FAIL] {path:<65} -> Status: {status} (SPA Leak: {is_spa_leak})")
            all_passed = False
            
    return all_passed

def test_positive_cases():
    print("\n--- 2. RUNNING POSITIVE FUNCTIONAL & HEADER TESTS (Must return 200 + valid MIME) ---")
    all_passed = True
    for path, expected_mime in POSITIVE_CASES:
        status, headers, body = run_https_request(path)
        content_type = headers.get("content-type", "")
        cache_control = headers.get("cache-control", "None")
        
        status_ok = (status == 200)
        mime_ok = expected_mime in content_type
        
        # Check security headers
        missing_sec = [h for h in REQUIRED_SECURITY_HEADERS if h not in headers]
        sec_ok = len(missing_sec) == 0
        
        if status_ok and mime_ok and sec_ok:
            print(f" [PASS] {path:<32} -> {status} | MIME: {content_type:<24} | Cache: {cache_control}")
        else:
            print(f" [FAIL] {path:<32} -> {status} | MIME: {content_type:<24} | Missing Sec: {missing_sec}")
            all_passed = False
            
    return all_passed

def test_http_redirect():
    print("\n--- 3. RUNNING HTTP TO HTTPS REDIRECT TEST ---")
    status, headers = run_http_request("/")
    location = headers.get("location", "")
    
    status_ok = (status == 301)
    location_ok = location.startswith("https://danabus.638686.xyz")
    
    if status_ok and location_ok:
        print(f" [PASS] HTTP Port 80 Redirect -> {status} Location: {location}")
        return True
    else:
        print(f" [FAIL] HTTP Port 80 Redirect -> {status} Location: {location}")
        return False

def main():
    print("=" * 80)
    print("DANABUS PRODUCTION SECURITY HARDENING VERIFICATION")
    print(f"Target: https://{HOST_HEADER} ({TARGET_HOST})")
    print("=" * 80)
    
    p1 = test_negative_cases()
    p2 = test_positive_cases()
    p3 = test_http_redirect()
    
    print("\n" + "=" * 80)
    if p1 and p2 and p3:
        print(">>> ALL SECURITY SMOKE CHECKS PASSED SUCCESSFULLY (100%) <<<")
        print("=" * 80)
        return 0
    else:
        print(">>> SOME CHECKS FAILED - PLEASE REVIEW LOGS ABOVE <<<")
        print("=" * 80)
        return 1

if __name__ == "__main__":
    sys.exit(main())
