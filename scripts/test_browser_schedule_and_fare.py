#!/usr/bin/env python3
"""
Browser Integration Test for Task 7: Schedule & Fare Correctness
Uses Headless Chrome via CDP over WebSocket to test actual DOM in the browser.
Verifies:
- Spotlight dynamic fare & schedule status
- Routes catalog fare display (tiered, flat, unknown)
- Route detail fare rendering and tag semantics (Theo chặng, Trợ giá, Đang cập nhật)
- Trip search results fare & countdown rendering without fake values
- Captures deliverable screenshot to docs/reports/task7_schedule_fare_evidence.png
"""

import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
PORT = 8992
CDP_PORT = 9445
SCREENSHOT_PATH = WORKSPACE / "docs" / "reports" / "task7_schedule_fare_evidence.png"


class SimpleWebSocket:
    def __init__(self, ws_url):
        rest = ws_url[5:]
        host_port, path = rest.split('/', 1)
        path = '/' + path
        host, port = host_port.split(':') if ':' in host_port else (host_port, 80)
        self.sock = socket.create_connection((host, int(port)), timeout=10)
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
        if length <= 125:
            header = bytes([0x81, 0x80 | length]) + mask
        elif length <= 65535:
            header = bytes([0x81, 0x80 | 126]) + struct.pack('>H', length) + mask
        else:
            header = bytes([0x81, 0x80 | 127]) + struct.pack('>Q', length) + mask
        masked_data = bytearray(length)
        for i in range(length):
            masked_data[i] = data[i] ^ mask[i % 4]
        self.sock.sendall(header + masked_data)

    def recv_text(self):
        def recv_exact(n):
            buf = bytearray()
            while len(buf) < n:
                chunk = self.sock.recv(n - len(buf))
                if not chunk:
                    raise ConnectionError("Socket closed prematurely")
                buf.extend(chunk)
            return bytes(buf)

        while True:
            b1, b2 = struct.unpack('BB', recv_exact(2))
            is_masked = bool(b2 & 0x80)
            payload_len = b2 & 0x7F
            if payload_len == 126:
                payload_len = struct.unpack('>H', recv_exact(2))[0]
            elif payload_len == 127:
                payload_len = struct.unpack('>Q', recv_exact(8))[0]

            mask = recv_exact(4) if is_masked else None
            payload = bytearray(recv_exact(payload_len))
            if is_masked:
                for i in range(payload_len):
                    payload[i] ^= mask[i % 4]

            opcode = b1 & 0x0F
            if opcode == 1:
                return payload.decode('utf-8', errors='replace')
            elif opcode == 8:
                self.sock.close()
                raise ConnectionError("Server closed connection")
            elif opcode == 9:
                self.sock.sendall(bytes([0x8A, 0x00]))

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


class ChromeRunner:
    def __init__(self):
        self.http_proc = None
        self.chrome_proc = None
        self.ws = None
        self.msg_id = 0

    def start(self):
        import tempfile
        self.profile_dir = tempfile.mkdtemp(prefix="danabus_test_profile_")

        # 1. Start Python HTTP Server
        self.http_proc = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(PORT)],
            cwd=WORKSPACE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(0.5)

        # 2. Start Headless Chrome
        chrome_bin = "/bin/google-chrome"
        test_url = f"http://127.0.0.1:{PORT}/index.html"
        self.chrome_proc = subprocess.Popen(
            [
                chrome_bin,
                "--headless=new",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--ignore-certificate-errors",
                f"--user-data-dir={self.profile_dir}",
                "--remote-allow-origins=*",
                f"--remote-debugging-port={CDP_PORT}",
                test_url
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(1.5)

        # 3. Connect CDP
        cdp_url = f"http://127.0.0.1:{CDP_PORT}/json"
        ws_url = None
        for _ in range(30):
            try:
                with urllib.request.urlopen(cdp_url, timeout=1) as resp:
                    tabs = json.loads(resp.read().decode())
                    page_tabs = [t for t in tabs if t.get('type') == 'page']
                    if page_tabs and "webSocketDebuggerUrl" in page_tabs[0]:
                        ws_url = page_tabs[0]["webSocketDebuggerUrl"]
                        break
            except Exception:
                time.sleep(0.2)
        if not ws_url:
            raise RuntimeError("Failed to connect to Chrome CDP")

        self.ws = SimpleWebSocket(ws_url)
        self.call("Network.enable")
        self.call("Network.setCacheDisabled", {"cacheDisabled": True})
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("Page.navigate", {"url": test_url})

        # Wait until page and data load completely
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
        if self.ws:
            self.ws.close()
        if self.chrome_proc:
            self.chrome_proc.terminate()
            self.chrome_proc.wait()
        if self.http_proc:
            self.http_proc.terminate()
            self.http_proc.wait()


def run_checks():
    runner = ChromeRunner()
    print("[Browser Test] Launching Headless Chrome & connecting CDP...")
    runner.start()
    try:
        # Check 1: Spotlight card fare, schedule subtitle & countdown
        spotlight_fare = runner.evaluate("document.getElementById('spotlight-fare')?.textContent")
        spotlight_schedule = runner.evaluate("document.getElementById('spotlight-schedule')?.textContent")
        spotlight_countdown = runner.evaluate("document.getElementById('spotlight-countdown')?.textContent")
        print(f"[Check 1] Spotlight Fare: {spotlight_fare}, Schedule: {spotlight_schedule}, Countdown: {spotlight_countdown}")
        assert spotlight_fare == "8.000đ - 30.000đ", f"Unexpected spotlight fare: {spotlight_fare}"
        assert spotlight_schedule and "15-30 phút" in spotlight_schedule and "05:15 - 18:30" in spotlight_schedule, f"Spotlight schedule error: {spotlight_schedule}"
        assert "Tần suất 15 phút •" not in spotlight_schedule, f"Hardcoded 15 phút detected in spotlight schedule: {spotlight_schedule}"
        assert spotlight_countdown and "6 phút" not in spotlight_countdown, f"Fake placeholder detected: {spotlight_countdown}"

        # Check 2: Routes Catalog Fares & Frequency
        runner.evaluate("window.app.navigateTo('routes')")
        time.sleep(0.5)
        routes_data = runner.evaluate("""
        (() => {
            const cards = document.querySelectorAll('.route-card');
            const map = {};
            cards.forEach(c => {
                const id = c.getAttribute('data-route-id');
                const fareSpan = c.querySelector('.text-emerald-700');
                const textNodes = Array.from(c.querySelectorAll('.text-slate-500 span')).map(s => s.textContent.trim());
                if (id && fareSpan) {
                    map[id] = {
                        fare: fareSpan.textContent.trim(),
                        freq: textNodes.find(t => t.includes('/chuyến') || t.includes('Lịch bay') || t.includes('Đang cập nhật')) || ''
                    };
                }
            });
            return map;
        })()
        """)
        print("[Check 2] Catalog routes sampled data:")
        print(f"  Route 02: {routes_data.get('02')}")
        print(f"  Route 06: {routes_data.get('06')}")
        print(f"  Route 05: {routes_data.get('05')}")
        print(f"  Route 09: {routes_data.get('09')}")
        print(f"  Route 13: {routes_data.get('13')}")
        print(f"  Route LK01: {routes_data.get('LK01')}")
        print(f"  Route 01SB: {routes_data.get('01SB')}")

        assert routes_data.get("02", {}).get("fare") == "8.000đ - 30.000đ", f"Route 02 fare error: {routes_data.get('02')}"
        assert routes_data.get("02", {}).get("freq") == "15-30p/chuyến", f"Route 02 catalog frequency error: {routes_data.get('02')}"
        assert routes_data.get("06", {}).get("fare") == "15.000đ - 22.000đ", f"Route 06 fare error: {routes_data.get('06')}"
        assert routes_data.get("05", {}).get("fare") == "8.000đ", f"Route 05 fare error: {routes_data.get('05')}"
        assert routes_data.get("09", {}).get("fare") == "Đang cập nhật", f"Route 09 fake fare: {routes_data.get('09')}"
        assert routes_data.get("13", {}).get("fare") == "Đang cập nhật", f"Route 13 fake fare: {routes_data.get('13')}"
        assert routes_data.get("LK01", {}).get("fare") == "80.000đ", f"Route LK01 fare error: {routes_data.get('LK01')}"
        assert routes_data.get("01SB", {}).get("fare") == "120.000đ", f"Route 01SB fare error: {routes_data.get('01SB')}"

        # Check 3: Route 02 Detail View
        runner.evaluate("window.app.openRouteDetail('02')")
        time.sleep(0.3)
        r02_detail_fare = runner.evaluate("document.getElementById('detail-fare-single')?.textContent")
        r02_detail_tag = runner.evaluate("document.getElementById('detail-fare-tag')?.textContent")
        r02_detail_freq = runner.evaluate("document.getElementById('detail-stat-freq')?.textContent")
        print(f"[Check 3] Route 02 Detail: Fare={r02_detail_fare}, Tag={r02_detail_tag}, Freq={r02_detail_freq}")
        assert "8.000đ - 30.000đ" in r02_detail_fare
        assert r02_detail_tag == "Theo chặng"
        assert r02_detail_freq == "15-30 phút", f"Route 02 detail frequency mismatch: {r02_detail_freq}"

        # Check 4: Route 05 Detail View
        runner.evaluate("window.app.openRouteDetail('05')")
        time.sleep(0.3)
        r05_detail_fare = runner.evaluate("document.getElementById('detail-fare-single')?.textContent")
        r05_detail_tag = runner.evaluate("document.getElementById('detail-fare-tag')?.textContent")
        print(f"[Check 4] Route 05 Detail: {r05_detail_fare} (Tag: {r05_detail_tag})")
        assert "8.000đ" in r05_detail_fare
        assert r05_detail_tag == "Trợ giá"

        # Check 5: Route 09 Detail View
        runner.evaluate("window.app.openRouteDetail('09')")
        time.sleep(0.3)
        r09_detail_fare = runner.evaluate("document.getElementById('detail-fare-single')?.textContent")
        r09_detail_tag = runner.evaluate("document.getElementById('detail-fare-tag')?.textContent")
        print(f"[Check 5] Route 09 Detail: {r09_detail_fare} (Tag: {r09_detail_tag})")
        assert "Đang cập nhật" in r09_detail_fare
        assert r09_detail_tag == "Đang cập nhật"

        # Check 6: Trip Results rendering
        runner.evaluate("window.app.showTripResults('Bến xe Trung tâm', 'Phố cổ Hội An')")
        time.sleep(0.5)
        trip_fare = runner.evaluate("document.getElementById('trip-fare-value')?.textContent")
        trip_time = runner.evaluate("document.getElementById('trip-countdown-time')?.textContent")
        trip_timer = runner.evaluate("document.getElementById('trip-countdown-timer')?.textContent")
        trip_freq = runner.evaluate("document.getElementById('trip-freq-value')?.textContent")
        print(f"[Check 6] Trip Results: Fare={trip_fare}, Time={trip_time}, Timer={trip_timer}, Freq={trip_freq}")
        assert trip_fare == "8.000đ - 30.000đ", f"Trip fare error: {trip_fare}"
        assert trip_fare != "30.000đ", "Trip fare must not fallback to flat 30.000đ!"
        assert trip_freq == "15-30p", f"Trip frequency should be 15-30p for route 02, got: {trip_freq}"

        # Check 6b: Missing frequency fail-closed UI
        runner.evaluate("""
        (() => {
            const fakeRoute = { id: '99', routeNumber: '99', shortName: 'Test', category: 'subsidized' };
            document.getElementById('trip-freq-value').textContent = window.busService.formatRouteFrequency(fakeRoute, true);
        })()
        """)
        trip_freq_missing = runner.evaluate("document.getElementById('trip-freq-value')?.textContent")
        assert trip_freq_missing == "Đang cập nhật", f"Expected 'Đang cập nhật' when frequency missing, got: {trip_freq_missing}"

        # Check 7: Screenshot Capture
        runner.capture_screenshot(SCREENSHOT_PATH)
        print(f"[Check 7] Deliverable screenshot saved to {SCREENSHOT_PATH} ({os.path.getsize(SCREENSHOT_PATH)} bytes)")

        print("\n>>> ALL TASK 7 BROWSER ACCEPTANCE CHECKS PASSED (7/7) <<<")
    finally:
        runner.stop()


if __name__ == "__main__":
    run_checks()
