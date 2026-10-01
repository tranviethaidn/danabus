#!/usr/bin/env python3
"""
Browser Integration Test Suite for Address-to-Address Trip Planner (Task 4)
Uses Headless Chrome + Chrome DevTools Protocol (CDP) to verify:
1. End-to-end address/POI selection in location picker
2. Multi-leg trip planning execution and results rendering
3. Trip ranking badges (Tuyến trực tiếp, Ít đi bộ nhất, Nhanh nhất)
4. Leaflet multi-leg map rendering (walking dashed lines, bus polyline, marker pins)
5. Non-stale swap locations behavior
6. Fail-closed empty state for disconnected endpoints
7. Deliverable screenshot generation
"""

import os
import sys
import time
import json
import base64
import socket
import urllib.request
import subprocess
import argparse
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
DEFAULT_SCREENSHOT_PATH = WORKSPACE / "docs" / "reports" / "task4_trip_planner_evidence.png"

class SimpleWebSocket:
    def __init__(self, url):
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        self.host = parsed.hostname
        self.port = parsed.port or 80
        self.path = parsed.path or "/"
        self.sock = socket.create_connection((self.host, self.port), timeout=15)
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
        while True:
            header = self.sock.recv(2)
            if not header or len(header) < 2:
                raise ConnectionError("Socket closed")
            b1, b2 = header[0], header[1]
            length = b2 & 0x7f
            if length == 126:
                length = int.from_bytes(self.sock.recv(2), 'big')
            elif length == 127:
                length = int.from_bytes(self.sock.recv(8), 'big')
            body = b""
            while len(body) < length:
                chunk = self.sock.recv(length - len(body))
                if not chunk:
                    break
                body += chunk
            return body.decode('utf-8', errors='replace')

    def close(self):
        try:
            self.sock.close()
        except:
            pass


class ChromeRunner:
    def __init__(self, port=9333, http_port=8181):
        self.port = port
        self.http_port = http_port
        self.chrome_proc = None
        self.http_proc = None
        self.ws = None
        self.msg_id = 0

    def start(self):
        self.http_proc = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(self.http_port)],
            cwd=WORKSPACE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(0.5)

        chrome_cmd = [
            "chromium-browser",
            "--headless=new",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            f"--remote-debugging-port={self.port}",
            "--window-size=1280,900"
        ]
        self.chrome_proc = subprocess.Popen(chrome_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.0)

        tabs_url = f"http://127.0.0.1:{self.port}/json"
        ws_url = None
        for _ in range(20):
            try:
                with urllib.request.urlopen(tabs_url, timeout=2) as r:
                    tabs = json.loads(r.read().decode())
                    if tabs:
                        ws_url = tabs[0]["webSocketDebuggerUrl"]
                        break
            except:
                time.sleep(0.2)
        if not ws_url:
            raise RuntimeError("Failed to obtain Chrome CDP WebSocket URL")

        test_url = f"http://127.0.0.1:{self.http_port}/index.html"
        self.ws = SimpleWebSocket(ws_url)
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("Page.navigate", {"url": test_url})

        for _ in range(30):
            ready = self.evaluate("document.readyState === 'complete' && !!document.title && (window.busService?.routes?.length > 0)")
            if ready:
                break
            time.sleep(0.3)
        time.sleep(0.5)

    def call(self, method, params=None):
        self.msg_id += 1
        curr_id = self.msg_id
        req = {"id": curr_id, "method": method, "params": params or {}}
        self.ws.send_text(json.dumps(req))
        while True:
            raw = self.ws.recv_text()
            res = json.loads(raw)
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
        return res.get("result", {}).get("value")

    def capture_screenshot(self, output_path):
        res = self.call("Page.captureScreenshot", {"format": "png"})
        b64 = res.get("data", "")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(b64))

    def stop(self):
        if self.ws: self.ws.close()
        if self.chrome_proc:
            self.chrome_proc.terminate()
            self.chrome_proc.wait()
        if self.http_proc:
            self.http_proc.terminate()
            self.http_proc.wait()


def run_browser_checks(screenshot_path=None):
    runner = ChromeRunner()
    print("[Browser Test] Launching Headless Chrome for Task 4...")
    runner.start()
    try:
        # Check 1: Location Manager & POI Autocomplete in Browser DOM
        runner.evaluate("window.app.openLocationPicker('origin')")
        time.sleep(0.2)
        runner.evaluate("document.getElementById('picker-search-input').value = 'Bách Khoa'")
        runner.evaluate("window.app.renderPickerResults('Bách Khoa')")
        time.sleep(0.3)
        picker_first_item = runner.evaluate("document.querySelector('.picker-item')?.getAttribute('data-name')")
        print(f"[Check 1] Location Picker Search for 'Bách Khoa': {picker_first_item}")
        assert picker_first_item and "Bách Khoa" in picker_first_item, f"Expected Bách Khoa POI, got: {picker_first_item}"

        # Check 2: Execute Trip Planning (Đại học Bách Khoa -> Công viên Biển Đông)
        runner.evaluate("""
        (() => {
            window.app.showTripResults('Trường Đại học Bách Khoa - ĐHĐN', 'Công viên Biển Đông');
        })()
        """)
        time.sleep(0.5)

        trip_view_active = runner.evaluate("document.getElementById('view-trip-results').classList.contains('active')")
        options_count = runner.evaluate("document.querySelectorAll('#trip-planner-options .bg-white').length")
        first_badge = runner.evaluate("document.querySelector('#trip-planner-options .bg-white span')?.textContent?.trim()")
        print(f"[Check 2] Trip Results Screen: Active={trip_view_active}, Options Count={options_count}, First Badge='{first_badge}'")
        assert trip_view_active, "Trip results screen must be active"
        assert options_count > 0, "Planned trip options must be rendered"
        assert first_badge in ["Tuyến trực tiếp", "Ít đi bộ nhất", "Nhanh nhất"], f"Unexpected badge: {first_badge}"

        # Check 3: Leaflet Multi-Leg Rendering (Trigger 'Bản đồ' on First Option)
        runner.evaluate("document.querySelector('.btn-view-planned-map')?.click()")
        time.sleep(0.5)
        map_view_active = runner.evaluate("document.getElementById('view-map').classList.contains('active')")
        has_orig_marker = runner.evaluate("document.querySelectorAll('.trip-origin-marker').length > 0")
        has_dest_marker = runner.evaluate("document.querySelectorAll('.trip-dest-marker').length > 0")
        trip_polylines_count = runner.evaluate("window.mapService.tripPolylines.length")
        print(f"[Check 3] Multi-Leg Map View: Active={map_view_active}, OriginMarker={has_orig_marker}, DestMarker={has_dest_marker}, Polylines={trip_polylines_count}")
        assert map_view_active, "Map view must be active after clicking Bản đồ"
        assert has_orig_marker and has_dest_marker, "Origin (A) and Destination (B) markers must be rendered"
        assert trip_polylines_count >= 2, f"Expected walking and transit polylines, got: {trip_polylines_count}"

        # Check 4: Non-Stale Location Swap
        runner.evaluate("window.app.navigateTo('trip-results')")
        time.sleep(0.2)
        runner.evaluate("document.getElementById('btn-trip-swap')?.click()")
        time.sleep(0.5)
        swapped_title = runner.evaluate("document.getElementById('trip-header-title')?.textContent")
        print(f"[Check 4] Swapped Trip Title: {swapped_title}")
        assert "Công viên Biển Đông ➔ Trường Đại học Bách Khoa" in swapped_title

        # Check 5: Disjoint Fail-Closed Empty State
        runner.evaluate("window.app.showTripResults('Bến xe TT', 'Hà Nội')")
        time.sleep(0.3)
        empty_visible = runner.evaluate("!document.getElementById('trip-content-empty').classList.contains('hidden')")
        success_hidden = runner.evaluate("document.getElementById('trip-content-success').classList.contains('hidden')")
        print(f"[Check 5] Fail-Closed Disjoint Query: EmptyVisible={empty_visible}, SuccessHidden={success_hidden}")
        assert empty_visible and success_hidden, "Disjoint city endpoints must fail-closed to empty state"

        # Check 6: Deliverable Screenshot
        runner.evaluate("window.app.showTripResults('Trường Đại học Bách Khoa - ĐHĐN', 'Công viên Biển Đông')")
        time.sleep(0.5)
        runner.evaluate("document.querySelector('.btn-view-planned-map')?.click()")
        time.sleep(0.5)
        target_shot = Path(screenshot_path) if screenshot_path else DEFAULT_SCREENSHOT_PATH
        target_shot.parent.mkdir(parents=True, exist_ok=True)
        runner.capture_screenshot(target_shot)
        print(f"[Check 6] Deliverable screenshot saved to {target_shot} ({os.path.getsize(target_shot)} bytes)")

        print("\n>>> ALL TASK 4 BROWSER ACCEPTANCE CHECKS PASSED (6/6) <<<")
    finally:
        runner.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Browser Trip Planner Acceptance Test")
    parser.add_argument("--screenshot-path", default=None, help="Custom screenshot destination")
    args = parser.parse_args()
    run_browser_checks(screenshot_path=args.screenshot_path)
