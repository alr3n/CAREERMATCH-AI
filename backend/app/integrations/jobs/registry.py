"""Build provider instances from configuration.

Only providers that fetch real postings from an external, documented source
are registered here. There is no demo or sample provider in the application;
offline test data lives in ``backend/tests`` and is injected by the test suite.
"""

from __future__ import annotations

import re

import httpx

from app.core.config import Settings
from app.integrations.jobs.base import JobProvider
from app.integrations.jobs.greenhouse import GreenhouseProvider
from app.integrations.jobs.jsearch import JSearchProvider
from app.integrations.jobs.lever import LeverProvider
from app.integrations.jobs.remotive import RemotiveProvider
from app.integrations.jobs.smartrecruiters import SmartRecruitersProvider

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,119}$")

# Providers the application knows how to talk to, with their access terms.
KNOWN_PROVIDERS = {
    "greenhouse": {
        "name": "Greenhouse Job Board API",
        "docs": "https://developers.greenhouse.io/job-board.html",
        "config": "GREENHOUSE_BOARDS",
        "access": "Public, no key",
        "notes": "Per-company boards. Only postings located in the Philippines (or remote and open to it) are kept.",
    },
    "lever": {
        "name": "Lever Postings API",
        "docs": "https://github.com/lever/postings-api",
        "config": "LEVER_SITES",
        "access": "Public, no key",
        "notes": "Per-company sites. Only postings located in the Philippines (or remote and open to it) are kept.",
    },
    "smartrecruiters": {
        "name": "SmartRecruiters Posting API",
        "docs": "https://developers.smartrecruiters.com/docs/posting-api",
        "config": "SMARTRECRUITERS_COMPANIES",
        "access": "Public, no key",
        "notes": "Per-company postings, filtered to the Philippines by SmartRecruiters (SMARTRECRUITERS_COUNTRY).",
    },
    "remotive": {
        "name": "Remotive Remote Jobs API",
        "docs": "https://github.com/remotive-com/remote-jobs-api",
        "config": "REMOTIVE_ENABLED",
        "access": "Public, no key; attribution and link-back required; at most ~4 fetches a day",
        "notes": "Remote roles open to applicants worldwide, in Asia/APAC or in the Philippines. Public feed is delayed 24 hours.",
    },
    "jsearch": {
        "name": "JSearch (Google for Jobs aggregator)",
        "docs": "https://www.openwebninja.com/api/jsearch",
        "config": "JSEARCH_API_KEY + JSEARCH_QUERIES",
        "access": "Paid API key (free plan: 200 requests/month)",
        "notes": "The authorised route to postings published on LinkedIn, Indeed, Glassdoor and JobStreet.",
    },
}


def _display(identifier: str) -> str:
    return identifier.replace("-", " ").replace("_", " ").title()


def configured_sources(settings: Settings) -> dict[str, list[str]]:
    """Identifiers configured for each known provider (for status pages)."""
    return {
        "greenhouse": [t for t in settings.greenhouse_boards if _IDENTIFIER.match(t)],
        "lever": [s for s in settings.lever_sites if _IDENTIFIER.match(s)],
        "smartrecruiters": [c for c in settings.smartrecruiters_companies if _IDENTIFIER.match(c)],
        "remotive": ["remote-jobs"] if settings.remotive_enabled else [],
        # Queries, not the key, are shown.
        "jsearch": settings.jsearch_queries if settings.jsearch_configured else [],
    }


def build_providers(settings: Settings, transport: httpx.BaseTransport | None = None) -> list[JobProvider]:
    timeout = settings.provider_timeout_seconds
    configured = configured_sources(settings)
    providers: list[JobProvider] = []
    for token in configured["greenhouse"]:
        providers.append(GreenhouseProvider(token, _display(token), timeout=timeout, transport=transport))
    for site in configured["lever"]:
        providers.append(
            LeverProvider(site, _display(site), timeout=timeout, transport=transport, region=settings.lever_region)
        )
    for company in configured["smartrecruiters"]:
        providers.append(
            SmartRecruitersProvider(
                company,
                company,
                timeout=timeout,
                transport=transport,
                country=settings.smartrecruiters_country,
                max_details=settings.smartrecruiters_max_details,
            )
        )
    if settings.remotive_enabled:
        providers.append(
            RemotiveProvider(
                "remote-jobs", "Remotive", timeout=timeout, transport=transport, category=settings.remotive_category
            )
        )
    if settings.jsearch_configured:
        providers.append(
            JSearchProvider(
                settings.jsearch_country.lower(),
                f"JSearch ({settings.jsearch_country.upper()})",
                timeout=timeout,
                transport=transport,
                api_key=settings.jsearch_api_key,
                queries=settings.jsearch_queries,
                country=settings.jsearch_country.lower(),
                date_posted=settings.jsearch_date_posted,
                pages=settings.jsearch_pages,
                min_interval_minutes=settings.jsearch_min_interval_minutes,
            )
        )
    return providers
