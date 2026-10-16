"""Saved jobs, search history and the evaluation summary."""

from __future__ import annotations

import json
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.errors import not_found
from app.models import EvaluationRun, JobListing, SavedJob, SearchHistory, User
from app.schemas.activity import EvaluationSummary, HistoryOut, SavedJobOut
from app.services import job_service


def list_saved(db: Session, user: User, page: int, page_size: int) -> tuple[list[SavedJobOut], int]:
    base = select(SavedJob).where(SavedJob.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.options(
            selectinload(SavedJob.job).selectinload(JobListing.skills),
            selectinload(SavedJob.job).selectinload(JobListing.source),
        )
        .order_by(SavedJob.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    saved = {r.job_id for r in rows}
    return [
        SavedJobOut(id=r.id, note=r.note, created_at=r.created_at, job=job_service.to_summary(r.job, saved))
        for r in rows
    ], total


def save_job(db: Session, user: User, job_id: uuid.UUID, note: str | None) -> SavedJobOut:
    job = db.get(JobListing, job_id)
    if job is None or job.is_demo:
        raise not_found("Job")
    saved = db.scalar(select(SavedJob).where(SavedJob.user_id == user.id, SavedJob.job_id == job_id))
    if saved is None:
        saved = SavedJob(user_id=user.id, job_id=job_id, note=note)
        db.add(saved)
        try:
            db.commit()
        except IntegrityError:  # concurrent double-save
            db.rollback()
            saved = db.scalar(select(SavedJob).where(SavedJob.user_id == user.id, SavedJob.job_id == job_id))
    elif note is not None:
        saved.note = note
        db.commit()
    db.refresh(saved)
    return SavedJobOut(id=saved.id, note=saved.note, created_at=saved.created_at,
                       job=job_service.to_summary(saved.job, {job_id}))


def unsave_job(db: Session, user: User, job_id: uuid.UUID) -> None:
    result = db.execute(delete(SavedJob).where(SavedJob.user_id == user.id, SavedJob.job_id == job_id))
    db.commit()
    if result.rowcount == 0:
        raise not_found("Saved job")


def list_history(db: Session, user: User, page: int, page_size: int) -> tuple[list[HistoryOut], int]:
    base = select(SearchHistory).where(SearchHistory.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(base.order_by(SearchHistory.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    return [HistoryOut.model_validate(r, from_attributes=True) for r in rows], total


def clear_history(db: Session, user: User) -> None:
    db.execute(delete(SearchHistory).where(SearchHistory.user_id == user.id))
    db.commit()


def evaluation_summary(db: Session) -> EvaluationSummary:
    runs = db.scalars(select(EvaluationRun).order_by(EvaluationRun.evaluated_at.desc()).limit(20)).all()
    if runs:
        return EvaluationSummary(
            status="evaluated",
            source="database",
            report={
                "runs": [
                    {
                        "dataset_name": r.dataset_name,
                        "dataset_version": r.dataset_version,
                        "split": r.split,
                        "metrics": r.metrics,
                        "config": r.config,
                        "notes": r.notes,
                        "evaluated_at": r.evaluated_at.isoformat(),
                    }
                    for r in runs
                ]
            },
            message="Results recorded in the evaluation_runs table.",
        )
    path = get_settings().evaluation_report_path
    if path.exists():
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            report = None
        if report:
            return EvaluationSummary(
                status="evaluated", source=path.name, report=report,
                message="Results produced by scripts/evaluate_matching.py.",
            )
    return EvaluationSummary(status="not_evaluated", message="Not yet evaluated.")
