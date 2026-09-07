"""
Unit Tests: Camera Health Monitoring & Reconnection
"""

import pytest
from unittest.mock import patch, MagicMock
from app.database.models import Camera
from app.services.health_service import HealthService
from app.services.camera_service import CameraService

@pytest.fixture(autouse=True)
def reset_health_state():
    """Resets in-memory retry state before each test."""
    HealthService._RETRY_STATE.clear()


@patch("app.services.health_service.check_socket_reachable")
@patch("app.services.stream_service.StreamService.get_stream_status")
@patch("app.services.camera_service.CameraService.update_status")
def test_camera_health_online(mock_update_status, mock_stream_status, mock_socket):
    mock_socket.return_value = (True, "Port open")
    mock_stream_status.return_value = {"active": True, "ready": True}

    camera = Camera(id=1, name="Entrance", ip_address="192.168.1.50", rtsp_url="rtsp://192.168.1.50/live", status="ONLINE")
    
    status, err = HealthService.check_camera_health(camera)
    assert status == "ONLINE"
    assert err is None
    mock_update_status.assert_called_with(1, "ONLINE")


@patch("app.services.health_service.check_socket_reachable")
@patch("app.services.camera_service.CameraService.update_status")
@patch("app.services.stream_service.StreamService.reconnect_stream")
def test_camera_health_connection_loss_and_reconnect(mock_reconnect, mock_update_status, mock_socket):
    # Simulate network down
    mock_socket.return_value = (False, "Connection refused")
    mock_reconnect.return_value = (False, "Camera still offline")

    camera = Camera(id=2, name="Backyard", ip_address="192.168.1.60", rtsp_url="rtsp://192.168.1.60/live", status="ONLINE")

    # First check: detects loss, enters CONNECTING
    status1, _ = HealthService.check_camera_health(camera)
    assert status1 == "CONNECTING"

    retry_info = HealthService.get_retry_info(2)
    assert retry_info["attempts"] == 1


@patch("app.services.health_service.check_socket_reachable")
@patch("app.services.camera_service.CameraService.update_status")
def test_camera_health_max_retries_exceeded(mock_update_status, mock_socket):
    mock_socket.return_value = (False, "Host unreachable")

    camera = Camera(id=3, name="Roof", ip_address="192.168.1.70", rtsp_url="rtsp://192.168.1.70/live", status="OFFLINE")

    # Manually simulate max retries reached
    state = HealthService.get_retry_info(3)
    state["attempts"] = HealthService.MAX_RETRIES

    status, err = HealthService.check_camera_health(camera)
    assert status == "ERROR"
    assert "maximum reconnect attempts" in err.lower()
    mock_update_status.assert_called_with(3, "ERROR", last_error=err)
