from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """IAM service configuration. All env vars use prefix IAM_ unless aliased."""

    model_config = SettingsConfigDict(env_prefix="IAM_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://iam:iam@127.0.0.1:5432/iam"
    redis_url: str = "redis://127.0.0.1:6379/1"

    jwt_issuer: str = "http://127.0.0.1:8100"
    jwt_audience: str = "devault-api"
    jwt_key_id: str = "iam-1"
    jwt_private_key: str = ""
    jwt_public_key: str = ""
    jwt_private_key_file: str = ""
    jwt_public_key_file: str = ""

    environment: Literal["development", "production"] = "development"

    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 604800
    login_rate_limit_per_minute: int = 60
    authorize_rate_limit_per_minute: int = 240

    permission_cache_ttl_seconds: int = 300
    api_key_access_token_ttl_seconds: int = 1800

    internal_api_token: str = ""

    metrics_enabled: bool = True
    http_access_log_enabled: bool = True
    access_log_json: bool = False

    cors_origins: str = ""

    @field_validator("cors_origins", mode="before")
    @classmethod
    def strip_cors(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v).strip()

    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins:
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def is_production(self) -> bool:
        return self.environment == "production"

    def assert_production_config(self) -> None:
        """Raise if production deployment is missing required secrets."""
        from devault_iam.bootstrap import resolve_jwt_private_pem, resolve_jwt_public_pem

        if not self.is_production():
            return
        if not resolve_jwt_private_pem(self).strip():
            raise RuntimeError(
                "production requires IAM_JWT_PRIVATE_KEY or IAM_JWT_PRIVATE_KEY_FILE to be set",
            )
        if not resolve_jwt_public_pem(self).strip():
            raise RuntimeError(
                "production requires IAM_JWT_PUBLIC_KEY or IAM_JWT_PUBLIC_KEY_FILE to be set",
            )
        if not (self.jwt_issuer or "").strip().lower().startswith("https://"):
            raise RuntimeError("production requires IAM_JWT_ISSUER to use an https:// URL")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
