# Task 10 Plan - Business-Logic Regression & Production Acceptance

Task-ID: tsk_bacc9b91-9386-4e80-b7bc-5b5fc294696d

## Mục tiêu

Khóa toàn bộ remediation wave Task 5-9 bằng một regression/acceptance contract có thể chạy lại, để trạng thái PASS phản ánh đúng security, search, schedule, fare, data quality, GPS/map và UI semantics trên cả local logic lẫn production.

Task này ưu tiên reuse các suite đã được chứng minh ở Task 5-9. Chỉ bổ sung test hoặc orchestration khi có lỗ coverage; không viết lại business logic đã PASS và không triển khai Address-to-Address Trip Planner của Task 4.

## Baseline đã xác minh

- Approved roadmap yêu cầu Task 10 bao phủ business-logic matrix, browser interaction, public production smoke và negative/error/offline cases.
- Task 9 acceptance report đã ghi nhận 8 suite hiện tại đều PASS ở lần review gần nhất:
  - `scripts/test_ui_integrity_and_accessibility.py`
  - `scripts/test_search_correctness.py`
  - `scripts/test_schedule_and_fare.py`
  - `scripts/test_data_quality_and_planner_readiness.py`
  - `scripts/test_map_and_gps.py`
  - `scripts/security_smoke_test.py`
  - `scripts/test_browser_schedule_and_fare.py`
  - `scripts/browser_smoke_test.py`
- Các mandatory case của roadmap hiện đã có coverage phân tán: direction/order, validation/no-result, suspended/ineligible, before/in/after/next-day/unknown schedule, tiered fare, nearby stops, swap non-stale, voice/reminder fail-closed và sensitive public paths.
- Chưa có Task 10 plan/report hoặc một entry point tổng hợp chứng minh toàn bộ matrix chạy như một acceptance wave.
- Working tree đang chứa thay đổi Task 7-9 chưa commit; Task 10 không được tự ý revert, rewrite hoặc kéo scope sang housekeeping/publish nếu không cần cho acceptance.

## Thiết kế đề xuất cho vòng TL -> DEV -> TL discussion

### 1. Regression matrix có traceability

Tạo một matrix Task 10 ánh xạ từng acceptance case của roadmap tới đúng test hiện có hoặc test mới nếu coverage chưa đủ.

Mỗi case cần ghi rõ:
- case id/nghiệp vụ;
- layer kiểm thử;
- test/script sở hữu;
- expected fail-closed behavior;
- local hay production;
- kết quả thực tế khi acceptance chạy.

Không chấp nhận chỉ ghi "suite PASS" nếu không trace được case P0/P1 sang assertion cụ thể.

### 2. Orchestration tối thiểu, không duplicate logic

Ưu tiên một Task 10 runner mỏng dưới `scripts/` để:
- gọi các suite deterministic/local theo thứ tự cố định;
- chạy validator/data-quality;
- chạy browser/public smoke riêng ở nhóm integration/production;
- fail non-zero ngay khi một suite/case thất bại;
- in summary machine-readable hoặc text ổn định đủ dùng cho acceptance report.

Runner không copy assertion từ Task 5-9 trừ khi roadmap case thật sự chưa có coverage.

### 3. Hai lớp acceptance

**Layer A - deterministic/local**
- Search direction/order/input/no-result/suspended/missing-data.
- Schedule state contract.
- Fare schema/tier/provenance.
- Data quality, eligibility, GPS/nearby-stop primitives.
- UI static/Node truthfulness contract.

**Layer B - browser/production**
- Browser interaction + loading/error/offline/recovery.
- Browser schedule/fare semantics.
- Public production security smoke.
- Browser smoke trên production gồm asset/cache/runtime semantics.

Production failure phải làm Task 10 FAIL; không được hạ xuống warning chỉ vì local suite PASS.

### 4. Negative/fail-closed bắt buộc

Matrix phải chứng minh tối thiểu:
- origin == destination và input rỗng -> validation error;
- reverse order không match outbound sai;
- no direct route -> no-result, không fake fallback;
- suspended/ineligible/missing stop/geometry -> excluded hoặc degraded đúng contract;
- trước/sau service window -> đúng `before_service` / `after_service` / `next_day` / `unknown`;
- tiered fare không bị render như flat fare;
- nearby-stop chỉ dùng candidate verified hợp lệ;
- swap không giữ stale result;
- voice/reminder disabled không tạo fake success;
- dataset/network failure fail-closed và recovery hoạt động;
- sensitive public paths bị chặn.

### 5. Production acceptance evidence

Acceptance cuối Task 10 phải ghi:
- commit/worktree identity đang được test;
- domain production thực tế;
- từng command/suite và actual result;
- matrix PASS/FAIL;
- known limitations không thuộc remediation wave;
- xác nhận không triển khai Task 4 sớm.

Nếu test sinh screenshot/evidence thì chỉ dùng artifact thực do browser test tạo; không dựng ảnh thủ công.

## File dự kiến

- `docs/plans/2026-09-28-task-10-business-logic-regression-production-acceptance-plan.md`
- Có thể thêm một runner mới dưới `scripts/`, tên cuối cùng do discussion chốt.
- Chỉ sửa test hiện có khi phát hiện coverage gap hoặc defect trong assertion.
- `docs/reports/2026-09-28-task-10-business-logic-regression-production-acceptance-report.md` ở phase review/verification.
- Không sửa application business logic trừ khi regression phát hiện defect bắt buộc; khi đó phải quay đúng lifecycle fix/review thay vì che test.

## Acceptance matrix bắt buộc

1. A -> B đúng direction/order: PASS.
2. B -> A ngược order: không match outbound.
3. origin == destination: validation error.
4. origin empty: validation error.
5. destination empty: validation error.
6. Không có direct route: no-result.
7. Suspended/ineligible route: không đề xuất.
8. Thiếu stop/geometry: excluded/degraded theo data-quality contract.
9. 00:46 với service start 05:15: 269 phút / `before_service`.
10. Sau service window: `after_service` hoặc `next_day` đúng contract.
11. Malformed/suspended schedule: `unknown`, không fake time.
12. Tiered fare: không hiển thị flat fare sai.
13. GPS coordinate: nearby-stop candidate hợp lệ, verified-only.
14. Swap locations: không stale result.
15. Voice/reminder disabled: không fake success.
16. Dataset/network failure: visible error, zero fabricated data, retry recovery.
17. Sensitive public paths: blocked.
18. Browser/public smoke: production runtime semantics PASS.
19. Toàn bộ suite Task 5-9 liên quan: regression PASS.
20. Task 4 planner chưa bị triển khai sớm trong Task 10.

## Verification dự kiến

- `python3 scripts/test_search_correctness.py`
- `python3 scripts/test_schedule_and_fare.py`
- `python3 scripts/test_data_quality_and_planner_readiness.py`
- `python3 scripts/test_map_and_gps.py`
- `python3 scripts/test_ui_integrity_and_accessibility.py`
- `python3 scripts/security_smoke_test.py`
- `python3 scripts/test_browser_schedule_and_fare.py`
- `python3 scripts/browser_smoke_test.py`
- Task 10 runner tổng hợp sau khi discussion chốt, nếu DEV xác nhận đây là cách nhỏ nhất để khóa matrix.

## Out of scope

- Address/POI resolution, direct/transfer planner, walking legs, ranking và map rendering của Task 4.
- Realtime vehicle telemetry/provider mới.
- Push Notification scheduler/backend mới.
- Thay đổi product UI hoặc business logic đã PASS chỉ để "làm sạch" code.
- Publish/push/commit policy ngoài phần cần thiết để chứng minh đúng revision đang acceptance.

## Handoff discussion cần DEV phản biện

DEV cần phản hồi ngắn gọn trước implementation:

1. Với 20 acceptance item trên, item nào hiện chưa có assertion trực tiếp trong 8 suite đang có?
2. Có nên thêm một runner Task 10 mỏng để orchestrate và fail-fast, hay một manifest/matrix test khác sẽ nhỏ hơn mà vẫn traceable?
3. Cách tách local deterministic và production/browser tests thế nào để kết quả rõ ràng, không che lỗi mạng/runtime?
4. Negative case nào còn thiếu để bảo đảm fail-closed thay vì chỉ happy-path?
5. Có file production/business logic nào thật sự cần sửa trong Task 10, hay scope implementation chỉ nên là regression harness + evidence/report?
