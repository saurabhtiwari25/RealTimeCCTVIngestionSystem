"""
SQLAlchemy Database Models for Surveillance Platform
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    ip_address = Column(String(100), nullable=False)
    username = Column(String(100), nullable=True)
    password = Column(String(255), nullable=True)
    rtsp_url = Column(String(500), nullable=False)
    sub_stream_url = Column(String(500), nullable=True)  # Lower-res stream for grid view (saves bandwidth)
    protocol = Column(String(20), default="TCP", nullable=False)
    description = Column(Text, nullable=True)
    
    # Status: ONLINE, OFFLINE, CONNECTING, ERROR
    status = Column(String(20), default="OFFLINE", nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_seen = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    def sanitized_rtsp_url(self) -> str:
        """Returns the RTSP URL with any embedded password masked."""
        from app.utils.rtsp import sanitize_rtsp_url
        return sanitize_rtsp_url(self.rtsp_url)

    def sanitized_sub_stream_url(self) -> str:
        """Returns the sub-stream RTSP URL with password masked, or empty string."""
        if not self.sub_stream_url:
            return ""
        from app.utils.rtsp import sanitize_rtsp_url
        return sanitize_rtsp_url(self.sub_stream_url)

    def to_dict(self, include_password: bool = False) -> dict:
        """Serializes camera model to dict, omitting password by default."""
        data = {
            "id": self.id,
            "name": self.name,
            "ip_address": self.ip_address,
            "username": self.username,
            "rtsp_url": self.rtsp_url if include_password else self.sanitized_rtsp_url(),
            "sub_stream_url": self.sub_stream_url if include_password else self.sanitized_sub_stream_url(),
            "protocol": self.protocol,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "last_error": self.last_error,
        }
        if include_password:
            data["password"] = self.password
        return data

    def __repr__(self) -> str:
        return f"<Camera(id={self.id}, name='{self.name}', ip='{self.ip_address}', status='{self.status}')>"
