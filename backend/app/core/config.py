"""Application configuration loaded from environment variables.

All secrets and deployment-specific values come from the environment (or a
local ``.env`` file). Nothing sensitive is hardcoded here.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_DEFAULT_SECRET = "change-me-to-a-long-random-string"


def _split_csv(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [v.strip() for v in value if v and v.strip()]
    return [v.strip() for v in value.split(",") if v.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "CareerMatch AI"
    app_env: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"

    secret_key: str = INSECURE_DEFAULT_SECRET
    access_token_expire_minutes: int = Field(default=60, ge=5, le=60 * 24 * 7)
    jwt_algorithm: str = "HS256"

    database_url: str = "sqlite:///./careermatch.db"

    cors_origins_raw: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    max_upload_mb: float = Field(default=5, gt=0, le=25)
    storage_dir: Path = Path("./storage")
    retain_resume_files: bool = False
    max_resume_chars: int = 60_000

    greenhouse_boards_raw: str = Field(default="", alias="GREENHOUSE_BOARDS")
    lever_sites_raw: str = Field(default="", alias="LEVER_SITES")
    lever_region: Literal["global", "eu"] = "global"
    provider_timeout_seconds: float = 15.0
    refresh_cooldown_minutes: int = 10
    listing_stale_days: int = 7
    enable_demo_provider: bool = True

    embedding_backend: Literal["auto", "sentence-transformers", "lsa"] = "auto"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    llm_provider: Literal["none", "anthropic"] = "none"
    anthropic_api_key: str = ""
    llm_model: str = ""
    llm_timeout_seconds: float = 60.0

    # Rate limits: "<requests>/<seconds>"
    rate_limit_auth: str = "10/60"
    rate_limit_upload: str = "10/3600"
    rate_limit_refresh: str = "6/3600"
    rate_limit_match: str = "30/3600"
    rate_limit_assistant: str = "30/3600"

    evaluation_report_path: Path = Path(__file__).resolve().parents[3] / "ml" / "artifacts" / "evaluation_report.json"

    @field_validator("storage_dir", mode="before")
    @classmethod
    def _expand_storage(cls, v: str | Path) -> Path:
        return Path(v).expanduser()

    @model_validator(mode="after")
    def _production_guards(self) -> Settings:
        if self.app_env == "production":
            if self.secret_key == INSECURE_DEFAULT_SECRET or len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be set to a random value of at least 32 characters in production")
            # Demo data must never be mixed into a production deployment.
            self.enable_demo_provider = False
        return self

    @property
    def cors_origins(self) -> list[str]:
        return _split_csv(self.cors_origins_raw)

    @property
    def greenhouse_boards(self) -> list[str]:
        return _split_csv(self.greenhouse_boards_raw)

    @property
    def lever_sites(self) -> list[str]:
        return _split_csv(self.lever_sites_raw)

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)

    @property
    def llm_configured(self) -> bool:
        return self.llm_provider == "anthropic" and bool(self.anthropic_api_key) and bool(self.llm_model)


@lru_cache
def get_settings() -> Settings:
    return Settings()
