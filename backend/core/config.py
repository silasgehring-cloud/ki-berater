from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    api_version: str = Field(default="0.1.0")

    database_url: str = Field(
        default="postgresql+asyncpg://ki:ki@localhost:5432/ki",
    )
    redis_url: str = Field(default="redis://localhost:6379/0")
    qdrant_url: str = Field(default="http://localhost:6333")

    anthropic_api_key: str = Field(default="")
    google_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")

    stripe_api_key: str = Field(default="")
    stripe_webhook_secret: str = Field(default="")
    # Stripe Price-IDs per plan (set in Stripe dashboard, paste into .env).
    stripe_price_starter: str = Field(default="")
    stripe_price_growth: str = Field(default="")
    stripe_price_pro: str = Field(default="")
    stripe_price_enterprise: str = Field(default="")
    # Where Stripe Checkout sends the user back. {shop_id} placeholder optional.
    stripe_success_url: str = Field(default="https://example.com/billing/success")
    stripe_cancel_url: str = Field(default="https://example.com/billing/cancel")

    admin_api_key: str = Field(default="")
    cors_allow_origins: str = Field(default="*")
    rate_limit_default: str = Field(default="100/minute")
    # Empty -> in-memory storage (dev/CI). In prod, set to redis://... .
    rate_limit_storage_uri: str = Field(default="")

    # ":memory:" runs Qdrant embedded (dev/CI). Production: http(s)://host:6333.
    qdrant_mode: str = Field(default=":memory:")

    # Sentry — empty DSN = disabled (no errors sent).
    sentry_dsn: str = Field(default="")
    sentry_traces_sample_rate: float = Field(default=0.0)  # 0..1, 0 disables tracing
    sentry_environment: str = Field(default="")  # falls back to `environment`

    # DSGVO retention: conversations + messages + llm_usage older than this
    # are purged hourly. Override via .env if your AVV says otherwise.
    retention_days: int = Field(default=90)
    # Set to 0 to disable the in-process retention scheduler (e.g. when an
    # external cron/k8s CronJob handles purging).
    retention_loop_enabled: bool = Field(default=True)

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


settings = Settings()
