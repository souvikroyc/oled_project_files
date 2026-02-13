import time
import subprocess
import psutil
import glob
import signal
import sys
import os
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont

# OLED setup
serial = i2c(port=1, address=0x3C)  # Adjust the I2C address if needed
device = ssd1306(serial, width=128, height=64)

# Load fonts
default_font = ImageFont.load_default()
ip_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 10)

# ---- Shutdown handler ----
def shutdown_handler(signum, frame):
    """Clear and power off OLED on shutdown/exit."""
    try:
        device.clear()
        device.hide()   # sends 'display off' command (0xAE)
    except Exception as e:
        print(f"Error turning off OLED: {e}")
    sys.exit(0)

# Catch system signals (shutdown/reboot/ctrl+c)
signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

# ---- System info functions ----
def get_ip_address():
    cmd = "hostname -I | cut -d' ' -f1"
    return subprocess.check_output(cmd, shell=True).decode('utf-8').strip()

def get_cpu_usage():
    return psutil.cpu_percent(interval=0.5)

def get_memory_usage():
    mem = psutil.virtual_memory()
    return mem.percent, mem.used / (1024**3), mem.total / (1024**3)

def get_temperature_f():
    """Return CPU temperature in Fahrenheit as a string like '120.3°F'."""
    try:
        raw = subprocess.check_output(["vcgencmd", "measure_temp"]).decode()
        celsius = float(raw.split('=')[1].split("'")[0])
        fahrenheit = celsius * 9 / 5 + 32
        return f"{fahrenheit:.1f}°F"
    except Exception:
        return "N/A"

def get_disk_usage():
    disk = psutil.disk_usage('/')
    return disk.percent, disk.used / (1024**3), disk.total / (1024**3)

def get_fan_speed_with_percent(max_rpm=6500):
    """
    Returns a string like '2450 RPM (58%)'.
    `max_rpm` should be set to your fan's max RPM (consult spec, e.g., 4200 RPM).
    """
    try:
        paths = glob.glob("/sys/devices/platform/cooling_fan/hwmon/*/fan1_input")
        if not paths:
            return "N/A"

        with open(paths[0], "r") as f:
            rpm_str = f.read().strip()
        rpm = int(rpm_str)

        percent = min(int(rpm / max_rpm * 100), 100)
        return f"{rpm} RPM ({percent}%)"
    except Exception:
        return "N/A"

# ---- Main loop ----
try:
    while True:
        ip_address = get_ip_address()
        cpu_usage = get_cpu_usage()
        mem_percent, mem_used, mem_total = get_memory_usage()
        temperature_f = get_temperature_f()
        disk_percent, disk_used, disk_total = get_disk_usage()
        fan_speed = get_fan_speed_with_percent()

        with canvas(device) as draw:
            draw.text((0, 0),  "Raspberry Pi Stats:", font=ip_font, fill="white")
            draw.text((0, 15), f"CPU:{cpu_usage:.1f}% Temp:{temperature_f}", font=default_font, fill="white")
            draw.text((0, 25), f"RAM:{mem_used:.2f}/{mem_total:.2f}GB",      font=default_font, fill="white")
            draw.text((0, 35), f"Disk:{disk_used:.2f}/{disk_total:.2f}GB",   font=default_font, fill="white")
            draw.text((0, 45), f"Fan: {fan_speed}",                          font=default_font, fill="white")
            draw.text((0, 55), f"IP: {ip_address}",                          font=default_font, fill="white")

        time.sleep(1)

except KeyboardInterrupt:
    shutdown_handler(None, None)

