# Báo cáo nghiệm thu Task 006

Task-ID: tsk_a701b34c-19b8-46f0-aff7-4abfda088416

Ngày nghiệm thu: 2026-09-30

## Phạm vi

Nghiệm thu Roadmap V3 Task 1: đối soát dữ liệu tuyến theo nguồn chính thức, mô hình vòng đời `active | suspended | merged | retired`, provenance, hiệu lực thời gian, alias/lịch sử tuyến, temporary overrides và fail-closed service resolver dùng cho search/schedule/planner.

Không bao gồm Roadmap V3 Tasks 2-6: geocoding/best-stop, multi-transfer graph expansion, hoàn thiện GPS/shape, redesign UX và final release gate.

## Bằng chứng triển khai

- Commit triển khai chính: `17ba14d4f8c453c2a83aed5d8fd06f682604bc04`.
- Commit sửa fail-closed/provenance: `ae1c700f9398cc1ac2a86f52e2aa09f607e2cbbc`.
- Commit sửa official lifecycle: `6c84365a0c45e9854ee6d1ce0c789925e7a33fcd`.
- Dataset hiện có 23 bản ghi: 18 `active`, 3 `suspended`, 2 `merged`, 0 `retired`.
- Provenance machine-readable: 23/23 tuyến verified, 0 evidence gap, 0 alias conflict, 0 lifecycle reference issue.
- `LK02` được giữ làm historical record với `status=merged`, `mergedInto=02`, `effectiveTo=2025-07-17`.
- `LK21` được giữ làm historical record với `status=merged`, `mergedInto=21`, `effectiveTo=2025-07-17`.
- Tuyến `02` và `21` có `effectiveFrom=2025-07-18` cho service sau hợp nhất.
- Nguồn lifecycle hợp nhất: thông báo chính thức DanangBus/Datramac ngày 17/07/2025, hiệu lực từ 18/07/2025:
  `https://www.danangbus.vn/tin-tuc/tin-tuc/hop-nhat-va-dieu-chinh-mot-so-tuyen-buyt-khong-tro-gia-tren-dia-ban-thanh-pho-da-nang-moi-5456.html`.
- Machine-readable reconciliation report: `docs/reports/task-1-official-route-reconciliation.json`.

## Kiểm tra và xác minh

- `python3 scripts/reconcile_official_routes.py --check`: PASS, 23/23 verified explicit official provenance, 0 evidence gap, zero drift.
- `python3 scripts/test_temporal_route_service.py`: PASS 23/23.
- `python3 scripts/validate_data_quality.py --check`: PASS, zero drift.
- `python3 scripts/test_data_quality_and_planner_readiness.py`: PASS 14/14.
- `python3 scripts/test_search_correctness.py`: PASS 10/10 acceptance, 21 Node checks.
- `python3 scripts/test_schedule_and_fare.py`: PASS 9/9.
- `python3 scripts/test_trip_planner.py`: PASS 10/10.
- `python3 scripts/test_map_and_gps.py`: PASS 11/11.
- `python3 scripts/test_production_pwa_runtime.py`: PASS 8/8.
- `python3 scripts/test_task10_regression_acceptance.py`: PASS 20/20 full matrix.

TL cũng chạy probe độc lập cho temporal handover:

- `LK02` và `LK21` usable tại `2025-07-17T23:59:59+07:00`.
- Cả hai fail-closed với `status=merged` tại `2025-07-18T00:00:00+07:00`.
- Historical lookup không `followSuccessor` vẫn trả `LK02/LK21`.
- Explicit `followSuccessor` trả `LK02 -> 02` và `LK21 -> 21`.

## Kết quả review

PASS về technical acceptance cho Task 006.

Các lỗi review trước đã được xử lý:

- Không còn auto-verify route thiếu explicit evidence.
- Thiếu hoặc sai `verificationStatus` fail-closed.
- Schedule không còn bypass temporal unusable state.
- Temporary override bắt buộc provenance hợp lệ khi đang hiệu lực.
- Reconciliation report có evidence/gap/alias/lifecycle/temporal/override validation.
- Official lifecycle của `LK02/LK21` đã khớp thông báo Datramac và không còn xuất hiện như current active service sau ngày hợp nhất.

## Giới hạn đã biết

- Dataset hiện không có temporary override thực tế đang active; override semantics được kiểm chứng bằng test synthetic/negative.
- `git_push_authorized=OFF`, nên các commit local chưa được publish lên remote trong logical run này. Đây là policy bình thường và không phải technical blocker.
- Production browser suites PASS trên deployment hiện tại, nhưng việc publish riêng các thay đổi Task 006 lên production vẫn thuộc bước publication/release do PO kiểm soát.
