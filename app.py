from flask import Flask, render_template
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from google.transit import gtfs_realtime_pb2
from dotenv import load_dotenv
import os

load_dotenv()

CTA_API_KEY = os.getenv("CTA_API_KEY")
CTA_BUS_API_KEY = os.getenv("CTA_BUS_API_KEY")
METRA_API_TOKEN = os.getenv("METRA_API_TOKEN")
METEOSOURCE_API_KEY = os.getenv("METEOSOURCE_API_KEY")

BUS_STOPS = {
    "1423": {"name": "State & Lake", "routes": ["2"]}
}

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

def get_bus_arrivals():
    bus_arrivals = []

    for stop_id, stop_info in BUS_STOPS.items():
        url = f"https://www.ctabustracker.com/bustime/api/v2/getpredictions?key={CTA_BUS_API_KEY}&stpid={stop_id}&format=json"
        response = requests.get(url)
        data = response.json()

        if "prd" in data.get("bustime-response", {}):
            for bus in data["bustime-response"]["prd"]:
                if bus["rt"] in stop_info["routes"]:
                    minutes = bus["prdctdn"]
                    if minutes == "DUE":
                        minutes = 0
                    elif minutes == "DLY":
                        continue
                    else:
                        minutes = int(minutes)

                    bus_arrivals.append({
                        "route": bus["rt"],
                        "destination": bus["des"],
                        "stop": stop_info["name"],
                        "minutes": minutes
                    })

    return sorted(bus_arrivals, key=lambda x: x["minutes"])[:5]

weather_cache = {"temp": None, "last_updated": None}

def get_weather():
    chicago = ZoneInfo("America/Chicago")
    now = datetime.now(chicago)

    # Only refresh every 10 minutes (max ~144 calls/day, well under 400 limit)
    if weather_cache["last_updated"]:
        elapsed = (now - weather_cache["last_updated"]).total_seconds()
        if elapsed < 600 and weather_cache["temp"] is not None:
            return weather_cache["temp"]

    try:
        url = f"https://www.meteosource.com/api/v1/free/point?place_id=chicago&sections=current&key={METEOSOURCE_API_KEY}"
        response = requests.get(url)
        data = response.json()
        temp = round(data["current"]["temperature"])
        weather_cache["temp"] = temp
        weather_cache["last_updated"] = now
        return temp
    except:
        return weather_cache["temp"]

@app.route("/")
def home():
    cta = get_cta_arrivals()
    metra = get_metra_arrivals()
    bus = get_bus_arrivals()
    return render_template("index.html", cta=cta, metra=metra, bus=bus)

FONT_3X5 = {
    '0': ["111", "101", "101", "101", "111"],
    '1': ["010", "110", "010", "010", "111"],
    '2': ["111", "001", "111", "100", "111"],
    '3': ["111", "001", "111", "001", "111"],
    '4': ["101", "101", "111", "001", "001"],
    '5': ["111", "100", "111", "001", "111"],
    '6': ["111", "100", "111", "101", "111"],
    '7': ["111", "001", "001", "001", "001"],
    '8': ["111", "101", "111", "101", "111"],
    '9': ["111", "101", "111", "001", "111"],
    'A': ["010", "101", "111", "101", "101"],
    'D': ["110", "101", "101", "101", "110"],
    'E': ["111", "100", "111", "100", "111"],
    'F': ["111", "100", "111", "100", "100"],
    'H': ["101", "101", "111", "101", "101"],
    'I': ["111", "010", "010", "010", "111"],
    'M': ["10001", "11011", "10101", "10001", "10001"],
    'N': ["10001", "11001", "10101", "10011", "10001"],
    'O': ["010", "101", "101", "101", "010"],
    'R': ["110", "101", "110", "101", "101"],
    'S': ["111", "100", "111", "001", "111"],
    'T': ["111", "010", "010", "010", "010"],
    'U': ["101", "101", "101", "101", "111"],
    'W': ["10001", "10001", "10101", "11011", "10001"],
    '#': ["01010", "11111", "01010", "11111", "01010"],
    '/': ["001", "010", "010", "010", "100"],
    ':': ["0", "1", "0", "1", "0"],
    '-': ["000", "000", "111", "000", "000"],
    '.': ["0", "0", "0", "0", "1"],
    ' ': ["0", "0", "0", "0", "0"],
}

def draw_text(grid, text, start_x, start_y, color=1):
    x = start_x
    for char in text:
        if char in FONT_3X5:
            pattern = FONT_3X5[char]
            for row_idx, row in enumerate(pattern):
                for col_idx, pixel in enumerate(row):
                    if pixel == '1':
                        grid_y = start_y + row_idx
                        grid_x = x + col_idx
                        if 0 <= grid_x < 32 and 0 <= grid_y < 32:
                            grid[grid_y][grid_x] = color
            x += len(pattern[0]) + 1

def get_time_str(arrivals, index):
    if arrivals and len(arrivals) > index:
        mins = arrivals[index]["minutes"]
        return (str(mins) if mins > 0 else "0", 2 if mins < 2 else 1)
    return ("--", 1)

@app.route("/led")
def led():
    chicago = ZoneInfo("America/Chicago")
    now = datetime.now(chicago)

    metra = get_metra_arrivals()
    bus = get_bus_arrivals()
    temp = get_weather()

    grid = [[0] * 32 for _ in range(32)]

    # Row 1: Day of week (y=1)
    days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    day_str = days[now.weekday()]
    draw_text(grid, day_str, 1, 1)

    # Date (right side)
    date_str = f"{now.month}/{now.day}"
    draw_text(grid, date_str, 17, 1)

    # Row 2: Temperature (y=8)
    if temp is not None:
        temp_str = f"{temp}F"
        draw_text(grid, temp_str, 1, 8)

    # Current time (right side, y=8)
    hour = now.hour % 12
    if hour == 0:
        hour = 12
    time_str = f"{hour}:{now.minute:02d}"
    draw_text(grid, time_str, 15, 8)

    # Divider line (y=14)
    for x in range(32):
        grid[14][x] = 1

    # Row 3: "ME" label (y=17)
    draw_text(grid, "ME", 1, 17)
    # First ME time (always green if scheduled)
    time_str, _ = get_time_str(metra, 0)
    color = 2 if time_str != "--" else 1
    draw_text(grid, time_str, 12, 17, color)
    # Separator dot (centered between times)
    grid[19][21] = 1
    # Second ME time
    time_str, color = get_time_str(metra, 1)
    draw_text(grid, time_str, 24, 17, color)

    # Divider line (y=24)
    for x in range(32):
        grid[24][x] = 1

    # Row 4: "#2" label (y=27)
    draw_text(grid, "#2", 1, 27)
    # First bus time (always green if scheduled)
    time_str, _ = get_time_str(bus, 0)
    color = 2 if time_str != "--" else 1
    draw_text(grid, time_str, 12, 27, color)
    # Separator dot (centered between times)
    grid[29][21] = 1
    # Second bus time
    time_str, color = get_time_str(bus, 1)
    draw_text(grid, time_str, 24, 27, color)

    return render_template("led.html", grid=grid)

if __name__ == "__main__":
    app.run(debug=True)