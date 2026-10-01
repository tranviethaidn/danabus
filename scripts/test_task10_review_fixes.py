#!/usr/bin/env python3
"""
Targeted Regression Test Suite for Task 010 Review Fixes
Verifies all 7 acceptance defects identified in TL review:
1. Alternatives hidden by default, toggle expands/collapses, aria-expanded synced
2. Transfer count truthful (2-transfer journey renders 'Chuyển tuyến (2 lần)')
3. Route detail uses direction of current journey, never stale from prior search
4. Frequency never contains transfer metadata, never renders 'Theo lịch: 1 chuyển tiếp'
5. Missing schedule/frequency fails-closed to 'Chưa có dữ liệu', never 'Theo lịch công bố'
6. Planner km never aggregates full-route distances; fails-closed to 'Chưa có dữ liệu' without segment distance
7. Planner technical details reset direct schedule and truthfully label connecting trips / estimated duration

Task-ID: tsk_d45190c7-1380-48e0-9dc7-5239307f5a4b
"""

import os
import sys
import time
import json
import base64
import socket
import tempfile
import urllib.request
import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent

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


class CleanChromeRunner:
    def __init__(self, port=9444, http_port=8282):
        self.port = port
        self.http_port = http_port
        self.chrome_proc = None
        self.http_proc = None
        self.tmp_dir = tempfile.TemporaryDirectory()
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
            "--incognito",
            f"--user-data-dir={self.tmp_dir.name}",
            f"--remote-debugging-port={self.port}",
            "--window-size=1280,900"
        ]
        self.chrome_proc = subprocess.Popen(chrome_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.0)

        tabs_url = f"http://127.0.0.1:{self.port}/json"
        ws_url = None
        for _ in range(25):
            try:
                with urllib.request.urlopen(tabs_url, timeout=2) as r:
                    tabs = json.loads(r.read().decode())
                    page_tabs = [t for t in tabs if t.get("type") == "page"]
                    if page_tabs:
                        ws_url = page_tabs[0]["webSocketDebuggerUrl"]
                        break
            except:
                time.sleep(0.2)
        if not ws_url:
            raise RuntimeError("Failed to obtain Chrome CDP WebSocket URL")

        test_url = f"http://127.0.0.1:{self.http_port}/index.html"
        self.ws = SimpleWebSocket(ws_url)
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("Network.enable")
        self.call("Network.setCacheDisabled", {"cacheDisabled": True})
        self.call("Page.navigate", {"url": test_url})

        for _ in range(40):
            ready = self.evaluate("document.readyState === 'complete' && !!document.title && Boolean(window.busService?.routes?.length > 0) && Boolean(window.app)")
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
        if "exceptionDetails" in res:
            raise RuntimeError(f"JS evaluation error: {res['exceptionDetails']}")
        return res.get("result", {}).get("value")

    def stop(self):
        if self.ws:
            self.ws.close()
        if self.chrome_proc:
            self.chrome_proc.terminate()
            self.chrome_proc.wait()
        if self.http_proc:
            self.http_proc.terminate()
            self.http_proc.wait()
        try:
            self.tmp_dir.cleanup()
        except:
            pass


def run_tests():
    print("=" * 70)
    print("RUNNING TARGETED REGRESSION SUITE: TASK 010 REVIEW FIXES")
    print("Task-ID: tsk_d45190c7-1380-48e0-9dc7-5239307f5a4b")
    print("=" * 70)

    runner = CleanChromeRunner(port=9448, http_port=8288)
    runner.start()
    try:
        # -------------------------------------------------------------
        # Defect 1: Alternatives hidden by default & toggle sync
        # -------------------------------------------------------------
        print("\n>> [Check 1] Alternatives hidden by default & toggle synchronization...")
        runner.evaluate("window.app.showTripResults('Trường Đại học Bách Khoa - ĐHĐN', 'Công viên Biển Đông')")
        time.sleep(0.5)

        opt_hidden_initial = runner.evaluate("document.getElementById('trip-planner-options').classList.contains('hidden')")
        btn_aria_initial = runner.evaluate("document.getElementById('btn-toggle-alternatives').getAttribute('aria-expanded')")
        print(f"   Initial state after search: hidden={opt_hidden_initial}, aria-expanded={btn_aria_initial}")
        assert opt_hidden_initial is True, "Defect 1 FAIL: #trip-planner-options must be hidden by default after search!"
        assert btn_aria_initial == "false", f"Defect 1 FAIL: #btn-toggle-alternatives aria-expanded must be 'false', got {btn_aria_initial}"

        # Toggle to open
        runner.evaluate("document.getElementById('btn-toggle-alternatives').click()")
        time.sleep(0.2)
        opt_hidden_open = runner.evaluate("document.getElementById('trip-planner-options').classList.contains('hidden')")
        btn_aria_open = runner.evaluate("document.getElementById('btn-toggle-alternatives').getAttribute('aria-expanded')")
        print(f"   State after click toggle: hidden={opt_hidden_open}, aria-expanded={btn_aria_open}")
        assert opt_hidden_open is False, "Defect 1 FAIL: #trip-planner-options must become visible after clicking toggle!"
        assert btn_aria_open == "true", f"Defect 1 FAIL: #btn-toggle-alternatives aria-expanded must be 'true', got {btn_aria_open}"

        # Toggle to close
        runner.evaluate("document.getElementById('btn-toggle-alternatives').click()")
        time.sleep(0.2)
        opt_hidden_close = runner.evaluate("document.getElementById('trip-planner-options').classList.contains('hidden')")
        btn_aria_close = runner.evaluate("document.getElementById('btn-toggle-alternatives').getAttribute('aria-expanded')")
        print(f"   State after second toggle: hidden={opt_hidden_close}, aria-expanded={btn_aria_close}")
        assert opt_hidden_close is True, "Defect 1 FAIL: #trip-planner-options must be hidden after closing toggle!"
        assert btn_aria_close == "false", "Defect 1 FAIL: aria-expanded must be 'false' after closing toggle!"

        # Open and click 'Chọn' on alternative trip card
        runner.evaluate("document.getElementById('btn-toggle-alternatives').click()")
        time.sleep(0.2)
        runner.evaluate("document.querySelectorAll('.btn-select-trip')[0]?.click()")
        time.sleep(0.3)
        opt_hidden_selected = runner.evaluate("document.getElementById('trip-planner-options').classList.contains('hidden')")
        btn_aria_selected = runner.evaluate("document.getElementById('btn-toggle-alternatives').getAttribute('aria-expanded')")
        print(f"   State after selecting alternative: hidden={opt_hidden_selected}, aria-expanded={btn_aria_selected}")
        assert opt_hidden_selected is True, "Defect 1 FAIL: selecting a journey must collapse alternatives!"
        assert btn_aria_selected == "false", "Defect 1 FAIL: selecting a journey must reset aria-expanded to false!"
        print("   [PASS] Check 1: Alternatives hidden by default & toggle synchronized.")

        # -------------------------------------------------------------
        # Defect 2: Truthful transfer count label (2 transfers != 1 lần)
        # -------------------------------------------------------------
        print("\n>> [Check 2] Truthful transfer count label...")
        res_transfers = runner.evaluate("""
        (() => {
            const fakeTrip = {
                type: 'connecting',
                transfers: 2,
                totalDurationMinutes: 55,
                totalWalkingMeters: 400,
                fareText: '16.000đ',
                rankingCategory: 'Ít đi bộ nhất',
                legs: [
                    { type: 'walking', summary: 'Đi bộ', distanceMeters: 100, durationMinutes: 2, fromLabel: 'A', toLabel: 'Stop1' },
                    { type: 'transit', routeNumber: '02', direction: 'outbound', boardingStop: { name: 'Stop1' }, alightingStop: { name: 'Stop2' }, stopsCount: 5, route: window.busService.getRouteById('02') },
                    { type: 'walking', summary: 'Chuyển tuyến', distanceMeters: 100, durationMinutes: 2 },
                    { type: 'transit', routeNumber: '05', direction: 'outbound', boardingStop: { name: 'Stop2' }, alightingStop: { name: 'Stop3' }, stopsCount: 4, route: window.busService.getRouteById('05') },
                    { type: 'walking', summary: 'Chuyển tuyến', distanceMeters: 100, durationMinutes: 2 },
                    { type: 'transit', routeNumber: '07', direction: 'outbound', boardingStop: { name: 'Stop3' }, alightingStop: { name: 'Stop4' }, stopsCount: 3, route: window.busService.getRouteById('07') },
                    { type: 'walking', summary: 'Đến nơi', distanceMeters: 100, durationMinutes: 2, toLabel: 'B' }
                ]
            };
            window.app.renderPlannerResults([fakeTrip]);
            return {
                busTag: document.getElementById('trip-bus-tag')?.textContent?.trim(),
                badge: document.getElementById('journey-type-badge')?.textContent?.trim()
            };
        })()
        """)
        print(f"   2-transfer trip labels: busTag='{res_transfers['busTag']}', badge='{res_transfers['badge']}'")
        assert "2 lần" in res_transfers['busTag'], f"Defect 2 FAIL: busTag must state 2 transfers, got '{res_transfers['busTag']}'"
        assert "1 lần" not in res_transfers['busTag'], f"Defect 2 FAIL: busTag must not hard-code 1 lần for 2 transfers: '{res_transfers['busTag']}'"
        assert "2 lần" in res_transfers['badge'], f"Defect 2 FAIL: badge must state 2 lần chuyển tuyến, got '{res_transfers['badge']}'"
        print("   [PASS] Check 2: Truthful transfer count label verified (no hardcoded '1 lần').")

        # -------------------------------------------------------------
        # Defect 3: Route detail direction not stale
        # -------------------------------------------------------------
        print("\n>> [Check 3] Route detail direction alignment with current journey...")
        res_dir = runner.evaluate("""
        (() => {
            // Step A: Set prior state to inbound
            window.app.matchedDirection = 'inbound';
            window.app.currentDirection = 'inbound';

            // Step B: Now planner delivers a trip whose primary transit leg is 'outbound'
            const plannedTrip = {
                type: 'connecting',
                transfers: 1,
                totalDurationMinutes: 40,
                totalWalkingMeters: 200,
                fareText: '16.000đ',
                legs: [
                    { type: 'walking', distanceMeters: 100, fromLabel: 'Start', toLabel: 'Stop A' },
                    { type: 'transit', routeNumber: '02', direction: 'outbound', boardingStop: { name: 'Stop A' }, alightingStop: { name: 'Stop B' }, stopsCount: 5, route: window.busService.getRouteById('02') },
                    { type: 'transit', routeNumber: '05', direction: 'inbound', boardingStop: { name: 'Stop B' }, alightingStop: { name: 'Stop C' }, stopsCount: 5, route: window.busService.getRouteById('05') }
                ]
            };
            window.app.renderPlannerResults([plannedTrip]);

            let capturedRouteId = null;
            let capturedDirection = null;
            const origOpenRouteDetail = window.app.openRouteDetail.bind(window.app);
            window.app.openRouteDetail = (rId, dir) => {
                capturedRouteId = rId;
                capturedDirection = dir;
            };

            // Trigger secondary action route detail
            document.getElementById('btn-journey-route-detail')?.click();

            // Restore
            window.app.openRouteDetail = origOpenRouteDetail;

            return {
                appMatchedDirection: window.app.matchedDirection,
                appCurrentDirection: window.app.currentDirection,
                capturedRouteId,
                capturedDirection
            };
        })()
        """)
        print(f"   Route detail test: capturedDirection='{res_dir['capturedDirection']}', appDirection='{res_dir['appCurrentDirection']}'")
        assert res_dir['capturedDirection'] == 'outbound', f"Defect 3 FAIL: Route detail opened with stale direction '{res_dir['capturedDirection']}', expected 'outbound'!"
        assert res_dir['appCurrentDirection'] == 'outbound', f"Defect 3 FAIL: app.currentDirection was '{res_dir['appCurrentDirection']}', expected 'outbound'!"
        print("   [PASS] Check 3: Route detail uses active journey direction, zero stale direction leakage.")

        # -------------------------------------------------------------
        # Defect 4: Frequency never contains transfer metadata
        # -------------------------------------------------------------
        print("\n>> [Check 4] Frequency text integrity (no transfer counts under 'Theo lịch')...")
        res_freq = runner.evaluate("""
        (() => {
            const trip = {
                type: 'connecting',
                transfers: 1,
                totalDurationMinutes: 35,
                totalWalkingMeters: 150,
                legs: [
                    { type: 'walking', distanceMeters: 150 },
                    { type: 'transit', routeNumber: '02', direction: 'outbound', route: window.busService.getRouteById('02') }
                ]
            };
            const vm = window.app.buildJourneyViewModelFromPlanned(trip, 'A', 'B');
            window.app.renderJourneyRecommendation(vm);
            const metricsText = document.getElementById('journey-summary-metrics')?.textContent || '';
            const cardText = document.getElementById('journey-recommendation-card')?.textContent || '';
            return {
                vmFrequencyText: vm.frequencyText,
                hasBadSchedulePhrase: metricsText.includes('Theo lịch: 1 chuyển tiếp') || metricsText.includes('Theo lịch: 2 chuyển tiếp') || cardText.includes('Theo lịch: 1 chuyển tiếp')
            };
        })()
        """)
        print(f"   ViewModel frequencyText: {res_freq['vmFrequencyText']}, hasBadPhrase={res_freq['hasBadSchedulePhrase']}")
        assert res_freq['vmFrequencyText'] is None or "chuyển tiếp" not in str(res_freq['vmFrequencyText']), f"Defect 4 FAIL: vm.frequencyText contains transfer metadata: {res_freq['vmFrequencyText']}"
        assert not res_freq['hasBadSchedulePhrase'], "Defect 4 FAIL: UI rendered 'Theo lịch: 1 chuyển tiếp'!"
        print("   [PASS] Check 4: Frequency semantics truthful, transfer counts never tagged as 'Theo lịch'.")

        # -------------------------------------------------------------
        # Defect 5: Missing schedule/frequency fail-closed
        # -------------------------------------------------------------
        print("\n>> [Check 5] Fallback schedule fail-closed (no 'Theo lịch công bố' when missing)...")
        res_fallback = runner.evaluate("""
        (() => {
            const tripNoSchedule = {
                type: 'direct',
                route: { id: 'test_route', routeNumber: '99', frequency: { type: 'unknown' }, vehicleInfo: null },
                totalDurationMinutes: 20,
                totalWalkingMeters: 0,
                fareText: '8.000đ',
                transfers: 0,
                legs: [
                    { type: 'transit', routeNumber: '99', direction: 'outbound', departure: { status: 'unknown' } }
                ]
            };
            const vm = window.app.buildJourneyViewModelFromPlanned(tripNoSchedule, 'A', 'B');
            // Force null walking, null dep, null freq
            vm.totalWalkingMeters = 0;
            vm.departure = null;
            vm.frequencyText = null;
            window.app.renderJourneyRecommendation(vm);

            const metricsHtml = document.getElementById('journey-summary-metrics')?.innerHTML || '';
            const metricsText = document.getElementById('journey-summary-metrics')?.textContent || '';
            return {
                metricsText,
                hasChuaCoDuLieu: metricsText.includes('Chưa có dữ liệu'),
                hasTheoLichCongBo: metricsText.includes('Theo lịch công bố') || metricsHtml.includes('Theo lịch công bố')
            };
        })()
        """)
        print(f"   Missing schedule metrics: '{res_fallback['metricsText']}'")
        assert res_fallback['hasChuaCoDuLieu'], "Defect 5 FAIL: Missing schedule/frequency must render 'Chưa có dữ liệu'!"
        assert not res_fallback['hasTheoLichCongBo'], "Defect 5 FAIL: UI must NOT assert 'Theo lịch công bố' when missing schedule!"
        print("   [PASS] Check 5: Missing schedule/frequency strictly fails-closed to 'Chưa có dữ liệu'.")

        # -------------------------------------------------------------
        # Defect 6: Planner distance does not fake segment distance
        # -------------------------------------------------------------
        print("\n>> [Check 6] Planner distance fails-closed to null without segment data...")
        res_dist = runner.evaluate("""
        (() => {
            // Case A: Transit legs have no segmentDistanceKm (only full route exists on route object)
            const r02 = window.busService.getRouteById('02');
            const tripWithoutSegmentKm = {
                type: 'connecting',
                transfers: 1,
                totalDurationMinutes: 45,
                totalWalkingMeters: 200,
                fareText: '16.000đ',
                legs: [
                    { type: 'walking', distanceMeters: 100 },
                    { type: 'transit', routeNumber: '02', direction: 'outbound', route: r02, stopsCount: 4 },
                    { type: 'transit', routeNumber: '05', direction: 'outbound', route: window.busService.getRouteById('05'), stopsCount: 3 },
                    { type: 'walking', distanceMeters: 100 }
                ]
            };
            const vmA = window.app.buildJourneyViewModelFromPlanned(tripWithoutSegmentKm, 'A', 'B');
            window.app.renderPlannerResults([tripWithoutSegmentKm]);
            const kmElA = document.getElementById('trip-stat-km')?.textContent?.trim();

            // Case B: Transit legs have authentic segment distances
            const tripWithSegmentKm = {
                type: 'connecting',
                transfers: 1,
                totalDurationMinutes: 45,
                totalWalkingMeters: 200,
                fareText: '16.000đ',
                legs: [
                    { type: 'walking', distanceMeters: 100 },
                    { type: 'transit', routeNumber: '02', direction: 'outbound', route: r02, stopsCount: 4, segmentDistanceKm: 3.5 },
                    { type: 'transit', routeNumber: '05', direction: 'outbound', route: window.busService.getRouteById('05'), stopsCount: 3, segmentDistanceKm: 4.2 },
                    { type: 'walking', distanceMeters: 100 }
                ]
            };
            const vmB = window.app.buildJourneyViewModelFromPlanned(tripWithSegmentKm, 'A', 'B');
            window.app.renderPlannerResults([tripWithSegmentKm]);
            const kmElB = document.getElementById('trip-stat-km')?.textContent?.trim();

            return {
                vmADistance: vmA.distanceKm,
                kmElA,
                vmBDistance: vmB.distanceKm,
                kmElB
            };
        })()
        """)
        print(f"   Case A (no segment km): distanceKm={res_dist['vmADistance']}, DOM='{res_dist['kmElA']}'")
        print(f"   Case B (with segment km 3.5 + 4.2): distanceKm={res_dist['vmBDistance']}, DOM='{res_dist['kmElB']}'")
        assert res_dist['vmADistance'] is None, f"Defect 6 FAIL: Planner distance must be null without segment km, got {res_dist['vmADistance']}"
        assert res_dist['kmElA'] == 'Chưa có dữ liệu', f"Defect 6 FAIL: DOM km must display 'Chưa có dữ liệu', got '{res_dist['kmElA']}'"
        assert res_dist['vmBDistance'] == 7.7, f"Defect 6 FAIL: Planner distance must sum segment distances (expected 7.7, got {res_dist['vmBDistance']})"
        assert '7.7 km' in res_dist['kmElB'], f"Defect 6 FAIL: DOM km must display 7.7 km, got '{res_dist['kmElB']}'"
        print("   [PASS] Check 6: Planner distance does not fake segment distance from full-route distance.")

        # -------------------------------------------------------------
        # Defect 7: Planner technical details reset direct schedule & truthful copy
        # -------------------------------------------------------------
        print("\n>> [Check 7] Planner technical details reset direct schedule & truthful semantics...")
        res_tech = runner.evaluate("""
        (() => {
            // Step 1: Search direct route with authentic schedule (Route 02) to populate legacy schedule fields
            window.app.showTripResults('Bến xe Phía Nam', 'Bến xe Trung tâm');
            const directLaterTime = document.getElementById('trip-later-time')?.textContent?.trim();
            const directLaterNote = document.getElementById('trip-later-note')?.textContent?.trim();
            const directDepLabel = document.getElementById('trip-departure-label')?.textContent?.trim();
            const directTransferText = document.getElementById('trip-direct-transfer-text')?.textContent?.trim();

            // Step 2: Now render a planner connecting result (2 legs, transfers: 1)
            const r02 = window.busService.getRouteById('02');
            const r05 = window.busService.getRouteById('05');
            const connectingTrip = {
                type: 'connecting',
                transfers: 1,
                totalDurationMinutes: 45,
                totalWalkingMeters: 200,
                fareText: '16.000đ',
                rankingCategory: 'Nhanh nhất',
                legs: [
                    { type: 'walking', distanceMeters: 100, durationMinutes: 2, fromLabel: 'Điểm A', toLabel: 'Trạm 1' },
                    { type: 'transit', routeNumber: '02', direction: 'outbound', route: r02, boardingStop: { name: 'Trạm 1' }, alightingStop: { name: 'Trạm 2' }, stopsCount: 4 },
                    { type: 'walking', distanceMeters: 100, durationMinutes: 2 },
                    { type: 'transit', routeNumber: '05', direction: 'outbound', route: r05, boardingStop: { name: 'Trạm 2' }, alightingStop: { name: 'Trạm 3' }, stopsCount: 3 },
                    { type: 'walking', distanceMeters: 0, durationMinutes: 0, toLabel: 'Điểm B' }
                ]
            };
            window.app.renderPlannerResults([connectingTrip]);

            // Step 3: Open #trip-secondary-details-card
            const techCard = document.getElementById('trip-secondary-details-card');
            const btnTech = document.getElementById('btn-toggle-tech-details');
            if (techCard && techCard.classList.contains('hidden') && btnTech) {
                btnTech.click();
            }

            // Step 4: Extract current values from technical details card
            const depLabel = document.getElementById('trip-departure-label')?.textContent?.trim();
            const countdownTime = document.getElementById('trip-countdown-time')?.textContent?.trim();
            const countdownTimer = document.getElementById('trip-countdown-timer')?.textContent?.trim();
            const directDescHidden = document.getElementById('trip-direct-transfer-desc')?.classList.contains('hidden');
            const directText = document.getElementById('trip-direct-transfer-text')?.textContent?.trim();
            const laterTime = document.getElementById('trip-later-time')?.textContent?.trim();
            const laterDiff = document.getElementById('trip-later-diff')?.textContent?.trim();
            const laterNote = document.getElementById('trip-later-note')?.textContent?.trim();
            const cardText = techCard?.textContent || '';
            const cardHidden = techCard?.classList.contains('hidden');

            return {
                directLaterTime,
                directLaterNote,
                directDepLabel,
                directTransferText,
                cardHidden,
                depLabel,
                countdownTime,
                countdownTimer,
                directDescHidden,
                directText,
                laterTime,
                laterDiff,
                laterNote,
                cardText,
                hasDirectClaim: cardText.includes('Đi thẳng suốt tuyến không đổi xe'),
                hasScheduleHeadingClaim: cardText.includes('Chuyến dự kiến theo lịch')
            };
        })()
        """)
        print(f"   Direct search initial: laterTime='{res_tech['directLaterTime']}', laterNote='{res_tech['directLaterNote']}', depLabel='{res_tech['directDepLabel']}'")
        print(f"   Connecting planner result: depLabel='{res_tech['depLabel']}', time='{res_tech['countdownTime']}', timer='{res_tech['countdownTimer']}'")
        print(f"   Connecting later: laterTime='{res_tech['laterTime']}', laterDiff='{res_tech['laterDiff']}', laterNote='{res_tech['laterNote']}'")
        print(f"   Direct transfer row: hidden={res_tech['directDescHidden']}, text='{res_tech['directText']}', hasClaim={res_tech['hasDirectClaim']}")

        # 1. Assert card opened
        assert res_tech['cardHidden'] is False, "Defect 7 FAIL: #trip-secondary-details-card should be opened after clicking toggle!"

        # 2. Assert direct result time/note is NOT leaked into planner
        assert res_tech['laterTime'] != res_tech['directLaterTime'], f"Defect 7 FAIL: laterTime still contains leaked direct time: '{res_tech['laterTime']}'"
        assert res_tech['laterNote'] != res_tech['directLaterNote'], f"Defect 7 FAIL: laterNote still contains leaked direct note: '{res_tech['laterNote']}'"
        assert res_tech['laterNote'] != 'Xuất bến theo lịch trình công bố', f"Defect 7 FAIL: connecting trip must not retain static note 'Xuất bến theo lịch trình công bố'!"
        assert res_tech['laterTime'] == 'Chưa có dữ liệu', f"Defect 7 FAIL: connecting trip laterTime must fail-closed to 'Chưa có dữ liệu', got '{res_tech['laterTime']}'"
        assert res_tech['laterNote'] == 'Chưa có dữ liệu', f"Defect 7 FAIL: connecting trip laterNote must fail-closed to 'Chưa có dữ liệu', got '{res_tech['laterNote']}'"
        assert res_tech['laterDiff'] == '', f"Defect 7 FAIL: connecting trip laterDiff must be empty, got '{res_tech['laterDiff']}'"

        # 3. Assert no 'Đi thẳng suốt tuyến không đổi xe' for connecting trip
        assert res_tech['directDescHidden'] is True, "Defect 7 FAIL: #trip-direct-transfer-desc must be hidden for connecting trip!"
        assert not res_tech['hasDirectClaim'], "Defect 7 FAIL: secondary card must not contain 'Đi thẳng suốt tuyến không đổi xe' for connecting trip!"

        # 4. Assert planner duration labeled 'Ước tính', NOT under 'Chuyến dự kiến theo lịch'
        assert '~45p' in res_tech['countdownTime'], f"Defect 7 FAIL: countdownTime should show '~45p', got '{res_tech['countdownTime']}'"
        assert 'Ước tính' in res_tech['depLabel'], f"Defect 7 FAIL: departure label must contain 'Ước tính', got '{res_tech['depLabel']}'"
        assert not res_tech['hasScheduleHeadingClaim'], "Defect 7 FAIL: secondary card must not contain 'Chuyến dự kiến theo lịch' when displaying planner duration!"

        # 5. Assert missing next-departure/schedule fails-closed to 'Chưa có dữ liệu'
        assert res_tech['countdownTimer'] == 'Chưa có dữ liệu', f"Defect 7 FAIL: connecting trip timer pill must fail-closed to 'Chưa có dữ liệu', got '{res_tech['countdownTimer']}'"

        print("   [PASS] Check 7: Planner technical details reset direct schedule & enforce truthful semantics.")

        print("\n" + "=" * 70)
        print("ALL 7 REVIEW DEFECT REGRESSION TESTS PASSED STRICTLY (7/7 PASS)")
        print("=" * 70)
    finally:
        runner.stop()

if __name__ == "__main__":
    run_tests()
