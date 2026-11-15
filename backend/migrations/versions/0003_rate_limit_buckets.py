"""Add shared registration rate-limit buckets.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_buckets",
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("key_hash"),
    )
    op.create_index("ix_rate_limit_buckets_expires_at", "rate_limit_buckets", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_rate_limit_buckets_expires_at", table_name="rate_limit_buckets")
    op.drop_table("rate_limit_buckets")
