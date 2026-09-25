"""Persist risk-history score deltas.

Revision ID: c8d0f3a9b1e2
Revises: a44e48c9cbd9
"""
from alembic import op
import sqlalchemy as sa

revision = "c8d0f3a9b1e2"
down_revision = "a44e48c9cbd9"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("risk_scores", sa.Column("score_delta", sa.Integer(), nullable=True))

def downgrade() -> None:
    op.drop_column("risk_scores", "score_delta")
