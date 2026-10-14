"""Aggregate router for all versioned API endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, evaluation, history, jobs, matches, profile, resumes, saved_jobs, skills

api_router = APIRouter()
for module in (auth, profile, resumes, jobs, matches, saved_jobs, skills, history, evaluation):
    api_router.include_router(module.router)
