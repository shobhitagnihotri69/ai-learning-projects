#!/usr/bin/env bash
# deploy_to_boxlite.sh
# Deploys and runs the Startup Radar 24/7 on BoxLite Cloud

set -e

BOX_NAME="startup-radar-daemon"
IMAGE="python:3.11-slim"

echo "🚀 Deploying Startup Radar Daemon to BoxLite Cloud..."

# 1. Check if BoxLite CLI is installed
if ! command -v boxlite &> /dev/null; then
    echo "⚠️  BoxLite CLI not found in PATH."
    echo "Installing BoxLite CLI..."
    curl -fsSL https://sh.boxlite.ai | sh || {
        echo "Please ensure BoxLite CLI is installed via: curl -fsSL https://sh.boxlite.ai | sh"
        exit 1
    }
fi

# 2. Check login status
echo "🔑 Checking BoxLite Cloud auth..."
boxlite auth status || boxlite auth login

# 3. Create persistent box (Stateful by default in BoxLite)
echo "📦 Provisioning BoxLite Cloud microVM..."
boxlite run \
  --name "$BOX_NAME" \
  --detach \
  "$IMAGE" \
  sleep infinity

echo "📁 Copying radar scripts into the BoxLite box..."
boxlite cp ./startup_radar.py "$BOX_NAME":/data/startup_radar.py
boxlite cp ./radar_daemon.py "$BOX_NAME":/data/radar_daemon.py

# 4. Start daemon inside BoxLite
echo "⚡ Starting 24/7 Radar Daemon in background..."
boxlite exec "$BOX_NAME" nohup python3 /data/radar_daemon.py > /data/radar.log 2>&1 &

echo ""
echo "✅ SUCCESS: Startup Radar is now running 24/7 in BoxLite Cloud!"
echo "To check live logs: boxlite exec $BOX_NAME tail -f /data/radar.log"
echo "To view generated report: boxlite cp $BOX_NAME:/data/STARTUP_RADAR_REPORT.md ./STARTUP_RADAR_REPORT.md"

