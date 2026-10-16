"""TEST USE ONLY: API server for the Playwright end-to-end suite.

Starts the normal application with the offline fixture provider added, so the
browser tests have listings without network access. Real providers are turned
off through the environment set in ``frontend/playwright.config.ts``. This file
lives under ``backend/tests`` and is never used by the deployed application.

    python -m tests.e2e_server --port 8000
"""

from __future__ import annotations

import argparse

import uvicorn

from app.integrations.jobs import registry
from tests.fixture_jobs import FixtureProvider

_real_build_providers = registry.build_providers


def _with_fixture(settings, transport=None):
    return _real_build_providers(settings, transport) + [FixtureProvider()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    registry.build_providers = _with_fixture
    from app.main import create_app

    uvicorn.run(create_app(), host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
