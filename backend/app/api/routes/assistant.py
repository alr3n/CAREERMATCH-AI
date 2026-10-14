from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, rate_limit_user
from app.db.session import get_db
from app.models import User
from app.schemas.assistant import AssistantRequest, AssistantResponse, AssistantStatus
from app.services import assistant_service

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.get("/status", response_model=AssistantStatus, summary="Whether an LLM is available and what it would receive")
def status(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AssistantStatus:
    return assistant_service.status(db, user)


@router.post(
    "",
    response_model=AssistantResponse,
    dependencies=[Depends(rate_limit_user("assistant", "rate_limit_assistant"))],
    summary="Grounded career help for a selected job (drafts require your review)",
)
def run(body: AssistantRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AssistantResponse:
    return assistant_service.run(db, user, body)
