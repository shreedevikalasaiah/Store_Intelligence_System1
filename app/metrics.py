"""
metrics.py — Real-time store metric computation.

# PROMPT: Write retail analytics metric queries for unique visitors,
# conversion rate via POS correlation, avg dwell per zone, queue depth,
# abandonment rate. Exclude staff. Handle zero-purchase stores gracefully.
# CHANGES MADE: Used 5-minute billing zone window for POS correlation
# instead of simple count, added reentry_visitors field, used
# COUNT(DISTINCT visitor_id) to prevent session double-counting.
"""
from datetime import datetime, timezone
from app.database import get_db


def compute_conversion(store_id: str, conn) -> tuple[float, int, int]:
    """
    Visitor counts as converted if they were in BILLING_ZONE
    within 5 minutes before a POS transaction timestamp.
    """
    transactions = conn.execute(
        "SELECT timestamp FROM pos_transactions WHERE store_id=? ORDER BY timestamp",
        (store_id,)
    ).fetchall()

    converted = set()
    for txn in transactions:
        visitors = conn.execute(
            """
            SELECT DISTINCT visitor_id FROM events
            WHERE store_id=? AND zone_id='BILLING_ZONE' AND is_staff=0
              AND timestamp BETWEEN datetime(?, '-5 minutes') AND ?
            """,
            (store_id, txn["timestamp"], txn["timestamp"])
        ).fetchall()
        for v in visitors:
            converted.add(v["visitor_id"])

    total = conn.execute("""
        SELECT COUNT(DISTINCT visitor_id) FROM events
        WHERE store_id=? AND event_type IN ('ENTRY','REENTRY') AND is_staff=0
    """, (store_id,)).fetchone()[0] or 0

    rate = round(len(converted) / total, 4) if total > 0 else 0.0
    return rate, len(converted), total


def get_metrics(store_id: str) -> dict:
    conn = get_db()
    try:
        unique = conn.execute("""
            SELECT COUNT(DISTINCT visitor_id) FROM events
            WHERE store_id=? AND is_staff=0 AND event_type IN ('ENTRY','REENTRY')
        """, (store_id,)).fetchone()[0] or 0

        dwell_rows = conn.execute("""
            SELECT zone_id, AVG(dwell_ms) as avg_dwell,
                   COUNT(*) as visits, COUNT(DISTINCT visitor_id) as uniq
            FROM events WHERE store_id=? AND is_staff=0 AND zone_id IS NOT NULL
            GROUP BY zone_id
        """, (store_id,)).fetchall()

        avg_dwell = {r["zone_id"]: {
            "avg_dwell_ms": round(r["avg_dwell"], 1),
            "visit_count": r["visits"],
            "unique_visitors": r["uniq"]
        } for r in dwell_rows}

        queue = conn.execute("""
            SELECT queue_depth FROM events
            WHERE store_id=? AND zone_id='BILLING_ZONE' AND queue_depth IS NOT NULL
            ORDER BY timestamp DESC LIMIT 1
        """, (store_id,)).fetchone()

        abandon = conn.execute("""
            SELECT COUNT(*) FROM events
            WHERE store_id=? AND event_type='BILLING_QUEUE_ABANDON'
        """, (store_id,)).fetchone()[0] or 0

        joins = conn.execute("""
            SELECT COUNT(*) FROM events
            WHERE store_id=? AND event_type='BILLING_QUEUE_JOIN'
        """, (store_id,)).fetchone()[0] or 0

        pos = conn.execute(
            "SELECT COUNT(DISTINCT transaction_id) FROM pos_transactions WHERE store_id=?",
            (store_id,)
        ).fetchone()[0] or 0

        reentry = conn.execute("""
            SELECT COUNT(DISTINCT visitor_id) FROM events
            WHERE store_id=? AND event_type='REENTRY'
        """, (store_id,)).fetchone()[0] or 0

        conv_rate, converted, _ = compute_conversion(store_id, conn)
        conn.close()

        return {
            "store_id": store_id,
            "unique_visitors": unique,
            "reentry_visitors": reentry,
            "conversion_rate": conv_rate,
            "converted_visitors": converted,
            "avg_dwell_per_zone": avg_dwell,
            "queue_depth": queue["queue_depth"] if queue else 0,
            "abandonment_rate": round(abandon / joins, 4) if joins > 0 else 0.0,
            "pos_transactions": pos,
            "data_as_of": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        conn.close()
        raise e
