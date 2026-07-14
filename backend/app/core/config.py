from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(default="sqlite:///./football_picks.db", alias="DATABASE_URL")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    admin_email: str = Field(default="admin@example.com", alias="ADMIN_EMAIL")
    admin_password: str = Field(default="admin", alias="ADMIN_PASSWORD")
    football_api_key: str | None = Field(default=None, alias="FOOTBALL_API_KEY")
    api_football_key: str | None = Field(default=None, alias="API_FOOTBALL_KEY")
    api_football_base_url: str = Field(
        default="https://v3.football.api-sports.io",
        alias="API_FOOTBALL_BASE_URL",
    )
    odds_api_key: str | None = Field(default=None, alias="ODDS_API_KEY")
    rapidapi_key: str | None = Field(default=None, alias="RAPIDAPI_KEY")
    flashscore_rapidapi_host: str = Field(default="flashscore4.p.rapidapi.com", alias="FLASHSCORE_RAPIDAPI_HOST")
    flashscore_matches_path: str | None = Field(default=None, alias="FLASHSCORE_MATCHES_PATH")
    flashscore_odds_path: str | None = Field(default=None, alias="FLASHSCORE_ODDS_PATH")
    flashscore_team_history_path: str | None = Field(default=None, alias="FLASHSCORE_TEAM_HISTORY_PATH")
    data_provider: str = Field(default="mock", alias="DATA_PROVIDER")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    backend_url: str = Field(default="http://localhost:8000", alias="BACKEND_URL")
    app_timezone: str = Field(default="Europe/Madrid", alias="APP_TIMEZONE")

    admin_token_header: str = "X-Admin-Token"
    minimum_minutes_before_kickoff: int = 15


@lru_cache
def get_settings() -> Settings:
    return Settings()
