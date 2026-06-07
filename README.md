# Store Intelligence

A lightweight retail analytics system that converts CCTV detection data into store events, metrics, funnel analysis, and anomaly detection.

## Repository structure

- `app/` — FastAPI backend and analytics modules
- `pipeline/` — detection, tracker, event schema, and event emission
- `tests/` — integration and analytics tests
- `docs/` — architecture and design decisions
- `docker-compose.yml` — container launch configuration
- `Dockerfile` — container build instructions
- `requirements.txt` — Python dependencies

## Setup

```powershell
cd Store_Intelligence_System1-main
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

The pipeline will use a local `yolov8n.pt` file if present, otherwise it will fall back to the remote `yolov8n` model from Ultralytics.

If you want to use a custom local path, set:

```powershell
$env:YOLO_MODEL_PATH = "C:\path\to\yolov8n.pt"
```

## Run the API

```powershell
cd Store_Intelligence_System1-main
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Run the detection pipeline

```bash
bash pipeline/run.sh "CCTV Footage" http://127.0.0.1:8000
```

Or run detection only:

```bash
python pipeline/detect.py "CCTV Footage" events_all.jsonl
```

## Docker

```bash
docker-compose up --build
```

## Notes

- Raw sample footage and generated event artifacts are not included in this repository.
- `yolov8n.pt` is intentionally excluded from source control.
- The API stores events in a local SQLite database by default.
