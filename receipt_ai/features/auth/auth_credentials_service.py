from __future__ import annotations

from datetime import UTC, datetime

from passlib.context import CryptContext
from sqlalchemy import delete as sa_delete
from sqlalchemy import select

from receipt_ai.core.db.models import Permission, Role, RolePermission, SessionToken, User, UserRole
from receipt_ai.core.db.session import get_async_session
from receipt_ai.features.auth.auth_mailer_service import send_email
from receipt_ai.features.auth.auth_rate_limit_service import (
    check_login_rate_limit,
    check_reset_rate_limit,
    clear_rate_limit,
)
from receipt_ai.features.auth.auth_token_service import (
    consume_email_verification_token,
    consume_password_reset_token,
    issue_email_verification_token,
    issue_password_reset_token,
)
from receipt_ai.features.auth.config import AuthConfig
from receipt_ai.features.auth.types import AuthUser

_PWD_CTX = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(raw_password: str) -> str:
    return _PWD_CTX.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    return _PWD_CTX.verify(raw_password, password_hash)


def validate_password_strength(password: str) -> str | None:
    clean = password or ""
    if len(clean) < 12:
        return "Password must be at least 12 characters."
    checks = 0
    checks += int(any(ch.islower() for ch in clean))
    checks += int(any(ch.isupper() for ch in clean))
    checks += int(any(ch.isdigit() for ch in clean))
    checks += int(any(not ch.isalnum() for ch in clean))
    if checks < 3:
        return "Password must include at least 3 of: lowercase, uppercase, number, symbol."
    return None


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


async def _resolve_user_rbac(user_id: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    roles = await list_user_roles(user_id)
    perms = await list_user_permissions(user_id)
    return roles, perms


def _to_auth_user(row: User, roles: tuple[str, ...], perms: tuple[str, ...]) -> AuthUser:
    return AuthUser(
        id=row.id,
        email=row.email,
        display_name=row.display_name,
        roles=roles,
        permissions=perms,
        email_verified=bool(row.email_verified_at),
    )


async def get_user_by_email(email: str) -> AuthUser | None:
    clean = email.strip().lower()
    if not clean:
        return None
    async with get_async_session() as db:
        row = await db.scalar(select(User).where(User.email == clean))
        if row is None:
            return None
        roles, perms = await _resolve_user_rbac(row.id)
        return _to_auth_user(row, roles, perms)


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
        _, user = row
        roles, perms = await _resolve_user_rbac(user.id)
        return _to_auth_user(user, roles, perms)


async def authenticate_user(email: str, password: str, *, identity_key: str = "default") -> AuthUser | None:
    cfg = AuthConfig.from_env()
    allowed, retry_after = check_login_rate_limit(identity_key, cfg)
    if not allowed:
        raise RuntimeError(f"Too many login attempts. Try again in {retry_after}s.")
    clean = email.strip().lower()
    async with get_async_session() as db:
        row = await db.scalar(select(User).where(User.email == clean, User.is_active.is_(True)))
        if row is None:
            return None
        if not verify_password(password, row.password_hash):
            return None
        clear_rate_limit(f"login:{identity_key}")
        roles, perms = await _resolve_user_rbac(row.id)
        return _to_auth_user(row, roles, perms)


async def request_password_reset(email: str, *, identity_key: str = "default") -> None:
    cfg = AuthConfig.from_env()
    allowed, retry_after = check_reset_rate_limit(identity_key, cfg)
    if not allowed:
        raise RuntimeError(f"Too many reset attempts. Try again in {retry_after}s.")

    clean = email.strip().lower()
    if not clean:
        return
    async with get_async_session() as db:
        row = await db.scalar(select(User).where(User.email == clean, User.is_active.is_(True)))
    if row is None:
        return

    token = await issue_password_reset_token(row.id, cfg)
    reset_link = f"{cfg.app_base_url.rstrip('/')}/reset-password?token={token}"
    send_email(
        to_email=clean,
        subject="Reset your Receipt AI password",
        body_text=f"We received a password reset request.\n\nReset link:\n{reset_link}\n\nIf you did not request this, ignore this email.",
        config=cfg,
    )


async def reset_password_with_token(raw_token: str, new_password: str) -> AuthUser | None:
    pw_error = validate_password_strength(new_password)
    if pw_error:
        raise RuntimeError(pw_error)
    user = await consume_password_reset_token(raw_token)
    if user is None:
        return None
    async with get_async_session() as db:
        row = await db.scalar(select(User).where(User.id == user.id, User.is_active.is_(True)))
        if row is None:
            return None
        row.password_hash = hash_password(new_password)
        await db.commit()
        await db.refresh(row)
        roles, perms = await _resolve_user_rbac(row.id)
        return _to_auth_user(row, roles, perms)


async def request_email_verification(email: str, *, identity_key: str = "default") -> None:
    cfg = AuthConfig.from_env()
    allowed, retry_after = check_reset_rate_limit(identity_key, cfg)
    if not allowed:
        raise RuntimeError(f"Too many verification attempts. Try again in {retry_after}s.")

    clean = email.strip().lower()
    if not clean:
        return
    async with get_async_session() as db:
        row = await db.scalar(select(User).where(User.email == clean, User.is_active.is_(True)))
    if row is None or row.email_verified_at is not None:
        return
    token = await issue_email_verification_token(row.id, cfg)
    verify_link = f"{cfg.app_base_url.rstrip('/')}/verify-email?token={token}"
    send_email(
        to_email=clean,
        subject="Verify your Receipt AI email",
        body_text=f"Verify your account by opening:\n{verify_link}\n\nIf this wasn't you, ignore this message.",
        config=cfg,
    )


async def verify_email_with_token(raw_token: str) -> AuthUser | None:
    user = await consume_email_verification_token(raw_token)
    if user is None:
        return None
    roles, perms = await _resolve_user_rbac(user.id)
    return _to_auth_user(user, roles, perms)


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
                email_verified_at=datetime.now(UTC),
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
            if desired_roles:
                role_rows = (await db.execute(select(Role).where(Role.name.in_(list(desired_roles))))).scalars().all()
                for role in role_rows:
                    db.add(UserRole(user_id=row.id, role_id=role.id))
                await db.commit()
            roles, perms = await _resolve_user_rbac(row.id)
            return _to_auth_user(row, roles, perms)

        row.password_hash = hash_password(password)
        row.display_name = display_name.strip() or row.display_name
        row.is_active = True
        if row.email_verified_at is None:
            row.email_verified_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(row)
        if desired_roles:
            await db.execute(sa_delete(UserRole).where(UserRole.user_id == row.id))
            role_rows = (await db.execute(select(Role).where(Role.name.in_(list(desired_roles))))).scalars().all()
            for role in role_rows:
                db.add(UserRole(user_id=row.id, role_id=role.id))
            await db.commit()
        roles, perms = await _resolve_user_rbac(row.id)
        return _to_auth_user(row, roles, perms)


async def update_user_display_name(user_id: str, display_name: str) -> AuthUser | None:
    clean_user_id = user_id.strip()
    clean_display_name = display_name.strip()
    if not clean_user_id or not clean_display_name:
        return None
    async with get_async_session() as db:
        row = await db.scalar(select(User).where(User.id == clean_user_id, User.is_active.is_(True)))
        if row is None:
            return None
        row.display_name = clean_display_name
        await db.commit()
        await db.refresh(row)
        roles, perms = await _resolve_user_rbac(row.id)
        return _to_auth_user(row, roles, perms)


async def user_has_permission(user_id: str, permission_code: str) -> bool:
    wanted = permission_code.strip().lower()
    if not wanted:
        return False
    perms = await list_user_permissions(user_id)
    return wanted in {p.lower() for p in perms}
