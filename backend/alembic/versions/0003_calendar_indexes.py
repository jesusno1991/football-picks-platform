"""calendar indexes

Revision ID: 0003_calendar_indexes
Revises: 0002_market_engine
Create Date: 2026-07-14
"""

from alembic import op


revision = "0003_calendar_indexes"
down_revision = "0002_market_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("idx_matches_kickoff_at", "matches", ["kickoff_at"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("idx_matches_kickoff_at", table_name="matches", if_exists=True)
