from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DEVAULT_",
        env_file=".env",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+psycopg://devault:devault@localhost:5432/devault",
        description="SQLAlchemy URL for platform metadata DB",
    )
    redis_url: str = Field(default="redis://localhost:6379/0")

    api_token: str | None = Field(default=None, description="If set, require Authorization: Bearer")

    storage_backend: str = Field(default="local", description="local | s3")
    local_storage_root: str = Field(default="./data/storage")

    s3_endpoint: str | None = Field(default=None, description="MinIO/S3 endpoint URL")
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket: str = "devault"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False

    env_name: str = Field(default="dev", description="Key prefix segment dev|prod")

    allowed_path_prefixes: str | None = Field(
        default=None,
        description="Comma-separated absolute path prefixes; if set, backup paths must match one",
    )

    @property
    def allowed_prefix_list(self) -> list[str] | None:
        if not self.allowed_path_prefixes:
            return None
        parts = [p.strip() for p in self.allowed_path_prefixes.split(",") if p.strip()]
        return parts or None

    @field_validator("storage_backend")
    @classmethod
    def storage_ok(cls, v: str) -> str:
        v = v.lower()
        if v not in ("local", "s3"):
            raise ValueError("storage_backend must be local or s3")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
