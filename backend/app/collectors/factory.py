from app.collectors.base import FootballDataProvider
from app.collectors.api_football_provider import ApiFootballProvider
from app.collectors.flashscore_provider import FlashScoreRapidApiProvider
from app.collectors.mock_provider import MockFootballDataProvider
from app.core.config import get_settings


def get_provider() -> FootballDataProvider:
    settings = get_settings()
    provider = settings.data_provider.strip().lower()
    if provider in {"api_football", "api-football", "football_api"}:
        return ApiFootballProvider()
    if provider in {"flashscore", "rapidapi_flashscore"}:
        return FlashScoreRapidApiProvider()
    if provider == "mock":
        return MockFootballDataProvider()
    raise RuntimeError(
        f"Unsupported DATA_PROVIDER={settings.data_provider!r}. "
        "Use api_football, flashscore, or mock only in local tests."
    )
