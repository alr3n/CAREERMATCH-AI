from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.activity import SavedJobOut, SaveJobIn
from app.schemas.common import Page
from app.services import activity_service

router = APIRouter(prefix="/saved-jobs", tags=["saved jobs"])


@router.get("", response_model=Page[SavedJobOut], summary="Your saved opportunities")
def list_saved(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[SavedJobOut]:
    items, total = activity_service.list_saved(db, user, page, page_size)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=SavedJobOut, status_code=status.HTTP_201_CREATED, summary="Save a job")
def save(body: SaveJobIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SavedJobOut:
    return activity_service.save_job(db, user, body.job_id, body.note)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove a saved job")
def unsave(job_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    activity_service.unsave_job(db, user, job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
