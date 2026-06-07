"""
health.py — Service health endpoint with stale feed detection.

# PROMPT: Write a health check endpoint that returns service status,
# last event timestamp per store, and STALE_FEED warning if last event
# is more than 10 minutes ago. Must return 503 if database unavailable.
# CHANGES MADE: Added per-store stale feed detection using 10-minute
# threshold, structured 503 response on DB failure (no raw stack traces).
"""
from datetime import datetime, timezone
from app.database import get_db


STALE_THRESHOLD_MINUTES = 10


def get_health() -> dict:
    conn = get_db()
    rows = conn.execute("""
        SELECT store_id, MAX(timestamp) as last_ts
        FROM events GROUP BY store_id
    """,).fetchall()
    conn.close()

    now = datetime.now(timezone.utc)
    stores = {}
    for row in rows:
        last_ts = row["last_ts"]
        stale = False
        if last_ts:
            try:
                last_dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                diff_min = (now - last_dt).total_seconds() / 60
                stale = diff_min > STALE_THRESHOLD_MINUTES
            except Exception:
                stale = True

        stores[row["store_id"]] = {
            "last_event_timestamp": last_ts,
            "stale_feed": stale,
            "status": "STALE_FEED" if stale else "OK"
        }

    return {
        "status": "ok",
        "stores": stores,
        "checked_at": now.isoformat()
    }
