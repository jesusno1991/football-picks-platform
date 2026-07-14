"""football information platform

Revision ID: 0004_football_info_platform
Revises: 0003_calendar_indexes
Create Date: 2026-07-14 19:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_football_info_platform"
down_revision = "0003_calendar_indexes"
branch_labels = None
depends_on = None


def _timestamps():
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "countries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=12), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("flag_url", sa.String(length=500), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_countries_code", "countries", ["code"])
    op.create_index("ix_countries_name", "countries", ["name"])

    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id"), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("competition_id", "name", name="uq_season_competition_name"),
    )
    op.create_index("ix_seasons_competition_id", "seasons", ["competition_id"])
    op.create_index("ix_seasons_name", "seasons", ["name"])
    op.create_index("ix_seasons_year", "seasons", ["year"])
    op.create_index("ix_seasons_is_current", "seasons", ["is_current"])

    op.create_table(
        "competition_rounds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id"), nullable=False),
        sa.Column("season", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("competition_id", "season", "name", name="uq_competition_round"),
    )
    op.create_index("ix_competition_rounds_competition_id", "competition_rounds", ["competition_id"])
    op.create_index("ix_competition_rounds_season", "competition_rounds", ["season"])
    op.create_index("ix_competition_rounds_name", "competition_rounds", ["name"])

    op.create_table(
        "team_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("alias", sa.String(length=180), nullable=False),
        sa.Column("source_provider", sa.String(length=80), nullable=True),
        sa.UniqueConstraint("team_id", "alias", name="uq_team_alias"),
    )
    op.create_index("ix_team_aliases_team_id", "team_aliases", ["team_id"])
    op.create_index("ix_team_aliases_alias", "team_aliases", ["alias"])
    op.create_index("ix_team_aliases_source_provider", "team_aliases", ["source_provider"])

    op.create_table(
        "coaches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(length=120), nullable=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("nationality", sa.String(length=120), nullable=True),
        sa.Column("photo_url", sa.String(length=500), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_coaches_external_id", "coaches", ["external_id"])
    op.create_index("ix_coaches_name", "coaches", ["name"])
    op.create_index("ix_coaches_nationality", "coaches", ["nationality"])

    op.create_table(
        "venues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(length=120), nullable=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("surface", sa.String(length=80), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_venues_external_id", "venues", ["external_id"])
    op.create_index("ix_venues_name", "venues", ["name"])
    op.create_index("ix_venues_city", "venues", ["city"])
    op.create_index("ix_venues_country", "venues", ["country"])

    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_id", sa.String(length=120), nullable=True),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("firstname", sa.String(length=120), nullable=True),
        sa.Column("lastname", sa.String(length=120), nullable=True),
        sa.Column("nationality", sa.String(length=120), nullable=True),
        sa.Column("birth_date", sa.DateTime(), nullable=True),
        sa.Column("position", sa.String(length=80), nullable=True),
        sa.Column("height", sa.String(length=40), nullable=True),
        sa.Column("weight", sa.String(length=40), nullable=True),
        sa.Column("photo_url", sa.String(length=500), nullable=True),
        sa.Column("current_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_players_external_id", "players", ["external_id"])
    op.create_index("ix_players_name", "players", ["name"])
    op.create_index("ix_players_nationality", "players", ["nationality"])
    op.create_index("ix_players_position", "players", ["position"])
    op.create_index("ix_players_current_team_id", "players", ["current_team_id"])

    op.create_table(
        "player_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("alias", sa.String(length=180), nullable=False),
        sa.Column("source_provider", sa.String(length=80), nullable=True),
        sa.UniqueConstraint("player_id", "alias", name="uq_player_alias"),
    )
    op.create_index("ix_player_aliases_player_id", "player_aliases", ["player_id"])
    op.create_index("ix_player_aliases_alias", "player_aliases", ["alias"])
    op.create_index("ix_player_aliases_source_provider", "player_aliases", ["source_provider"])

    op.create_table(
        "fixture_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("halftime_home", sa.Integer(), nullable=True),
        sa.Column("halftime_away", sa.Integer(), nullable=True),
        sa.Column("fulltime_home", sa.Integer(), nullable=True),
        sa.Column("fulltime_away", sa.Integer(), nullable=True),
        sa.Column("extratime_home", sa.Integer(), nullable=True),
        sa.Column("extratime_away", sa.Integer(), nullable=True),
        sa.Column("penalties_home", sa.Integer(), nullable=True),
        sa.Column("penalties_away", sa.Integer(), nullable=True),
        sa.Column("source_provider", sa.String(length=80), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("match_id", name="uq_fixture_score_match"),
    )
    op.create_index("ix_fixture_scores_match_id", "fixture_scores", ["match_id"])
    op.create_index("ix_fixture_scores_source_provider", "fixture_scores", ["source_provider"])

    op.create_table(
        "fixture_periods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("period_type", sa.String(length=60), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("home_score", sa.Integer(), nullable=True),
        sa.Column("away_score", sa.Integer(), nullable=True),
        sa.Column("source_provider", sa.String(length=80), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("match_id", "period_type", name="uq_fixture_period"),
    )
    op.create_index("ix_fixture_periods_match_id", "fixture_periods", ["match_id"])
    op.create_index("ix_fixture_periods_period_type", "fixture_periods", ["period_type"])
    op.create_index("ix_fixture_periods_source_provider", "fixture_periods", ["source_provider"])

    op.create_table(
        "fixture_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
        sa.Column("assist_player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
        sa.Column("minute", sa.Integer(), nullable=True),
        sa.Column("extra_minute", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("detail", sa.String(length=180), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("score_home", sa.Integer(), nullable=True),
        sa.Column("score_away", sa.Integer(), nullable=True),
        sa.Column("source_provider", sa.String(length=80), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        *_timestamps(),
    )
    for column in ["match_id", "team_id", "player_id", "assist_player_id", "minute", "event_type", "source_provider"]:
        op.create_index(f"ix_fixture_events_{column}", "fixture_events", [column])

    op.create_table(
        "fixture_lineups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
        sa.Column("coach_id", sa.Integer(), sa.ForeignKey("coaches.id"), nullable=True),
        sa.Column("formation", sa.String(length=40), nullable=True),
        sa.Column("line_type", sa.String(length=40), nullable=False),
        sa.Column("position", sa.String(length=40), nullable=True),
        sa.Column("grid", sa.String(length=40), nullable=True),
        sa.Column("shirt_number", sa.Integer(), nullable=True),
        sa.Column("is_captain", sa.Boolean(), nullable=False),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("source_provider", sa.String(length=80), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        *_timestamps(),
    )
    for column in ["match_id", "team_id", "player_id", "coach_id", "line_type", "source_provider"]:
        op.create_index(f"ix_fixture_lineups_{column}", "fixture_lineups", [column])

    op.create_table(
        "fixture_player_statistics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("minutes", sa.Float(), nullable=True),
        sa.Column("goals", sa.Float(), nullable=True),
        sa.Column("assists", sa.Float(), nullable=True),
        sa.Column("shots", sa.Float(), nullable=True),
        sa.Column("shots_on_target", sa.Float(), nullable=True),
        sa.Column("passes", sa.Float(), nullable=True),
        sa.Column("pass_accuracy", sa.Float(), nullable=True),
        sa.Column("tackles", sa.Float(), nullable=True),
        sa.Column("saves", sa.Float(), nullable=True),
        sa.Column("xg", sa.Float(), nullable=True),
        sa.Column("xa", sa.Float(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("yellow_cards", sa.Float(), nullable=True),
        sa.Column("red_cards", sa.Float(), nullable=True),
        sa.Column("source_provider", sa.String(length=80), nullable=True),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("match_id", "team_id", "player_id", name="uq_fixture_player_stat"),
    )
    for column in ["match_id", "team_id", "player_id", "source_provider"]:
        op.create_index(f"ix_fixture_player_statistics_{column}", "fixture_player_statistics", [column])

    op.create_table(
        "standings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id"), nullable=False),
        sa.Column("season", sa.String(length=40), nullable=False),
        sa.Column("group_name", sa.String(length=120), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("played", sa.Integer(), nullable=True),
        sa.Column("wins", sa.Integer(), nullable=True),
        sa.Column("draws", sa.Integer(), nullable=True),
        sa.Column("losses", sa.Integer(), nullable=True),
        sa.Column("goals_for", sa.Integer(), nullable=True),
        sa.Column("goals_against", sa.Integer(), nullable=True),
        sa.Column("goal_difference", sa.Integer(), nullable=True),
        sa.Column("points", sa.Integer(), nullable=True),
        sa.Column("form", sa.String(length=40), nullable=True),
        sa.Column("description", sa.String(length=180), nullable=True),
        sa.Column("source_provider", sa.String(length=80), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("competition_id", "season", "group_name", "team_id", name="uq_standing_row"),
    )
    for column in ["competition_id", "season", "group_name", "rank", "team_id", "source_provider"]:
        op.create_index(f"ix_standings_{column}", "standings", [column])

    op.create_table(
        "injuries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id"), nullable=True),
        sa.Column("reason", sa.String(length=180), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("source_provider", sa.String(length=80), nullable=True),
        *_timestamps(),
    )
    for column in ["player_id", "team_id", "competition_id", "status", "source_provider"]:
        op.create_index(f"ix_injuries_{column}", "injuries", [column])

    op.create_table(
        "suspensions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("competition_id", sa.Integer(), sa.ForeignKey("competitions.id"), nullable=True),
        sa.Column("reason", sa.String(length=180), nullable=True),
        sa.Column("matches_remaining", sa.Integer(), nullable=True),
        sa.Column("source_provider", sa.String(length=80), nullable=True),
        *_timestamps(),
    )
    for column in ["player_id", "team_id", "competition_id", "source_provider"]:
        op.create_index(f"ix_suspensions_{column}", "suspensions", [column])

    op.create_table(
        "provider_raw_responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("endpoint", sa.String(length=240), nullable=False),
        sa.Column("external_id", sa.String(length=120), nullable=True),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("response_status", sa.String(length=80), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("checksum", sa.String(length=120), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    for column in ["provider", "endpoint", "external_id", "requested_at", "response_status", "checksum", "expires_at"]:
        op.create_index(f"ix_provider_raw_responses_{column}", "provider_raw_responses", [column])

    op.create_table(
        "provider_entity_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("internal_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("provider_external_id", sa.String(length=120), nullable=False),
        sa.Column("provider_name", sa.String(length=180), nullable=True),
        sa.Column("normalized_name", sa.String(length=180), nullable=True),
        sa.Column("match_status", sa.String(length=60), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("entity_type", "provider", "provider_external_id", name="uq_provider_entity_mapping"),
    )
    for column in ["entity_type", "internal_id", "provider", "provider_external_id", "provider_name", "normalized_name", "match_status"]:
        op.create_index(f"ix_provider_entity_mappings_{column}", "provider_entity_mappings", [column])

    op.create_table(
        "api_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("endpoint", sa.String(length=240), nullable=False),
        sa.Column("requests_count", sa.Integer(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("rate_limit_remaining", sa.Integer(), nullable=True),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("provider", "endpoint", "period_start", "period_end", name="uq_api_usage_period"),
    )
    for column in ["provider", "endpoint", "period_start", "period_end"]:
        op.create_index(f"ix_api_usage_{column}", "api_usage", [column])

    op.create_table(
        "sync_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_type", sa.String(length=80), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("target_date", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("records_processed", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        *_timestamps(),
    )
    for column in ["job_type", "provider", "status", "target_date"]:
        op.create_index(f"ix_sync_jobs_{column}", "sync_jobs", [column])

    op.create_table(
        "sync_errors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sync_job_id", sa.Integer(), sa.ForeignKey("sync_jobs.id"), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=True),
        sa.Column("endpoint", sa.String(length=240), nullable=True),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("external_id", sa.String(length=120), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    for column in ["sync_job_id", "provider", "endpoint", "entity_type", "external_id", "created_at"]:
        op.create_index(f"ix_sync_errors_{column}", "sync_errors", [column])


def downgrade() -> None:
    for table in [
        "sync_errors",
        "sync_jobs",
        "api_usage",
        "provider_entity_mappings",
        "provider_raw_responses",
        "suspensions",
        "injuries",
        "standings",
        "fixture_player_statistics",
        "fixture_lineups",
        "fixture_events",
        "fixture_periods",
        "fixture_scores",
        "player_aliases",
        "players",
        "venues",
        "coaches",
        "team_aliases",
        "competition_rounds",
        "seasons",
        "countries",
    ]:
        op.drop_table(table)
