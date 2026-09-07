"""
Unit Tests: Stream Service & RTSP Connection Testing
"""

import pytest
import subprocess
from unittest.mock import patch, MagicMock
from app.database.models import Camera
from app.services.stream_service import StreamService
from app.utils.rtsp import test_rtsp_connection as probe_rtsp, sanitize_rtsp_url, build_rtsp_url

# ==============================================================================
# 1. STREAM SERVICE TESTS (UNIT TESTS WITH MOCKS)
# ==============================================================================

def test_stream_urls_generation():
    camera = Camera(id=1, name="Test Cam", ip_address="192.168.1.50", rtsp_url="rtsp://192.168.1.50/live", protocol="TCP")
    urls = StreamService.get_stream_urls(camera)
    
    assert "cam_1" in urls["webrtc"]
    assert "8889" in urls["webrtc"]
    assert "cam_1" in urls["hls"]
    assert "8888" in urls["hls"]
    assert "index.m3u8" in urls["hls_playlist"]
    assert "8554" in urls["rtsp_proxy"]


@patch("app.services.stream_service.requests.post")
@patch("app.services.camera_service.CameraService.update_status")
def test_start_stream_success(mock_update_status, mock_post):
    mock_post.return_value = MagicMock(status_code=201, text="ok")
    camera = Camera(id=2, name="Cam 2", ip_address="10.0.0.2", rtsp_url="rtsp://10.0.0.2/stream", protocol="TCP")

    success, msg = StreamService.start_stream(camera)
    assert success is True
    assert "started successfully" in msg.lower()
    mock_update_status.assert_called_with(2, "ONLINE")


@patch("app.services.stream_service.requests.delete")
@patch("app.services.camera_service.CameraService.update_status")
def test_stop_stream_success(mock_update_status, mock_delete):
    mock_delete.return_value = MagicMock(status_code=200, text="deleted")
    camera = Camera(id=3, name="Cam 3", ip_address="10.0.0.3", rtsp_url="rtsp://10.0.0.3/stream", protocol="TCP")

    success, msg = StreamService.stop_stream(camera)
    assert success is True
    mock_update_status.assert_called_with(3, "OFFLINE")


# ==============================================================================
# 2. RTSP UTILITY & CONNECTION TESTS
# ==============================================================================

def test_sanitize_rtsp_url():
    raw_url = "rtsp://admin:SecretPass123@192.168.1.100:554/stream1"
    sanitized = sanitize_rtsp_url(raw_url)
    assert "SecretPass123" not in sanitized
    assert "admin:***@" in sanitized


def test_build_rtsp_url():
    url = build_rtsp_url("192.168.1.50", 554, "stream1", "user", "pass")
    assert url == "rtsp://user:pass@192.168.1.50:554/stream1"


def test_rtsp_invalid_url():
    ok, msg = probe_rtsp("http://not-an-rtsp-stream.com")
    assert ok is False
    assert "must start with 'rtsp://'" in msg.lower()


def test_rtsp_unreachable_camera():
    # Attempt connecting to non-existent reserved IP
    ok, msg = probe_rtsp("rtsp://192.0.2.1:554/stream1", timeout=1)
    assert ok is False
    assert "unreachable" in msg.lower() or "timeout" in msg.lower()


@patch("app.utils.rtsp.check_socket_reachable")
@patch("app.utils.rtsp.subprocess.run")
def test_rtsp_probe_timeout(mock_subproc, mock_socket):
    mock_socket.return_value = (True, "Port open")
    mock_subproc.side_effect = subprocess.TimeoutExpired(cmd="ffprobe", timeout=2)

    ok, msg = probe_rtsp("rtsp://192.168.1.10:554/stream1", timeout=2)
    assert ok is False
    assert "timed out" in msg.lower()
