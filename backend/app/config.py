"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Any

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Application Settings
    # ==========================================================================
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    frontend_url: str = Field(
        default="http://localhost:3000", description="Frontend URL for CORS"
    )
    secret_key: str = Field(
        default="change-me-in-production", description="Secret key for JWT"
    )

    # ==========================================================================
    # Database Settings
    # ==========================================================================
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="stockresearch", description="Database name")
    postgres_user: str = Field(default="stockuser", description="Database user")
    postgres_password: str = Field(default="", description="Database password")
    database_url: str | None = Field(default=None, description="Full database URL")

    @property
    def async_database_url(self) -> str:
        """Get async database URL."""
        if self.database_url:
            # Convert to async driver if needed
            url = self.database_url
            if "postgresql://" in url:
                return url.replace("postgresql://", "postgresql+asyncpg://")
            return url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """Get sync database URL for Alembic."""
        if self.database_url:
            url = self.database_url
            if "asyncpg" in url:
                return url.replace("postgresql+asyncpg://", "postgresql://")
            return url
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ==========================================================================
    # Redis Settings
    # ==========================================================================
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: str = Field(default="", description="Redis password")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_url: str | None = Field(default=None, description="Full Redis URL")

    @property
    def redis_connection_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_url:
            return self.redis_url
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ==========================================================================
    # Celery Settings
    # ==========================================================================
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1", description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2", description="Celery result backend"
    )

    # ==========================================================================
    # API Keys
    # ==========================================================================
    alpha_vantage_api_key: str = Field(default="", description="Alpha Vantage API key")
    fmp_api_key: str = Field(default="", description="Financial Modeling Prep API key")
    sec_user_agent: str = Field(
        default="StockResearchTool/1.0 admin@example.com",
        description="SEC EDGAR user agent",
    )

    # ==========================================================================
    # Rate Limiting
    # ==========================================================================
    rate_limit_per_hour: int = Field(
        default=100, description="Rate limit per hour per user"
    )
    alpha_vantage_rate_limit: int = Field(
        default=30, description="Alpha Vantage requests per minute"
    )
    sec_rate_limit: int = Field(
        default=10, description="SEC EDGAR requests per second"
    )

    # ==========================================================================
    # Ollama Settings
    # ==========================================================================
    ollama_base_url: str = Field(
        default="http://localhost:11434", description="Ollama server URL"
    )
    ollama_model: str = Field(default="mistral:7b", description="Default Ollama model")

    # ==========================================================================
    # Logging
    # ==========================================================================
    log_level: str = Field(default="INFO", description="Log level")
    json_logs: bool = Field(default=False, description="Use JSON structured logging")

    # ==========================================================================
    # Monitoring
    # ==========================================================================
    sentry_dsn: str | None = Field(default=None, description="Sentry DSN")
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience function for dependency injection
def get_config() -> Settings:
    """Get settings for FastAPI dependency injection."""
    return get_settings()


settings = Settings()