#!/bin/bash
# run.sh — One command to process all CCTV clips and load events into API
# Usage: bash pipeline/run.sh /path/to/cctv_footage http://localhost:8000

CAM_PATH=${1:-"cctv_footage"}
API_URL=${2:-"http://localhost:8000"}

echo "=== Store Intelligence Detection Pipeline ==="
echo "Camera path : $CAM_PATH"
echo "API URL     : $API_URL"

# Install dependencies
pip install ultralytics supervision opencv-python-headless -q

# Run detection
python pipeline/detect.py "$CAM_PATH" events_all.jsonl

# Load events into API in batches
python - <<EOF
import json, requests

events = [json.loads(l) for l in open("events_all.jsonl")]
print(f"Loading {len(events)} events into API...")

success = 0
for i in range(0, len(events), 500):
    r = requests.post("$API_URL/events/ingest", json=events[i:i+500], timeout=30)
    success += r.json().get("inserted", 0)

print(f"✅ Loaded {success} events")
r = requests.get("$API_URL/stores/ST1008/metrics")
print("Metrics:", r.json())
EOF

echo "=== Done ==="
