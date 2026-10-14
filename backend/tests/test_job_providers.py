"""Provider tests use recorded-format responses (shapes from the official docs).

No network access is needed: httpx.MockTransport stands in for the provider.
"""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.integrations.jobs.base import ProviderError, ProviderRateLimited, ProviderSchemaError
from app.integrations.jobs.greenhouse import GreenhouseProvider
from app.integrations.jobs.lever import LeverProvider
from app.models import JobListing, JobSource
from app.services import job_service

GH_CONTENT = (
    "&lt;p&gt;We build tools for small businesses.&lt;/p&gt;"
    "&lt;h3&gt;Requirements&lt;/h3&gt;&lt;ul&gt;&lt;li&gt;Strong SQL and Python&lt;/li&gt;"
    "&lt;li&gt;2+ years of experience with data analysis&lt;/li&gt;&lt;/ul&gt;"
    "&lt;h3&gt;Nice to have&lt;/h3&gt;&lt;ul&gt;&lt;li&gt;Power BI&lt;/li&gt;&lt;/ul&gt;"
)


def gh_job(job_id=101, title="Data Analyst", content=GH_CONTENT, **extra):
    job = {
        "id": job_id,
        "internal_job_id": 555,
        "title": title,
        "updated_at": "2026-10-01T10:00:00-04:00",
        "requisition_id": "R-1",
        "location": {"name": "Manila, Philippines (Hybrid)"},
        "absolute_url": f"https://boards.greenhouse.io/acme/jobs/{job_id}",
        "language": "en",
        "metadata": None,
        "content": content,
        "departments": [{"id": 1, "name": "Analytics", "parent_id": None, "child_ids": []}],
        "offices": [],
    }
    job.update(extra)
    return job


def lever_posting(pid="abc-123", **extra):
    posting = {
        "id": pid,
        "text": "Junior Frontend Engineer",
        "categories": {"location": "Remote - Philippines", "commitment": "Full-time", "team": "Web", "department": "Engineering"},
        "country": "PH",
        "workplaceType": "remote",
        "description": "<div>Join our web team.</div>",
        "descriptionPlain": "Join our web team.",
        "lists": [
            {"text": "What you'll need", "content": "<li>Experience with React and TypeScript</li><li>Git</li>"},
            {"text": "Bonus points", "content": "<li>Tailwind CSS</li>"},
        ],
        "additional": "<div>We offer HMO coverage.</div>",
        "hostedUrl": f"https://jobs.lever.co/acme/{pid}",
        "applyUrl": f"https://jobs.lever.co/acme/{pid}/apply",
        "salaryRange": {"currency": "PHP", "interval": "per-month-salary", "min": 40000, "max": 60000},
        "createdAt": 1759000000000,
    }
    posting.update(extra)
    return posting


def transport(routes):
    def handler(request: httpx.Request) -> httpx.Response:
        for prefix, response in routes.items():
            if str(request.url).startswith(prefix):
                return response(request) if callable(response) else response
        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------- unit level


def test_greenhouse_parses_documented_shape():
    t = transport({"https://boards-api.greenhouse.io/v1/boards/acme/jobs": httpx.Response(200, json={"jobs": [gh_job()], "meta": {"total": 1}})})
    result = GreenhouseProvider("acme", "Acme", transport=t).fetch()
    assert len(result.listings) == 1
    listing = result.listings[0]
    assert listing.external_id == "101" and listing.company == "Acme"
    assert listing.posted_at is None  # updated_at is not a posting date
    normalised = job_service.normalise(listing)
    levels = {s.skill: s.requirement for s in normalised["_skills"]}
    assert levels["SQL"] == "required" and levels["Python"] == "required" and levels["Power BI"] == "preferred"
    assert normalised["work_arrangement"] == "hybrid"
    assert normalised["min_years_experience"] == 2
    assert normalised["salary_min"] is None  # never invented


def test_lever_parses_lists_salary_and_paginates():
    calls = []

    def handler(request):
        calls.append(dict(request.url.params))
        skip = int(request.url.params["skip"])
        if skip == 0:
            return httpx.Response(200, json=[lever_posting(f"p{i}") for i in range(100)])
        return httpx.Response(200, json=[lever_posting("last")])

    t = transport({"https://api.lever.co/v0/postings/acme": handler})
    result = LeverProvider("acme", "Acme", transport=t).fetch()
    assert len(result.listings) == 101
    assert [c["skip"] for c in calls] == ["0", "100"]
    normalised = job_service.normalise(result.listings[0])
    levels = {s.skill: s.requirement for s in normalised["_skills"]}
    assert levels["React"] == "required" and levels["Tailwind CSS"] == "preferred"
    assert normalised["work_arrangement"] == "remote"
    assert normalised["employment_type"] == "full_time"
    assert normalised["experience_level"] == "entry"
    assert str(normalised["salary_min"]) == "40000" and normalised["salary_currency"] == "PHP"


def test_empty_responses():
    gh = transport({"https://boards-api.greenhouse.io": httpx.Response(200, json={"jobs": [], "meta": {"total": 0}})})
    lv = transport({"https://api.lever.co": httpx.Response(200, json=[])})
    assert GreenhouseProvider("acme", transport=gh).fetch().listings == []
    assert LeverProvider("acme", transport=lv).fetch().listings == []


def test_rate_limit_and_errors():
    limited = transport({"https://boards-api.greenhouse.io": httpx.Response(429, headers={"Retry-After": "30"})})
    with pytest.raises(ProviderRateLimited) as info:
        GreenhouseProvider("acme", transport=limited).fetch()
    assert info.value.retry_after == 30
    broken = transport({"https://boards-api.greenhouse.io": httpx.Response(503)})
    with pytest.raises(ProviderError):
        GreenhouseProvider("acme", transport=broken).fetch()
    missing = transport({})
    with pytest.raises(ProviderError, match="not found"):
        LeverProvider("nope", transport=missing).fetch()

    def boom(request):
        raise httpx.ConnectError("down")

    with pytest.raises(ProviderError, match="could not be reached"):
        GreenhouseProvider("acme", transport=httpx.MockTransport(boom)).fetch()


def test_invalid_schema():
    bad_shape = transport({"https://boards-api.greenhouse.io": httpx.Response(200, json={"postings": []})})
    with pytest.raises(ProviderSchemaError):
        GreenhouseProvider("acme", transport=bad_shape).fetch()
    not_json = transport({"https://api.lever.co": httpx.Response(200, text="<html>")})
    with pytest.raises(ProviderSchemaError):
        LeverProvider("acme", transport=not_json).fetch()
    partial = transport({"https://boards-api.greenhouse.io": httpx.Response(
        200, json={"jobs": [gh_job(), {"id": 2}, gh_job(3, absolute_url="http://insecure.example/3")]})})
    result = GreenhouseProvider("acme", transport=partial).fetch()
    assert len(result.listings) == 1 and result.skipped_invalid == 2


# ---------------------------------------------------------------- service level


@pytest.fixture()
def live_settings(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "greenhouse_boards_raw", "acme")
    monkeypatch.setattr(settings, "lever_sites_raw", "acme")
    monkeypatch.setattr(settings, "enable_demo_provider", False)
    return settings


def _routes(gh_jobs, lever_postings, gh_status=200):
    return transport({
        "https://boards-api.greenhouse.io/v1/boards/acme/jobs": httpx.Response(gh_status, json={"jobs": gh_jobs}),
        "https://api.lever.co/v0/postings/acme": httpx.Response(200, json=lever_postings),
    })


def test_refresh_ingests_and_records_freshness(db, live_settings):
    results = job_service.refresh_jobs(db, live_settings, transport=_routes([gh_job()], [lever_posting()]))
    assert {r.status for r in results} == {"ok"}
    jobs = db.scalars(select(JobListing)).all()
    assert len(jobs) == 2
    for job in jobs:
        assert job.apply_url.startswith("https://") and job.last_checked_at is not None
        assert job.is_demo is False


def test_duplicate_listings_are_collapsed(db, live_settings):
    same = gh_job(201, title="Junior Frontend Engineer", content="<div>Join our web team.</div>",
                  location={"name": "Remote - Philippines"})
    # Same company/title/location/description posted on two providers.
    lever = lever_posting("dup", lists=[], additional=None)
    live_settings.greenhouse_boards_raw = "acme"
    t = _routes([same], [lever])
    # Make company names match (Greenhouse falls back to the board display name).
    job_service.refresh_jobs(db, live_settings, transport=t)
    jobs = db.scalars(select(JobListing)).all()
    assert len(jobs) == 2
    assert sum(1 for j in jobs if j.duplicate_of_id is not None) == 1


def test_missing_listing_is_expired_on_next_refresh(db, live_settings):
    job_service.refresh_jobs(db, live_settings, transport=_routes([gh_job(1), gh_job(2, title="BI Analyst")], []))
    job_service.refresh_jobs(db, live_settings, force=True, transport=_routes([gh_job(1)], []))
    statuses = {j.external_id: j.status for j in db.scalars(select(JobListing))}
    assert statuses == {"1": "active", "2": "expired"}


def test_past_deadline_is_expired(db, live_settings):
    past = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    job_service.refresh_jobs(db, live_settings, transport=_routes([gh_job(9, application_deadline=past)], []))
    assert db.scalar(select(JobListing)).status == "expired"


def test_provider_error_keeps_existing_listings(db, live_settings):
    job_service.refresh_jobs(db, live_settings, transport=_routes([gh_job(1)], []))
    results = job_service.refresh_jobs(db, live_settings, force=True, transport=_routes([], [], gh_status=500))
    gh = next(r for r in results if r.provider == "greenhouse")
    assert gh.status == "error"
    assert db.scalar(select(JobListing).where(JobListing.external_id == "1")).status == "active"
    source = db.scalar(select(JobSource).where(JobSource.provider == "greenhouse"))
    assert source.last_status == "error" and "500" in source.last_error


def test_cooldown_skips_recent_sources(db, live_settings):
    t = _routes([gh_job(1)], [])
    job_service.refresh_jobs(db, live_settings, transport=t)
    results = job_service.refresh_jobs(db, live_settings, transport=t)
    assert {r.status for r in results} == {"skipped_cooldown"}


def test_unconfigured_providers_reported_honestly(client, auth_headers, monkeypatch):
    monkeypatch.setattr(get_settings(), "enable_demo_provider", False)
    body = client.get("/api/v1/jobs/sources", headers=auth_headers).json()
    assert all(p["configured"] is False for p in body["providers"])
    assert body["sources"] == [] and body["demo_enabled"] is False
    assert "LinkedIn" in body["unsupported_note"]
    listing = client.get("/api/v1/jobs", headers=auth_headers).json()
    assert listing["total"] == 0 and listing["items"] == []


def test_concurrent_source_sync_is_safe(db_engine):
    """Several requests syncing sources at once must not fail on the unique constraint."""
    from concurrent.futures import ThreadPoolExecutor

    from app.db.session import SessionLocal
    from app.integrations.jobs.registry import build_providers

    def worker(_):
        with SessionLocal() as session:
            job_service.sync_sources(session, build_providers(get_settings()))
            session.commit()

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(worker, range(8)))
    with SessionLocal() as session:
        assert len(session.scalars(select(JobSource)).all()) == 1
