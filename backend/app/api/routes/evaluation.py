from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.activity import EvaluationSummary
from app.services import activity_service

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get("/summary", response_model=EvaluationSummary, summary="Latest model evaluation results, or 'not yet evaluated'")
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> EvaluationSummary:
    return activity_service.evaluation_summary(db)
