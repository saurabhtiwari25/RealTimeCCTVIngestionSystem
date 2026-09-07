"""
RTSP Utilities for Connection Testing, URL Parsing, and Snapshots
"""

import re
import socket
import subprocess
import os
import shutil
import urllib.parse
from pathlib import Path
from typing import Tuple, Optional
import cv2
import numpy as np

from app.utils.logging_config import get_logger

logger = get_logger("rtsp_utils")


def find_tool(tool_name: str) -> str:
    """Finds tool binary in PATH or Windows WinGet package directory."""
    which_path = shutil.which(tool_name)
    if which_path:
        return which_path
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        winget_pkgs = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if winget_pkgs.exists():
            for exe in winget_pkgs.glob(f"**/{tool_name}.exe"):
                os.environ["PATH"] = str(exe.parent) + os.pathsep + os.environ.get("PATH", "")
                return str(exe)
    return tool_name


CREDENTIAL_PATTERN = re.compile(r"^(rtsp://)([^:@\s]+):([^@\s]+)@(.*)$", re.IGNORECASE)


def sanitize_rtsp_url(url: str) -> str:
    """Masks credentials in RTSP URL."""
    return CREDENTIAL_PATTERN.sub(r"\1\2:***@\4", url) if url else ""


def build_rtsp_url(ip: str, port: int = 554, path: str = "/stream1", username: Optional[str] = None, password: Optional[str] = None) -> str:
    """Constructs a standard RTSP URL."""
    clean_ip, clean_path = ip.strip(), path.strip()
    if not clean_path.startswith("/"):
        clean_path = f"/{clean_path}"
    if username and password:
        return f"rtsp://{urllib.parse.quote(username.strip(), safe='')}:{urllib.parse.quote(password.strip(), safe='')}@{clean_ip}:{port}{clean_path}"
    if username:
        return f"rtsp://{urllib.parse.quote(username.strip(), safe='')}@{clean_ip}:{port}{clean_path}"
    return f"rtsp://{clean_ip}:{port}{clean_path}"


def parse_rtsp_host_port(rtsp_url: str) -> Tuple[Optional[str], int]:
    """Extracts hostname and port from an RTSP URL."""
    try:
        parsed = urllib.parse.urlparse(rtsp_url)
        return parsed.hostname, parsed.port or 554
    except Exception:
        return None, 554


def check_socket_reachable(host: str, port: int, timeout: float = 3.0) -> Tuple[bool, str]:
    """Performs a quick TCP socket handshake to verify network reachability."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return (True, "Port open") if result == 0 else (False, f"Connection refused or port {port} closed (error code {result})")
    except socket.gaierror:
        return False, f"Could not resolve host '{host}'"
    except socket.timeout:
        return False, f"Network timeout after {timeout}s reaching {host}:{port}"
    except Exception as e:
        return False, str(e)


def test_rtsp_connection(rtsp_url: str, timeout: int = 6) -> Tuple[bool, str]:
    """Tests whether an RTSP stream is reachable and contains a valid video stream."""
    if not rtsp_url or not rtsp_url.lower().startswith("rtsp://"):
        return False, "Invalid RTSP URL format. Must start with 'rtsp://'"

    host, port = parse_rtsp_host_port(rtsp_url)
    if not host:
        return False, "Invalid RTSP URL: Hostname or IP address missing."

    is_reachable, reach_msg = check_socket_reachable(host, port, timeout=min(3.0, float(timeout)))
    if not is_reachable:
        return False, f"Camera unreachable at {host}:{port} ({reach_msg})"

    # Probe with ffprobe
    try:
        proc = subprocess.run(
            [find_tool("ffprobe"), "-v", "error", "-rtsp_transport", "tcp", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name,width,height,avg_frame_rate", "-of", "default=noprint_wrappers=1:nokey=0", rtsp_url],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        if proc.returncode == 0 and proc.stdout:
            details = ", ".join(line.strip() for line in proc.stdout.splitlines() if line.strip())
            logger.info(f"RTSP connection successful for {sanitize_rtsp_url(rtsp_url)}: {details}")
            return True, f"Connection successful! Stream verified: ({details})"
        stderr_snippet = proc.stderr.strip()
        if "401 Unauthorized" in stderr_snippet or "Unauthorized" in stderr_snippet:
            return False, "Authentication failed (401 Unauthorized). Verify camera username and password."
        if "404 Not Found" in stderr_snippet or "Not Found" in stderr_snippet:
            return False, "Stream path not found (404). Verify camera RTSP stream path."
        if stderr_snippet:
            return False, f"FFprobe error: {stderr_snippet[:200]}"
    except FileNotFoundError:
        logger.warning("ffprobe command not found, falling back to OpenCV VideoCapture test.")
    except subprocess.TimeoutExpired:
        return False, f"Connection timed out after {timeout} seconds waiting for stream data."
    except Exception as e:
        logger.warning(f"ffprobe check failed with error: {e}. Falling back to OpenCV.")

    # Fallback to OpenCV
    try:
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout * 1000)
        cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout * 1000)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                return True, f"Connection successful! Frame received ({w}x{h})"
            return False, "Connected to RTSP stream, but failed to read initial video frame."
        return False, "Failed to open RTSP stream via video capture."
    except Exception as e:
        return False, f"Stream test failed: {str(e)}"


def capture_snapshot(rtsp_url: str, timeout: int = 5) -> Optional[np.ndarray]:
    """Captures a single snapshot frame from the RTSP stream using OpenCV."""
    try:
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout * 1000)
        if not cap.isOpened():
            return None
        ret, frame = cap.read()
        cap.release()
        return frame if ret and frame is not None else None
    except Exception as e:
        logger.warning(f"Error capturing snapshot: {e}")
    return None


# Mark test_rtsp_connection as a non-test function for pytest discovery
test_rtsp_connection.__test__ = False
