from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gateway_database_url: str = "postgresql+psycopg://aicery:aicery@localhost:5434/aicery_gateway"
    aicery_runtime_url: str = "http://localhost:8000"
    aicery_service_api_key: str = "dev"
    admin_token: str = "admin-dev"
    internal_webhook_secret: str = "internal-dev"
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_pro: str | None = None
    stripe_price_team: str | None = None
    checkout_success_url: str = "http://localhost:8081/ui/billing/success"
    checkout_cancel_url: str = "http://localhost:8081/ui/billing/cancel"
    api_version: str = "0.0.1"
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str | None = None
    otel_service_name: str = "aicery-gateway"
    otel_exporter_otlp_protocol: str = "http/protobuf"
    otel_resource_attributes: str | None = None
    jwt_enabled: bool = False
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_audience: str | None = None
    jwt_expire_minutes: int = 60
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 100
    rate_limit_backend: str = "memory"  # memory | redis
    redis_url: str = "redis://localhost:6380/0"
