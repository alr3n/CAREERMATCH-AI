"""User accounts and preference profiles."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.base import utcnow
from app.models import Resume, User, UserProfile
from app.schemas.profile import CompletenessItem, ProfileUpdate
from app.security.files import delete_user_files
from app.security.passwords import DUMMY_HASH, hash_password, verify_password
from app.services import audit


def register_user(db: Session, email: str, password: str) -> User:
    email = email.strip().lower()
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise AppError(409, "email_taken", "An account with this email already exists")
    user = User(email=email, password_hash=hash_password(password))
    user.profile = UserProfile()
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "email_taken", "An account with this email already exists") from None
    audit.record(db, "user_registered", user.id)
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))
    if user is None:
        verify_password(password, DUMMY_HASH)  # equalise timing
        raise AppError(401, "invalid_credentials", "Incorrect email or password")
    if not verify_password(password, user.password_hash) or not user.is_active:
        audit.record(db, "login_failed", user.id)
        db.commit()
        raise AppError(401, "invalid_credentials", "Incorrect email or password")
    audit.record(db, "login_succeeded", user.id)
    db.commit()
    return user


def get_profile(db: Session, user: User) -> UserProfile:
    if user.profile is None:
        user.profile = UserProfile()
        db.commit()
    return user.profile


def update_profile(db: Session, user: User, update: ProfileUpdate) -> UserProfile:
    profile = get_profile(db, user)
    data = update.model_dump(exclude_unset=True)
    consent_changed = False
    for key, value in data.items():
        if key.startswith("consent_") and getattr(profile, key) != value:
            consent_changed = True
        if value is None and key in {
            "preferred_titles", "preferred_industries", "preferred_locations",
            "work_arrangements", "employment_types", "skills_to_develop",
        }:
            value = []
        setattr(profile, key, value)
    if consent_changed:
        profile.consent_updated_at = utcnow()
        audit.record(
            db,
            "consent_changed",
            user.id,
            llm=profile.consent_llm_processing,
            store_resume_text=profile.consent_store_resume_text,
        )
        if not profile.consent_store_resume_text:
            # Withdrawing consent removes previously stored resume text.
            for resume in user.resumes:
                resume.raw_text = None
    db.commit()
    db.refresh(profile)
    return profile


def active_resume(db: Session, user: User) -> Resume | None:
    return db.scalar(
        select(Resume).where(Resume.user_id == user.id, Resume.is_active.is_(True)).order_by(Resume.created_at.desc())
    )


def completeness(db: Session, user: User) -> tuple[int, list[CompletenessItem]]:
    profile = get_profile(db, user)
    resume = active_resume(db, user)
    items = [
        ("resume", "Upload a resume", resume is not None, 25),
        ("skills", "At least 3 skills on your profile", bool(resume and len(resume.skills) >= 3), 15),
        ("education", "Education details", bool(resume and resume.education), 10),
        ("career_stage", "Career stage", profile.career_stage is not None, 10),
        ("titles", "Preferred job titles", bool(profile.preferred_titles), 10),
        ("arrangement", "Work arrangement preference", bool(profile.work_arrangements), 10),
        ("employment", "Employment type preference", bool(profile.employment_types), 10),
        ("location", "Preferred locations (or remote)", bool(profile.preferred_locations)
         or "remote" in (profile.work_arrangements or []), 10),
    ]
    score = sum(weight for _, _, done, weight in items if done)
    return score, [CompletenessItem(key=k, label=label, done=d, weight=w) for k, label, d, w in items]


def delete_account(db: Session, user: User) -> None:
    """Delete the user, every dependent record (via cascades) and stored files."""
    settings = get_settings()
    user_id = user.id
    delete_user_files(settings.storage_dir, user_id)
    db.delete(user)
    db.flush()
    audit.record(db, "account_deleted", None)
    db.commit()
