"""
Surveillance Platform - Main Streamlit Entrypoint
"""

import streamlit as st
import subprocess
import requests

from app.database.database import init_db, engine
from app.utils.config import settings
from app.utils.logging_config import get_logger

logger = get_logger("streamlit_app")

st.set_page_config(page_title="Argus Eye | Surveillance Platform", page_icon="📹", layout="wide", initial_sidebar_state="expanded")

# Custom Surveillance Theme Styling
st.markdown("""
<style>
    .stApp { background-color: #0b0f17; color: #e2e8f0; }
    div[data-testid="stMetric"] { background: #151d2c; border: 1px solid #1e293b; padding: 12px 16px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.3); }
    div[data-testid="stMetricValue"] { font-family: monospace; font-weight: 700; }
    div[data-testid="stVerticalBlockBorderWrapper"] { background: #111827; border-color: #1f2937; border-radius: 10px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4); }
    .stButton>button { border-radius: 6px; font-weight: 600; transition: all 0.2s ease; }
    section[data-testid="stSidebar"] { background-color: #0d131f; border-right: 1px solid #1e293b; }
</style>
""", unsafe_allow_html=True)

# Initialize database schema once on startup
@st.cache_resource
def setup_database():
    try:
        init_db()
        return True, None
    except Exception as e:
        return False, str(e)

db_ready, db_err = setup_database()
if not db_ready:
    st.sidebar.error(f"Database init error: {db_err}")

# System Health Probe for Sidebar (cached for 15s)
@st.cache_data(ttl=15)
def check_system_services():
    db_ok = False
    try:
        with engine.connect():
            db_ok = True
    except Exception:
        pass

    mtx_ok = False
    try:
        r = requests.get(f"{settings.MEDIAMTX_API_URL.rstrip('/')}/v3/paths/list", timeout=1.0)
        mtx_ok = (r.status_code == 200)
    except Exception:
        pass

    ffmpeg_ok = False
    try:
        p = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1.0)
        ffmpeg_ok = (p.returncode == 0)
    except Exception:
        pass

    return db_ok, mtx_ok, ffmpeg_ok

# Multipage Navigation
pg = st.navigation({"Surveillance Hub": [
    st.Page("pages/dashboard.py", title="Dashboard", icon=":material/dashboard:", default=True),
    st.Page("pages/cameras.py", title="Cameras", icon=":material/videocam:"),
    st.Page("pages/recordings.py", title="Recordings", icon=":material/video_library:"),
    st.Page("pages/system_health.py", title="System Health", icon=":material/monitor_heart:"),
]})

# Sidebar Footer with Live System Indicators
with st.sidebar:
    st.markdown("<div style='display:flex;align-items:center;gap:8px;'><span style='font-size:18px;font-weight:700;color:#f8fafc;'>Argus Eye</span></div>", unsafe_allow_html=True)
    st.caption("Real-Time IP Surveillance Platform")
    st.divider()

    db_ok, mtx_ok, ffmpeg_ok = check_system_services()
    st.markdown("#### System Telemetry")

    for name, ok in [("PostgreSQL", db_ok), ("MediaMTX Gateway", mtx_ok), ("FFmpeg Engine", ffmpeg_ok)]:
        dot = "#22c55e" if ok else "#ef4444"
        glow = "0 0 4px rgba(34,197,94,0.7)" if ok else "0 0 4px rgba(239,68,68,0.7)"
        st.markdown(f'''
        <div style="display:flex;justify-content:space-between;align-items:center;font-size:12px;padding:3px 0;color:#94a3b8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
            <span>{name}</span>
            <span style="display:inline-flex;align-items:center;gap:6px;color:#f1f5f9;font-weight:500;">
                <span style="display:inline-block;width:4.5px;height:4.5px;border-radius:50%;background:{dot};box-shadow:{glow};flex-shrink:0;"></span>
                {"Online" if ok else "Offline"}
            </span>
        </div>''', unsafe_allow_html=True)

    st.divider()
    st.caption("Active Ingestion Ports:")
    st.caption("RTSP: `8554` | WebRTC: `8889` | HLS: `8888`")

pg.run()
