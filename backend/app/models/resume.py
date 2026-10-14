"""Resumes and the structured profile extracted from them."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, Timestamps, UUIDPk

if TYPE_CHECKING:
    from app.models.user import User


class Resume(UUIDPk, Timestamps, Base):
    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Sanitised display name only; the stored file (if retained) uses a random name.
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)  # pdf | docx
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(512))
    page_count: Mapped[int | None] = mapped_column(Integer)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # processed | reviewed
    status: Mapped[str] = mapped_column(String(32), default="processed", nullable=False)
    extraction_method: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_warnings: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    # Only stored when the user consented; contact details are redacted first.
    raw_text: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    total_experience_months: Mapped[int | None] = mapped_column(Integer)
    certifications: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    achievements: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    # Preferences detected in the resume text (suggestions the user confirms).
    detected_preferences: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="resumes")
    skills: Mapped[list["ExtractedSkill"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", passive_deletes=True, order_by="ExtractedSkill.skill"
    )
    education: Mapped[list["EducationRecord"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", passive_deletes=True, order_by="EducationRecord.position"
    )
    experience: Mapped[list["ExperienceRecord"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", passive_deletes=True, order_by="ExperienceRecord.position"
    )
    projects: Mapped[list["Project"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan", passive_deletes=True, order_by="Project.position"
    )


class ExtractedSkill(UUIDPk, Base):
    __tablename__ = "extracted_skills"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    skill: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64))
    # extracted | user
    source: Mapped[str] = mapped_column(String(16), default="extracted", nullable=False)
    evidence: Mapped[str | None] = mapped_column(String(300))
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    resume: Mapped[Resume] = relationship(back_populates="skills")


class EducationRecord(UUIDPk, Base):
    __tablename__ = "education_records"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    institution: Mapped[str | None] = mapped_column(String(200))
    degree: Mapped[str | None] = mapped_column(String(200))
    field_of_study: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[str | None] = mapped_column(String(32))
    end_date: Mapped[str | None] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(16), default="extracted", nullable=False)

    resume: Mapped[Resume] = relationship(back_populates="education")


class ExperienceRecord(UUIDPk, Base):
    __tablename__ = "experience_records"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200))
    organization: Mapped[str | None] = mapped_column(String(200))
    start_date: Mapped[str | None] = mapped_column(String(32))
    end_date: Mapped[str | None] = mapped_column(String(32))
    duration_months: Mapped[int | None] = mapped_column(Integer)
    is_internship: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(16), default="extracted", nullable=False)

    resume: Mapped[Resume] = relationship(back_populates="experience")


class Project(UUIDPk, Base):
    __tablename__ = "projects"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    source: Mapped[str] = mapped_column(String(16), default="extracted", nullable=False)

    resume: Mapped[Resume] = relationship(back_populates="projects")
