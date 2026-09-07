"""
FFmpeg Stream Recording Service
"""

import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from app.database.models import Camera
from app.utils.config import settings
from app.utils.logging_config import get_logger
from app.utils.rtsp import sanitize_rtsp_url, find_tool

logger = get_logger("recording_service")


class RecordingService:
    _ACTIVE_RECORDINGS: Dict[int, Dict[str, Any]] = {}

    @classmethod
    def get_recordings_dir(cls) -> Path:
        """Returns the base recordings directory path."""
        base_dir = Path(settings.RECORDINGS_DIR)
        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir

    @classmethod
    def get_camera_recording_dir(cls, camera_id: int) -> Path:
        """Returns the directory for a camera's current day recordings."""
        cam_dir = cls.get_recordings_dir() / f"camera_{camera_id}" / datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cam_dir.mkdir(parents=True, exist_ok=True)
        return cam_dir

    @classmethod
    def get_next_filename(cls, camera_id: int) -> Path:
        """Computes the next sequential recording filename."""
        folder = cls.get_camera_recording_dir(camera_id)
        return folder / f"recording_{len(list(folder.glob('recording_*.mp4'))) + 1:03d}.mp4"

    @classmethod
    def is_recording(cls, camera: Camera) -> bool:
        """Checks if a recording process is actively running for the camera."""
        if camera.id not in cls._ACTIVE_RECORDINGS:
            return False
        proc = cls._ACTIVE_RECORDINGS[camera.id].get("process")
        if proc and proc.poll() is None:
            return True
        cls._cleanup_finished(camera.id)
        return False

    @classmethod
    def _cleanup_finished(cls, camera_id: int):
        """Cleans up in-memory reference to a terminated recording process."""
        if camera_id in cls._ACTIVE_RECORDINGS:
            rec_info = cls._ACTIVE_RECORDINGS.pop(camera_id)
            proc = rec_info.get("process")
            if proc:
                logger.info(f"Recording process for camera ID {camera_id} exited with code {proc.poll()}. File: {rec_info.get('filepath', 'unknown')}")

    @classmethod
    def start_recording(cls, camera: Camera) -> Tuple[bool, str]:
        """Starts an FFmpeg recording process for the camera stream."""
        if cls.is_recording(camera):
            return False, f"Recording already active for camera '{camera.name}'."

        output_path = cls.get_next_filename(camera.id)
        logger.info(f"Initiating recording for camera '{camera.name}' -> {output_path}")

        cmd = [find_tool("ffmpeg"), "-y", "-rtsp_transport", (camera.protocol or "tcp").lower(), "-i", camera.rtsp_url, "-c", "copy", "-movflags", "+faststart", str(output_path)]

        try:
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            time.sleep(1.0)
            if proc.poll() is not None:
                stderr = proc.stderr.read() if proc.stderr else ""
                logger.error(f"FFmpeg failed to start recording: {stderr[:300]}")
                return False, f"FFmpeg failed to record: {stderr[:150]}"

            cls._ACTIVE_RECORDINGS[camera.id] = {"process": proc, "filepath": str(output_path), "start_time": datetime.now(timezone.utc), "camera_name": camera.name}
            logger.info(f"Recording started successfully for camera ID {camera.id} (PID {proc.pid})")
            return True, f"Recording started: {output_path.name}"
        except FileNotFoundError:
            err = "FFmpeg executable not found in system PATH. Cannot record."
            logger.error(err)
            return False, err
        except Exception as e:
            err = f"Failed to launch recording: {str(e)}"
            logger.error(err)
            return False, err

    @classmethod
    def stop_recording(cls, camera: Camera) -> Tuple[bool, str]:
        """Stops the active FFmpeg recording process gracefully."""
        if not cls.is_recording(camera):
            return False, f"No active recording found for camera '{camera.name}'."

        rec_info = cls._ACTIVE_RECORDINGS.get(camera.id)
        if not rec_info:
            return False, "No recording process found."

        proc, filepath = rec_info.get("process"), rec_info.get("filepath")
        try:
            if proc.stdin:
                try:
                    proc.stdin.write("q\n")
                    proc.stdin.flush()
                except Exception:
                    pass
            try:
                proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                logger.warning(f"FFmpeg PID {proc.pid} did not terminate on 'q'. Sending terminate signal.")
                proc.terminate()
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    proc.kill()

            cls._cleanup_finished(camera.id)
            logger.info(f"Stopped recording for camera '{camera.name}'. Saved to {filepath}")
            return True, f"Recording saved: {Path(filepath).name if filepath else 'file'}"
        except Exception as e:
            logger.error(f"Error stopping recording for camera ID {camera.id}: {e}")
            cls._cleanup_finished(camera.id)
            return False, f"Error stopping recording: {str(e)}"

    @classmethod
    def get_active_recording_info(cls, camera_id: int) -> Optional[Dict[str, Any]]:
        """Returns details about an ongoing recording."""
        if camera_id not in cls._ACTIVE_RECORDINGS:
            return None
        info = cls._ACTIVE_RECORDINGS[camera_id]
        start_time = info.get("start_time")
        return {"filepath": info.get("filepath"), "elapsed_seconds": int((datetime.now(timezone.utc) - start_time).total_seconds()) if start_time else 0, "camera_name": info.get("camera_name")}

    @classmethod
    def list_all_recordings(cls) -> List[Dict[str, Any]]:
        """Scans the recordings directory and returns a sorted list of all recordings."""
        recordings = []
        for cam_dir in cls.get_recordings_dir().glob("camera_*"):
            if not cam_dir.is_dir():
                continue
            try:
                cam_id = int(cam_dir.name.replace("camera_", ""))
            except ValueError:
                cam_id = None
            for date_dir in cam_dir.glob("????-??-??"):
                if not date_dir.is_dir():
                    continue
                for file in date_dir.glob("*.mp4"):
                    if not file.is_file():
                        continue
                    stat = file.stat()
                    recordings.append({"camera_id": cam_id, "date": date_dir.name, "filename": file.name, "path": str(file), "size_mb": round(stat.st_size / (1024 * 1024), 2), "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")})
        recordings.sort(key=lambda x: x["modified_at"], reverse=True)
        return recordings

    @classmethod
    def delete_recording(cls, filepath: str) -> Tuple[bool, str]:
        """Deletes a recording file from disk."""
        try:
            path = Path(filepath)
            if path.exists() and path.is_file():
                path.unlink()
                logger.info(f"Deleted recording file: {filepath}")
                return True, "Recording deleted successfully."
            return False, "File not found."
        except Exception as e:
            return False, f"Failed to delete file: {str(e)}"

    @classmethod
    def cleanup_old_recordings(cls, max_age_days: int = 30) -> int:
        """Auto-deletes recordings older than max_age_days. Returns count of deleted files."""
        cutoff = datetime.now(timezone.utc).timestamp() - (max_age_days * 86400)
        deleted = 0
        base = cls.get_recordings_dir()
        for mp4 in base.rglob("*.mp4"):
            try:
                if mp4.is_file() and mp4.stat().st_mtime < cutoff:
                    mp4.unlink()
                    logger.info(f"Auto-deleted old recording: {mp4.name} (>{max_age_days} days)")
                    deleted += 1
            except Exception as e:
                logger.warning(f"Failed to delete {mp4}: {e}")
        # Clean up empty date/camera directories
        for cam_dir in base.glob("camera_*"):
            if cam_dir.is_dir():
                for date_dir in cam_dir.glob("????-??-??"):
                    if date_dir.is_dir() and not any(date_dir.iterdir()):
                        date_dir.rmdir()
                if not any(cam_dir.iterdir()):
                    cam_dir.rmdir()
        if deleted:
            logger.info(f"Retention cleanup complete: {deleted} recording(s) deleted (>{max_age_days} days old)")
        return deleted

    @classmethod
    def get_archive_size_bytes(cls) -> int:
        """Returns total size in bytes of all recordings on disk."""
        return sum(f.stat().st_size for f in cls.get_recordings_dir().rglob("*.mp4") if f.is_file())

