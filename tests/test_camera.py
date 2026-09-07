"""
Unit Tests: Camera CRUD & Validation
"""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use isolated in-memory SQLite for testing
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database.models import Base, Camera
from app.services.camera_service import CameraService
import app.database.database as db_mod

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Creates a fresh in-memory SQLite database for each test."""
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=test_engine)

    from contextlib import contextmanager

    @contextmanager
    def mock_get_db():
        session = TestingSessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr(db_mod, "get_db", mock_get_db)
    monkeypatch.setattr("app.services.camera_service.get_db", mock_get_db)
    yield
    Base.metadata.drop_all(bind=test_engine)


def test_create_camera_success():
    cam, err = CameraService.create_camera(
        name="Front Entrance",
        ip_address="192.168.1.100",
        rtsp_url="rtsp://admin:secret@192.168.1.100:554/stream1",
        username="admin",
        password="secret",
        protocol="TCP",
        description="Gate surveillance",
    )
    assert err is None
    assert cam is not None
    assert cam.id is not None
    assert cam.name == "Front Entrance"
    assert cam.status == "OFFLINE"
    # Password should be masked in sanitized url
    assert "secret" not in cam.sanitized_rtsp_url()
    assert "***" in cam.sanitized_rtsp_url()


def test_create_camera_validation_failure():
    # Empty name
    cam, err = CameraService.create_camera(
        name="",
        ip_address="192.168.1.100",
        rtsp_url="rtsp://192.168.1.100:554/stream",
    )
    assert cam is None
    assert "name is required" in err.lower()

    # Invalid RTSP URL (must start with rtsp://)
    cam2, err2 = CameraService.create_camera(
        name="Invalid Cam",
        ip_address="192.168.1.100",
        rtsp_url="http://192.168.1.100/video",
    )
    assert cam2 is None
    assert "must start with 'rtsp://'" in err2.lower()


def test_read_and_list_cameras():
    cam1, _ = CameraService.create_camera(name="Cam A", ip_address="10.0.0.1", rtsp_url="rtsp://10.0.0.1/1")
    cam2, _ = CameraService.create_camera(name="Cam B", ip_address="10.0.0.2", rtsp_url="rtsp://10.0.0.2/1")

    all_cams = CameraService.get_all_cameras()
    assert len(all_cams) == 2
    names = [c.name for c in all_cams]
    assert "Cam A" in names
    assert "Cam B" in names

    retrieved = CameraService.get_camera(cam1.id)
    assert retrieved is not None
    assert retrieved.name == "Cam A"


def test_update_camera():
    cam, _ = CameraService.create_camera(name="Old Name", ip_address="10.0.0.1", rtsp_url="rtsp://10.0.0.1/1")
    
    updated, err = CameraService.update_camera(
        camera_id=cam.id,
        name="New Name",
        ip_address="10.0.0.50",
        rtsp_url="rtsp://10.0.0.50/stream2",
        protocol="UDP",
        description="Updated position",
    )
    assert err is None
    assert updated.name == "New Name"
    assert updated.ip_address == "10.0.0.50"
    assert updated.protocol == "UDP"


def test_delete_camera():
    cam, _ = CameraService.create_camera(name="To Delete", ip_address="10.0.0.1", rtsp_url="rtsp://10.0.0.1/1")
    cam_id = cam.id

    success, err = CameraService.delete_camera(cam_id)
    assert success is True
    assert err is None

    assert CameraService.get_camera(cam_id) is None
