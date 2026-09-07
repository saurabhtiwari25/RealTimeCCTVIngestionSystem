"""
Multi-Camera RTSP Stream Simulator with Real Video Footage & Custom Folder Support

Features:
1. Real CCTV & Surveillance Footage: Streams any downloaded MP4/MKV/MOV/AVI video file.
2. Custom Folder Support: Reads from project 'sample_videos/' or any user-specified folder.
3. Broadcast Modes: broadcast_all, distribute, per_camera, synthetic.
4. Dynamic Live Reload: Listens to 'sample_videos/active_config.json' and reloads streams immediately.
5. Environment Resilient: Works automatically in Docker (rtsp://mediamtx:8554) and on host (rtsp://localhost:8554).
"""

import os
import sys
import time
import json
import socket
import logging
import subprocess
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [SIMULATOR] %(message)s")
logger = logging.getLogger("simulator")

SUPPORTED_EXTS = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".ts", ".m4v")
DEFAULT_VIDEOS_DIR = Path(__file__).resolve().parent.parent / "sample_videos"
CONFIG_FILE = DEFAULT_VIDEOS_DIR / "active_config.json"

CAMERAS_CONFIG = [
    {"name": "simulated_cam_1", "label": "CAM 01 - Front Entrance", "offset": 0},
    {"name": "simulated_cam_2", "label": "CAM 02 - Parking Lot", "offset": 10},
    {"name": "simulated_cam_3", "label": "CAM 03 - Warehouse Dock", "offset": 20},
    {"name": "simulated_cam_4", "label": "CAM 04 - Perimeter Fence", "offset": 30},
    {"name": "simulated_cam_5", "label": "CAM 05 - Lobby Reception", "offset": 40},
]

SEMANTIC_VIDEO_MAP = {
    "simulated_cam_1": ["security_footage.mp4", "face", "walking", "entrance"],
    "simulated_cam_2": ["traffic_footage.mp4", "car", "parking", "traffic"],
    "simulated_cam_3": ["indoor_surveillance.mp4", "classroom", "warehouse", "loading"],
    "simulated_cam_4": ["street_surveillance.mp4", "bicycle", "perimeter", "fence", "street"],
    "simulated_cam_5": ["people_surveillance.mp4", "people", "lobby", "reception"],
}

DEFAULT_CONFIG = {"mode": "broadcast_all", "selected_video": "", "stagger_offsets": True, "folder_path": "", "per_camera_map": {}}


def find_ffmpeg() -> str:
    """Finds ffmpeg executable in PATH or WinGet package directory."""
    ffmpeg_cmd = shutil.which("ffmpeg")
    if ffmpeg_cmd:
        return ffmpeg_cmd
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        winget_pkgs = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if winget_pkgs.exists():
            for exe in winget_pkgs.glob("**/ffmpeg.exe"):
                os.environ["PATH"] = str(exe.parent) + os.pathsep + os.environ.get("PATH", "")
                return str(exe)
    return "ffmpeg"


def get_active_folder(config: Dict[str, Any]) -> Path:
    """Returns the resolved Path for the active video footage folder."""
    custom = config.get("folder_path")
    if custom:
        p = Path(custom)
        if p.exists() and p.is_dir():
            return p
    DEFAULT_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_VIDEOS_DIR


def get_available_videos(folder: Path) -> List[Path]:
    """Returns valid video files in the specified folder."""
    if not folder.exists() or not folder.is_dir():
        return []
    videos = []
    for f in folder.iterdir():
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS:
            try:
                if f.stat().st_size > 10240:
                    videos.append(f)
            except Exception:
                pass
    videos.sort(key=lambda x: x.name)
    return videos


def read_config() -> Dict[str, Any]:
    """Reads active configuration or returns default broadcast_all mode."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error reading config: {e}")
    return dict(DEFAULT_CONFIG)


def _match_semantic(cam_name: str, videos: List[Path]) -> Optional[Path]:
    """Finds a video matching semantic keywords for a camera."""
    for kw in SEMANTIC_VIDEO_MAP.get(cam_name, []):
        for v in videos:
            if kw.lower() in v.name.lower():
                return v
    return None


def get_video_for_camera(index: int, cam_name: str, config: Dict[str, Any], videos: List[Path]) -> Optional[Path]:
    """Determines which video file to use for a given camera."""
    if not videos:
        return None
    mode = config.get("mode", "broadcast_all")
    if mode == "synthetic":
        return None

    video_dict = {v.name: v for v in videos}

    if mode in ("broadcast_all", "single"):
        selected = config.get("selected_video", "")
        return video_dict.get(selected, videos[0])

    if mode == "distribute":
        return _match_semantic(cam_name, videos) or videos[index % len(videos)]

    if mode == "per_camera":
        mapped = config.get("per_camera_map", {}).get(cam_name, "")
        if mapped and mapped in video_dict:
            return video_dict[mapped]
        return _match_semantic(cam_name, videos) or videos[index % len(videos)]

    return videos[0]


def wait_for_rtsp_server(host: str, port: int, timeout_sec: int = 30) -> bool:
    """Waits until the MediaMTX RTSP port is open before pushing streams."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.5):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            time.sleep(1)
    return False


def spawn_camera_stream(ffmpeg_bin: str, cam: Dict[str, Any], video_file: Optional[Path], base_rtsp_url: str, stagger_offsets: bool = True) -> subprocess.Popen:
    """Spawns FFmpeg streaming either real video footage or fallback test patterns."""
    target_url = f"{base_rtsp_url.rstrip('/')}/{cam['name']}"
    common_args = ["-threads", "1", "-vcodec", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-g", "30", "-r", "20", "-pix_fmt", "yuv420p", "-an", "-f", "rtsp", "-rtsp_transport", "tcp", target_url]

    if video_file and video_file.exists():
        offset = cam.get("offset", 0) if stagger_offsets else 0
        cmd = [ffmpeg_bin, "-re", "-stream_loop", "-1"]
        if offset > 0:
            cmd.extend(["-ss", str(offset)])
        cmd.extend(["-i", str(video_file)] + common_args)
        source_label = f"REAL FOOTAGE '{video_file.name}' (offset +{offset}s)"
    else:
        cmd = [ffmpeg_bin, "-re", "-f", "lavfi", "-i", "smptebars=size=768x432:rate=20",
               "-vf", "drawtext=text='%{pts\\:hms}':x=(w-tw)/2:y=15:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.7:boxborderw=6"] + common_args
        source_label = "SMPTE COLOR BARS & COMPACT DIGITAL CLOCK"

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logger.info(f"[{cam['label']}] -> {source_label} -> {target_url} (PID {proc.pid})")
    return proc


def get_default_rtsp_base() -> str:
    """Auto-detects RTSP server base URL depending on environment."""
    env_base = os.getenv("MEDIAMTX_RTSP_BASE")
    if env_base:
        return env_base
    if os.path.exists("/.dockerenv") or os.getenv("CONTAINER_NAME"):
        return "rtsp://mediamtx:8554"
    return "rtsp://localhost:8554"


def run_all_simulators(base_rtsp_url: Optional[str] = None):
    """Main daemon loop running 5 camera streams with dynamic video reloading."""
    if not base_rtsp_url:
        base_rtsp_url = get_default_rtsp_base()

    ffmpeg_bin = find_ffmpeg()
    logger.info(f"Starting Multi-Camera Surveillance Simulator using FFmpeg ({ffmpeg_bin})...")
    logger.info(f"Target RTSP Base: {base_rtsp_url}")

    try:
        url_clean = base_rtsp_url.replace("rtsp://", "").split("/")[0]
        parts = url_clean.split(":")
        host, port = parts[0], int(parts[1]) if len(parts) > 1 else 8554
        logger.info(f"Waiting for RTSP server at {host}:{port}...")
        if not wait_for_rtsp_server(host, port, timeout_sec=20):
            logger.warning(f"RTSP server at {host}:{port} did not respond within 20s. Proceeding anyway...")
    except Exception as e:
        logger.warning(f"Could not check RTSP host: {e}")

    procs: Dict[str, subprocess.Popen] = {}
    current_config = read_config()
    active_folder = get_active_folder(current_config)
    current_videos = get_available_videos(active_folder)

    logger.info(f"Using footage folder: {active_folder}")
    logger.info(f"Found {len(current_videos)} valid video file(s): {[v.name for v in current_videos]}")

    def restart_all():
        nonlocal procs, current_config, active_folder, current_videos
        for proc in procs.values():
            if proc and proc.poll() is None:
                try:
                    proc.kill()
                    proc.wait(timeout=0.3)
                except Exception:
                    pass
        procs.clear()
        time.sleep(0.1)

        current_config = read_config()
        active_folder = get_active_folder(current_config)
        current_videos = get_available_videos(active_folder)
        stagger = current_config.get("stagger_offsets", True)
        logger.info(f"Active Mode: {current_config.get('mode', 'broadcast_all')} | Stagger: {stagger}")

        for idx, cam in enumerate(CAMERAS_CONFIG):
            v = get_video_for_camera(idx, cam["name"], current_config, current_videos)
            procs[cam["name"]] = spawn_camera_stream(ffmpeg_bin, cam, v, base_rtsp_url, stagger_offsets=stagger)

    restart_all()
    last_config_mtime = CONFIG_FILE.stat().st_mtime if CONFIG_FILE.exists() else 0

    try:
        while True:
            time.sleep(1)
            if CONFIG_FILE.exists():
                mtime = CONFIG_FILE.stat().st_mtime
                if mtime != last_config_mtime:
                    last_config_mtime = mtime
                    logger.info("Configuration change detected! Reloading all camera streams with new footage...")
                    restart_all()
                    continue

            stagger = current_config.get("stagger_offsets", True)
            for idx, cam in enumerate(CAMERAS_CONFIG):
                name = cam["name"]
                proc = procs.get(name)
                if proc is None or proc.poll() is not None:
                    v = get_video_for_camera(idx, name, current_config, current_videos)
                    procs[name] = spawn_camera_stream(ffmpeg_bin, cam, v, base_rtsp_url, stagger_offsets=stagger)

    except KeyboardInterrupt:
        logger.info("Stopping all simulators...")
        for proc in procs.values():
            if proc and proc.poll() is None:
                proc.terminate()
        logger.info("All simulators stopped.")

if __name__ == "__main__":
    run_all_simulators()
