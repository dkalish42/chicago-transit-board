# Raspberry Pi LED Matrix Setup

## Hardware Assembly

1. Attach the **RGB Matrix Bonnet** to the Pi's GPIO pins
2. Connect the **ribbon cable** from the bonnet to the LED matrix (arrow on cable matches arrow on matrix)
3. Connect **5V power supply** to the bonnet's power terminal (+ and -)
4. Connect **Micro USB power** to the Pi (or power via bonnet if supported)

## Software Setup

### 1. Install Raspberry Pi OS

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to flash **Raspberry Pi OS Lite (64-bit)** to your SD card.

Enable SSH and configure WiFi during imaging.

### 2. SSH into your Pi

```bash
ssh pi@raspberrypi.local
```

### 3. Install the RGB Matrix Library

```bash
curl https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/main/rgb-matrix.sh > rgb-matrix.sh
sudo bash rgb-matrix.sh
```

Choose:
- **Quality**: Choose "Quality" (disables audio but improves display)
- **Interface**: Choose "Adafruit Bonnet"

Reboot when prompted.

### 4. Install Python Dependencies

```bash
sudo apt install python3-pip python3-venv
python3 -m venv ~/transit-env
source ~/transit-env/bin/activate
pip install requests python-dotenv gtfs-realtime-bindings
```

### 5. Clone the Project

```bash
git clone https://github.com/dkalish42/chicago-transit-board.git
cd chicago-transit-board
```

### 6. Create .env File

```bash
nano .env
```

Add your API keys:
```
CTA_BUS_API_KEY=your_key_here
METRA_API_TOKEN=your_token_here
METEOSOURCE_API_KEY=your_key_here
```

### 7. Test the Display

```bash
sudo ~/transit-env/bin/python led_driver.py
```

You should see the transit board on your LED matrix!

## Auto-Start on Boot

### Create a systemd service

```bash
sudo nano /etc/systemd/system/transit-board.service
```

Add:
```ini
[Unit]
Description=Transit Board LED Display
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/pi/chicago-transit-board
ExecStart=/home/pi/transit-env/bin/python led_driver.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and start

```bash
sudo systemctl enable transit-board
sudo systemctl start transit-board
```

### Check status

```bash
sudo systemctl status transit-board
```

## Troubleshooting

**Display flickering or wrong colors:**
- Try increasing `gpio_slowdown` in `led_driver.py` (line ~285)
- Values 1-4 work for most setups

**Display too bright/dim:**
- Adjust `options.brightness` in `led_driver.py` (line ~286)
- Values 1-100

**No display:**
- Check ribbon cable orientation (arrows should match)
- Verify 5V power is connected to bonnet
- Run with `sudo` (required for GPIO)

**API errors:**
- Check your .env file has valid API keys
- Verify Pi has internet: `ping google.com`
