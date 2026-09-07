"""
Unit Tests: FFmpeg Recording Service
"""

import os
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from app.database.models import Camera
from app.services.recording_service import RecordingService

@pytest.fixture(autouse=True)
def clean_recordings_state(tmp_path, monkeypatch):
    """Sets a temporary directory for recordings during tests."""
    monkeypatch.setattr(RecordingService, "get_recordings_dir", classmethod(lambda cls: tmp_path))
    RecordingService._ACTIVE_RECORDINGS.clear()
    yield
    RecordingService._ACTIVE_RECORDINGS.clear()


def test_recording_directory_and_naming_structure(tmp_path):
    camera = Camera(id=5, name="Driveway", ip_address="192.168.1.5", rtsp_url="rtsp://192.168.1.5/stream", protocol="TCP")

    file1 = RecordingService.get_next_filename(camera.id)
    assert f"camera_{camera.id}" in str(file1)
    assert file1.name == "recording_001.mp4"

    # Simulate creation of file 1
    file1.touch()
    file2 = RecordingService.get_next_filename(camera.id)
    assert file2.name == "recording_002.mp4"


@patch("app.services.recording_service.subprocess.Popen")
def test_start_and_stop_recording_success(mock_popen):
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None  # Process running
    mock_proc.pid = 9999
    mock_popen.return_value = mock_proc

    camera = Camera(id=1, name="Front Door", ip_address="192.168.1.10", rtsp_url="rtsp://192.168.1.10/live", protocol="TCP")

    # Start recording
    success, msg = RecordingService.start_recording(camera)
    assert success is True
    assert "started" in msg.lower()
    assert RecordingService.is_recording(camera) is True

    # Starting again should be rejected
    success2, msg2 = RecordingService.start_recording(camera)
    assert success2 is False
    assert "already active" in msg2.lower()

    # Stop recording
    mock_proc.wait.return_value = 0
    stop_success, stop_msg = RecordingService.stop_recording(camera)
    assert stop_success is True
    assert "saved" in stop_msg.lower()
    assert RecordingService.is_recording(camera) is False


@patch("app.services.recording_service.subprocess.Popen")
def test_recording_process_immediate_failure(mock_popen):
    mock_proc = MagicMock()
    mock_proc.poll.return_value = 1  # Exited with error
    mock_proc.stderr.read.return_value = "Connection to RTSP server failed"
    mock_popen.return_value = mock_proc

    camera = Camera(id=2, name="Hallway", ip_address="192.168.1.20", rtsp_url="rtsp://192.168.1.20/live", protocol="TCP")

    success, msg = RecordingService.start_recording(camera)
    assert success is False
    assert "failed" in msg.lower()
    assert RecordingService.is_recording(camera) is False


def test_cleanup_old_recordings_and_archive_size(tmp_path):
    cam_dir = tmp_path / "camera_1" / "2026-09-01"
    cam_dir.mkdir(parents=True, exist_ok=True)
    old_file = cam_dir / "recording_001.mp4"
    old_file.write_bytes(b"test" * 100)

    # Modify file mtime to 40 days ago
    past_time = os.path.getmtime(old_file) - (40 * 86400)
    os.utime(old_file, (past_time, past_time))

    new_dir = tmp_path / "camera_1" / "2026-09-06"
    new_dir.mkdir(parents=True, exist_ok=True)
    new_file = new_dir / "recording_002.mp4"
    new_file.write_bytes(b"test" * 200)

    assert RecordingService.get_archive_size_bytes() == 1200

    deleted = RecordingService.cleanup_old_recordings(max_age_days=30)
    assert deleted == 1
    assert not old_file.exists()
    assert new_file.exists()
    assert RecordingService.get_archive_size_bytes() == 800

