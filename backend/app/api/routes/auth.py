from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import rate_limit_ip
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.security.tokens import create_access_token
from app.services import profile_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _token(user) -> TokenResponse:
    token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires_in, user=UserOut.model_validate(user))


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_ip("auth", "rate_limit_auth"))],
    summary="Create an account",
)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = profile_service.register_user(db, body.email, body.password)
    return _token(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_ip("auth", "rate_limit_auth"))],
    summary="Exchange credentials for an access token",
)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = profile_service.authenticate(db, body.email, body.password)
    return _token(user)
