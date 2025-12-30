import requests
from google.transit import gtfs_realtime_pb2
from datetime import datetime
from zoneinfo import ZoneInfo

METRA_API_TOKEN = "179|QnjVySibzcRfjluBXNlA4hVSbetoMhb2KqkqKgOlb6909b61"  # the full thing with the |

url = f"https://gtfspublic.metrarr.com/gtfs/public/tripupdates?api_token={METRA_API_TOKEN}"

response = requests.get(url)

feed = gtfs_realtime_pb2.FeedMessage()
feed.ParseFromString(response.content)

chicago = ZoneInfo("America/Chicago")
now = datetime.now(chicago)

print(f"\n🚆 Metra Electric\n")

arrivals = []

for entity in feed.entity:
    if entity.HasField("trip_update"):
        trip = entity.trip_update
        route_id = trip.trip.route_id
        
        if route_id != "ME":
            continue
        
        for stop_update in trip.stop_time_update:
            if stop_update.stop_id == "MILLENNIUM":
                # Use departure time if available, otherwise arrival
                if stop_update.departure.time:
                    time_stamp = stop_update.departure.time
                elif stop_update.arrival.time:
                    time_stamp = stop_update.arrival.time
                else:
                    continue
                
                departure_dt = datetime.fromtimestamp(time_stamp, tz=chicago)
                minutes_away = round((departure_dt - now).total_seconds() / 60)
                
                if minutes_away < 0:
                    continue
                
                arrivals.append({
                    "trip": trip.trip.trip_id,
                    "minutes": minutes_away
                })

# Sort by time and show next few trains
arrivals = sorted(arrivals, key=lambda x: x["minutes"])[:5]

for train in arrivals:
    if train["minutes"] < 1:
        time_str = "Due"
    else:
        time_str = f"{train['minutes']} min"
    
    print(f"Train {train['trip']}: {time_str}")