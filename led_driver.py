#!/usr/bin/env python3
"""
LED Matrix Driver for 32x32 RGB Panel

This script drives a physical 32x32 LED matrix connected to a Raspberry Pi
via the Adafruit RGB Matrix Bonnet.

Hardware required:
- Raspberry Pi (Zero 2 W, 3, 4, or 5)
- 32x32 RGB LED Matrix (P4 or P5)
- Adafruit RGB Matrix Bonnet

Setup:
1. Install the RGB Matrix library:
   curl https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/main/rgb-matrix.sh > rgb-matrix.sh
   sudo bash rgb-matrix.sh

2. Install Python dependencies:
   pip install requests python-dotenv

3. Copy your .env file to the Pi with your API keys

4. Run with sudo (required for GPIO access):
   sudo python3 led_driver.py
"""

import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

CTA_BUS_API_KEY = os.getenv("CTA_BUS_API_KEY")
METRA_API_TOKEN = os.getenv("METRA_API_TOKEN")
METEOSOURCE_API_KEY = os.getenv("METEOSOURCE_API_KEY")

# Try to import the RGB Matrix library (only works on Pi)
try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
    PI_MODE = True
except ImportError:
    print("RGB Matrix library not found - running in simulation mode")
    PI_MODE = False

# Colors (RGB)
AMBER = (255, 157, 0)
GREEN = (0, 255, 0)
DIM = (40, 40, 40)

# 3x5 pixel font
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
    'N': ["101", "111", "111", "101", "101"],
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

BUS_STOPS = {
    "1423": {"name": "State & Lake", "routes": ["2"]}
}

# Weather cache
weather_cache = {"temp": None, "last_updated": None}


def get_metra_arrivals():
    """Fetch Metra Electric arrivals from Millennium Station."""
    try:
        from google.transit import gtfs_realtime_pb2
    except ImportError:
        print("gtfs-realtime-bindings not installed, skipping Metra")
        return []

    chicago = ZoneInfo("America/Chicago")
    now = datetime.now(chicago)

    try:
        url = f"https://gtfspublic.metrarr.com/gtfs/public/tripupdates?api_token={METRA_API_TOKEN}"
        response = requests.get(url, timeout=10)

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)

        arrivals = []
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

                        arrivals.append({"minutes": minutes_away})

        return sorted(arrivals, key=lambda x: x["minutes"])[:5]
    except Exception as e:
        print(f"Error fetching Metra: {e}")
        return []


def get_bus_arrivals():
    """Fetch CTA Bus #2 arrivals."""
    bus_arrivals = []

    for stop_id, stop_info in BUS_STOPS.items():
        try:
            url = f"https://www.ctabustracker.com/bustime/api/v2/getpredictions?key={CTA_BUS_API_KEY}&stpid={stop_id}&format=json"
            response = requests.get(url, timeout=10)
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

                        bus_arrivals.append({"minutes": minutes})
        except Exception as e:
            print(f"Error fetching bus: {e}")

    return sorted(bus_arrivals, key=lambda x: x["minutes"])[:5]


def get_weather():
    """Fetch current temperature with 10-minute caching."""
    chicago = ZoneInfo("America/Chicago")
    now = datetime.now(chicago)

    if weather_cache["last_updated"]:
        elapsed = (now - weather_cache["last_updated"]).total_seconds()
        if elapsed < 600 and weather_cache["temp"] is not None:
            return weather_cache["temp"]

    try:
        url = f"https://www.meteosource.com/api/v1/free/point?place_id=chicago&sections=current&key={METEOSOURCE_API_KEY}"
        response = requests.get(url, timeout=10)
        data = response.json()
        temp = round(data["current"]["temperature"])
        weather_cache["temp"] = temp
        weather_cache["last_updated"] = now
        return temp
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return weather_cache["temp"]


def draw_text(grid, text, start_x, start_y, color=1):
    """Draw text onto the grid using the 3x5 font."""
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
    """Get formatted time string for an arrival."""
    if arrivals and len(arrivals) > index:
        mins = arrivals[index]["minutes"]
        return (str(mins) if mins > 0 else "0", 2 if mins < 2 else 1)
    return ("--", 1)


def build_grid():
    """Build the 32x32 display grid."""
    chicago = ZoneInfo("America/Chicago")
    now = datetime.now(chicago)

    metra = get_metra_arrivals()
    bus = get_bus_arrivals()
    temp = get_weather()

    # 0 = off, 1 = amber, 2 = green
    grid = [[0] * 32 for _ in range(32)]

    # Row 1: Day of week (y=1)
    days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    day_str = days[now.weekday()]
    draw_text(grid, day_str, 1, 1)

    # Date (right side)
    date_str = f"{now.month}/{now.day}"
    draw_text(grid, date_str, 20, 1)

    # Row 2: Temperature (y=8)
    if temp is not None:
        temp_str = f"{temp}F"
        draw_text(grid, temp_str, 1, 8)

    # Current time (right side, y=8)
    hour = now.hour % 12
    if hour == 0:
        hour = 12
    time_str = f"{hour}:{now.minute:02d}"
    draw_text(grid, time_str, 18, 8)

    # Divider line (y=14)
    for x in range(32):
        grid[14][x] = 1

    # Row 3: "ME" label (y=17)
    draw_text(grid, "ME", 1, 17)
    # First ME time (always green if scheduled)
    time_str, _ = get_time_str(metra, 0)
    color = 2 if time_str != "--" else 1
    draw_text(grid, time_str, 12, 17, color)
    # Separator dot
    grid[19][20] = 1
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
    # Separator dot
    grid[29][20] = 1
    # Second bus time
    time_str, color = get_time_str(bus, 1)
    draw_text(grid, time_str, 24, 27, color)

    return grid


def render_to_matrix(matrix, grid):
    """Render the grid to the physical LED matrix."""
    offset_canvas = matrix.CreateFrameCanvas()

    for y in range(32):
        for x in range(32):
            pixel = grid[y][x]
            if pixel == 0:
                r, g, b = DIM
            elif pixel == 1:
                r, g, b = AMBER
            elif pixel == 2:
                r, g, b = GREEN
            else:
                r, g, b = (0, 0, 0)

            offset_canvas.SetPixel(x, y, r, g, b)

    matrix = matrix.SwapOnVSync(offset_canvas)
    return matrix


def print_grid(grid):
    """Print the grid to console (for testing without hardware)."""
    os.system('clear' if os.name == 'posix' else 'cls')
    for row in grid:
        line = ""
        for pixel in row:
            if pixel == 0:
                line += "·"
            elif pixel == 1:
                line += "█"
            elif pixel == 2:
                line += "▓"
        print(line)
    print()


def setup_matrix():
    """Configure and return the RGB matrix."""
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 32
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = 'adafruit-hat'
    options.gpio_slowdown = 4
    options.brightness = 50  # Adjust 1-100

    return RGBMatrix(options=options)


def main():
    """Main loop - refresh display every 30 seconds."""
    print("Starting LED Transit Board...")

    if PI_MODE:
        matrix = setup_matrix()
        print("LED Matrix initialized")
    else:
        matrix = None
        print("Running in simulation mode (console output)")

    refresh_interval = 30  # seconds

    try:
        while True:
            grid = build_grid()

            if PI_MODE:
                render_to_matrix(matrix, grid)
            else:
                print_grid(grid)

            time.sleep(refresh_interval)

    except KeyboardInterrupt:
        print("\nShutting down...")
        if PI_MODE:
            matrix.Clear()


if __name__ == "__main__":
    main()
