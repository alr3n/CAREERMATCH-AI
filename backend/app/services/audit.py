"""Audit trail helper. Never pass resume content or contact details here."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models import AuditEvent


def record(db: Session, event_type: str, user_id: uuid.UUID | None = None, **detail: object) -> None:
    safe = {k: (str(v) if isinstance(v, uuid.UUID) else v) for k, v in detail.items()}
    db.add(AuditEvent(user_id=user_id, event_type=event_type, detail=safe))
