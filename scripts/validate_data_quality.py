#!/usr/bin/env python3
"""
Task 8: Data Quality Contract & Planner Readiness Validator
Deterministic validator for Danabus routes dataset.

Evaluates and guarantees dataQuality contract:
- hasOutboundStops / hasInboundStops (verified subset >= 2 stops with strictly monotonic order)
- hasOutboundGeometry / hasInboundGeometry (GPS verified provenance + valid polyline)
- hasFareModel (valid canonical flat or distance-tiered pricing)
- tripPlanningReady (route active + both directions eligible + valid fare)
- directions.outbound / directions.inbound (direction-level planning readiness)
- stopMetrics (total, verified, unresolved stops per direction)

Modes:
  --check    : Validates that dataQuality in data/danangbus_routes.json matches computed values (fails with exit code 1 if drift)
  --enrich   : Computes and updates dataQuality directly into data/danangbus_routes.json
  --coverage : Generates machine-readable coverage report docs/reports/task-8-data-quality-coverage.json
"""

import sys
import os
import json
import math
import argparse
from datetime import datetime

ROUTES_FILE = "data/danangbus_routes.json"
COVERAGE_REPORT_FILE = "docs/reports/task-8-data-quality-coverage.json"

def is_finite_number(val):
    if isinstance(val, bool):
        return False
    return val is not None and isinstance(val, (int, float)) and not math.isnan(val) and not math.isinf(val)

def is_valid_coordinate(lat, lng):
    if not is_finite_number(lat) or not is_finite_number(lng):
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0

def is_verified_stop(stop):
    if not isinstance(stop, dict):
        return False
    if stop.get("status") != "verified":
        return False
    lat = stop.get("lat")
    lng = stop.get("lng")
    return is_valid_coordinate(lat, lng)

def evaluate_direction_stops(stops_list):
    if not isinstance(stops_list, list):
        stops_list = []
    
    total = len(stops_list)
    verified_stops = []
    
    for s in stops_list:
        if is_verified_stop(s):
            verified_stops.append(s)
            
    verified_count = len(verified_stops)
    unresolved_count = total - verified_count
    
    metrics = {
        "total": total,
        "verified": verified_count,
        "unresolved": unresolved_count
    }
    
    # Requirement: at least 2 verified stops with strictly increasing order
    if verified_count < 2:
        return False, metrics, f"Chỉ có {verified_count}/{total} trạm verified (yêu cầu tối thiểu 2 trạm có tọa độ hợp lệ)"
    
    # Check monotonic order
    for i in range(len(verified_stops) - 1):
        curr_order = verified_stops[i].get("order", 0)
        next_order = verified_stops[i + 1].get("order", 0)
        if not (is_finite_number(curr_order) and is_finite_number(next_order) and curr_order < next_order):
            return False, metrics, f"Thứ tự trạm dừng verified không tăng đơn điệu (order {curr_order} >= {next_order})"
            
    return True, metrics, None

def evaluate_direction_geometry(route, direction):
    geom = route.get("geometry") or {}
    points = geom.get(direction)
    prov = (geom.get("provenance") or {}).get(direction) or {}
    
    if not isinstance(points, list) or len(points) < 2:
        return False, "Thiếu dữ liệu lộ trình polyline (points < 2)"
    
    # Verify all coordinates in points are finite and within geographic range
    for pt in points:
        if not (isinstance(pt, (list, tuple)) and len(pt) == 2 and is_valid_coordinate(pt[0], pt[1])):
            return False, "Tọa độ polyline không hợp lệ (ngoài phạm vi địa lý hoặc không phải số)"
            
    if prov.get("verified") is not True:
        return False, "Lộ trình chưa được xác minh (provenance.verified != true)"
        
    return True, None

def evaluate_fare_model(route):
    fares = route.get("fares") or {}
    fare_type = fares.get("type")
    
    if fare_type == "flat":
        price = fares.get("flatPrice") if fares.get("flatPrice") is not None else fares.get("singleTicket")
        if is_finite_number(price) and price > 0:
            return True, None
        return False, "Giá vé đồng giá không hợp lệ hoặc thiếu giá"
        
    elif fare_type == "distance_tiered":
        min_p = fares.get("minPrice")
        max_p = fares.get("maxPrice")
        tiers = fares.get("tiers")
        
        # Explicit fail-closed check on minPrice / maxPrice if present
        if min_p is not None and not (is_finite_number(min_p) and min_p > 0):
            return False, "Bảng giá theo chặng chứa minPrice không hợp lệ"
        if max_p is not None and not (is_finite_number(max_p) and max_p > 0):
            return False, "Bảng giá theo chặng chứa maxPrice không hợp lệ"
        if min_p is not None and max_p is not None and is_finite_number(min_p) and is_finite_number(max_p) and min_p > max_p:
            return False, "Bảng giá theo chặng có maxPrice nhỏ hơn minPrice"

        has_min_max = is_finite_number(min_p) and min_p > 0 and is_finite_number(max_p) and max_p >= min_p
        
        # If tiers is present, it must be a non-empty list of valid tier objects
        tiers_present = (tiers is not None)
        has_valid_tiers = False
        if tiers_present:
            if not isinstance(tiers, list) or len(tiers) == 0:
                return False, "Bảng giá tiers không hợp lệ (phải là danh sách không rỗng)"
            for t in tiers:
                if not isinstance(t, dict):
                    return False, "Bảng giá tiers chứa phần tử không phải object"
                price = t.get("price")
                if not (is_finite_number(price) and price > 0):
                    return False, "Bảng giá tiers chứa giá vé không hợp lệ"
                dist_max = t.get("distanceMaxKm")
                if dist_max is not None and not (is_finite_number(dist_max) and dist_max > 0):
                    return False, "Bảng giá tiers chứa khoảng cách distanceMaxKm không hợp lệ"
            has_valid_tiers = True
            
        if not (has_min_max or has_valid_tiers):
            return False, "Bảng giá theo chặng thiếu cả min/maxPrice và tiers hợp lệ"
            
        if fares.get("singleTicket") is not None:
            return False, "Bảng giá theo chặng vi phạm cấm flat singleTicket"
            
        return True, None
        
    return False, f"Loại giá vé không hợp lệ hoặc chưa rõ ({fare_type})"

def compute_data_quality(route):
    """
    Computes canonical dataQuality dictionary for a route.
    Guarantees deterministic, fail-closed results without modifying the route object.
    """
    route_status = route.get("status")
    is_active = (route_status == "active")
    
    stops = route.get("stops") or {}
    out_stops_ready, out_metrics, out_stop_err = evaluate_direction_stops(stops.get("outbound"))
    in_stops_ready, in_metrics, in_stop_err = evaluate_direction_stops(stops.get("inbound"))
    
    out_geom_ready, out_geom_err = evaluate_direction_geometry(route, "outbound")
    in_geom_ready, in_geom_err = evaluate_direction_geometry(route, "inbound")
    
    has_fare_model, fare_err = evaluate_fare_model(route)
    
    # Provenance verification (Task 006 / Roadmap V3 Task 1)
    source_url = route.get("sourceUrl")
    last_verified = route.get("lastVerifiedAt")
    ver_status = route.get("verificationStatus")
    has_provenance = bool(
        source_url
        and isinstance(source_url, str)
        and source_url.startswith("http")
        and last_verified
        and ver_status == "verified"
    )
    prov_err = "Thiếu hoặc chưa xác minh nguồn chính thức (sourceUrl, lastVerifiedAt, verificationStatus)" if not has_provenance else None

    # Direction-level planning eligibility
    out_reasons = []
    if not is_active:
        out_reasons.append(f"Tuyến không hoạt động (status={route_status})")
    if not has_provenance:
        out_reasons.append(prov_err)
    if not out_stops_ready:
        out_reasons.append(out_stop_err)
    if not out_geom_ready:
        out_reasons.append(out_geom_err)
    if not has_fare_model:
        out_reasons.append(fare_err)
    out_eligible = len(out_reasons) == 0
    
    in_reasons = []
    if not is_active:
        in_reasons.append(f"Tuyến không hoạt động (status={route_status})")
    if not has_provenance:
        in_reasons.append(prov_err)
    if not in_stops_ready:
        in_reasons.append(in_stop_err)
    if not in_geom_ready:
        in_reasons.append(in_geom_err)
    if not has_fare_model:
        in_reasons.append(fare_err)
    in_eligible = len(in_reasons) == 0
    
    # Route-level tripPlanningReady
    route_reasons = []
    if not is_active:
        route_reasons.append(f"Tuyến {route.get('id')} tạm ngừng (status={route_status})")
    if not has_provenance:
        route_reasons.append(prov_err)
    if not out_eligible:
        route_reasons.append(f"Chiều đi chưa sẵn sàng: {'; '.join(out_reasons)}")
    if not in_eligible:
        route_reasons.append(f"Chiều về chưa sẵn sàng: {'; '.join(in_reasons)}")
    if not has_fare_model:
        route_reasons.append(f"Giá vé chưa sẵn sàng: {fare_err}")
        
    trip_planning_ready = is_active and has_provenance and out_eligible and in_eligible and has_fare_model
    
    data_quality = {
        "hasOutboundStops": out_stops_ready,
        "hasInboundStops": in_stops_ready,
        "hasOutboundGeometry": out_geom_ready,
        "hasInboundGeometry": in_geom_ready,
        "hasFareModel": has_fare_model,
        "tripPlanningReady": trip_planning_ready,
        "directions": {
            "outbound": {
                "stopsReady": out_stops_ready,
                "geometryReady": out_geom_ready,
                "eligibleForPlanning": out_eligible,
                "reason": None if out_eligible else "; ".join(out_reasons)
            },
            "inbound": {
                "stopsReady": in_stops_ready,
                "geometryReady": in_geom_ready,
                "eligibleForPlanning": in_eligible,
                "reason": None if in_eligible else "; ".join(in_reasons)
            }
        },
        "stopMetrics": {
            "outbound": out_metrics,
            "inbound": in_metrics
        },
        "ineligibilityReasons": route_reasons if not trip_planning_ready else []
    }
    
    return data_quality

def clean_data_quality_for_comparison(dq):
    """Deep clone and strip volatile timestamps if present."""
    if not dq or not isinstance(dq, dict):
        return {}
    res = json.loads(json.dumps(dq))
    res.pop("evaluatedAt", None)
    return res

def run_validation(routes, strict_check=False):
    drift_count = 0
    errors = []
    
    for r in routes:
        rid = r.get("id")
        computed = compute_data_quality(r)
        current = r.get("dataQuality")
        
        if strict_check:
            if current is None:
                drift_count += 1
                errors.append(f"Tuyến {rid}: Thiếu trường 'dataQuality'")
            else:
                c_clean = clean_data_quality_for_comparison(current)
                comp_clean = clean_data_quality_for_comparison(computed)
                if c_clean != comp_clean:
                    drift_count += 1
                    errors.append(f"Tuyến {rid}: Metadata 'dataQuality' bị drift so với tính toán gốc.\n  Hiện tại : {json.dumps(c_clean, ensure_ascii=False)}\n  Kỳ vọng  : {json.dumps(comp_clean, ensure_ascii=False)}")
                    
    return drift_count, errors

def generate_coverage_report(routes):
    total_routes = len(routes)
    active_routes = sum(1 for r in routes if r.get("status") == "active")
    suspended_routes = sum(1 for r in routes if r.get("status") == "suspended")
    
    planning_ready_routes = []
    outbound_only_ready = []
    inbound_only_ready = []
    neither_ready = []
    
    route_details = []
    
    total_stops = 0
    total_verified_stops = 0
    total_unresolved_stops = 0
    
    for r in routes:
        rid = r.get("id")
        r_num = r.get("routeNumber")
        name = r.get("name")
        dq = compute_data_quality(r)
        
        out_dq = dq["directions"]["outbound"]
        in_dq = dq["directions"]["inbound"]
        out_m = dq["stopMetrics"]["outbound"]
        in_m = dq["stopMetrics"]["inbound"]
        
        total_stops += out_m["total"] + in_m["total"]
        total_verified_stops += out_m["verified"] + in_m["verified"]
        total_unresolved_stops += out_m["unresolved"] + in_m["unresolved"]
        
        ready = dq["tripPlanningReady"]
        out_el = out_dq["eligibleForPlanning"]
        in_el = in_dq["eligibleForPlanning"]
        
        if ready:
            planning_ready_routes.append(rid)
        elif out_el and not in_el:
            outbound_only_ready.append(rid)
        elif in_el and not out_el:
            inbound_only_ready.append(rid)
        else:
            neither_ready.append(rid)
            
        route_details.append({
            "id": rid,
            "routeNumber": r_num,
            "name": name,
            "status": r.get("status"),
            "tripPlanningReady": ready,
            "directions": dq["directions"],
            "stopMetrics": dq["stopMetrics"],
            "ineligibilityReasons": dq["ineligibilityReasons"]
        })
        
    report = {
        "generatedAt": datetime.now().isoformat(),
        "summary": {
            "totalRoutes": total_routes,
            "activeRoutes": active_routes,
            "suspendedRoutes": suspended_routes,
            "tripPlanningReadyCount": len(planning_ready_routes),
            "tripPlanningReadyRoutes": planning_ready_routes,
            "outboundOnlyReadyCount": len(outbound_only_ready),
            "outboundOnlyReadyRoutes": outbound_only_ready,
            "inboundOnlyReadyCount": len(inbound_only_ready),
            "inboundOnlyReadyRoutes": inbound_only_ready,
            "neitherReadyCount": len(neither_ready),
            "neitherReadyRoutes": neither_ready,
            "stops": {
                "total": total_stops,
                "verified": total_verified_stops,
                "unresolved": total_unresolved_stops,
                "verifiedPercentage": round((total_verified_stops / total_stops * 100), 2) if total_stops else 0
            }
        },
        "routes": route_details
    }
    return report

def main():
    parser = argparse.ArgumentParser(description="Task 8 Data Quality Validator")
    parser.add_argument("--check", action="store_true", help="Kiểm tra drift metadata trong data/danangbus_routes.json")
    parser.add_argument("--enrich", action="store_true", help="Ghi trực tiếp dataQuality vào data/danangbus_routes.json")
    parser.add_argument("--coverage", action="store_true", help="Xuất báo cáo coverage ra docs/reports/task-8-data-quality-coverage.json")
    args = parser.parse_args()
    
    if not os.path.exists(ROUTES_FILE):
        print(f"Lỗi: Không tìm thấy file {ROUTES_FILE}", file=sys.stderr)
        sys.exit(1)
        
    with open(ROUTES_FILE, "r", encoding="utf-8") as f:
        routes = json.load(f)
        
    if not isinstance(routes, list):
        print(f"Lỗi: Dữ liệu trong {ROUTES_FILE} phải là danh sách (Array)", file=sys.stderr)
        sys.exit(1)
        
    print(f"[*] Đã tải {len(routes)} tuyến từ {ROUTES_FILE}")
    
    if args.enrich:
        print("[*] Đang cập nhật dataQuality trực tiếp vào dataset...")
        for r in routes:
            dq = compute_data_quality(r)
            r["dataQuality"] = dq
            
        with open(ROUTES_FILE, "w", encoding="utf-8") as f:
            json.dump(routes, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"[V] Đã enrich thành công 100% dataQuality cho {len(routes)} tuyến vào {ROUTES_FILE}.")
        
    if args.coverage:
        os.makedirs(os.path.dirname(COVERAGE_REPORT_FILE), exist_ok=True)
        report = generate_coverage_report(routes)
        with open(COVERAGE_REPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"[V] Đã xuất báo cáo coverage máy đọc được ra {COVERAGE_REPORT_FILE}")
        print(f"    - Tuyến tripPlanningReady: {report['summary']['tripPlanningReadyCount']}/{report['summary']['totalRoutes']} {report['summary']['tripPlanningReadyRoutes']}")
        print(f"    - Chiều Inbound-only ready: {report['summary']['inboundOnlyReadyRoutes']}")
        print(f"    - Trạm verified: {report['summary']['stops']['verified']}/{report['summary']['stops']['total']} ({report['summary']['stops']['verifiedPercentage']}%)")

    if args.check or (not args.enrich and not args.coverage):
        drift_count, errors = run_validation(routes, strict_check=True)
        if drift_count > 0:
            print(f"[X] PHÁT HIỆN METADATA DRIFT TRÊN {drift_count} TUYẾN:", file=sys.stderr)
            for err in errors[:10]:
                print(f"    - {err}", file=sys.stderr)
            if len(errors) > 10:
                print(f"    ... và {len(errors) - 10} lỗi khác.", file=sys.stderr)
            sys.exit(1)
        else:
            print("[V] PASS: 100% routes có metadata dataQuality khớp hoàn toàn với validator tất định. Zero drift.")
            sys.exit(0)

if __name__ == "__main__":
    main()
