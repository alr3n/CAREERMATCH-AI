from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, rate_limit_user
from app.db.base import utcnow
from app.db.session import get_db
from app.models import User
from app.schemas.common import Page
from app.schemas.job import (
    EmploymentType,
    ExperienceLevel,
    FacetsOut,
    JobDetailOut,
    JobFilters,
    JobSummaryOut,
    RefreshResponse,
    SourcesResponse,
    WorkArrangement,
)
from app.services import job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/sources", response_model=SourcesResponse, summary="Configured job sources and their status")
def sources(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SourcesResponse:
    return job_service.list_sources(db)


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    dependencies=[Depends(rate_limit_user("refresh", "rate_limit_refresh"))],
    summary="Fetch the latest listings from every configured provider",
)
def refresh(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> RefreshResponse:
    results = job_service.refresh_jobs(db)
    return RefreshResponse(results=results, refreshed_at=utcnow())


@router.get("/facets", response_model=FacetsOut, summary="Counts used to build filters")
def facets(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> FacetsOut:
    job_service.ensure_jobs_loaded(db)
    return job_service.facets(db)


@router.get("", response_model=Page[JobSummaryOut], summary="List stored listings with filters")
def list_jobs(
    q: str | None = Query(default=None, max_length=200),
    employment_types: list[EmploymentType] = Query(default=[]),
    work_arrangements: list[WorkArrangement] = Query(default=[]),
    experience_levels: list[ExperienceLevel] = Query(default=[]),
    categories: list[str] = Query(default=[]),
    location: str | None = Query(default=None, max_length=120),
    skills: list[str] = Query(default=[]),
    checked_within_days: int | None = Query(default=None, ge=1, le=365),
    include_demo: bool = True,
    saved_only: bool = False,
    sort: str = Query(default="recently_checked", pattern="^(recently_checked|posted|title)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[JobSummaryOut]:
    job_service.ensure_jobs_loaded(db)
    filters = JobFilters(
        q=q, employment_types=employment_types, work_arrangements=work_arrangements,
        experience_levels=experience_levels, categories=categories, location=location, skills=skills,
        checked_within_days=checked_within_days, include_demo=include_demo, saved_only=saved_only,
        sort=sort, page=page, page_size=page_size,
    )
    items, total = job_service.search(db, user, filters)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("/search", response_model=Page[JobSummaryOut], summary="Search listings and record the search in history")
def search_jobs(
    filters: JobFilters, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Page[JobSummaryOut]:
    job_service.ensure_jobs_loaded(db)
    items, total = job_service.search(db, user, filters, record_history=True)
    return Page(items=items, total=total, page=filters.page, page_size=filters.page_size)


@router.get("/{job_id}", response_model=JobDetailOut, summary="Full listing details with source attribution")
def get_job(job_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> JobDetailOut:
    return job_service.get_job(db, user, job_id)
