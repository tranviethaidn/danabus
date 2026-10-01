# Kế hoạch Task 011 - Nghiệm thu End-to-End & Production Gate

Task-ID: tsk_fa69d045-fc12-452b-9c82-8f4da320fafc  
Ngày: 2026-10-01

## 1. Mục tiêu

Khóa một release boundary cuối cho Roadmap V3 bằng ma trận nghiệm thu có thể lặp lại, truy vết được và fail-closed trên local lẫn production.

Release mục tiêu:

- Release: `v12`
- Build: `20261001_v12`
- Service Worker cache: `danabus-cache-v12`
- Static asset query: `?v=20261001_v12`

## 2. Nguyên tắc

- Không sửa/hạ data-quality contract để làm test PASS.
- Không tạo realtime/provider/geometry/stop giả.
- Tái sử dụng suite hiện có; tạo runner Task 011 mới thay vì biến runner Task 010 thành historical mismatch.
- Secret audit chỉ xuất tên file, loại rule và số lượng vi phạm; không in secret/matched value.
- Không `git push` khi `git_push_authorized=OFF`.
- Production publication là boundary riêng sau khi local release candidate PASS.

## 3. Chặng A - Chuẩn bị Release Candidate v12

DEV thực hiện:

1. Bump đồng bộ `sw.js` và `index.html` từ v11 sang v12.
2. Cập nhật toàn bộ runtime/test assertion còn phụ thuộc v11 trong `scripts/`; grep toàn bộ workspace để bảo đảm không còn runtime reference v11 ngoài tài liệu lịch sử/evidence hợp lệ.
3. Cập nhật PWA warm migration để purge cả `danabus-cache-v11`.
4. Bổ sung assertion cho Consumer UX Task 010 trong browser/UI suite nếu còn thiếu.
5. Tạo `scripts/test_release_gate_acceptance.py`.

Runner Task 011 phải có:

- `--local-only`.
- `--repeat N`, mặc định 3 cho browser clean-state khi chạy full gate.
- Layer 1 local deterministic contracts.
- Layer 2 release integrity, secret audit, release/version manifest validation.
- Layer 3 browser/production integration chỉ khi không dùng `--local-only`.
- Non-zero exit ngay khi suite bắt buộc fail.
- JSON summary ổn định để acceptance report đọc lại.

## 4. Chặng B - Local Release Gate

Bắt buộc chạy và PASS:

- temporal route service;
- trip planner core: direct, 1-transfer, 2-transfer, anti-loop;
- inactive-route rejection;
- data-quality/planner readiness;
- map/GPS;
- search correctness;
- schedule/fare;
- Task 010 review regression;
- UI/accessibility assertions không cần production;
- static secret/credential audit;
- release identity consistency v12.

Local browser suites phải chạy clean-state lặp lại tối thiểu 3 vòng nếu suite hỗ trợ profile isolation.

Chỉ sau local PASS mới tạo local commit cho release candidate.

## 5. Chặng C - Production Publication & Verification

Không tự động thực hiện publication production nếu chưa có authority rõ ràng trong turn thực thi.

Khi publication được phép:

1. Chạy staged deploy hiện có: payload -> manifest -> atomic `index.html` -> atomic `sw.js` cuối.
2. Đối chiếu SHA-256 giữa workspace, `/var/www/danabus/public` và live payload cho whitelist deliverables.
3. Chạy production security smoke.
4. Chạy production PWA runtime ít nhất 3 clean profiles:
   - SW takeover/controllerchange;
   - fresh precache v12;
   - warm purge v4-v11;
   - offline fallback;
   - planner E2E;
   - Task 010 feature markers.
5. Chạy browser smoke trên production.
6. Lưu failure diagnostics nếu có: console/network summary, DOM snapshot, screenshot; không lưu secrets.

## 6. Release Traceability

Tạo machine-readable summary:

`docs/reports/task-11-release-gate-summary.json`

Summary tối thiểu gồm:

- release/build/cache identity;
- Git HEAD local;
- origin relation;
- dataset/reconciliation version hoặc artifact reference;
- suite name/status/duration;
- repeat count;
- hash comparison status theo file;
- secret audit status;
- production verification status;
- known limitations.

Không đưa secret values vào JSON.

## 7. Acceptance Report

Sau khi toàn bộ phần được phép chạy PASS, cập nhật/tạo:

`docs/reports/2026-10-01-danabus-roadmap-v3-final-release-acceptance-report.md`

Báo cáo phải tiếng Việt-first và gồm:

- Traceability matrix Task 011.
- Kết quả local deterministic.
- Kết quả repeated browser.
- PWA fresh/warm/offline.
- Asset/hash traceability.
- Secret/security audit.
- Production smoke khi đã publish.
- Git state và ghi nhận `git_push_authorized=OFF`.
- Known limitations/fail-closed boundaries.

## 8. Definition of Done kỹ thuật

- Release identity v12 nhất quán.
- Local release gate PASS lặp lại.
- Không có credential/secret bị bundle hoặc commit.
- Recommended planner journeys vẫn dùng verified data/geometry.
- Direct, 1-transfer, 2-transfer và inactive-route rejection PASS.
- Mobile UX/accessibility/fail-closed PASS.
- Khi production publication được phép: production artifact khớp release candidate và full production smoke/PWA gate PASS.
- Acceptance report có bằng chứng đủ để TL review độc lập.
