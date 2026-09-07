"""
System Health & Diagnostics Page with Professional Console Layout
"""

import streamlit as st
import subprocess
import requests

from app.database.database import engine
from app.database.models import Camera
from app.services.camera_service import CameraService
from app.services.health_service import HealthService
from app.services.stream_service import StreamService
from app.utils.config import settings

st.title("System Diagnostics")
st.caption("Real-time telemetry, service reachability, and camera connectivity matrix")

st.subheader("Core Infrastructure Services")
col_s1, col_s2, col_s3 = st.columns(3)

with col_s1:
    with st.container(border=True):
        st.markdown("#### Database • PostgreSQL")
        try:
            with engine.connect():
                st.success("Connected & Ready", icon=":material/check_circle:")
                db_display = settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL
                st.caption(f"Host: `{db_display}`")
        except Exception as e:
            st.error("Unreachable", icon=":material/error:")
            st.caption(f"Error: {e}")

with col_s2:
    with st.container(border=True):
        st.markdown("#### Media Gateway • MediaMTX")
        try:
            r = requests.get(f"{settings.MEDIAMTX_API_URL.rstrip('/')}/v3/paths/list", timeout=2)
            if r.status_code == 200:
                paths = r.json().get("items", [])
                st.success(f"Online ({len(paths)} active paths)", icon=":material/check_circle:")
                st.caption(f"API: `{settings.MEDIAMTX_API_URL}`")
            else:
                st.warning(f"Response: {r.status_code}", icon=":material/warning:")
        except Exception:
            st.error("Offline", icon=":material/error:")
            st.caption(f"API: `{settings.MEDIAMTX_API_URL}` unreachable")

with col_s3:
    with st.container(border=True):
        st.markdown("#### Video Engine • FFmpeg")
        try:
            p = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2)
            if p.returncode == 0:
                st.success("Operational", icon=":material/check_circle:")
                st.caption(f"`{(p.stdout.splitlines()[0] if p.stdout else 'FFmpeg ready')[:40]}...`")
            else:
                st.error("Execution failure", icon=":material/error:")
        except Exception:
            st.error("Not Detected", icon=":material/error:")
            st.caption("FFmpeg binary not found in PATH")

st.divider()

# 2. Camera Health Matrix
st.subheader("Camera Health & Reconnection Telemetry")

if st.columns([2, 4])[0].button("Run Diagnostic Scan", icon=":material/refresh:", type="primary", use_container_width=True):
    with st.spinner("Scanning cameras..."):
        HealthService.check_all()
        st.toast("Health telemetry updated.", icon=":material/check_circle:")
        st.rerun()

cameras = CameraService.get_all_cameras()
if not cameras:
    st.info("No registered cameras to monitor.")
else:
    STATUS_COLORS = {"ONLINE": "green", "CONNECTING": "orange", "OFFLINE": "gray", "ERROR": "red"}
    for cam in cameras:
        mtx_status = StreamService.get_stream_status(cam)
        retry_info = HealthService.get_retry_info(cam.id)
        with st.container(border=True):
            col_h1, col_h2, col_h3 = st.columns([3, 2, 2])
            with col_h1:
                st.markdown(f"**{cam.name}** (`{cam.ip_address}`)")
                st.caption(f"URL: `{cam.sanitized_rtsp_url()}`")
            with col_h2:
                st.markdown(f"Status: :{STATUS_COLORS.get(cam.status, 'gray')}[**{cam.status}**]")
                if cam.last_seen:
                    st.caption(f"Last Heartbeat: {cam.last_seen.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                if cam.last_error:
                    st.caption(f":red[{cam.last_error[:80]}]")
            with col_h3:
                st.markdown(f"**MediaMTX Pipeline**: `{'Ready' if mtx_status.get('ready') else 'Idle'}`")
                st.caption(f"Active Readers: `{mtx_status.get('readers', 0)}`")
                st.caption(f"Reconnect Count: `{retry_info['attempts']}/{HealthService.MAX_RETRIES}`")
