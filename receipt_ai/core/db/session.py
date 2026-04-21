from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from receipt_ai.core.db.config import get_database_url


_DATABASE_URL = get_database_url()
_ENGINE = create_async_engine(
    _DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"timeout": 5} if _DATABASE_URL.startswith("postgresql") else {},
)
AsyncSessionLocal = async_sessionmaker(bind=_ENGINE, autoflush=False, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session
