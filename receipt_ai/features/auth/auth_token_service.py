from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import secrets

from sqlalchemy import select

from receipt_ai.core.db.models import EmailVerificationToken, PasswordResetToken, SessionToken, User
from receipt_ai.core.db.session import get_async_session
from receipt_ai.features.auth.config import AuthConfig


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_raw_token() -> str:
    return secrets.token_urlsafe(48)


async def create_session_token(user_id: str, *, ttl_hours: int | None = None, config: AuthConfig | None = None) -> str:
    cfg = config or AuthConfig.from_env()
    token = generate_raw_token()
    expires_at = datetime.now(UTC) + timedelta(hours=max(1, ttl_hours or cfg.session_ttl_hours))
    async with get_async_session() as db:
        db.add(SessionToken(user_id=user_id, token=token, expires_at=expires_at))
        await db.commit()
    return token


async def delete_session_token(token: str) -> None:
    clean = token.strip()
    if not clean:
        return
    async with get_async_session() as db:
        row = await db.scalar(select(SessionToken).where(SessionToken.token == clean))
        if row is None:
            return
        await db.delete(row)
        await db.commit()


async def issue_password_reset_token(user_id: str, config: AuthConfig | None = None) -> str:
    cfg = config or AuthConfig.from_env()
    raw_token = generate_raw_token()
    token_hash = hash_token(raw_token)
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=max(5, cfg.reset_token_ttl_minutes))
    async with get_async_session() as db:
        db.add(
            PasswordResetToken(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )
        await db.commit()
    return raw_token


async def consume_password_reset_token(raw_token: str) -> User | None:
    clean = raw_token.strip()
    if not clean:
        return None
    token_hash = hash_token(clean)
    now = datetime.now(UTC)
    async with get_async_session() as db:
        row = await db.scalar(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.expires_at > now,
                PasswordResetToken.consumed_at.is_(None),
            )
        )
        if row is None:
            return None
        user = await db.scalar(select(User).where(User.id == row.user_id, User.is_active.is_(True)))
        if user is None:
            return None
        row.consumed_at = now
        await db.commit()
        return user


async def issue_email_verification_token(user_id: str, config: AuthConfig | None = None) -> str:
    cfg = config or AuthConfig.from_env()
    raw_token = generate_raw_token()
    token_hash = hash_token(raw_token)
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=max(1, cfg.verify_token_ttl_hours))
    async with get_async_session() as db:
        db.add(
            EmailVerificationToken(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
            )
        )
        await db.commit()
    return raw_token


async def consume_email_verification_token(raw_token: str) -> User | None:
    clean = raw_token.strip()
    if not clean:
        return None
    token_hash = hash_token(clean)
    now = datetime.now(UTC)
    async with get_async_session() as db:
        row = await db.scalar(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == token_hash,
                EmailVerificationToken.expires_at > now,
                EmailVerificationToken.consumed_at.is_(None),
            )
        )
        if row is None:
            return None
        user = await db.scalar(select(User).where(User.id == row.user_id, User.is_active.is_(True)))
        if user is None:
            return None
        row.consumed_at = now
        user.email_verified_at = now
        await db.commit()
        return user
