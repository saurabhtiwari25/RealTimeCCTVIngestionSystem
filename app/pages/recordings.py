"""
Recordings Page: List, Playback, and Download Recorded Streams with Professional UI
"""

import shutil
import streamlit as st
from pathlib import Path
from app.services.recording_service import RecordingService
from app.services.camera_service import CameraService
from app.utils.config import settings

st.title("Camera Recordings")
st.caption("Browse, preview, and download locally stored MP4 surveillance archives")

recordings_dir = RecordingService.get_recordings_dir()
recordings = RecordingService.list_all_recordings()

try:
    total_disk, _, free_disk = shutil.disk_usage(recordings_dir)
    archive_bytes = RecordingService.get_archive_size_bytes()
    col_d1, col_d2, col_d3, col_d4 = st.columns([1.5, 1.5, 1, 2])
    col_d1.metric("Archive Size", f"{archive_bytes / (1024**3):.2f} GB" if archive_bytes > 1024**3 else f"{archive_bytes / (1024**2):.1f} MB")
    col_d2.metric("Disk Free", f"{free_disk / (1024**3):.1f} GB")
    col_d3.metric("Total Recordings", len(recordings))
    with col_d4:
        st.caption("Retention Policy")
        rc1, rc2 = st.columns([1, 1])
        max_days = rc1.number_input("Max age (days)", min_value=1, value=30, step=1, key="retention_days", label_visibility="collapsed")
        if rc2.button("Clean Up", icon=":material/auto_delete:", use_container_width=True, help=f"Delete all recordings older than {max_days} days"):
            deleted = RecordingService.cleanup_old_recordings(max_age_days=int(max_days))
            if deleted:
                st.toast(f"Cleaned up {deleted} old recording(s)", icon=":material/auto_delete:")
                st.rerun()
            else:
                st.toast("No recordings older than threshold found", icon=":material/check_circle:")
except Exception:
    pass

st.divider()


cameras = CameraService.get_all_cameras()
cam_map = {c.id: c.name for c in cameras}

active_recordings = [(c, RecordingService.get_active_recording_info(c.id)) for c in cameras if RecordingService.is_recording(c)]
active_recordings = [(c, info) for c, info in active_recordings if info]

if active_recordings:
    st.subheader("Active Recordings")
    for cam, info in active_recordings:
        with st.container(border=True):
            col_a1, col_a2, col_a3 = st.columns([3, 2, 2])
            with col_a1:
                st.markdown(f"**Camera**: `{cam.name}`")
                st.caption(f"Destination: `{Path(info['filepath']).name}`")
            with col_a2:
                mins, secs = divmod(info.get("elapsed_seconds", 0), 60)
                st.markdown(f"**Duration**: `{mins:02d}:{secs:02d}`")
            with col_a3:
                if st.button("Stop Recording", icon=":material/stop:", key=f"stop_rec_page_{cam.id}", type="primary"):
                    RecordingService.stop_recording(cam)
                    st.toast("Recording finalized", icon=":material/check_circle:")
                    st.rerun()
    st.divider()

# Stored Recordings List
st.subheader("Saved Archive")

if not recordings:
    st.info("No recordings found in the archive directory.")
else:
    for idx, rec in enumerate(recordings):
        cam_name = cam_map.get(rec.get("camera_id"), f"Camera {rec.get('camera_id')}" if rec.get("camera_id") else "Unknown")
        filepath = rec.get("path")

        with st.container(border=True):
            col_r1, col_r2, col_r3 = st.columns([3, 2, 2.4])
            with col_r1:
                st.markdown(f"**{cam_name}**")
                st.caption(f"File: `{rec['filename']}` • {rec['size_mb']} MB")
                st.caption(f"Date: `{rec['date']}`")
            with col_r2:
                st.caption(f"Created: {rec['modified_at']}")
            with col_r3:
                c_btn1, c_btn2, c_btn3 = st.columns(3)
                play_key = f"play_{idx}_{rec['filename']}"
                with c_btn1:
                    is_playing = st.button("Play", icon=":material/play_circle:", key=play_key, use_container_width=True)
                with c_btn2:
                    # Improvement #3: Stream file instead of loading entire video into RAM
                    try:
                        st.download_button(label="Export", icon=":material/download:", data=open(filepath, "rb"), file_name=rec['filename'], mime="video/mp4", key=f"dl_{idx}_{rec['filename']}", use_container_width=True)
                    except Exception as e:
                        st.error(f"Error reading file: {e}")
                with c_btn3:
                    if st.button("Delete", icon=":material/delete:", key=f"del_{idx}_{rec['filename']}", use_container_width=True):
                        RecordingService.delete_recording(filepath)
                        st.toast(f"Deleted {rec['filename']}", icon=":material/delete:")
                        st.rerun()

            if st.session_state.get(play_key, False) or is_playing:
                st.video(filepath)
