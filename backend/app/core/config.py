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

    # ------------------------------------------------------------------
    # Job sources. Defaults are employers verified (2026-10-16) to publish
    # Philippine openings through public, documented job-board APIs.
    # Set any of these to an empty value to turn that source off.
    # ------------------------------------------------------------------
    # Entries are "identifier" or "identifier:Company Name" (the name is shown
    # when the provider's API has no company field, as with Lever).
    greenhouse_boards_raw: str = Field(default="xendit:Xendit", alias="GREENHOUSE_BOARDS")
    lever_sites_raw: str = Field(
        default="coins:Coins.ph,lalamove:Lalamove,ninjavan:Ninja Van,tala:Tala", alias="LEVER_SITES"
    )
    lever_region: Literal["global", "eu"] = "global"
    smartrecruiters_companies_raw: str = Field(
        default="Sutherland,DeliveryHero:Delivery Hero (foodpanda),Grab,BoschGroup:Bosch,Canva,HomeCredit:Home Credit",
        alias="SMARTRECRUITERS_COMPANIES",
    )
    smartrecruiters_country: str = Field(default="ph", pattern=r"^([a-zA-Z]{2})?$")
    smartrecruiters_max_details: int = Field(default=100, ge=0, le=500)
    remotive_enabled: bool = True
    remotive_category: str = ""
    # JSearch (Google for Jobs aggregator: LinkedIn, Indeed, Glassdoor, JobStreet …). Needs a key.
    jsearch_api_key: str = Field(default="", repr=False)
    jsearch_queries_raw: str = Field(default="", alias="JSEARCH_QUERIES")
    jsearch_country: str = Field(default="ph", pattern=r"^[a-zA-Z]{2}$")
    jsearch_date_posted: Literal["all", "today", "3days", "week", "month"] = "month"
    jsearch_pages: int = Field(default=1, ge=1, le=5)
    jsearch_min_interval_minutes: int = Field(default=720, ge=60)
    # Keep only listings located in (or remote and open to) this country for
    # providers that return worldwide postings. "none" keeps everything.
    job_location_filter: Literal["ph", "none"] = "ph"
    provider_timeout_seconds: float = 15.0
    refresh_cooldown_minutes: int = 10
    listing_stale_days: int = 7
    # Background refresh interval inside the API process; 0 disables it (use
    # `python -m app.cli refresh-jobs` from cron instead).
    auto_refresh_minutes: int = Field(default=360, ge=0)

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
    def smartrecruiters_companies(self) -> list[str]:
        return _split_csv(self.smartrecruiters_companies_raw)

    @property
    def jsearch_queries(self) -> list[str]:
        # Semicolon-separated because queries contain commas ("developer in Makati, PH").
        return [q.strip() for q in self.jsearch_queries_raw.split(";") if q.strip()][:10]

    @property
    def jsearch_configured(self) -> bool:
        return bool(self.jsearch_api_key) and bool(self.jsearch_queries)

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)

    @property
    def llm_configured(self) -> bool:
        return self.llm_provider == "anthropic" and bool(self.anthropic_api_key) and bool(self.llm_model)


@lru_cache
def get_settings() -> Settings:
    return Settings()
