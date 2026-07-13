from app.collectors.base import FootballDataProvider
from app.collectors.flashscore_provider import FlashScoreRapidApiProvider
from app.collectors.mock_provider import MockFootballDataProvider
from app.core.config import get_settings


def get_provider() -> FootballDataProvider:
    settings = get_settings()
    if settings.data_provider in {"flashscore", "rapidapi_flashscore"}:
        return FlashScoreRapidApiProvider()
    if settings.data_provider == "mock":
        return MockFootballDataProvider()
    return MockFootballDataProvider()
