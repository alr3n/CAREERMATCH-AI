"""Aggregate router for all versioned API endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, profile

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(profile.router)
