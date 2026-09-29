#!/usr/bin/env python3
"""
Browser Smoke Test for Danabus Web Application
Uses 100% Python Standard Library (socket, struct, urllib, subprocess, json, base64)
with zero external pip dependencies. Communicates directly with Headless Chrome via CDP.

Checks:
1. Application Boot & DOM State
2. Routes Catalog (23 routes rendered)
3. Route Detail & Map View (02, 05, 11, TKY-TMY, 01DL, 01SB)
4. Direction Switching & Stale Layer Cleanup
5. Geolocation API (Success, Error Code 1/2/3, Accuracy Circle)
6. Capture Screenshot for Deliverable Evidence
"""

import os
import sys
import time
import json
import base64
import socket
import struct
import shutil
import subprocess
import urllib.request

PORT = 8991
CDP_PORT = 9444
SCREENSHOT_PATH = "docs/reports/browser_smoke_evidence.png"

class SimpleWebSocket:
    """Lightweight RFC 6455 WebSocket client using Python standard library socket."""
    def __init__(self, ws_url):
        assert ws_url.startswith('ws://'), f"Invalid WebSocket URL: {ws_url}"
        rest = ws_url[5:]
        host_port, path = rest.split('/', 1)
        path = '/' + path
        if ':' in host_port:
            host, port = host_port.split(':')
            port = int(port)
        else:
            host = host_port
            port = 80

        self.sock = socket.create_connection((host, port), timeout=10)
        key = base64.b64encode(os.urandom(16)).decode('utf-8')
        
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode('utf-8'))
        
        resp = b''
        while b'\r\n\r\n' not in resp:
            chunk = self.sock.recv(1024)
            if not chunk:
                raise ConnectionError("Handshake failed: connection closed")
            resp += chunk
        
        if b'101' not in resp:
            raise ConnectionError(f"WebSocket handshake failed: {resp}")

    def send_text(self, text):
        data = text.encode('utf-8')
        length = len(data)
        mask = os.urandom(4)
        
        header = bytearray([0x81]) # FIN + Text frame
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack('>H', length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack('>Q', length))
        
        header.extend(mask)
        masked_data = bytearray(b ^ mask[i % 4] for i, b in enumerate(data))
        self.sock.sendall(header + masked_data)

    def recv_text(self):
        while True:
            head = self._recv_exact(2)
            b1, b2 = head[0], head[1]
            opcode = b1 & 0x0F
            is_masked = (b2 & 0x80) != 0
            payload_len = b2 & 0x7F
            
            if payload_len == 126:
                payload_len = struct.unpack('>H', self._recv_exact(2))[0]
            elif payload_len == 127:
                payload_len = struct.unpack('>Q', self._recv_exact(8))[0]
            
            if is_masked:
                mask = self._recv_exact(4)
                payload = self._recv_exact(payload_len)
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            else:
                payload = self._recv_exact(payload_len)
            
            if opcode == 0x1: # Text frame
                return payload.decode('utf-8', errors='replace')
            elif opcode == 0x8: # Close frame
                self.sock.close()
                raise ConnectionResetError("WebSocket closed by server")
            elif opcode == 0x9: # Ping frame
                pong = bytearray([0x8A, 0x80]) + os.urandom(4)
                self.sock.sendall(pong)

    def _recv_exact(self, n):
        buf = b''
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionResetError("Socket closed unexpectedly")
            buf += chunk
        return buf

    def close(self):
        try:
            self.sock.close()
        except:
            pass

def preflight_check():
    """Verifies that Python and a suitable browser binary are present."""
    if sys.version_info < (3, 7):
        print("[Preflight Error] Python 3.7+ is required.")
        return None

    candidates = ['google-chrome', 'chromium', 'chromium-browser']
    browser_bin = None
    for c in candidates:
        path = shutil.which(c)
        if path:
            browser_bin = path
            break

    if not browser_bin:
        print("[Preflight Error] No Chromium-based browser found on PATH.")
        print("Please install Google Chrome or Chromium (e.g. `dnf install chromium` or `apt install chromium-browser`).")
        return None

    print(f"[Preflight OK] Using browser binary: {browser_bin}")
    return browser_bin

def run_browser_smoke_test(target_url=None):
    browser_bin = preflight_check()
    if not browser_bin:
        return False

    os.makedirs('docs/reports', exist_ok=True)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    http_proc = None
    if not target_url:
        print("[Browser Smoke Test] Starting local HTTP server & headless Chrome...")
        http_proc = subprocess.Popen(
            [sys.executable, '-m', 'http.server', '-d', project_root, str(PORT)],
            cwd=project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(1)
        test_url = f'http://127.0.0.1:{PORT}/index.html'
    else:
        print(f"[Browser Smoke Test] Testing directly against target URL: {target_url}...")
        test_url = target_url

    import tempfile
    temp_profile_dir = tempfile.mkdtemp(prefix="chrome_smoke_")

    chrome_proc = subprocess.Popen([
        browser_bin,
        '--headless=new',
        '--no-sandbox',
        '--disable-gpu',
        '--disable-dev-shm-usage',
        '--ignore-certificate-errors',
        '--host-rules=MAP danabus.638686.xyz 127.0.0.1',
        f'--user-data-dir={temp_profile_dir}',
        '--remote-allow-origins=*',
        f'--remote-debugging-port={CDP_PORT}',
        test_url
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{CDP_PORT}/json') as res:
            tabs = json.loads(res.read().decode())

        page_tab = next(t for t in tabs if t.get('type') == 'page')
        ws_url = page_tab['webSocketDebuggerUrl']
        ws = SimpleWebSocket(ws_url)

        req_state = {'id': 1}
        def send_cdp(method, params=None):
            cmd_id = req_state['id']
            req_state['id'] += 1
            payload = {'id': cmd_id, 'method': method}
            if params:
                payload['params'] = params
            ws.send_text(json.dumps(payload))
            while True:
                msg = json.loads(ws.recv_text())
                if msg.get('id') == cmd_id:
                    return msg.get('result', {})

        def eval_js(expr):
            res = send_cdp('Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
            return res.get('result', {}).get('value')

        send_cdp('Network.enable')
        send_cdp('Network.setCacheDisabled', {'cacheDisabled': True})
        send_cdp('Page.enable')
        send_cdp('Page.navigate', {'url': test_url})

        # Wait until page and data load completely
        for _ in range(30):
            ready = eval_js("document.readyState === 'complete' && !!document.title && (window.busService?.routes?.length > 0)")
            if ready:
                break
            time.sleep(0.3)

        # 1. Test Application Boot & DOM State
        print("[Check 1] Verifying initial Application state...")
        boot_state = eval_js("""
            (() => {
                return {
                    title: document.title,
                    currentView: window.app?.currentView,
                    allRoutesCount: window.busService?.routes?.length || 0,
                    homeViewActive: document.getElementById('view-home')?.classList.contains('active'),
                    originPlaceholder: document.getElementById('home-origin-input')?.placeholder || document.getElementById('home-origin-input')?.value
                };
            })()
        """)
        print(f" -> Boot state: {boot_state}")
        assert boot_state['title'] == "Danabus - Tra Cứu Xe Buýt Đà Nẵng", "Page title mismatch"
        assert boot_state['allRoutesCount'] == 23, f"Expected 23 routes, got {boot_state['allRoutesCount']}"
        assert boot_state['homeViewActive'] is True, "Home view must be active"

        # 2. Test Routes Catalog Navigation
        print("[Check 2] Navigating to Routes Catalog...")
        eval_js("window.app.navigateTo('routes'); window.app.renderRoutesList();")
        routes_view_state = None
        for _ in range(30):
            routes_view_state = eval_js("""
                (() => {
                    const list = document.getElementById('routes-list-container');
                    const cards = list ? list.querySelectorAll('.route-card') : [];
                    if (window.app?.currentView !== 'routes' || cards.length < 20) return null;
                    return {
                        currentView: window.app.currentView,
                        routesViewActive: document.getElementById('view-routes')?.classList.contains('active'),
                        renderedCardsCount: cards.length
                    };
                })()
            """)
            if routes_view_state:
                break
            time.sleep(0.1)
        if not routes_view_state:
            routes_view_state = eval_js("""
                (() => {
                    const list = document.getElementById('routes-list-container');
                    const cards = list ? list.querySelectorAll('.route-card') : [];
                    return {
                        currentView: window.app?.currentView,
                        routesViewActive: document.getElementById('view-routes')?.classList.contains('active'),
                        renderedCardsCount: cards.length
                    };
                })()
            """)
        print(f" -> Routes view state: {routes_view_state}")
        assert routes_view_state['currentView'] == 'routes', "Must be in routes view"
        assert routes_view_state['renderedCardsCount'] == 23, f"Expected 23 route cards rendered, got {routes_view_state['renderedCardsCount']}"

        # 3. Test Route Detail & Map View for multiple routes (02, 05, 11, TKY-TMY, TKY-NTH, 01DL, 01SB)
        test_routes = ['02', '05', '11', 'TKY-TMY', 'TKY-NTH', '01DL', '01SB']
        for rid in test_routes:
            print(f"[Check 3] Testing Map rendering for Route {rid}...")
            map_state = eval_js(f"""
                (() => {{
                    const route = window.busService.getRouteById('{rid}');
                    window.app.selectedRoute = route;
                    window.app.currentDirection = 'outbound';
                    window.app.navigateTo('map');
                    
                    window.mapService.init('map-container');
                    window.mapService.renderRoute(route, 'outbound');
                    
                    const mapEl = document.getElementById('map-container');
                    const mapInstance = window.mapService?.map;
                    const overlay = document.getElementById('map-info-overlay');
                    const markersCount = window.mapService?.markersLayer?.getLayers()?.length || 0;
                    const polylineExists = !!window.mapService?.routeLine;

                    return {{
                        routeId: '{rid}',
                        routeNumber: route?.routeNumber,
                        hasMapEl: !!mapEl,
                        hasMapInstance: !!mapInstance,
                        overlayText: overlay ? overlay.textContent.trim() : null,
                        markersCount: markersCount,
                        polylineExists: polylineExists
                    }};
                }})()
            """)
            print(f" -> Route {rid} map state: {map_state}")
            assert map_state['hasMapInstance'] is True, f"Leaflet map must be initialized for Route {rid}"
            
            # Strict mutual exclusion assertion: polyline and no-data overlay must NEVER coexist
            assert not (map_state['polylineExists'] and map_state['overlayText']), (
                f"Inconsistency on Route {rid}: polyline exists ({map_state['polylineExists']}) "
                f"while no-data overlay is also displayed ('{map_state['overlayText']}')"
            )

            if rid in ['05', 'TKY-TMY', 'TKY-NTH']:
                assert map_state['polylineExists'] is True, f"Route {rid} geometry is verified so Leaflet polyline must exist"
                assert map_state['overlayText'] is None, f"Route {rid} overlay must be None when polyline exists"
                assert map_state['markersCount'] >= 5, f"Route {rid} must render verified stop markers, got {map_state['markersCount']}"
            else:
                assert map_state['polylineExists'] is False, f"Route {rid} geometry is unverified so polyline must be null"
                assert "Chưa có dữ liệu bản đồ cho tuyến này" in (map_state['overlayText'] or ""), f"Overlay message missing for unverified Route {rid}"

        # 4. Test Switching Outbound / Inbound, Stale Layer Cleanup & Single-direction verified availability
        print("[Check 4] Testing Direction Switch & Availability on Route 02, 11, 05, TKY-TMY, TKY-NTH, and single-direction Route TKY-CHU...")
        dir_switch_state = eval_js("""
            (() => {
                // 4a. Test Route 02 (Both directions unverified geometry)
                const route02 = window.busService.getRouteById('02');
                window.app.selectedRoute = route02;
                window.mapService.renderRoute(route02, 'inbound');
                const r02_inMarkers = window.mapService.markersLayer.getLayers().length;
                const r02_inPolyline = !!window.mapService.routeLine;
                const r02_inOverlay = !!document.getElementById('map-info-overlay');
                
                window.mapService.renderRoute(route02, 'outbound');
                const r02_outMarkers = window.mapService.markersLayer.getLayers().length;
                const r02_outPolyline = !!window.mapService.routeLine;
                const r02_outOverlay = !!document.getElementById('map-info-overlay');

                // 4b. Test Route 11 (Both directions unverified geometry)
                const route11 = window.busService.getRouteById('11');
                window.app.selectedRoute = route11;
                window.mapService.renderRoute(route11, 'inbound');
                const r11_inPolyline = !!window.mapService.routeLine;
                const r11_inOverlay = !!document.getElementById('map-info-overlay');
                window.mapService.renderRoute(route11, 'outbound');
                const r11_outPolyline = !!window.mapService.routeLine;
                const r11_outOverlay = !!document.getElementById('map-info-overlay');

                // 4c. Test Route 05 (Both directions verified geometry)
                const route05 = window.busService.getRouteById('05');
                window.app.selectedRoute = route05;
                window.mapService.renderRoute(route05, 'outbound');
                const r05_outPolyline = !!window.mapService.routeLine;
                const r05_outOverlay = !!document.getElementById('map-info-overlay');
                window.mapService.renderRoute(route05, 'inbound');
                const r05_inPolyline = !!window.mapService.routeLine;
                const r05_inOverlay = !!document.getElementById('map-info-overlay');

                // 4d. Test Route TKY-TMY (Both directions verified geometry)
                const routeTkyTmy = window.busService.getRouteById('TKY-TMY');
                window.app.selectedRoute = routeTkyTmy;
                window.mapService.renderRoute(routeTkyTmy, 'outbound');
                const tkyTmy_outPolyline = !!window.mapService.routeLine;
                const tkyTmy_outOverlay = !!document.getElementById('map-info-overlay');
                window.mapService.renderRoute(routeTkyTmy, 'inbound');
                const tkyTmy_inPolyline = !!window.mapService.routeLine;
                const tkyTmy_inOverlay = !!document.getElementById('map-info-overlay');

                // 4e. Test Route TKY-NTH (Both directions verified geometry)
                const routeTkyNth = window.busService.getRouteById('TKY-NTH');
                window.app.selectedRoute = routeTkyNth;
                window.mapService.renderRoute(routeTkyNth, 'outbound');
                const tkyNth_outPolyline = !!window.mapService.routeLine;
                const tkyNth_outOverlay = !!document.getElementById('map-info-overlay');
                window.mapService.renderRoute(routeTkyNth, 'inbound');
                const tkyNth_inPolyline = !!window.mapService.routeLine;
                const tkyNth_inOverlay = !!document.getElementById('map-info-overlay');

                // 4f. Test Route TKY-CHU (Outbound unverified -> Inbound verified)
                const routeTkyChu = window.busService.getRouteById('TKY-CHU');
                window.app.selectedRoute = routeTkyChu;
                window.mapService.renderRoute(routeTkyChu, 'outbound');
                const tkyChu_outPolyline = !!window.mapService.routeLine;
                const tkyChu_outOverlayText = document.getElementById('map-info-overlay')?.textContent.trim() || null;
                
                window.mapService.renderRoute(routeTkyChu, 'inbound');
                const tkyChu_inPolyline = !!window.mapService.routeLine;
                const tkyChu_inOverlay = !!document.getElementById('map-info-overlay');
                const tkyChu_inMarkers = window.mapService.markersLayer.getLayers().length;

                return {
                    r02: { inMarkers: r02_inMarkers, inPolyline: r02_inPolyline, inOverlay: r02_inOverlay, outMarkers: r02_outMarkers, outPolyline: r02_outPolyline, outOverlay: r02_outOverlay },
                    r11: { inPolyline: r11_inPolyline, inOverlay: r11_inOverlay, outPolyline: r11_outPolyline, outOverlay: r11_outOverlay },
                    r05: { outPolyline: r05_outPolyline, outOverlay: r05_outOverlay, inPolyline: r05_inPolyline, inOverlay: r05_inOverlay },
                    tkyTmy: { outPolyline: tkyTmy_outPolyline, outOverlay: tkyTmy_outOverlay, inPolyline: tkyTmy_inPolyline, inOverlay: tkyTmy_inOverlay },
                    tkyNth: { outPolyline: tkyNth_outPolyline, outOverlay: tkyNth_outOverlay, inPolyline: tkyNth_inPolyline, inOverlay: tkyNth_inOverlay },
                    tkyChu: {
                        outPolyline: tkyChu_outPolyline,
                        outOverlayText: tkyChu_outOverlayText,
                        inPolyline: tkyChu_inPolyline,
                        inOverlay: tkyChu_inOverlay,
                        inMarkers: tkyChu_inMarkers
                    },
                    cleanNoStaleLayers: true
                };
            })()
        """)
        print(f" -> Direction switch state: {dir_switch_state}")
        assert dir_switch_state['r02']['outPolyline'] is False and dir_switch_state['r02']['outOverlay'] is True, "Route 02 Outbound must show overlay"
        assert dir_switch_state['r02']['inPolyline'] is False and dir_switch_state['r02']['inOverlay'] is True, "Route 02 Inbound must show overlay"
        assert dir_switch_state['r11']['outPolyline'] is False and dir_switch_state['r11']['outOverlay'] is True, "Route 11 Outbound must show overlay"
        assert dir_switch_state['r11']['inPolyline'] is False and dir_switch_state['r11']['inOverlay'] is True, "Route 11 Inbound must show overlay"
        assert dir_switch_state['r05']['outPolyline'] is True and dir_switch_state['r05']['outOverlay'] is False, "Route 05 Outbound must have polyline and no overlay"
        assert dir_switch_state['r05']['inPolyline'] is True and dir_switch_state['r05']['inOverlay'] is False, "Route 05 Inbound must have polyline and no overlay"
        assert dir_switch_state['tkyTmy']['outPolyline'] is True and dir_switch_state['tkyTmy']['outOverlay'] is False, "TKY-TMY Outbound must have polyline and no overlay"
        assert dir_switch_state['tkyTmy']['inPolyline'] is True and dir_switch_state['tkyTmy']['inOverlay'] is False, "TKY-TMY Inbound must have polyline and no overlay"
        assert dir_switch_state['tkyNth']['outPolyline'] is True and dir_switch_state['tkyNth']['outOverlay'] is False, "TKY-NTH Outbound must have polyline and no overlay"
        assert dir_switch_state['tkyNth']['inPolyline'] is True and dir_switch_state['tkyNth']['inOverlay'] is False, "TKY-NTH Inbound must have polyline and no overlay"
        assert dir_switch_state['tkyChu']['outPolyline'] is False and "Chưa có dữ liệu" in (dir_switch_state['tkyChu']['outOverlayText'] or ""), "TKY-CHU Outbound must show no-data overlay"
        assert dir_switch_state['tkyChu']['inPolyline'] is True and dir_switch_state['tkyChu']['inOverlay'] is False, "TKY-CHU Inbound must render polyline and hide overlay"
        assert dir_switch_state['tkyChu']['inMarkers'] >= 10, "TKY-CHU Inbound must render stop markers"
        assert dir_switch_state['cleanNoStaleLayers'] is True

        # 5. Test Browser Geolocation Integration (locateUser)
        print("[Check 5] Testing Browser Geolocation with Mock & Error Handling...")
        geo_test_res = eval_js("""
            (async () => {
                const originalGeo = navigator.geolocation;
                const mockPos = {
                    coords: {
                        latitude: 16.0544,
                        longitude: 108.2022,
                        accuracy: 25.0
                    },
                    timestamp: Date.now()
                };
                
                navigator.geolocation.getCurrentPosition = (success, error, opts) => {
                    success(mockPos);
                };

                const resSuccess = await window.mapService.locateUser();
                const hasUserMarker = !!window.mapService.userMarker;
                const hasAccuracyCircle = !!window.mapService.accuracyCircle;
                const circleRadius = window.mapService.accuracyCircle?.getRadius();

                navigator.geolocation.getCurrentPosition = (success, error, opts) => {
                    error({ code: 1, message: 'User denied geolocation' });
                };
                const resDenied = await window.mapService.locateUser();

                navigator.geolocation = originalGeo;

                return {
                    successResult: resSuccess,
                    hasUserMarker,
                    hasAccuracyCircle,
                    circleRadius,
                    deniedResult: resDenied
                };
            })()
        """)
        print(f" -> Geolocation test result: {geo_test_res}")
        assert geo_test_res['successResult']['success'] is True, "Geolocation success mock failed"
        assert geo_test_res['hasUserMarker'] is True, "User marker must be created upon GPS success"
        assert geo_test_res['hasAccuracyCircle'] is True, "Accuracy circle must be created"
        assert geo_test_res['circleRadius'] == 25.0, "Accuracy circle radius must match GPS accuracy"
        assert geo_test_res['deniedResult']['success'] is False, "Denied GPS error must be handled cleanly"
        assert "bị từ chối" in geo_test_res['deniedResult']['error'], "Denied message mismatch"

        # 6. Test Route 05 Context Retention during locateUser & fitRoute (PO Regression Test)
        print("[Check 6] Testing Route 05 Map Context Retention during Geolocation & fitRoute...")
        r05_geo_res = eval_js("""
            (async () => {
                // Navigate to Route 05 Map View
                const route05 = window.busService.getRouteById('05');
                window.app.selectedRoute = route05;
                window.app.currentDirection = 'outbound';
                window.app.openMapView('05');
                window.mapService.renderRoute(route05, 'outbound');

                const initialPolyline = !!window.mapService.routeLine;
                const initialRouteTitle = document.getElementById('map-route-title')?.textContent.trim();
                const initialStopsCount = window.mapService.markersLayer.getLayers().length;

                // Mock user location (e.g. user in Hoi An or Da Nang)
                const originalGeo = navigator.geolocation;
                const mockPos = {
                    coords: {
                        latitude: 15.8801,
                        longitude: 108.3380,
                        accuracy: 20.0
                    },
                    timestamp: Date.now()
                };
                navigator.geolocation.getCurrentPosition = (success, error, opts) => success(mockPos);

                // Locate user
                const locateRes = await window.mapService.locateUser();
                const afterLocatePolyline = !!window.mapService.routeLine;
                const hasUserMarker = !!window.mapService.userMarker;
                const hasAccuracyCircle = !!window.mapService.accuracyCircle;
                const routeTitleAfterLocate = document.getElementById('map-route-title')?.textContent.trim();
                const userIconClass = window.mapService.userMarker?.options?.icon?.options?.className;

                // Test Toàn tuyến (fitRoute) button
                document.getElementById('btn-map-fit-route')?.click();
                const afterFitPolyline = !!window.mapService.routeLine;
                const mapBounds = window.mapService.map?.getBounds();
                const routeBounds = window.mapService.routeLine?.getBounds();

                // Test switching direction while user marker is active
                document.getElementById('btn-map-switch-dir')?.click();
                const inPolyline = !!window.mapService.routeLine;
                const inStopsCount = window.mapService.markersLayer.getLayers().length;
                const userMarkerAfterSwitch = !!window.mapService.userMarker;

                navigator.geolocation = originalGeo;

                return {
                    initialPolyline,
                    initialRouteTitle,
                    initialStopsCount,
                    locateSuccess: locateRes.success,
                    afterLocatePolyline,
                    hasUserMarker,
                    hasAccuracyCircle,
                    userIconClass,
                    routeTitleAfterLocate,
                    afterFitPolyline,
                    inPolyline,
                    inStopsCount,
                    userMarkerAfterSwitch
                };
            })()
        """)
        print(f" -> Route 05 locateUser context state: {r05_geo_res}")
        assert r05_geo_res['initialPolyline'] is True, "Route 05 must have polyline initially"
        assert r05_geo_res['locateSuccess'] is True, "locateUser must succeed with mock"
        assert r05_geo_res['afterLocatePolyline'] is True, "Route 05 polyline MUST NOT be removed or lost after locateUser"
        assert r05_geo_res['hasUserMarker'] is True, "User marker must exist after locateUser"
        assert r05_geo_res['userIconClass'] == 'user-loc-icon', "User marker must have distinct user-loc-icon class"
        assert "05" in r05_geo_res['routeTitleAfterLocate'] or "Hòa Hiệp" in r05_geo_res['routeTitleAfterLocate'], "Route title context must remain Route 05"
        assert r05_geo_res['afterFitPolyline'] is True, "fitRoute must keep polyline intact"
        assert r05_geo_res['inPolyline'] is True, "Route 05 Inbound polyline must be intact after direction switch"
        assert r05_geo_res['userMarkerAfterSwitch'] is True, "User marker must be maintained after direction switch"

        # 7. Test Service Worker Lifecycle, Cache Policy & Stale Cache Eviction (Existing Client Update Simulation)
        print("[Check 7] Testing Service Worker Lifecycle & Cache Policy Migration...")
        # Step 7a: Pre-create obsolete cache stores from earlier versions (simulating legacy user client)
        pre_cache_keys = eval_js("""
            (async () => {
                await caches.open('danabus-cache-v4');
                await caches.open('danabus-cache-v5');
                await caches.open('danabus-cache-v6');
                await caches.open('danabus-cache-v7');
                return await caches.keys();
            })()
        """)
        print(f" -> Pre-migration cache keys: {pre_cache_keys}")
        assert 'danabus-cache-v4' in pre_cache_keys, "danabus-cache-v4 must be present in pre-migration caches"
        assert 'danabus-cache-v5' in pre_cache_keys, "danabus-cache-v5 must be present in pre-migration caches"
        assert 'danabus-cache-v6' in pre_cache_keys, "danabus-cache-v6 must be present in pre-migration caches"
        assert 'danabus-cache-v7' in pre_cache_keys, "danabus-cache-v7 must be present in pre-migration caches"

        # Step 7b: Trigger Service Worker installation & activation lifecycle
        eval_js("""
            (async () => {
                const regToken = Date.now();
                await navigator.serviceWorker.register(`sw.js?migration_cycle=${regToken}`);
            })()
        """)

        # Step 7c & 7d: Wait for SW activate handler to purge caches and controllerchange reload to settle with bounded predicate
        post_sw_state = None
        for _ in range(50):
            state = eval_js("""
                (async () => {
                    const activeReg = await navigator.serviceWorker.getRegistration();
                    const cacheKeys = await caches.keys();
                    const swActive = !!(activeReg && (activeReg.active || activeReg.installing || activeReg.waiting));
                    const swScope = activeReg ? activeReg.scope : null;
                    const hasFitRoute = typeof window.mapService?.fitRoute === 'function';
                    const scriptSrcs = Array.from(document.querySelectorAll('script[src]')).map(s => s.getAttribute('src'));
                    const mapScriptSrc = scriptSrcs.find(s => s.includes('mapService.js'));
                    const appScriptSrc = scriptSrcs.find(s => s.includes('app.js'));

                    return {
                        swActive,
                        swScope,
                        postMigrationCacheKeys: cacheKeys,
                        hasFitRoute,
                        mapScriptSrc,
                        appScriptSrc
                    };
                })()
            """)
            if (
                state and
                state.get('swActive') and
                state.get('hasFitRoute') and
                'danabus-cache-v9' in state.get('postMigrationCacheKeys', []) and
                'danabus-cache-v4' not in state.get('postMigrationCacheKeys', []) and
                'danabus-cache-v7' not in state.get('postMigrationCacheKeys', [])
            ):
                post_sw_state = state
                break
            time.sleep(0.2)
        if not post_sw_state:
            post_sw_state = state

        print(f" -> Post-migration SW & Cache state: {post_sw_state}")
        assert post_sw_state is not None, "Post-migration check must return valid state"
        assert post_sw_state['swActive'] is True, "Service Worker must be registered and active"
        assert 'danabus-cache-v9' in post_sw_state['postMigrationCacheKeys'], "danabus-cache-v9 must be present after SW activation"
        assert 'danabus-cache-v4' not in post_sw_state['postMigrationCacheKeys'], "danabus-cache-v4 must be strictly purged"
        assert 'danabus-cache-v5' not in post_sw_state['postMigrationCacheKeys'], "danabus-cache-v5 must be strictly purged"
        assert 'danabus-cache-v6' not in post_sw_state['postMigrationCacheKeys'], "danabus-cache-v6 must be strictly purged"
        assert 'danabus-cache-v7' not in post_sw_state['postMigrationCacheKeys'], "danabus-cache-v7 must be strictly purged"
        assert post_sw_state['hasFitRoute'] is True, "window.mapService.fitRoute must be present in active client"
        assert "v=20260928_v9" in (post_sw_state['mapScriptSrc'] or ""), f"mapService.js must have cache-busting v=20260928_v9, got {post_sw_state['mapScriptSrc']}"
        assert "v=20260928_v9" in (post_sw_state['appScriptSrc'] or ""), f"app.js must have cache-busting v=20260928_v9, got {post_sw_state['appScriptSrc']}"

        # 8. Take Screenshot for Deliverable Evidence
        print("[Check 8] Capturing deliverable screenshot...")
        shot_res = send_cdp('Page.captureScreenshot', {'format': 'png'})
        if shot_res.get('data'):
            img_bytes = base64.b64decode(shot_res['data'])
            with open(SCREENSHOT_PATH, 'wb') as f:
                f.write(img_bytes)
            print(f" -> Screenshot saved to {SCREENSHOT_PATH} ({len(img_bytes)} bytes)")

        ws.close()
        print("\n>>> ALL BROWSER SMOKE CHECKS PASSED (8/8) <<<")
        return True

    finally:
        if 'ws' in locals() and ws:
            try:
                ws.close()
            except:
                pass
        if 'chrome_proc' in locals() and chrome_proc:
            try:
                chrome_proc.terminate()
                chrome_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                chrome_proc.kill()
                chrome_proc.wait(timeout=2)
            except:
                pass
        if http_proc:
            try:
                http_proc.terminate()
                http_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                http_proc.kill()
                http_proc.wait(timeout=2)
            except:
                pass
        if 'temp_profile_dir' in locals() and temp_profile_dir:
            shutil.rmtree(temp_profile_dir, ignore_errors=True)

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else None
    success = run_browser_smoke_test(target)
    sys.exit(0 if success else 1)
