"""Aggregate router for all versioned API endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, jobs, matches, profile, resumes

api_router = APIRouter()
for module in (auth, profile, resumes, jobs, matches):
    api_router.include_router(module.router)
