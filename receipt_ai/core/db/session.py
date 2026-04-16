from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from receipt_ai.core.db.config import get_database_url


_ENGINE = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=_ENGINE, autoflush=False, autocommit=False, class_=Session)


def get_session() -> Session:
    return SessionLocal()
