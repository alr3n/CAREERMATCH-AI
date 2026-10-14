from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.auth import UserOut
from app.schemas.common import ORMModel

CareerStage = Literal["student", "fresh_graduate", "entry_level", "experienced", "career_transition"]
Goal = Literal["internship", "entry_level", "experienced", "career_transition"]
WorkArrangement = Literal["remote", "hybrid", "onsite"]
EmploymentType = Literal["full_time", "part_time", "contract", "internship", "temporary"]

_ShortText = Field(max_length=120)


def _clean_list(values: list[str] | None, limit: int = 20) -> list[str] | None:
    if values is None:
        return None
    seen: list[str] = []
    for v in values:
        v = " ".join(str(v).split())[:120]
        if v and v.lower() not in {s.lower() for s in seen}:
            seen.append(v)
    return seen[:limit]


class ProfileOut(ORMModel):
    display_name: str | None
    career_stage: CareerStage | None
    goal: Goal | None
    preferred_titles: list[str]
    preferred_industries: list[str]
    preferred_locations: list[str]
    work_arrangements: list[WorkArrangement]
    employment_types: list[EmploymentType]
    min_salary: Decimal | None
    salary_currency: str | None
    skills_to_develop: list[str]
    consent_llm_processing: bool
    consent_store_resume_text: bool
    consent_updated_at: datetime | None
    onboarding_completed: bool
    updated_at: datetime


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    career_stage: CareerStage | None = None
    goal: Goal | None = None
    preferred_titles: list[str] | None = None
    preferred_industries: list[str] | None = None
    preferred_locations: list[str] | None = None
    work_arrangements: list[WorkArrangement] | None = None
    employment_types: list[EmploymentType] | None = None
    min_salary: Decimal | None = Field(default=None, ge=0, le=100_000_000)
    salary_currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    skills_to_develop: list[str] | None = None
    consent_llm_processing: bool | None = None
    consent_store_resume_text: bool | None = None
    onboarding_completed: bool | None = None

    @field_validator("preferred_titles", "preferred_industries", "preferred_locations", "skills_to_develop")
    @classmethod
    def _clean(cls, v: list[str] | None) -> list[str] | None:
        return _clean_list(v)

    @field_validator("work_arrangements", "employment_types")
    @classmethod
    def _dedupe(cls, v: list[str] | None) -> list[str] | None:
        return list(dict.fromkeys(v)) if v is not None else None


class CompletenessItem(BaseModel):
    key: str
    label: str
    done: bool
    weight: int


class ProfileResponse(BaseModel):
    user: UserOut
    profile: ProfileOut
    completeness: int
    completeness_items: list[CompletenessItem]
    has_resume: bool
    llm_available: bool
