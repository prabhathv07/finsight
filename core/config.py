import os
from functools import lru_cache


class Settings:
    """Runtime configuration pulled from the environment.

    Local development falls back to the Postgres instance defined in
    infra/docker-compose.yml. Nothing here should ever carry a real
    secret as a default.
    """

    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg2://finsight:finsight@localhost:5432/finsight",
        )
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        # Optional keyed fallback provider. Empty means yfinance only.
        self.polygon_api_key = os.getenv("POLYGON_API_KEY", "")

        self.timezone = os.getenv("FINSIGHT_TZ", "America/Chicago")

    def has_polygon(self):
        return bool(self.polygon_api_key)


@lru_cache
def get_settings():
    return Settings()
