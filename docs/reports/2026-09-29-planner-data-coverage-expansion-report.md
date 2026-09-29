# Planner Data Coverage Expansion Acceptance Report

Task-ID: tsk_19e19c78-c75e-4346-be75-00f26b27bf8f

Ngày review: 2026-09-29
Role review: TL
Task: Planner Data Coverage Expansion

## Scope
- Mở rộng planner-ready coverage cho route `02` cả hai chiều.
- Mở rộng `TKY-CHU` outbound để toàn tuyến đạt two-direction readiness.
- Giữ route `21` ngoài slice vì còn false-positive/location issue cần xử lý riêng.
- Không hạ chuẩn fail-closed, không fabricate stop coordinates hoặc geometry.
- Sửa parser/provenance bug làm ngưỡng giá vé 10km bị gán nhầm vào route distance.

## Implementation Evidence
- Commit implementation: `e5f70f1a152cb1e2fe50b413b513e12b6ab8f367`.
- Route `02`:
  - `distanceKm` được trả về unknown/null vì không có independent official route-distance evidence.
  - Không dùng độ dài OSRM như official route distance.
  - Outbound/inbound geometry đạt provenance `osm_osrm_verified` sau khi PASS các check còn áp dụng.
- `TKY-CHU` outbound:
  - Resolver loại false-positive `463 Phan Bội Châu` -> `63 Phan Bội Châu`.
  - Bổ sung audited landmarks từ OSM cache và locality formatting cho Quảng Nam.
  - Outbound đạt đủ verified anchors và geometry PASS.
- Route `21` tiếp tục fail-closed.

## Coverage Result
Baseline:
- 3 routes `tripPlanningReady`.
- 7 / 46 directions `eligibleForPlanning`.
- 359 / 638 verified stops (56.27%).

Sau implementation:
- 5 routes `tripPlanningReady`: `05`, `02`, `TKY-TMY`, `TKY-NTH`, `TKY-CHU`.
- 10 / 46 directions `eligibleForPlanning`.
- 363 / 638 verified stops (56.90%).
- 275 unresolved stops tiếp tục fail-closed.
- DataQuality drift: 0.

## TL Independent Verification
TL đã tự chạy lại:
- `python3 scripts/validate_data_quality.py --check` -> PASS, 100% routes khớp canonical validator, zero drift.
- `python3 scripts/validate_data_quality.py --coverage` -> PASS, 5/23 planning-ready, 363/638 verified stops.
- `python3 scripts/test_data_quality_and_planner_readiness.py` -> 14/14 PASS.
- `python3 -m unittest discover -s scripts -p "test_*.py"` -> 44/44 PASS.
- `python3 scripts/test_trip_planner.py` -> 10/10 PASS.
- `python3 scripts/test_task10_regression_acceptance.py` -> 20/20 PASS.

Review note:
- DEV review prose ghi sai tọa độ cho OSM nodes `11898042382` và `11898042393`, nhưng TL đối chiếu trực tiếp `data/osm_cache/transit.json`; implementation dùng đúng tọa độ cache:
  - `11898042382`: `15.5787507, 108.4753287`.
  - `11898042393`: `15.5616137, 108.4994601`.
- Đây là transcription mismatch trong DEV handoff, không phải implementation defect.

## Review Result
TL Technical Acceptance: PASS.

Task đạt acceptance của Planner Data Coverage Expansion:
- Coverage tăng đo được.
- Mọi direction mới planner-eligible đều đi qua validator hiện hành.
- Không giảm validator thresholds.
- Unresolved/ambiguous data vẫn fail-closed.
- Regression matrix hiện tại PASS.

## Known Limitations
- Production tại thời điểm review vẫn đang phục vụ coverage cũ cho route `02` và `TKY-CHU outbound`; production browser smoke PASS nhưng chưa chứng minh dataset coverage mới đã deploy.
- Việc publish/deploy dataset mới và source/production traceability thuộc release/closure gate tiếp theo.
- Route `21` vẫn chưa planner-ready và cần xử lý false-positive/corridor evidence riêng.
- External geocoding/walking provider và realtime vehicle/ETA không nằm trong scope Task này.
- Git publication chưa được thực hiện vì `git_push_authorized=OFF`; local `HEAD` đang ahead `origin/main` 20 commits, không phải blocker theo policy.
