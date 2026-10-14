from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.job import JobSummaryOut


class SaveJobIn(BaseModel):
    job_id: uuid.UUID
    note: str | None = Field(default=None, max_length=1000)


class SavedJobOut(BaseModel):
    id: uuid.UUID
    note: str | None
    created_at: datetime
    job: JobSummaryOut


class HistoryOut(BaseModel):
    id: uuid.UUID
    kind: str
    query: dict
    result_count: int
    run_id: uuid.UUID | None
    created_at: datetime


class GapExample(BaseModel):
    job_id: uuid.UUID
    title: str
    company: str
    requirement: str
    evidence: str | None
    is_demo: bool


class SkillGap(BaseModel):
    skill: str
    category: str | None
    required_count: int
    preferred_count: int
    priority: int
    in_development_list: bool
    examples: list[GapExample]


class IdentifiedSkill(BaseModel):
    skill: str
    category: str | None
    jobs_requesting: int


class SkillFrequency(BaseModel):
    skill: str
    jobs: int
    share: float
    user_has: bool


class SkillGapReport(BaseModel):
    basis: str
    jobs_analyzed: int
    target_titles: list[str]
    identified_skills: list[IdentifiedSkill]
    gaps: list[SkillGap]
    skill_frequency: list[SkillFrequency]
    total_listings: int
    note: str


class ResourceOut(BaseModel):
    title: str
    url: str
    provider: str
    cost: str


class SkillRecommendation(BaseModel):
    skill: str
    why: str
    project_idea: str
    how_to_demonstrate: str
    resources: list[ResourceOut]
    resources_note: str | None


class RecommendationsOut(BaseModel):
    basis: str
    recommendations: list[SkillRecommendation]
    note: str


class EvaluationSummary(BaseModel):
    status: str  # evaluated | not_evaluated
    source: str | None = None
    report: dict | None = None
    message: str
