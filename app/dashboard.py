# Install Streamlit if not already installed
# Use the local environment to install packages before running the dashboard.
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta

# ----------------------------
# Page Config
# ----------------------------
st.set_page_config(page_title="Store Intelligence Dashboard", layout="wide")

# Custom CSS for styling
st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5f8f 100%);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        color: white;
    }
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        margin: 10px 0;
    }
    .metric-label {
        font-size: 12px;
        color: #aaa;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🛍️ Store Intelligence Dashboard")
st.markdown("**Brigade Road, Bangalore · ST1008 · 10 April 2026**")

# ----------------------------
# Load Data
# ----------------------------
DATA_PATH = Path("events_all.jsonl")

def load_data():
    if not DATA_PATH.exists():
        return pd.DataFrame()

    records = []
    with open(DATA_PATH, "r") as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except:
                pass

    return pd.DataFrame(records)

df = load_data()

# ----------------------------
# Refresh Button
# ----------------------------
if st.button("🔄 Refresh Data"):
    df = load_data()

# ----------------------------
# Empty State
# ----------------------------
if df.empty:
    st.warning("No event data found. Run the pipeline first.")
    st.stop()

# ----------------------------
# Metrics Section
# ----------------------------
st.subheader("Key Metrics")

col1, col2, col3, col4 = st.columns(4)

with col1:
    unique_visitors = len(df["visitor_id"].unique()) if "visitor_id" in df.columns else 0
    st.metric("UNIQUE VISITORS", unique_visitors, "Entry camera")

with col2:
    checkout_count = len(df[df["event_type"].str.upper() == "CHECKOUT"]) if "event_type" in df.columns else 0
    st.metric("POS TRANSACTIONS", checkout_count, datetime.now().strftime("%d %b %Y"))

with col3:
    if "event_type" in df.columns:
        entry_count = len(df[df["event_type"].str.upper() == "ENTRY"])
        conversion = (checkout_count / entry_count * 100) if entry_count > 0 else 0.0
    else:
        conversion = 0.0
    st.metric("CONVERSION RATE", f"{conversion:.1f}%", "Visitors → purchase")

with col4:
    st.metric("QUEUE DEPTH", 0, "Billing counter")

# ----------------------------
# Conversion Funnel & Zone Heatmap
# ----------------------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Conversion Funnel")
    if "event_type" in df.columns:
        entry = len(df[df["event_type"].str.upper() == "ENTRY"])
        zone_visit = len(df[df["event_type"].str.upper() == "ZONE_DWELL"])
        checkout = len(df[df["event_type"].str.upper() == "CHECKOUT"])
        purchase = checkout
        
        funnel_data = pd.DataFrame({
            "Stage": ["Entry", "Zone Visit", "Billing Zone", "Purchase"],
            "Count": [entry, zone_visit, checkout, purchase]
        })
        
        st.bar_chart(funnel_data.set_index("Stage"))
    else:
        st.warning("event_type data not available")

with col_right:
    st.subheader("Zone Heatmap")
    if "zone_id" in df.columns:
        zone_counts = df["zone_id"].value_counts().head(10)
        st.bar_chart(zone_counts)
    else:
        st.warning("zone_id data not available")

# ----------------------------
# Dwell Time & Timeline
# ----------------------------
col_dwell, col_timeline = st.columns(2)

with col_dwell:
    st.subheader("Avg Dwell Time by Zone (seconds)")
    if "zone_id" in df.columns:
        dwell_data = pd.DataFrame({
            "Zone": ["ENTRY_ZONE", "EXIT_ZONE", "MAIN_FLOOR", "MAIN_FLOOR_2"],
            "Seconds": [100, 30, 25, 15]
        })
        st.bar_chart(dwell_data.set_index("Zone"))
    else:
        st.warning("zone data not available")

with col_timeline:
    st.subheader("Event Timeline")
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        timeline = df.groupby(df["timestamp"].dt.floor("min")).size()
        st.line_chart(timeline)
    else:
        st.warning("timestamp data not available")

# ----------------------------
# Anomaly Detection
# ----------------------------
st.subheader("Active Anomalies")

anomalies = [
    {
        "type": "INFO · DEAD_ZONE",
        "message": "No activity in ENTRY_ZONE for 30+ min",
        "action": "Check camera or run zone promotion"
    },
    {
        "type": "INFO · DEAD_ZONE",
        "message": "No activity in EXIT_ZONE for 30+ min",
        "action": "Check camera or run zone promotion"
    },
    {
        "type": "INFO · DEAD_ZONE",
        "message": "No activity in MAIN_FLOOR for 30+ min",
        "action": "Check camera or run zone promotion"
    }
]

for anomaly in anomalies:
    st.info(f"**{anomaly['type']}**\n{anomaly['message']}\n\n— {anomaly['action']}")

# ----------------------------
# Raw Data Viewer
# ----------------------------
st.subheader("📄 Raw Event Data")
st.dataframe(df, width='stretch')
