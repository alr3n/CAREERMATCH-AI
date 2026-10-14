from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import User
from app.schemas.auth import UserOut
from app.schemas.profile import ProfileOut, ProfileResponse, ProfileUpdate
from app.services import profile_service

router = APIRouter(prefix="/profile", tags=["profile"])


def _response(db: Session, user: User) -> ProfileResponse:
    profile = profile_service.get_profile(db, user)
    score, items = profile_service.completeness(db, user)
    return ProfileResponse(
        user=UserOut.model_validate(user),
        profile=ProfileOut.model_validate(profile),
        completeness=score,
        completeness_items=items,
        has_resume=profile_service.active_resume(db, user) is not None,
        llm_available=get_settings().llm_configured,
    )


@router.get("", response_model=ProfileResponse, summary="Get your profile, preferences and consent settings")
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ProfileResponse:
    return _response(db, user)


@router.patch("", response_model=ProfileResponse, summary="Update preferences or consent")
def update_profile(
    body: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ProfileResponse:
    profile_service.update_profile(db, user, body)
    return _response(db, user)


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Permanently delete your account, resumes, extracted data, matches and saved jobs",
)
def delete_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    profile_service.delete_account(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
