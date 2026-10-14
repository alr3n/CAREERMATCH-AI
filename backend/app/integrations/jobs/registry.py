"""Build provider instances from configuration."""

from __future__ import annotations

import re

import httpx

from app.core.config import Settings
from app.integrations.jobs.base import JobProvider
from app.integrations.jobs.demo import DemoProvider
from app.integrations.jobs.greenhouse import GreenhouseProvider
from app.integrations.jobs.lever import LeverProvider

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,119}$")

# Providers the application knows how to talk to, with their access terms.
KNOWN_PROVIDERS = {
    "greenhouse": {
        "name": "Greenhouse Job Board API",
        "docs": "https://developers.greenhouse.io/job-board.html",
        "config": "GREENHOUSE_BOARDS",
        "notes": "Public, per-company boards. Configure the board tokens of companies you want to track.",
    },
    "lever": {
        "name": "Lever Postings API",
        "docs": "https://github.com/lever/postings-api",
        "config": "LEVER_SITES",
        "notes": "Public, per-company postings. Configure the Lever site names of companies you want to track.",
    },
}


def _display(identifier: str) -> str:
    return identifier.replace("-", " ").replace("_", " ").title()


def build_providers(settings: Settings, transport: httpx.BaseTransport | None = None) -> list[JobProvider]:
    providers: list[JobProvider] = []
    for token in settings.greenhouse_boards:
        if _IDENTIFIER.match(token):
            providers.append(
                GreenhouseProvider(token, _display(token), timeout=settings.provider_timeout_seconds, transport=transport)
            )
    for site in settings.lever_sites:
        if _IDENTIFIER.match(site):
            providers.append(
                LeverProvider(
                    site,
                    _display(site),
                    timeout=settings.provider_timeout_seconds,
                    transport=transport,
                    region=settings.lever_region,
                )
            )
    if settings.enable_demo_provider:
        providers.append(DemoProvider())
    return providers
