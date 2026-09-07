"""
Dashboard Camera Card Component with Live Controls & Professional Styling
"""

import streamlit as st
from app.database.models import Camera
from app.components.status_badge import render_status_badge
from app.components.video_player import render_video_player
from app.services.stream_service import StreamService
from app.services.recording_service import RecordingService
from app.utils.rtsp import test_rtsp_connection, sanitize_rtsp_url
from app.utils.logging_config import get_logger

logger = get_logger("camera_card")

_WEBCAM_CHIP = (
    '<span style="display:inline-flex;align-items:center;gap:5px;font-size:10px;font-weight:600;letter-spacing:0.5px;'
    'background:rgba(34,197,94,0.1);color:#4ade80;border:1px solid rgba(34,197,94,0.3);padding:2px 8px;border-radius:4px;'
    'text-transform:uppercase;"><span style="display:inline-block;width:5px;height:5px;border-radius:50%;background:#22c55e;'
    'box-shadow:0 0 5px #22c55e;"></span>Local Webcam</span>'
)
_VIRTUAL_CHIP = (
    '<span style="display:inline-flex;align-items:center;gap:5px;font-size:10px;font-weight:600;letter-spacing:0.5px;'
    'background:rgba(56,189,248,0.08);color:#38bdf8;border:1px solid rgba(56,189,248,0.3);padding:2px 8px;border-radius:4px;'
    'text-transform:uppercase;"><span style="display:inline-block;width:5px;height:5px;border-radius:50%;background:#38bdf8;'
    'box-shadow:0 0 5px #38bdf8;"></span>Virtual Feed</span>'
)


def render_camera_card(camera: Camera):
    """Renders an isolated, interactive card for a single camera with professional icons and controls."""
    try:
        is_rec = RecordingService.is_recording(camera)
        is_webcam = camera.protocol == "WEBCAM" or "laptop_cam" in camera.rtsp_url or "laptop" in camera.name.lower() or "webcam" in camera.name.lower()
        is_simulated = not is_webcam and ("simulated" in camera.name.lower() or "simulated_cam" in camera.rtsp_url or "localhost:8554" in camera.rtsp_url or "mediamtx:8554" in camera.rtsp_url)

        with st.container(border=True):
            col_h1, col_h2 = st.columns([3, 1])
            with col_h1:
                chip = _WEBCAM_CHIP if is_webcam else (_VIRTUAL_CHIP if is_simulated else "")
                st.markdown(f"<div style='display:flex;align-items:center;gap:8px;'><span style='font-size:16px;font-weight:600;color:#f8fafc;'>{camera.name}</span>{chip}</div>", unsafe_allow_html=True)
                st.caption(f"Device: `{camera.ip_address}` • Protocol: `{camera.protocol}`")
            with col_h2:
                render_status_badge(camera.status, is_recording=is_rec)

            col_mode, col_res, col_focus = st.columns([1.8, 1.8, 1.2])
            with col_mode:
                if is_webcam:
                    st.caption("📷 Hardware Direct Stream")
                    player_mode = "webrtc"
                else:
                    player_mode = st.radio("Format", options=["webrtc", "hls"], format_func=lambda x: "WebRTC (Realtime)" if x == "webrtc" else "HLS (Buffered)", horizontal=True, key=f"mode_{camera.id}", label_visibility="collapsed")
            with col_res:
                if camera.sub_stream_url:
                    stream_choice = st.radio("Stream", options=["sub", "main"], format_func=lambda x: "⚡ Sub (720p)" if x == "sub" else "🌟 Main (HD)", horizontal=True, key=f"stream_res_{camera.id}", label_visibility="collapsed")
                else:
                    stream_choice = "main"
                    st.caption(" Main Stream (HD)")
            with col_focus:
                if st.button("Focus", icon=":material/fullscreen:", key=f"focus_btn_{camera.id}", use_container_width=True, help="Full-screen high-definition focus view with Main Stream"):
                    st.session_state["focused_camera_id"] = camera.id
                    st.rerun()

            render_video_player(camera, height=240, mode=player_mode, version=st.session_state.get("stream_version", 0), stream_type=stream_choice)

            col_b1, col_b2, col_b3 = st.columns(3)

            with col_b1:
                if is_webcam:
                    st.button("Webcam Ready", icon=":material/photo_camera:", key=f"test_{camera.id}", use_container_width=True, disabled=True)
                elif st.button("Probe", icon=":material/network_check:", key=f"test_{camera.id}", use_container_width=True, help="Probe RTSP reachability and codec metadata"):
                    with st.spinner("Probing stream..."):
                        success, message = test_rtsp_connection(camera.rtsp_url, timeout=5)
                        (st.success if success else st.error)(message)
                        st.toast(f"{camera.name}: {message}", icon=":material/check_circle:" if success else ":material/error:")

            with col_b2:
                if camera.status in ("ONLINE", "CONNECTING"):
                    if st.button("Stop Stream", icon=":material/stop_circle:", key=f"stop_{camera.id}", use_container_width=True):
                        success, msg = StreamService.stop_stream(camera)
                        if success:
                            st.toast(f"Stream stopped: {camera.name}", icon=":material/stop_circle:")
                            st.rerun()
                        else:
                            st.error(msg)
                elif st.button("Start Stream", icon=":material/play_circle:", key=f"start_{camera.id}", use_container_width=True):
                    with st.spinner("Starting stream..."):
                        success, msg = StreamService.start_stream(camera)
                        if success:
                            st.toast(f"Stream active: {camera.name}", icon=":material/play_circle:")
                            st.rerun()
                        else:
                            st.error(msg)

            with col_b3:
                if is_rec:
                    if st.button("Stop Rec", icon=":material/stop:", key=f"rec_stop_{camera.id}", use_container_width=True, type="primary"):
                        with st.spinner("Finalizing recording..."):
                            success, msg = RecordingService.stop_recording(camera)
                            if success:
                                st.toast(msg, icon=":material/check_circle:")
                                st.rerun()
                            else:
                                st.error(msg)
                elif st.button("Record", icon=":material/fiber_manual_record:", key=f"rec_start_{camera.id}", use_container_width=True):
                    with st.spinner("Launching FFmpeg recorder..."):
                        success, msg = RecordingService.start_recording(camera)
                        if success:
                            st.toast(msg, icon=":material/radio_button_checked:")
                            st.rerun()
                        else:
                            st.error(msg)

    except Exception as e:
        logger.error(f"Error rendering camera card for ID {getattr(camera, 'id', 'unknown')}: {e}")
        st.error(f"Failed to display camera card: {str(e)}")
