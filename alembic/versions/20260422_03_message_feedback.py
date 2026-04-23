"""add message feedback table

Revision ID: 20260422_03
Revises: 20260422_02
Create Date: 2026-04-22 00:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260422_03"
down_revision = "20260422_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "message_feedback",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("message_id", sa.String(length=36), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vote", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("message_id", "user_id", name="uq_message_feedback_message_user"),
    )
    op.create_index("ix_message_feedback_message_id", "message_feedback", ["message_id"], unique=False)
    op.create_index("ix_message_feedback_user_id", "message_feedback", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_message_feedback_user_id", table_name="message_feedback")
    op.drop_index("ix_message_feedback_message_id", table_name="message_feedback")
    op.drop_table("message_feedback")
