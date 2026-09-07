"""
Application Configuration
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

class Settings:
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/camera_stream_db"
    )

    # MediaMTX
    # Host accessible by browser clients (e.g., localhost)
    MEDIAMTX_HOST: str = os.getenv("MEDIAMTX_HOST", "localhost")
    # API URL reachable by backend Python service
    MEDIAMTX_API_URL: str = os.getenv("MEDIAMTX_API_URL", "http://localhost:9997")
    
    MEDIAMTX_RTSP_PORT: int = int(os.getenv("MEDIAMTX_RTSP_PORT", "8554"))
    MEDIAMTX_WEBRTC_PORT: int = int(os.getenv("MEDIAMTX_WEBRTC_PORT", "8889"))
    MEDIAMTX_HLS_PORT: int = int(os.getenv("MEDIAMTX_HLS_PORT", "8888"))
    MEDIAMTX_API_PORT: int = int(os.getenv("MEDIAMTX_API_PORT", "9997"))

    # Storage
    RECORDINGS_DIR: str = os.getenv("RECORDINGS_DIR", "recordings")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
