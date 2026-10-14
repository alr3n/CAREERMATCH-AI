from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field, model_validator

AssistantTask = Literal[
    "explain_requirements",
    "resume_suggestions",
    "rewrite_bullet",
    "portfolio_projects",
    "interview_questions",
    "cover_letter",
]

REVIEW_NOTICE = (
    "Draft for your review. It is based only on your profile and this job posting — check every statement, "
    "remove anything that is not true for you, and never submit it unedited. CareerMatch AI does not send "
    "applications on your behalf."
)


class AssistantRequest(BaseModel):
    task: AssistantTask
    job_id: uuid.UUID
    input_text: str | None = Field(default=None, max_length=1500, description="Resume bullet to rewrite")
    mode: Literal["auto", "template", "llm"] = "auto"

    @model_validator(mode="after")
    def _bullet_required(self) -> AssistantRequest:
        if self.task == "rewrite_bullet" and not (self.input_text and self.input_text.strip()):
            raise ValueError("input_text is required for rewrite_bullet")
        return self


class AssistantSection(BaseModel):
    heading: str
    items: list[str]


class AssistantResponse(BaseModel):
    task: AssistantTask
    mode_used: Literal["template", "llm"]
    model: str | None
    title: str
    sections: list[AssistantSection]
    text: str
    review_required: bool = True
    notice: str = REVIEW_NOTICE
    fallback_reason: str | None = None


class AssistantStatus(BaseModel):
    llm_configured: bool
    provider: str | None
    consent_given: bool
    data_shared_with_llm: list[str]
    note: str
