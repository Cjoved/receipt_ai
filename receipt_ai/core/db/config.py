from __future__ import annotations

import os

from dotenv import load_dotenv


def get_database_url() -> str:
    """Return configured DB URL; default to local postgres from docker-compose."""
    load_dotenv()
    raw = os.getenv("DATABASE_URL", "").strip()
    if raw:
        # Normalize plain postgres URLs to asyncpg driver for async SQLAlchemy sessions.
        if raw.startswith("postgresql://"):
            return "postgresql+asyncpg://" + raw[len("postgresql://") :]
        return raw
    return "postgresql+asyncpg://receipt_ai:receipt_ai_dev@localhost:5432/receipt_ai"
