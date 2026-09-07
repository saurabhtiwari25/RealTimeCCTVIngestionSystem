"""
Camera Management Page: Add, Edit, Delete, and Test RTSP Cameras with Professional UI
"""

import streamlit as st
from app.services.camera_service import CameraService
from app.services.stream_service import StreamService
from app.services.health_service import HealthService
from app.utils.rtsp import test_rtsp_connection, build_rtsp_url, sanitize_rtsp_url

st.title("Camera Management")
st.caption("Register, configure, test, and manage IP surveillance cameras")

tab_list, tab_add, tab_edit = st.tabs(["Active Directory", "Register Camera", "Edit Configuration"])

with tab_list:
    cameras = CameraService.get_all_cameras()
    if not cameras:
        st.info("No cameras found. Add your first camera using the 'Register Camera' tab.")
    else:
        for cam in cameras:
            with st.container(border=True):
                col_c1, col_c2, col_c3 = st.columns([3, 2, 2.2])
                with col_c1:
                    is_sim = "simulated" in cam.name.lower() or "simulated_cam" in cam.rtsp_url or "localhost:8554" in cam.rtsp_url or "mediamtx:8554" in cam.rtsp_url
                    chip = ' <span style="display:inline-flex;align-items:center;gap:4px;font-size:10px;font-weight:600;letter-spacing:0.5px;background:rgba(56,189,248,0.08);color:#38bdf8;border:1px solid rgba(56,189,248,0.3);padding:1px 6px;border-radius:3px;text-transform:uppercase;"><span style="display:inline-block;width:4px;height:4px;border-radius:50%;background:#38bdf8;"></span>Virtual</span>' if is_sim else ""
                    st.markdown(f"<div style='display:flex;align-items:center;gap:6px;'><span style='font-size:15px;font-weight:600;color:#f8fafc;'>{cam.name}</span><span style='color:#64748b;font-size:12px;'>(ID: {cam.id})</span>{chip}</div>", unsafe_allow_html=True)
                    st.caption(f"**IP**: `{cam.ip_address}` • **Protocol**: `{cam.protocol}`")
                    st.markdown(f"**Main Stream** (1080p/4MP):")
                    st.code(cam.sanitized_rtsp_url(), language="bash")
                    if cam.sub_stream_url:
                        st.markdown(f"**Sub-Stream** (720p/D1 - Grid):")
                        st.code(cam.sanitized_sub_stream_url(), language="bash")
                    if cam.description:
                        st.caption(f"*{cam.description}*")
                with col_c2:
                    st.markdown(f"**Status**: `{cam.status}`")
                    if cam.last_seen:
                        st.caption(f"Last Heartbeat: {cam.last_seen.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    if cam.last_error:
                        st.caption(f":red[Error: {cam.last_error[:100]}]")
                with col_c3:
                    b_col1, b_col2 = st.columns(2)
                    with b_col1:
                        if st.button("Probe", icon=":material/network_check:", key=f"tbl_test_{cam.id}", use_container_width=True):
                            with st.spinner("Testing reachability..."):
                                ok, msg = test_rtsp_connection(cam.rtsp_url, timeout=5)
                                (st.success if ok else st.error)(msg, icon=":material/check_circle:" if ok else ":material/error:")
                    with b_col2:
                        if cam.status == "ONLINE":
                            if st.button("Stop", icon=":material/stop_circle:", key=f"tbl_stop_{cam.id}", use_container_width=True):
                                StreamService.stop_stream(cam)
                                st.rerun()
                        elif st.button("Start", icon=":material/play_circle:", key=f"tbl_start_{cam.id}", use_container_width=True):
                            StreamService.start_stream(cam)
                            st.rerun()
                    if st.button("Delete", icon=":material/delete:", key=f"tbl_del_{cam.id}", use_container_width=True):
                        StreamService.stop_stream(cam)
                        CameraService.delete_camera(cam.id)
                        st.toast(f"Deleted camera: {cam.name}", icon=":material/delete:")
                        st.rerun()

with tab_add:
    st.subheader("Add New IP Camera")
    st.caption("Provide connection parameters for the surveillance camera.")

    with st.form("add_camera_form", clear_on_submit=False):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            name = st.text_input("Camera Name *", placeholder="e.g. Front Gate Camera")
            ip_address = st.text_input("IP Address or Hostname *", placeholder="e.g. 192.168.1.100")
            protocol = st.selectbox("Transport Protocol", ["TCP", "UDP"], help="TCP is recommended for reliability over RTSP")
            description = st.text_area("Description (Optional)", placeholder="Location, camera model, lens angle, etc.")
        with col_f2:
            username = st.text_input("Username (Optional)", placeholder="e.g. admin")
            password = st.text_input("Password (Optional)", type="password", placeholder="Camera password")
            rtsp_url = st.text_input("Main RTSP URL * (Full Resolution)", placeholder="rtsp://admin:password@192.168.1.100:554/stream1", help="Direct RTSP URL or generated from parameters above.")
            sub_stream_url = st.text_input("Sub-Stream RTSP URL (Optional)", placeholder="rtsp://admin:password@192.168.1.100:554/stream2", help="Lower-res stream (720p/D1) used for multi-camera grid view to save bandwidth.")

        st.caption("💡 **Sub-stream paths by brand**: Hikvision / Sparsh (`/Streaming/Channels/102`), CP Plus / Dahua (`/cam/realmonitor?channel=1&subtype=1`), Honeywell (`/h264/ch1/sub/av_stream`).")

        col_sub1, col_sub2 = st.columns(2)
        with col_sub1:
            test_first = st.form_submit_button("Test Connection", icon=":material/network_check:", use_container_width=True)
        with col_sub2:
            submit = st.form_submit_button("Register Camera", icon=":material/add_circle:", type="primary", use_container_width=True)

    def _get_effective_url():
        url = rtsp_url.strip()
        if not url and ip_address:
            url = build_rtsp_url(ip_address, 554, "/stream1", username, password)
        return url

    if test_first:
        effective_url = _get_effective_url()
        if not effective_url:
            st.error("Please enter an RTSP URL or IP address to test.")
        else:
            with st.spinner(f"Testing connection to {sanitize_rtsp_url(effective_url)}..."):
                ok, msg = test_rtsp_connection(effective_url, timeout=6)
                (st.success if ok else st.error)(msg, icon=":material/check_circle:" if ok else ":material/error:")

    if submit:
        cam, err = CameraService.create_camera(
            name=name,
            ip_address=ip_address,
            rtsp_url=_get_effective_url(),
            sub_stream_url=sub_stream_url.strip() if sub_stream_url and sub_stream_url.strip() else None,
            username=username,
            password=password,
            protocol=protocol,
            description=description
        )
        if cam:
            st.success(f"Camera '{cam.name}' successfully registered!", icon=":material/check_circle:")
            st.rerun()
        else:
            st.error(f"Failed to add camera: {err}", icon=":material/error:")

# TAB 3: EDIT CAMERA
with tab_edit:
    st.subheader("Edit Existing Camera")
    cameras = CameraService.get_all_cameras()
    if not cameras:
        st.info("No cameras to edit.")
    else:
        cam_map = {f"{c.name} (ID: {c.id})": c for c in cameras}
        selected_cam = cam_map[st.selectbox("Select Camera to Edit", list(cam_map.keys()))]

        with st.form(f"edit_form_{selected_cam.id}"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                edit_name = st.text_input("Camera Name", value=selected_cam.name)
                edit_ip = st.text_input("IP Address", value=selected_cam.ip_address)
                edit_proto = st.selectbox("Protocol", ["TCP", "UDP"], index=0 if selected_cam.protocol == "TCP" else 1)
                edit_desc = st.text_area("Description", value=selected_cam.description or "")
            with col_e2:
                edit_user = st.text_input("Username", value=selected_cam.username or "")
                edit_pass = st.text_input("Password", type="password", placeholder="Leave blank to keep current password")
                edit_url = st.text_input("Main RTSP Stream URL", value=selected_cam.rtsp_url)
                edit_sub_url = st.text_input("Sub-Stream RTSP URL (Optional)", value=selected_cam.sub_stream_url or "")

            if st.form_submit_button("Save Changes", icon=":material/save:", type="primary"):
                updated, err = CameraService.update_camera(
                    camera_id=selected_cam.id,
                    name=edit_name,
                    ip_address=edit_ip,
                    rtsp_url=edit_url,
                    sub_stream_url=edit_sub_url.strip() if edit_sub_url and edit_sub_url.strip() else None,
                    username=edit_user,
                    password=edit_pass if edit_pass else selected_cam.password,
                    protocol=edit_proto,
                    description=edit_desc
                )
                if updated:
                    st.success(f"Updated '{updated.name}' successfully!", icon=":material/check_circle:")
                    st.rerun()
                else:
                    st.error(f"Update failed: {err}", icon=":material/error:")
