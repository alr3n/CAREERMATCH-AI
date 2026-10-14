"""Shared pytest fixtures.

Tests run against SQLite by default so they need no external services. Set
``TEST_DATABASE_URL`` to a PostgreSQL URL to run the same suite against
PostgreSQL (CI does this).
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="careermatch-tests-"))
os.environ.setdefault("APP_ENV", "test")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_TMP / 'test.db'}")
os.environ["STORAGE_DIR"] = str(_TMP / "storage")
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256-signing"
os.environ["ENABLE_DEMO_PROVIDER"] = "true"
os.environ["GREENHOUSE_BOARDS"] = ""
os.environ["LEVER_SITES"] = ""
os.environ["EMBEDDING_BACKEND"] = "lsa"
os.environ["LLM_PROVIDER"] = "none"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.core.rate_limit import rate_limiter  # noqa: E402
from app.db import session as db_session  # noqa: E402
from app.db.base import Base  # noqa: E402
import app.models  # noqa: E402,F401
from app.main import create_app  # noqa: E402


@pytest.fixture()
def db_engine():
    engine = db_session.engine
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db(db_engine):
    session = db_session.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_engine) -> Iterator[TestClient]:
    rate_limiter.reset()
    with TestClient(create_app()) as c:
        yield c
    rate_limiter.reset()
