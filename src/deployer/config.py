from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "deployer"
    app_version: str = "0.1.0"
    environment: str = "development"  # development | staging | production
    debug: bool = False
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # Auth
    api_keys: list[str] = []
    require_auth: bool = True

    # LLM Provider
    llm_provider: str = "openai"  # openai | anthropic
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    default_model: str = "gpt-4o-mini"
    request_timeout: int = 60

    # Rate Limiting
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    # Cache
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Circuit Breaker
    circuit_breaker_threshold: int = 5
    circuit_breaker_recovery_seconds: int = 30

    # CORS
    cors_origins: list[str] = ["*"]

    @field_validator("api_keys", "cors_origins", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v  # type: ignore[return-value]

    @field_validator("log_level", mode="before")
    @classmethod
    def uppercase_log_level(cls, v: object) -> str:
        if isinstance(v, str):
            return v.upper()
        return str(v)


settings = Settings()
