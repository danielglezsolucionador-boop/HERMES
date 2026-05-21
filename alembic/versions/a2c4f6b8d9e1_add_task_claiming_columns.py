"""add task claiming columns

Revision ID: a2c4f6b8d9e1
Revises: c5d6f1b7a9e2
Create Date: 2026-05-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a2c4f6b8d9e1"
down_revision: Union[str, None] = "c5d6f1b7a9e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("runner_id", sa.String(length=100), nullable=True))
    op.add_column("tasks", sa.Column("runtime_id", sa.String(length=100), nullable=True))
    op.add_column("tasks", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tasks", sa.Column("claim_state", sa.String(length=50), nullable=True))
    op.add_column(
        "tasks",
        sa.Column("claim_attempts", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index(
        "ix_tasks_claiming_status_claimed_at",
        "tasks",
        ["status", "claimed_at"],
    )
    op.create_index(
        "ix_tasks_claiming_runtime_state",
        "tasks",
        ["runtime_id", "claim_state"],
    )


def downgrade() -> None:
    op.drop_index("ix_tasks_claiming_runtime_state", table_name="tasks")
    op.drop_index("ix_tasks_claiming_status_claimed_at", table_name="tasks")
    op.drop_column("tasks", "claim_attempts")
    op.drop_column("tasks", "claim_state")
    op.drop_column("tasks", "claimed_at")
    op.drop_column("tasks", "runtime_id")
    op.drop_column("tasks", "runner_id")
