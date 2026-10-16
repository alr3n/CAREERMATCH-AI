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


def parse_entries(values: list[str]) -> list[tuple[str, str]]:
    """Parse ``identifier`` or ``identifier:Display Name`` entries.

    The display name is the operator's label for the company, used when the
    provider's API has no company-name field (Lever). Invalid identifiers are
    ignored.
    """
    entries: list[tuple[str, str]] = []
    for value in values:
        identifier, _, name = value.partition(":")
        identifier, name = identifier.strip(), name.strip()[:80]
        if _IDENTIFIER.match(identifier):
            entries.append((identifier, name or _display(identifier)))
    return entries


def configured_sources(settings: Settings) -> dict[str, list[str]]:
    """Identifiers configured for each known provider (for status pages)."""
    return {
        "greenhouse": [i for i, _ in parse_entries(settings.greenhouse_boards)],
        "lever": [i for i, _ in parse_entries(settings.lever_sites)],
        "smartrecruiters": [i for i, _ in parse_entries(settings.smartrecruiters_companies)],
        "remotive": ["remote-jobs"] if settings.remotive_enabled else [],
        # Queries, not the key, are shown.
        "jsearch": settings.jsearch_queries if settings.jsearch_configured else [],
    }


def build_providers(settings: Settings, transport: httpx.BaseTransport | None = None) -> list[JobProvider]:
    timeout = settings.provider_timeout_seconds
    providers: list[JobProvider] = []
    for token, name in parse_entries(settings.greenhouse_boards):
        providers.append(GreenhouseProvider(token, name, timeout=timeout, transport=transport))
    for site, name in parse_entries(settings.lever_sites):
        providers.append(LeverProvider(site, name, timeout=timeout, transport=transport, region=settings.lever_region))
    for company, name in parse_entries(settings.smartrecruiters_companies):
        providers.append(
            SmartRecruitersProvider(
                company,
                name,
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
