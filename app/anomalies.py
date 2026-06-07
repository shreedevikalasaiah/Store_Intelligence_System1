"""
anomalies.py — Operational anomaly detection.

# PROMPT: Write anomaly detection for a retail store API covering:
# queue spike (BILLING_QUEUE_SPIKE), dead zone (DEAD_ZONE no visits 30min),
# conversion drop (CONVERSION_DROP below 10%), re-entry rate anomaly,
# empty store returns no anomalies, severity values are valid.
# Each anomaly needs severity INFO/WARN/CRITICAL and suggested_action string.
# CHANGES MADE: Added HIGH_REENTRY_RATE anomaly, tuned queue thresholds
# (>5 = WARN, >10 = CRITICAL), used live compute_conversion for drop detection.
"""
from datetime import datetime, timezone
from app.database import get_db
from app.metrics import compute_conversion


def get_anomalies(store_id: str) -> dict:
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    anomalies = []

    # 1. Billing queue spike
    queue = conn.execute("""
        SELECT MAX(queue_depth) as max_q FROM events
        WHERE store_id=? AND zone_id='BILLING_ZONE'
    """, (store_id,)).fetchone()
    if queue and queue["max_q"] and queue["max_q"] > 5:
        anomalies.append({
            "anomaly_type":    "BILLING_QUEUE_SPIKE",
            "severity":        "CRITICAL" if queue["max_q"] > 10 else "WARN",
            "description":     f"Billing queue reached depth {queue['max_q']}",
            "suggested_action": "Open additional billing counter immediately",
            "detected_at":     now
        })

    # 2. Dead zone — no visits in 30 min
    dead = conn.execute("""
        SELECT zone_id, MAX(timestamp) as last_visit FROM events
        WHERE store_id=? AND zone_id IS NOT NULL AND is_staff=0
        GROUP BY zone_id
        HAVING last_visit < datetime('now', '-30 minutes')
    """, (store_id,)).fetchall()
    for z in dead:
        anomalies.append({
            "anomaly_type":    "DEAD_ZONE",
            "severity":        "INFO",
            "description":     f"No visitor activity in {z['zone_id']} for 30+ minutes",
            "suggested_action": "Check camera feed or run zone promotion",
            "detected_at":     now
        })

    # 3. Conversion drop
    conv_rate, _, total = compute_conversion(store_id, conn)
    if conv_rate < 0.1 and total > 10:
        anomalies.append({
            "anomaly_type":    "CONVERSION_DROP",
            "severity":        "WARN",
            "description":     f"Conversion rate {conv_rate:.1%}% below 10% threshold",
            "suggested_action": "Review billing zone staffing and queue wait times",
            "detected_at":     now
        })

    # 4. High re-entry rate
    reentry = conn.execute("""
        SELECT COUNT(DISTINCT visitor_id) FROM events
        WHERE store_id=? AND event_type='REENTRY'
    """, (store_id,)).fetchone()[0] or 0
    if reentry > 5:
        anomalies.append({
            "anomaly_type":    "HIGH_REENTRY_RATE",
            "severity":        "INFO",
            "description":     f"{reentry} visitors re-entered the store",
            "suggested_action": "Investigate — may indicate fitting room or exit confusion",
            "detected_at":     now
        })

    conn.close()
    return {"store_id": store_id, "anomalies": anomalies, "checked_at": now}
