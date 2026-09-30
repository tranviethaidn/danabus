#!/usr/bin/env python3
"""
TASK 7 AUTOMATED ACCEPTANCE TEST SUITE: SCHEDULE & FARE CORRECTNESS
Verifies:
1. calculateNextDeparture 5-status contract:
   - before_service (e.g. 00:46 -> 05:15 = 269 min, no headway modulo)
   - in_service (within service window, isOperating=True)
   - after_service (service ended today, no reliable next-day -> timeStr=null, minutes=null)
   - next_day (service ended today, reliable next-day -> isNextDay=True, accurate minutes)
   - unknown (suspended route, malformed operatingHours -> fail-closed, no fake 08:30/6p)
2. Timetable priority over synthetic headway
3. Service cutoff boundary (no infinite headway after closing)
4. Deterministic time injection support
5. Fare schema & classification (flat, distance_tiered, unknown)
6. Tiered fare integrity: singleTicket is null, no fake flat rate
7. Unknown fare fail-closed: Route 09 & 13 return 'Đang cập nhật', no fake 8k-30k/30.000đ
8. Flat fare provenance: Subsidized 8.000đ, Commercial LK01 80.000đ, 01SB 120.000đ
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent


class TestScheduleAndFare(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(WORKSPACE / "data" / "danangbus_routes.json", encoding="utf-8") as f:
            cls.routes = json.load(f)
        cls.routes_by_id = {r["id"]: r for r in cls.routes}

    # -------------------------------------------------------------------------
    # 1. Dataset & Schema Integrity Tests
    # -------------------------------------------------------------------------
    def test_all_23_routes_have_fare_info(self):
        """All 23 routes must have properly structured fare information."""
        self.assertEqual(len(self.routes), 23)
        for r in self.routes:
            fares = r.get("fares")
            self.assertIsNotNone(fares, f"Route {r['id']} missing fares object")
            self.assertIn(fares.get("type"), ["flat", "distance_tiered", "unknown"])

    def test_single_ticket_only_on_flat_routes(self):
        """singleTicket must only be set on flat routes and must match flatPrice; tiered/unknown must be null."""
        for r in self.routes:
            f = r.get("fares", {})
            ftype = f.get("type")
            st = f.get("singleTicket")
            if ftype == "flat":
                self.assertIsNotNone(st, f"Flat route {r['id']} must have singleTicket")
                self.assertEqual(st, f.get("flatPrice"), f"Route {r['id']} singleTicket must match flatPrice")
            else:
                self.assertIsNone(
                    st,
                    f"Non-flat route {r['id']} (type={ftype}) must have singleTicket=None, got {st}"
                )

    def test_tiered_fare_02_and_06_integrity(self):
        """Routes 02 and 06 must be distance_tiered with exact price ranges and null singleTicket."""
        r02 = self.routes_by_id["02"]["fares"]
        self.assertEqual(r02["type"], "distance_tiered")
        self.assertIsNone(r02["singleTicket"])
        self.assertEqual(r02["minPrice"], 8000)
        self.assertEqual(r02["maxPrice"], 30000)
        self.assertEqual(r02["studentPrice"], 8000)
        self.assertTrue(len(r02.get("tiers", [])) >= 3)

        r06 = self.routes_by_id["06"]["fares"]
        self.assertEqual(r06["type"], "distance_tiered")
        self.assertIsNone(r06["singleTicket"])
        self.assertEqual(r06["minPrice"], 15000)
        self.assertEqual(r06["maxPrice"], 22000)
        self.assertEqual(r06["studentPrice"], 8000)
        self.assertTrue(len(r06.get("tiers", [])) >= 2)

    def test_unknown_fare_routes_09_and_13(self):
        """Routes 09 and 13 lack price data in raw summary and must be marked unknown."""
        for r_id in ["09", "13"]:
            f = self.routes_by_id[r_id]["fares"]
            self.assertEqual(f["type"], "unknown")
            self.assertIsNone(f["singleTicket"])
            self.assertIsNone(f["minPrice"])
            self.assertIsNone(f["maxPrice"])
            self.assertEqual(f.get("provenance", {}).get("source"), "unknown")

    def test_subsidized_and_commercial_flat_fare_integrity(self):
        """Subsidized routes must be flat 8.000đ; LK01 must be 80.000đ; 01SB must be 120.000đ."""
        for r_id in ["05", "07", "08", "11", "12", "04", "10", "15"]:
            f = self.routes_by_id[r_id]["fares"]
            self.assertEqual(f["type"], "flat")
            self.assertEqual(f["flatPrice"], 8000)
            self.assertEqual(f["singleTicket"], 8000)

        f_lk01 = self.routes_by_id["LK01"]["fares"]
        self.assertEqual(f_lk01["type"], "flat")
        self.assertEqual(f_lk01["flatPrice"], 80000)
        self.assertEqual(f_lk01["singleTicket"], 80000)

        f_01sb = self.routes_by_id["01SB"]["fares"]
        self.assertEqual(f_01sb["type"], "flat")
        self.assertEqual(f_01sb["flatPrice"], 120000)
        self.assertEqual(f_01sb["singleTicket"], 120000)

    def test_missing_and_invalid_frequency_fail_closed(self):
        """Missing, empty, zero, negative or non-numeric frequency must fail-closed to unknown."""
        js_code = """
        const { BusService } = require('./js/busService.js');
        const bs = new BusService();
        const base = { id: 'syn', operatingHours: { start: '05:30', end: '19:00' } };
        const cases = [
            undefined,
            {},
            { peakMinutes: 0 },
            { peakMinutes: -5 },
            { peakMinutes: 'abc' },
            { peakMinutes: NaN },
            { peakMinutes: null },
            { peakMinutes: 0, offPeakMinutes: 0 }
        ];
        const results = cases.map(freq => {
            const res = bs.calculateNextDeparture({ ...base, frequency: freq }, { currentTime: '08:00' });
            return (res.status === 'unknown' && res.timeStr === null && res.minutesUntilDeparture === null && res.isOperating === false);
        });
        console.log(JSON.stringify(results));
        """
        proc = subprocess.run(
            ["node", "-e", js_code],
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            check=True
        )
        results = json.loads(proc.stdout.strip())
        self.assertTrue(all(results), f"Some invalid frequency cases did not fail-closed: {results}")

    def test_route_02_frequency_and_views_consistency(self):
        """Route 02 frequency must be range 15-30 with no 30-only or 15-only discrepancy."""
        r02 = self.routes_by_id["02"]
        freq = r02["frequency"]
        self.assertEqual(freq["raw"], "15-30 phút/lượt.")
        self.assertEqual(freq["type"], "range")
        self.assertEqual(freq["minMinutes"], 15)
        self.assertEqual(freq["maxMinutes"], 30)
        self.assertFalse(freq["exactHeadway"])

    def test_irregular_routes_before_service_fail_safe(self):
        """Irregular routes before service window must return before_service with timeStr=null and minutesUntilDeparture=null."""
        js_code = """
        const { BusService } = require('./js/busService.js');
        const fs = require('fs');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const bs = new BusService();
        const r01sb = routes.find(r => r.id === '01SB');
        const rTkyChu = routes.find(r => r.id === 'TKY-CHU');
        const r01dl = routes.find(r => r.id === '01DL');

        const dep01sb = bs.calculateNextDeparture(r01sb, { currentTime: '04:00' });
        const depTkyChu = bs.calculateNextDeparture(rTkyChu, { currentTime: '04:00' });
        const dep01dl = bs.calculateNextDeparture(r01dl, { currentTime: '07:00' });

        const results = {
            '01SB': dep01sb.status === 'before_service' &&
                    dep01sb.timeStr === null &&
                    dep01sb.minutesUntilDeparture === null &&
                    dep01sb.minutesLeft === null &&
                    dep01sb.isOperating === false &&
                    dep01sb.isNextDay === false &&
                    !dep01sb.message.includes('chuyến đầu') &&
                    dep01sb.message.includes('Chưa đến khung giờ hoạt động'),
            'TKY-CHU': depTkyChu.status === 'before_service' &&
                       depTkyChu.timeStr === null &&
                       depTkyChu.minutesUntilDeparture === null &&
                       depTkyChu.minutesLeft === null &&
                       depTkyChu.isOperating === false &&
                       depTkyChu.isNextDay === false &&
                       !depTkyChu.message.includes('chuyến đầu') &&
                       depTkyChu.message.includes('Chưa đến khung giờ hoạt động'),
            '01DL': dep01dl.status === 'before_service' &&
                    dep01dl.timeStr === null &&
                    dep01dl.minutesUntilDeparture === null &&
                    dep01dl.minutesLeft === null &&
                    dep01dl.isOperating === false &&
                    dep01dl.isNextDay === false &&
                    !dep01dl.message.includes('chuyến đầu') &&
                    dep01dl.message.includes('Chưa đến khung giờ hoạt động')
        };
        console.log(JSON.stringify(results));
        """
        proc = subprocess.run(
            ["node", "-e", js_code],
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            check=True
        )
        res = json.loads(proc.stdout.strip())
        for k, v in res.items():
            self.assertTrue(v, f"Irregular before_service check failed for {k}")

    # -------------------------------------------------------------------------
    # 2. Node.js BusService Integration Verification
    # -------------------------------------------------------------------------
    def test_nodejs_busservice_contract(self):
        """Directly verify BusService.js methods in Node.js runtime."""
        js_code = """
        const { BusService } = require('./js/busService.js');
        const fs = require('fs');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));

        const bs = new BusService();
        bs.routes = routes;
        const r02 = routes.find(r => r.id === '02');
        const r06 = routes.find(r => r.id === '06');
        const r09 = routes.find(r => r.id === '09');
        const r13 = routes.find(r => r.id === '13');
        const r05 = routes.find(r => r.id === '05');
        const r01sb = routes.find(r => r.id === '01SB');
        const rTkyTmy = routes.find(r => r.id === 'TKY-TMY');
        const rSuspended = routes.find(r => r.id === '04');

        const results = [];

        // 1. Before service window: 00:46 on Route 02 (start 05:15 = 315 min) -> 269 min exactly
        const depBefore = bs.calculateNextDeparture(r02, { currentTime: '00:46' });
        results.push({
            name: 'before_service_269_min',
            passed: depBefore.status === 'before_service' &&
                    depBefore.minutesUntilDeparture === 269 &&
                    depBefore.timeStr === '05:15' &&
                    depBefore.isOperating === false &&
                    depBefore.isNextDay === false
        });

        // 2. In service window (range route without exact headway): 08:00 on Route 02 (15-30 min) -> no false precision
        const depIn = bs.calculateNextDeparture(r02, { currentTime: '08:00' });
        results.push({
            name: 'in_service_window_range_fail_safe',
            passed: depIn.status === 'in_service' &&
                    depIn.isOperating === true &&
                    depIn.timeStr === null &&
                    depIn.minutesUntilDeparture === null &&
                    depIn.isNextDay === false &&
                    depIn.message.includes('15-30 phút')
        });

        // 2b. In service window (exact headway route): 30m fixed headway at 07:10 (start 06:00, end 18:00) -> 07:30 (20 min)
        const rFixed = {
            id: 'fixed_test',
            status: 'active',
            sourceUrl: 'https://www.danangbus.vn/lo-trinh-tuyen.html',
            lastVerifiedAt: '2026-09-30',
            verificationStatus: 'verified',
            operatingHours: { start: '06:00', end: '18:00' },
            frequency: { type: 'fixed', exactHeadway: true, peakMinutes: 30, offPeakMinutes: 30, raw: '30 phút/chuyến' }
        };
        const depFixed = bs.calculateNextDeparture(rFixed, { currentTime: '07:10' });
        results.push({
            name: 'in_service_exact_headway',
            passed: depFixed.status === 'in_service' &&
                    depFixed.isOperating === true &&
                    depFixed.timeStr === '07:30' &&
                    depFixed.minutesUntilDeparture === 20 &&
                    depFixed.isNextDay === false
        });

        // 3. Next day: 20:00 on Route 02 (after closing 18:30) -> 05:15 tomorrow (555 min)
        const depNextDay = bs.calculateNextDeparture(r02, { currentTime: '20:00' });
        results.push({
            name: 'next_day_departure',
            passed: depNextDay.status === 'next_day' &&
                    depNextDay.isOperating === false &&
                    depNextDay.isNextDay === true &&
                    depNextDay.timeStr === '05:15' &&
                    depNextDay.minutesUntilDeparture === 555
        });

        // 4. After service without next day: allowNextDay = false
        const depAfterService = bs.calculateNextDeparture(r02, { currentTime: '20:00', allowNextDay: false });
        results.push({
            name: 'after_service_no_next_day',
            passed: depAfterService.status === 'after_service' &&
                    depAfterService.isOperating === false &&
                    depAfterService.isNextDay === false &&
                    depAfterService.timeStr === null &&
                    depAfterService.minutesUntilDeparture === null
        });

        // 5. Irregular schedule after hours: 01SB is flight-dependent, after 22:00 returns after_service
        const dep01sb = bs.calculateNextDeparture(r01sb, { currentTime: '23:00' });
        results.push({
            name: 'irregular_flight_after_service',
            passed: dep01sb.status === 'after_service' &&
                    dep01sb.isOperating === false &&
                    dep01sb.timeStr === null &&
                    dep01sb.minutesUntilDeparture === null
        });

        // 5b. Irregular schedule before service: 01SB and TKY-CHU before service window -> before_service with timeStr=null and minutesUntilDeparture=null
        const dep01sbBefore = bs.calculateNextDeparture(r01sb, { currentTime: '04:00' });
        const rTkyChu = routes.find(r => r.id === 'TKY-CHU');
        const depTkyChuBefore = bs.calculateNextDeparture(rTkyChu, { currentTime: '04:00' });
        results.push({
            name: 'irregular_routes_before_service',
            passed: dep01sbBefore.status === 'before_service' &&
                    dep01sbBefore.timeStr === null &&
                    dep01sbBefore.minutesUntilDeparture === null &&
                    !dep01sbBefore.message.includes('chuyến đầu') &&
                    depTkyChuBefore.status === 'before_service' &&
                    depTkyChuBefore.timeStr === null &&
                    depTkyChuBefore.minutesUntilDeparture === null &&
                    !depTkyChuBefore.message.includes('chuyến đầu')
        });

        // 6. Timetable priority: Route TKY-TMY has outbound timetable ['5:00', '5:35', '6:10', ...]
        const depTt = bs.calculateNextDeparture(rTkyTmy, { currentTime: '05:10' });
        results.push({
            name: 'timetable_priority_05_35',
            passed: depTt.status === 'in_service' &&
                    depTt.source === 'timetable' &&
                    depTt.timeStr === '05:35' &&
                    depTt.minutesUntilDeparture === 25
        });

        // 7. Service cutoff boundary: Route 02 ends 18:30. At 18:35 next departure is tomorrow 05:15
        const depCutoff = bs.calculateNextDeparture(r02, { currentTime: '18:35' });
        results.push({
            name: 'service_cutoff_boundary',
            passed: depCutoff.status === 'next_day' &&
                    depCutoff.isOperating === false &&
                    depCutoff.isNextDay === true &&
                    depCutoff.timeStr === '05:15'
        });

        // 8. Malformed / Suspended schedule: fail-closed to unknown without fake 08:30/6p
        const depSuspended = bs.calculateNextDeparture(rSuspended);
        const depMalformed = bs.calculateNextDeparture({ id: 'bad', operatingHours: { start: 'abc' } });
        const depEmpty = bs.calculateNextDeparture(null);
        results.push({
            name: 'malformed_schedule_fail_closed',
            passed: depSuspended.status === 'unknown' && depSuspended.timeStr === null &&
                    depMalformed.status === 'unknown' && depMalformed.timeStr === null &&
                    depEmpty.status === 'unknown' && depEmpty.timeStr === null
        });

        // 8b. Frequency missing/empty/zero/non-numeric: fail-closed to unknown (NO default 15m)
        const rBase = { id: 'test_freq', operatingHours: { start: '05:30', end: '19:00' } };
        const depFreqMissing = bs.calculateNextDeparture({ ...rBase }, { currentTime: '08:00' });
        const depFreqEmpty = bs.calculateNextDeparture({ ...rBase, frequency: {} }, { currentTime: '08:00' });
        const depFreqZero = bs.calculateNextDeparture({ ...rBase, frequency: { peakMinutes: 0 } }, { currentTime: '08:00' });
        const depFreqNonNum = bs.calculateNextDeparture({ ...rBase, frequency: { peakMinutes: 'abc' } }, { currentTime: '08:00' });
        const depFreqNeg = bs.calculateNextDeparture({ ...rBase, frequency: { peakMinutes: -10 } }, { currentTime: '08:00' });
        const depFreqBothZero = bs.calculateNextDeparture({ ...rBase, frequency: { peakMinutes: 0, offPeakMinutes: 0 } }, { currentTime: '08:00' });

        const freqFailClosed = [depFreqMissing, depFreqEmpty, depFreqZero, depFreqNonNum, depFreqNeg, depFreqBothZero].every(
            d => d.status === 'unknown' && d.timeStr === null && d.minutesUntilDeparture === null && d.isOperating === false
        );

        results.push({
            name: 'frequency_missing_or_invalid_fail_closed',
            passed: freqFailClosed
        });

        // 8c. Format route frequency helper: valid vs invalid/missing
        const freqFmtCheck = (
            bs.formatRouteFrequency(r02) === '15-30 phút' &&
            bs.formatRouteFrequency(r02, true) === '15-30p' &&
            bs.formatRouteFrequency({ frequency: { type: 'fixed', peakMinutes: 30, offPeakMinutes: 30 } }) === '30 phút' &&
            bs.formatRouteFrequency({ frequency: { type: 'irregular', raw: 'Theo lịch bay Cảng hàng không Quốc tế Đà Nẵng' } }) === 'Theo lịch bay' &&
            bs.formatRouteFrequency({ frequency: { type: 'irregular', raw: 'Theo lịch bay Cảng hàng không Quốc tế Đà Nẵng' } }, true) === 'Lịch bay' &&
            bs.formatRouteFrequency({ frequency: {} }) === 'Đang cập nhật' &&
            bs.formatRouteFrequency({ frequency: { peakMinutes: 0 } }) === 'Đang cập nhật' &&
            bs.formatRouteFrequency({ frequency: { peakMinutes: 'abc' } }) === 'Đang cập nhật' &&
            bs.formatRouteFrequency(null) === 'Đang cập nhật'
        );
        results.push({
            name: 'format_route_frequency_helper',
            passed: freqFmtCheck
        });

        // 9. Format fare helper: Tiered route 02 and 06
        results.push({
            name: 'format_tiered_fare_02',
            passed: bs.formatRouteFare(r02) === '8.000đ - 30.000đ'
        });
        results.push({
            name: 'format_tiered_fare_06',
            passed: bs.formatRouteFare(r06) === '15.000đ - 22.000đ'
        });

        // 10. Format fare helper: Unknown fare routes 09 & 13 -> 'Đang cập nhật', no fake 8k-30k/30.000đ
        results.push({
            name: 'format_unknown_fare_fail_closed',
            passed: bs.formatRouteFare(r09) === 'Đang cập nhật' &&
                    bs.formatRouteFare(r13) === 'Đang cập nhật'
        });

        // 11. Format fare helper: Subsidized 05 -> '8.000đ'
        results.push({
            name: 'format_subsidized_fare',
            passed: bs.formatRouteFare(r05) === '8.000đ'
        });

        console.log(JSON.stringify(results));
        """
        proc = subprocess.run(
            ["node", "-e", js_code],
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            check=True
        )
        results = json.loads(proc.stdout.strip())
        for r in results:
            self.assertTrue(r["passed"], f"Node.js check failed: {r['name']}")


def main():
    print("=" * 70)
    print("TASK 7 AUTOMATED ACCEPTANCE TEST SUITE: SCHEDULE & FARE CORRECTNESS")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestScheduleAndFare)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
    print("\n" + "=" * 70)
    print("ALL TASK 7 ACCEPTANCE CRITERIA STRICTLY VERIFIED (100% PASS)")
    print("=" * 70)


if __name__ == "__main__":
    main()
