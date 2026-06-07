"""
main.py — FastAPI entrypoint. Routes delegate to module files.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import json, uuid, time

from app.models import Event, IngestResponse
from app.database import get_db, init_db
from app.ingestion import ingest_events as _ingest
from app.metrics import get_metrics as _metrics
from app.funnel import get_funnel, get_heatmap
from app.anomalies import get_anomalies
from app.health import get_health

app = FastAPI(title="Store Intelligence API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    trace_id = str(uuid.uuid4())[:8]
    start    = time.time()
    response = await call_next(request)
    latency  = int((time.time() - start) * 1000)
    store_id = request.path_params.get("store_id", "-")
    print(json.dumps({
        "trace_id":    trace_id,
        "store_id":    store_id,
        "endpoint":    str(request.url.path),
        "method":      request.method,
        "status_code": response.status_code,
        "latency_ms":  latency
    }))
    return response

@app.post("/events/ingest", response_model=IngestResponse)
def ingest(events: List[Event]):
    return _ingest(events)

@app.get("/stores/{store_id}/metrics")
def metrics(store_id: str):
    try:
        return _metrics(store_id)
    except Exception as e:
        return JSONResponse(status_code=503,
                           content={"status": "error", "detail": str(e)})

@app.get("/stores/{store_id}/funnel")
def funnel(store_id: str):
    return get_funnel(store_id)

@app.get("/stores/{store_id}/heatmap")
def heatmap(store_id: str):
    return get_heatmap(store_id)

@app.get("/stores/{store_id}/anomalies")
def anomalies(store_id: str):
    return get_anomalies(store_id)

@app.get("/health")
def health():
    try:
        return get_health()
    except Exception as e:
        return JSONResponse(status_code=503,
                           content={"status": "degraded", "error": str(e)})
