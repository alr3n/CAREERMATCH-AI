"""Users, profiles (preferences + consent) and audit events."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, Timestamps, UUIDPk, utcnow

if TYPE_CHECKING:
    from app.models.resume import Resume


class User(UUIDPk, Timestamps, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profile: Mapped[UserProfile] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False, passive_deletes=True
    )
    resumes: Mapped[list[Resume]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class UserProfile(UUIDPk, Timestamps, Base):
    """Job-search preferences and consent flags. Every field is optional."""

    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    display_name: Mapped[str | None] = mapped_column(String(120))
    # student | fresh_graduate | entry_level | experienced | career_transition
    career_stage: Mapped[str | None] = mapped_column(String(32))
    # internship | entry_level | experienced | career_transition
    goal: Mapped[str | None] = mapped_column(String(32))
    preferred_titles: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    preferred_industries: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    preferred_locations: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    # remote | hybrid | onsite
    work_arrangements: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    # full_time | part_time | contract | internship | temporary
    employment_types: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)
    min_salary: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    skills_to_develop: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)

    consent_llm_processing: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_store_resume_text: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    consent_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="profile")


class AuditEvent(UUIDPk, Base):
    """Security-relevant events (logins, deletions, consent changes).

    ``detail`` must never contain resume content or contact information.
    ``user_id`` is set to NULL when the user is deleted so that the fact that
    a deletion happened is retained without keeping personal data.
    """

    __tablename__ = "audit_events"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    detail: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
