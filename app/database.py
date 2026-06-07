import sqlite3, os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "store_events.db"))
DB_PATH = os.path.abspath(DB_PATH)
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn
def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            event_id TEXT PRIMARY KEY, store_id TEXT NOT NULL,
            camera_id TEXT, visitor_id TEXT, event_type TEXT,
            timestamp TEXT, zone_id TEXT, dwell_ms INTEGER DEFAULT 0,
            is_staff INTEGER DEFAULT 0, confidence REAL,
            queue_depth INTEGER, sku_zone TEXT, session_seq INTEGER,
            inserted_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_store   ON events(store_id);
        CREATE INDEX IF NOT EXISTS idx_visitor ON events(visitor_id);
        CREATE INDEX IF NOT EXISTS idx_type    ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_ts      ON events(timestamp);
        CREATE TABLE IF NOT EXISTS pos_transactions (
            transaction_id TEXT PRIMARY KEY, store_id TEXT,
            timestamp TEXT, amount REAL, order_id TEXT
        );
    """)
    conn.commit(); conn.close()
    print("✅ Database initialized")
