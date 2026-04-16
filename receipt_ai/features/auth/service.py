from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import secrets

from passlib.context import CryptContext
from sqlalchemy import select

from receipt_ai.core.db.models import SessionToken, User
from receipt_ai.core.db.session import get_session

_PWD_CTX = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str
    display_name: str


def hash_password(raw_password: str) -> str:
    return _PWD_CTX.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    return _PWD_CTX.verify(raw_password, password_hash)


def get_user_by_email(email: str) -> AuthUser | None:
    with get_session() as db:
        row = db.scalar(select(User).where(User.email == email.strip().lower()))
        if row is None:
            return None
        return AuthUser(id=row.id, email=row.email, display_name=row.display_name)


def authenticate_user(email: str, password: str) -> AuthUser | None:
    clean = email.strip().lower()
    with get_session() as db:
        row = db.scalar(select(User).where(User.email == clean, User.is_active.is_(True)))
        if row is None:
            return None
        if not verify_password(password, row.password_hash):
            return None
        return AuthUser(id=row.id, email=row.email, display_name=row.display_name)


def create_session_token(user_id: str, *, ttl_hours: int = 24) -> str:
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(hours=max(1, ttl_hours))
    with get_session() as db:
        db.add(
            SessionToken(
                user_id=user_id,
                token=token,
                expires_at=expires_at,
            )
        )
        db.commit()
    return token


def get_session_user(token: str) -> AuthUser | None:
    clean = token.strip()
    if not clean:
        return None
    now = datetime.now(UTC)
    with get_session() as db:
        row = db.execute(
            select(SessionToken, User)
            .join(User, User.id == SessionToken.user_id)
            .where(
                SessionToken.token == clean,
                SessionToken.expires_at > now,
                User.is_active.is_(True),
            )
        ).first()
        if row is None:
            return None
        session_token, user = row
        return AuthUser(id=user.id, email=user.email, display_name=user.display_name)


def delete_session_token(token: str) -> None:
    clean = token.strip()
    if not clean:
        return
    with get_session() as db:
        row = db.scalar(select(SessionToken).where(SessionToken.token == clean))
        if row is None:
            return
        db.delete(row)
        db.commit()


def upsert_user(email: str, password: str, *, display_name: str) -> AuthUser:
    clean = email.strip().lower()
    with get_session() as db:
        row = db.scalar(select(User).where(User.email == clean))
        if row is None:
            row = User(
                email=clean,
                password_hash=hash_password(password),
                display_name=display_name.strip() or "User",
                is_active=True,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return AuthUser(id=row.id, email=row.email, display_name=row.display_name)

        row.password_hash = hash_password(password)
        row.display_name = display_name.strip() or row.display_name
        row.is_active = True
        db.commit()
        db.refresh(row)
        return AuthUser(id=row.id, email=row.email, display_name=row.display_name)
