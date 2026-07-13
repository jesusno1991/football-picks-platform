from app.collectors.base import FootballDataProvider
from app.collectors.mock_provider import MockFootballDataProvider
from app.core.config import get_settings


def get_provider() -> FootballDataProvider:
    settings = get_settings()
    if settings.data_provider == "mock":
        return MockFootballDataProvider()
    return MockFootballDataProvider()
