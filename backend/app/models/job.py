"""Job sources, normalised job listings and the skills they mention."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, Timestamps, UUIDPk


class JobSource(UUIDPk, Timestamps, Base):
    """A configured provider endpoint, e.g. one Greenhouse board or Lever site."""

    __tablename__ = "job_sources"
    __table_args__ = (UniqueConstraint("provider", "identifier", name="uq_job_sources_provider_identifier"),)

    provider: Mapped[str] = mapped_column(String(32), nullable=False)  # greenhouse | lever | demo
    identifier: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # never | ok | error | rate_limited
    last_status: Mapped[str] = mapped_column(String(32), default="never", nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(500))
    last_fetch_count: Mapped[int | None] = mapped_column(Integer)

    listings: Mapped[list["JobListing"]] = relationship(
        back_populates="source", cascade="all, delete-orphan", passive_deletes=True
    )


class JobListing(UUIDPk, Timestamps, Base):
    __tablename__ = "job_listings"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_job_listings_source_external"),
        Index("ix_job_listings_status_demo", "status", "is_demo"),
        Index("ix_job_listings_filters", "work_arrangement", "employment_type", "experience_level"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("job_sources.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    required_qualifications: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    preferred_qualifications: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    location: Mapped[str | None] = mapped_column(String(300))
    country: Mapped[str | None] = mapped_column(String(2))
    # remote | hybrid | onsite | unknown
    work_arrangement: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)
    # full_time | part_time | contract | internship | temporary | unknown
    employment_type: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)
    # internship | entry | mid | senior | unknown
    experience_level: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)
    min_years_experience: Mapped[int | None] = mapped_column(Integer)
    category: Mapped[str | None] = mapped_column(String(64), index=True)
    department: Mapped[str | None] = mapped_column(String(200))
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    salary_interval: Mapped[str | None] = mapped_column(String(32))
    salary_text: Mapped[str | None] = mapped_column(String(300))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    apply_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    # active | expired
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    content_fingerprint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("job_listings.id", ondelete="SET NULL")
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    source: Mapped[JobSource] = relationship(back_populates="listings")
    skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", passive_deletes=True
    )


class JobSkill(UUIDPk, Base):
    __tablename__ = "job_skills"
    __table_args__ = (Index("ix_job_skills_skill", "skill"),)

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("job_listings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    skill: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64))
    # required | preferred | mentioned
    requirement: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence: Mapped[str | None] = mapped_column(String(400))

    job: Mapped[JobListing] = relationship(back_populates="skills")
