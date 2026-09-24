import sys
import os
import re
import json
from lxml import html

sys.stdout.reconfigure(encoding='utf-8')
os.makedirs('data', exist_ok=True)

with open(r'C:\Users\Hai Tran\.gemini\antigravity-ide\brain\30dd6919-cd3a-449e-aec1-26e917e02d72\.system_generated\steps\5\content.md', 'r', encoding='utf-8') as f:
    full_md = f.read()

with open('danangbus_raw.html', 'r', encoding='utf-8') as f:
    raw_html = f.read()

tree = html.fromstring(raw_html)
tables = tree.xpath('//table')

def clean(text):
    if not text:
        return ""
    text = re.sub(r'\xa0', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def parse_four_col_stops_table(table):
    outbound = []
    inbound = []
    rows = table.xpath('.//tr')
    start_row = 0
    for r_idx, row in enumerate(rows):
        cells = [clean(c.text_content()) for c in row.xpath('.//td|.//th')]
        if any(c.isdigit() for c in cells[:2]):
            start_row = r_idx
            break
            
    for row in rows[start_row:]:
        cells = [clean(c.text_content()) for c in row.xpath('.//td|.//th')]
        if len(cells) >= 5:
            stt = cells[0]
            if cells[1] or cells[2]:
                outbound.append({
                    "order": int(stt) if stt.isdigit() else len(outbound) + 1,
                    "name": cells[1],
                    "street": cells[2]
                })
            if cells[3] or cells[4]:
                inbound.append({
                    "order": int(stt) if stt.isdigit() else len(inbound) + 1,
                    "name": cells[3],
                    "street": cells[4]
                })
        elif len(cells) >= 2 and any(cells):
            stt = cells[0] if cells[0].isdigit() else str(len(outbound) + 1)
            name = cells[1] if len(cells) > 1 else cells[0]
            street = cells[2] if len(cells) > 2 else ""
            outbound.append({
                "order": int(stt) if stt.isdigit() else len(outbound) + 1,
                "name": name,
                "street": street
            })
    return {"outbound": outbound, "inbound": inbound}

def parse_two_col_stops_table(table):
    stops = []
    rows = table.xpath('.//tr')
    for row in rows:
        cells = [clean(c.text_content()) for c in row.xpath('.//td|.//th')]
        if len(cells) >= 2 and (cells[0] or cells[1]):
            c0_lower = cells[0].lower()
            if any(h in c0_lower for h in ['chiều đi', 'chiều về', 'điểm dừng', 'tuyến lk', 'tên đường', 'stt']):
                continue
            stops.append({
                "order": len(stops) + 1,
                "name": cells[0],
                "street": cells[1]
            })
    return stops

def parse_schedule_table(table):
    rows = table.xpath('.//tr')
    if len(rows) < 2:
        return []
    headers = [clean(c.text_content()) for c in rows[0].xpath('.//td|.//th')]
    schedules = []
    for r in rows[1:]:
        cells = [clean(c.text_content()) for c in r.xpath('.//td|.//th')]
        if len(cells) >= 2 and cells[0].isdigit():
            trip_info = {"trip": int(cells[0])}
            stops_times = {}
            for h, c in zip(headers[1:], cells[1:]):
                if h and c:
                    stops_times[h] = c
            trip_info["timeline"] = stops_times
            if len(cells) > 1 and cells[1]:
                trip_info["departureTime"] = cells[1]
            schedules.append(trip_info)
    return schedules

def extract_streets_from_path(path_text):
    if not path_text:
        return []
    parts = re.split(r'\s*[-–—→>]\s*', path_text)
    streets = []
    for p in parts:
        p_clean = clean(p)
        p_base = re.sub(r'\(.*?\)', '', p_clean).strip()
        if p_base and len(p_base) > 2 and len(p_base) < 60:
            if p_base not in streets:
                streets.append(p_base)
    return streets

norm_md = re.sub(r'\xa0', ' ', full_md)
lines = norm_md.splitlines()

from setup_master_routes import route_definitions

# Custom overrides for routes with unique text format
route_overrides = {
    "03": {
        "operatingHours": {"start": "05:45", "end": "18:00", "raw": "32 lượt xe/ngày, hành trình 60 phút/chuyến"},
        "frequency": {"peakMinutes": 30, "offPeakMinutes": 45, "raw": "32 lượt/ngày (khoảng 30-45 phút/chuyến)"},
        "distanceKm": {"average": 25.0, "outbound": 25.0, "inbound": 25.0, "raw": "25 km"},
        "terminals": {"origin": "Trạm xe buýt Sân bay Đà Nẵng", "destination": "Bãi đỗ xe KDL Bà Nà Hills"}
    },
    "06": {
        "operatingHours": {"start": "05:30", "end": "19:25", "raw": "Mở bến: 05h30 (ĐH Việt Hàn) / 05h45 (Sân bay) - Đóng bến: 19h00 (ĐH Việt Hàn) / 19h25 (Sân bay)"},
        "frequency": {"peakMinutes": 30, "offPeakMinutes": 60, "raw": "30-60 phút/chuyến (48 lượt xe/ngày)"},
        "distanceKm": {"average": 21.3, "outbound": 21.3, "inbound": 21.3, "raw": "21,3 km"},
        "terminals": {"origin": "Trạm xe buýt Sân bay Đà Nẵng", "destination": "Trạm xe buýt Đại học Việt Hàn"}
    },
    "14": {
        "operatingHours": {"start": "05:45", "end": "18:00", "raw": "Mở tuyến: 05h45 - Đóng tuyến: 18h00 (Hành trình 60 phút/chuyến)"},
        "frequency": {"peakMinutes": 30, "offPeakMinutes": 45, "raw": "30-45 phút/chuyến"},
        "distanceKm": {"average": 26.5, "outbound": 26.5, "inbound": 26.5, "raw": "26,5 km"},
        "terminals": {"origin": "Cảng sông Hàn (đầu đường Như Nguyệt)", "destination": "Trạm xe buýt Khu Công nghệ cao"}
    },
    "TKY-CHU": {
        "operatingHours": {"start": "05:00", "end": "18:00", "raw": "Xuất bến trước giờ bay 130 phút, lượt về sau máy bay đến 20 phút"},
        "frequency": {"peakMinutes": 60, "offPeakMinutes": 90, "raw": "Theo lịch trình chuyến bay tại Sân bay Chu Lai"},
        "terminals": {"origin": "90 Phan Bội Châu (Tam Kỳ)", "destination": "Sân bay Chu Lai"}
    },
    "01DL": {
        "operatingHours": {"start": "08:00", "end": "17:30", "raw": "Mở tuyến: 08h00 - Đóng tuyến: 17h30"},
        "frequency": {"peakMinutes": 60, "offPeakMinutes": 120, "raw": "Theo các khung giờ tham quan du lịch"},
        "distanceKm": {"average": 105.0, "outbound": 105.0, "inbound": 105.0, "raw": "105 km"},
        "terminals": {"origin": "KĐT Nam Hội An City", "destination": "Bãi đỗ xe KDL Cổng Trời Đông Giang"}
    },
    "01SB": {
        "operatingHours": {"start": "06:00", "end": "22:00", "raw": "Từ 6h00 đến 22h00 theo lịch các chuyến bay"},
        "frequency": {"peakMinutes": 30, "offPeakMinutes": 60, "raw": "Theo lịch bay Cảng hàng không Quốc tế Đà Nẵng"},
        "distanceKm": {"average": 30.0, "outbound": 30.0, "inbound": 30.0, "raw": "30 km"},
        "terminals": {"origin": "Cảng HKQT Đà Nẵng (Bãi đỗ xe Ga T1)", "destination": "Bãi đỗ xe Bến tàu Cửa Đại (Hội An)"}
    },
    "LK02": {
        "operatingHours": {"start": "05:00", "end": "19:05", "raw": "Mở: 05h00 (Cửa Đại) / 06h05 (ĐH Việt Hàn) - Đóng: 18h00 (Cửa Đại) / 19h05 (ĐH Việt Hàn)"},
        "frequency": {"peakMinutes": 15, "offPeakMinutes": 30, "raw": "15-30 phút/chuyến (72 lượt xe/ngày)"},
        "distanceKm": {"average": 23.2, "outbound": 23.2, "inbound": 23.2, "raw": "23,2 km"},
        "terminals": {"origin": "Trạm xe buýt Đại học Việt Hàn (Đà Nẵng)", "destination": "Bãi đỗ xe Bến thủy nội địa Cửa Đại (Hội An)"}
    },
    "LK21": {
        "operatingHours": {"start": "04:45", "end": "18:15", "raw": "Mở: 04h45 (Tam Kỳ) / 05h30 (BX Phía Nam) - Đóng: 17h30 (Tam Kỳ) / 18h15 (BX Phía Nam)"},
        "frequency": {"peakMinutes": 15, "offPeakMinutes": 25, "raw": "15-25 phút/chuyến (64 lượt xe/ngày)"},
        "distanceKm": {"average": 56.5, "outbound": 56.5, "inbound": 56.5, "raw": "56,5 km"},
        "terminals": {"origin": "Bến xe phía Nam (Đà Nẵng)", "destination": "954 Phan Châu Trinh (Cầu Tam Kỳ)"}
    }
}

parsed_routes = []

for rdef in route_definitions:
    rid = rdef["id"]
    s_idx = rdef["line_start"]
    e_idx = rdef["line_end"]
    chunk_lines = lines[s_idx:e_idx]
    chunk_text = "\n".join(chunk_lines)

    # 1. Terminals
    start_terminal = ""
    end_terminal = ""
    term_m = re.search(r'Điểm đầu(?:\s*cuối|\s*-\s*cuối)?:\s*(?:-\s*Điểm đầu:\s*([^\n\r]+))?(?:.*?- Điểm cuối:\s*([^\n\r]+))?', chunk_text, re.DOTALL | re.IGNORECASE)
    if term_m:
        if term_m.group(1):
            start_terminal = clean(term_m.group(1))
        if term_m.group(2):
            end_terminal = clean(term_m.group(2))
    
    if not start_terminal:
        st_m = re.search(r'Điểm đầu:\s*([^\n\r;]+)', chunk_text, re.IGNORECASE)
        if st_m:
            start_terminal = clean(st_m.group(1))
    if not end_terminal:
        et_m = re.search(r'Điểm cuối:\s*([^\n\r;]+)', chunk_text, re.IGNORECASE)
        if et_m:
            end_terminal = clean(et_m.group(1))

    # 2. Operating Hours
    hours_raw = ""
    hours_start = ""
    hours_end = ""
    h_m = re.search(r'(?:Thời gian hoạt động|Thời gian mở tuyến|Thời gian hoạt động hàng ngày)[^:]*:\s*([^\n\r]+)', chunk_text, re.IGNORECASE)
    if h_m:
        hours_raw = clean(h_m.group(1))
        times = re.findall(r'(\d{1,2}[h:]\d{2})', hours_raw)
        if len(times) >= 2:
            hours_start = times[0].replace('h', ':')
            hours_end = times[1].replace('h', ':')
    
    # 3. Frequency
    freq_raw = ""
    freq_peak = None
    freq_offpeak = None
    freq_m = re.search(r'(?:Tần suất hoạt động|Tần suất chạy xe|Giãn cách chạy xe)[^:]*:\s*([^\n\r]+)', chunk_text, re.IGNORECASE)
    if freq_m:
        freq_raw = clean(freq_m.group(1))
    elif '(' in hours_raw and 'phút' in hours_raw:
        freq_m2 = re.search(r'\(([^)]+phút[^)]*)\)', hours_raw)
        if freq_m2:
            freq_raw = clean(freq_m2.group(1))
            
    if freq_raw:
        minutes = [int(x) for x in re.findall(r'(\d+)\s*phút', freq_raw)]
        if len(minutes) == 1:
            freq_peak = minutes[0]
            freq_offpeak = minutes[0]
        elif len(minutes) >= 2:
            freq_peak = min(minutes)
            freq_offpeak = max(minutes)

    # 4. Distance
    dist_avg = None
    dist_go = None
    dist_back = None
    dist_m = re.search(r'Cự ly[^:]*:\s*([^\n\r]+)', chunk_text, re.IGNORECASE)
    dist_raw = ""
    if dist_m:
        dist_raw = clean(dist_m.group(1))
        nums = [float(x.replace(',', '.')) for x in re.findall(r'(\d+(?:[.,]\d+)?)\s*km', dist_raw)]
        if len(nums) == 1:
            dist_avg = nums[0]
        elif len(nums) >= 3:
            dist_avg = nums[0]
            dist_go = nums[1]
            dist_back = nums[2]
        elif len(nums) == 2:
            dist_go = nums[0]
            dist_back = nums[1]
            dist_avg = round((nums[0] + nums[1]) / 2, 2)

    # 5. Paths (Chiều đi, Chiều về)
    path_go = ""
    path_back = ""
    go_m = re.search(r'(?:Chiều đi|\+ Chiều đi|Hành trình chạy xe:\s*Chiều đi):\s*([^\n\r]+(?:\n[^\n\r#1-9STT\+]+)?)', chunk_text, re.IGNORECASE)
    if go_m:
        path_go = clean(go_m.group(1))
    back_m = re.search(r'(?:Chiều về|\+ Chiều về):\s*([^\n\r]+(?:\n[^\n\r#1-9STT\+]+)?)', chunk_text, re.IGNORECASE)
    if back_m:
        path_back = clean(back_m.group(1))

    for stop_word in ['STT', 'Bảng điểm dừng', '4. Giá vé', '5. Cự ly', 'b) Cự ly', '2. Điểm đầu']:
        if stop_word in path_go:
            path_go = path_go.split(stop_word)[0].strip()
        if stop_word in path_back:
            path_back = path_back.split(stop_word)[0].strip()

    streets_go = extract_streets_from_path(path_go)
    streets_back = extract_streets_from_path(path_back)

    # 6. Fares
    single_fare = None
    if "8.000 đồng" in chunk_text:
        single_fare = 8000
    elif "80.000 đồng" in chunk_text and rid == "LK01":
        single_fare = 80000

    fares_obj = {
        "singleTicket": single_fare,
        "rawSummary": ""
    }
    fare_section_m = re.search(r'(?:Giá vé|4\.\s*Giá vé|d\)\s*Giá vé)[^:]*:(.*?)(?:e\)\s*Đơn vị|5\.\s*Chỉ tiêu|5\.\s*Các chỉ tiêu|6\.\s*Biểu đồ|Căn cứ|\Z)', chunk_text, re.DOTALL | re.IGNORECASE)
    if fare_section_m:
        fare_text = clean(fare_section_m.group(1))
        fares_obj["rawSummary"] = fare_text[:350]
        m_pri = re.search(r'ưu tiên[^:]*:\s*([\d.]+)\s*đồng', fare_text, re.IGNORECASE)
        m_reg = re.search(r'không ưu tiên[^:]*:\s*([\d.]+)\s*đồng', fare_text, re.IGNORECASE)
        if m_pri:
            try: fares_obj["monthlyPriority"] = int(m_pri.group(1).replace('.', ''))
            except: pass
        if m_reg:
            try: fares_obj["monthlyRegular"] = int(m_reg.group(1).replace('.', ''))
            except: pass

    # 7. Stops table
    stops_data = {"outbound": [], "inbound": []}
    if "stops_table" in rdef:
        st_cfg = rdef["stops_table"]
        if st_cfg["type"] == "four_col":
            stops_data = parse_four_col_stops_table(tables[st_cfg["index"]])
        elif st_cfg["type"] == "two_col_pair":
            stops_data = {
                "outbound": parse_two_col_stops_table(tables[st_cfg["outbound_index"]]),
                "inbound": parse_two_col_stops_table(tables[st_cfg["inbound_index"]])
            }
        elif st_cfg["type"] == "two_col_single":
            stops_data = {
                "outbound": parse_two_col_stops_table(tables[st_cfg["index"]]),
                "inbound": []
            }

    # 8. Schedules / Timetable
    schedule_data = {}
    if "schedule_table" in rdef:
        sc_cfg = rdef["schedule_table"]
        if "outbound_index" in sc_cfg:
            schedule_data["outbound"] = parse_schedule_table(tables[sc_cfg["outbound_index"]])
        if "inbound_index" in sc_cfg:
            schedule_data["inbound"] = parse_schedule_table(tables[sc_cfg["inbound_index"]])

    # 9. Vehicle & Fleet Info
    vehicle_info = ""
    v_m = re.search(r'(?:Nhãn hiệu, sức chứa và số xe|Số lượng phương tiện)[^:]*:\s*([^\n\r]+(?:\n[^\n\r]+)?)', chunk_text, re.IGNORECASE)
    if v_m:
        vehicle_info = clean(v_m.group(1))

    # Apply overrides if available
    if rid in route_overrides:
        ovr = route_overrides[rid]
        if "operatingHours" in ovr:
            hours_start = ovr["operatingHours"]["start"]
            hours_end = ovr["operatingHours"]["end"]
            hours_raw = ovr["operatingHours"]["raw"]
        if "frequency" in ovr:
            freq_peak = ovr["frequency"]["peakMinutes"]
            freq_offpeak = ovr["frequency"]["offPeakMinutes"]
            freq_raw = ovr["frequency"]["raw"]
        if "distanceKm" in ovr:
            dist_avg = ovr["distanceKm"]["average"]
            dist_go = ovr["distanceKm"]["outbound"]
            dist_back = ovr["distanceKm"]["inbound"]
            dist_raw = ovr["distanceKm"]["raw"]
        if "terminals" in ovr:
            start_terminal = ovr["terminals"]["origin"]
            end_terminal = ovr["terminals"]["destination"]

    # Assemble route object
    route_obj = {
        "id": rdef["id"],
        "routeNumber": rdef["routeNumber"],
        "name": rdef["name"],
        "shortName": rdef.get("shortName", rdef["name"]),
        "formerName": rdef.get("formerName"),
        "aliases": rdef.get("aliases", []),
        "category": rdef["category"],
        "status": rdef["status"],
        "statusNote": rdef.get("statusNote"),
        "operator": rdef.get("operator", ""),
        "terminals": {
            "origin": start_terminal,
            "destination": end_terminal
        },
        "operatingHours": {
            "start": hours_start,
            "end": hours_end,
            "raw": hours_raw
        },
        "frequency": {
            "peakMinutes": freq_peak,
            "offPeakMinutes": freq_offpeak,
            "raw": freq_raw
        },
        "distanceKm": {
            "average": dist_avg,
            "outbound": dist_go,
            "inbound": dist_back,
            "raw": dist_raw
        },
        "fares": fares_obj,
        "routePaths": {
            "outbound": {
                "text": path_go,
                "streets": streets_go
            },
            "inbound": {
                "text": path_back,
                "streets": streets_back
            }
        },
        "stops": stops_data,
        "timetable": schedule_data,
        "vehicleInfo": vehicle_info,
        "pdfUrls": rdef.get("pdf_urls", [])
    }

    parsed_routes.append(route_obj)

# 1. Save master JSON
with open('data/danangbus_routes.json', 'w', encoding='utf-8') as f:
    json.dump(parsed_routes, f, ensure_ascii=False, indent=2)

# 2. Build Compact Version for PWA quick offline cache
compact_routes = []
for r in parsed_routes:
    compact_routes.append({
        "id": r["id"],
        "routeNumber": r["routeNumber"],
        "name": r["name"],
        "shortName": r["shortName"],
        "category": r["category"],
        "status": r["status"],
        "operator": r["operator"],
        "terminals": r["terminals"],
        "operatingHours": r["operatingHours"],
        "frequency": r["frequency"],
        "distanceKm": r["distanceKm"]["average"],
        "singleFare": r["fares"].get("singleTicket"),
        "totalStops": {
            "outbound": len(r["stops"].get("outbound", [])),
            "inbound": len(r["stops"].get("inbound", []))
        },
        "streets": list(set(r["routePaths"]["outbound"]["streets"] + r["routePaths"]["inbound"]["streets"])),
        "pdfUrls": r.get("pdfUrls", [])
    })

with open('data/danangbus_routes_compact.json', 'w', encoding='utf-8') as f:
    json.dump(compact_routes, f, ensure_ascii=False, indent=2)

# 3. Build Normalized Stops Directory
stops_dict = {}
for r in parsed_routes:
    for direction in ["outbound", "inbound"]:
        for s in r["stops"].get(direction, []):
            s_name = s.get("name", "").strip()
            s_street = s.get("street", "").strip()
            if not s_name:
                continue
            key = f"{s_name} | {s_street}" if s_street else s_name
            if key not in stops_dict:
                stops_dict[key] = {
                    "id": f"stop_{len(stops_dict) + 1:04d}",
                    "name": s_name,
                    "street": s_street,
                    "routes": []
                }
            route_entry = {
                "routeId": r["id"],
                "routeNumber": r["routeNumber"],
                "direction": direction,
                "stopOrder": s.get("order")
            }
            if route_entry not in stops_dict[key]["routes"]:
                stops_dict[key]["routes"].append(route_entry)

all_stops_list = list(stops_dict.values())
with open('data/danangbus_stops.json', 'w', encoding='utf-8') as f:
    json.dump(all_stops_list, f, ensure_ascii=False, indent=2)

# 4. Build Street-to-Routes Index
streets_index = {}
for r in parsed_routes:
    all_streets = set(r["routePaths"]["outbound"]["streets"] + r["routePaths"]["inbound"]["streets"])
    for direction in ["outbound", "inbound"]:
        for s in r["stops"].get(direction, []):
            st = s.get("street", "").strip()
            if st and len(st) > 2:
                all_streets.add(st)
                
    for street in all_streets:
        street_clean = clean(street)
        if not street_clean or len(street_clean) < 3:
            continue
        if street_clean not in streets_index:
            streets_index[street_clean] = []
        if r["routeNumber"] not in streets_index[street_clean]:
            streets_index[street_clean].append(r["routeNumber"])

with open('data/danangbus_streets.json', 'w', encoding='utf-8') as f:
    json.dump(streets_index, f, ensure_ascii=False, indent=2)

# 5. Build Summary
categories_count = {}
for r in parsed_routes:
    cat = r["category"]
    categories_count[cat] = categories_count.get(cat, 0) + 1

summary = {
    "totalRoutes": len(parsed_routes),
    "activeRoutes": sum(1 for r in parsed_routes if r["status"] == "active"),
    "suspendedRoutes": sum(1 for r in parsed_routes if r["status"] == "suspended"),
    "categories": categories_count,
    "totalUniqueStops": len(all_stops_list),
    "totalIndexedStreets": len(streets_index),
    "sourceUrl": "https://www.danangbus.vn/lo-trinh-tuyen.html",
    "updatedAt": "2026-09-22"
}

with open('data/danangbus_summary.json', 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print("Finished generating all datasets cleanly!")
