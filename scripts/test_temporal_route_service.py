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
18. Unknown/unconfigured route reconciliation negative test (Defect 1)
19. Missing verificationStatus fail-closed regression (Defect 2)
20. Schedule calculation fail-closed on all unusable states (Defect 3)
21. Temporary override provenance enforcement across all types (Defect 4)
22. Reconciliation report contract completeness (Defect 5)
"""

import os
import sys
import json
import unittest
import subprocess

WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)
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
        res = run_node_eval(js)
        for item in res:
            self.assertFalse(item["isUsable"], f"Route {item['id']} must not be usable")
            self.assertEqual(item["status"], "suspended")
            self.assertFalse(item["usable"])
            self.assertEqual(item["depStatus"], "unknown")

    def test_retired_route(self):
        """Retired routes must fail closed."""
        js = """
        const { BusService } = require('./js/busService.js');
        const bs = new BusService();
        const r = {
            id: 'RETIRED-01',
            status: 'retired',
            statusNote: 'Tuyến dừng vĩnh viễn từ 2024',
            sourceUrl: 'https://danangbus.vn',
            lastVerifiedAt: '2026-09-30',
            verificationStatus: 'verified'
        };
        const state = bs.getServiceTemporalState(r, new Date());
        console.log(JSON.stringify({ isUsable: state.isUsable, status: state.status }));
        """
        res = run_node_eval(js)
        self.assertFalse(res["isUsable"])
        self.assertEqual(res["status"], "retired")

    def test_merged_route(self):
        """Merged routes must fail closed and indicate target route."""
        js = """
        const { BusService } = require('./js/busService.js');
        const bs = new BusService();
        const r = {
            id: 'OLD-01',
            status: 'merged',
            mergedInto: 'NEW-01',
            sourceUrl: 'https://danangbus.vn',
            lastVerifiedAt: '2026-09-30',
            verificationStatus: 'verified'
        };
        const state = bs.getServiceTemporalState(r, new Date());
        console.log(JSON.stringify({ isUsable: state.isUsable, status: state.status, reason: state.reason }));
        """
        res = run_node_eval(js)
        self.assertFalse(res["isUsable"])
        self.assertEqual(res["status"], "merged")
        self.assertIn("NEW-01", res["reason"])

    # -------------------------------------------------------------------------
    # 2. Permanent Temporal Bounds Tests
    # -------------------------------------------------------------------------
    def test_future_effective_from_fails_closed(self):
        """Query time before route effectiveFrom must fail closed."""
        js = """
        const { BusService } = require('./js/busService.js');
        const bs = new BusService();
        const r = {
            id: 'FUTURE-01',
            status: 'active',
            effectiveFrom: '2026-11-01T00:00:00+07:00',
            sourceUrl: 'https://danangbus.vn',
            lastVerifiedAt: '2026-09-30',
            verificationStatus: 'verified'
        };
        const stateEarly = bs.getServiceTemporalState(r, '2026-10-31T23:59:59+07:00');
        const stateExact = bs.getServiceTemporalState(r, '2026-11-01T00:00:00+07:00');
        console.log(JSON.stringify({
            earlyUsable: stateEarly.isUsable,
            earlyStatus: stateEarly.status,
            exactUsable: stateExact.isUsable,
            exactStatus: stateExact.status
        }));
        """
        res = run_node_eval(js)
        self.assertFalse(res["earlyUsable"])
        self.assertEqual(res["earlyStatus"], "future")
        self.assertTrue(res["exactUsable"])
        self.assertEqual(res["exactStatus"], "active")

    def test_expired_effective_to_fails_closed(self):
        """Query time after route effectiveTo must fail closed."""
        js = """
        const { BusService } = require('./js/busService.js');
        const bs = new BusService();
        const r = {
            id: 'EXPIRED-01',
            status: 'active',
            effectiveTo: '2026-09-01T23:59:59+07:00',
            sourceUrl: 'https://danangbus.vn',
            lastVerifiedAt: '2026-09-30',
            verificationStatus: 'verified'
        };
        const stateAfter = bs.getServiceTemporalState(r, '2026-09-02T00:00:01+07:00');
        const stateWithin = bs.getServiceTemporalState(r, '2026-09-01T12:00:00+07:00');
        console.log(JSON.stringify({
            afterUsable: stateAfter.isUsable,
            afterStatus: stateAfter.status,
            withinUsable: stateWithin.isUsable
        }));
        """
        res = run_node_eval(js)
        self.assertFalse(res["afterUsable"])
        self.assertEqual(res["afterStatus"], "expired")
        self.assertTrue(res["withinUsable"])

    def test_exact_temporal_boundaries_with_timezone(self):
        """Check ISO-8601 exact boundary behavior across timezone offsets."""
        js = """
        const { BusService } = require('./js/busService.js');
        const bs = new BusService();
        const r = {
            id: 'TZ-BOUNDED',
            status: 'active',
            effectiveFrom: '2026-09-30T00:00:00+07:00',
            effectiveTo: '2026-09-30T23:59:59+07:00',
            sourceUrl: 'https://danangbus.vn',
            lastVerifiedAt: '2026-09-30',
            verificationStatus: 'verified'
        };
        // In UTC: 2026-09-29T17:00:00Z === 2026-09-30T00:00:00+07:00
        const stateAtStart = bs.getServiceTemporalState(r, '2026-09-29T17:00:00Z');
        const stateJustBefore = bs.getServiceTemporalState(r, '2026-09-29T16:59:59Z');
        // In UTC: 2026-09-30T16:59:59Z === 2026-09-30T23:59:59+07:00
        const stateAtEnd = bs.getServiceTemporalState(r, '2026-09-30T16:59:59Z');
        const stateJustAfter = bs.getServiceTemporalState(r, '2026-09-30T17:00:00Z');

        console.log(JSON.stringify({
            atStart: stateAtStart.isUsable,
            justBefore: stateJustBefore.isUsable,
            atEnd: stateAtEnd.isUsable,
            justAfter: stateJustAfter.isUsable
        }));
        """
        res = run_node_eval(js)
        self.assertTrue(res["atStart"])
        self.assertFalse(res["justBefore"])
        self.assertTrue(res["atEnd"])
        self.assertFalse(res["justAfter"])

    # -------------------------------------------------------------------------
    # 3. Temporary Overrides Tests
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
            effectiveTo: '2026-10-12T23:59:59+07:00',
            sourceUrl: 'https://www.danangbus.vn/thong-bao-lu-lut.html',
            lastVerifiedAt: '2026-09-30',
            verificationStatus: 'verified'
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
            sourceUrl: 'https://www.danangbus.vn/thong-bao-cau-song-han.html',
            lastVerifiedAt: '2026-09-30',
            verificationStatus: 'verified',
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
            effectiveTo: '2026-08-05T23:59:59+07:00',
            sourceUrl: 'https://www.danangbus.vn/thong-bao-cu.html',
            lastVerifiedAt: '2026-09-30',
            verificationStatus: 'verified'
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
            effectiveTo: '2026-10-01T00:00:00+07:00', // inverted dates
            sourceUrl: 'https://www.danangbus.vn/bad.html',
            lastVerifiedAt: '2026-09-30',
            verificationStatus: 'verified'
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

        const r05 = bs.getRouteById('05');
        const res05 = bs.resolveRouteIdentifier('05');
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
            { id: 'C1', status: 'retired', supersededBy: 'C2', sourceUrl: 'https://danangbus.vn', lastVerifiedAt: '2026-09-30' },
            { id: 'C2', status: 'retired', supersededBy: 'C1', sourceUrl: 'https://danangbus.vn', lastVerifiedAt: '2026-09-30' },
            { id: 'B1', status: 'retired', supersededBy: 'MISSING', sourceUrl: 'https://danangbus.vn', lastVerifiedAt: '2026-09-30' },
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
        self.assertEqual(res["noFollowTargetId"], "V1")

    # -------------------------------------------------------------------------
    # 6. Reconciliation Report Contract Verification
    # -------------------------------------------------------------------------
    def test_reconciliation_report_coverage(self):
        """Machine-readable report docs/reports/task-1-official-route-reconciliation.json must exist and match dataset."""
        self.assertTrue(os.path.exists(REPORT_PATH), f"Report {REPORT_PATH} must exist")
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            report = json.load(f)

        self.assertIn(report.get("reportVersion"), ["1.0", "1.1"])
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
        actual_prov = sum(
            1 for r in routes
            if r.get("sourceUrl")
            and isinstance(r.get("sourceUrl"), str)
            and r.get("sourceUrl").startswith("http")
            and r.get("lastVerifiedAt")
            and r.get("verificationStatus") == "verified"
        )

        self.assertEqual(summary["totalRoutes"], actual_total)
        self.assertEqual(summary["active"], actual_active)
        self.assertEqual(summary["suspended"], actual_suspended)
        self.assertEqual(summary["withProvenance"], actual_prov)
        self.assertEqual(len(report.get("routes", [])), 23)

    # -------------------------------------------------------------------------
    # 7. Regressions for Review Defects 1 - 5
    # -------------------------------------------------------------------------
    def test_unknown_route_reconciliation_negative(self):
        """Defect 1: Unknown or unconfigured route must NOT become verified automatically."""
        from scripts.reconcile_official_routes import reconcile_route
        raw_route = {
            "id": "UNVERIFIED-X",
            "status": "active",
            "aliases": [],
            "dataQuality": {
                "tripPlanningReady": True,
                "directions": {
                    "outbound": {"eligible": True},
                    "inbound": {"eligible": True}
                }
            }
        }
        res = reconcile_route(raw_route)
        self.assertEqual(res["verificationStatus"], "unverified", "Unconfigured route must remain unverified")
        self.assertIsNone(res["sourceUrl"], "Must not fabricate sourceUrl")
        self.assertIsNone(res["sourceName"], "Must not fabricate sourceName")
        self.assertIsNone(res["lastVerifiedAt"], "Must not fabricate lastVerifiedAt")
        self.assertFalse(res["dataQuality"]["tripPlanningReady"], "Unverified route must become tripPlanningReady=False")
        self.assertFalse(res["dataQuality"]["directions"]["outbound"]["eligible"])
        self.assertFalse(res["dataQuality"]["directions"]["inbound"]["eligible"])

    def test_missing_verification_status_fail_closed(self):
        """Defect 2: Route with missing verificationStatus must fail closed as unverified/unusable."""
        js = """
        const { BusService } = require('./js/busService.js');
        const fs = require('fs');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;

        // Route 02 with verificationStatus deleted
        const r02 = JSON.parse(JSON.stringify(bs.getRouteById('02')));
        delete r02.verificationStatus;
        const stateMissing = bs.getServiceTemporalState(r02, new Date());

        // Route 02 with verificationStatus explicit unverified
        const r02Unver = JSON.parse(JSON.stringify(bs.getRouteById('02')));
        r02Unver.verificationStatus = 'unverified';
        const stateUnver = bs.getServiceTemporalState(r02Unver, new Date());

        console.log(JSON.stringify({
            missingUsable: stateMissing.isUsable,
            missingStatus: stateMissing.status,
            missingReason: stateMissing.reason,
            unverUsable: stateUnver.isUsable,
            unverStatus: stateUnver.status
        }));
        """
        res = run_node_eval(js)
        self.assertFalse(res["missingUsable"], "Route with missing verificationStatus must be unusable")
        self.assertEqual(res["missingStatus"], "unverified")
        self.assertIn("verificationStatus", res["missingReason"])
        self.assertFalse(res["unverUsable"], "Route with explicit unverified must be unusable")
        self.assertEqual(res["unverStatus"], "unverified")

    def test_calculate_next_departure_fail_closed(self):
        """Defect 3: Schedule calculation must fail closed to unknown for all unusable temporal states."""
        js = """
        const { BusService } = require('./js/busService.js');
        const fs = require('fs');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;

        const r02 = bs.getRouteById('02');

        // 1. Explicit unverified route
        const rUnver = JSON.parse(JSON.stringify(r02));
        rUnver.verificationStatus = 'unverified';
        const depUnver = bs.calculateNextDeparture(rUnver);

        // 2. Missing verificationStatus
        const rNoVer = JSON.parse(JSON.stringify(r02));
        delete rNoVer.verificationStatus;
        const depNoVer = bs.calculateNextDeparture(rNoVer);

        // 3. Invalid query time
        const depInvalidTime = bs.calculateNextDeparture(r02, { queryTime: 'not-a-valid-time' });

        // 4. Suspended route
        const r04 = bs.getRouteById('04');
        const depSuspended = bs.calculateNextDeparture(r04);

        // 5. Active unverified override
        const rUnverOvr = JSON.parse(JSON.stringify(r02));
        rUnverOvr.temporaryOverrides = [{
            id: 'ovr_unver',
            type: 'suspension',
            reason: 'Tin đồn tạm dừng',
            effectiveFrom: '2026-09-30T00:00:00+07:00',
            effectiveTo: '2026-10-01T23:59:59+07:00'
        }];
        const depUnverOvr = bs.calculateNextDeparture(rUnverOvr, { queryTime: '2026-09-30T12:00:00+07:00' });

        console.log(JSON.stringify({
            unverStatus: depUnver.status,
            unverOperating: depUnver.isOperating,
            noVerStatus: depNoVer.status,
            noVerOperating: depNoVer.isOperating,
            invalidTimeStatus: depInvalidTime.status,
            invalidTimeOperating: depInvalidTime.isOperating,
            suspendedStatus: depSuspended.status,
            suspendedOperating: depSuspended.isOperating,
            unverOvrStatus: depUnverOvr.status,
            unverOvrOperating: depUnverOvr.isOperating
        }));
        """
        res = run_node_eval(js)
        self.assertEqual(res["unverStatus"], "unknown", "Unverified route schedule must fail closed to unknown")
        self.assertFalse(res["unverOperating"])
        self.assertEqual(res["noVerStatus"], "unknown", "Missing verificationStatus schedule must fail closed to unknown")
        self.assertFalse(res["noVerOperating"])
        self.assertEqual(res["invalidTimeStatus"], "unknown", "Invalid time schedule must fail closed to unknown")
        self.assertFalse(res["invalidTimeOperating"])
        self.assertEqual(res["suspendedStatus"], "unknown", "Suspended route schedule must fail closed to unknown")
        self.assertFalse(res["suspendedOperating"])
        self.assertEqual(res["unverOvrStatus"], "unknown", "Unverified override route schedule must fail closed to unknown")
        self.assertFalse(res["unverOvrOperating"])

    def test_temporary_override_provenance_fail_closed(self):
        """Defect 4: Active temporary overrides without verified official provenance must fail closed across all types."""
        js = """
        const { BusService } = require('./js/busService.js');
        const fs = require('fs');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;

        const types = ['suspension', 'detour', 'schedule_adjustment', 'fare_adjustment'];
        const results = {};

        for (const t of types) {
            const r = JSON.parse(JSON.stringify(bs.getRouteById('05')));
            r.temporaryOverrides = [{
                id: 'ovr_' + t,
                type: t,
                reason: 'Kiểm thử override ' + t,
                effectiveFrom: '2026-10-01T00:00:00+07:00',
                effectiveTo: '2026-10-05T23:59:59+07:00'
                // Missing required provenance: sourceUrl, lastVerifiedAt, verificationStatus
            }];

            const stateActive = bs.getServiceTemporalState(r, '2026-10-02T10:00:00+07:00');
            const stateFuture = bs.getServiceTemporalState(r, '2026-09-30T10:00:00+07:00');
            const statePast = bs.getServiceTemporalState(r, '2026-10-06T10:00:00+07:00');

            results[t] = {
                activeUsable: stateActive.isUsable,
                activeStatus: stateActive.status,
                futureUsable: stateFuture.isUsable,
                pastUsable: statePast.isUsable
            };
        }
        console.log(JSON.stringify(results));
        """
        res = run_node_eval(js)
        for t in ['suspension', 'detour', 'schedule_adjustment', 'fare_adjustment']:
            self.assertFalse(res[t]["activeUsable"], f"Active override of type {t} without provenance must fail closed")
            self.assertEqual(res[t]["activeStatus"], "unverified_override")
            self.assertTrue(res[t]["futureUsable"], f"Future override of type {t} does not affect current time")
            self.assertTrue(res[t]["pastUsable"], f"Expired override of type {t} is ignored cleanly")

    def test_reconciliation_report_contract_completeness(self):
        """Defect 5: Reconciliation report must expose explicit evidence, gaps, validations, and override sections."""
        self.assertTrue(os.path.exists(REPORT_PATH), f"Report {REPORT_PATH} must exist")
        with open(REPORT_PATH, "r", encoding="utf-8") as f:
            report = json.load(f)

        required_sections = [
            "reportVersion", "generatedAt", "task", "dataset", "summary",
            "evidence", "evidenceGaps", "unresolvedEvidence", "aliasConflicts",
            "lifecycleReferenceIssues", "temporalValidation", "overrideValidation", "routes"
        ]
        for sec in required_sections:
            self.assertIn(sec, report, f"Section '{sec}' missing in reconciliation report")

        evidence = report["evidence"]
        self.assertEqual(len(evidence), 23)
        for ev in evidence:
            self.assertTrue(ev["hasExplicitEvidence"])
            self.assertEqual(ev["verificationStatus"], "verified")
            self.assertTrue(ev["sourceUrl"].startswith("http"))
            self.assertIsNotNone(ev["lastVerifiedAt"])
            self.assertIsNotNone(ev["evidenceNote"])

        self.assertEqual(len(report["evidenceGaps"]), 0)
        self.assertEqual(report["summary"]["evidenceGapsCount"], 0)
        self.assertEqual(len(report["aliasConflicts"]), 0)
        self.assertEqual(report["summary"]["aliasConflictsCount"], 0)
        self.assertEqual(len(report["lifecycleReferenceIssues"]), 0)
        self.assertEqual(report["summary"]["lifecycleReferenceIssuesCount"], 0)

        ovr_val = report["overrideValidation"]
        self.assertIn("totalOverrides", ovr_val)
        self.assertIn("validOverrides", ovr_val)
        self.assertIn("invalidOverrides", ovr_val)
        self.assertIn("records", ovr_val)


if __name__ == "__main__":
    unittest.main()
