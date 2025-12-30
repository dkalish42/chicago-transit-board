from flask import Flask, render_template
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from google.transit import gtfs_realtime_pb2
from dotenv import load_dotenv
import os

load_dotenv()

CTA_API_KEY = os.getenv("CTA_API_KEY")
METRA_API_TOKEN = os.getenv("METRA_API_TOKEN")

CTA_STATIONS = {
    "40380": "Clark/Lake",
    "41700": "Washington/Wabash",
    "41660": "Lake"
}

app = Flask(__name__)

def get_cta_arrivals():
    chicago = ZoneInfo("America/Chicago")
    now = datetime.now(chicago)
    cta_arrivals = []
    
    for station_id, station_name in CTA_STATIONS.items():
        url = f"https://lapi.transitchicago.com/api/1.0/ttarrivals.aspx?key={CTA_API_KEY}&mapid={station_id}&max=20&outputType=JSON"
        response = requests.get(url)
        data = response.json()
        
        if "eta" in data["ctatt"]:
            for train in data["ctatt"]["eta"]:
                arrival_time = datetime.strptime(train["arrT"], "%Y-%m-%dT%H:%M:%S")
                arrival_time = arrival_time.replace(tzinfo=chicago)
                minutes_away = round((arrival_time - now).total_seconds() / 60)
                
                if minutes_away >= 0:
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
    
    return cta_lines

def get_metra_arrivals():
    chicago = ZoneInfo("America/Chicago")
    now = datetime.now(chicago)
    
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
                    
                    train_num = trip.trip.trip_id.split("_")[1].replace("ME", "")
                    
                    metra_arrivals.append({
                        "train": train_num,
                        "minutes": minutes_away
                    })
    
    return sorted(metra_arrivals, key=lambda x: x["minutes"])[:5]

@app.route("/")
def home():
    cta = get_cta_arrivals()
    metra = get_metra_arrivals()
    return render_template("index.html", cta=cta, metra=metra)

if __name__ == "__main__":
    app.run(debug=True)