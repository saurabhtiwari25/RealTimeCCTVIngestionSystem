"""
Camera Health Monitoring & Exponential Backoff Reconnection Service
"""

import time
from datetime import datetime, timezone
from typing import Dict, Tuple, Optional, Any

from app.database.models import Camera
from app.services.camera_service import CameraService
from app.services.stream_service import StreamService
from app.utils.logging_config import get_logger
from app.utils.rtsp import check_socket_reachable, parse_rtsp_host_port

logger = get_logger("health_service")


class HealthService:
    _RETRY_STATE: Dict[int, Dict[str, Any]] = {}
    MAX_RETRIES = 5
    BASE_BACKOFF_SECONDS = 5.0
    MAX_BACKOFF_SECONDS = 60.0

    @classmethod
    def get_retry_info(cls, camera_id: int) -> Dict[str, Any]:
        """Returns the current retry state for a camera."""
        if camera_id not in cls._RETRY_STATE:
            cls._RETRY_STATE[camera_id] = {"attempts": 0, "next_retry_ts": 0.0, "last_status": "OFFLINE"}
        return cls._RETRY_STATE[camera_id]

    @classmethod
    def reset_retry_state(cls, camera_id: int):
        """Resets retry counter after successful connection."""
        cls._RETRY_STATE[camera_id] = {"attempts": 0, "next_retry_ts": 0.0, "last_status": "ONLINE"}

    @classmethod
    def check_camera_health(cls, camera: Camera) -> Tuple[str, Optional[str]]:
        """Determines the real-time health of a camera."""
        host, port = parse_rtsp_host_port(camera.rtsp_url)
        if not host:
            err = "Invalid RTSP host configuration."
            CameraService.update_status(camera.id, "ERROR", last_error=err)
            return "ERROR", err

        is_reachable, reach_msg = check_socket_reachable(host, port, timeout=2.5)
        now_ts = time.time()
        state = cls.get_retry_info(camera.id)

        if is_reachable:
            mtx_status = StreamService.get_stream_status(camera)
            if (mtx_status.get("active") and mtx_status.get("ready")) or camera.status == "ONLINE":
                CameraService.update_status(camera.id, "ONLINE")
                cls.reset_retry_state(camera.id)
                return "ONLINE", None
            return camera.status, None

        # Connection is down
        if camera.status == "ONLINE":
            logger.warning(f"Camera '{camera.name}' [ID={camera.id}] lost connection: {reach_msg}")
            CameraService.update_status(camera.id, "OFFLINE", last_error=f"Connection lost: {reach_msg}")
            state["last_status"] = "OFFLINE"

        if state["attempts"] < cls.MAX_RETRIES:
            if now_ts >= state["next_retry_ts"]:
                state["attempts"] += 1
                delay = min(cls.BASE_BACKOFF_SECONDS * (2 ** (state["attempts"] - 1)), cls.MAX_BACKOFF_SECONDS)
                state["next_retry_ts"] = now_ts + delay
                logger.info(f"Attempting reconnect {state['attempts']}/{cls.MAX_RETRIES} for camera '{camera.name}' (next retry in {delay:.1f}s)")
                CameraService.update_status(camera.id, "CONNECTING", last_error=f"Reconnecting (Attempt {state['attempts']}/{cls.MAX_RETRIES})...")
                success, msg = StreamService.reconnect_stream(camera)
                if success:
                    cls.reset_retry_state(camera.id)
                    return "ONLINE", None
                return "CONNECTING", f"Reconnect attempt {state['attempts']} failed: {msg}"
            return "CONNECTING", f"Waiting {max(0.0, state['next_retry_ts'] - now_ts):.1f}s for next reconnect attempt..."

        err_msg = f"Maximum reconnect attempts ({cls.MAX_RETRIES}) reached. Camera offline."
        CameraService.update_status(camera.id, "ERROR", last_error=err_msg)
        return "ERROR", err_msg

    @classmethod
    def check_all(cls) -> Dict[int, str]:
        """Performs health check across all registered cameras."""
        return {cam.id: cls.check_camera_health(cam)[0] for cam in CameraService.get_all_cameras()}
