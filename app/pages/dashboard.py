"""
Dashboard Page: Multi-Camera Live Grid, Real-Time Monitoring & Real Video Footage Studio
"""

import os
import time
import json
from pathlib import Path
import streamlit as st

from app.services.camera_service import CameraService
from app.services.recording_service import RecordingService
from app.services.stream_service import StreamService
from app.services.health_service import HealthService
from app.components.camera_card import render_camera_card
from app.components.video_player import render_video_player

st.title("Surveillance Dashboard")
st.caption("Real-time multi-camera CCTV monitoring, stream recording, and video simulation studio")

cameras = CameraService.get_all_cameras()
cleaned = False
for c in cameras:
    if c.rtsp_url.rstrip("/").endswith("/simulated_cam") or "default" in c.name.lower() or c.name == "Simulated Camera 01":
        CameraService.delete_camera(c.id)
        cleaned = True
if cleaned:
    cameras = CameraService.get_all_cameras()

SUPPORTED_EXTS = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".ts", ".m4v")
default_sample_dir = Path("sample_videos")
default_sample_dir.mkdir(parents=True, exist_ok=True)
config_file = default_sample_dir / "active_config.json"

current_config = {"mode": "broadcast_all", "selected_video": "security_footage.mp4", "stagger_offsets": True, "folder_path": "", "per_camera_map": {}}
if config_file.exists():
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            current_config.update(json.load(f))
    except Exception:
        pass

active_folder_path = default_sample_dir
custom_folder = current_config.get("folder_path", "").strip()
if custom_folder:
    p = Path(custom_folder)
    if p.exists() and p.is_dir():
        active_folder_path = p

valid_videos = sorted([f for f in active_folder_path.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS and f.stat().st_size > 10240], key=lambda x: x.name) if active_folder_path.exists() else []
video_filenames = [f.name for f in valid_videos]

curr_mode = current_config.get("mode", "broadcast_all")
curr_selected = current_config.get("selected_video", "")
curr_stagger = current_config.get("stagger_offsets", True)
is_synthetic = curr_mode == "synthetic"


def _save_config(cfg):
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def _start_sim_cameras():
    for c in cameras:
        if "simulated" in c.name.lower() and c.status != "ONLINE":
            StreamService.start_stream(c)


# Compute high-level metrics
total_cams = len(cameras)
online_cams = sum(1 for c in cameras if c.status == "ONLINE")
offline_cams = sum(1 for c in cameras if c.status == "OFFLINE")
connecting_cams = sum(1 for c in cameras if c.status == "CONNECTING")
active_recs = sum(1 for c in cameras if RecordingService.is_recording(c))

# Metrics Header Row
for col, (label, val) in zip(st.columns(5), [("Total Cameras", total_cams), ("Online Feeds", online_cams), ("Offline", offline_cams), ("Connecting", connecting_cams), ("Active Recordings", active_recs)]):
    with col:
        st.metric(label, val)

st.divider()

# Action Bar
col_act1, col_act2, col_act3, col_act4, col_act5 = st.columns([1.2, 1.2, 1.3, 2.0, 2.3])

with col_act1:
    if st.button("Start All", icon=":material/play_circle:", use_container_width=True):
        started = sum(1 for c in cameras if c.status != "ONLINE" and StreamService.start_stream(c)[0])
        st.toast(f"Started {started} stream(s)", icon=":material/play_circle:")
        st.rerun()

with col_act2:
    if st.button("Stop All", icon=":material/stop_circle:", use_container_width=True):
        stopped = sum(1 for c in cameras if c.status in ("ONLINE", "CONNECTING") and StreamService.stop_stream(c)[0])
        st.toast(f"Stopped {stopped} stream(s)", icon=":material/stop_circle:")
        st.rerun()

with col_act3:
    if st.button("Diagnostics", icon=":material/health_and_safety:", use_container_width=True):
        with st.spinner("Checking health across all cameras..."):
            results = HealthService.check_all()
            st.toast(f"Health check completed for {len(results)} cameras.", icon=":material/check_circle:")
            st.rerun()

with col_act4:
    sim_count = sum(1 for c in cameras if "simulated" in c.name.lower() or "simulated_cam" in c.rtsp_url)
    if sim_count < 5:
        btn_label = "Add 5 Simulation Cams" if sim_count == 0 else f"Add ({5 - sim_count}) Simulation Cams"
        if st.button(btn_label, icon=":material/videocam:", use_container_width=True, type="primary"):
            sim_specs = [
                ("CAM 01 • Front Entrance", "rtsp://localhost:8554/simulated_cam_1", "Main building gate entrance"),
                ("CAM 02 • Parking Lot", "rtsp://localhost:8554/simulated_cam_2", "Employee parking area"),
                ("CAM 03 • Warehouse Loading", "rtsp://localhost:8554/simulated_cam_3", "Cargo and freight loading dock"),
                ("CAM 04 • Perimeter Fence", "rtsp://localhost:8554/simulated_cam_4", "North outer perimeter boundary"),
                ("CAM 05 • Lobby Reception", "rtsp://localhost:8554/simulated_cam_5", "Main visitor lobby check-in desk"),
            ]
            existing_names = {c.name for c in cameras}
            added = 0
            for name, url, desc in sim_specs:
                if name not in existing_names:
                    cam, err = CameraService.create_camera(name=name, ip_address="127.0.0.1", rtsp_url=url, protocol="TCP", description=desc)
                    if cam:
                        StreamService.start_stream(cam)
                        added += 1
            st.toast(f"Added and initialized {added} simulation cameras.", icon=":material/check_circle:")
            st.rerun()
    else:
        st.button("5 Cameras Active", icon=":material/verified:", use_container_width=True, disabled=True)

with col_act5:
    if is_synthetic:
        if st.button("Switch to Real Video", icon=":material/movie:", type="primary", use_container_width=True, help="Switch all camera streams from synthetic test pattern to real downloaded local video footage"):
            current_config["mode"] = "broadcast_all"
            if not current_config.get("selected_video") or current_config["selected_video"] not in video_filenames:
                current_config["selected_video"] = video_filenames[0] if video_filenames else "security_footage.mp4"
            _save_config(current_config)
            st.session_state["stream_version"] = int(time.time() * 1000)
            if "studio_mode_radio" in st.session_state:
                st.session_state["studio_mode_radio"] = "broadcast_all"
            _start_sim_cameras()
            st.toast("Broadcasting Real Video Footage", icon=":material/check_circle:")
            st.rerun()
    else:
        if st.button("Switch to Color Bars", icon=":material/tune:", type="secondary", use_container_width=True, help="Switch all camera streams to SMPTE color bars & digital test pattern"):
            current_config["mode"] = "synthetic"
            _save_config(current_config)
            st.session_state["stream_version"] = int(time.time() * 1000)
            if "studio_mode_radio" in st.session_state:
                st.session_state["studio_mode_radio"] = "synthetic"
            _start_sim_cameras()
            st.toast("Switched to Synthetic Color Bars", icon=":material/tune:")
            st.rerun()

# --- Active Footage Status Banner ---
if curr_mode in ("broadcast_all", "single"):
    stagger_text = " • Multi-Angle Staggering Active (+0s, +10s, +20s, +30s, +40s)" if curr_stagger else " • Synchronous Loop"
    video_disp = curr_selected if curr_selected in video_filenames else (video_filenames[0] if video_filenames else "No Video")
    st.info(f"**Live Footage Active:** Broadcasting **`{video_disp}`** across **ALL 5 camera streams** ({len(valid_videos)} video(s) in `{active_folder_path.name}/`{stagger_text})", icon=":material/videocam:")
elif curr_mode == "distribute":
    st.info(f"**Live Footage Active:** Distributing **{len(video_filenames)} videos** across the 5 cameras from `{active_folder_path.name}/`.", icon=":material/shuffle:")
elif curr_mode == "per_camera":
    st.info("**Live Footage Active:** Custom per-camera video footage mapping is active.", icon=":material/camera_indoor:")
elif curr_mode == "synthetic":
    st.warning("**Synthetic Pattern Active:** Streams are currently displaying SMPTE color bars & test patterns.", icon=":material/tune:")

# Expandable Footage Studio
with st.expander("Video Footage Studio (Folder & Stream Broadcast Controls)", expanded=False):
    tab_broadcast, tab_folder, tab_upload = st.tabs(["Stream Broadcast Settings", "Video Folder Manager", "Upload Video"])

    with tab_broadcast:
        col_b1, col_b2 = st.columns([3, 2])
        with col_b1:
            st.markdown("#### Choose What to Broadcast into All Streams")
            mode_options = ["broadcast_all", "distribute", "per_camera", "synthetic"]
            mode_labels = {
                "broadcast_all": "Broadcast ONE downloaded video across ALL streams (Recommended)",
                "distribute": f"Distribute all {len(video_filenames)} folder videos across CAM 1 to CAM 5",
                "per_camera": "Assign a specific downloaded video to each individual camera",
                "synthetic": "Color bars & SMPTE test pattern (Fallback)",
            }
            mode_choice = st.radio("Streaming Mode", options=mode_options, index=mode_options.index(curr_mode) if curr_mode in mode_options else 0, format_func=lambda x: mode_labels.get(x, x), key="studio_mode_radio")

            selected_vid, stagger_choice = curr_selected, curr_stagger
            per_camera_map = current_config.get("per_camera_map", {})

            if mode_choice == "broadcast_all":
                if video_filenames:
                    def_idx = video_filenames.index(curr_selected) if curr_selected in video_filenames else 0
                    selected_vid = st.selectbox("Select Downloaded Video File to Broadcast to ALL Cameras:", video_filenames, index=def_idx, key="studio_selected_vid")
                    stagger_choice = st.checkbox("Enable Multi-Angle CCTV Simulation (Staggers start time by +10s per camera)", value=curr_stagger, help="Offsets camera start times so CAM 1 is at 0s, CAM 2 at 10s, CAM 3 at 20s, etc., making one video look like 5 distinct security camera angles.", key="studio_stagger_cb")
                else:
                    st.warning("No valid video files found in the active folder. Add or upload a video below!")
            elif mode_choice == "per_camera":
                st.markdown("**Select video for each camera:**")
                sim_cams = [c for c in cameras if "simulated" in c.name.lower()] or [type("Obj", (), {"name": f"simulated_cam_{i}"}) for i in range(1, 6)]
                for sc in sim_cams[:5]:
                    c_name = sc.name if hasattr(sc, "name") else str(sc)
                    curr_val = per_camera_map.get(c_name, video_filenames[0] if video_filenames else "")
                    idx = video_filenames.index(curr_val) if curr_val in video_filenames else 0
                    per_camera_map[c_name] = st.selectbox(f"{c_name}", video_filenames if video_filenames else ["(No videos)"], index=idx, key=f"cam_map_{c_name}")

            if st.button("Apply Broadcast Settings", icon=":material/send:", type="primary", use_container_width=True):
                _save_config({"mode": mode_choice, "selected_video": selected_vid, "stagger_offsets": stagger_choice, "folder_path": custom_folder, "per_camera_map": per_camera_map})
                _start_sim_cameras()
                st.toast("Stream mode applied! Feeds are reloading.", icon=":material/check_circle:")
                st.rerun()

        with col_b2:
            st.markdown("#### Available Footage in Folder")
            if valid_videos:
                for vf in valid_videos:
                    badge = " • Active" if vf.name == selected_vid and mode_choice == "broadcast_all" else ""
                    st.markdown(f"- `{vf.name}` ({vf.stat().st_size / (1024 * 1024):.1f} MB){badge}")
            else:
                st.info("No videos found. Upload a video file using the 'Upload Video' tab.")

    with tab_folder:
        st.markdown("#### Manage Video Source Folder")
        st.caption("By default, the platform reads video files from `./sample_videos/`. You can also enter any custom folder path on your computer:")
        folder_input = st.text_input("Custom Video Folder Path (e.g. C:\\Users\\...\\Downloads or /path/to/videos):", value=custom_folder, placeholder="Leave empty to use project sample_videos folder", key="custom_folder_input")

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            if st.button("Set Active Folder", icon=":material/folder_open:", use_container_width=True):
                target_p = Path(folder_input.strip()) if folder_input.strip() else default_sample_dir
                if folder_input.strip() and (not target_p.exists() or not target_p.is_dir()):
                    st.error(f"Directory does not exist: `{folder_input}`")
                else:
                    current_config["folder_path"] = folder_input.strip()
                    _save_config(current_config)
                    st.success(f"Active video folder updated to: `{target_p}`", icon=":material/check_circle:")
                    st.rerun()
        with col_f2:
            if st.button("Reset to Default Folder", icon=":material/refresh:", use_container_width=True):
                current_config["folder_path"] = ""
                _save_config(current_config)
                st.toast("Reset to default project folder `./sample_videos/`", icon=":material/check_circle:")
                st.rerun()

        st.markdown(f"**Current Resolved Folder:** `{active_folder_path.resolve()}`")
        st.caption(f"Detected **{len(valid_videos)}** supported video file(s).")

    with tab_upload:
        st.markdown("#### Upload a Video File")
        st.caption(f"Files uploaded here are saved directly into `{active_folder_path}`:")
        uploaded_file = st.file_uploader("Select Video File (.mp4, .mov, .mkv, .avi, .webm)", type=["mp4", "mov", "mkv", "avi", "webm"], key="dashboard_video_uploader")
        if uploaded_file is not None:
            dest_file = active_folder_path / uploaded_file.name
            with open(dest_file, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"Successfully uploaded `{uploaded_file.name}` ({uploaded_file.size / (1024*1024):.1f} MB) to `{active_folder_path.name}/`!", icon=":material/check_circle:")
            current_config["selected_video"] = uploaded_file.name
            _save_config(current_config)
            st.rerun()

st.divider()

focused_id = st.session_state.get("focused_camera_id")
focused_cam = next((c for c in cameras if c.id == focused_id), None) if focused_id else None

if focused_cam:
    col_back, col_title, col_ctrl = st.columns([1.5, 3.5, 2])
    with col_back:
        if st.button("← Back to Grid", icon=":material/grid_view:", use_container_width=True):
            st.session_state["focused_camera_id"] = None
            st.rerun()
    with col_title:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;'>"
            f"<span style='font-size:18px;font-weight:700;color:#f8fafc;'>🔍 Focus View: {focused_cam.name}</span>"
            f"<span style='font-size:11px;color:#10b981;font-weight:700;background:rgba(16,185,129,0.12);padding:3px 8px;border-radius:4px;border:1px solid rgba(16,185,129,0.3);letter-spacing:0.5px;'>🌟 MAIN STREAM (1080p/4MP)</span>"
            f"</div>",
            unsafe_allow_html=True
        )
    with col_ctrl:
        focus_fmt = st.radio("Format", options=["webrtc", "hls"], format_func=lambda x: "WebRTC (Realtime)" if x == "webrtc" else "HLS (Buffered)", horizontal=True, key="focus_fmt_radio", label_visibility="collapsed")

    with st.container(border=True):
        render_video_player(focused_cam, height=480, mode=focus_fmt, version=st.session_state.get("stream_version", 0), stream_type="main")

        col_d1, col_d2, col_d3 = st.columns([3, 2, 2])
        with col_d1:
            st.caption(f"**IP Address:** `{focused_cam.ip_address}` • **Protocol:** `{focused_cam.protocol}`")
            st.caption(f"**Main RTSP:** `{focused_cam.sanitized_rtsp_url()}`")
            if focused_cam.sub_stream_url:
                st.caption(f"**Sub RTSP:** `{focused_cam.sanitized_sub_stream_url()}`")
        with col_d2:
            st.caption(f"**Status:** `{focused_cam.status}`")
            if focused_cam.last_seen:
                st.caption(f"**Heartbeat:** `{focused_cam.last_seen.strftime('%Y-%m-%d %H:%M:%S UTC')}`")
        with col_d3:
            other_cams = [c for c in cameras if c.id != focused_cam.id]
            if other_cams:
                cam_map_opts = {f"{c.name}": c.id for c in other_cams}
                switch_target = st.selectbox("Quick Switch Camera:", list(cam_map_opts.keys()), key="switch_cam_focus_sel", label_visibility="collapsed")
                if st.button("Switch Camera", icon=":material/swap_horiz:", use_container_width=True):
                    st.session_state["focused_camera_id"] = cam_map_opts[switch_target]
                    st.rerun()

elif not cameras:
    st.info("No cameras registered yet. Click **Add 5 Simulation Cams** above or visit the **Cameras** page to register an RTSP camera.")
else:
    cols = st.columns(2)
    for idx, camera in enumerate(cameras):
        with cols[idx % 2]:
            render_camera_card(camera)

# Auto-refresh: silently reload dashboard every 10 seconds to keep metrics & streams live
import streamlit.components.v1 as components
components.html('<script>setTimeout(()=>window.parent.location.reload(),10000000)</script>', height=0)
