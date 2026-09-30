"""add monitoring health fields

Revision ID: f3a9b7c21d4e
Revises: 81757b410cdd
Create Date: 2026-09-30 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3a9b7c21d4e'
down_revision: Union[str, Sequence[str], None] = '81757b410cdd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('repositories', sa.Column('last_polled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('repositories', sa.Column('last_successful_poll_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('repositories', sa.Column('last_processed_sha', sa.String(), nullable=True))
    op.add_column('repositories', sa.Column('last_seen_sha', sa.String(), nullable=True))
    op.add_column('repositories', sa.Column('last_poll_error', sa.String(), nullable=True))
    op.add_column('repositories', sa.Column('last_etag', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('repositories', 'last_etag')
    op.drop_column('repositories', 'last_poll_error')
    op.drop_column('repositories', 'last_seen_sha')
    op.drop_column('repositories', 'last_processed_sha')
    op.drop_column('repositories', 'last_successful_poll_at')
    op.drop_column('repositories', 'last_polled_at')
