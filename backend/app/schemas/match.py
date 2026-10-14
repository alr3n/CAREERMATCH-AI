from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.ml.scoring import DEFAULT_WEIGHTS
from app.schemas.job import EmploymentType, ExperienceLevel, JobDetailOut, JobSummaryOut, WorkArrangement

SCORE_DISCLAIMER = (
    "The compatibility score (0–100) summarises how well your resume profile and preferences align with the "
    "posting. It is not a probability of being hired, and a skill 'not found in your resume' may simply be "
    "unlisted rather than missing."
)


class MatchFilters(BaseModel):
    employment_types: list[EmploymentType] = []
    work_arrangements: list[WorkArrangement] = []
    experience_levels: list[ExperienceLevel] = []
    categories: list[str] = Field(default_factory=list, max_length=20)
    location: str | None = Field(default=None, max_length=120)
    checked_within_days: int | None = Field(default=None, ge=1, le=365)
    include_demo: bool = True


class MatchRequest(BaseModel):
    preset: Literal["balanced", "skills_first", "preferences_first"] = "balanced"
    weights: dict[str, float] | None = Field(
        default=None, description="Custom weights per component (non-negative); overrides the preset"
    )
    filters: MatchFilters = MatchFilters()
    limit: int = Field(default=50, ge=1, le=100)

    @field_validator("weights")
    @classmethod
    def _valid_weights(cls, v: dict[str, float] | None) -> dict[str, float] | None:
        if v is None:
            return None
        unknown = set(v) - set(DEFAULT_WEIGHTS)
        if unknown:
            raise ValueError(f"Unknown weight keys: {', '.join(sorted(unknown))}")
        if any(x < 0 or x > 10 for x in v.values()):
            raise ValueError("Weights must be between 0 and 10")
        if sum(v.values()) <= 0:
            raise ValueError("At least one weight must be positive")
        return v


class MatchEvidenceOut(BaseModel):
    kind: str
    label: str
    detail: str | None
    requirement: str | None


class MatchSummaryOut(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    rank: int
    score: float
    evidence_coverage: float
    components: dict[str, float | None]
    matched_skills: list[str]
    related_skills: list[str]
    missing_required: list[str]
    missing_preferred: list[str]
    top_reason: str | None
    job: JobSummaryOut


class MatchRunOut(BaseModel):
    run_id: uuid.UUID
    created_at: datetime
    semantic_backend: str
    model_version: str
    weights: dict[str, float]
    total_considered: int
    results: list[MatchSummaryOut]
    disclaimer: str = SCORE_DISCLAIMER


class MatchPage(BaseModel):
    run_id: uuid.UUID | None
    created_at: datetime | None
    semantic_backend: str | None
    model_version: str | None
    weights: dict[str, float] | None
    items: list[MatchSummaryOut]
    total: int
    page: int
    page_size: int
    disclaimer: str = SCORE_DISCLAIMER


class MatchDetailOut(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    rank: int
    score: float
    evidence_coverage: float
    components: dict[str, float | None]
    weights: dict[str, float]
    component_labels: dict[str, str]
    semantic_backend: str
    model_version: str
    created_at: datetime
    evidence: list[MatchEvidenceOut]
    job: JobDetailOut
    feedback: str | None = None
    disclaimer: str = SCORE_DISCLAIMER


class FeedbackIn(BaseModel):
    rating: Literal["relevant", "not_relevant"]
    comment: str | None = Field(default=None, max_length=1000)
