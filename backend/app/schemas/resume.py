from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel


class SkillOut(ORMModel):
    skill: str
    category: str | None
    source: str
    evidence: str | None
    confidence: float


class EducationOut(ORMModel):
    institution: str | None
    degree: str | None
    field_of_study: str | None
    start_date: str | None
    end_date: str | None
    source: str


class ExperienceOut(ORMModel):
    title: str | None
    organization: str | None
    start_date: str | None
    end_date: str | None
    duration_months: int | None
    is_internship: bool
    description: str | None
    source: str


class ProjectOut(ORMModel):
    name: str
    description: str | None
    skills: list[str]
    source: str


class ResumeSummaryOut(ORMModel):
    id: uuid.UUID
    original_filename: str
    content_type: str
    status: str
    is_active: bool
    created_at: datetime


class ResumeOut(ORMModel):
    id: uuid.UUID
    original_filename: str
    content_type: str
    file_size: int
    page_count: int | None
    char_count: int
    status: str
    extraction_method: str
    extraction_warnings: list[str]
    summary: str | None
    total_experience_months: int | None
    certifications: list[str]
    achievements: list[str]
    detected_preferences: dict
    is_active: bool
    raw_text_stored: bool = False
    file_retained: bool = False
    skills: list[SkillOut]
    education: list[EducationOut]
    experience: list[ExperienceOut]
    projects: list[ProjectOut]
    created_at: datetime
    updated_at: datetime


# ----- corrections submitted by the user -----


class SkillIn(BaseModel):
    skill: str = Field(min_length=1, max_length=120)


class EducationIn(BaseModel):
    institution: str | None = Field(default=None, max_length=200)
    degree: str | None = Field(default=None, max_length=200)
    field_of_study: str | None = Field(default=None, max_length=200)
    start_date: str | None = Field(default=None, max_length=32)
    end_date: str | None = Field(default=None, max_length=32)


class ExperienceIn(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    organization: str | None = Field(default=None, max_length=200)
    start_date: str | None = Field(default=None, max_length=32)
    end_date: str | None = Field(default=None, max_length=32)
    duration_months: int | None = Field(default=None, ge=0, le=600)
    is_internship: bool = False
    description: str | None = Field(default=None, max_length=3000)


class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=3000)
    skills: list[str] = Field(default_factory=list, max_length=40)


class ResumeProfileUpdate(BaseModel):
    """Fields that are provided replace the stored values; omitted fields are unchanged."""

    skills: list[SkillIn] | None = Field(default=None, max_length=150)
    education: list[EducationIn] | None = Field(default=None, max_length=20)
    experience: list[ExperienceIn] | None = Field(default=None, max_length=40)
    projects: list[ProjectIn] | None = Field(default=None, max_length=40)
    certifications: list[str] | None = Field(default=None, max_length=40)
    achievements: list[str] | None = Field(default=None, max_length=40)
    summary: str | None = Field(default=None, max_length=1000)
    total_experience_months: int | None = Field(default=None, ge=0, le=600)

    @field_validator("certifications", "achievements")
    @classmethod
    def _trim(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        return [" ".join(x.split())[:200] for x in v if x and x.strip()]
