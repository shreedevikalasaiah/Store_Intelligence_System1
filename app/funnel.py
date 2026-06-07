"""
funnel.py — Conversion funnel with session deduplication.

# PROMPT: Write a retail conversion funnel query that counts unique visitors
# at each stage: Entry, Zone Visit, Billing Zone, Purchase. Use session as
# unit not raw events. Re-entries must not double-count a visitor.
# CHANGES MADE: Used COUNT(DISTINCT visitor_id) at every stage,
# included REENTRY in Entry stage count, used POS transaction count
# for Purchase stage (not a visitor event).
"""
from app.database import get_db


def get_funnel(store_id: str) -> dict:
    conn = get_db()

    entries = conn.execute("""
        SELECT COUNT(DISTINCT visitor_id) FROM events
        WHERE store_id=? AND event_type IN ('ENTRY','REENTRY') AND is_staff=0
    """, (store_id,)).fetchone()[0] or 0

    zone_visits = conn.execute("""
        SELECT COUNT(DISTINCT visitor_id) FROM events
        WHERE store_id=? AND event_type IN ('ZONE_DWELL','ZONE_ENTER','BILLING_QUEUE_JOIN')
          AND is_staff=0
    """, (store_id,)).fetchone()[0] or 0

    billing = conn.execute("""
        SELECT COUNT(DISTINCT visitor_id) FROM events
        WHERE store_id=? AND zone_id='BILLING_ZONE' AND is_staff=0
    """, (store_id,)).fetchone()[0] or 0

    purchases = conn.execute(
        "SELECT COUNT(DISTINCT transaction_id) FROM pos_transactions WHERE store_id=?",
        (store_id,)
    ).fetchone()[0] or 0

    def drop(a, b):
        return round((1 - b / a) * 100, 1) if a > 0 else 0.0

    conn.close()
    return {
        "store_id": store_id,
        "funnel": [
            {"stage": "Entry",        "visitors": entries,     "dropoff_pct": 0},
            {"stage": "Zone Visit",   "visitors": zone_visits, "dropoff_pct": drop(entries, zone_visits)},
            {"stage": "Billing Zone", "visitors": billing,     "dropoff_pct": drop(zone_visits, billing)},
            {"stage": "Purchase",     "visitors": purchases,   "dropoff_pct": drop(billing, purchases)},
        ]
    }


def get_heatmap(store_id: str) -> dict:
    conn = get_db()
    rows = conn.execute("""
        SELECT zone_id, COUNT(DISTINCT visitor_id) as visitors,
               AVG(dwell_ms) as avg_dwell
        FROM events WHERE store_id=? AND zone_id IS NOT NULL AND is_staff=0
        GROUP BY zone_id
    """, (store_id,)).fetchall()

    if not rows:
        conn.close()
        return {"store_id": store_id, "zones": [], "data_confidence": "LOW"}

    max_v = max(r["visitors"] for r in rows) or 1
    max_d = max(r["avg_dwell"] for r in rows) or 1
    total = conn.execute("""
        SELECT COUNT(DISTINCT visitor_id) FROM events
        WHERE store_id=? AND event_type='ENTRY'
    """, (store_id,)).fetchone()[0] or 0

    conn.close()
    zones = [{
        "zone_id": r["zone_id"],
        "visit_frequency": r["visitors"],
        "avg_dwell_ms": round(r["avg_dwell"], 1),
        "frequency_normalised": round(r["visitors"] / max_v * 100, 1),
        "dwell_normalised": round(r["avg_dwell"] / max_d * 100, 1),
    } for r in rows]

    return {
        "store_id": store_id,
        "zones": sorted(zones, key=lambda x: x["frequency_normalised"], reverse=True),
        "data_confidence": "LOW" if total < 20 else "HIGH"
    }
