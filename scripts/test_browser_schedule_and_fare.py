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
import tempfile
import time
import urllib.request
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent
PORT = 8992
CDP_PORT = 9445
DEFAULT_SCREENSHOT_PATH = WORKSPACE / "docs" / "reports" / "task7_schedule_fare_evidence.png"


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

    def _recv_exact(self, n):
        buf = bytearray()
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Socket closed prematurely while reading frame")
            buf.extend(chunk)
        return bytes(buf)

    def recv_text(self):
        while True:
            head = self._recv_exact(2)
            b1, b2 = struct.unpack('BB', head)
            opcode = b1 & 0x0F
            is_masked = bool(b2 & 0x80)
            payload_len = b2 & 0x7F
            if payload_len == 126:
                payload_len = struct.unpack('>H', self._recv_exact(2))[0]
            elif payload_len == 127:
                payload_len = struct.unpack('>Q', self._recv_exact(8))[0]

            mask = self._recv_exact(4) if is_masked else None
            payload = bytearray(self._recv_exact(payload_len))
            if is_masked:
                for i in range(payload_len):
                    payload[i] ^= mask[i % 4]

            if opcode == 1:
                return payload.decode('utf-8', errors='replace')
            elif opcode == 8:
                self.close()
                raise ConnectionError("Server closed connection")
            elif opcode == 9:
                pong = bytes([0x8A, 0x80]) + os.urandom(4)
                self.sock.sendall(pong)

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
        self.temp_dir = tempfile.TemporaryDirectory(prefix="danabus_fare_test_")
        self.profile_dir = self.temp_dir.name
        self.console_logs = []
        self.runtime_exceptions = []
        self.failed_requests = []
        self.requests = {}

    def start(self):
        # 1. Start Python HTTP Server
        self.http_proc = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(PORT)],
            cwd=WORKSPACE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # 2. Start Headless Chrome at about:blank (single controlled navigation via CDP)
        chrome_bin = "/bin/google-chrome"
        if not os.path.exists(chrome_bin):
            chrome_bin = "/usr/bin/google-chrome"
        cmd = [
            chrome_bin,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-sync",
            "--disable-default-apps",
            "--no-first-run",
            "--no-default-browser-check",
            "--ignore-certificate-errors",
            f"--user-data-dir={self.profile_dir}",
            "--remote-allow-origins=*",
            f"--remote-debugging-port={CDP_PORT}",
            "about:blank"
        ]
        self.chrome_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # 3. Connect CDP with bounded retry loop
        cdp_url = f"http://127.0.0.1:{CDP_PORT}/json"
        ws_url = None
        start = time.time()
        while time.time() - start < 10.0:
            if self.chrome_proc.poll() is not None:
                raise RuntimeError(f"Chrome exited prematurely with code {self.chrome_proc.returncode}")
            try:
                with urllib.request.urlopen(cdp_url, timeout=1) as resp:
                    tabs = json.loads(resp.read().decode())
                    page_tabs = [t for t in tabs if t.get('type') == 'page']
                    if page_tabs and "webSocketDebuggerUrl" in page_tabs[0]:
                        ws_url = page_tabs[0]["webSocketDebuggerUrl"]
                        break
            except Exception:
                time.sleep(0.1)
        if not ws_url:
            raise RuntimeError("Failed to connect to Chrome CDP within 10.0s")

        self.ws = SimpleWebSocket(ws_url)
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("Network.enable")
        self.call("Log.enable")

        # Single controlled navigation
        test_url = f"http://127.0.0.1:{PORT}/index.html"
        self.call("Page.navigate", {"url": test_url})

        # Wait until page and SW settle after real first-run takeover and reload
        self.wait_for_settled(timeout=12.0)

    def _record_event(self, method, params):
        if method == "Runtime.consoleAPICalled":
            msg_type = params.get("type", "log")
            args = [a.get("value", a.get("description", "")) for a in params.get("args", [])]
            self.console_logs.append(f"[{msg_type.upper()}] {' '.join(str(x) for x in args)}")
        elif method == "Runtime.exceptionThrown":
            desc = params.get("exceptionDetails", {}).get("text", "")
            exp = params.get("exceptionDetails", {}).get("exception", {}).get("description", "")
            self.runtime_exceptions.append(f"{desc}: {exp}")
        elif method == "Log.entryAdded":
            entry = params.get("entry", {})
            self.console_logs.append(f"[BROWSER-{entry.get('level', 'info').upper()}] {entry.get('text', '')}")
        elif method == "Network.requestWillBeSent":
            req_id = params.get("requestId")
            req = params.get("request", {})
            if req_id and "url" in req:
                self.requests[req_id] = req["url"]
        elif method == "Network.loadingFailed":
            req_id = params.get("requestId")
            url = self.requests.get(req_id, params.get("type", "unknown"))
            err = params.get("errorText", "unknown error")
            req_type = params.get("type", "other")
            self.failed_requests.append(f"Failed request: {url} - {err} ({req_type})")
        elif method == "Network.responseReceived":
            resp = params.get("response", {})
            status = resp.get("status", 200)
            if status >= 400:
                self.failed_requests.append(f"HTTP {status}: {resp.get('url')}")

    def call(self, method, params=None):
        self.msg_id += 1
        curr_id = self.msg_id
        req = {"id": curr_id, "method": method, "params": params or {}}
        self.ws.send_text(json.dumps(req))
        while True:
            raw = self.ws.recv_text()
            try:
                res = json.loads(raw)
            except Exception:
                continue
            if "method" in res:
                self._record_event(res["method"], res.get("params", {}))
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
        result_inner = res.get("result", {})
        if result_inner.get("subtype") == "error":
            raise RuntimeError(f"JavaScript error: {result_inner.get('description', 'Unknown error')} (expr: {expr[:200]})")
        if result_inner.get("type") == "undefined":
            return None
        return result_inner.get("value")

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

    def wait_for_settled(self, timeout=12.0):
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
                                 window.busService.routes && window.busService.routes.length > 0;

                if (appReady && busReady) {
                    return {
                        navType,
                        controllerActive: true,
                        appState: window.app.loadState,
                        routesCount: window.busService.routes.length
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
            time.sleep(0.1)
        raise TimeoutError(f"Page did not settle with SW controller & reload within {timeout}s")

    def capture_screenshot(self, output_path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        res = self.call("Page.captureScreenshot", {"format": "png"})
        b64 = res.get("data", "")
        if b64:
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(b64))

    def capture_diagnostics(self, diag_screenshot_path=None):
        print("\n" + "=" * 70)
        print("!!! BROWSER RUNNER DIAGNOSTIC DUMP (TASK 7) !!!")
        print("=" * 70)
        try:
            state = self.evaluate("""
                (() => {
                    try {
                        return {
                            url: window.location.href,
                            readyState: document.readyState,
                            appLoadState: window.app?.loadState,
                            currentView: window.app?.currentView,
                            selectedRouteId: window.app?.selectedRoute?.id,
                            busServiceLoaded: window.busService?.isLoaded,
                            routesCount: window.busService?.routes?.length,
                            spotlightFare: document.getElementById('spotlight-fare')?.textContent?.trim(),
                            spotlightSchedule: document.getElementById('spotlight-schedule')?.textContent?.trim(),
                            spotlightCountdown: document.getElementById('spotlight-countdown')?.textContent?.trim()
                        };
                    } catch (e) {
                        return { error: e.toString() };
                    }
                })()
            """)
            print(f"Browser State Snapshot:\n{json.dumps(state, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"Could not retrieve state snapshot: {e}")

        if self.console_logs:
            print(f"\nCaptured Console Logs ({len(self.console_logs)} entries):")
            for log in self.console_logs[-20:]:
                print(f"  {log}")

        if self.runtime_exceptions:
            print(f"\nCaptured JS Exceptions ({len(self.runtime_exceptions)} entries):")
            for exc in self.runtime_exceptions:
                print(f"  {exc}")

        if self.failed_requests:
            print(f"\nCaptured Failed Requests ({len(self.failed_requests)} entries):")
            for req in self.failed_requests:
                print(f"  {req}")

        if diag_screenshot_path:
            try:
                self.capture_screenshot(diag_screenshot_path)
                print(f"\nDiagnostic screenshot written to: {diag_screenshot_path}")
            except Exception as e:
                print(f"Failed to capture diagnostic screenshot: {e}")
        print("=" * 70 + "\n")

    def stop(self):
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None
        if self.chrome_proc:
            try:
                self.chrome_proc.terminate()
                self.chrome_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.chrome_proc.kill()
                self.chrome_proc.wait(timeout=2)
            except Exception:
                pass
            self.chrome_proc = None
        if self.http_proc:
            try:
                self.http_proc.terminate()
                self.http_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.http_proc.kill()
                self.http_proc.wait(timeout=2)
            except Exception:
                pass
            self.http_proc = None
        if hasattr(self, 'temp_dir') and self.temp_dir:
            try:
                self.temp_dir.cleanup()
            except Exception:
                pass
            self.temp_dir = None


def run_checks(test_diagnostic=False, screenshot_path=None):
    runner = ChromeRunner()
    print("[Browser Test] Launching Headless Chrome & connecting CDP...")
    diag_screenshot = WORKSPACE / "docs" / "reports" / "task7_failure_diagnostic.png"
    runner.start()
    try:
        if test_diagnostic:
            print("[TEST-DIAGNOSTIC] Intentionally triggering synthetic failure to verify diagnostic capture...")
            runner.evaluate("console.error('Synthetic diagnostic test error: simulated failure condition in suite B.2')")
            # Trigger synthetic network failure to prove network diagnostics domain
            runner.evaluate("(async () => { try { await fetch('/synthetic_diagnostic_404_test_fare'); } catch (e) {} })()")
            # Trigger synthetic JS runtime exception via setTimeout to ensure Runtime.exceptionThrown event fires
            runner.evaluate("setTimeout(() => { throw new Error('Synthetic diagnostic runtime error in suite B.2'); }, 0)")
            try:
                runner.wait_for_condition("document.getElementById('non_existent_element_in_suite_b2') !== null", timeout=0.6, description="Synthetic element wait")
            except Exception as syn_err:
                print(f"[TEST-DIAGNOSTIC] Caught expected synthetic error: {syn_err}")
                runner.capture_diagnostics(diag_screenshot)
                assert diag_screenshot.exists() and diag_screenshot.stat().st_size > 0, "Diagnostic screenshot must be written and non-empty!"
                assert len(runner.console_logs) > 0, "Console logs must be captured!"
                assert len(runner.runtime_exceptions) > 0, "Runtime exceptions must be captured!"
                assert len(runner.failed_requests) > 0, "Failed network requests must be captured!"
                print(f"[TEST-DIAGNOSTIC] PASS: Diagnostic snapshot, console, runtime, network, and screenshot verified ({diag_screenshot.stat().st_size} bytes)")
                return

        # Check 1: Spotlight card fare, schedule subtitle & countdown
        spotlight = runner.wait_for_condition(
            """(() => {
                const fare = document.getElementById('spotlight-fare')?.textContent?.trim();
                const schedule = document.getElementById('spotlight-schedule')?.textContent?.trim();
                const countdown = document.getElementById('spotlight-countdown')?.textContent?.trim();
                if (!fare || !schedule || !countdown) return null;
                return { fare, schedule, countdown };
            })()""",
            timeout=8.0,
            description="Spotlight card elements rendered"
        )
        spotlight_fare = spotlight['fare']
        spotlight_schedule = spotlight['schedule']
        spotlight_countdown = spotlight['countdown']
        print(f"[Check 1] Spotlight Fare: {spotlight_fare}, Schedule: {spotlight_schedule}, Countdown: {spotlight_countdown}")
        assert spotlight_fare == "8.000đ - 30.000đ", f"Unexpected spotlight fare: {spotlight_fare}"
        assert "15-30 phút" in spotlight_schedule and "05:15 - 18:30" in spotlight_schedule, f"Spotlight schedule error: {spotlight_schedule}"
        assert "Tần suất 15 phút •" not in spotlight_schedule, f"Hardcoded 15 phút detected in spotlight schedule: {spotlight_schedule}"
        assert "6 phút" not in spotlight_countdown, f"Fake placeholder detected: {spotlight_countdown}"

        # Check 2: Routes Catalog Fares & Frequency
        runner.evaluate("window.app.navigateTo('routes')")
        routes_data = runner.wait_for_condition(
            """(() => {
                if (window.app.currentView !== 'routes') return null;
                const cards = document.querySelectorAll('.route-card');
                if (cards.length < 20) return null;
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
            })()""",
            timeout=8.0,
            description="Routes catalog rendered with at least 20 routes"
        )
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
        r02_detail = runner.wait_for_condition(
            """(() => {
                if (window.app.currentView !== 'route-detail' || window.app.selectedRoute?.id !== '02') return null;
                const fare = document.getElementById('detail-fare-single')?.textContent?.trim();
                const tag = document.getElementById('detail-fare-tag')?.textContent?.trim();
                const freq = document.getElementById('detail-stat-freq')?.textContent?.trim();
                if (!fare) return null;
                return { fare, tag, freq };
            })()""",
            timeout=8.0,
            description="Route 02 detail view rendered"
        )
        r02_detail_fare = r02_detail['fare']
        r02_detail_tag = r02_detail['tag']
        r02_detail_freq = r02_detail['freq']
        print(f"[Check 3] Route 02 Detail: Fare={r02_detail_fare}, Tag={r02_detail_tag}, Freq={r02_detail_freq}")
        assert "8.000đ - 30.000đ" in r02_detail_fare
        assert r02_detail_tag == "Theo chặng"
        assert r02_detail_freq == "15-30 phút", f"Route 02 detail frequency mismatch: {r02_detail_freq}"

        # Check 4: Route 05 Detail View
        runner.evaluate("window.app.openRouteDetail('05')")
        r05_detail = runner.wait_for_condition(
            """(() => {
                if (window.app.currentView !== 'route-detail' || window.app.selectedRoute?.id !== '05') return null;
                const fare = document.getElementById('detail-fare-single')?.textContent?.trim();
                const tag = document.getElementById('detail-fare-tag')?.textContent?.trim();
                if (!fare) return null;
                return { fare, tag };
            })()""",
            timeout=8.0,
            description="Route 05 detail view rendered"
        )
        r05_detail_fare = r05_detail['fare']
        r05_detail_tag = r05_detail['tag']
        print(f"[Check 4] Route 05 Detail: {r05_detail_fare} (Tag: {r05_detail_tag})")
        assert "8.000đ" in r05_detail_fare
        assert r05_detail_tag == "Trợ giá"

        # Check 5: Route 09 Detail View
        runner.evaluate("window.app.openRouteDetail('09')")
        r09_detail = runner.wait_for_condition(
            """(() => {
                if (window.app.currentView !== 'route-detail' || window.app.selectedRoute?.id !== '09') return null;
                const fare = document.getElementById('detail-fare-single')?.textContent?.trim();
                const tag = document.getElementById('detail-fare-tag')?.textContent?.trim();
                if (!fare) return null;
                return { fare, tag };
            })()""",
            timeout=8.0,
            description="Route 09 detail view rendered"
        )
        r09_detail_fare = r09_detail['fare']
        r09_detail_tag = r09_detail['tag']
        print(f"[Check 5] Route 09 Detail: {r09_detail_fare} (Tag: {r09_detail_tag})")
        assert "Đang cập nhật" in r09_detail_fare
        assert r09_detail_tag == "Đang cập nhật"

        # Check 6: Trip Results rendering
        runner.evaluate("window.app.showTripResults('Bến xe Trung tâm', 'Phố cổ Hội An')")
        trip_res = runner.wait_for_condition(
            """(() => {
                if (window.app.currentView !== 'trip-results') return null;
                const fare = document.getElementById('trip-fare-value')?.textContent?.trim();
                const time = document.getElementById('trip-countdown-time')?.textContent?.trim();
                const timer = document.getElementById('trip-countdown-timer')?.textContent?.trim();
                const freq = document.getElementById('trip-freq-value')?.textContent?.trim();
                if (!fare || fare === '--') return null;
                return { fare, time, timer, freq };
            })()""",
            timeout=8.0,
            description="Trip results rendered"
        )
        trip_fare = trip_res['fare']
        trip_time = trip_res['time']
        trip_timer = trip_res['timer']
        trip_freq = trip_res['freq']
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
        trip_freq_missing = runner.wait_for_condition(
            """(() => {
                const val = document.getElementById('trip-freq-value')?.textContent?.trim();
                return val === 'Đang cập nhật' ? val : null;
            })()""",
            timeout=4.0,
            description="Missing frequency updated to 'Đang cập nhật'"
        )
        assert trip_freq_missing == "Đang cập nhật", f"Expected 'Đang cập nhật' when frequency missing, got: {trip_freq_missing}"

        # Check 7: Screenshot Capture
        target_shot = Path(screenshot_path) if screenshot_path else DEFAULT_SCREENSHOT_PATH
        target_shot.parent.mkdir(parents=True, exist_ok=True)
        runner.capture_screenshot(target_shot)
        print(f"[Check 7] Deliverable screenshot saved to {target_shot} ({os.path.getsize(target_shot)} bytes)")

        print("\n>>> ALL TASK 7 BROWSER ACCEPTANCE CHECKS PASSED (7/7) <<<")
    except Exception as e:
        runner.capture_diagnostics(diag_screenshot)
        raise
    finally:
        runner.stop()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Browser Schedule & Fare Acceptance Test")
    parser.add_argument("--test-diagnostic", action="store_true", help="Trigger synthetic failure")
    parser.add_argument("--screenshot-path", default=None, help="Custom screenshot destination")
    args = parser.parse_args()
    run_checks(test_diagnostic=args.test_diagnostic, screenshot_path=args.screenshot_path)
