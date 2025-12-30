import requests
from datetime import datetime
from zoneinfo import ZoneInfo

API_KEY = "a256063ea7434f7db551e2b70ea42893"  # paste your key back in

STATIONS = {
    "40380": "Clark/Lake",
    "41700": "Washington/Wabash",
    "41660": "Lake"
}

MAX_RESULTS = 20  # max per API call (we'll filter further by line)

chicago = ZoneInfo("America/Chicago")
now = datetime.now(chicago)

all_arrivals = []

for station_id, station_name in STATIONS.items():
    url = f"https://lapi.transitchicago.com/api/1.0/ttarrivals.aspx?key={API_KEY}&mapid={station_id}&max={MAX_RESULTS}&outputType=JSON"
    
    response = requests.get(url)
    data = response.json()
    
    if "eta" in data["ctatt"]:
        for train in data["ctatt"]["eta"]:
            arrival_time = datetime.strptime(train["arrT"], "%Y-%m-%dT%H:%M:%S")
            arrival_time = arrival_time.replace(tzinfo=chicago)
            minutes_away = round((arrival_time - now).total_seconds() / 60)
            
            all_arrivals.append({
                "station": station_name,
                "route": train["rt"],
                "destination": train["destNm"],
                "minutes": minutes_away
            })

# Group by line and only keep the next 3 trains per line
lines = {}
for arrival in all_arrivals:
    route = arrival["route"]
    if route not in lines:
        lines[route] = []
    lines[route].append(arrival)

# Sort each line by time and keep only first 3
for route in lines:
    lines[route] = sorted(lines[route], key=lambda x: x["minutes"])[:3]

# Print results
print(f"\n🚇 CTA Departures\n")

for route in sorted(lines.keys()):
    print(f"{route} Line:")
    for train in lines[route]:
        if train["minutes"] < 1:
            time_str = "Due"
        else:
            time_str = f"{train['minutes']} min"
        print(f"  {train['destination']} ({train['station']}): {time_str}")
    print()