
import json
import uuid
from datetime import datetime, timezone
from typing import Optional


VALID_EVENT_TYPES = {
    'ENTRY', 'EXIT', 'ZONE_ENTER', 'ZONE_EXIT',
    'ZONE_DWELL', 'BILLING_QUEUE_JOIN', 'BILLING_QUEUE_ABANDON', 'REENTRY'
}

STORE_ID = "ST1008"


def make_event(
    camera_id:  str,
    visitor_id: str,
    event_type: str,
    timestamp:  str,
    zone_id:    Optional[str],
    dwell_ms:   int,
    is_staff:   bool,
    confidence: float,
    queue_depth: Optional[int] = None,
    sku_zone:   Optional[str] = None,
    session_seq: int = 1,
) -> 
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"Invalid event_type: {event_type}")

    # Auto-upgrade to BILLING_QUEUE_JOIN
    if (
        event_type == 'ZONE_ENTER'
            and zone_id == 'BILLING_ZONE'
            and queue_depth is not None
            and queue_depth > 2
    ):
        event_type = 'BILLING_QUEUE_JOIN'

    # zone_id is null for ENTRY / EXIT / REENTRY
    if event_type in ('ENTRY', 'EXIT', 'REENTRY'):
        zone_id = None

    return {
        "event_id":   str(uuid.uuid4()),
        "store_id":   STORE_ID,
        "camera_id":  camera_id,
        "visitor_id": visitor_id,
        "event_type": event_type,
        "timestamp":  timestamp,
        "zone_id":    zone_id,
        "dwell_ms":   dwell_ms,
        "is_staff":   is_staff,
        "confidence": round(float(confidence), 4),
        "metadata": {
            "queue_depth": queue_depth,
            "sku_zone":    sku_zone or zone_id,
            "session_seq": session_seq,
        }
    }


def emit_to_file(event: dict, file_handle) -> None:
    """Write a single event as a JSONL line."""
    file_handle.write(json.dumps(event) + "\n")


def validate_event(event: dict) -> list[str]:
    """Return list of validation errors. Empty = valid."""
    errors = []
    required = ['event_id','store_id','camera_id','visitor_id',
                'event_type','timestamp','is_staff','confidence','metadata']
    for field in required:
        if field not in event:
            errors.append(f"Missing field: {field}")
    if event.get('event_type') not in VALID_EVENT_TYPES:
        errors.append(f"Invalid event_type: {event.get('event_type')}")
    if not isinstance(event.get('confidence'), (int, float)):
        errors.append("confidence must be numeric")
    return errors
