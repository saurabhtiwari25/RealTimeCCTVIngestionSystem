"""
Stream Service: MediaMTX Path Management and Stream Ingestion Control
"""

import requests
from typing import Tuple, Dict, Any, Optional

from app.database.models import Camera
from app.services.camera_service import CameraService
from app.utils.config import settings
from app.utils.logging_config import get_logger
from app.utils.rtsp import sanitize_rtsp_url

logger = get_logger("stream_service")


class StreamService:
    @staticmethod
    def get_path_name(camera: Camera, stream_type: str = "main") -> str:
        """Returns the unique MediaMTX stream path for a camera (main or sub-stream)."""
        if "simulated_cam" in camera.rtsp_url:
            last_part = camera.rtsp_url.rstrip("/").split("/")[-1].split("?")[0]
            base = last_part if last_part.startswith("simulated_cam") else "simulated_cam"
            return f"{base}_sub" if (stream_type == "sub" and camera.sub_stream_url) else base
        base = f"cam_{camera.id}"
        return f"{base}_sub" if (stream_type == "sub" and camera.sub_stream_url) else base

    @staticmethod
    def get_stream_urls(camera: Camera, stream_type: str = "main") -> Dict[str, Any]:
        """Returns browser-accessible WebRTC, HLS, and RTSP stream URLs for main or sub stream."""
        use_sub = (stream_type == "sub" and bool(camera.sub_stream_url))
        path = StreamService.get_path_name(camera, "sub" if use_sub else "main")
        host = settings.MEDIAMTX_HOST
        return {
            "webrtc": f"http://{host}:{settings.MEDIAMTX_WEBRTC_PORT}/{path}/",
            "webrtc_whep": f"http://{host}:{settings.MEDIAMTX_WEBRTC_PORT}/{path}/whep",
            "hls": f"http://{host}:{settings.MEDIAMTX_HLS_PORT}/{path}/",
            "hls_playlist": f"http://{host}:{settings.MEDIAMTX_HLS_PORT}/{path}/index.m3u8",
            "rtsp_proxy": f"rtsp://{host}:{settings.MEDIAMTX_RTSP_PORT}/{path}",
            "path_name": path,
            "has_sub_stream": bool(camera.sub_stream_url),
            "is_sub_stream": use_sub,
        }

    @staticmethod
    def _configure_mediamtx_path(api_base: str, path_name: str, source_url: str, protocol: str) -> Tuple[bool, str]:
        """Registers or patches an RTSP source path in MediaMTX."""
        payload = {"source": source_url, "sourceOnDemand": False, "rtspTransport": (protocol or "tcp").lower()}
        res = requests.post(f"{api_base}/v3/config/paths/add/{path_name}", json=payload, timeout=4)
        if res.status_code == 400 and "already exists" in res.text.lower():
            patch_res = requests.patch(f"{api_base}/v3/config/paths/patch/{path_name}", json=payload, timeout=4)
            if patch_res.status_code in (200, 201):
                return True, "Path updated"
            return False, f"Patch failed: {patch_res.text}"
        if res.status_code in (200, 201):
            return True, "Path registered"
        return False, f"MediaMTX error ({res.status_code}): {res.text}"

    @staticmethod
    def start_stream(camera: Camera) -> Tuple[bool, str]:
        """Registers/starts the camera RTSP source (and sub-stream if configured) with MediaMTX."""
        path_name = StreamService.get_path_name(camera, "main")

        if "simulated_cam" in camera.rtsp_url or "localhost:8554" in camera.rtsp_url or "mediamtx:8554" in camera.rtsp_url:
            CameraService.update_status(camera.id, "ONLINE")
            logger.info(f"Simulated camera stream path '{path_name}' marked ONLINE (direct RTSP publisher).")
            return True, "Simulated camera stream is active."

        api_base = settings.MEDIAMTX_API_URL.rstrip('/')

        try:
            CameraService.update_status(camera.id, "CONNECTING")
            # 1. Register/Start Main Stream
            ok_main, msg_main = StreamService._configure_mediamtx_path(api_base, path_name, camera.rtsp_url, camera.protocol)
            if not ok_main:
                CameraService.update_status(camera.id, "ERROR", last_error=msg_main)
                return False, msg_main

            # 2. Register/Start Sub-stream if present
            if camera.sub_stream_url:
                sub_path = StreamService.get_path_name(camera, "sub")
                ok_sub, msg_sub = StreamService._configure_mediamtx_path(api_base, sub_path, camera.sub_stream_url, camera.protocol)
                if not ok_sub:
                    logger.warning(f"Failed to register sub-stream '{sub_path}': {msg_sub}")
                else:
                    logger.info(f"Sub-stream path '{sub_path}' registered successfully for camera ID {camera.id}")

            CameraService.update_status(camera.id, "ONLINE")
            logger.info(f"Registered stream paths for {camera.name} (Main={path_name}, Sub={bool(camera.sub_stream_url)})")
            return True, "Stream started successfully."

        except requests.exceptions.ConnectionError:
            err_msg = f"MediaMTX is not reachable at {settings.MEDIAMTX_API_URL}. Is MediaMTX running?"
            logger.error(err_msg)
            CameraService.update_status(camera.id, "ERROR", last_error=err_msg)
            return False, err_msg
        except Exception as e:
            err_msg = f"Error starting stream: {str(e)}"
            logger.error(err_msg)
            CameraService.update_status(camera.id, "ERROR", last_error=err_msg)
            return False, err_msg

    @staticmethod
    def stop_stream(camera: Camera) -> Tuple[bool, str]:
        """Removes the camera stream paths (main and sub) from MediaMTX and sets status to OFFLINE."""
        path_name = StreamService.get_path_name(camera, "main")
        api_base = settings.MEDIAMTX_API_URL.rstrip('/')
        try:
            requests.delete(f"{api_base}/v3/config/paths/delete/{path_name}", timeout=4)
            if camera.sub_stream_url:
                sub_path = StreamService.get_path_name(camera, "sub")
                requests.delete(f"{api_base}/v3/config/paths/delete/{sub_path}", timeout=4)

            CameraService.update_status(camera.id, "OFFLINE")
            logger.info(f"Removed stream paths for camera ID {camera.id} from MediaMTX.")
            return True, "Stream stopped successfully."
        except requests.exceptions.ConnectionError:
            CameraService.update_status(camera.id, "OFFLINE")
            return True, "Stream marked offline (MediaMTX server offline)."
        except Exception as e:
            CameraService.update_status(camera.id, "OFFLINE", last_error=str(e))
            return False, f"Error stopping stream: {str(e)}"

    @staticmethod
    def get_stream_status(camera: Camera) -> Dict[str, Any]:
        """Queries MediaMTX runtime path status."""
        path_name = StreamService.get_path_name(camera)
        try:
            response = requests.get(f"{settings.MEDIAMTX_API_URL.rstrip('/')}/v3/paths/get/{path_name}", timeout=3)
            if response.status_code == 200:
                data = response.json()
                return {"active": True, "ready": data.get("ready", False), "readers": len(data.get("readers", [])), "bytes_received": data.get("bytesReceived", 0), "tracks": data.get("tracks", [])}
            if response.status_code == 404:
                return {"active": False, "ready": False, "readers": 0, "bytes_received": 0}
            return {"active": False, "error": response.text}
        except Exception as e:
            return {"active": False, "error": str(e)}

    @staticmethod
    def reconnect_stream(camera: Camera) -> Tuple[bool, str]:
        """Attempts to reconnect an interrupted camera stream."""
        logger.info(f"Reconnecting stream for camera ID {camera.id}...")
        StreamService.stop_stream(camera)
        return StreamService.start_stream(camera)
