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

    # Tier toggles — control which optional services are required
    elasticsearch_enabled: bool = False
    neo4j_enabled: bool = False
    redis_enabled: bool = False
    mcp_enabled: bool = False

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

    # OIDC (RR-007)
    oidc_provider_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    default_tenant_id: str = "default"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # File storage
    file_storage_path: str = "/tmp/rulerepo-files"

    # GitHub App integration
    github_app_id: str = ""
    github_app_private_key: str = ""
    github_webhook_secret: str = ""

    # LLM provider abstraction (RR-010)
    llm_provider_primary: str = "gemini"
    llm_provider_fallback: str = ""
    llm_provider_self_hosted_url: str = ""
    llm_provider_self_hosted_api_key: str = ""
    llm_tenant_overrides: str = "{}"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # LLM cost guardrails (RR-027)
    llm_tenant_monthly_budget_usd: float = 0.0
    llm_tenant_budget_warning_threshold: float = 0.8

    # Audit WORM (RR-011)
    audit_worm_enabled: bool = False
    audit_worm_s3_bucket: str = ""
    audit_worm_s3_region: str = ""

    # Observability (RR-025)
    otel_exporter_otlp_endpoint: str = ""
    prometheus_enabled: bool = True

    # Weekly digest
    digest_webhook_url: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
