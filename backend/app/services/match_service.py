"""Matching: build profiles, score listings, persist evidence-backed results."""

from __future__ import annotations

import time
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import AppError, not_found
from app.db.base import utcnow
from app.ml.embeddings import get_backend
from app.ml.explain import COMPONENT_LABELS, build_evidence
from app.ml.features import CandidateProfile, ExperienceEntry, JobRecord, JobSkillRef, ProjectEntry
from app.ml.scoring import MODEL_VERSION, WEIGHT_PRESETS, rank
from app.models import JobListing, MatchEvidence, MatchResult, Resume, SearchHistory, User, UserFeedback
from app.repositories import job_repository as repo
from app.schemas.job import JobFilters
from app.schemas.match import (
    MatchDetailOut,
    MatchEvidenceOut,
    MatchPage,
    MatchRequest,
    MatchRunOut,
    MatchSummaryOut,
)
from app.services import job_service
from app.services.profile_service import active_resume, get_profile


def candidate_from(resume: Resume, user: User) -> CandidateProfile:
    prefs = user.profile
    return CandidateProfile(
        skills={s.skill for s in resume.skills},
        skill_evidence={s.skill: s.evidence for s in resume.skills if s.evidence},
        experiences=[
            ExperienceEntry(e.title, e.organization, e.description, e.is_internship) for e in resume.experience
        ],
        projects=[ProjectEntry(p.name, p.description, list(p.skills or [])) for p in resume.projects],
        education_fields=[e.field_of_study or e.degree for e in resume.education if (e.field_of_study or e.degree)],
        certifications=list(resume.certifications or []),
        summary=resume.summary,
        total_experience_months=resume.total_experience_months,
        career_stage=prefs.career_stage if prefs else None,
        preferred_titles=list(prefs.preferred_titles or []) if prefs else [],
        preferred_categories=list(prefs.preferred_industries or []) if prefs else [],
        preferred_locations=list(prefs.preferred_locations or []) if prefs else [],
        work_arrangements=list(prefs.work_arrangements or []) if prefs else [],
        employment_types=list(prefs.employment_types or []) if prefs else [],
        min_salary=prefs.min_salary if prefs else None,
        salary_currency=prefs.salary_currency if prefs else None,
    )


def job_record(job: JobListing) -> JobRecord:
    def refs(level: str) -> list[JobSkillRef]:
        return [JobSkillRef(s.skill, s.evidence) for s in job.skills if s.requirement == level]

    return JobRecord(
        id=str(job.id),
        title=job.title,
        company=job.company,
        description=job.description,
        category=job.category,
        location=job.location,
        work_arrangement=job.work_arrangement,
        employment_type=job.employment_type,
        experience_level=job.experience_level,
        min_years_experience=job.min_years_experience,
        required_skills=refs("required"),
        preferred_skills=refs("preferred"),
        mentioned_skills=refs("mentioned"),
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
        salary_interval=job.salary_interval,
        department=job.department,
        freshness=job_service.freshness(job.last_checked_at),
    )


def _summary(match: MatchResult, saved: set[uuid.UUID]) -> MatchSummaryOut:
    by_kind: dict[str, list[MatchEvidence]] = {}
    for e in match.evidence:
        by_kind.setdefault(e.kind, []).append(e)
    reasons = by_kind.get("reason", [])
    return MatchSummaryOut(
        id=match.id,
        run_id=match.run_id,
        rank=match.rank,
        score=match.score,
        evidence_coverage=match.evidence_coverage,
        components=match.components,
        matched_skills=[e.label for e in by_kind.get("matched_skill", [])],
        related_skills=[e.label for e in by_kind.get("related_skill", [])],
        missing_required=[e.label for e in by_kind.get("missing_required", [])],
        missing_preferred=[e.label for e in by_kind.get("missing_preferred", [])],
        top_reason=reasons[0].detail if reasons else None,
        job=job_service.to_summary(match.job, saved),
    )


def run_matching(db: Session, user: User, request: MatchRequest) -> MatchRunOut:
    settings = get_settings()
    get_profile(db, user)
    resume = active_resume(db, user)
    if resume is None:
        raise AppError(400, "resume_required", "Upload a resume before generating matches.")
    job_service.ensure_jobs_loaded(db)

    filters = JobFilters(**request.filters.model_dump())
    stmt = repo.apply_filters(repo.visible_listings(), filters, user.id)
    jobs = db.scalars(stmt.options(selectinload(JobListing.skills), selectinload(JobListing.source))).all()

    profile = candidate_from(resume, user)
    records = [job_record(j) for j in jobs]
    backend = get_backend(settings.embedding_backend, settings.embedding_model)
    started = time.perf_counter()
    semantic = list(backend.similarities(profile.document(), [r.document() for r in records])) if records else []
    weights = request.weights or WEIGHT_PRESETS[request.preset]
    ranked = rank(profile, records, semantic or None, weights)[: request.limit]
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)

    run_id = uuid.uuid4()
    jobs_by_id = {str(j.id): j for j in jobs}
    matches: list[MatchResult] = []
    for position, (record, breakdown) in enumerate(ranked, start=1):
        match = MatchResult(
            user_id=user.id,
            resume_id=resume.id,
            job_id=jobs_by_id[record.id].id,
            run_id=run_id,
            rank=position,
            score=breakdown.score,
            evidence_coverage=breakdown.evidence_coverage,
            components=breakdown.components,
            weights=breakdown.weights,
            semantic_backend=backend.name,
            model_version=MODEL_VERSION,
        )
        match.evidence = [
            MatchEvidence(position=i, kind=e.kind, label=e.label[:300], detail=e.detail, requirement=e.requirement)
            for i, e in enumerate(build_evidence(profile, record, breakdown, backend.name))
        ]
        match.job = jobs_by_id[record.id]
        matches.append(match)
    db.add_all(matches)
    db.add(
        SearchHistory(
            user_id=user.id,
            kind="match",
            query={
                "preset": request.preset if request.weights is None else "custom",
                "filters": request.filters.model_dump(mode="json", exclude_defaults=True),
                "limit": request.limit,
                "latency_ms": elapsed_ms,
            },
            result_count=len(matches),
            run_id=run_id,
        )
    )
    db.commit()
    saved = repo.saved_ids(db, user.id, [m.job_id for m in matches])
    normalised_weights = matches[0].weights if matches else {k: round(v, 4) for k, v in weights.items()}
    return MatchRunOut(
        run_id=run_id,
        created_at=matches[0].created_at if matches else utcnow(),
        semantic_backend=backend.name,
        model_version=MODEL_VERSION,
        weights=normalised_weights,
        total_considered=len(records),
        results=[_summary(m, saved) for m in matches],
    )


def latest_run_id(db: Session, user: User) -> uuid.UUID | None:
    return db.scalar(
        select(MatchResult.run_id)
        .where(MatchResult.user_id == user.id)
        .order_by(MatchResult.created_at.desc())
        .limit(1)
    )


def list_matches(db: Session, user: User, run_id: uuid.UUID | None, page: int, page_size: int) -> MatchPage:
    run_id = run_id or latest_run_id(db, user)
    if run_id is None:
        return MatchPage(run_id=None, created_at=None, semantic_backend=None, model_version=None, weights=None,
                         items=[], total=0, page=page, page_size=page_size)
    base = select(MatchResult).where(MatchResult.user_id == user.id, MatchResult.run_id == run_id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    if total == 0:
        raise not_found("Match run")
    rows = db.scalars(
        base.options(
            selectinload(MatchResult.evidence),
            selectinload(MatchResult.job).selectinload(JobListing.skills),
            selectinload(MatchResult.job).selectinload(JobListing.source),
        )
        .order_by(MatchResult.rank)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    saved = repo.saved_ids(db, user.id, [m.job_id for m in rows])
    first = rows[0] if rows else db.scalar(base.limit(1))
    return MatchPage(
        run_id=run_id,
        created_at=first.created_at,
        semantic_backend=first.semantic_backend,
        model_version=first.model_version,
        weights=first.weights,
        items=[_summary(m, saved) for m in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_match(db: Session, user: User, match_id: uuid.UUID) -> MatchDetailOut:
    match = db.scalar(
        select(MatchResult)
        .options(
            selectinload(MatchResult.evidence),
            selectinload(MatchResult.job).selectinload(JobListing.skills),
            selectinload(MatchResult.job).selectinload(JobListing.source),
        )
        .where(MatchResult.id == match_id)
    )
    if match is None or match.user_id != user.id:
        raise not_found("Match")
    saved = repo.saved_ids(db, user.id, [match.job_id])
    feedback = db.scalar(
        select(UserFeedback.rating).where(UserFeedback.user_id == user.id, UserFeedback.job_id == match.job_id)
    )
    return MatchDetailOut(
        id=match.id,
        run_id=match.run_id,
        rank=match.rank,
        score=match.score,
        evidence_coverage=match.evidence_coverage,
        components=match.components,
        weights=match.weights,
        component_labels=COMPONENT_LABELS,
        semantic_backend=match.semantic_backend,
        model_version=match.model_version,
        created_at=match.created_at,
        evidence=[MatchEvidenceOut(kind=e.kind, label=e.label, detail=e.detail, requirement=e.requirement)
                  for e in match.evidence],
        job=job_service.to_detail(match.job, saved),
        feedback=feedback,
    )


def record_feedback(db: Session, user: User, match_id: uuid.UUID, rating: str, comment: str | None) -> None:
    match = db.get(MatchResult, match_id)
    if match is None or match.user_id != user.id:
        raise not_found("Match")
    existing = db.scalar(
        select(UserFeedback).where(UserFeedback.user_id == user.id, UserFeedback.job_id == match.job_id)
    )
    if existing is None:
        existing = UserFeedback(user_id=user.id, job_id=match.job_id)
        db.add(existing)
    existing.match_id = match.id
    existing.rating = rating
    existing.comment = comment
    db.commit()
