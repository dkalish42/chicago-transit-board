import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from google.transit import gtfs_realtime_pb2

# === CONFIG ===
CTA_API_KEY = "a256063ea7434f7db551e2b70ea42893"
METRA_API_TOKEN = "179|QnjVySibzcRfjluBXNlA4hVSbetoMhb2KqkqKgOlb6909b61"

CTA_STATIONS = {
    "40380": "Clark/Lake",
    "41700": "Washington/Wabash",
    "41660": "Lake"
}

chicago = ZoneInfo("America/Chicago")

# === CTA ===
print("\n🚇 CTA Departures\n")

cta_arrivals = []
now = datetime.now(chicago)  # refresh time right before CTA calls

for station_id, station_name in CTA_STATIONS.items():
    url = f"https://lapi.transitchicago.com/api/1.0/ttarrivals.aspx?key={CTA_API_KEY}&mapid={station_id}&max=20&outputType=JSON"
    response = requests.get(url)
    data = response.json()
    
    if "eta" in data["ctatt"]:
        for train in data["ctatt"]["eta"]:
            arrival_time = datetime.strptime(train["arrT"], "%Y-%m-%dT%H:%M:%S")
            arrival_time = arrival_time.replace(tzinfo=chicago)
            minutes_away = round((arrival_time - now).total_seconds() / 60)
            
            if minutes_away >= 0:  # only include trains that haven't left
                cta_arrivals.append({
                    "station": station_name,
                    "route": train["rt"],
                    "destination": train["destNm"],
                    "minutes": minutes_away
                })

# Group by line, keep next 3 per line
cta_lines = {}
for arrival in cta_arrivals:
    route = arrival["route"]
    if route not in cta_lines:
        cta_lines[route] = []
    cta_lines[route].append(arrival)

for route in cta_lines:
    cta_lines[route] = sorted(cta_lines[route], key=lambda x: x["minutes"])[:3]

if not cta_lines:
    print("  No CTA data available\n")
else:
    for route in sorted(cta_lines.keys()):
        print(f"{route} Line:")
        for train in cta_lines[route]:
            time_str = "Due" if train["minutes"] < 1 else f"{train['minutes']} min"
            print(f"  {train['destination']} ({train['station']}): {time_str}")
        print()

# === METRA ===
print("🚆 Metra Electric\n")

now = datetime.now(chicago)  # refresh time right before Metra calls

metra_url = f"https://gtfspublic.metrarr.com/gtfs/public/tripupdates?api_token={METRA_API_TOKEN}"
response = requests.get(metra_url)

feed = gtfs_realtime_pb2.FeedMessage()
feed.ParseFromString(response.content)

metra_arrivals = []

for entity in feed.entity:
    if entity.HasField("trip_update"):
        trip = entity.trip_update
        
        if trip.trip.route_id != "ME":
            continue
        
        for stop_update in trip.stop_time_update:
            if stop_update.stop_id == "MILLENNIUM":
                time_stamp = stop_update.departure.time or stop_update.arrival.time
                if not time_stamp:
                    continue
                
                departure_dt = datetime.fromtimestamp(time_stamp, tz=chicago)
                minutes_away = round((departure_dt - now).total_seconds() / 60)
                
                if minutes_away < 0:
                    continue
                
                # Extract train number from trip ID (e.g., "ME_ME320_V3_B" -> "320")
                train_num = trip.trip.trip_id.split("_")[1].replace("ME", "")
                
                metra_arrivals.append({
                    "train": train_num,
                    "minutes": minutes_away
                })

metra_arrivals = sorted(metra_arrivals, key=lambda x: x["minutes"])[:5]

if not metra_arrivals:
    print("  No Metra data available\n")
else:
    for train in metra_arrivals:
        time_str = "Due" if train["minutes"] < 1 else f"{train['minutes']} min"
        print(f"  Train {train['train']}: {time_str}")
    print()