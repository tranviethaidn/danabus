# Báo cáo nghiệm thu Task 2 - Deterministic Browser Acceptance & Release Gate Stabilization

Task-ID: tsk_f5e8f2d5-f649-4254-aac6-4f65a3ae50cb

Ngày review: 2026-09-29

## Scope

Ổn định browser acceptance và release gate cho baseline Task 9/Task 10, loại bỏ first-run flakiness bằng readiness rõ ràng, browser/profile isolation, lifecycle synchronization và diagnostics có bằng chứng. Không dùng fixed sleep làm điều kiện correctness chính và không thay đổi product code chỉ để làm test xanh.

## Implementation Evidence

Implementation chính nằm trong hai local commit:

- `f2e54b4`: thêm isolated ephemeral browser profiles, predicate waits, CDP framing/error propagation, diagnostics và deterministic teardown.
- `e788de7`: bỏ hoàn toàn việc suppress `controllerchange`, đồng bộ với Service Worker first-run takeover/reload thật bằng `wait_for_settled`, đồng thời bật `Network.enable` trước navigation và bổ sung URL/status cho network diagnostics.

Các file test chính được ổn định:

- `scripts/test_ui_integrity_and_accessibility.py`
- `scripts/test_browser_schedule_and_fare.py`
- `scripts/test_task10_regression_acceptance.py`
- `scripts/browser_smoke_test.py`

Root cause được xác nhận trong browser log: fresh profile đăng ký Service Worker, `clients.claim()` gây `controllerchange`, ứng dụng reload lần đầu; test cũ có thể đọc DOM trong cửa sổ race này. Test mới không vô hiệu behavior đó mà chờ trạng thái sau reload thật.

## TL Verification

TL chạy lại trực tiếp trên workspace hiện tại với fresh ephemeral profiles:

- Task 9 browser acceptance: 5/5 standalone PASS.
- Schedule/Fare browser acceptance: 5/5 standalone PASS.
- Full Task 10 regression acceptance: 3/3 PASS, mỗi lần 20/20, tổng 60/60.
- Khi tính các browser suite chạy lại bên trong 3 full matrix, log ghi nhận 8 lần PASS cho Task 9 và 8 lần PASS cho Schedule/Fare.
- Diagnostic mode Task 9: PASS.
- Diagnostic mode Schedule/Fare: PASS.

Diagnostic verification chứng minh đủ các lớp bằng chứng:

- browser/app state snapshot;
- console logs;
- uncaught runtime JS exception;
- network failure với URL/status;
- failure screenshot.

Log diagnostic đồng thời ghi nhận lifecycle thật:

- Service Worker registered;
- new Service Worker activated;
- `controllerchange` dẫn tới page reload;
- app khởi tạo lại và đạt trạng thái ready sau reload.

Không có unexplained transient failure trong chuỗi TL re-verification.

## Review Result

PASS - TL VERIFIED TECHNICAL ACCEPTANCE.

Task đạt acceptance của Roadmap V2 cho deterministic browser acceptance và release gate stabilization.

## Known Limitations

- Task này chỉ ổn định test/release gate; không productionize Address-to-Address Trip Planner.
- PWA release identity hiện vẫn thuộc baseline `v9`; bump/migration release cho Task 4 thuộc Task Roadmap V2 tiếp theo.
- `git_push_authorized=OFF`; local commits chưa push và đây không phải blocker theo policy hiện hành.
