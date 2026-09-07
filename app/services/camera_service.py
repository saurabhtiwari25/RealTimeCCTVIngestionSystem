"""
Camera Management Service (CRUD & Validation)
"""

from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models import Camera
from app.utils.logging_config import get_logger
from app.utils.rtsp import sanitize_rtsp_url

logger = get_logger("camera_service")


class CameraService:
    @staticmethod
    def validate_camera_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validates camera form input fields."""
        name, ip, url = data.get("name", "").strip(), data.get("ip_address", "").strip(), data.get("rtsp_url", "").strip()
        sub_url = data.get("sub_stream_url", "")
        if not name: return False, "Camera name is required."
        if len(name) < 2: return False, "Camera name must be at least 2 characters."
        if not ip: return False, "IP address or hostname is required."
        if not url: return False, "Main RTSP URL is required."
        if not url.lower().startswith("rtsp://"): return False, "Main RTSP URL must start with 'rtsp://'."
        if sub_url and sub_url.strip() and not sub_url.strip().lower().startswith("rtsp://"):
            return False, "Sub-stream URL must start with 'rtsp://'."
        return True, None

    @staticmethod
    def create_camera(name: str, ip_address: str, rtsp_url: str, sub_stream_url: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None, protocol: str = "TCP", description: Optional[str] = None) -> Tuple[Optional[Camera], Optional[str]]:
        """Creates and stores a new camera in the database."""
        valid, err = CameraService.validate_camera_data({"name": name, "ip_address": ip_address, "rtsp_url": rtsp_url, "sub_stream_url": sub_stream_url})
        if not valid:
            return None, err
        with get_db() as db:
            if db.query(Camera).filter(Camera.name == name.strip()).first():
                return None, f"A camera with the name '{name.strip()}' already exists."
            sub_clean = sub_stream_url.strip() if sub_stream_url and sub_stream_url.strip() else None
            camera = Camera(
                name=name.strip(),
                ip_address=ip_address.strip(),
                username=username.strip() if username else None,
                password=password if password else None,
                rtsp_url=rtsp_url.strip(),
                sub_stream_url=sub_clean,
                protocol=protocol.upper() if protocol else "TCP",
                description=description.strip() if description else None,
                status="OFFLINE"
            )
            db.add(camera)
            db.flush()
            db.refresh(camera)
            db.expunge(camera)
            logger.info(f"Created camera: ID={camera.id}, Name='{camera.name}', RTSP={sanitize_rtsp_url(camera.rtsp_url)}, SubStream={'Configured' if camera.sub_stream_url else 'None'}")
            return camera, None

    @staticmethod
    def get_camera(camera_id: int) -> Optional[Camera]:
        """Retrieves a camera by ID."""
        with get_db() as db:
            camera = db.query(Camera).filter(Camera.id == camera_id).first()
            if camera:
                db.expunge(camera)
            return camera

    @staticmethod
    def get_all_cameras() -> List[Camera]:
        """Retrieves all registered cameras ordered by ID."""
        with get_db() as db:
            cameras = db.query(Camera).order_by(Camera.id.asc()).all()
            for c in cameras:
                db.expunge(c)
            return cameras

    @staticmethod
    def update_camera(camera_id: int, name: str, ip_address: str, rtsp_url: str, sub_stream_url: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None, protocol: str = "TCP", description: Optional[str] = None) -> Tuple[Optional[Camera], Optional[str]]:
        """Updates camera configuration."""
        valid, err = CameraService.validate_camera_data({"name": name, "ip_address": ip_address, "rtsp_url": rtsp_url, "sub_stream_url": sub_stream_url})
        if not valid:
            return None, err
        with get_db() as db:
            camera = db.query(Camera).filter(Camera.id == camera_id).first()
            if not camera:
                return None, f"Camera ID {camera_id} not found."
            if db.query(Camera).filter(Camera.name == name.strip(), Camera.id != camera_id).first():
                return None, f"Another camera named '{name.strip()}' already exists."
            camera.name, camera.ip_address, camera.rtsp_url = name.strip(), ip_address.strip(), rtsp_url.strip()
            camera.sub_stream_url = sub_stream_url.strip() if sub_stream_url and sub_stream_url.strip() else None
            camera.username = username.strip() if username else None
            if password is not None and password != "":
                camera.password = password
            camera.protocol = protocol.upper() if protocol else "TCP"
            camera.description = description.strip() if description else None
            db.flush()
            db.refresh(camera)
            db.expunge(camera)
            logger.info(f"Updated camera ID={camera.id}: Name='{camera.name}'")
            return camera, None

    @staticmethod
    def delete_camera(camera_id: int) -> Tuple[bool, Optional[str]]:
        """Deletes a camera from database."""
        with get_db() as db:
            camera = db.query(Camera).filter(Camera.id == camera_id).first()
            if not camera:
                return False, f"Camera ID {camera_id} not found."
            db.delete(camera)
            logger.info(f"Deleted camera ID={camera_id}")
            return True, None

    @staticmethod
    def update_status(camera_id: int, status: str, last_error: Optional[str] = None):
        """Updates camera operational status and last_seen / last_error timestamp."""
        from datetime import datetime, timezone
        with get_db() as db:
            camera = db.query(Camera).filter(Camera.id == camera_id).first()
            if camera:
                camera.status = status
                if status == "ONLINE":
                    camera.last_seen = datetime.now(timezone.utc)
                    camera.last_error = None
                elif last_error:
                    camera.last_error = last_error
                db.flush()
