from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, rate_limit_user
from app.db.session import get_db
from app.models import User
from app.schemas.match import FeedbackIn, MatchDetailOut, MatchPage, MatchRequest, MatchRunOut
from app.services import match_service

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post(
    "",
    response_model=MatchRunOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_user("match", "rate_limit_match"))],
    summary="Rank current listings against your active resume and preferences",
)
def create_matches(
    body: MatchRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MatchRunOut:
    return match_service.run_matching(db, user, body)


@router.get("", response_model=MatchPage, summary="List results of a matching run (latest by default)")
def list_matches(
    run_id: uuid.UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MatchPage:
    return match_service.list_matches(db, user, run_id, page, page_size)


@router.get("/{match_id}", response_model=MatchDetailOut, summary="Full explanation for one recommendation")
def get_match(
    match_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MatchDetailOut:
    return match_service.get_match(db, user, match_id)


@router.post("/{match_id}/feedback", status_code=status.HTTP_204_NO_CONTENT,
             summary="Tell us whether a recommendation was relevant")
def feedback(
    match_id: uuid.UUID, body: FeedbackIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    match_service.record_feedback(db, user, match_id, body.rating, body.comment)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
