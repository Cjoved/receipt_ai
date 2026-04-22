import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from receipt_ai.core.db import models
from receipt_ai.core.db.base import Base
from receipt_ai.core.db.config import get_database_url
from receipt_ai.core.db.session import get_async_session
from receipt_ai.features.auth.service import upsert_user


async def ensure_rbac_seed() -> None:
    async with get_async_session() as db:
        roles = {r.name: r for r in (await db.execute(select(models.Role))).scalars().all()}
        perms = {p.code: p for p in (await db.execute(select(models.Permission))).scalars().all()}

        if "admin" not in roles:
            db.add(models.Role(id=str(uuid.uuid4()), name="admin", description="System administrator"))
        if "user" not in roles:
            db.add(models.Role(id=str(uuid.uuid4()), name="user", description="Standard application user"))

        wanted_perms = {
            "files:read": "Read files area",
            "files:write": "Mutate files and folders",
            "chat:read": "Read chat history",
            "chat:write": "Send chat messages",
            "chat:image_upload": "Upload images via chat",
        }
        for code, desc in wanted_perms.items():
            if code not in perms:
                db.add(models.Permission(id=str(uuid.uuid4()), code=code, description=desc))

        await db.commit()

    async with get_async_session() as db:
        roles = {r.name: r for r in (await db.execute(select(models.Role))).scalars().all()}
        perms = {p.code: p for p in (await db.execute(select(models.Permission))).scalars().all()}

        existing = {
            (rp.role_id, rp.permission_id)
            for rp in (await db.execute(select(models.RolePermission))).scalars().all()
        }

        admin_perms = ["files:read", "files:write", "chat:read", "chat:write", "chat:image_upload"]
        user_perms = ["chat:read", "chat:write", "chat:image_upload"]

        for code in admin_perms:
            key = (roles["admin"].id, perms[code].id)
            if key not in existing:
                db.add(models.RolePermission(role_id=roles["admin"].id, permission_id=perms[code].id))
        for code in user_perms:
            key = (roles["user"].id, perms[code].id)
            if key not in existing:
                db.add(models.RolePermission(role_id=roles["user"].id, permission_id=perms[code].id))

        await db.commit()


async def main() -> None:
    db_url = get_database_url()
    engine = create_async_engine(
        db_url,
        pool_pre_ping=True,
        connect_args={"timeout": 5} if db_url.startswith("postgresql") else {},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await ensure_rbac_seed()

    await upsert_user("admin@receipt.ai", "AdminPass#12345", display_name="Admin", role_names=("admin",))
    await upsert_user("user@receipt.ai", "UserPass#12345", display_name="User", role_names=("user",))

    print("RBAC ready. Accounts created.")
    print("admin@receipt.ai / AdminPass#12345")
    print("user@receipt.ai / UserPass#12345")


if __name__ == "__main__":
    asyncio.run(main())
