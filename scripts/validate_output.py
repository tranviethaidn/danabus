import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

with open('data/danangbus_routes.json', 'r', encoding='utf-8') as f:
    routes = json.load(f)

print(f"Total routes in json: {len(routes)}")
for r in routes:
    h = r['operatingHours']
    stops = r['stops']
    term = r['terminals']
    paths = r['routePaths']
    print(f"[{r['id']:7s}] {r['routeNumber']:15s} | {r['shortName']:30s} | {r['category']:15s} | Hours: {h.get('start','')}-{h.get('end','')} | Stops: {len(stops.get('outbound',[]))}/{len(stops.get('inbound',[]))} | Streets: {len(paths['outbound']['streets'])}/{len(paths['inbound']['streets'])}")
