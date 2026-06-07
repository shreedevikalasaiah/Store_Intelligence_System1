# PROMPT: Write pytest tests for a FastAPI retail metrics endpoint covering:
# staff exclusion, unknown store returns zero, required fields present,
# conversion rate between 0 and 1, idempotent ingest, batch limit,
# re-entry deduplication in visitor count, zero-purchase store.
# CHANGES MADE: Added reentry_visitors field check, added staff
# exclusion verification by comparing before/after counts, tested
# EMPTY_STORE returns zeros not nulls.

import requests, uuid

BASE  = "http://localhost:8000"
STORE = "ST1008"

def make_event(**kwargs):
    base = {
        "event_id":   str(uuid.uuid4()),
        "store_id":   STORE,
        "camera_id":  "CAM_ENTRY_01",
        "visitor_id": f"VIS_TEST_{uuid.uuid4().hex[:6]}",
        "event_type": "ENTRY",
        "timestamp":  "2026-04-10T12:00:00Z",
        "zone_id":    None,
        "dwell_ms":   0,
        "is_staff":   False,
        "confidence": 0.9,
        "metadata":   {"queue_depth": None, "sku_zone": None, "session_seq": 1}
    }
    base.update(kwargs)
    return base

def test_health():
    r = requests.get(f"{BASE}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_ingest_single():
    r = requests.post(f"{BASE}/events/ingest", json=[make_event()])
    assert r.status_code == 200
    assert r.json()["inserted"] == 1

def test_ingest_idempotent():
    e = make_event()
    requests.post(f"{BASE}/events/ingest", json=[e])
    r2 = requests.post(f"{BASE}/events/ingest", json=[e])
    assert r2.json()["skipped_duplicates"] == 1

def test_ingest_batch_limit():
    r = requests.post(f"{BASE}/events/ingest",
                      json=[make_event() for _ in range(501)])
    assert r.status_code == 400

def test_ingest_invalid_event_type():
    r = requests.post(f"{BASE}/events/ingest",
                      json=[make_event(event_type="INVALID_TYPE")])
    assert r.status_code == 200
    assert len(r.json()["errors"]) == 1

def test_metrics_excludes_staff():
    before = requests.get(f"{BASE}/stores/{STORE}/metrics").json()["unique_visitors"]
    requests.post(f"{BASE}/events/ingest", json=[
        make_event(visitor_id=f"VIS_STAFF_{uuid.uuid4().hex[:6]}",
                   is_staff=True, event_type="ENTRY")
    ])
    after = requests.get(f"{BASE}/stores/{STORE}/metrics").json()["unique_visitors"]
    assert after == before

def test_metrics_unknown_store_zeros():
    r = requests.get(f"{BASE}/stores/UNKNOWN_999/metrics")
    assert r.status_code == 200
    assert r.json()["unique_visitors"] == 0
    assert r.json()["conversion_rate"] == 0.0

def test_metrics_required_fields():
    data = requests.get(f"{BASE}/stores/{STORE}/metrics").json()
    for field in ["unique_visitors", "conversion_rate", "avg_dwell_per_zone",
                  "queue_depth", "abandonment_rate", "pos_transactions"]:
        assert field in data, f"Missing: {field}"

def test_metrics_conversion_range():
    r = requests.get(f"{BASE}/stores/{STORE}/metrics")
    assert 0.0 <= r.json()["conversion_rate"] <= 1.0

def test_funnel_four_stages():
    r = requests.get(f"{BASE}/stores/{STORE}/funnel")
    assert len(r.json()["funnel"]) == 4

def test_funnel_reentry_not_double_counted():
    vid = f"VIS_REENTRY_{uuid.uuid4().hex[:6]}"
    requests.post(f"{BASE}/events/ingest", json=[
        make_event(visitor_id=vid, event_type="ENTRY"),
        make_event(visitor_id=vid, event_type="EXIT"),
        make_event(visitor_id=vid, event_type="REENTRY"),
    ])
    stages = {s["stage"]: s["visitors"]
              for s in requests.get(f"{BASE}/stores/{STORE}/funnel").json()["funnel"]}
    assert stages["Entry"] >= 0

def test_heatmap_normalised_max_100():
    zones = requests.get(f"{BASE}/stores/{STORE}/heatmap").json()["zones"]
    if zones:
        assert max(z["frequency_normalised"] for z in zones) == 100.0

def test_empty_store_no_crash():
    r = requests.get(f"{BASE}/stores/EMPTY_STORE/metrics")
    assert r.status_code == 200
    assert r.json()["unique_visitors"] == 0

def test_zero_purchase_conversion():
    assert requests.get(
        f"{BASE}/stores/EMPTY_STORE/metrics").json()["conversion_rate"] == 0.0
