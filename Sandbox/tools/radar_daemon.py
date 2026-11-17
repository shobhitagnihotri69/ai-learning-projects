#!/usr/bin/env python3
"""
Continuous 24/7 Radar Daemon
Runs startup_radar.py on a recurring schedule and logs updates.
Can optionally send alerts to a Discord Webhook if DISCORD_WEBHOOK_URL is set.
"""

import os
import sys
import time
import subprocess
from datetime import datetime

# Optional: set via environment variable: export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RADAR_SCRIPT = os.path.join(SCRIPT_DIR, "startup_radar.py")
REPORT_PATH = os.path.join(SCRIPT_DIR, "STARTUP_RADAR_REPORT.md")

# Default scan frequency: every 4 hours (14400 seconds)
SCAN_INTERVAL_SECONDS = int(os.environ.get("RADAR_INTERVAL", 14400))

def send_discord_alert(message):
    if not WEBHOOK_URL:
        return
    import json
    import urllib.request
    import ssl
    payload = {"content": message}
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "BoxLiteRadar/1.0"}
    )
    try:
        urllib.request.urlopen(req, context=ssl._create_unverified_context(), timeout=10)
        print("📨 Discord webhook notification sent.")
    except Exception as e:
        print(f"⚠️ Failed to send Discord webhook: {e}")

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 Startup Radar Daemon Initialized.")
    print(f"Scanning every {SCAN_INTERVAL_SECONDS // 3600} hours...")
    
    send_discord_alert("🟢 **Startup Radar Daemon Started inside BoxLite Cloud**\nMonitoring newly launched AI sandboxes & microVM repos 24/7.")

    while True:
        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n--- [{start_time}] Starting radar scan ---")
        
        try:
            res = subprocess.run([sys.executable, RADAR_SCRIPT], capture_output=True, text=True)
            print(res.stdout)
            if res.returncode != 0:
                print(f"Scan error: {res.stderr}")
            else:
                print("✅ Radar scan completed successfully.")
        except Exception as e:
            print(f"Execution failed: {e}")

        print(f"Sleeping for {SCAN_INTERVAL_SECONDS} seconds until next scan...")
        time.sleep(SCAN_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()

