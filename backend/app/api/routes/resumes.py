from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, rate_limit_user
from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.models import User
from app.schemas.resume import ResumeOut, ResumeProfileUpdate, ResumeSummaryOut
from app.services import resume_service

router = APIRouter(prefix="/resumes", tags=["resumes"])

_CHUNK = 64 * 1024


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    data = bytearray()
    while chunk := await file.read(_CHUNK):
        data.extend(chunk)
        if len(data) > limit:
            raise AppError(413, "file_too_large", f"The file exceeds the {get_settings().max_upload_mb:g} MB limit.")
    return bytes(data)


@router.post(
    "/upload",
    response_model=ResumeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_user("upload", "rate_limit_upload"))],
    summary="Upload a PDF or DOCX resume and extract a structured profile",
)
async def upload_resume(
    file: UploadFile = File(..., description="PDF or DOCX, up to MAX_UPLOAD_MB"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeOut:
    data = await _read_limited(file, get_settings().max_upload_bytes)
    resume = resume_service.process_upload(db, user, file.filename, data)
    return resume_service.to_out(resume)


@router.get("", response_model=list[ResumeSummaryOut], summary="List your resumes")
def list_resumes(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[ResumeSummaryOut]:
    return [ResumeSummaryOut.model_validate(r) for r in resume_service.list_user_resumes(db, user)]


@router.get("/{resume_id}", response_model=ResumeOut, summary="Get an extracted resume profile")
def get_resume(
    resume_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ResumeOut:
    return resume_service.to_out(resume_service.get_user_resume(db, user, resume_id))


@router.patch(
    "/{resume_id}/profile",
    response_model=ResumeOut,
    summary="Correct the extracted profile (skills, education, experience, projects …)",
)
def correct_resume(
    resume_id: uuid.UUID,
    body: ResumeProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ResumeOut:
    resume = resume_service.get_user_resume(db, user, resume_id)
    return resume_service.to_out(resume_service.apply_corrections(db, user, resume, body))


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a resume, its stored file, extracted profile and related matches",
)
def delete_resume(
    resume_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    resume = resume_service.get_user_resume(db, user, resume_id)
    resume_service.delete_resume(db, user, resume)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
