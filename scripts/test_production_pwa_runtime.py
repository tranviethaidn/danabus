#!/usr/bin/env python3
"""
Production Runtime Verification for Task 005: Address-to-Address Trip Planner & PWA v11
Target: https://danabus.638686.xyz/
Verifies:
0. Staged deploy order invariant: payload -> manifest -> index.html (atomic) -> sw.js (atomic, last)
1. First-install Service Worker takeover, controllerchange, and reload settled lifecycle
2. Feature markers of TransitPlanner and multi-leg UI
3. Live planner E2E execution and Leaflet multi-leg map rendering (bounded predicates)
4. Fresh install precache in isolated profile (danabus-cache-v11)
5. Warm-cache migration from v10 (and v4-v9) to v11 with clean purge
6. Offline fallback resilience for app shell, scripts, styles, and datasets
7. Deliverable screenshot capture
"""

import os
import sys
import time
import json
import base64
import socket
import tempfile
import shutil
import urllib.request
import subprocess
import argparse
from pathlib import Path

TARGET_URL = "https://danabus.638686.xyz/"
WORKSPACE = Path(__file__).resolve().parent.parent
SCREENSHOT_PATH = WORKSPACE / "docs" / "reports" / "task5_production_pwa_v11_evidence.png"


def verify_deploy_order_invariant():
    """
    Verifies that scripts/deploy_danabus_production.sh implements the strict publish order:
    1. payload assets (css, js, assets, data)
    2. manifest.json
    3. atomic index.html swap
    4. atomic sw.js swap (LAST)
    Ensuring sw.js v11 can never precache an outdated index.html.
    """
    deploy_script = (WORKSPACE / "scripts" / "deploy_danabus_production.sh").read_text(encoding="utf-8")

    pos_payload_sync = deploy_script.find('rsync -a --delete "$WORKSPACE"/css/')
    pos_manifest_copy = deploy_script.find('cp -f "$WORKSPACE"/manifest.json')
    pos_index_swap = deploy_script.find('mv -f "$PUBLIC_DIR/index.html.tmp" "$PUBLIC_DIR/index.html"')
    pos_sw_swap = deploy_script.find('mv -f "$PUBLIC_DIR/sw.js.tmp" "$PUBLIC_DIR/sw.js"')

    assert pos_payload_sync != -1 and pos_manifest_copy != -1 and pos_index_swap != -1 and pos_sw_swap != -1, \
        "Deploy script missing required staged deploy milestones"
    assert pos_payload_sync < pos_manifest_copy, "Payload assets must be synced before manifest"
    assert pos_manifest_copy < pos_index_swap, "Manifest must be copied before atomic index.html swap"
    assert pos_index_swap < pos_sw_swap, \
        "Atomic index.html swap MUST precede atomic sw.js swap to prevent worker precaching old index"


class SimpleWebSocket:
    def __init__(self, url):
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        self.host = parsed.hostname
        self.port = parsed.port or 80
        self.path = parsed.path or "/"
        self.sock = socket.create_connection((self.host, self.port), timeout=25)
        self._handshake()

    def _handshake(self):
        key = base64.b64encode(os.urandom(16)).decode('ascii')
        headers = [
            f"GET {self.path} HTTP/1.1",
            f"Host: {self.host}:{self.port}",
            "Upgrade: websocket",
            "Connection: Upgrade",
            f"Sec-WebSocket-Key: {key}",
            "Sec-WebSocket-Version: 13",
            "\r\n"
        ]
        self.sock.sendall("\r\n".join(headers).encode('utf-8'))
        resp = b""
        while b"\r\n\r\n" not in resp:
            data = self.sock.recv(1024)
            if not data:
                raise ConnectionError("WebSocket handshake failed")
            resp += data

    def send_text(self, text):
        data = text.encode('utf-8')
        length = len(data)
        frame = bytearray([0x81])
        mask_key = os.urandom(4)
        if length <= 125:
            frame.append(0x80 | length)
        elif length <= 65535:
            frame.append(0x80 | 126)
            frame.extend(length.to_bytes(2, 'big'))
        else:
            frame.append(0x80 | 127)
            frame.extend(length.to_bytes(8, 'big'))
        frame.extend(mask_key)
        masked = bytearray(b ^ mask_key[i % 4] for i, b in enumerate(data))
        frame.extend(masked)
        self.sock.sendall(frame)

    def recv_text(self):
        def recv_exact(n):
            buf = bytearray()
            while len(buf) < n:
                chunk = self.sock.recv(n - len(buf))
                if not chunk:
                    raise ConnectionError("Socket closed prematurely")
                buf.extend(chunk)
            return bytes(buf)

        head = recv_exact(2)
        masked = bool(head[1] & 0x80)
        pay_len = head[1] & 0x7F
        if pay_len == 126:
            pay_len = int.from_bytes(recv_exact(2), 'big')
        elif pay_len == 127:
            pay_len = int.from_bytes(recv_exact(8), 'big')

        mask_key = recv_exact(4) if masked else None
        body = recv_exact(pay_len)
        if masked:
            body = bytes(b ^ mask_key[i % 4] for i, b in enumerate(body))
        return body.decode('utf-8')

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


class ChromeBrowserSession:
    def __init__(self, port=9444, user_data_dir=None):
        self.port = port
        self.user_data_dir = user_data_dir or tempfile.mkdtemp(prefix="danabus_prod_test_")
        self.proc = None
        self.ws = None
        self.msg_id = 0
        self.settled_lifecycle = None

    def start(self, target_url=TARGET_URL):
        chrome_bin = "/bin/google-chrome"
        if not os.path.exists(chrome_bin):
            chrome_bin = shutil.which("chromium") or shutil.which("chromium-browser") or "google-chrome"

        cmd = [
            chrome_bin,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--ignore-certificate-errors",
            "--host-rules=MAP danabus.638686.xyz 127.0.0.1",
            f"--user-data-dir={self.user_data_dir}",
            "--remote-allow-origins=*",
            f"--remote-debugging-port={self.port}",
            target_url
        ]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.2)

        tabs_url = f"http://127.0.0.1:{self.port}/json"
        ws_url = None
        for _ in range(30):
            try:
                with urllib.request.urlopen(tabs_url, timeout=2) as r:
                    tabs = json.loads(r.read().decode())
                    page_tabs = [t for t in tabs if t.get('type') == 'page']
                    if page_tabs:
                        ws_url = page_tabs[0]["webSocketDebuggerUrl"]
                        break
            except Exception:
                time.sleep(0.2)
        if not ws_url:
            raise RuntimeError("Failed to connect to Headless Chrome CDP")

        self.ws = SimpleWebSocket(ws_url)
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("Network.enable")

        # Deterministic settled barrier: survive and wait for first-install Service Worker
        # takeover and controllerchange reload to complete.
        self.settled_lifecycle = self.wait_for_settled(timeout=15.0)

    def call(self, method, params=None):
        self.msg_id += 1
        curr_id = self.msg_id
        req = {"id": curr_id, "method": method, "params": params or {}}
        self.ws.send_text(json.dumps(req))
        while True:
            raw = self.ws.recv_text()
            if not raw:
                raise ConnectionError("Empty CDP response received")
            try:
                res = json.loads(raw)
            except Exception:
                continue
            if res.get("id") == curr_id:
                if "error" in res:
                    raise RuntimeError(f"CDP error: {res['error']}")
                return res.get("result", {})

    def evaluate(self, expr):
        res = self.call("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": True
        })
        if "exceptionDetails" in res:
            exc = res["exceptionDetails"]
            desc = exc.get("exception", {}).get("description") or exc.get("text", "Unknown JS error")
            raise RuntimeError(f"JavaScript evaluation threw exception: {desc} (expr: {expr[:200]})")
        res_obj = res.get("result", {})
        if res_obj.get("subtype") == "error":
            raise RuntimeError(f"JavaScript error: {res_obj.get('description', 'Unknown error')} (expr: {expr[:200]})")
        return res_obj.get("value")

    def wait_for_condition(self, expr, timeout=10.0, step=0.1, description=""):
        start = time.time()
        desc = description or expr[:80]
        while time.time() - start < timeout:
            try:
                val = self.evaluate(expr)
                if val:
                    return val
            except Exception:
                pass
            time.sleep(step)
        raise TimeoutError(f"Condition timed out after {timeout:.1f}s: {desc}")

    def wait_for_settled(self, timeout=15.0):
        start = time.time()
        predicate = """
            (() => {
                if (document.readyState !== 'complete') return null;
                const sw = window.navigator?.serviceWorker;
                if (!sw) return null;
                const nav = performance.getEntriesByType('navigation')[0];
                const navType = nav ? nav.type : null;
                const controller = sw.controller;

                const swSettled = (controller !== null && navType === 'reload');
                if (!swSettled) return null;

                const appReady = window.app && window.app.loadState === 'ready';
                const busReady = window.busService && window.busService.isLoaded &&
                                 window.busService.routes && window.busService.routes.length > 0 &&
                                 window.busService.stops && window.busService.stops.length > 0;

                if (appReady && busReady) {
                    return {
                        navType,
                        controllerActive: true,
                        controllerScriptURL: controller.scriptURL,
                        appState: window.app.loadState,
                        routesCount: window.busService.routes.length,
                        stopsCount: window.busService.stops.length
                    };
                }
                return null;
            })()
        """
        while time.time() - start < timeout:
            try:
                val = self.evaluate(predicate)
                if val:
                    return val
            except Exception:
                pass
            time.sleep(0.15)
        raise TimeoutError(f"Page did not settle with SW controller & reload within {timeout}s")

    def close(self):
        if self.ws:
            self.ws.close()
        if self.proc:
            self.proc.terminate()
            self.proc.wait()
        if os.path.exists(self.user_data_dir):
            shutil.rmtree(self.user_data_dir, ignore_errors=True)


def test_production_single(port=9455, iteration_label="", target_url=None):
    url = target_url or TARGET_URL
    prefix = f"[{iteration_label}] " if iteration_label else ""
    print(f"{prefix}=== Danabus Production Runtime Verification ({url}) ===\n")

    # Check 0: Staged deploy order invariant
    print(f"{prefix}[Check 0] Verifying Staged Deploy Order Invariant (zero mixed-state cache race)...")
    verify_deploy_order_invariant()
    print(f"{prefix} [PASS] Check 0: Deploy script publishes payload -> manifest -> index.html (atomic) -> sw.js (atomic, last).\n")

    session = ChromeBrowserSession(port=port)
    try:
        session.start(target_url=url)

        # Check 1: First-Install Service Worker Takeover & Controllerchange Lifecycle
        print(f"{prefix}[Check 1] Verifying First-Install Service Worker Takeover & Controllerchange Lifecycle...")
        lifecycle = session.settled_lifecycle
        print(f"{prefix} -> Settled Lifecycle: {json.dumps(lifecycle, indent=2)}")
        assert lifecycle is not None, "Page must achieve settled state"
        assert lifecycle['controllerActive'] is True, "Service Worker must control the page"
        assert lifecycle['navType'] == 'reload', f"Expected reload after controllerchange, got {lifecycle['navType']}"
        assert lifecycle['appState'] == 'ready', f"App state must be 'ready', got {lifecycle['appState']}"
        assert lifecycle['routesCount'] == 23, f"Expected 23 routes loaded, got {lifecycle['routesCount']}"
        assert lifecycle['stopsCount'] > 0, f"Expected stops loaded, got {lifecycle['stopsCount']}"
        assert "sw.js" in lifecycle['controllerScriptURL'], f"Controller URL must point to sw.js, got {lifecycle['controllerScriptURL']}"
        print(f"{prefix} [PASS] Check 1: Controllerchange reload settled cleanly with active Service Worker.\n")

        # Check 2: Production Feature Markers & DOM Elements
        print(f"{prefix}[Check 2] Verifying Production Feature Markers & DOM Elements...")
        markers = session.wait_for_condition("""
            (() => {
                if (!window.TransitPlanner || !window.transitPlanner || !window.busService?.routes) return null;
                return {
                    hasTransitPlannerClass: typeof window.TransitPlanner === 'function',
                    hasTransitPlannerInstance: !!window.transitPlanner,
                    hasRenderTrip: typeof window.mapService?.renderTrip === 'function',
                    hasTripOptionsEl: !!document.getElementById('trip-planner-options'),
                    hasSwapBtn: !!document.getElementById('btn-swap-locations'),
                    hasOriginBtn: !!document.getElementById('btn-home-origin'),
                    hasOriginDisplay: !!document.getElementById('home-origin-display'),
                    hasDestinationInput: !!document.getElementById('home-destination-input'),
                    routesCount: window.busService?.routes?.length || 0,
                    appVersionScript: Array.from(document.querySelectorAll('script[src]'))
                        .map(s => s.getAttribute('src'))
                        .find(s => s.includes('app.js'))
                };
            })()
        """, timeout=10.0, description="Feature markers query")
        print(f"{prefix} -> Feature Markers: {json.dumps(markers, indent=2)}")
        assert markers['hasTransitPlannerClass'] is True, "TransitPlanner class must be exposed"
        assert markers['hasTransitPlannerInstance'] is True, "window.transitPlanner instance must exist"
        assert markers['hasRenderTrip'] is True, "window.mapService.renderTrip must exist"
        assert markers['hasTripOptionsEl'] is True, "#trip-planner-options container must exist"
        assert markers['hasSwapBtn'] is True, "#btn-swap-locations must exist"
        assert markers['hasOriginBtn'] is True, "#btn-home-origin must exist"
        assert markers['hasOriginDisplay'] is True, "#home-origin-display must exist"
        assert markers['hasDestinationInput'] is True, "#home-destination-input must exist"
        assert markers['routesCount'] == 23, f"Must have 23 catalog routes, got {markers['routesCount']}"
        assert "v=20261001_v12" in markers['appVersionScript'], f"Script query must be v12, got {markers['appVersionScript']}"
        print(f"{prefix} [PASS] Check 2: Feature markers and Task 4 DOM containers verified on production.\n")

        # Check 3: Live Address-to-Address Trip Planner E2E & Leaflet Map Rendering
        print(f"{prefix}[Check 3] Live Trip Planner E2E on Production (Bách Khoa -> Biển Đông)...")
        session.evaluate("""
            (() => {
                window.app.showTripResults('Trường Đại học Bách Khoa - ĐHĐN', 'Công viên Biển Đông');
            })()
        """)

        plan_state = session.wait_for_condition("""
            (() => {
                const tripView = document.getElementById('view-trip-results');
                const tripViewActive = !!(tripView && tripView.classList.contains('active'));
                const options = document.querySelectorAll('#trip-planner-options .bg-white');
                const firstBadge = options[0]?.querySelector('span')?.textContent?.trim() || '';
                if (tripViewActive && options.length > 0) {
                    return {
                        tripViewActive: true,
                        optionsCount: options.length,
                        firstBadge: firstBadge
                    };
                }
                return null;
            })()
        """, timeout=10.0, description="Wait for trip planner options rendered")
        print(f"{prefix} -> Live Planner Execution Result: {json.dumps(plan_state, indent=2)}")
        assert plan_state['tripViewActive'] is True, "Trip results screen must be active"
        assert plan_state['optionsCount'] > 0, "Planned trip options must be rendered"
        assert plan_state['firstBadge'] in ["Tuyến trực tiếp", "Ít đi bộ nhất", "Nhanh nhất"], f"Unexpected badge: {plan_state['firstBadge']}"

        # Render trip on map via user click
        session.wait_for_condition("document.querySelector('.btn-view-planned-map') !== null", timeout=5.0, description="Wait for view map button")
        session.evaluate("document.querySelector('.btn-view-planned-map')?.click()")

        render_result = session.wait_for_condition("""
            (() => {
                const mapViewActive = !!document.getElementById('view-map')?.classList.contains('active');
                const hasOrigMarker = document.querySelectorAll('.trip-origin-marker').length > 0;
                const hasDestMarker = document.querySelectorAll('.trip-dest-marker').length > 0;
                const tripPolylinesCount = window.mapService?.tripPolylines?.length || 0;
                if (mapViewActive && hasOrigMarker && hasDestMarker && tripPolylinesCount >= 2) {
                    return {
                        mapViewActive: true,
                        hasOrigMarker: true,
                        hasDestMarker: true,
                        tripPolylinesCount: tripPolylinesCount
                    };
                }
                return null;
            })()
        """, timeout=10.0, description="Wait for map trip render")
        print(f"{prefix} -> Map Render Result: {json.dumps(render_result, indent=2)}")
        assert render_result['mapViewActive'] is True, "Map view must become active"
        assert render_result['hasOrigMarker'] is True, "Trip origin marker must be present"
        assert render_result['hasDestMarker'] is True, "Trip dest marker must be present"
        assert render_result['tripPolylinesCount'] >= 2, "Trip polylines must be rendered (walking + bus)"
        print(f"{prefix} [PASS] Check 3: Live Address-to-Address Trip Planner execution and multi-leg map rendering succeeded on production.\n")

        # Check 4: Fresh Install Precache
        print(f"{prefix}[Check 4] Verifying Fresh Install & Service Worker Cache Registration (danabus-cache-v12)...")
        sw_ready = session.wait_for_condition("""
            (async () => {
                const reg = await navigator.serviceWorker.getRegistration();
                const keys = await caches.keys();
                if (reg && keys.includes('danabus-cache-v12')) {
                    return {
                        hasReg: true,
                        active: !!(reg.active || reg.installing || reg.waiting),
                        keys: keys
                    };
                }
                return null;
            })()
        """, timeout=12.0, description="Wait for danabus-cache-v12 cache registration")

        print(f"{prefix} -> Fresh SW State: {sw_ready}")
        assert sw_ready['hasReg'] is True, "Service Worker registration must exist"
        assert 'danabus-cache-v12' in sw_ready['keys'], f"danabus-cache-v12 must exist in fresh install, got {sw_ready['keys']}"

        cached_urls = session.wait_for_condition("""
            (async () => {
                const cache = await caches.open('danabus-cache-v12');
                const reqs = await cache.keys();
                if (reqs && reqs.length >= 25) {
                    return reqs.map(r => r.url);
                }
                return null;
            })()
        """, timeout=10.0, description="Wait for cached asset keys")
        print(f"{prefix} -> Cached assets count: {len(cached_urls)}")
        assert any("index.html" in u for u in cached_urls), "index.html must be in danabus-cache-v12"
        assert any("app.css?v=20261001_v12" in u for u in cached_urls), "app.css v12 must be in cache"
        assert any("busService.js?v=20261001_v12" in u for u in cached_urls), "busService.js v12 must be in cache"
        assert any("mapService.js?v=20261001_v12" in u for u in cached_urls), "mapService.js v12 must be in cache"
        assert any("app.js?v=20261001_v12" in u for u in cached_urls), "app.js v12 must be in cache"
        print(f"{prefix} [PASS] Check 4: Fresh PWA install & static asset precache verified.\n")

        # Check 5: Warm Cache Migration & Legacy Store Purge
        print(f"{prefix}[Check 5] Verifying Warm-Cache Migration & Purge of Legacy Stores (v4-v11 -> v12)...")
        session.evaluate("""
            (async () => {
                await caches.open('danabus-cache-v4');
                await caches.open('danabus-cache-v5');
                await caches.open('danabus-cache-v6');
                await caches.open('danabus-cache-v7');
                await caches.open('danabus-cache-v9');
                await caches.open('danabus-cache-v10');
                await caches.open('danabus-cache-v11');
            })()
        """)
        pre_keys = session.evaluate("(async () => await caches.keys())()")
        print(f"{prefix} -> Injected legacy caches: {pre_keys}")
        assert 'danabus-cache-v11' in pre_keys
        assert 'danabus-cache-v10' in pre_keys
        assert 'danabus-cache-v9' in pre_keys

        session.evaluate("""
            (async () => {
                const regToken = Date.now();
                await navigator.serviceWorker.register(`sw.js?test_token=${regToken}`);
            })()
        """)

        post_migration_keys = session.wait_for_condition("""
            (async () => {
                const k = await caches.keys();
                if (k.includes('danabus-cache-v12') && !k.includes('danabus-cache-v11') && !k.includes('danabus-cache-v10') && !k.includes('danabus-cache-v9') && !k.includes('danabus-cache-v7') && !k.includes('danabus-cache-v4')) {
                    return k;
                }
                return null;
            })()
        """, timeout=12.0, description="Wait for legacy caches purged")

        print(f"{prefix} -> Post-migration cache keys: {post_migration_keys}")
        assert 'danabus-cache-v12' in post_migration_keys
        assert 'danabus-cache-v11' not in post_migration_keys
        assert 'danabus-cache-v10' not in post_migration_keys
        assert 'danabus-cache-v9' not in post_migration_keys
        assert 'danabus-cache-v7' not in post_migration_keys
        assert 'danabus-cache-v4' not in post_migration_keys
        print(f"{prefix} [PASS] Check 5: Warm-cache migration cleanly purged v11 and earlier legacy stores.\n")

        # Check 6: Offline Fallback Resilience
        print(f"{prefix}[Check 6] Testing Offline Fallback Resilience via CDP Network Emulation...")
        session.call("Network.emulateNetworkConditions", {
            "offline": True,
            "latency": 0,
            "downloadThroughput": 0,
            "uploadThroughput": 0
        })

        offline_eval = session.evaluate("""
            (async () => {
                const resApp = await fetch('js/app.js?v=20261001_v12');
                const resBus = await fetch('js/busService.js?v=20261001_v12');
                const resCss = await fetch('css/app.css?v=20261001_v12');
                const resRoutes = await fetch('data/danangbus_routes.json');
                return {
                    appStatus: resApp.status,
                    busStatus: resBus.status,
                    cssStatus: resCss.status,
                    routesStatus: resRoutes.status,
                    routesOk: resRoutes.ok
                };
            })()
        """)
        print(f"{prefix} -> Offline fetch test results: {offline_eval}")
        assert offline_eval['appStatus'] == 200, "app.js must resolve offline from cache"
        assert offline_eval['busStatus'] == 200, "busService.js must resolve offline from cache"
        assert offline_eval['cssStatus'] == 200, "app.css must resolve offline from cache"
        assert offline_eval['routesStatus'] == 200, "danangbus_routes.json must resolve offline from cache/network-first"

        session.call("Network.emulateNetworkConditions", {
            "offline": False,
            "latency": 0,
            "downloadThroughput": 0,
            "uploadThroughput": 0
        })
        print(f"{prefix} [PASS] Check 6: Offline fallback resilience confirmed under simulated offline mode.\n")

        # Check 7: Deliverable Screenshot Capture
        print(f"{prefix}[Check 7] Capturing Production Verification Screenshot...")
        shot_res = session.call("Page.captureScreenshot", {"format": "png"})
        if shot_res.get("data"):
            img_bytes = base64.b64decode(shot_res["data"])
            with open(SCREENSHOT_PATH, "wb") as f:
                f.write(img_bytes)
            print(f"{prefix} -> Screenshot saved to {SCREENSHOT_PATH} ({len(img_bytes)} bytes)")
            print(f"{prefix} [PASS] Check 7: Screenshot captured.\n")

        print(f"{prefix}>>> ALL PRODUCTION RUNTIME CHECKS PASSED (8/8) <<<\n")
        return True

    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Danabus Production Runtime Verification")
    parser.add_argument("--repeat", type=int, default=1, help="Number of times to run verification from fresh profiles")
    parser.add_argument("--base-port", type=int, default=9455, help="Base CDP port")
    parser.add_argument("--target-url", default=TARGET_URL, help="Target URL to test")
    args = parser.parse_args()

    total_runs = max(1, args.repeat)
    print(f"=== Starting Production Runtime Test Suite (Total runs: {total_runs}) ===\n")
    for r in range(total_runs):
        port = args.base_port + r
        label = f"RUN {r+1}/{total_runs}" if total_runs > 1 else ""
        t0 = time.time()
        success = test_production_single(port=port, iteration_label=label, target_url=args.target_url)
        dur = time.time() - t0
        assert success, f"Run {r+1} failed"
        print(f"--- Completed run {r+1}/{total_runs} in {dur:.2f}s ---\n")

    print(f"============================================================")
    print(f"ALL {total_runs} FRESH-PROFILE RUNS COMPLETED SUCCESSFULLY (100% PASS)")
    print(f"============================================================")


if __name__ == "__main__":
    main()
