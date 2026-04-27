"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Rule Repository server.

    All values are read from environment variables. See .env.example for the full list.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://rule:rule@localhost:5432/ruledb"

    # Elasticsearch
    elasticsearch_url: str = "http://localhost:9200"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "ruledev"

    # Gemini
    gemini_api_key: str = ""

    # LLM model selection
    llm_default_model: str = "gemini-3-flash-preview"
    llm_judge_model: str = "gemini-3.1-pro-preview"

    # Logging
    log_level: str = "INFO"

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Auth
    auth_required: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # File storage
    file_storage_path: str = "/tmp/rulerepo-files"

    # GitHub App integration
    github_app_id: str = ""
    github_app_private_key: str = ""
    github_webhook_secret: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
