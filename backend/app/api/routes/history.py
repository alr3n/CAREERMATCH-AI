from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.activity import HistoryOut
from app.schemas.common import Page
from app.services import activity_service

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=Page[HistoryOut], summary="Your previous searches and matching runs (no resume data)")
def history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[HistoryOut]:
    items, total = activity_service.list_history(db, user, page, page_size)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, summary="Clear your search history")
def clear(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    activity_service.clear_history(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
