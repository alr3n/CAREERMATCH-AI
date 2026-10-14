from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

Freshness = Literal["fresh", "recent", "stale"]
EmploymentType = Literal["full_time", "part_time", "contract", "internship", "temporary", "unknown"]
WorkArrangement = Literal["remote", "hybrid", "onsite", "unknown"]
ExperienceLevel = Literal["internship", "entry", "mid", "senior", "unknown"]


class JobSkillOut(ORMModel):
    skill: str
    category: str | None
    requirement: Literal["required", "preferred", "mentioned"]
    evidence: str | None


class JobSummaryOut(BaseModel):
    id: uuid.UUID
    title: str
    company: str
    location: str | None
    work_arrangement: WorkArrangement
    employment_type: EmploymentType
    experience_level: ExperienceLevel
    category: str | None
    salary_min: Decimal | None
    salary_max: Decimal | None
    salary_currency: str | None
    salary_interval: str | None
    salary_text: str | None
    posted_at: datetime | None
    deadline: datetime | None
    apply_url: str
    last_checked_at: datetime
    freshness: Freshness
    status: str
    provider: str
    source_name: str
    is_demo: bool
    is_saved: bool = False
    required_skills: list[str] = []


class JobDetailOut(JobSummaryOut):
    description: str
    required_qualifications: list[str]
    preferred_qualifications: list[str]
    skills: list[JobSkillOut]
    min_years_experience: int | None
    department: str | None
    country: str | None
    source_attribution: str


class JobFilters(BaseModel):
    q: str | None = Field(default=None, max_length=200, description="Keywords matched against title, company, description")
    employment_types: list[EmploymentType] = []
    work_arrangements: list[WorkArrangement] = []
    experience_levels: list[ExperienceLevel] = []
    categories: list[str] = Field(default_factory=list, max_length=20)
    location: str | None = Field(default=None, max_length=120)
    skills: list[str] = Field(default_factory=list, max_length=20, description="Listing must mention all of these skills")
    salary_min: Decimal | None = Field(default=None, ge=0, description="Only listings with salary data at or above this")
    salary_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    checked_within_days: int | None = Field(default=None, ge=1, le=365)
    include_demo: bool = True
    saved_only: bool = False
    sort: Literal["recently_checked", "posted", "title"] = "recently_checked"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class JobSourceOut(ORMModel):
    id: uuid.UUID
    provider: str
    identifier: str
    display_name: str
    is_demo: bool
    enabled: bool
    last_fetched_at: datetime | None
    last_status: str
    last_error: str | None
    last_fetch_count: int | None
    active_listings: int = 0


class ProviderStatus(BaseModel):
    provider: str
    name: str
    configured: bool
    sources: list[str]
    docs: str
    notes: str
    config_variable: str


class SourcesResponse(BaseModel):
    sources: list[JobSourceOut]
    providers: list[ProviderStatus]
    demo_enabled: bool
    unsupported_note: str


class RefreshItem(BaseModel):
    provider: str
    identifier: str
    status: Literal["ok", "error", "rate_limited", "skipped_cooldown"]
    fetched: int = 0
    created: int = 0
    updated: int = 0
    expired: int = 0
    duplicates: int = 0
    skipped_invalid: int = 0
    message: str | None = None


class RefreshResponse(BaseModel):
    results: list[RefreshItem]
    refreshed_at: datetime


class FacetCount(BaseModel):
    value: str
    count: int


class FacetsOut(BaseModel):
    total_active: int
    live_active: int
    demo_active: int
    categories: list[FacetCount]
    locations: list[FacetCount]
    skills: list[FacetCount]
    last_checked_at: datetime | None
