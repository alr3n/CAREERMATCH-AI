"""Shared API dependencies: authentication and rate limiting."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.rate_limit import rate_limiter
from app.db.session import get_db
from app.models import User
from app.security.tokens import InvalidToken, decode_access_token

_bearer = HTTPBearer(auto_error=False)


def _unauthorized(message: str = "Authentication required") -> AppError:
    return AppError(
        status.HTTP_401_UNAUTHORIZED, "unauthorized", message, headers={"WWW-Authenticate": "Bearer"}
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidToken:
        raise _unauthorized("Invalid or expired token") from None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("Invalid or expired token")
    return user


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def rate_limit_ip(bucket: str, setting_name: str) -> Callable:
    """Rate limit anonymous endpoints (login, register) by client IP."""

    def dependency(request: Request) -> None:
        rate_limiter.hit(bucket, client_ip(request), getattr(get_settings(), setting_name))

    return dependency


def rate_limit_user(bucket: str, setting_name: str) -> Callable:
    """Rate limit authenticated endpoints by user id (not by token)."""

    def dependency(user: User = Depends(get_current_user)) -> None:
        rate_limiter.hit(bucket, str(user.id), getattr(get_settings(), setting_name))

    return dependency
