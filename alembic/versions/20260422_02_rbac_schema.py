"""add rbac schema and seed baseline roles/permissions

Revision ID: 20260422_02
Revises: 20260416_01
Create Date: 2026-04-22 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260422_02"
down_revision = "20260416_01"
branch_labels = None
depends_on = None


ROLE_ADMIN_ID = "fdb8ad70-2218-4c5d-b57a-0ae4f0cf2a11"
ROLE_USER_ID = "fef50e89-892e-43e7-a377-c6af4d3ae888"

PERM_FILES_READ_ID = "80670a16-ae65-4678-aafe-c99f91bc4dad"
PERM_FILES_WRITE_ID = "32d5583b-b2fe-4662-b8dc-98817ed9e5f8"
PERM_CHAT_READ_ID = "8a31d4d0-f4e1-475e-bf8b-f7ea1f8dbf09"
PERM_CHAT_WRITE_ID = "6894670d-aee3-46d5-a09e-89940db6a79f"
PERM_CHAT_IMAGE_UPLOAD_ID = "7f767669-4f9e-4d0f-9682-c0e4a3f3c8a8"


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)

    op.create_table(
        "permissions",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", sa.String(length=36), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"], unique=False)
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"], unique=False)

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.String(length=36), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "permission_id", sa.String(length=36), sa.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"], unique=False)
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"], unique=False)

    roles = sa.table("roles", sa.column("id", sa.String()), sa.column("name", sa.String()), sa.column("description", sa.String()))
    op.bulk_insert(
        roles,
        [
            {"id": ROLE_ADMIN_ID, "name": "admin", "description": "System administrator"},
            {"id": ROLE_USER_ID, "name": "user", "description": "Standard application user"},
        ],
    )

    permissions = sa.table(
        "permissions",
        sa.column("id", sa.String()),
        sa.column("code", sa.String()),
        sa.column("description", sa.String()),
    )
    op.bulk_insert(
        permissions,
        [
            {"id": PERM_FILES_READ_ID, "code": "files:read", "description": "Read files area"},
            {"id": PERM_FILES_WRITE_ID, "code": "files:write", "description": "Mutate files and folders"},
            {"id": PERM_CHAT_READ_ID, "code": "chat:read", "description": "Read chat history"},
            {"id": PERM_CHAT_WRITE_ID, "code": "chat:write", "description": "Send chat messages"},
            {"id": PERM_CHAT_IMAGE_UPLOAD_ID, "code": "chat:image_upload", "description": "Upload images via chat"},
        ],
    )

    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.String()),
        sa.column("permission_id", sa.String()),
    )
    op.bulk_insert(
        role_permissions,
        [
            {"role_id": ROLE_ADMIN_ID, "permission_id": PERM_FILES_READ_ID},
            {"role_id": ROLE_ADMIN_ID, "permission_id": PERM_FILES_WRITE_ID},
            {"role_id": ROLE_ADMIN_ID, "permission_id": PERM_CHAT_READ_ID},
            {"role_id": ROLE_ADMIN_ID, "permission_id": PERM_CHAT_WRITE_ID},
            {"role_id": ROLE_ADMIN_ID, "permission_id": PERM_CHAT_IMAGE_UPLOAD_ID},
            {"role_id": ROLE_USER_ID, "permission_id": PERM_CHAT_READ_ID},
            {"role_id": ROLE_USER_ID, "permission_id": PERM_CHAT_WRITE_ID},
            {"role_id": ROLE_USER_ID, "permission_id": PERM_CHAT_IMAGE_UPLOAD_ID},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_role_permissions_permission_id", table_name="role_permissions")
    op.drop_index("ix_role_permissions_role_id", table_name="role_permissions")
    op.drop_table("role_permissions")

    op.drop_index("ix_user_roles_role_id", table_name="user_roles")
    op.drop_index("ix_user_roles_user_id", table_name="user_roles")
    op.drop_table("user_roles")

    op.drop_index("ix_permissions_code", table_name="permissions")
    op.drop_table("permissions")

    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
