from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.activity import RecommendationsOut, SkillGapReport
from app.services import skill_gap_service

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("/gaps", response_model=SkillGapReport, summary="Skills requested by your top matches but not found in your resume")
def gaps(
    run_id: uuid.UUID | None = None,
    top_k: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SkillGapReport:
    return skill_gap_service.gap_report(db, user, run_id, top_k)


@router.get("/recommendations", response_model=RecommendationsOut, summary="Learning and portfolio suggestions for skill gaps")
def recommendations(
    run_id: uuid.UUID | None = None,
    limit: int = Query(default=8, ge=1, le=20),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecommendationsOut:
    return skill_gap_service.recommendations(db, user, run_id, limit)
