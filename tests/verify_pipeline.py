"""
End-to-End Pipeline Verification Script

Tests the complete workflow against the running system:
1. Database Camera Creation
2. RTSP Connection Probing
3. MediaMTX Stream Ingestion & Status
4. FFmpeg Subprocess Recording (-c copy)
5. Recorded File Inspection
6. Health Monitoring
"""

import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database.database import init_db
from app.database.models import Camera
from app.services.camera_service import CameraService
from app.services.stream_service import StreamService
from app.services.recording_service import RecordingService
from app.services.health_service import HealthService
from app.utils.rtsp import test_rtsp_connection, find_tool

def run_verification():
    print("=" * 60)
    print("1. INITIALIZING DATABASE")
    print("=" * 60)
    init_db()
    print(" Database tables initialized.")

    import os
    from app.utils.config import settings
    # Detect if running in Docker container or on host
    mediamtx_host = "mediamtx" if "mediamtx" in settings.MEDIAMTX_API_URL else "localhost"
    sim_url = f"rtsp://{mediamtx_host}:8554/simulated_cam_1"
    print(f"Target RTSP URL: {sim_url}")
    ok, msg = test_rtsp_connection(sim_url, timeout=5)
    print(f"RTSP Probe Result: {' SUCCESS' if ok else ' FAILED'}")
    print(f"Details: {msg}")
    assert ok, f"RTSP connection test failed: {msg}"

    print("\n" + "=" * 60)
    print("3. REGISTERING CAMERA IN DATABASE")
    print("=" * 60)
    # Check if already exists
    existing = [c for c in CameraService.get_all_cameras() if c.name == "Simulated Camera 01"]
    if existing:
        cam = existing[0]
        print(f"Camera already registered: ID={cam.id}, Name='{cam.name}'")
    else:
        cam, err = CameraService.create_camera(
            name="Simulated Camera 01",
            ip_address="127.0.0.1",
            rtsp_url=sim_url,
            protocol="TCP",
            description="Synthetic camera feed for automated testing",
        )
        assert cam is not None, f"Failed to create camera: {err}"
        print(f" Created Camera: ID={cam.id}, Name='{cam.name}', Status={cam.status}")

    print("\n" + "=" * 60)
    print("4. STARTING STREAM IN MEDIAMTX")
    print("=" * 60)
    start_ok, start_msg = StreamService.start_stream(cam)
    print(f"Start Stream Result: {start_ok} | Message: {start_msg}")
    
    # Check stream status in MediaMTX
    time.sleep(1)
    status_info = StreamService.get_stream_status(cam)
    print(f"MediaMTX Stream Telemetry: {status_info}")
    
    urls = StreamService.get_stream_urls(cam)
    print(f"WebRTC WHEP URL: {urls['webrtc_whep']}")
    print(f"HLS Stream URL:  {urls['hls']}")

    print("\n" + "=" * 60)
    print("5. TESTING HEALTH SERVICE")
    print("=" * 60)
    health_status, health_err = HealthService.check_camera_health(cam)
    print(f"Camera Health Status: {health_status} (Error: {health_err})")
    assert health_status == "ONLINE", f"Expected ONLINE, got {health_status}"

    print("\n" + "=" * 60)
    print("6. TESTING FFMPEG RECORDING SERVICE")
    print("=" * 60)
    rec_ok, rec_msg = RecordingService.start_recording(cam)
    print(f"Recording Start Result: {rec_ok} | Message: {rec_msg}")
    assert rec_ok, f"Failed to start recording: {rec_msg}"

    print("Recording active... capturing 4 seconds of video...")
    time.sleep(4)

    assert RecordingService.is_recording(cam), "Recording process terminated prematurely!"
    rec_info = RecordingService.get_active_recording_info(cam.id)
    print(f"Active Recording Info: {rec_info}")

    print("Stopping recording...")
    stop_ok, stop_msg = RecordingService.stop_recording(cam)
    print(f"Recording Stop Result: {stop_ok} | Message: {stop_msg}")
    assert stop_ok, f"Failed to stop recording: {stop_msg}"

    print("\n" + "=" * 60)
    print("7. VERIFYING RECORDED MP4 FILE")
    print("=" * 60)
    recordings = RecordingService.list_all_recordings()
    print(f"Found {len(recordings)} saved recording(s):")
    for r in recordings:
        print(f" - [{r['date']}] {r['filename']} ({r['size_mb']} MB) at {r['path']}")
    
    assert len(recordings) > 0, "No recordings were saved!"
    latest_rec = recordings[0]
    assert latest_rec["size_mb"] > 0, "Recorded file is empty (0 MB)!"
    print(f" Verified: Latest recording '{latest_rec['filename']}' is {latest_rec['size_mb']} MB.")

    print("\n" + "=" * 60)
    print("ALL PIPELINE VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_verification()
