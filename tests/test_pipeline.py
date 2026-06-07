# PROMPT: Write pytest tests for the pipeline event emission flow, including event format validation and duplicate ingest behavior.

import uuid
from pipeline.emit import make_event, validate_event


def test_make_event_has_required_fields():
    event = make_event(
        camera_id="CAM_ENTRY_01",
        visitor_id="VIS123",
        event_type="ENTRY",
        timestamp="2026-04-10T12:00:00Z",
        zone_id=None,
        dwell_ms=0,
        is_staff=False,
        confidence=0.85,
    )

    assert event["store_id"] == "ST1008"
    assert event["event_type"] == "ENTRY"
    assert event["metadata"]["session_seq"] == 1


def test_validate_event_accepts_valid_event():
    event = make_event(
        camera_id="CAM_ENTRY_01",
        visitor_id="VIS123",
        event_type="ZONE_ENTER",
        timestamp="2026-04-10T12:01:00Z",
        zone_id="MAIN_FLOOR",
        dwell_ms=1000,
        is_staff=False,
        confidence=0.92,
    )

    errors = validate_event(event)
    assert errors == []


def test_validate_event_rejects_missing_field():
    event = make_event(
        camera_id="CAM_ENTRY_01",
        visitor_id="VIS123",
        event_type="ENTRY",
        timestamp="2026-04-10T12:02:00Z",
        zone_id=None,
        dwell_ms=0,
        is_staff=False,
        confidence=0.7,
    )
    del event["camera_id"]

    errors = validate_event(event)
    assert any("Missing field" in msg for msg in errors)
