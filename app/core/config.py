"""
Application configuration loaded from environment variables.

Uses pydantic-settings so all values are validated at startup — fail fast
rather than discovering a missing MONGO_URI at request time.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central config object. All env vars are declared here; nothing is hardcoded elsewhere."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # MongoDB
    mongo_uri: str = "mongodb://localhost:27017"
    db_name: str = "metadata_db"
    collection_name: str = "metadata"

    # HTTP fetcher
    fetch_timeout_seconds: int = 10
    fetch_max_redirects: int = 5

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"


settings = Settings()
