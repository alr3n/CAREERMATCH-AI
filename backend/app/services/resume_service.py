"""Resume upload, extraction, correction and deletion."""

from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, not_found
from app.core.logging import redact
from app.ml.document_text import DocumentError, extract_document
from app.ml.profile_extractor import extract_profile
from app.ml.taxonomy import canonicalize, category_of
from app.models import EducationRecord, ExperienceRecord, ExtractedSkill, Project, Resume, User
from app.schemas.resume import ResumeOut, ResumeProfileUpdate
from app.security.files import delete_file, new_storage_path, sanitize_filename
from app.services import audit
from app.services.profile_service import get_profile

_CONTENT_TYPES = {"pdf": "pdf", "docx": "docx"}


def process_upload(db: Session, user: User, filename: str | None, data: bytes) -> Resume:
    settings = get_settings()
    safe_name = sanitize_filename(filename)
    if len(data) > settings.max_upload_bytes:
        raise AppError(413, "file_too_large", f"The file exceeds the {settings.max_upload_mb:g} MB limit.")
    try:
        document = extract_document(safe_name, data, settings.max_resume_chars)
    except DocumentError as exc:
        status = 415 if exc.code in {"unsupported_type", "type_mismatch"} else 422
        raise AppError(status, exc.code, exc.message) from None

    profile = extract_profile(document.text)
    preferences = get_profile(db, user)

    storage_path = None
    if settings.retain_resume_files:
        path = new_storage_path(settings.storage_dir, user.id, document.content_type)
        path.write_bytes(data)
        storage_path = str(path)

    # Only one active resume per user; older ones stay until the user deletes them.
    db.execute(update(Resume).where(Resume.user_id == user.id).values(is_active=False))

    resume = Resume(
        user_id=user.id,
        original_filename=safe_name,
        content_type=_CONTENT_TYPES[document.content_type],
        file_size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        storage_path=storage_path,
        page_count=document.page_count,
        char_count=len(document.text),
        status="processed",
        extraction_method=f"{document.method}+rules-v1",
        extraction_warnings=document.warnings + profile.warnings,
        raw_text=redact(document.text) if preferences.consent_store_resume_text else None,
        summary=profile.summary,
        total_experience_months=profile.total_experience_months,
        certifications=profile.certifications,
        achievements=profile.achievements,
        detected_preferences=profile.detected_preferences,
        is_active=True,
    )
    resume.skills = [
        ExtractedSkill(
            skill=m.name,
            category=m.category,
            source="extracted",
            evidence=m.evidence,
            confidence=0.9 if m.in_skill_context else 0.7,
        )
        for m in profile.skills
    ]
    resume.education = [
        EducationRecord(position=i, **vars(e)) for i, e in enumerate(profile.education)
    ]
    resume.experience = [
        ExperienceRecord(
            position=i,
            title=e.title,
            organization=e.organization,
            start_date=e.start_date,
            end_date=e.end_date,
            duration_months=e.duration_months,
            is_internship=e.is_internship,
            description=e.description,
        )
        for i, e in enumerate(profile.experience)
    ]
    resume.projects = [
        Project(position=i, name=p.name, description=p.description, skills=p.skills)
        for i, p in enumerate(profile.projects)
    ]
    db.add(resume)
    db.flush()
    audit.record(db, "resume_uploaded", user.id, resume_id=resume.id, content_type=resume.content_type)
    db.commit()
    db.refresh(resume)
    return resume


def get_user_resume(db: Session, user: User, resume_id: uuid.UUID) -> Resume:
    resume = db.get(Resume, resume_id)
    # Do not reveal whether another user's resume exists.
    if resume is None or resume.user_id != user.id:
        raise not_found("Resume")
    return resume


def list_user_resumes(db: Session, user: User) -> list[Resume]:
    return list(db.scalars(select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc())))


def to_out(resume: Resume) -> ResumeOut:
    out = ResumeOut.model_validate(resume)
    out.raw_text_stored = resume.raw_text is not None
    out.file_retained = resume.storage_path is not None
    return out


def apply_corrections(db: Session, user: User, resume: Resume, update_in: ResumeProfileUpdate) -> Resume:
    data = update_in.model_dump(exclude_unset=True)
    if "skills" in data and update_in.skills is not None:
        previous = {s.skill: s for s in resume.skills}
        new_skills: list[ExtractedSkill] = []
        seen: set[str] = set()
        for item in update_in.skills:
            name = canonicalize(item.skill)
            if name.lower() in seen:
                continue
            seen.add(name.lower())
            old = previous.get(name)
            if old is not None:
                new_skills.append(
                    ExtractedSkill(
                        skill=old.skill, category=old.category, source=old.source,
                        evidence=old.evidence, confidence=old.confidence,
                    )
                )
            else:
                new_skills.append(
                    ExtractedSkill(skill=name, category=category_of(name), source="user", evidence=None, confidence=1.0)
                )
        resume.skills = new_skills
    if update_in.education is not None:
        resume.education = [
            EducationRecord(position=i, source="user", **e.model_dump()) for i, e in enumerate(update_in.education)
        ]
    if update_in.experience is not None:
        resume.experience = [
            ExperienceRecord(position=i, source="user", **e.model_dump()) for i, e in enumerate(update_in.experience)
        ]
    if update_in.projects is not None:
        resume.projects = [
            Project(
                position=i,
                source="user",
                name=p.name,
                description=p.description,
                skills=[canonicalize(s) for s in p.skills if s.strip()],
            )
            for i, p in enumerate(update_in.projects)
        ]
    for key in ("certifications", "achievements", "summary", "total_experience_months"):
        if key in data:
            setattr(resume, key, data[key] if data[key] is not None else ([] if key in {"certifications", "achievements"} else None))
    resume.status = "reviewed"
    audit.record(db, "resume_corrected", user.id, resume_id=resume.id)
    db.commit()
    db.refresh(resume)
    return resume


def delete_resume(db: Session, user: User, resume: Resume) -> None:
    settings = get_settings()
    delete_file(settings.storage_dir, resume.storage_path)
    was_active = resume.is_active
    resume_id = resume.id
    db.delete(resume)
    db.flush()
    if was_active:
        newest = db.scalar(select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc()))
        if newest is not None:
            newest.is_active = True
    audit.record(db, "resume_deleted", user.id, resume_id=resume_id)
    db.commit()
