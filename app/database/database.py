"""
Database connection and session management
"""

import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.database.models import Base
from app.utils.logging_config import get_logger

logger = get_logger("database")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/camera_stream_db")


def create_db_engine():
    """Creates SQLAlchemy engine with automatic fallback for local development if PostgreSQL is unavailable."""
    try:
        if DATABASE_URL.startswith("sqlite"):
            return create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20, echo=False)
        with engine.connect():
            pass
        logger.info("Successfully connected to PostgreSQL database.")
        return engine
    except Exception as e:
        logger.warning(f"Could not connect to configured database ({DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'db'}). Error: {e}. Falling back to SQLite.")
        os.makedirs("recordings", exist_ok=True)
        return create_engine("sqlite:///recordings/cameras_fallback.db", connect_args={"check_same_thread": False}, echo=False)


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)


def init_db():
    """Creates all database tables and ensures schema is up-to-date."""
    try:
        Base.metadata.create_all(bind=engine)
        with engine.connect() as conn:
            from sqlalchemy import text
            try:
                conn.execute(text("ALTER TABLE cameras ADD COLUMN sub_stream_url VARCHAR(500)"))
                conn.commit()
            except Exception:
                pass  
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database tables: {e}")
        raise


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session rolled back due to error: {e}")
        raise
    finally:
        session.close()
