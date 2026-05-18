"""expand_tasks_table

Revision ID: 81bcf5745490
Revises: d8c794b45f16
Create Date: 2026-05-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '81bcf5745490'
down_revision: Union[str, None] = 'd8c794b45f16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename name → title (preserva datos)
    op.alter_column('tasks', 'name', new_column_name='title')
    # Agregar description
    op.add_column('tasks', sa.Column('description', sa.Text(), nullable=True))
    # Agregar phase
    op.add_column('tasks', sa.Column('phase', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'phase')
    op.drop_column('tasks', 'description')
    op.alter_column('tasks', 'title', new_column_name='name')