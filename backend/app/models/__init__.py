"""Import all models so that metadata is complete for Alembic and tests."""

from app.models.activity import (
    EvaluationRun,
    MatchEvidence,
    MatchResult,
    ModelVersion,
    SavedJob,
    SearchHistory,
    UserFeedback,
)
from app.models.job import JobListing, JobSkill, JobSource
from app.models.resume import EducationRecord, ExperienceRecord, ExtractedSkill, Project, Resume
from app.models.user import AuditEvent, User, UserProfile

__all__ = [
    "AuditEvent",
    "EducationRecord",
    "EvaluationRun",
    "ExperienceRecord",
    "ExtractedSkill",
    "JobListing",
    "JobSkill",
    "JobSource",
    "MatchEvidence",
    "MatchResult",
    "ModelVersion",
    "Project",
    "Resume",
    "SavedJob",
    "SearchHistory",
    "User",
    "UserFeedback",
    "UserProfile",
]
