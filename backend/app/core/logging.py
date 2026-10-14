"""Logging configuration that avoids leaking personal information.

Resume text, contact details, tokens and passwords must never be logged. The
``RedactingFilter`` is a last line of defence: it masks e-mail addresses,
phone-number-like sequences and bearer tokens if they slip into a log record.
"""

from __future__ import annotations

import logging
import re

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Phone-like: 10+ digits separated by spaces, dashes or brackets (not dots, so IPs are left alone).
_PHONE = re.compile(r"(?<![\d.])\+?\d(?:[\s()-]*\d){9,}(?![\d.])")
_BEARER = re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]+")
_JWT = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")


def redact(text: str) -> str:
    text = _BEARER.sub("Bearer [REDACTED]", text)
    text = _JWT.sub("[REDACTED_TOKEN]", text)
    text = _EMAIL.sub("[REDACTED_EMAIL]", text)
    text = _PHONE.sub("[REDACTED_PHONE]", text)
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - trivial
        try:
            message = record.getMessage()
        except Exception:
            return True
        record.msg = redact(message)
        record.args = None
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # Uvicorn access logs include query strings; keep them but redact.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers = [handler]
        logger.propagate = False
