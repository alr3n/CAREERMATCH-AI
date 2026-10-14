"""Matching results, saved jobs, search history, feedback and model metadata."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JSONType, UUIDPk, utcnow
from app.models.job import JobListing


class MatchResult(UUIDPk, Base):
    __tablename__ = "match_results"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("job_listings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Groups all results produced by one matching request.
    run_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)  # 0..100 compatibility score
    evidence_coverage: Mapped[float] = mapped_column(Float, nullable=False)  # 0..1
    components: Mapped[dict] = mapped_column(JSONType, nullable=False)
    weights: Mapped[dict] = mapped_column(JSONType, nullable=False)
    semantic_backend: Mapped[str] = mapped_column(String(120), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    job: Mapped[JobListing] = relationship()
    evidence: Mapped[list[MatchEvidence]] = relationship(
        back_populates="match", cascade="all, delete-orphan", passive_deletes=True, order_by="MatchEvidence.position"
    )


class MatchEvidence(UUIDPk, Base):
    __tablename__ = "match_evidence"

    match_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("match_results.id", ondelete="CASCADE"), index=True, nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # matched_skill | related_skill | missing_required | missing_preferred |
    # relevant_experience | experience_level | preference | reason | caveat
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(String(300), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    requirement: Mapped[str | None] = mapped_column(String(16))

    match: Mapped[MatchResult] = relationship(back_populates="evidence")


class SavedJob(UUIDPk, Base):
    __tablename__ = "saved_jobs"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_saved_jobs_user_job"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("job_listings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    note: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    job: Mapped[JobListing] = relationship()


class SearchHistory(UUIDPk, Base):
    """Search/match requests. Stores filters and keywords only — never resume data."""

    __tablename__ = "search_history"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # search | match
    query: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    run_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class UserFeedback(UUIDPk, Base):
    """Explicit relevance feedback; a future source of ranking labels."""

    __tablename__ = "user_feedback"
    __table_args__ = (UniqueConstraint("user_id", "job_id", name="uq_user_feedback_user_job"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("job_listings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    match_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("match_results.id", ondelete="SET NULL"))
    rating: Mapped[str] = mapped_column(String(16), nullable=False)  # relevant | not_relevant
    comment: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ModelVersion(UUIDPk, Base):
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_model_versions_name_version"),)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # baseline | scoring | ranker | extractor
    config: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EvaluationRun(UUIDPk, Base):
    __tablename__ = "evaluation_runs"

    model_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("model_versions.id", ondelete="SET NULL")
    )
    dataset_name: Mapped[str] = mapped_column(String(200), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(64), nullable=False)
    split: Mapped[str] = mapped_column(String(32), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONType, nullable=False)
    config: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
