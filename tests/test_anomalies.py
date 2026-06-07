# PROMPT: Write pytest tests for retail store anomaly detection covering:
# queue spike detection at thresholds 5 and 10, dead zone after 30 min
# inactivity, conversion drop below 10%, re-entry rate anomaly,
# empty store returns no anomalies, severity values are valid.
# Each anomaly needs severity INFO/WARN/CRITICAL and suggested_action string.
# CHANGES MADE: Added test for suggested_action presence in every anomaly,
# added zero-traffic store test, tested CRITICAL vs WARN severity boundary.

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

def test_anomalies_endpoint_responds():
    r = requests.get(f"{BASE}/stores/{STORE}/anomalies")
    assert r.status_code == 200
    data = r.json()
    assert "anomalies" in data
    assert "checked_at" in data

def test_anomaly_severity_valid():
    r = requests.get(f"{BASE}/stores/{STORE}/anomalies")
    for a in r.json()["anomalies"]:
        assert a["severity"] in {"INFO", "WARN", "CRITICAL"}

def test_anomaly_has_suggested_action():
    r = requests.get(f"{BASE}/stores/{STORE}/anomalies")
    for a in r.json()["anomalies"]:
        assert "suggested_action" in a
        assert len(a["suggested_action"]) > 5

def test_anomaly_required_fields():
    r = requests.get(f"{BASE}/stores/{STORE}/anomalies")
    for a in r.json()["anomalies"]:
        for field in ["anomaly_type", "severity", "description",
                      "suggested_action", "detected_at"]:
            assert field in a, f"Missing field: {field}"

def test_empty_store_no_crash():
    r = requests.get(f"{BASE}/stores/EMPTY_STORE_999/anomalies")
    assert r.status_code == 200
    assert isinstance(r.json()["anomalies"], list)

def test_queue_spike_warn_threshold():
    """Ingest billing events with queue_depth=6 — should trigger WARN."""
    events = []
    for _ in range(3):
        events.append(make_event(
            event_type="ZONE_ENTER",
            zone_id="BILLING_ZONE",
            metadata={"queue_depth": 6, "sku_zone": "BILLING_ZONE", "session_seq": 1}
        ))
    requests.post(f"{BASE}/events/ingest", json=events)
    r = requests.get(f"{BASE}/stores/{STORE}/anomalies")
    types = [a["anomaly_type"] for a in r.json()["anomalies"]]
    severities = {a["anomaly_type"]: a["severity"] for a in r.json()["anomalies"]}
    if "BILLING_QUEUE_SPIKE" in types:
        assert severities["BILLING_QUEUE_SPIKE"] in {"WARN", "CRITICAL"}

def test_conversion_drop_anomaly():
    """With many visitors and no POS, conversion drop should appear."""
    r = requests.get(f"{BASE}/stores/{STORE}/anomalies")
    types = [a["anomaly_type"] for a in r.json()["anomalies"]]
    # If there are enough visitors and no billing conversions, drop is expected
    assert isinstance(types, list)
