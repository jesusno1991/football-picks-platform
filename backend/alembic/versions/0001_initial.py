"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-13
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "competitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(120), nullable=False, unique=True),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("country", sa.String(120), nullable=False),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("season", sa.String(40), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(120), nullable=False, unique=True),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("short_name", sa.String(80)),
        sa.Column("country", sa.String(120)),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(120), nullable=False, unique=True),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id")),
        sa.Column("home_team_id", sa.Integer(), sa.ForeignKey("teams.id")),
        sa.Column("away_team_id", sa.Integer(), sa.ForeignKey("teams.id")),
        sa.Column("kickoff_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("home_score", sa.Integer()),
        sa.Column("away_score", sa.Integer()),
        sa.Column("home_corners", sa.Integer()),
        sa.Column("away_corners", sa.Integer()),
        sa.Column("venue", sa.String(180)),
        sa.Column("round", sa.String(80)),
        sa.Column("season", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_table(
        "team_match_statistics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id")),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id")),
        sa.Column("is_home", sa.Boolean(), nullable=False),
        sa.Column("possession", sa.Float()),
        sa.Column("shots", sa.Float()),
        sa.Column("shots_on_target", sa.Float()),
        sa.Column("corners", sa.Float()),
        sa.Column("dangerous_attacks", sa.Float()),
        sa.Column("goals", sa.Float()),
        sa.Column("xg", sa.Float()),
        sa.Column("yellow_cards", sa.Float()),
        sa.Column("red_cards", sa.Float()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "team_form",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id")),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id")),
        sa.Column("reference_date", sa.DateTime(), nullable=False),
        sa.Column("matches_sample", sa.Integer(), nullable=False),
        sa.Column("goals_for_avg", sa.Float()),
        sa.Column("goals_against_avg", sa.Float()),
        sa.Column("first_half_goals_avg", sa.Float()),
        sa.Column("second_half_goals_avg", sa.Float()),
        sa.Column("corners_for_avg", sa.Float()),
        sa.Column("corners_against_avg", sa.Float()),
        sa.Column("shots_avg", sa.Float()),
        sa.Column("shots_on_target_avg", sa.Float()),
        sa.Column("xg_avg", sa.Float()),
        sa.Column("xga_avg", sa.Float()),
        sa.Column("big_chances_avg", sa.Float()),
        sa.Column("dangerous_attacks_avg", sa.Float()),
        sa.Column("possession_avg", sa.Float()),
        sa.Column("over_8_5_corners_rate", sa.Float()),
        sa.Column("over_9_5_corners_rate", sa.Float()),
        sa.Column("over_10_5_corners_rate", sa.Float()),
        sa.Column("btts_rate", sa.Float()),
        sa.Column("over_1_5_goals_rate", sa.Float()),
        sa.Column("over_2_5_goals_rate", sa.Float()),
        sa.Column("over_3_5_goals_rate", sa.Float()),
        sa.Column("home_away_sample", sa.Integer()),
        sa.Column("h2h_goals_avg", sa.Float()),
        sa.Column("h2h_btts_rate", sa.Float()),
        sa.Column("clean_sheet_rate", sa.Float()),
        sa.Column("created_at", sa.DateTime()),
        sa.UniqueConstraint("team_id", "competition_id", "reference_date", name="uq_team_form_ref"),
    )
    op.create_table(
        "odds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id")),
        sa.Column("bookmaker", sa.String(120), nullable=False),
        sa.Column("market", sa.String(120), nullable=False),
        sa.Column("selection", sa.String(120), nullable=False),
        sa.Column("line", sa.Float()),
        sa.Column("odds", sa.Float(), nullable=False),
        sa.Column("collected_at", sa.DateTime()),
        sa.Column("is_closing_odds", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "prediction_systems",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("market", sa.String(120), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("minimum_probability", sa.Float(), nullable=False),
        sa.Column("minimum_value", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id")),
        sa.Column("system_id", sa.Integer(), sa.ForeignKey("prediction_systems.id")),
        sa.Column("market", sa.String(120), nullable=False),
        sa.Column("selection", sa.String(120), nullable=False),
        sa.Column("line", sa.Float()),
        sa.Column("predicted_probability", sa.Float()),
        sa.Column("fair_odds", sa.Float()),
        sa.Column("available_odds", sa.Float()),
        sa.Column("expected_value", sa.Float()),
        sa.Column("confidence", sa.Float()),
        sa.Column("recommended_stake", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("feature_snapshot", sa.Text()),
        sa.Column("generated_at", sa.DateTime()),
        sa.Column("published_at", sa.DateTime()),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("result", sa.String(40)),
        sa.Column("profit", sa.Float()),
        sa.Column("closing_odds", sa.Float()),
        sa.Column("verified_at", sa.DateTime()),
        sa.UniqueConstraint("match_id", "system_id", "market", "selection", "line", name="uq_prediction_market"),
    )
    op.create_table(
        "system_performance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("system_id", sa.Integer(), sa.ForeignKey("prediction_systems.id")),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id")),
        sa.Column("market", sa.String(120), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("wins", sa.Integer(), nullable=False),
        sa.Column("losses", sa.Integer(), nullable=False),
        sa.Column("voids", sa.Integer(), nullable=False),
        sa.Column("total_stake", sa.Float(), nullable=False),
        sa.Column("total_profit", sa.Float(), nullable=False),
        sa.Column("yield_percentage", sa.Float(), nullable=False),
        sa.Column("hit_rate", sa.Float(), nullable=False),
        sa.Column("average_odds", sa.Float(), nullable=False),
        sa.Column("maximum_drawdown", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime()),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(180), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )


def downgrade() -> None:
    for table in [
        "users",
        "system_performance",
        "predictions",
        "prediction_systems",
        "odds",
        "team_form",
        "team_match_statistics",
        "matches",
        "teams",
        "competitions",
    ]:
        op.drop_table(table)
