from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import secrets

from passlib.context import CryptContext
from sqlalchemy import delete as sa_delete
from sqlalchemy import select

from receipt_ai.core.db.models import Permission, Role, RolePermission, SessionToken, User, UserRole
from receipt_ai.core.db.session import get_async_session

_PWD_CTX = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


@dataclass(frozen=True)
class AuthUser:
    id: str
    email: str
    display_name: str
    roles: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()


async def list_user_roles(user_id: str) -> tuple[str, ...]:
    async with get_async_session() as db:
        rows = (
            await db.execute(
                select(Role.name)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user_id)
                .order_by(Role.name.asc())
            )
        ).scalars().all()
    return tuple(str(x) for x in rows)


async def list_user_permissions(user_id: str) -> tuple[str, ...]:
    async with get_async_session() as db:
        rows = (
            await db.execute(
                select(Permission.code)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .join(Role, Role.id == RolePermission.role_id)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user_id)
                .distinct()
                .order_by(Permission.code.asc())
            )
        ).scalars().all()
    return tuple(str(x) for x in rows)


async def user_has_permission(user_id: str, permission_code: str) -> bool:
    wanted = permission_code.strip().lower()
    if not wanted:
        return False
    perms = await list_user_permissions(user_id)
    return wanted in {p.lower() for p in perms}


async def _resolve_user_rbac(user_id: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    roles = await list_user_roles(user_id)
    perms = await list_user_permissions(user_id)
    return roles, perms


def hash_password(raw_password: str) -> str:
    return _PWD_CTX.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    return _PWD_CTX.verify(raw_password, password_hash)


async def get_user_by_email(email: str) -> AuthUser | None:
    async with get_async_session() as db:
        row = await db.scalar(select(User).where(User.email == email.strip().lower()))
        if row is None:
            return None
        roles, perms = await _resolve_user_rbac(row.id)
        return AuthUser(id=row.id, email=row.email, display_name=row.display_name, roles=roles, permissions=perms)


async def authenticate_user(email: str, password: str) -> AuthUser | None:
    clean = email.strip().lower()
    async with get_async_session() as db:
        row = await db.scalar(select(User).where(User.email == clean, User.is_active.is_(True)))
        if row is None:
            return None
        if not verify_password(password, row.password_hash):
            return None
        roles, perms = await _resolve_user_rbac(row.id)
        return AuthUser(id=row.id, email=row.email, display_name=row.display_name, roles=roles, permissions=perms)


async def create_session_token(user_id: str, *, ttl_hours: int = 24) -> str:
    token = secrets.token_urlsafe(48)
    expires_at = datetime.now(UTC) + timedelta(hours=max(1, ttl_hours))
    async with get_async_session() as db:
        db.add(
            SessionToken(
                user_id=user_id,
                token=token,
                expires_at=expires_at,
            )
        )
        await db.commit()
    return token


async def get_session_user(token: str) -> AuthUser | None:
    clean = token.strip()
    if not clean:
        return None
    now = datetime.now(UTC)
    async with get_async_session() as db:
        row = (
            await db.execute(
            select(SessionToken, User)
            .join(User, User.id == SessionToken.user_id)
            .where(
                SessionToken.token == clean,
                SessionToken.expires_at > now,
                User.is_active.is_(True),
            )
            )
        ).first()
        if row is None:
            return None
        session_token, user = row
        roles, perms = await _resolve_user_rbac(user.id)
        return AuthUser(id=user.id, email=user.email, display_name=user.display_name, roles=roles, permissions=perms)


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


async def upsert_user(
    email: str,
    password: str,
    *,
    display_name: str,
    role_names: tuple[str, ...] | list[str] | None = None,
) -> AuthUser:
    clean = email.strip().lower()
    async with get_async_session() as db:
        row = await db.scalar(select(User).where(User.email == clean))
        desired_roles = tuple({r.strip().lower() for r in (role_names or []) if r and r.strip()})

        if row is None:
            row = User(
                email=clean,
                password_hash=hash_password(password),
                display_name=display_name.strip() or "User",
                is_active=True,
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            if desired_roles:
                role_rows = (
                    await db.execute(select(Role).where(Role.name.in_(list(desired_roles))))
                ).scalars().all()
                for role in role_rows:
                    db.add(UserRole(user_id=row.id, role_id=role.id))
                await db.commit()
            roles, perms = await _resolve_user_rbac(row.id)
            return AuthUser(id=row.id, email=row.email, display_name=row.display_name, roles=roles, permissions=perms)

        row.password_hash = hash_password(password)
        row.display_name = display_name.strip() or row.display_name
        row.is_active = True
        await db.commit()
        await db.refresh(row)
        if desired_roles:
            await db.execute(sa_delete(UserRole).where(UserRole.user_id == row.id))
            role_rows = (
                await db.execute(select(Role).where(Role.name.in_(list(desired_roles))))
            ).scalars().all()
            for role in role_rows:
                db.add(UserRole(user_id=row.id, role_id=role.id))
            await db.commit()
        roles, perms = await _resolve_user_rbac(row.id)
        return AuthUser(id=row.id, email=row.email, display_name=row.display_name, roles=roles, permissions=perms)


async def update_user_display_name(user_id: str, display_name: str) -> AuthUser | None:
    clean_user_id = user_id.strip()
    clean_display_name = display_name.strip()
    if not clean_user_id:
        return None
    if not clean_display_name:
        return None

    async with get_async_session() as db:
        row = await db.scalar(select(User).where(User.id == clean_user_id, User.is_active.is_(True)))
        if row is None:
            return None
        row.display_name = clean_display_name
        await db.commit()
        await db.refresh(row)
        roles, perms = await _resolve_user_rbac(row.id)
        return AuthUser(id=row.id, email=row.email, display_name=row.display_name, roles=roles, permissions=perms)
