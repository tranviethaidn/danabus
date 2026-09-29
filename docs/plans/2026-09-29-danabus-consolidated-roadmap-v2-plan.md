# Kế Hoạch Hợp Nhất Danabus Roadmap V2

**Ngày:** 2026-09-29  
**Nguồn:** Full re-audit ngày 29/09/2026  
**Report:** `docs/reports/2026-09-29-danabus-full-project-reaudit-report.md`  
**Trạng thái:** PLANNING - chờ PO phê duyệt danh sách Task mới trước khi tạo Task trong Core.

## 1. Mục tiêu

Giữ nguyên giá trị của Task 1-10 đã thực hiện, không rebuild project từ đầu, và chuyển project sang một execution plan mới dựa trên trạng thái source/production thực tế.

Mục tiêu gần:

- Git lưu được toàn bộ source đã nghiệm thu.
- Test release deterministic.
- Task 4 có mặt thật trên production.
- PWA/client upgrade an toàn.
- Production acceptance được chạy trên đúng release mới.

Mục tiêu sau:

- tăng coverage planner theo dữ liệu thật;
- optional geocoding/walking provider khi PO chọn provider/cost;
- realtime chỉ mở lại khi có API chính thức/authorized.

## 2. Baseline lịch sử được giữ

| Baseline | Quyết định |
|---|---|
| Task 1 | Giữ accepted baseline |
| Task 2 | Giữ map/GPS fail-closed baseline |
| Task 3 | Giữ CLOSED/DEFERRED, không mở lại |
| Task 4 | Giữ implementation local hiện có, không viết lại |
| Task 5 | Giữ security hardening baseline |
| Task 6 | Giữ search correctness baseline |
| Task 7 | Giữ schedule/fare baseline |
| Task 8 | Giữ data-quality contract |
| Task 9 | Giữ implementation, nhưng revalidate sau stabilization |
| Task 10 | Giữ regression matrix, nâng thành deterministic release gate |

## 3. Danh sách Task mới đề xuất

### Task 11 - Repository & Project Context Reconciliation

**Mục tiêu:** đưa toàn bộ trạng thái đã nghiệm thu vào một Git baseline có thể phục hồi và làm source of truth mới.

**Scope:**

- Audit toàn bộ modified/untracked files.
- Phân loại source, test, plan/report, generated evidence.
- Không bỏ mất code Task 7-10/Task 4.
- Commit theo milestone hợp lý.
- Push `main` sau khi verification PASS.
- Xác nhận `origin/main` khớp release baseline.
- Giữ project context snapshot mới trong workspace.

**Acceptance:**

- `git status` sạch ngoại trừ artifact cố ý bỏ qua.
- Local/remote commit graph rõ ràng.
- Không có accepted implementation chỉ tồn tại ngoài Git.
- Local deterministic suites cơ bản vẫn PASS sau commit.

### Task 12 - Deterministic Browser Acceptance & Release Gate Stabilization

**Mục tiêu:** loại bỏ tình trạng Task 9/Task 10 first-run FAIL nhưng rerun PASS.

**Scope:**

- Reproduce nhiều vòng từ clean browser/profile.
- Phân tích lifecycle: app init, data loaded, navigation, keyboard interaction, `showTripResults`, DOM readiness.
- Không dùng sleep tùy ý làm fix chính.
- Thêm explicit readiness/wait conditions.
- Cách ly test state giữa suites.
- Capture console/runtime/network evidence khi failure xảy ra.
- Chạy repeated acceptance để chứng minh tính ổn định.

**Acceptance:**

- Task 9 browser suite chạy liên tiếp nhiều vòng không flaky.
- Full Task 10 matrix chạy liên tiếp nhiều vòng từ clean state và PASS.
- Failure nếu có phải có diagnostic evidence, không còn "transient" không giải thích được.

### Task 13 - Task 4 Productionization & PWA Release Upgrade

**Mục tiêu:** đưa Address-to-Address Trip Planner đã PASS local lên production đúng cách.

**Scope:**

- Bump release/cache identity khỏi `v9`.
- Đồng bộ `index.html`, CSS/JS, schema/data cần thiết vào explicit production root.
- Deploy `TransitPlanner`, `LocationManager`, `WalkingRouter`, multi-leg map/UI.
- Test fresh install, warm cache migration, controller change và offline fallback.
- Xác minh production artifact hash/feature markers khớp release source.
- Không bật Google API/realtime.

**Acceptance:**

- Production có planner implementation thật.
- Production Task 4 E2E/browser acceptance PASS.
- PWA upgrade từ release cũ sang release mới PASS.
- Không regression security/search/schedule/data-quality/accessibility.
- Production source markers/hash khớp release artifact.

### Task 14 - Planner Data Coverage Expansion

**Mục tiêu:** tăng số tuyến usable cho planner mà không hạ chuẩn fail-closed.

**Scope:**

- Ưu tiên các tuyến active có nhu cầu cao nhưng thiếu verified stops/geometry.
- Resolve thêm stop coordinates bằng evidence/provenance.
- Validate route geometry theo direction.
- Sửa metadata distance/fare nếu evidence cho thấy sai.
- Regenerate `dataQuality` và coverage report.
- Không fabricate coordinates/geometry.

**Acceptance:**

- Coverage tăng đo được so với baseline 3 tuyến hai chiều + 1 tuyến một chiều.
- Mọi tuyến mới được planner dùng phải PASS validator.
- Unresolved data vẫn fail-closed.

### Task 15 - Production Release Acceptance & Project Closure Gate

**Mục tiêu:** tạo một release boundary cuối sau Task 11-14.

**Scope:**

- Full matrix local + production.
- Fresh browser/profile và PWA upgrade path.
- Security negative paths.
- Planner direct/transfer/walking/fail-closed cases.
- Offline/error recovery.
- Dataset drift validation.
- Git/source/production version traceability.
- Tạo final acceptance report.

**Acceptance:**

- Release gate deterministic.
- Production đúng artifact đã commit.
- Không có critical known defect chưa được phân loại.
- PO có đủ evidence để quyết định close project hoặc mở roadmap mới.

## 4. Conditional / Future Scope

Không đưa vào mandatory execution manifest hiện tại:

### External Geocoding / Walking Road Provider

Chỉ mở Task mới khi PO chọn provider và chấp nhận billing/terms. Khi đó mới thay local curated search hoặc Haversine walking estimate bằng provider hợp lệ.

### Realtime Vehicle / ETA

Task 3 vẫn CLOSED. Chỉ mở Task mới nếu có official/authorized API hoặc nguồn GPS được phép dùng, có auth/rate-limit/license rõ ràng.

## 5. Thứ tự thực thi đề xuất

```text
Historical Task 1-10
        |
        v
Task 11 Repository & Context Reconciliation
        |
        v
Task 12 Deterministic Browser Acceptance
        |
        v
Task 13 Task 4 Productionization + PWA Release
        |
        v
Task 14 Planner Data Coverage Expansion
        |
        v
Task 15 Final Production Acceptance / Closure Gate
```

Task 14 có thể được hoãn nếu PO muốn đóng release hiện tại sau Task 13; khi đó Task 15 có thể nghiệm thu release với coverage hiện có và ghi Task 14 thành roadmap tiếp theo. Mặc định trong plan này Task 14 nằm trong execution list để nâng chất lượng planner trước closure.

## 6. Danh sách Task để Core tạo sau khi PO duyệt

1. **Repository & Project Context Reconciliation**
2. **Deterministic Browser Acceptance & Release Gate Stabilization**
3. **Task 4 Productionization & PWA Release Upgrade**
4. **Planner Data Coverage Expansion**
5. **Production Release Acceptance & Project Closure Gate**

Không tạo lại Task 1-10.

## 7. Definition of Done Roadmap V2

- Repository phản ánh đầy đủ accepted source.
- Browser/release gate deterministic.
- Task 4 hoạt động trên production.
- PWA release migration được kiểm chứng.
- Security/search/schedule/data-quality/UI baseline không regression.
- Data coverage có trạng thái minh bạch, không fabricate.
- Production release traceable về commit/source.
- Final acceptance report hoàn tất.
