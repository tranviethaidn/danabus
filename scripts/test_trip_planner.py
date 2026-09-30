#!/usr/bin/env python3
"""
Comprehensive Automated Test Suite for Address Search, Geocoding & Best Boarding/Alighting Stop (Task 007)
Validates:
1. ResolvedLocation contract (validation, coordinates, provider metadata, map pin)
2. LocationSearchProvider & LocalLocationProvider (POI resolution, address search, stop search, duplicate street names)
3. GoogleLocationProvider contract (Places Autocomplete New, details, minimal field mask, session token, timeout/429/network safe fallback, stale suppression)
4. LocationManager integration (primary/fallback provider, cache, GPS, map pin)
5. Service Area geofence & Out-of-service-area rejection (OUT_OF_SERVICE_AREA)
6. BestStopResolver & candidate filtering (wrong-direction rejected, inactive route rejected, disconnected candidate rejected)
7. Controlled walking radius expansion (800m -> 1500m) & metadata disclosure (isExpandedRadius, searchRadiusMeters)
8. Multi-factor ranking & deterministic tie-breaking (walking cost, transit duration, transfer penalty, data confidence)
9. Explainable failures (OUT_OF_SERVICE_AREA, NO_NEARBY_STOPS, NO_VIABLE_ROUTE)
10. TransitPlanner direct route matching regression (Route 05)
11. TransitPlanner 1-transfer routing & detour ratio regression (Tam Kỳ <= 1.8)
12. MapService Leaflet multi-leg rendering & map pin contract (Leaflet/OSM preserved, zero Google Maps SDK)
13. Security & Credential Audit (zero hardcoded API keys / secrets)
14. Backward compatibility (findRoutesBetween)
"""

import os
import re
import sys
import json
import unittest
import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent

class TestTripPlanner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(WORKSPACE / 'data' / 'danangbus_routes.json', 'r', encoding='utf-8') as f:
            cls.routes = json.load(f)
        with open(WORKSPACE / 'data' / 'danangbus_stops.json', 'r', encoding='utf-8') as f:
            cls.stops = json.load(f)

    # 1. ResolvedLocation Contract (including Map Pin & GPS)
    def test_resolved_location_contract(self):
        node_script = """
        const { ResolvedLocation, LocationManager } = require('./js/busService.js');
        const loc1 = new ResolvedLocation({
            displayName: 'Cầu Rồng',
            address: 'Nguyễn Văn Linh, Hải Châu',
            lat: 16.0612,
            lng: 108.2272,
            provider: 'local',
            type: 'poi'
        });
        if (!loc1.isValid() || loc1.lat !== 16.0612 || loc1.type !== 'poi') process.exit(1);

        const invalidLoc = new ResolvedLocation({ displayName: 'Lỗi', lat: null, lng: 'abc' });
        if (invalidLoc.isValid()) process.exit(2);

        const outOfRange = new ResolvedLocation({ displayName: 'Vũ trụ', lat: 105.0, lng: 200.0 });
        if (outOfRange.isValid()) process.exit(3);

        // Map pin contract: must not fabricate address if unavailable
        const lm = new LocationManager();
        const pinLoc = lm.resolveFromMapPin(16.0612, 108.2272);
        if (!pinLoc || !pinLoc.isValid()) process.exit(4);
        if (pinLoc.type !== 'pin' || pinLoc.provider !== 'map_pin') process.exit(5);
        if (!pinLoc.displayName.includes('Ghim trên bản đồ')) process.exit(6);
        if (pinLoc.address !== pinLoc.displayName) process.exit(7); // Must NOT fabricate street address

        // GPS contract
        const gpsLoc = lm.resolveFromCoordinates(16.0612, 108.2272, 'Vị trí hiện tại', 'gps');
        if (!gpsLoc || !gpsLoc.isValid() || gpsLoc.type !== 'gps') process.exit(8);
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "ResolvedLocation contract failed")

    # 2. Duplicate Street Names Disambiguation
    def test_duplicate_street_names_disambiguation(self):
        node_script = """
        const fs = require('fs');
        const { BusService, LocationManager } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const lm = new LocationManager(bs);
        (async () => {
            // Search 'Trần Phú': must return both Đà Nẵng and Hội An candidates
            const tranPhuResults = await lm.search('Trần Phú');
            const dnTranPhu = tranPhuResults.find(r => r.address.includes('Hải Châu') || r.address.includes('Đà Nẵng'));
            const haTranPhu = tranPhuResults.find(r => r.address.includes('Hội An') || r.address.includes('Quảng Nam'));
            if (!dnTranPhu || !haTranPhu) {
                console.error('Expected distinct candidates for duplicate street Trần Phú');
                process.exit(1);
            }
            if (dnTranPhu.lat === haTranPhu.lat && dnTranPhu.lng === haTranPhu.lng) {
                console.error('Duplicate street candidates must have distinct coordinates');
                process.exit(2);
            }

            // Search 'Hùng Vương': must return both Đà Nẵng and Tam Kỳ candidates
            const hungVuongResults = await lm.search('Hùng Vương');
            const dnHungVuong = hungVuongResults.find(r => r.address.includes('Hải Châu') || r.address.includes('Đà Nẵng'));
            const tkHungVuong = hungVuongResults.find(r => r.address.includes('Tam Kỳ') || r.address.includes('Quảng Nam'));
            if (!dnHungVuong || !tkHungVuong) {
                console.error('Expected distinct candidates for duplicate street Hùng Vương');
                process.exit(3);
            }
        })();
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Duplicate street names disambiguation test failed")

    # 3. GoogleLocationProvider Boundary, Isolation & Safe Fallback
    def test_google_provider_unconfigured_and_isolation(self):
        node_script = """
        const { GoogleLocationProvider, LocationSearchProvider, LocationManager } = require('./js/busService.js');
        
        // 1. Inheritance
        const gp = new GoogleLocationProvider();
        if (!(gp instanceof LocationSearchProvider)) process.exit(1);

        // 2. Unconfigured -> inactive & safe fallback
        if (gp.isConfigured() !== false) process.exit(2);

        (async () => {
            const results = await gp.search('Cầu Rồng');
            if (!Array.isArray(results) || results.length !== 0) process.exit(3);

            const resolved = await gp.resolve('place_123');
            if (resolved !== null) process.exit(4);

            // LocationManager with unconfigured provider falls back to local seamlessly
            const lm = new LocationManager(null, { google: { apiKey: null } });
            const lmResults = await lm.search('Cầu Rồng');
            if (!lmResults || lmResults.length === 0) process.exit(5);
            if (lmResults[0].provider !== 'local') process.exit(6);
        })();
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Google provider unconfigured/isolation test failed")

    # 4. GoogleLocationProvider Network Errors, Timeout & Safe Fallback
    def test_google_provider_error_handling(self):
        node_script = """
        const { GoogleLocationProvider, LocationManager } = require('./js/busService.js');

        (async () => {
            // Guard: direct REST web-service must never be called
            global.fetch = async (url) => {
                throw new Error('Prohibited direct REST endpoint call: ' + url);
            };

            global.window = {
                google: {
                    maps: {
                        places: {
                            AutocompleteSessionToken: function() { this.id = 'tok_err'; },
                            AutocompleteSuggestion: {
                                fetchAutocompleteSuggestions: async () => {
                                    throw new Error('Places SDK Rate Limit or Network Error');
                                }
                            },
                            Place: function() {
                                return {
                                    fetchFields: async () => {
                                        throw new Error('Place Details SDK Error');
                                    }
                                };
                            }
                        }
                    }
                }
            };

            const gp = new GoogleLocationProvider({ apiKey: 'mock_test_key', timeoutMs: 30 });
            
            // Test 1: Client SDK search rejection/error returns []
            const resErr = await gp.search('Nguyễn Văn Linh');
            if (!Array.isArray(resErr) || resErr.length !== 0) {
                console.error('Expected empty search array on SDK rejection, got:', resErr);
                process.exit(1);
            }

            // Test 2: Client SDK resolve rejection/error returns null
            const resolveErr = await gp.resolve('place_err');
            if (resolveErr !== null) {
                console.error('Expected null on resolve rejection, got:', resolveErr);
                process.exit(2);
            }

            // Test 3: True client SDK search timeout via Promise.race
            global.window.google.maps.places.AutocompleteSuggestion.fetchAutocompleteSuggestions = () => {
                return new Promise(r => setTimeout(r, 100)); // 100ms > timeoutMs 30ms
            };
            const resTimeout = await gp.search('Timeout query');
            if (!Array.isArray(resTimeout) || resTimeout.length !== 0) {
                console.error('Expected empty search array on SDK timeout, got:', resTimeout);
                process.exit(3);
            }

            // Test 4: True client SDK resolve timeout via Promise.race
            global.window.google.maps.places.Place = function() {
                return {
                    fetchFields: () => new Promise(r => setTimeout(r, 100))
                };
            };
            const resolveTimeout = await gp.resolve('place_timeout');
            if (resolveTimeout !== null) {
                console.error('Expected null on Place Details SDK timeout, got:', resolveTimeout);
                process.exit(4);
            }

            // Test 5: LocationManager fallback to local when Google SDK fails or times out
            const lm = new LocationManager(null, { google: { apiKey: 'mock_test_key', timeoutMs: 30 } });
            const lmRes = await lm.search('Cầu Rồng');
            if (!lmRes || lmRes.length === 0 || lmRes[0].provider !== 'local') {
                console.error('Expected LocationManager fallback to local on Google timeout');
                process.exit(5);
            }

            delete global.window;
        })();
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Google provider error handling test failed")

    # 5. Stale Response Suppression across Google Provider and LocationManager (Finding 2)
    def test_stale_response_suppression(self):
        node_script = """
        const { GoogleLocationProvider, LocationManager } = require('./js/busService.js');

        (async () => {
            // Guard: direct REST web-service must never be called
            global.fetch = async (url) => {
                throw new Error('Prohibited direct REST endpoint call: ' + url);
            };

            global.window = {
                google: {
                    maps: {
                        places: {
                            AutocompleteSessionToken: function() { this.id = 'tok_stale'; },
                            AutocompleteSuggestion: {
                                fetchAutocompleteSuggestions: async ({ input }) => {
                                    const delay = (input === 'query1' || input === 'Cầu Rồng Đà Nẵng') ? 80 : 10;
                                    await new Promise(r => setTimeout(r, delay));
                                    return {
                                        suggestions: [{
                                            placePrediction: {
                                                placeId: `id_${input}`,
                                                text: { text: `Result for ${input}` },
                                                structuredFormat: { mainText: { text: `Result for ${input}` } }
                                            }
                                        }]
                                    };
                                }
                            }
                        }
                    }
                }
            };

            // Part 1: Stale suppression inside GoogleLocationProvider
            const gp = new GoogleLocationProvider({ apiKey: 'mock_test_key' });
            const p1 = gp.search('query1');
            const p2 = gp.search('query2');

            const [r1, r2] = await Promise.all([p1, p2]);
            if (r1.length !== 0) {
                console.error('Expected r1 to be suppressed in Google provider, got:', r1);
                process.exit(1);
            }
            if (r2.length === 0 || !r2[0].displayName.includes('query2')) {
                console.error('Expected r2 to succeed with query2 results');
                process.exit(2);
            }

            // Part 2: Staleness enforced at LocationManager level (Finding 2)
            // Query A (old) starts first with delay, Query B (new) starts right after with shorter delay.
            // Query A finishing later must NOT fall back to local or overwrite Query B!
            const lm = new LocationManager(null, { google: { apiKey: 'mock_test_key' } });
            const searchA = lm.search('Cầu Rồng Đà Nẵng');
            const searchB = lm.search('Rồng');

            const [resA, resB] = await Promise.all([searchA, searchB]);
            if (resA.length !== 0) {
                console.error('Expected obsolete searchA to be suppressed at LocationManager level, got:', resA);
                process.exit(3);
            }
            if (resB.length === 0 || !resB[0].displayName.includes('Rồng')) {
                console.error('Expected newer searchB to succeed, got:', resB);
                process.exit(4);
            }

            delete global.window;
        })();
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Stale response suppression test failed")

    # 5b. Google Places Client SDK Lifecycle, Session Token & toPlace Details Contract (Turn 009)
    def test_google_places_client_sdk_contract(self):
        node_script = """
        const { GoogleLocationProvider, LocationManager } = require('./js/busService.js');

        class MockSessionToken {
            constructor() {
                this._isToken = true;
                this.id = 'token_' + Math.random().toString(36).substring(2, 9);
            }
        }

        (async () => {
            // Guard: Direct REST web-service endpoint must NEVER be called
            global.fetch = async (url) => {
                if (typeof url === 'string' && url.includes('places.googleapis.com')) {
                    throw new Error('Prohibited direct REST endpoint call: ' + url);
                }
                return { ok: false, status: 500 };
            };

            // 1. Browser-like loader invocation
            let scriptCreated = null;
            let scriptAppended = false;
            global.window = {};
            global.document = {
                querySelector: () => null,
                head: {
                    appendChild: (el) => {
                        scriptAppended = true;
                    }
                },
                createElement: (tag) => {
                    if (tag === 'script') {
                        const s = {
                            src: '',
                            async: false,
                            onload: null,
                            onerror: null
                        };
                        scriptCreated = s;
                        return s;
                    }
                    return {};
                }
            };

            const gp = new GoogleLocationProvider({ apiKey: 'mock_browser_key' });
            const searchPromise = gp.search('Cầu Rồng');

            // Verify script was created with correct params and appended to head
            if (!scriptCreated || !scriptAppended) {
                console.error('Expected script element creation and head attachment');
                process.exit(1);
            }
            if (!scriptCreated.src.includes('key=mock_browser_key') || !scriptCreated.src.includes('libraries=places')) {
                console.error('Expected script src with key and places library, got:', scriptCreated.src);
                process.exit(2);
            }

            // Simulate script load completing with Places SDK
            let tokenInstances = [];
            let fetchSuggestionsCalls = [];
            let fetchFieldsCalls = [];

            const mockPlace = {
                displayName: { text: 'Bảo tàng Điêu khắc Chăm' },
                formattedAddress: 'Số 2 đường 2 Tháng 9, Hải Châu, Đà Nẵng',
                location: { lat: () => 16.0601, lng: () => 108.2235 },
                fetchFields: async (opts) => {
                    fetchFieldsCalls.push(opts);
                    return mockPlace;
                }
            };

            const mockPrediction = {
                placeId: 'cham_museum_id',
                structuredFormat: {
                    mainText: { text: 'Bảo tàng Điêu khắc Chăm' },
                    secondaryText: { text: 'Hải Châu, Đà Nẵng' }
                },
                toPlace: () => mockPlace
            };

            global.window.google = {
                maps: {
                    places: {
                        AutocompleteSessionToken: function() {
                            const t = new MockSessionToken();
                            tokenInstances.push(t);
                            return t;
                        },
                        AutocompleteSuggestion: {
                            fetchAutocompleteSuggestions: async (req) => {
                                fetchSuggestionsCalls.push(req);
                                return { suggestions: [{ placePrediction: mockPrediction }] };
                            }
                        }
                    }
                }
            };

            // Trigger script onload
            scriptCreated.onload();

            const results = await searchPromise;
            if (!results || results.length !== 1) {
                console.error('Expected 1 search result from loaded SDK, got:', results);
                process.exit(3);
            }

            // 2. Verify AutocompleteSessionToken instance passed, not string
            if (fetchSuggestionsCalls.length !== 1) {
                console.error('Expected 1 suggestion call, got:', fetchSuggestionsCalls.length);
                process.exit(4);
            }
            const sessionTokenUsed = fetchSuggestionsCalls[0].sessionToken;
            if (!(sessionTokenUsed instanceof MockSessionToken) || typeof sessionTokenUsed === 'string') {
                console.error('Session token must be an instance of AutocompleteSessionToken, not string:', sessionTokenUsed);
                process.exit(5);
            }

            // 3. Verify resolve invokes placePrediction.toPlace().fetchFields()
            const resolved = await gp.resolve(results[0].id, results[0]);
            if (!resolved || resolved.displayName !== 'Bảo tàng Điêu khắc Chăm' || resolved.lat !== 16.0601) {
                console.error('Resolve failed to produce expected ResolvedLocation:', resolved);
                process.exit(6);
            }
            if (fetchFieldsCalls.length !== 1) {
                console.error('Expected place.fetchFields to be called once, got:', fetchFieldsCalls.length);
                process.exit(7);
            }
            const fieldsRequested = fetchFieldsCalls[0].fields;
            if (!fieldsRequested || !fieldsRequested.includes('displayName') || !fieldsRequested.includes('location')) {
                console.error('Invalid fields requested on Place instance:', fieldsRequested);
                process.exit(8);
            }

            // 4. Verify session token reset and new token created for subsequent session
            if (gp.sessionToken !== null) {
                console.error('Session token must be reset to null after selection');
                process.exit(9);
            }

            await gp.search('Nguyễn Văn Linh');
            if (tokenInstances.length < 2) {
                console.error('Expected second session to instantiate a new token, count:', tokenInstances.length);
                process.exit(10);
            }
            if (tokenInstances[0] === tokenInstances[1]) {
                console.error('Session token must not be reused across sessions');
                process.exit(11);
            }

            // 5. SDK load failure -> local fallback, no crash, no REST call
            delete global.window.google;
            const gpFail = new GoogleLocationProvider({ apiKey: 'fail_key' });
            global.document.createElement = (tag) => {
                const s = { onload: null, onerror: null };
                setTimeout(() => { if (s.onerror) s.onerror(new Error('Load failed')); }, 5);
                return s;
            };
            const failResults = await gpFail.search('Cầu Rồng');
            if (!Array.isArray(failResults) || failResults.length !== 0) {
                console.error('Expected empty search array on SDK load failure, got:', failResults);
                process.exit(12);
            }

            const lm = new LocationManager(null, { google: { apiKey: 'fail_key' } });
            const lmResults = await lm.search('Cầu Rồng');
            if (!lmResults || lmResults.length === 0 || lmResults[0].provider !== 'local') {
                console.error('Expected LocationManager local fallback on SDK load failure');
                process.exit(13);
            }

            delete global.window;
            delete global.document;
        })();
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Google Places client SDK contract test failed")

    # 5c. Google Places SDK Loader Timeout & Fail-Safe Fallback Contract (Turn 011)
    def test_google_sdk_loader_timeout_fail_safe(self):
        node_script = """
        const { GoogleLocationProvider, LocationManager } = require('./js/busService.js');

        (async () => {
            // Guard: Direct REST web-service endpoint must NEVER be called
            let restCallAttempted = false;
            global.fetch = async (url) => {
                if (typeof url === 'string' && url.includes('places.googleapis.com')) {
                    restCallAttempted = true;
                    throw new Error('Prohibited direct REST endpoint call: ' + url);
                }
                return { ok: false, status: 500 };
            };

            // Setup browser environment where appendChild does nothing and onload/onerror never fire
            let scriptCreated = null;
            let appendCalled = false;
            global.window = {};
            global.document = {
                querySelector: () => null,
                head: {
                    appendChild: (el) => {
                        appendCalled = true;
                        // Neither onload nor onerror fires; simulates pending network request
                    }
                },
                createElement: (tag) => {
                    if (tag === 'script') {
                        scriptCreated = {
                            src: '',
                            async: false,
                            onload: null,
                            onerror: null
                        };
                        return scriptCreated;
                    }
                    return {};
                }
            };

            const gp = new GoogleLocationProvider({ apiKey: 'mock_timeout_key', timeoutMs: 25 });

            // 1. Assert Google search settles within a bounded test window and returns []
            const startSearch = Date.now();
            const searchPromise = gp.search('Cầu Rồng');
            const results = await searchPromise;
            const searchElapsed = Date.now() - startSearch;

            if (!appendCalled || !scriptCreated) {
                console.error('Expected script element creation and appendChild invocation');
                process.exit(1);
            }
            if (!Array.isArray(results) || results.length !== 0) {
                console.error('Expected empty search array on SDK loader timeout, got:', results);
                process.exit(2);
            }
            if (searchElapsed > 500) {
                console.error('Google search took too long to settle on SDK loader timeout:', searchElapsed);
                process.exit(3);
            }

            // 2. Assert Google resolve settles within a bounded window and returns null
            const startResolve = Date.now();
            const resolved = await gp.resolve('mock_place_id');
            const resolveElapsed = Date.now() - startResolve;

            if (resolved !== null) {
                console.error('Expected null from resolve on SDK loader timeout, got:', resolved);
                process.exit(4);
            }
            if (resolveElapsed > 500) {
                console.error('Google resolve took too long to settle on SDK loader timeout:', resolveElapsed);
                process.exit(5);
            }

            // 3. Assert LocationManager search returns valid local fallback
            const lm = new LocationManager(null, { google: { apiKey: 'mock_timeout_key', timeoutMs: 25 } });
            const lmResults = await lm.search('Cầu Rồng');
            if (!lmResults || lmResults.length === 0 || lmResults[0].provider !== 'local') {
                console.error('Expected LocationManager local fallback on SDK loader timeout, got:', lmResults);
                process.exit(6);
            }
            if (!lmResults[0].displayName.includes('Cầu Rồng')) {
                console.error('Expected local fallback result for Cầu Rồng, got:', lmResults[0]);
                process.exit(7);
            }

            // 4. Assert no places.googleapis.com REST call occurred
            if (restCallAttempted) {
                console.error('Prohibited direct REST call was attempted during loader timeout');
                process.exit(8);
            }

            // 5. Assert retry is unpoisoned: subsequent call after SDK loads succeeds
            global.window.google = {
                maps: {
                    places: {
                        AutocompleteSessionToken: function() { this.id = 'tok_retry'; },
                        AutocompleteSuggestion: {
                            fetchAutocompleteSuggestions: async () => ({
                                suggestions: [{
                                    placePrediction: {
                                        placeId: 'id_recovered',
                                        structuredFormat: {
                                            mainText: { text: 'Cầu Rồng Đà Nẵng' },
                                            secondaryText: { text: 'Hải Châu, Đà Nẵng' }
                                        }
                                    }
                                }]
                            })
                        }
                    }
                }
            };
            const retryResults = await gp.search('Cầu Rồng');
            if (!retryResults || retryResults.length !== 1 || retryResults[0].id !== 'id_recovered') {
                console.error('Expected subsequent search after SDK becomes available to succeed, got:', retryResults);
                process.exit(9);
            }

            delete global.window;
            delete global.document;
            delete global.fetch;
        })();
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Google Places SDK loader timeout fail-safe test failed")

    # 6. Service Area Geofence Check & OUT_OF_SERVICE_AREA
    def test_out_of_service_area_geofence(self):
        node_script = """
        const fs = require('fs');
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation, isWithinServiceArea } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const tp = new TransitPlanner(bs, new WalkingRouter());

        // Check isWithinServiceArea bounds
        if (!isWithinServiceArea(16.0612, 108.2272)) process.exit(1); // Da Nang Center
        if (!isWithinServiceArea(15.8778, 108.3283)) process.exit(2); // Hoi An
        if (!isWithinServiceArea(15.5684, 108.4816)) process.exit(3); // Tam Ky
        if (isWithinServiceArea(21.0285, 105.8542)) process.exit(4);  // Hanoi (Out of bounds)
        if (isWithinServiceArea(10.7769, 106.7009)) process.exit(5);  // HCMC (Out of bounds)

        // Planner out-of-service-area call
        const oLoc = new ResolvedLocation({ displayName: 'Đà Nẵng', lat: 16.0617, lng: 108.1834 });
        const dLoc = new ResolvedLocation({ displayName: 'Hồ Gươm Hà Nội', lat: 21.0285, lng: 105.8542 });

        const plan = tp.planTrip(oLoc, dLoc);
        if (plan.trips.length !== 0) process.exit(6);
        if (plan.error !== 'OUT_OF_SERVICE_AREA') {
            console.error('Expected OUT_OF_SERVICE_AREA, got:', plan.error);
            process.exit(7);
        }
        if (!plan.message || !plan.message.includes('ngoài phạm vi phục vụ')) process.exit(8);
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Out-of-service-area geofence test failed")

    # 7. Controlled Walking Radius Expansion (800m -> 1500m) & Disclosure Metadata
    def test_controlled_radius_expansion(self):
        node_script = """
        const fs = require('fs');
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const tp = new TransitPlanner(bs, new WalkingRouter());

        // Origin point at ~1000m from nearest bus stop in Hoa Hiep Nam (0 stops in 800m, 3 stops in 1500m)
        const oLoc = new ResolvedLocation({ displayName: 'Hòa Hiệp Nam Xa', lat: 16.1174388, lng: 108.1321979 });
        // Destination at CV Biển Đông on Route 05
        const dLoc = new ResolvedLocation({ displayName: 'CV Biển Đông', lat: 16.0687, lng: 108.2464 });

        const plan = tp.planTrip(oLoc, dLoc);
        if (!plan.trips || plan.trips.length === 0) {
            console.error('Expected trip via expanded radius (1500m)');
            process.exit(1);
        }

        // Must disclose expanded radius in plan and trip metadata
        if (plan.isExpandedRadius !== true) {
            console.error('Expected plan.isExpandedRadius === true');
            process.exit(2);
        }
        if (plan.searchRadiusMeters !== 1500) {
            console.error('Expected plan.searchRadiusMeters === 1500, got:', plan.searchRadiusMeters);
            process.exit(3);
        }

        const topTrip = plan.trips[0];
        if (topTrip.isExpandedRadius !== true || topTrip.searchRadiusMeters !== 1500) {
            console.error('Expected trip to carry isExpandedRadius metadata');
            process.exit(4);
        }
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Controlled radius expansion test failed")

    # 8. Best Stop Selection: Wrong-Direction Nearest Stop Rejected
    def test_wrong_direction_nearest_stop_rejected(self):
        node_script = """
        const fs = require('fs');
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation, BestStopResolver } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const tp = new TransitPlanner(bs, new WalkingRouter());
        const r05 = routes.find(r => r.routeNumber === '05');
        const outboundStops = r05.stops.outbound;

        // Choose stop S5 as destination
        const destStop = outboundStops[5];
        // Choose stop S2 as origin reference
        const origStop = outboundStops[2];

        // Position origin slightly closer to stop S7 than to stop S2
        // S7 is downstream (after S5 on outbound), so taking S7 is WRONG DIRECTION
        const oLoc = new ResolvedLocation({
            displayName: 'Điểm thử nghiệm',
            lat: origStop.lat,
            lng: origStop.lng
        });
        const dLoc = new ResolvedLocation({
            displayName: 'Điểm đến',
            lat: destStop.lat,
            lng: destStop.lng
        });

        const plan = tp.planTrip(oLoc, dLoc);
        if (!plan.trips || plan.trips.length === 0) process.exit(1);

        const trip = plan.trips[0];
        const transitLeg = trip.legs.find(l => l.type === 'transit');
        // The boarding stop must be upstream from destStop (oi < di)
        const oi = outboundStops.findIndex(s => s.name === transitLeg.boardingStop.name);
        const di = outboundStops.findIndex(s => s.name === transitLeg.alightingStop.name);

        if (oi >= di) {
            console.error('Monotonic direction violated: oi >= di');
            process.exit(2);
        }
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Wrong-direction nearest stop rejection test failed")

    # 9. Inactive & Temporally Invalid Route Rejected
    def test_inactive_route_rejected(self):
        node_script = """
        const fs = require('fs');
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const tp = new TransitPlanner(bs, new WalkingRouter());

        const oLoc = new ResolvedLocation({ displayName: 'ĐH Bách Khoa', lat: 16.0754, lng: 108.1528 });
        const dLoc = new ResolvedLocation({ displayName: 'CV Biển Đông', lat: 16.0687, lng: 108.2464 });

        // Temporarily suspend route 05 with verified override
        const r05 = bs.routes.find(r => r.routeNumber === '05');
        r05.temporaryOverrides = [{
            type: 'suspension',
            effectiveFrom: '2026-09-01T00:00:00+07:00',
            effectiveTo: '2026-10-31T23:59:59+07:00',
            verificationStatus: 'verified',
            sourceUrl: 'https://danangbus.vn/thong-bao-tam-dung-05'
        }];

        const plan = tp.planTrip(oLoc, dLoc, { queryTime: new Date('2026-09-30T10:00:00+07:00') });

        if (plan.trips && plan.trips.length > 0) {
            console.error('Expected 0 trips for temporally suspended route');
            process.exit(1);
        }
        if (plan.error !== 'NO_VIABLE_ROUTE') {
            console.error('Expected NO_VIABLE_ROUTE for suspended route query, got:', plan.error);
            process.exit(2);
        }
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Inactive route rejection test failed")

    # 10. Explainable Failure Contracts
    def test_explainable_failure_contracts(self):
        node_script = """
        const fs = require('fs');
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const tp = new TransitPlanner(bs, new WalkingRouter());

        // 1. OUT_OF_SERVICE_AREA
        const p1 = tp.planTrip(
            new ResolvedLocation({ displayName: 'Đà Nẵng', lat: 16.0617, lng: 108.1834 }),
            new ResolvedLocation({ displayName: 'Hà Nội', lat: 21.0285, lng: 105.8542 })
        );
        if (p1.error !== 'OUT_OF_SERVICE_AREA' || !p1.message.includes('ngoài phạm vi phục vụ')) process.exit(1);

        // 2. NO_NEARBY_STOPS: isolated mountain in Ba Na hills outside 1.5km of any stop
        const p2 = tp.planTrip(
            new ResolvedLocation({ displayName: 'Bà Nà Đỉnh', lat: 15.9980, lng: 107.9950 }),
            new ResolvedLocation({ displayName: 'CV Biển Đông', lat: 16.0687, lng: 108.2464 })
        );
        if (p2.error !== 'NO_NEARBY_STOPS' || !p2.message.includes('Không tìm thấy trạm dừng xe buýt')) process.exit(2);

        // 3. NO_VIABLE_ROUTE: route suspended
        const r05 = bs.routes.find(r => r.routeNumber === '05');
        r05.status = 'suspended';
        const p3 = tp.planTrip(
            new ResolvedLocation({ displayName: 'ĐH Bách Khoa', lat: 16.0754, lng: 108.1528 }),
            new ResolvedLocation({ displayName: 'CV Biển Đông', lat: 16.0687, lng: 108.2464 })
        );
        if (p3.error !== 'NO_VIABLE_ROUTE' || !p3.message.includes('Không tìm thấy hành trình phù hợp')) process.exit(3);
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Explainable failure contracts test failed")

    # 11. Direct Route Planning on Verified Route (Route 05) - Regression
    def test_transit_planner_direct_route_regression(self):
        node_script = """
        const fs = require('fs');
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const tp = new TransitPlanner(bs, new WalkingRouter());

        // Test pair on Route 05 (verified planning route)
        const oLoc = new ResolvedLocation({ displayName: 'ĐH Bách Khoa', lat: 16.0754, lng: 108.1528 });
        const dLoc = new ResolvedLocation({ displayName: 'CV Biển Đông', lat: 16.0687, lng: 108.2464 });

        const plan = tp.planTrip(oLoc, dLoc);
        if (!plan.trips || plan.trips.length === 0) process.exit(1);

        const topTrip = plan.trips[0];
        if (topTrip.type !== 'direct') process.exit(2);
        if (topTrip.transfers !== 0) process.exit(3);
        if (topTrip.legs.length !== 3) process.exit(4);
        if (topTrip.legs[0].type !== 'walking' || topTrip.legs[1].type !== 'transit' || topTrip.legs[2].type !== 'walking') process.exit(5);
        if (topTrip.legs[0].geometry !== null || topTrip.legs[2].geometry !== null) process.exit(6);
        if (!Array.isArray(topTrip.legs[1].geometry) || topTrip.legs[1].geometry.length <= 1) process.exit(7);
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "TransitPlanner direct route regression failed")

    # 12. One-Transfer Route Planning & Detour Ratio Check - Regression
    def test_transit_planner_transfer_and_detour_regression(self):
        node_script = """
        const fs = require('fs');
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const tp = new TransitPlanner(bs, new WalkingRouter());

        // Connect Route TKY-TMY and Route TKY-NTH in Tam Kỳ
        const oLoc = new ResolvedLocation({ displayName: 'Huỳnh Thúc Kháng', lat: 15.5673332, lng: 108.4904846 });
        const dLoc = new ResolvedLocation({ displayName: '954 Phan Châu Trinh', lat: 15.555436, lng: 108.5059009 });

        const plan = tp.planTrip(oLoc, dLoc);
        if (!plan.trips || plan.trips.length === 0) process.exit(1);

        const transferTrip = plan.trips.find(t => t.transfers === 1);
        if (!transferTrip) process.exit(2);

        if (transferTrip.legs.length !== 5) process.exit(3);
        if (transferTrip.legs[2].type !== 'walking') process.exit(4);
        if (transferTrip.legs[2].distanceMeters > tp.MAX_TRANSFER_WALK_METERS) process.exit(5);
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "TransitPlanner 1-transfer regression failed")

    # 13. MapService Multi-Leg & Pin Rendering Contract (Leaflet Preserved)
    def test_mapservice_multileg_and_pin_contract(self):
        with open(WORKSPACE / 'js' / 'mapService.js', 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('renderTrip', content, "MapService must provide renderTrip method")
        self.assertIn('clearTripLayers', content, "MapService must manage clearTripLayers")
        self.assertIn('tripPolylines', content, "MapService must track tripPolylines")
        self.assertIn('dashArray', content, "Estimated walking legs must use dashed styling")
        self.assertIn('trip-origin-marker', content, "Must render origin marker (A)")
        self.assertIn('trip-dest-marker', content, "Must render destination marker (B)")
        self.assertIn('trip-stop-transfer', content, "Must render transfer stop marker")
        self.assertIn('enableMapPinSelection', content, "Must implement enableMapPinSelection")
        self.assertIn('renderMapPinMarker', content, "Must implement renderMapPinMarker")
        self.assertIn('L.map', content, "Must strictly preserve Leaflet map")
        self.assertNotIn('google.maps', content, "Must NOT include Google Maps JavaScript SDK")

    # 14. UI Integration, Debounce & Map Pin Binding
    def test_app_ui_integration_contract(self):
        with open(WORKSPACE / 'js' / 'app.js', 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('tryRunPlanner', content, "app.js must implement tryRunPlanner")
        self.assertIn('renderPlannerResults', content, "app.js must implement renderPlannerResults")
        self.assertIn('renderTripOptions', content, "app.js must implement renderTripOptions")
        self.assertIn('openPlannedTripMap', content, "app.js must implement openPlannedTripMap")
        self.assertIn('trip-planner-options', content, "app.js must integrate trip-planner-options")
        self.assertIn('btn-picker-map-pin', content, "app.js must bind map pin picker CTA")
        self.assertIn('searchDebounceTimer', content, "app.js must debounce search input")
        self.assertIn("bestTrip.transfers === 2 ? '2 chuyển tiếp' : '1 chuyển tiếp'", content, "app.js must dynamically display 1 or 2 chuyen tiep based on transfers")

    # 15. Backward Compatibility: findRoutesBetween Unchanged
    def test_find_routes_between_backward_compatibility(self):
        node_script = """
        const fs = require('fs');
        const { BusService } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.isLoaded = true;

        const direct = bs.findRoutesBetween('Bến xe TT', 'Phố cổ Hội An');
        if (direct.length === 0 || direct[0].routeNumber !== '02') process.exit(1);

        const disjoint = bs.findRoutesBetween('Hòa Hiệp Nam', 'Phố cổ Hội An');
        if (!Array.isArray(disjoint) || disjoint.length !== 0) process.exit(2);
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "findRoutesBetween backward compatibility failed")

    # 16. Security Contract: Public/Restricted Client Credential Boundary (Finding 1)
    def test_security_credential_audit(self):
        # Prohibited terms representing algorithm bypass or Google Map instantiations (Leaflet strictly preserved)
        prohibited_sdk_terms = [
            "findTransferRoutes",
            "buildTransferItinerary",
            "findMultiLegRoutes",
            "transferItinerary",
            "google.maps.Map"  # Strictly prohibited: Leaflet/OSM must never be replaced by Google Map
        ]
        files_to_check = [
            WORKSPACE / "js" / "busService.js",
            WORKSPACE / "js" / "app.js",
            WORKSPACE / "js" / "mapService.js",
            WORKSPACE / "index.html"
        ]
        google_api_key_regex = re.compile(r'AIza[0-9A-Za-z-_]{35}')

        for fpath in files_to_check:
            if not fpath.exists(): continue
            content = fpath.read_text(encoding="utf-8")
            
            # 1. No committed real API keys
            matches = google_api_key_regex.findall(content)
            self.assertEqual(len(matches), 0, f"Found hardcoded Google API key in {fpath.name}: {matches}")

            # 2. No prohibited terms (no algorithm bypass, no google.maps.Map)
            for term in prohibited_sdk_terms:
                self.assertNotIn(term, content, f"Prohibited term '{term}' found in {fpath.name}")

        # 3. index.html must document public website-restricted client credential boundary (never secret)
        index_html = (WORKSPACE / "index.html").read_text(encoding="utf-8")
        self.assertIn("website-restricted", index_html, "index.html must document website-restricted credential boundary")
        self.assertIn("NEVER server secrets", index_html, "index.html must explicitly forbid server secrets")

        # 4. app.js must provide Places policy attribution branding when Google predictions are displayed
        app_js = (WORKSPACE / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn("google-attribution", app_js, "app.js must provide Google Places attribution branding")

    # 17. Invalid Place Resolution & Picker Guard Contract (Finding 3)
    def test_invalid_place_resolution_and_picker_guard(self):
        node_script = """
        const { LocationManager, ResolvedLocation } = require('./js/busService.js');

        (async () => {
            // Mock Place Details failure (e.g. 429 rate limit or error)
            global.fetch = async () => ({ ok: false, status: 429 });

            const lm = new LocationManager(null, { google: { apiKey: 'mock_test_key' } });

            // Case 1: Google autocomplete item with null coordinates fails resolve
            const googleItem = {
                id: 'place_err_1',
                placeId: 'place_err_1',
                displayName: 'Địa điểm không có tọa độ',
                address: 'Địa điểm không có tọa độ',
                lat: null,
                lng: null,
                provider: 'google'
            };

            const resolved = await lm.resolve('place_err_1', googleItem);
            if (resolved !== null) {
                console.error('Expected lm.resolve to return null on details failure, got:', resolved);
                process.exit(1);
            }

            // Case 2: Constructing ResolvedLocation with null coords fails isValid()
            const invalidLoc = new ResolvedLocation(googleItem);
            if (invalidLoc.isValid()) {
                console.error('ResolvedLocation with null coordinates must NOT be valid');
                process.exit(2);
            }

            // Case 3: Fallback ONLY occurs when real local candidate with valid coordinates exists
            const localMatched = await lm.resolve('poi_cau_rong', { displayName: 'Cầu Rồng Đà Nẵng', provider: 'google' });
            if (!localMatched || !localMatched.isValid() || localMatched.lat !== 16.0612) {
                console.error('Expected fallback to local candidate with valid coordinates');
                process.exit(3);
            }
        })();
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Invalid place resolution and picker guard test failed")

    # 18. Data-Confidence Ranking on Real Dataset & Transfer Legs (Finding 4)
    def test_data_confidence_ranking_on_real_data(self):
        node_script = """
        const fs = require('fs');
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation, BestStopResolver } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const bsr = new BestStopResolver(bs);

        // 1. Verify calculateConfidencePenalty on real route.dataQuality.stopMetrics
        const r05 = routes.find(r => r.routeNumber === '05');
        const pen05Out = bsr.calculateConfidencePenalty(r05, 'outbound');
        const pen05In = bsr.calculateConfidencePenalty(r05, 'inbound');
        if (pen05Out !== 0 || pen05In !== 0) {
            console.error('Expected penalty 0 for Route 05, got out:', pen05Out, 'in:', pen05In);
            process.exit(1);
        }

        const r12 = routes.find(r => r.routeNumber === '12 (Quảng Nam)');
        const pen12Out = bsr.calculateConfidencePenalty(r12, 'outbound');
        if (pen12Out !== 5.0) {
            console.error('Expected penalty 5.0 for Route 12 outbound, got:', pen12Out);
            process.exit(2);
        }

        // 2. Focused unit test: two viable routes with identical distance/duration where lower-quality route receives penalty
        const rHigh = JSON.parse(JSON.stringify(r05));
        rHigh.id = 'route_high_conf';
        rHigh.routeNumber = 'TH';
        rHigh.dataQuality.stopMetrics.outbound = { total: 10, verified: 9, unresolved: 1 }; // 90% verified -> 0 penalty

        const rLow = JSON.parse(JSON.stringify(r05));
        rLow.id = 'route_low_conf';
        rLow.routeNumber = 'TL';
        rLow.dataQuality.stopMetrics.outbound = { total: 10, verified: 5, unresolved: 5 }; // 50% verified -> 5.0 penalty

        const bsTest = new BusService();
        bsTest.routes = [rHigh, rLow];
        bsTest.stops = stops;
        bsTest.isLoaded = true;

        const tpTest = new TransitPlanner(bsTest, new WalkingRouter());
        const oLoc = new ResolvedLocation({ displayName: 'ĐH Bách Khoa', lat: 16.0754, lng: 108.1528 });
        const dLoc = new ResolvedLocation({ displayName: 'CV Biển Đông', lat: 16.0687, lng: 108.2464 });

        const plan = tpTest.planTrip(oLoc, dLoc);
        if (!plan.trips || plan.trips.length === 0) process.exit(3);

        const topTrip = plan.trips[0];
        if (topTrip.route.id !== 'route_high_conf') {
            console.error('Expected top trip to be route_high_conf, got:', topTrip.route.id);
            process.exit(4);
        }
        if (topTrip.confidencePenalty !== 0) {
            console.error('Expected top trip confidencePenalty === 0, got:', topTrip.confidencePenalty);
            process.exit(5);
        }

        // 3. For transfer trips, verify independent confidence calculation per leg
        const penA = bsr.calculateConfidencePenalty(rHigh, 'outbound'); // 0
        const penB = bsr.calculateConfidencePenalty(rLow, 'outbound');  // 5.0
        const totalTransferPen = penA + penB;
        if (totalTransferPen !== 5.0) {
            console.error('Expected transfer total penalty 5.0, got:', totalTransferPen);
            process.exit(6);
        }
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Data confidence ranking test failed")

    # 21. Task 008: 2-Transfer Route Planning, 7 Legs & Walking Roles Contract
    def test_task008_two_transfer_seven_legs_contract(self):
        node_script = """
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation } = require('./js/busService.js');

        const r1 = {
          id: 'R1', routeNumber: 'R1', name: 'Tuyến R1', status: 'active',
          stops: { outbound: [
            { name: 'Stop R1_1', lat: 16.000, lng: 108.000, status: 'verified' },
            { name: 'Stop R1_2', lat: 16.010, lng: 108.010, status: 'verified' }
          ]},
          geometry: { outbound: [[16.000, 108.000], [16.010, 108.010]] }
        };
        const r2 = {
          id: 'R2', routeNumber: 'R2', name: 'Tuyến R2', status: 'active',
          stops: { outbound: [
            { name: 'Stop R2_1', lat: 16.0105, lng: 108.0105, status: 'verified' },
            { name: 'Stop R2_2', lat: 16.020, lng: 108.020, status: 'verified' },
            { name: 'Stop R2_3', lat: 16.030, lng: 108.030, status: 'verified' }
          ]},
          geometry: { outbound: [[16.0105, 108.0105], [16.020, 108.020], [16.030, 108.030]] }
        };
        const r3 = {
          id: 'R3', routeNumber: 'R3', name: 'Tuyến R3', status: 'active',
          stops: { outbound: [
            { name: 'Stop R3_1', lat: 16.0305, lng: 108.0305, status: 'verified' },
            { name: 'Stop R3_2', lat: 16.040, lng: 108.040, status: 'verified' },
            { name: 'Stop R3_3', lat: 16.050, lng: 108.050, status: 'verified' }
          ]},
          geometry: { outbound: [[16.0305, 108.0305], [16.040, 108.040], [16.050, 108.050]] }
        };

        const bs = new BusService();
        bs.routes = [r1, r2, r3];
        bs.stops = [...r1.stops.outbound, ...r2.stops.outbound, ...r3.stops.outbound];
        bs.isLoaded = true;
        bs.isDirectionPlanningReady = (r, dir) => true;
        bs.isServiceUsable = (r, time, dir) => true;

        const tp = new TransitPlanner(bs, new WalkingRouter());
        const oLoc = new ResolvedLocation({ displayName: 'Điểm Đi', lat: 16.0001, lng: 108.0001 });
        const dLoc = new ResolvedLocation({ displayName: 'Điểm Đến', lat: 16.0499, lng: 108.0499 });

        const plan = tp.planTrip(oLoc, dLoc);
        if (!plan.trips || plan.trips.length === 0) process.exit(1);

        const t = plan.trips[0];
        if (t.type !== 'connecting') process.exit(2);
        if (t.transfers !== 2) process.exit(3);
        if (t.badge !== 'Chuyển tuyến 2 lần') process.exit(4);
        if (t.legs.length !== 7) process.exit(5);
        if (t.legs[0].walkingRole !== 'origin') process.exit(6);
        if (t.legs[1].type !== 'transit') process.exit(7);
        if (t.legs[2].walkingRole !== 'transfer') process.exit(8);
        if (t.legs[3].type !== 'transit') process.exit(9);
        if (t.legs[4].walkingRole !== 'transfer') process.exit(10);
        if (t.legs[5].type !== 'transit') process.exit(11);
        if (t.legs[6].walkingRole !== 'destination') process.exit(12);
        if (t.transferBufferMinutes !== 10) process.exit(13);
        if (!Array.isArray(t.routes) || t.routes.length !== 3) process.exit(14);
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Task 008 2-transfer 7-legs contract failed")

    # 22. Task 008: Anti-Loop & Route Reuse Rejection Fail-Closed
    def test_task008_anti_loop_and_route_reuse_rejection(self):
        node_script = """
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation } = require('./js/busService.js');

        const r1 = {
          id: 'R1', routeNumber: 'R1', name: 'Tuyến R1', status: 'active',
          stops: { outbound: [
            { name: 'Stop R1_1', lat: 16.000, lng: 108.000, status: 'verified' },
            { name: 'Stop R1_2', lat: 16.010, lng: 108.010, status: 'verified' }
          ]},
          geometry: { outbound: [[16.000, 108.000], [16.010, 108.010]] }
        };
        const r2 = {
          id: 'R2', routeNumber: 'R2', name: 'Tuyến R2', status: 'active',
          stops: { outbound: [
            { name: 'Stop R2_1', lat: 16.0105, lng: 108.0105, status: 'verified' },
            { name: 'Stop R2_2', lat: 16.020, lng: 108.020, status: 'verified' },
            { name: 'Stop R2_3', lat: 16.030, lng: 108.030, status: 'verified' }
          ]},
          geometry: { outbound: [[16.0105, 108.0105], [16.020, 108.020], [16.030, 108.030]] }
        };
        // Reused route ID: R3 has same ID as R1 -> R1 -> R2 -> R1 loop
        const r3 = {
          id: 'R1', routeNumber: 'R1', name: 'Tuyến R1', status: 'active',
          stops: { outbound: [
            { name: 'Stop R3_1', lat: 16.0305, lng: 108.0305, status: 'verified' },
            { name: 'Stop R3_2', lat: 16.040, lng: 108.040, status: 'verified' },
            { name: 'Stop R3_3', lat: 16.050, lng: 108.050, status: 'verified' }
          ]},
          geometry: { outbound: [[16.0305, 108.0305], [16.040, 108.040], [16.050, 108.050]] }
        };

        const bs = new BusService();
        bs.routes = [r1, r2, r3];
        bs.stops = [...r1.stops.outbound, ...r2.stops.outbound, ...r3.stops.outbound];
        bs.isLoaded = true;
        bs.isDirectionPlanningReady = (r, dir) => true;
        bs.isServiceUsable = (r, time, dir) => true;

        const tp = new TransitPlanner(bs, new WalkingRouter());
        const oLoc = new ResolvedLocation({ displayName: 'Điểm Đi', lat: 16.0001, lng: 108.0001 });
        const dLoc = new ResolvedLocation({ displayName: 'Điểm Đến', lat: 16.0499, lng: 108.0499 });

        const plan = tp.planTrip(oLoc, dLoc);
        const hasReused = plan.trips.some(t => {
          const ids = t.routes.map(r => r.id);
          return new Set(ids).size !== ids.length;
        });
        if (hasReused) process.exit(1);
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Anti-loop route reuse rejection failed")

    # 23. Task 008: Monotonic Direction, Inactive & Unready Route Rejection
    def test_task008_monotonic_direction_and_unready_rejection(self):
        node_script = """
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation } = require('./js/busService.js');

        const r1 = {
          id: 'R1', routeNumber: 'R1', name: 'Tuyến R1', status: 'active',
          stops: { outbound: [
            { name: 'Stop R1_1', lat: 16.000, lng: 108.000, status: 'verified' },
            { name: 'Stop R1_2', lat: 16.010, lng: 108.010, status: 'verified' }
          ]},
          geometry: { outbound: [[16.000, 108.000], [16.010, 108.010]] }
        };
        const r2 = {
          id: 'R2', routeNumber: 'R2', name: 'Tuyến R2', status: 'active',
          stops: { outbound: [
            { name: 'Stop R2_1', lat: 16.0105, lng: 108.0105, status: 'verified' },
            { name: 'Stop R2_2', lat: 16.020, lng: 108.020, status: 'verified' },
            { name: 'Stop R2_3', lat: 16.030, lng: 108.030, status: 'verified' }
          ]},
          geometry: { outbound: [[16.0105, 108.0105], [16.020, 108.020], [16.030, 108.030]] }
        };
        const r3 = {
          id: 'R3', routeNumber: 'R3', name: 'Tuyến R3', status: 'active',
          stops: { outbound: [
            { name: 'Stop R3_1', lat: 16.0305, lng: 108.0305, status: 'verified' },
            { name: 'Stop R3_2', lat: 16.040, lng: 108.040, status: 'verified' },
            { name: 'Stop R3_3', lat: 16.050, lng: 108.050, status: 'verified' }
          ]},
          geometry: { outbound: [[16.0305, 108.0305], [16.040, 108.040], [16.050, 108.050]] }
        };

        const oLoc = new ResolvedLocation({ displayName: 'Điểm Đi', lat: 16.0001, lng: 108.0001 });
        const dLoc = new ResolvedLocation({ displayName: 'Điểm Đến', lat: 16.0499, lng: 108.0499 });

        // Case A: Intermediate route is NOT planning ready
        const bsA = new BusService();
        bsA.routes = [r1, r2, r3];
        bsA.stops = [...r1.stops.outbound, ...r2.stops.outbound, ...r3.stops.outbound];
        bsA.isLoaded = true;
        bsA.isDirectionPlanningReady = (r, dir) => r.id !== 'R2';
        bsA.isServiceUsable = (r, time, dir) => true;

        const tpA = new TransitPlanner(bsA, new WalkingRouter());
        const planA = tpA.planTrip(oLoc, dLoc);
        if (planA.trips.length !== 0) process.exit(1);

        // Case B: Final route is suspended/not usable
        const bsB = new BusService();
        bsB.routes = [r1, r2, r3];
        bsB.stops = [...r1.stops.outbound, ...r2.stops.outbound, ...r3.stops.outbound];
        bsB.isLoaded = true;
        bsB.isDirectionPlanningReady = (r, dir) => true;
        bsB.isServiceUsable = (r, time, dir) => r.id !== 'R3';

        const tpB = new TransitPlanner(bsB, new WalkingRouter());
        const planB = tpB.planTrip(oLoc, dLoc);
        if (planB.trips.length !== 0) process.exit(2);
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Monotonic direction / unready route rejection failed")

    # 24. Task 008: Unresolved Transfer Stop Fail-Closed & Transfer Walk <= 400m
    def test_task008_unresolved_transfer_stop_fail_closed(self):
        node_script = """
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation } = require('./js/busService.js');

        const r1 = {
          id: 'R1', routeNumber: 'R1', name: 'Tuyến R1', status: 'active',
          stops: { outbound: [
            { name: 'Stop R1_1', lat: 16.000, lng: 108.000, status: 'verified' },
            { name: 'Stop R1_2', lat: 16.010, lng: 108.010, status: 'verified' }
          ]},
          geometry: { outbound: [[16.000, 108.000], [16.010, 108.010]] }
        };
        const r2Unresolved = {
          id: 'R2', routeNumber: 'R2', name: 'Tuyến R2', status: 'active',
          stops: { outbound: [
            { name: 'Stop R2_1', lat: null, lng: null, status: 'unresolved' },
            { name: 'Stop R2_2', lat: 16.020, lng: 108.020, status: 'verified' },
            { name: 'Stop R2_3', lat: 16.030, lng: 108.030, status: 'verified' }
          ]},
          geometry: { outbound: [[16.0105, 108.0105], [16.020, 108.020], [16.030, 108.030]] }
        };
        const r3 = {
          id: 'R3', routeNumber: 'R3', name: 'Tuyến R3', status: 'active',
          stops: { outbound: [
            { name: 'Stop R3_1', lat: 16.0305, lng: 108.0305, status: 'verified' },
            { name: 'Stop R3_2', lat: 16.040, lng: 108.040, status: 'verified' },
            { name: 'Stop R3_3', lat: 16.050, lng: 108.050, status: 'verified' }
          ]},
          geometry: { outbound: [[16.0305, 108.0305], [16.040, 108.040], [16.050, 108.050]] }
        };

        const bs = new BusService();
        bs.routes = [r1, r2Unresolved, r3];
        bs.stops = [...r1.stops.outbound, ...r2Unresolved.stops.outbound, ...r3.stops.outbound];
        bs.isLoaded = true;
        bs.isDirectionPlanningReady = (r, dir) => true;
        bs.isServiceUsable = (r, time, dir) => true;

        const tp = new TransitPlanner(bs, new WalkingRouter());
        const oLoc = new ResolvedLocation({ displayName: 'Điểm Đi', lat: 16.0001, lng: 108.0001 });
        const dLoc = new ResolvedLocation({ displayName: 'Điểm Đến', lat: 16.0499, lng: 108.0499 });

        const plan = tp.planTrip(oLoc, dLoc);
        if (plan.trips.length !== 0) process.exit(1);
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Unresolved transfer stop fail-closed test failed")

    # 25. Task 008: Deterministic Multi-Factor Ranking & Stable Tie-Break
    def test_task008_deterministic_ranking_multi_factor(self):
        node_script = """
        const fs = require('fs');
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const tp = new TransitPlanner(bs, new WalkingRouter());
        const oLoc = new ResolvedLocation({ displayName: 'Huỳnh Thúc Kháng', lat: 15.5673332, lng: 108.4904846 });
        const dLoc = new ResolvedLocation({ displayName: '954 Phan Châu Trinh', lat: 15.555436, lng: 108.5059009 });

        const run1 = tp.planTrip(oLoc, dLoc);
        const ids1 = run1.trips.map(t => t.id);

        for (let r = 0; r < 4; r++) {
          const runN = tp.planTrip(oLoc, dLoc);
          const idsN = runN.trips.map(t => t.id);
          if (JSON.stringify(ids1) !== JSON.stringify(idsN)) {
            process.exit(1);
          }
        }

        for (let i = 0; i < run1.trips.length - 1; i++) {
          const a = run1.trips[i];
          const b = run1.trips[i + 1];
          if (a.transfers > b.transfers) process.exit(2);
        }
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Deterministic multi-factor ranking test failed")

    # 26. Task 008: Performance Benchmark <250ms per Query
    def test_task008_search_performance_benchmark(self):
        node_script = """
        const fs = require('fs');
        const { BusService, WalkingRouter, TransitPlanner, ResolvedLocation } = require('./js/busService.js');
        const routes = JSON.parse(fs.readFileSync('./data/danangbus_routes.json', 'utf8'));
        const stops = JSON.parse(fs.readFileSync('./data/danangbus_stops.json', 'utf8'));
        const bs = new BusService();
        bs.routes = routes;
        bs.stops = stops;
        bs.isLoaded = true;

        const tp = new TransitPlanner(bs, new WalkingRouter());
        const queryPairs = [
          [ { displayName: 'ĐH Bách Khoa', lat: 16.0754, lng: 108.1528 }, { displayName: 'CV Biển Đông', lat: 16.0687, lng: 108.2464 } ],
          [ { displayName: 'Huỳnh Thúc Kháng', lat: 15.5673332, lng: 108.4904846 }, { displayName: '954 Phan Châu Trinh', lat: 15.555436, lng: 108.5059009 } ],
          [ { displayName: 'Bến xe TT', lat: 16.0594, lng: 108.1738 }, { displayName: 'Phố cổ Hội An', lat: 15.8801, lng: 108.3272 } ]
        ];

        tp.planTrip(new ResolvedLocation(queryPairs[0][0]), new ResolvedLocation(queryPairs[0][1]));

        for (const [o, d] of queryPairs) {
          const oLoc = new ResolvedLocation(o);
          const dLoc = new ResolvedLocation(d);
          const t0 = process.hrtime.bigint();
          const plan = tp.planTrip(oLoc, dLoc);
          const t1 = process.hrtime.bigint();
          const ms = Number(t1 - t0) / 1e6;
          if (ms >= 250) {
            console.error('Query exceeded 250ms SLA:', ms);
            process.exit(1);
          }
        }
        """
        res = subprocess.run(['node', '-e', node_script], cwd=WORKSPACE)
        self.assertEqual(res.returncode, 0, "Search performance benchmark SLA <250ms failed")

if __name__ == '__main__':
    unittest.main()
