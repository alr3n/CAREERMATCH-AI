"""Query helpers for job listings."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.base import utcnow
from app.ml.taxonomy import canonicalize
from app.models import JobListing, JobSkill, JobSource, SavedJob
from app.schemas.job import JobFilters


def visible_listings() -> Select:
    """Active, non-duplicate listings from enabled sources.

    Rows flagged ``is_demo`` (left behind by the removed demo provider) are
    always excluded, so fictional data can never reach the API.
    """
    return (
        select(JobListing)
        .join(JobSource, JobSource.id == JobListing.source_id)
        .where(
            JobListing.status == "active",
            JobListing.duplicate_of_id.is_(None),
            JobListing.is_demo.is_(False),
            JobSource.enabled.is_(True),
            JobSource.is_demo.is_(False),
        )
    )


def apply_filters(stmt: Select, filters: JobFilters, user_id: uuid.UUID | None) -> Select:
    if filters.q:
        terms = [t for t in filters.q.split() if t][:8]
        for term in terms:
            like = f"%{term.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(JobListing.title).like(like),
                    func.lower(JobListing.company).like(like),
                    func.lower(JobListing.description).like(like),
                )
            )
    if filters.employment_types:
        stmt = stmt.where(JobListing.employment_type.in_(filters.employment_types))
    if filters.work_arrangements:
        stmt = stmt.where(JobListing.work_arrangement.in_(filters.work_arrangements))
    if filters.experience_levels:
        stmt = stmt.where(JobListing.experience_level.in_(filters.experience_levels))
    if filters.categories:
        stmt = stmt.where(JobListing.category.in_(filters.categories))
    if filters.company:
        stmt = stmt.where(func.lower(JobListing.company).like(f"%{filters.company.lower()}%"))
    if filters.platforms:
        wanted = [p.lower() for p in filters.platforms]
        stmt = stmt.where(
            or_(
                func.lower(func.coalesce(JobListing.source_platform, "")).in_(wanted),
                func.lower(JobListing.provider).in_(wanted),
            )
        )
    if filters.location:
        stmt = stmt.where(func.lower(func.coalesce(JobListing.location, "")).like(f"%{filters.location.lower()}%"))
    for skill in filters.skills:
        name = canonicalize(skill)
        stmt = stmt.where(
            JobListing.id.in_(select(JobSkill.job_id).where(func.lower(JobSkill.skill) == name.lower()))
        )
    if filters.salary_min is not None:
        stmt = stmt.where(
            JobListing.salary_max.is_not(None),
            JobListing.salary_max >= filters.salary_min,
        )
        if filters.salary_currency:
            stmt = stmt.where(JobListing.salary_currency == filters.salary_currency)
    if filters.has_salary:
        stmt = stmt.where(
            or_(JobListing.salary_min.is_not(None), JobListing.salary_max.is_not(None), JobListing.salary_text.is_not(None))
        )
    if filters.checked_within_days:
        stmt = stmt.where(JobListing.last_checked_at >= utcnow() - timedelta(days=filters.checked_within_days))
    if filters.saved_only and user_id is not None:
        stmt = stmt.where(JobListing.id.in_(select(SavedJob.job_id).where(SavedJob.user_id == user_id)))
    return stmt


def order(stmt: Select, sort: str) -> Select:
    if sort == "posted":
        return stmt.order_by(JobListing.posted_at.desc().nulls_last(), JobListing.title)
    if sort == "title":
        return stmt.order_by(JobListing.title, JobListing.company)
    return stmt.order_by(JobListing.last_checked_at.desc(), JobListing.title)


def paginate(db: Session, stmt: Select, page: int, page_size: int) -> tuple[list[JobListing], int]:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.scalars(
        stmt.options(selectinload(JobListing.skills), selectinload(JobListing.source))
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total


def saved_ids(db: Session, user_id: uuid.UUID, job_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if not job_ids:
        return set()
    return set(db.scalars(select(SavedJob.job_id).where(and_(SavedJob.user_id == user_id, SavedJob.job_id.in_(job_ids)))))
