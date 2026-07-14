"""ultimate foundation tables

Revision ID: 0005_ultimate_foundation
Revises: 0004_football_info_platform
Create Date: 2026-07-14 20:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_ultimate_foundation"
down_revision = "0004_football_info_platform"
branch_labels = None
depends_on = None


def _timestamps():
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "referees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(length=120), nullable=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("nationality", sa.String(length=120), nullable=True),
        sa.Column("source_provider", sa.String(length=80), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("external_id"),
    )
    for column in ["external_id", "name", "nationality", "source_provider"]:
        op.create_index(f"ix_referees_{column}", "referees", [column])

    op.create_table(
        "squad_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("season", sa.String(length=40), nullable=False),
        sa.Column("shirt_number", sa.Integer(), nullable=True),
        sa.Column("position", sa.String(length=80), nullable=True),
        sa.Column("joined_at", sa.DateTime(), nullable=True),
        sa.Column("left_at", sa.DateTime(), nullable=True),
        sa.Column("source_provider", sa.String(length=80), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("team_id", "player_id", "season", name="uq_squad_member_season"),
    )
    for column in ["team_id", "player_id", "season", "position", "source_provider"]:
        op.create_index(f"ix_squad_members_{column}", "squad_members", [column])

    op.create_table(
        "standing_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id"), nullable=False),
        sa.Column("season", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phase", sa.String(length=120), nullable=True),
        sa.Column("source_provider", sa.String(length=80), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("competition_id", "season", "name", name="uq_standing_group"),
    )
    for column in ["competition_id", "season", "name", "phase", "source_provider"]:
        op.create_index(f"ix_standing_groups_{column}", "standing_groups", [column])

    op.create_table(
        "team_season_statistics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id"), nullable=True),
        sa.Column("season", sa.String(length=40), nullable=False),
        sa.Column("scope", sa.String(length=40), nullable=False),
        sa.Column("matches_played", sa.Integer(), nullable=True),
        sa.Column("goals_for", sa.Float(), nullable=True),
        sa.Column("goals_against", sa.Float(), nullable=True),
        sa.Column("xg_for", sa.Float(), nullable=True),
        sa.Column("xg_against", sa.Float(), nullable=True),
        sa.Column("shots", sa.Float(), nullable=True),
        sa.Column("shots_on_target", sa.Float(), nullable=True),
        sa.Column("corners_for", sa.Float(), nullable=True),
        sa.Column("corners_against", sa.Float(), nullable=True),
        sa.Column("cards", sa.Float(), nullable=True),
        sa.Column("btts_rate", sa.Float(), nullable=True),
        sa.Column("over_1_5_rate", sa.Float(), nullable=True),
        sa.Column("over_2_5_rate", sa.Float(), nullable=True),
        sa.Column("over_3_5_rate", sa.Float(), nullable=True),
        sa.Column("source_provider", sa.String(length=80), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("team_id", "competition_id", "season", "scope", name="uq_team_season_stat"),
    )
    for column in ["team_id", "competition_id", "season", "scope", "source_provider"]:
        op.create_index(f"ix_team_season_statistics_{column}", "team_season_statistics", [column])

    op.create_table(
        "player_season_statistics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id"), nullable=True),
        sa.Column("season", sa.String(length=40), nullable=False),
        sa.Column("appearances", sa.Integer(), nullable=True),
        sa.Column("minutes", sa.Float(), nullable=True),
        sa.Column("goals", sa.Float(), nullable=True),
        sa.Column("assists", sa.Float(), nullable=True),
        sa.Column("xg", sa.Float(), nullable=True),
        sa.Column("xa", sa.Float(), nullable=True),
        sa.Column("shots", sa.Float(), nullable=True),
        sa.Column("passes", sa.Float(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("yellow_cards", sa.Float(), nullable=True),
        sa.Column("red_cards", sa.Float(), nullable=True),
        sa.Column("source_provider", sa.String(length=80), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("player_id", "team_id", "competition_id", "season", name="uq_player_season_stat"),
    )
    for column in ["player_id", "team_id", "competition_id", "season", "source_provider"]:
        op.create_index(f"ix_player_season_statistics_{column}", "player_season_statistics", [column])

    op.create_table(
        "cache_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cache_key", sa.String(length=240), nullable=False),
        sa.Column("namespace", sa.String(length=80), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("cache_key", name="uq_cache_entry_key"),
    )
    for column in ["cache_key", "namespace", "expires_at"]:
        op.create_index(f"ix_cache_entries_{column}", "cache_entries", [column])

    op.create_table(
        "data_quality_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=True),
        sa.Column("completeness_score", sa.Float(), nullable=True),
        sa.Column("freshness_score", sa.Float(), nullable=True),
        sa.Column("reliability_score", sa.Float(), nullable=True),
        sa.Column("missing_fields", sa.Text(), nullable=True),
        sa.Column("warnings", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for column in ["entity_type", "entity_id", "provider", "created_at"]:
        op.create_index(f"ix_data_quality_snapshots_{column}", "data_quality_snapshots", [column])

    op.create_table(
        "model_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=True),
        sa.Column("model_name", sa.String(length=120), nullable=False),
        sa.Column("market", sa.String(length=120), nullable=True),
        sa.Column("version", sa.String(length=60), nullable=True),
        sa.Column("inputs_json", sa.Text(), nullable=True),
        sa.Column("output_json", sa.Text(), nullable=True),
        sa.Column("warnings", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for column in ["match_id", "model_name", "market", "version", "created_at"]:
        op.create_index(f"ix_model_audit_logs_{column}", "model_audit_logs", [column])


def downgrade() -> None:
    for table in [
        "model_audit_logs",
        "data_quality_snapshots",
        "cache_entries",
        "player_season_statistics",
        "team_season_statistics",
        "standing_groups",
        "squad_members",
        "referees",
    ]:
        op.drop_table(table)
