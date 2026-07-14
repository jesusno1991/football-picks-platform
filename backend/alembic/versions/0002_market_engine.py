"""market engine schema

Revision ID: 0002_market_engine
Revises: 0001_initial
Create Date: 2026-07-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_market_engine"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for column in [
        sa.Column("provider", sa.String(80), nullable=True),
        sa.Column("event_id", sa.String(120), nullable=True),
        sa.Column("fixture_id", sa.String(120), nullable=True),
        sa.Column("provider_competition_id", sa.String(120), nullable=True),
        sa.Column("market_family", sa.String(80), nullable=True),
        sa.Column("market_name_raw", sa.String(180), nullable=True),
        sa.Column("period", sa.String(40), nullable=True),
        sa.Column("team_scope", sa.String(40), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("validation_status", sa.String(60), nullable=True),
    ]:
        op.add_column("odds", column)

    op.create_table(
        "market_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(120), nullable=False, unique=True),
        sa.Column("family", sa.String(80), nullable=False),
        sa.Column("period", sa.String(40), nullable=False),
        sa.Column("team_scope", sa.String(40), nullable=False),
        sa.Column("selection", sa.String(80), nullable=False),
        sa.Column("line", sa.Float(), nullable=True),
        sa.Column("settlement_type", sa.String(80), nullable=False),
        sa.Column("is_supported", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_publishable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.UniqueConstraint(
            "family",
            "period",
            "team_scope",
            "selection",
            "line",
            "settlement_type",
            name="uq_market_definition_logic",
        ),
    )
    op.create_table(
        "model_probabilities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id")),
        sa.Column("market_definition_id", sa.Integer(), sa.ForeignKey("market_definitions.id")),
        sa.Column("probability_full_win", sa.Float()),
        sa.Column("probability_half_win", sa.Float()),
        sa.Column("probability_push", sa.Float()),
        sa.Column("probability_half_loss", sa.Float()),
        sa.Column("probability_full_loss", sa.Float()),
        sa.Column("model_probability", sa.Float()),
        sa.Column("fair_odds", sa.Float()),
        sa.Column("confidence", sa.Float()),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("feature_snapshot", sa.Text()),
        sa.Column("generated_at", sa.DateTime()),
    )
    op.create_table(
        "market_evaluations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id")),
        sa.Column("fixture_id", sa.String(120)),
        sa.Column("market_definition_id", sa.Integer(), sa.ForeignKey("market_definitions.id")),
        sa.Column("probability_full_win", sa.Float()),
        sa.Column("probability_half_win", sa.Float()),
        sa.Column("probability_push", sa.Float()),
        sa.Column("probability_half_loss", sa.Float()),
        sa.Column("probability_full_loss", sa.Float()),
        sa.Column("fair_odds", sa.Float()),
        sa.Column("market_odds", sa.Float()),
        sa.Column("expected_value", sa.Float()),
        sa.Column("bookmaker", sa.String(120)),
        sa.Column("merlin_score", sa.Float()),
        sa.Column("data_quality", sa.Float()),
        sa.Column("risk_level", sa.String(40)),
        sa.Column("validation_status", sa.String(60), nullable=False),
        sa.Column("decision", sa.String(60), nullable=False),
        sa.Column("reasons", sa.Text()),
        sa.Column("alerts", sa.Text()),
        sa.Column("evaluated_at", sa.DateTime()),
        sa.UniqueConstraint("match_id", "market_definition_id", "bookmaker", name="uq_market_eval_bookmaker"),
    )
    op.create_table(
        "prediction_features",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prediction_id", sa.Integer(), sa.ForeignKey("predictions.id")),
        sa.Column("market_evaluation_id", sa.Integer(), sa.ForeignKey("market_evaluations.id")),
        sa.Column("features_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "prediction_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("prediction_id", sa.Integer(), sa.ForeignKey("predictions.id")),
        sa.Column("settlement_status", sa.String(40), nullable=False),
        sa.Column("profit_units", sa.Float()),
        sa.Column("settled_score_home", sa.Integer()),
        sa.Column("settled_score_away", sa.Integer()),
        sa.Column("settled_at", sa.DateTime()),
    )
    op.create_table(
        "settlement_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("settlement_type", sa.String(80), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "model_calibrations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_name", sa.String(120), nullable=False),
        sa.Column("market_family", sa.String(80), nullable=False),
        sa.Column("period", sa.String(40), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("brier_score", sa.Float()),
        sa.Column("calibration_error", sa.Float()),
        sa.Column("is_production_validated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime()),
    )


def downgrade() -> None:
    for table in [
        "model_calibrations",
        "settlement_rules",
        "prediction_results",
        "prediction_features",
        "market_evaluations",
        "model_probabilities",
        "market_definitions",
    ]:
        op.drop_table(table)
    for column in [
        "validation_status",
        "raw_payload",
        "team_scope",
        "period",
        "market_name_raw",
        "market_family",
        "provider_competition_id",
        "fixture_id",
        "event_id",
        "provider",
    ]:
        op.drop_column("odds", column)
