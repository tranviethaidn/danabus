#!/usr/bin/env python3
"""
scripts/test_temporal_route_service.py
Task 006 / Roadmap V3 Task 1 Acceptance Test Suite:
Official Route Data Reconciliation & Temporal Service Model

Automated verification of:
1. Active verified route usability
2. Suspended route rejection
3. Retired route rejection
4. Merged route rejection
5. Future effectiveFrom fail-closed
6. Expired effectiveTo fail-closed
7. Exact temporal boundaries with timezone (+07:00) handling
8. Temporary suspension lifecycle (before/during/after)
9. Active detour without verified replacement (direction fail-closed) vs with replacement truth
10. Expired override ignored cleanly
11. Malformed override fail-closed
12. Missing provenance planner ineligibility
13. Canonical ID precedence
14. Former code and alias resolution
15. Ambiguous route number / alias fail-closed (no arbitrary tie-break)
16. Broken successor references and cycle detection
17. Machine-readable reconciliation report dynamic computation
"""

import os
import sys
import json
import unittest
import subprocess

WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROUTES_PATH = os.path.join(WORKSPACE, "data/danangbus_routes.json")
REPORT_PATH = os.path.join(WORKSPACE, "docs/reports/task-1-official-route-reconciliation.json")


def run_node_eval(script):
    """Executes javascript code in node.js runtime and returns parsed JSON stdout."""
    res = subprocess.run(
        ["node", "-e", script],
        cwd=WORKSPACE,
        capture_output=True,
        text=True
    )
    if res.returncode != 0:
        raise RuntimeError(f"Node execution failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
    return json.loads(res.stdout.strip())


class TestTemporalRouteService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(ROUTES_PATH, "r", encoding="utf-8") as f:
            cls.routes = json.load(f)
        cls.routes_by_id = {r["id"]: r for r in cls.routes}

    # -------------------------------------------------------------------------
    # 1. Lifecycle and Active/Suspended State Tests
    # -------------------------------------------------------------------------
    def test_active_verified_route(self):
        """Active verified route must be usable with isServiceUsable=True."""
        js = """
        const { BusService } = require('./js/busService.js');
        const fs = require('fs');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        const r05 = bs.getRouteById('05');
        const state = bs.getServiceTemporalState(r05, new Date());
        console.log(JSON.stringify({
            isUsable: state.isUsable,
            status: state.status,
            effectiveStatus: state.effectiveStatus,
            helperUsable: bs.isServiceUsable(r05)
        }));
        """
        res = run_node_eval(js)
        self.assertTrue(res["isUsable"])
        self.assertEqual(res["status"], "active")
        self.assertEqual(res["effectiveStatus"], "active")
        self.assertTrue(res["helperUsable"])

    def test_suspended_route(self):
        """Suspended routes (04, 10, 15) must be unusable (fail closed)."""
        js = """
        const { BusService } = require('./js/busService.js');
        const fs = require('fs');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        const results = ['04', '10', '15'].map(id => {
            const r = bs.getRouteById(id);
            const state = bs.getServiceTemporalState(r, new Date());
            const usable = bs.isServiceUsable(r);
            const dep = bs.calculateNextDeparture(r);
            return { id, isUsable: state.isUsable, status: state.status, usable, depStatus: dep.status };
        });
        console.log(JSON.stringify(results));
        """
        results = run_node_eval(js)
        for r in results:
            self.assertFalse(r["isUsable"], f"Route {r['id']} must not be usable")
            self.assertEqual(r["status"], "suspended")
            self.assertFalse(r["usable"])
            self.assertEqual(r["depStatus"], "unknown")

    def test_retired_route(self):
        """Retired route must fail closed with status='retired'."""
        js = """
        const { BusService } = require('./js/busService.js');
        const bs = new BusService();
        const rRetired = {
            id: 'RET_01',
            status: 'retired',
            statusNote: 'Tuyến ngừng hoạt động vĩnh viễn từ 2024',
            sourceUrl: 'https://www.danangbus.vn',
            lastVerifiedAt: '2026-09-30',
            verificationStatus: 'verified'
        };
        const state = bs.getServiceTemporalState(rRetired, new Date());
        console.log(JSON.stringify({ isUsable: state.isUsable, status: state.status, reason: state.reason }));
        """
        res = run_node_eval(js)
        self.assertFalse(res["isUsable"])
        self.assertEqual(res["status"], "retired")
        self.assertIn("vĩnh viễn", res["reason"])

    def test_merged_route(self):
        """Merged route must fail closed with status='merged'."""
        js = """
        const { BusService } = require('./js/busService.js');
        const bs = new BusService();
        const rMerged = {
            id: 'MRG_01',
            status: 'merged',
            mergedInto: '09',
            statusNote: 'Đã sáp nhập vào tuyến 09',
            sourceUrl: 'https://www.danangbus.vn',
            lastVerifiedAt: '2026-09-30',
            verificationStatus: 'verified'
        };
        const state = bs.getServiceTemporalState(rMerged, new Date());
        console.log(JSON.stringify({ isUsable: state.isUsable, status: state.status, reason: state.reason }));
        """
        res = run_node_eval(js)
        self.assertFalse(res["isUsable"])
        self.assertEqual(res["status"], "merged")
        self.assertIn("sáp nhập", res["reason"])

    # -------------------------------------------------------------------------
    # 2. Permanent Temporal Validity & Timezone Tests
    # -------------------------------------------------------------------------
    def test_future_effective_from(self):
        """Route with future effectiveFrom must fail closed before that date."""
        js = """
        const { BusService } = require('./js/busService.js');
        const bs = new BusService();
        const rFuture = {
            id: 'FUT_01',
            status: 'active',
            effectiveFrom: '2026-10-15T00:00:00+07:00',
            sourceUrl: 'https://www.danangbus.vn',
            lastVerifiedAt: '2026-09-30',
            verificationStatus: 'verified'
        };
        const before = bs.getServiceTemporalState(rFuture, '2026-10-14T23:59:59+07:00');
        const at = bs.getServiceTemporalState(rFuture, '2026-10-15T00:00:00+07:00');
        const after = bs.getServiceTemporalState(rFuture, '2026-10-16T12:00:00+07:00');
        console.log(JSON.stringify({
            beforeUsable: before.isUsable,
            beforeStatus: before.status,
            atUsable: at.isUsable,
            afterUsable: after.isUsable
        }));
        """
        res = run_node_eval(js)
        self.assertFalse(res["beforeUsable"])
        self.assertEqual(res["beforeStatus"], "future")
        self.assertTrue(res["atUsable"])
        self.assertTrue(res["afterUsable"])

    def test_expired_effective_to(self):
        """Route with expired effectiveTo must fail closed after that date."""
        js = """
        const { BusService } = require('./js/busService.js');
        const bs = new BusService();
        const rExpired = {
            id: 'EXP_01',
            status: 'active',
            effectiveTo: '2026-09-01T23:59:59+07:00',
            sourceUrl: 'https://www.danangbus.vn',
            lastVerifiedAt: '2026-09-30',
            verificationStatus: 'verified'
        };
        const before = bs.getServiceTemporalState(rExpired, '2026-09-01T12:00:00+07:00');
        const at = bs.getServiceTemporalState(rExpired, '2026-09-01T23:59:59+07:00');
        const after = bs.getServiceTemporalState(rExpired, '2026-09-02T00:00:01+07:00');
        console.log(JSON.stringify({
            beforeUsable: before.isUsable,
            atUsable: at.isUsable,
            afterUsable: after.isUsable,
            afterStatus: after.status
        }));
        """
        res = run_node_eval(js)
        self.assertTrue(res["beforeUsable"])
        self.assertTrue(res["atUsable"])
        self.assertFalse(res["afterUsable"])
        self.assertEqual(res["afterStatus"], "expired")

    def test_exact_temporal_boundaries_with_timezone(self):
        """Date-only 'YYYY-MM-DD' must be parsed with explicit local ICT (+07:00) timezone."""
        js = """
        const { BusService } = require('./js/busService.js');
        const bs = new BusService();
        const r = {
            id: 'TZ_01',
            status: 'active',
            effectiveFrom: '2026-10-01',
            effectiveTo: '2026-10-03',
            sourceUrl: 'https://www.danangbus.vn',
            lastVerifiedAt: '2026-09-30',
            verificationStatus: 'verified'
        };
        // 2026-10-01T00:30:00+07:00 is within day 1 in Vietnam time
        const day1Early = bs.getServiceTemporalState(r, '2026-10-01T00:30:00+07:00');
        // 2026-09-30T23:59:00+07:00 is 1 minute before effectiveFrom
        const beforeDay1 = bs.getServiceTemporalState(r, '2026-09-30T23:59:00+07:00');
        // 2026-10-03T23:59:00+07:00 is within effectiveTo (end of day)
        const day3Late = bs.getServiceTemporalState(r, '2026-10-03T23:59:00+07:00');
        // 2026-10-04T00:01:00+07:00 is after effectiveTo
        const day4Early = bs.getServiceTemporalState(r, '2026-10-04T00:01:00+07:00');

        console.log(JSON.stringify({
            day1Early: day1Early.isUsable,
            beforeDay1: beforeDay1.isUsable,
            day3Late: day3Late.isUsable,
            day4Early: day4Early.isUsable
        }));
        """
        res = run_node_eval(js)
        self.assertTrue(res["day1Early"])
        self.assertFalse(res["beforeDay1"])
        self.assertTrue(res["day3Late"])
        self.assertFalse(res["day4Early"])

    # -------------------------------------------------------------------------
    # 3. Temporary Service Overrides
    # -------------------------------------------------------------------------
    def test_temporary_suspension_lifecycle(self):
        """Temporary suspension must apply during window and expire cleanly afterwards."""
        js = """
        const { BusService } = require('./js/busService.js');
        const fs = require('fs');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        const r05 = JSON.parse(JSON.stringify(bs.getRouteById('05')));
        r05.temporaryOverrides = [{
            id: 'ovr_flood_05',
            type: 'suspension',
            reason: 'Tạm dừng do ngập lụt bão lũ',
            effectiveFrom: '2026-10-10T00:00:00+07:00',
            effectiveTo: '2026-10-12T23:59:59+07:00'
        }];

        const before = bs.getServiceTemporalState(r05, '2026-10-09T18:00:00+07:00');
        const during = bs.getServiceTemporalState(r05, '2026-10-11T10:00:00+07:00');
        const after = bs.getServiceTemporalState(r05, '2026-10-13T06:00:00+07:00');

        console.log(JSON.stringify({
            beforeUsable: before.isUsable,
            duringUsable: during.isUsable,
            duringEffStatus: during.effectiveStatus,
            duringReason: during.reason,
            afterUsable: after.isUsable
        }));
        """
        res = run_node_eval(js)
        self.assertTrue(res["beforeUsable"], "Route must be usable before override")
        self.assertFalse(res["duringUsable"], "Route must fail closed during suspension override")
        self.assertEqual(res["duringEffStatus"], "suspended")
        self.assertIn("ngập lụt", res["duringReason"])
        self.assertTrue(res["afterUsable"], "Route must be restored cleanly after override expires")

    def test_active_detour_without_replacement_fails_closed_by_direction(self):
        """Active detour with hasReplacementTruth=false must fail closed for affected direction only."""
        js = """
        const { BusService } = require('./js/busService.js');
        const fs = require('fs');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        const r05 = JSON.parse(JSON.stringify(bs.getRouteById('05')));
        r05.temporaryOverrides = [{
            id: 'ovr_bridge_detour_05',
            type: 'detour',
            reason: 'Sửa chữa cầu Sông Hàn, điều chỉnh lộ trình chiều đi',
            effectiveFrom: '2026-10-01T00:00:00+07:00',
            effectiveTo: '2026-10-05T23:59:59+07:00',
            affectedDirections: ['outbound'],
            hasReplacementTruth: false
        }];

        const t = '2026-10-02T10:00:00+07:00';
        const outState = bs.getServiceTemporalState(r05, t, 'outbound');
        const inState = bs.getServiceTemporalState(r05, t, 'inbound');

        // Test with replacement truth verified
        r05.temporaryOverrides[0].hasReplacementTruth = true;
        const outWithTruth = bs.getServiceTemporalState(r05, t, 'outbound');

        console.log(JSON.stringify({
            outUsable: outState.isUsable,
            outStatus: outState.effectiveStatus,
            inUsable: inState.isUsable,
            outWithTruthUsable: outWithTruth.isUsable
        }));
        """
        res = run_node_eval(js)
        self.assertFalse(res["outUsable"], "Outbound direction must fail closed without verified replacement truth")
        self.assertEqual(res["outStatus"], "detour_unverified")
        self.assertTrue(res["inUsable"], "Inbound direction is unaffected and must remain usable")
        self.assertTrue(res["outWithTruthUsable"], "Outbound must be usable when replacement truth is verified")

    def test_expired_override_ignored(self):
        """Overrides whose effectiveTo is in the past must be completely ignored."""
        js = """
        const { BusService } = require('./js/busService.js');
        const fs = require('fs');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        const r05 = JSON.parse(JSON.stringify(bs.getRouteById('05')));
        r05.temporaryOverrides = [{
            id: 'ovr_past_05',
            type: 'suspension',
            reason: 'Sự cố cũ',
            effectiveFrom: '2026-08-01T00:00:00+07:00',
            effectiveTo: '2026-08-05T23:59:59+07:00'
        }];
        const state = bs.getServiceTemporalState(r05, '2026-09-30T10:00:00+07:00');
        console.log(JSON.stringify({ isUsable: state.isUsable, activeOverride: state.activeOverride }));
        """
        res = run_node_eval(js)
        self.assertTrue(res["isUsable"])
        self.assertIsNone(res["activeOverride"])

    def test_malformed_override_fail_closed(self):
        """Malformed override (effectiveFrom > effectiveTo or invalid dates) must fail closed."""
        js = """
        const { BusService } = require('./js/busService.js');
        const fs = require('fs');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        const r05 = JSON.parse(JSON.stringify(bs.getRouteById('05')));
        r05.temporaryOverrides = [{
            id: 'ovr_bad_dates',
            type: 'suspension',
            reason: 'Lỗi cấu hình',
            effectiveFrom: '2026-10-10T00:00:00+07:00',
            effectiveTo: '2026-10-01T00:00:00+07:00' // inverted dates
        }];
        const state = bs.getServiceTemporalState(r05, '2026-10-05T10:00:00+07:00');
        console.log(JSON.stringify({ isUsable: state.isUsable, status: state.status }));
        """
        res = run_node_eval(js)
        self.assertFalse(res["isUsable"])
        self.assertEqual(res["status"], "malformed_override")

    # -------------------------------------------------------------------------
    # 4. Provenance and Validation Fail-Closed Tests
    # -------------------------------------------------------------------------
    def test_missing_provenance_planner_ineligible(self):
        """Route missing sourceUrl or lastVerifiedAt or unverified must fail closed for planning."""
        js = """
        const { BusService } = require('./js/busService.js');
        const fs = require('fs');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;

        // Route 05 with sourceUrl removed
        const rNoUrl = JSON.parse(JSON.stringify(bs.getRouteById('05')));
        delete rNoUrl.sourceUrl;
        const stateNoUrl = bs.getServiceTemporalState(rNoUrl, new Date());

        // Route 05 with verificationStatus unverified
        const rUnverified = JSON.parse(JSON.stringify(bs.getRouteById('05')));
        rUnverified.verificationStatus = 'unverified';
        const stateUnverified = bs.getServiceTemporalState(rUnverified, new Date());

        console.log(JSON.stringify({
            noUrlUsable: stateNoUrl.isUsable,
            noUrlStatus: stateNoUrl.status,
            unverifiedUsable: stateUnverified.isUsable,
            unverifiedStatus: stateUnverified.status
        }));
        """
        res = run_node_eval(js)
        self.assertFalse(res["noUrlUsable"])
        self.assertEqual(res["noUrlStatus"], "unverified")
        self.assertFalse(res["unverifiedUsable"])
        self.assertEqual(res["unverifiedStatus"], "unverified")

    # -------------------------------------------------------------------------
    # 5. Deterministic Identifier Resolution & Successor Tests
    # -------------------------------------------------------------------------
    def test_canonical_id_precedence(self):
        """Canonical ID exact match must always have highest priority."""
        js = """
        const { BusService } = require('./js/busService.js');
        const fs = require('fs');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;

        // Querying '05' must return Da Nang Route 05 (id: '05'), NOT TKY-NTH (routeNumber: '05 (Quảng Nam)')
        const r05 = bs.getRouteById('05');
        const res05 = bs.resolveRouteIdentifier('05');

        // Querying '02' must return Da Nang Route 02 (id: '02'), NOT TKY-TMY (routeNumber: '02 (Quảng Nam)')
        const r02 = bs.getRouteById('02');

        console.log(JSON.stringify({
            id05: r05.id,
            res05Status: res05.status,
            id02: r02.id
        }));
        """
        res = run_node_eval(js)
        self.assertEqual(res["id05"], "05")
        self.assertEqual(res["res05Status"], "exact_id")
        self.assertEqual(res["id02"], "02")

    def test_former_code_and_alias_resolution(self):
        """Former route codes (17, R17A, 16, R16, R4A) must resolve deterministically."""
        js = """
        const { BusService } = require('./js/busService.js');
        const fs = require('fs');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;

        const res17 = bs.resolveRouteIdentifier('17');
        const resR17A = bs.resolveRouteIdentifier('R17A');
        const res16 = bs.resolveRouteIdentifier('16');
        const resR16 = bs.resolveRouteIdentifier('R16');
        const resR4A = bs.resolveRouteIdentifier('R4A');

        console.log(JSON.stringify({
            r17_id: res17.route.id,
            r17_matchedVia: res17.matchedVia,
            rR17A_id: resR17A.route.id,
            r16_id: res16.route.id,
            rR16_id: resR16.route.id,
            rR4A_id: resR4A.route.id
        }));
        """
        res = run_node_eval(js)
        self.assertEqual(res["r17_id"], "09")
        self.assertIn("former_code", res["r17_matchedVia"])
        self.assertEqual(res["rR17A_id"], "09")
        self.assertEqual(res["r16_id"], "13")
        self.assertEqual(res["rR16_id"], "13")
        self.assertEqual(res["rR4A_id"], "04")

    def test_ambiguous_alias_fails_closed(self):
        """Ambiguous non-canonical token matching multiple routes must fail closed (no arbitrary tie-break)."""
        js = """
        const { BusService } = require('./js/busService.js');
        const bs = new BusService();
        bs.routes = [
            { id: 'ROUTE_A', routeNumber: 'A1', aliases: ['DUPLICATE_CODE'], status: 'active', sourceUrl: 'https://danangbus.vn', lastVerifiedAt: '2026-09-30' },
            { id: 'ROUTE_B', routeNumber: 'B1', aliases: ['DUPLICATE_CODE'], status: 'active', sourceUrl: 'https://danangbus.vn', lastVerifiedAt: '2026-09-30' }
        ];

        const res = bs.resolveRouteIdentifier('DUPLICATE_CODE');
        const route = bs.getRouteById('DUPLICATE_CODE');

        console.log(JSON.stringify({
            status: res.status,
            routeNull: res.route === null,
            candidatesCount: res.candidates.length,
            getRouteByIdNull: route === null
        }));
        """
        res = run_node_eval(js)
        self.assertEqual(res["status"], "ambiguous")
        self.assertTrue(res["routeNull"])
        self.assertEqual(res["candidatesCount"], 2)
        self.assertTrue(res["getRouteByIdNull"])

    def test_bad_successor_reference_and_cycle_detection(self):
        """Successor resolution must detect cycles and broken references fail-closed."""
        js = """
        const { BusService } = require('./js/busService.js');
        const bs = new BusService();
        bs.routes = [
            // Cycle: C1 -> C2 -> C1
            { id: 'C1', status: 'retired', supersededBy: 'C2', sourceUrl: 'https://danangbus.vn', lastVerifiedAt: '2026-09-30' },
            { id: 'C2', status: 'retired', supersededBy: 'C1', sourceUrl: 'https://danangbus.vn', lastVerifiedAt: '2026-09-30' },
            // Broken reference: B1 -> MISSING
            { id: 'B1', status: 'retired', supersededBy: 'MISSING', sourceUrl: 'https://danangbus.vn', lastVerifiedAt: '2026-09-30' },
            // Valid successor: V1 -> V2 (active)
            { id: 'V1', status: 'retired', supersededBy: 'V2', sourceUrl: 'https://danangbus.vn', lastVerifiedAt: '2026-09-30' },
            { id: 'V2', status: 'active', sourceUrl: 'https://danangbus.vn', lastVerifiedAt: '2026-09-30' }
        ];

        const resCycle = bs.resolveRouteIdentifier('C1', { followSuccessor: true });
        const resBroken = bs.resolveRouteIdentifier('B1', { followSuccessor: true });
        const resValid = bs.resolveRouteIdentifier('V1', { followSuccessor: true });
        const resValidNoFollow = bs.resolveRouteIdentifier('V1', { followSuccessor: false });

        console.log(JSON.stringify({
            cycleStatus: resCycle.status,
            brokenStatus: resBroken.status,
            validFollowed: resValid.followedSuccessor,
            validTargetId: resValid.route.id,
            noFollowTargetId: resValidNoFollow.route.id
        }));
        """
        res = run_node_eval(js)
        self.assertEqual(res["cycleStatus"], "cycle_detected")
        self.assertEqual(res["brokenStatus"], "broken_successor_reference")
        self.assertTrue(res["validFollowed"])
        self.assertEqual(res["validTargetId"], "V2")
        self.assertEqual(res["noFollowTargetId"], "V1", "Default resolution must preserve historical route")

    # -------------------------------------------------------------------------
    # 6. Reconciliation Report Contract Verification
    # -------------------------------------------------------------------------
    def test_reconciliation_report_coverage(self):
        """Machine-readable report docs/reports/task-1-official-route-reconciliation.json must exist and match dataset."""
        self.assertTrue(os.path.exists(REPORT_PATH), f"Report {REPORT_PATH} must exist")
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            report = json.load(f)

        self.assertEqual(report.get("reportVersion"), "1.0")
        self.assertEqual(report.get("dataset"), "data/danangbus_routes.json")
        summary = report.get("summary", {})

        self.assertEqual(summary["totalRoutes"], 23)
        self.assertEqual(summary["active"], 20)
        self.assertEqual(summary["suspended"], 3)
        self.assertEqual(summary["merged"], 0)
        self.assertEqual(summary["retired"], 0)
        self.assertEqual(summary["withProvenance"], 23)
        self.assertEqual(summary["provenanceCoveragePct"], 100.0)
        self.assertEqual(summary["verifiedCount"], 23)
        self.assertEqual(summary["unverifiedCount"], 0)

        # Dynamic cross-check against actual dataset
        routes = self.routes
        actual_total = len(routes)
        actual_active = sum(1 for r in routes if r.get("status") == "active")
        actual_suspended = sum(1 for r in routes if r.get("status") == "suspended")
        actual_prov = sum(1 for r in routes if r.get("sourceUrl") and r.get("lastVerifiedAt") and r.get("verificationStatus") == "verified")

        self.assertEqual(summary["totalRoutes"], actual_total)
        self.assertEqual(summary["active"], actual_active)
        self.assertEqual(summary["suspended"], actual_suspended)
        self.assertEqual(summary["withProvenance"], actual_prov)

        # Check per-route array length
        self.assertEqual(len(report.get("routes", [])), 23)


if __name__ == "__main__":
    unittest.main()
