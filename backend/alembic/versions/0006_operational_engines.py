"""operational engines

Revision ID: 0006_operational_engines
Revises: 0005_ultimate_foundation
Create Date: 2026-07-14 21:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_operational_engines"
down_revision = "0005_ultimate_foundation"
branch_labels = None
depends_on = None


def _idx(table: str, columns: list[str]) -> None:
    for column in columns:
        op.create_index(f"ix_{table}_{column}", table, [column])


def upgrade() -> None:
    op.create_table(
        "automation_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("engine", sa.String(length=80), nullable=False),
        sa.Column("task_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("records_processed", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=True),
    )
    _idx("automation_runs", ["engine", "task_name", "status", "started_at", "finished_at"])

    op.create_table(
        "historical_sync_windows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("scope", sa.String(length=80), nullable=False),
        sa.Column("date_from", sa.DateTime(), nullable=False),
        sa.Column("date_to", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("provider", "date_from", "date_to", "scope", name="uq_historical_sync_window"),
    )
    _idx("historical_sync_windows", ["provider", "scope", "date_from", "date_to", "status", "priority"])

    op.create_table(
        "provider_data_coverage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("data_type", sa.String(length=80), nullable=False),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id"), nullable=True),
        sa.Column("season", sa.String(length=40), nullable=True),
        sa.Column("available_count", sa.Integer(), nullable=False),
        sa.Column("missing_count", sa.Integer(), nullable=False),
        sa.Column("coverage_ratio", sa.Float(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("provider", "entity_type", "data_type", "country", "competition_id", "season", name="uq_provider_coverage"),
    )
    _idx("provider_data_coverage", ["provider", "entity_type", "data_type", "country", "competition_id", "season"])

    op.create_table(
        "market_rankings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prediction_id", sa.Integer(), sa.ForeignKey("predictions.id"), nullable=False),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("market", sa.String(length=120), nullable=False),
        sa.Column("selection", sa.String(length=120), nullable=False),
        sa.Column("line", sa.Float(), nullable=True),
        sa.Column("rank_score", sa.Float(), nullable=False),
        sa.Column("grade", sa.String(length=10), nullable=False),
        sa.Column("publish_decision", sa.String(length=60), nullable=False),
        sa.Column("factors_json", sa.Text(), nullable=True),
        sa.Column("ranked_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("prediction_id", name="uq_market_ranking_prediction"),
    )
    _idx("market_rankings", ["prediction_id", "match_id", "market", "selection", "rank_score", "grade", "publish_decision", "ranked_at"])

    op.create_table(
        "publication_queue",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prediction_id", sa.Integer(), sa.ForeignKey("predictions.id"), nullable=True),
        sa.Column("market_ranking_id", sa.Integer(), sa.ForeignKey("market_rankings.id"), nullable=True),
        sa.Column("channel", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    _idx("publication_queue", ["prediction_id", "market_ranking_id", "channel", "status", "priority", "scheduled_at", "published_at", "created_at"])

    op.create_table(
        "calibration_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("market", sa.String(length=120), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("brier_score", sa.Float(), nullable=True),
        sa.Column("calibration_error", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("report_json", sa.Text(), nullable=True),
    )
    _idx("calibration_runs", ["model_name", "market", "status", "started_at", "finished_at"])


def downgrade() -> None:
    for table in [
        "calibration_runs",
        "publication_queue",
        "market_rankings",
        "provider_data_coverage",
        "historical_sync_windows",
        "automation_runs",
    ]:
        op.drop_table(table)
