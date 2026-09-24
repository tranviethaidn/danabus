import sys
import os
import re
import json
from lxml import html

sys.stdout.reconfigure(encoding='utf-8')

# Ensure output directory exists
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

# Helpers for tables
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
        elif len(cells) == 3:
            stt = cells[0]
            outbound.append({
                "order": int(stt) if stt.isdigit() else len(outbound) + 1,
                "name": cells[1],
                "street": cells[2]
            })
    return {"outbound": outbound, "inbound": inbound}

def parse_two_col_stops_table(table):
    stops = []
    rows = table.xpath('.//tr')
    for row in rows:
        cells = [clean(c.text_content()) for c in row.xpath('.//td|.//th')]
        if len(cells) >= 2 and (cells[0] or cells[1]):
            # Skip if it is header
            c0_lower = cells[0].lower()
            if any(h in c0_lower for h in ['chiều đi', 'chiều về', 'điểm dừng', 'tuyến lk', 'tên đường']):
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

# Parse street sequence from path text
def extract_streets_from_path(path_text):
    if not path_text:
        return []
    # Split by hyphen or en-dash or arrow
    parts = re.split(r'\s*[-–—→>]\s*', path_text)
    streets = []
    for p in parts:
        p_clean = clean(p)
        # Remove parenthetical details for cleaner street names
        p_base = re.sub(r'\(.*?\)', '', p_clean).strip()
        # Remove prefixes like "đường", "cầu", "ngã ba", "trạm xe buýt", etc.
        if p_base and len(p_base) > 2 and len(p_base) < 60:
            if p_base not in streets:
                streets.append(p_base)
    return streets

norm_md = re.sub(r'\xa0', ' ', full_md)
md_lines = norm_md.splitlines()

# Master Route Configuration
route_definitions = [
    {
        "id": "05",
        "routeNumber": "05",
        "name": "Khu Chung cư Hòa Hiệp Nam – Công viên Biển Đông",
        "shortName": "Hòa Hiệp Nam – CV Biển Đông",
        "category": "subsidized",
        "status": "active",
        "operator": "Công ty Cổ phần Xe khách Phương Trang (FUTA Bus Lines)",
        "line_start": 386,
        "line_end": 611,
        "stops_table": {"type": "four_col", "index": 0},
        "pdf_urls": ["https://www.danangbus.vn/UploadImages/files/x%C6%B0%C6%A1ng%20c%C3%A1%2005.pdf"]
    },
    {
        "id": "07",
        "routeNumber": "07",
        "name": "Xuân Diệu – Hoà Phước",
        "shortName": "Xuân Diệu – Hoà Phước",
        "formerName": "Xuân Diệu - Bến xe phía Nam",
        "category": "subsidized",
        "status": "active",
        "operator": "Công ty Cổ phần Xe khách Phương Trang (FUTA Bus Lines)",
        "line_start": 611,
        "line_end": 646,
        "pdf_urls": ["https://www.danangbus.vn/UploadImages/files/x%C6%B0%C6%A1ng%20c%C3%A1%2007.pdf"]
    },
    {
        "id": "08",
        "routeNumber": "08",
        "name": "Vũng Thùng – Bến xe buýt Phạm Hùng",
        "shortName": "Vũng Thùng – BX Phạm Hùng",
        "formerName": "Thọ Quang – Phạm Hùng",
        "category": "subsidized",
        "status": "active",
        "operator": "Công ty Cổ phần Xe khách Phương Trang (FUTA Bus Lines)",
        "line_start": 646,
        "line_end": 681,
        "pdf_urls": ["https://www.danangbus.vn/UploadImages/files/x%C6%B0%C6%A1ng%20c%C3%A1%2008.pdf"]
    },
    {
        "id": "11",
        "routeNumber": "11",
        "name": "Xuân Diệu – Bệnh viện Phụ sản Nhi",
        "shortName": "Xuân Diệu – BV Phụ sản Nhi",
        "formerName": "Xuân Diệu – Siêu thị Lotte – Đại học Việt Hàn",
        "category": "subsidized",
        "status": "active",
        "operator": "Công ty Cổ phần Xe khách Phương Trang (FUTA Bus Lines)",
        "line_start": 681,
        "line_end": 716,
        "pdf_urls": ["https://www.danangbus.vn/UploadImages/files/x%C6%B0%C6%A1ng%20c%C3%A1%2011.pdf"]
    },
    {
        "id": "12",
        "routeNumber": "12",
        "name": "Xuân Diệu – Bến xe buýt Phạm Hùng",
        "shortName": "Xuân Diệu – BX Phạm Hùng",
        "formerName": "Công viên 29/3 - Vũng Thùng (BX Bùi Dương Lịch)",
        "category": "subsidized",
        "status": "active",
        "operator": "Công ty Cổ phần Xe khách Phương Trang (FUTA Bus Lines)",
        "line_start": 716,
        "line_end": 744,
        "pdf_urls": ["https://www.danangbus.vn/UploadImages/files/x%C6%B0%C6%A1ng%20c%C3%A1%2012.pdf"]
    },
    {
        "id": "02",
        "routeNumber": "02",
        "name": "Bến xe Trung tâm – Trung tâm hành chính thành phố Đà Nẵng - Cửa Đại",
        "shortName": "BX Trung tâm – TTHC TP – Cửa Đại",
        "category": "non_subsidized",
        "status": "active",
        "operator": "Công ty Cổ phần Xe khách Phương Trang (FUTA Bus Lines)",
        "line_start": 744,
        "line_end": 983,
        "stops_table": {"type": "two_col_pair", "outbound_index": 1, "inbound_index": 2}
    },
    {
        "id": "03",
        "routeNumber": "03",
        "name": "Sân bay Đà Nẵng – Khu du lịch Bà Nà Hills",
        "shortName": "Sân bay Đà Nẵng – Bà Nà Hills",
        "category": "non_subsidized",
        "status": "active",
        "operator": "Công ty Cổ phần Xe khách Phương Trang (FUTA Bus Lines)",
        "line_start": 983,
        "line_end": 1026
    },
    {
        "id": "06",
        "routeNumber": "06",
        "name": "Sân bay Đà Nẵng – Đại học Việt Hàn",
        "shortName": "Sân bay Đà Nẵng – ĐH Việt Hàn",
        "category": "non_subsidized",
        "status": "active",
        "operator": "Công ty Cổ phần Xe khách Phương Trang (FUTA Bus Lines)",
        "line_start": 1026,
        "line_end": 1077
    },
    {
        "id": "09",
        "routeNumber": "09",
        "aliases": ["17", "R17A"],
        "name": "Cảng Sông Hàn – Hòa Khương",
        "shortName": "Cảng Sông Hàn – Hòa Khương",
        "formerName": "Bệnh Viện Ung Bướu - Phạm Hùng (số hiệu cũ: 17 / R17A)",
        "category": "non_subsidized",
        "status": "active",
        "operator": "Công ty Cổ phần Xe khách Phương Trang (FUTA Bus Lines)",
        "line_start": 1077,
        "line_end": 1111,
        "pdf_urls": ["https://www.danangbus.vn/UploadImages/files/x%C6%B0%C6%A1ng%20c%C3%A1%2017%281%29.pdf"]
    },
    {
        "id": "13",
        "routeNumber": "13",
        "aliases": ["16", "R16"],
        "name": "Kim Liên – Đại học Việt Hàn",
        "shortName": "Kim Liên – ĐH Việt Hàn",
        "formerName": "Bệnh Viện Ung Bướu – Đại Học Việt Hàn (số hiệu cũ: 16 / R16)",
        "category": "non_subsidized",
        "status": "active",
        "operator": "Công ty Cổ phần Xe khách Phương Trang (FUTA Bus Lines)",
        "line_start": 1111,
        "line_end": 1144,
        "pdf_urls": ["https://www.danangbus.vn/UploadImages/files/x%C6%B0%C6%A1ng%20c%C3%A1%2016%281%29.pdf"]
    },
    {
        "id": "14",
        "routeNumber": "14",
        "name": "Cảng sông Hàn – Khu công nghệ cao",
        "shortName": "Cảng Sông Hàn – Khu CNC",
        "category": "non_subsidized",
        "status": "active",
        "operator": "Công ty Cổ phần Xe khách Phương Trang (FUTA Bus Lines)",
        "line_start": 1144,
        "line_end": 1194
    },
    {
        "id": "21",
        "routeNumber": "21",
        "name": "Bến xe Trung tâm – Trung tâm hành chính thành phố Đà Nẵng – Cầu Tam Kỳ",
        "shortName": "BX Trung tâm – TTHC TP – Cầu Tam Kỳ",
        "category": "non_subsidized",
        "status": "active",
        "operator": "Công ty Cổ phần Xe khách Phương Trang (FUTA Bus Lines)",
        "line_start": 1194,
        "line_end": 1589,
        "stops_table": {"type": "two_col_pair", "outbound_index": 8, "inbound_index": 9}
    },
    {
        "id": "TKY-TMY",
        "routeNumber": "02 (Quảng Nam)",
        "name": "Tam Kỳ – Trà My",
        "shortName": "Tam Kỳ – Trà My",
        "category": "non_subsidized",
        "status": "active",
        "operator": "Công ty TNHH Hợp Nhất Quảng Nam",
        "line_start": 1589,
        "line_end": 2002,
        "stops_table": {"type": "four_col", "index": 10},
        "schedule_table": {"outbound_index": 12, "inbound_index": 13}
    },
    {
        "id": "TKY-NTH",
        "routeNumber": "05 (Quảng Nam)",
        "name": "Tam Kỳ – Núi Thành (Cảng Kỳ Hà)",
        "shortName": "Tam Kỳ – Núi Thành",
        "category": "non_subsidized",
        "status": "active",
        "operator": "Công ty TNHH MTV Mai Linh Hội An",
        "line_start": 2002,
        "line_end": 2330,
        "stops_table": {"type": "four_col", "index": 14},
        "schedule_table": {"outbound_index": 16, "inbound_index": 17}
    },
    {
        "id": "TKY-CHU",
        "routeNumber": "12 (Quảng Nam)",
        "name": "Tam Kỳ – Sân bay Chu Lai",
        "shortName": "Tam Kỳ – SB Chu Lai",
        "category": "non_subsidized",
        "status": "active",
        "operator": "Công ty TNHH MTV Mai Linh Hội An",
        "line_start": 2330,
        "line_end": 2480,
        "stops_table": {"type": "four_col", "index": 18}
    },
    {
        "id": "LK01",
        "routeNumber": "LK01",
        "name": "Đà Nẵng – Huế",
        "shortName": "Đà Nẵng – Huế",
        "category": "interprovincial",
        "status": "active",
        "operator": "Liên danh các đơn vị vận tải (Hải Vân, Vitraco, HTX)",
        "line_start": 357,
        "line_end": 386
    },
    {
        "id": "01DL",
        "routeNumber": "01DL",
        "name": "Tuyến buýt du lịch: Hội An – Mỹ Sơn – Cổng trời Đông Giang",
        "shortName": "Hội An – Mỹ Sơn – Cổng Trời",
        "category": "tourist",
        "status": "active",
        "operator": "Công ty CP Du lịch FVG Travel",
        "line_start": 2683,
        "line_end": 2772,
        "stops_table": {"type": "four_col", "index": 19},
        "schedule_table": {"outbound_index": 20}
    },
    {
        "id": "01SB",
        "routeNumber": "01SB",
        "name": "Tuyến xe buýt Sân bay Đà Nẵng – Hội An",
        "shortName": "Sân bay Đà Nẵng – Hội An",
        "category": "tourist",
        "status": "active",
        "operator": "Công ty TNHH Vận tải & Du lịch Hải Vân",
        "line_start": 2772,
        "line_end": 2836,
        "stops_table": {"type": "four_col", "index": 21}
    },
    {
        "id": "LK02",
        "routeNumber": "LK02",
        "name": "Đà Nẵng (Đại học Việt Hàn) – Hội An (Cửa Đại)",
        "shortName": "ĐH Việt Hàn – Hội An (Cửa Đại)",
        "category": "interprovincial",
        "status": "active",
        "operator": "Công ty Cổ phần Xe khách Phương Trang (FUTA Bus Lines)",
        "line_start": 2836,
        "line_end": 2883,
        "stops_table": {"type": "two_col_single", "index": 22}
    },
    {
        "id": "LK21",
        "routeNumber": "LK21",
        "name": "Đà Nẵng (Bến xe phía Nam) – Tam Kỳ",
        "shortName": "BX Phía Nam – Tam Kỳ",
        "category": "interprovincial",
        "status": "active",
        "operator": "Công ty Cổ phần Xe khách Phương Trang (FUTA Bus Lines)",
        "line_start": 2883,
        "line_end": 2935,
        "stops_table": {"type": "two_col_single", "index": 23}
    },
    {
        "id": "04",
        "routeNumber": "04",
        "aliases": ["R4A"],
        "name": "Cầu Trần Thị Lý – Hoà Tiến",
        "shortName": "Trần Thị Lý – Hoà Tiến",
        "formerName": "R4A",
        "category": "suspended",
        "status": "suspended",
        "statusNote": "Tạm dừng hoạt động",
        "operator": "Công ty Cổ phần Công nghiệp Quảng An 1",
        "line_start": 2515,
        "line_end": 2545,
        "pdf_urls": ["https://www.danangbus.vn/UploadImages/files/x%C6%B0%C6%A1ng%20c%C3%A1%2004%281%29.pdf"]
    },
    {
        "id": "10",
        "routeNumber": "10",
        "name": "Sân bay Đà Nẵng – Thọ Quang",
        "shortName": "Sân bay Đà Nẵng – Thọ Quang",
        "category": "suspended",
        "status": "suspended",
        "statusNote": "Tạm dừng hoạt động",
        "operator": "Công ty Cổ phần Công nghiệp Quảng An 1",
        "line_start": 2545,
        "line_end": 2573,
        "pdf_urls": ["https://www.danangbus.vn/UploadImages/files/x%C6%B0%C6%A1ng%20c%C3%A1%2010%281%29.pdf"]
    },
    {
        "id": "15",
        "routeNumber": "R15",
        "aliases": ["15"],
        "name": "Bến xe Trung tâm – Bến xe Phía Nam",
        "shortName": "BX Trung tâm – BX Phía Nam",
        "category": "suspended",
        "status": "suspended",
        "statusNote": "Tạm dừng hoạt động",
        "operator": "Công ty Cổ phần Công nghiệp Quảng An 1",
        "line_start": 2573,
        "line_end": 2600,
        "pdf_urls": ["https://www.danangbus.vn/UploadImages/files/x%C6%B0%C6%A1ng%20c%C3%A1%2015%281%29.pdf"]
    }
]

print(f"Configured {len(route_definitions)} route definitions.")
