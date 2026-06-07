"""
ingestion.py — Event ingest, deduplication, and validation.

# PROMPT: Write a FastAPI ingest handler that accepts batches of up to 500
# retail CV events, validates each, deduplicates by event_id (idempotent),
# and returns partial success on malformed events.
# CHANGES MADE: Added batch size limit of 500, structured error response
# per event, used INSERT OR IGNORE for idempotency, added event_type whitelist.
"""
from fastapi import HTTPException
from typing import List
from app.models import Event, IngestResponse
from app.database import get_db

VALID_TYPES = {
    "ENTRY", "EXIT", "ZONE_ENTER", "ZONE_EXIT", "ZONE_DWELL",
    "BILLING_QUEUE_JOIN", "BILLING_QUEUE_ABANDON", "REENTRY"
}


def ingest_events(events: List[Event]) -> IngestResponse:
    if len(events) > 500:
        raise HTTPException(status_code=400, detail="Batch size exceeds 500 events")

    conn = get_db()
    inserted, skipped, errors = 0, 0, []

    for event in events:
        try:
            if event.event_type not in VALID_TYPES:
                errors.append({
                    "event_id": event.event_id,
                    "error": f"Invalid event_type: {event.event_type}"
                })
                continue

            cur = conn.execute("""
                INSERT OR IGNORE INTO events
                (event_id, store_id, camera_id, visitor_id, event_type,
                 timestamp, zone_id, dwell_ms, is_staff, confidence,
                 queue_depth, sku_zone, session_seq)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                event.event_id, event.store_id, event.camera_id,
                event.visitor_id, event.event_type, event.timestamp,
                event.zone_id, event.dwell_ms, int(event.is_staff),
                event.confidence, event.metadata.queue_depth,
                event.metadata.sku_zone, event.metadata.session_seq
            ))

            if cur.rowcount > 0:
                inserted += 1
            else:
                skipped += 1

        except Exception as e:
            errors.append({"event_id": event.event_id, "error": str(e)})

    conn.commit()
    conn.close()
    return IngestResponse(inserted=inserted, skipped_duplicates=skipped, errors=errors)
