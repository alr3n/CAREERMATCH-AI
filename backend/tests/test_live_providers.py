"""SmartRecruiters, Remotive and JSearch providers, location filtering,
cross-source deduplication and the demo-data purge migration.

Response bodies follow the shapes returned by the live APIs on 2026-10-16
(SmartRecruiters: Grab / Sutherland; Remotive: public feed; Greenhouse: Xendit;
Lever: Coins.ph). Values are shortened. No network access is used.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from app.integrations.jobs.base import ProviderError, ProviderListing
from app.integrations.jobs.jsearch import JSearchProvider
from app.integrations.jobs.location import in_philippines
from app.integrations.jobs.remotive import RemotiveProvider, open_to_philippines
from app.integrations.jobs.smartrecruiters import SmartRecruitersProvider
from app.models import JobListing
from app.services import job_service

BACKEND = Path(__file__).resolve().parents[1]


def transport(routes, calls: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request)
        url = str(request.url)
        for prefix, response in routes.items():
            if url.startswith(prefix):
                return response(request) if callable(response) else response
        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handler)


# ------------------------------------------------------------- SmartRecruiters


def sr_item(pid="744000155413387", name="Director, Grab Financial Group", **extra):
    item = {
        "id": pid,
        "name": name,
        "uuid": "8434187f-e2b4-4116-83d4-c9184492c7fd",
        "refNumber": "REF5965H",
        "company": {"identifier": "Grab", "name": "Grab"},
        "releasedDate": "2026-10-14T05:26:34.523Z",
        "location": {"city": "Pasig City", "country": "ph", "address": "Exquadra Tower", "remote": False,
                     "hybrid": False, "fullLocation": "Pasig City, , Philippines"},
        "industry": {"id": "financial_services", "label": "Financial Services"},
        "department": {},
        "function": {"id": "strategy_planning", "label": "Strategy/Planning"},
        "typeOfEmployment": {"id": "permanent", "label": "Full-time"},
        "experienceLevel": {"id": "executive", "label": "Executive"},
        "customField": [],
        "visibility": "PUBLIC",
        "ref": f"https://api.smartrecruiters.com/v1/companies/Grab/postings/{pid}",
        "language": {"code": "en", "label": "English"},
    }
    item.update(extra)
    return item


def sr_detail(pid="744000155413387"):
    return {
        **sr_item(pid),
        "postingUrl": f"https://jobs.smartrecruiters.com/Grab/{pid}-director-grab-financial-group",
        "applyUrl": f"https://jobs.smartrecruiters.com/Grab/{pid}-director-grab-financial-group?oga=true",
        "active": True,
        "jobAd": {"sections": {
            "companyDescription": {"title": "Company Description", "text": "<p>Grab is Southeast Asia's leading superapp.</p>"},
            "jobDescription": {"title": "Job Description", "text": "<p>Lead strategy for GFG Philippines.</p>"},
            "qualifications": {"title": "Qualifications", "text": "<ul><li>10+ years of experience in financial services</li>"
                                                                  "<li>Strong SQL and Excel</li></ul>"},
            "additionalInformation": {"title": "Additional Information", "text": "<p>Hybrid work.</p>"},
        }},
    }


def test_smartrecruiters_maps_list_and_detail():
    calls: list[httpx.Request] = []
    t = transport({
        "https://api.smartrecruiters.com/v1/companies/Grab/postings/744000155413387": httpx.Response(200, json=sr_detail()),
        "https://api.smartrecruiters.com/v1/companies/Grab/postings": httpx.Response(
            200, json={"offset": 0, "limit": 100, "totalFound": 1, "content": [sr_item()]}),
    }, calls)
    result = SmartRecruitersProvider("Grab", "Grab", transport=t, country="ph").fetch()
    assert calls[0].url.params["country"] == "ph"
    [job] = result.listings
    assert job.title == "Director, Grab Financial Group" and job.company == "Grab"
    assert job.location == "Pasig City, Philippines" and job.country == "PH"
    assert job.commitment == "Full-time" and job.department == "Strategy/Planning"
    assert job.posting_url.endswith("-director-grab-financial-group")
    assert job.apply_url.endswith("?oga=true") and job.source_platform == "SmartRecruiters"
    assert job.posted_at.year == 2026
    assert job.salary_min is None and job.salary_text is None  # not provided, not invented
    assert "10+ years" in job.content_html and job.content_html.index("Job Description") < job.content_html.index("Company")


def test_smartrecruiters_detail_failure_keeps_real_listing():
    t = transport({
        "https://api.smartrecruiters.com/v1/companies/Grab/postings/1": httpx.Response(500),
        "https://api.smartrecruiters.com/v1/companies/Grab/postings": httpx.Response(
            200, json={"offset": 0, "limit": 100, "totalFound": 2, "content": [sr_item("1"), {"name": "no id"}]}),
    })
    result = SmartRecruitersProvider("Grab", "Grab", transport=t).fetch()
    assert result.skipped_invalid == 1
    [job] = result.listings
    assert job.posting_url == "https://jobs.smartrecruiters.com/Grab/1"
    assert job.content_html is None and job.content_text == ""


# --------------------------------------------------------------------- Remotive


def remotive_job(jid=2069746, location="Worldwide", **extra):
    job = {
        "id": jid,
        "url": f"https://remotive.com/remote-jobs/software-development/tech-lead-{jid}",
        "title": "Tech Lead Full-Stack Rails Engineer",
        "company_name": "Mitre Media",
        "company_logo": f"https://remotive.com/job/{jid}/logo",
        "category": "Software Development",
        "tags": ["api", "docker"],
        "job_type": "full_time",
        "publication_date": "2026-10-14T20:33:44",
        "candidate_required_location": location,
        "salary": "$170k - $200k",
        "description": "<p>Requirements</p><ul><li>5+ years of Ruby on Rails</li></ul>",
    }
    job.update(extra)
    return job


def test_remotive_keeps_only_roles_open_to_the_philippines():
    body = {"00-warning": "…", "0-legal-notice": "…", "job-count": 3, "total-job-count": 3, "jobs": [
        remotive_job(1, "Worldwide"), remotive_job(2, "USA, Canada, USA timezones"), remotive_job(3, "Europe, USA, Canada, APAC"),
    ]}
    result = RemotiveProvider("remote-jobs", "Remotive", transport=transport(
        {"https://remotive.com/api/remote-jobs": httpx.Response(200, json=body)})).fetch()
    assert [x.external_id for x in result.listings] == ["1", "3"]
    job = result.listings[0]
    assert job.posting_url == job.apply_url and job.apply_url.startswith("https://remotive.com/")
    assert job.source_platform == "Remotive" and job.workplace_type == "remote"
    assert job.commitment == "Full-time" and job.salary_text == "$170k - $200k"
    assert open_to_philippines("Philippines only") and not open_to_philippines("UK")


# ---------------------------------------------------------------------- JSearch


def jsearch_job(jid="abc123==", publisher="LinkedIn", **extra):
    job = {
        "job_id": jid,
        "job_title": "Data Analyst",
        "employer_name": "Acme Philippines",
        "employer_logo": None,
        "job_publisher": publisher,
        "job_employment_type": "FULLTIME",
        "job_apply_link": f"https://www.linkedin.com/jobs/view/{abs(hash(jid)) % 10**9}",
        "job_apply_is_direct": False,
        "job_description": "We need SQL and Power BI skills.",
        "job_is_remote": False,
        "job_posted_at_datetime_utc": "2026-10-12T00:00:00.000Z",
        "job_location": "Makati, Metro Manila, Philippines",
        "job_city": "Makati",
        "job_country": "PH",
        "job_min_salary": None,
        "job_max_salary": None,
        "job_salary_period": None,
        "job_highlights": {"Qualifications": ["2+ years of experience with SQL"], "Responsibilities": ["Build dashboards"]},
    }
    job.update(extra)
    return job


def test_jsearch_sends_key_only_in_header_and_maps_publisher():
    calls: list[httpx.Request] = []
    body = {"status": "OK", "request_id": "x", "data": [
        jsearch_job(),
        jsearch_job("2", "Indeed", job_min_salary=30000, job_max_salary=45000, job_salary_currency="PHP",
                    job_salary_period="MONTH"),
        jsearch_job("3", job_apply_link="http://insecure.example/3"),
    ]}
    provider = JSearchProvider("ph", "JSearch (PH)", api_key="secret-key-123", queries=["data analyst in Philippines"],
                               transport=transport({"https://jsearch.p.rapidapi.com/search": httpx.Response(200, json=body)}, calls))
    result = provider.fetch()
    request = calls[0]
    assert request.headers["X-RapidAPI-Key"] == "secret-key-123"
    assert "secret-key-123" not in str(request.url) and "secret-key-123" not in repr(provider)
    assert request.url.params["country"] == "ph" and request.url.params["num_pages"] == "1"
    assert result.skipped_invalid == 1
    linkedin, indeed = result.listings
    assert linkedin.source_platform == "LinkedIn" and linkedin.commitment == "Full-time"
    assert linkedin.salary_min is None and linkedin.salary_currency is None and linkedin.salary_interval is None
    assert ("Qualifications", ["2+ years of experience with SQL"]) in linkedin.sections
    assert indeed.source_platform == "Indeed" and indeed.salary_min == 30000
    assert indeed.salary_currency == "PHP" and indeed.salary_interval == "per-month-salary"


def test_jsearch_auth_error_does_not_leak_key():
    provider = JSearchProvider("ph", "JSearch", api_key="secret-key-123", queries=["x"],
                               transport=transport({"https://jsearch.p.rapidapi.com": httpx.Response(403, text="bad key")}))
    with pytest.raises(ProviderError) as info:
        provider.fetch()
    assert "403" in info.value.message and "secret" not in info.value.message


def test_jsearch_needs_key_and_queries(monkeypatch, production_providers):
    from app.integrations.jobs import registry

    settings = production_providers
    monkeypatch.setattr(settings, "jsearch_api_key", "k")
    assert not any(p.provider == "jsearch" for p in registry.build_providers(settings))
    monkeypatch.setattr(settings, "jsearch_queries_raw", "data analyst in Philippines; developer in Cebu, PH")
    [jsearch] = [p for p in registry.build_providers(settings) if p.provider == "jsearch"]
    assert jsearch.queries == ["data analyst in Philippines", "developer in Cebu, PH"]
    sources = registry.configured_sources(settings)["jsearch"]
    assert "k" not in sources  # status lists queries, never the key


# ------------------------------------------------------------- location filter


@pytest.mark.parametrize(("location", "country", "workplace", "expected"), [
    ("Jakarta, Indonesia; Manila, Philippines", None, None, True),   # Greenhouse multi-office (Xendit)
    ("Taguig City, Metro Manila, Philippines", None, "hybrid", True),
    ("Cebu City", None, None, True),
    ("Remote, United States", None, "remote", False),
    ("Remote - APAC", None, "remote", True),
    ("Singapore", None, None, False),
    ("Anywhere", "PH", None, True),
    (None, None, None, False),
])
def test_in_philippines(location, country, workplace, expected):
    listing = ProviderListing(external_id="1", title="t", company="c", apply_url="https://x",
                              location=location, country=country, workplace_type=workplace)
    assert in_philippines(listing) is expected


@pytest.fixture()
def production_like(production_providers):
    return production_providers


def gh(job_id, title, location):
    return {"id": job_id, "title": title, "absolute_url": f"https://job-boards.greenhouse.io/xendit/jobs/{job_id}",
            "location": {"name": location}, "company_name": "Xendit", "first_published": "2026-09-11T06:36:48-04:00",
            "content": "&lt;p&gt;Requirements&lt;/p&gt;&lt;ul&gt;&lt;li&gt;SQL&lt;/li&gt;&lt;/ul&gt;", "departments": []}


def test_refresh_filters_non_philippine_postings(db, production_like, monkeypatch):
    monkeypatch.setattr(production_like, "greenhouse_boards_raw", "xendit")
    body = {"jobs": [gh(1, "FinOps Recons Associate", "Jakarta, Indonesia; Manila, Philippines"),
                     gh(2, "Account Executive", "Remote, France")]}
    t = transport({"https://boards-api.greenhouse.io/v1/boards/xendit/jobs": httpx.Response(200, json=body)})
    [item] = job_service.refresh_jobs(db, production_like, transport=t)
    assert item.fetched == 1 and item.filtered_out == 1
    assert [j.external_id for j in db.scalars(select(JobListing))] == ["1"]
    monkeypatch.setattr(production_like, "job_location_filter", "none")
    [item] = job_service.refresh_jobs(db, production_like, force=True, transport=t)
    assert item.fetched == 2 and item.filtered_out == 0


def test_provider_minimum_interval_is_respected_even_when_forced(db, production_like, monkeypatch):
    monkeypatch.setattr(production_like, "remotive_enabled", True)
    calls: list[httpx.Request] = []
    t = transport({"https://remotive.com/api/remote-jobs": httpx.Response(
        200, json={"job-count": 1, "jobs": [remotive_job()]})}, calls)
    assert job_service.refresh_jobs(db, production_like, transport=t)[0].status == "ok"
    second = job_service.refresh_jobs(db, production_like, force=True, transport=t)[0]
    assert second.status == "skipped_cooldown" and "360" in second.message
    assert len(calls) == 1


def test_aggregator_copy_of_employer_posting_is_hidden(db, production_like, monkeypatch):
    monkeypatch.setattr(production_like, "greenhouse_boards_raw", "xendit")
    monkeypatch.setattr(production_like, "jsearch_api_key", "k")
    monkeypatch.setattr(production_like, "jsearch_queries_raw", "fintech jobs in Philippines")
    copy = jsearch_job("j1", "LinkedIn", job_title="FinOps Recons Associate", employer_name="Xendit",
                       job_location="Jakarta, Indonesia; Manila, Philippines", job_description="Different wording.")
    t = transport({
        "https://boards-api.greenhouse.io/v1/boards/xendit/jobs": httpx.Response(
            200, json={"jobs": [gh(1, "FinOps Recons Associate", "Jakarta, Indonesia; Manila, Philippines")]}),
        "https://jsearch.p.rapidapi.com/search": httpx.Response(200, json={"status": "OK", "data": [copy, jsearch_job("j2")]}),
    })
    job_service.refresh_jobs(db, production_like, transport=t)
    jobs = {j.provider + ":" + j.external_id: j for j in db.scalars(select(JobListing))}
    assert jobs["greenhouse:1"].duplicate_of_id is None
    assert jobs["jsearch:j1"].duplicate_of_id == jobs["greenhouse:1"].id
    assert jobs["jsearch:j2"].duplicate_of_id is None
    assert jobs["jsearch:j2"].source_platform == "LinkedIn"


def test_same_url_on_two_sources_is_one_listing(db, production_like, monkeypatch):
    monkeypatch.setattr(production_like, "jsearch_api_key", "k")
    monkeypatch.setattr(production_like, "jsearch_queries_raw", "a;b")
    same = jsearch_job("x", job_apply_link="https://www.linkedin.com/jobs/view/42/")
    again = jsearch_job("y", job_apply_link="https://linkedin.com/jobs/view/42", job_title="Data Analyst II")
    t = transport({"https://jsearch.p.rapidapi.com/search": httpx.Response(200, json={"status": "OK", "data": [same, again]})})
    job_service.refresh_jobs(db, production_like, transport=t)
    visible = [j for j in db.scalars(select(JobListing)) if j.duplicate_of_id is None]
    assert len(visible) == 1


# ------------------------------------------------------------------- migration


def test_migration_purges_stored_demo_data(tmp_path):
    db_path = tmp_path / "legacy.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path}", "APP_ENV": "test"}

    def alembic(*args):
        subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND, env=env, check=True, capture_output=True)

    alembic("upgrade", "0001")
    con = sqlite3.connect(db_path)
    now = "2026-10-01 00:00:00"
    con.execute("INSERT INTO users (id, email, password_hash, is_active, created_at, updated_at) "
                "VALUES ('u1', 'a@example.com', 'x', 1, ?, ?)", (now, now))
    for sid, provider, demo in (("s1", "demo", 1), ("s2", "lever", 0)):
        con.execute("INSERT INTO job_sources (id, provider, identifier, display_name, is_demo, enabled, last_status, "
                    "created_at, updated_at) VALUES (?, ?, ?, ?, ?, 1, 'ok', ?, ?)", (sid, provider, provider, provider, demo, now, now))
    for jid, sid, demo in (("j1", "s1", 1), ("j2", "s2", 0)):
        con.execute(
            "INSERT INTO job_listings (id, source_id, provider, external_id, title, company, description, "
            "required_qualifications, preferred_qualifications, work_arrangement, employment_type, experience_level, "
            "apply_url, last_checked_at, status, content_fingerprint, is_demo, created_at, updated_at) "
            "VALUES (?, ?, 'x', ?, 't', 'c', '', '[]', '[]', 'unknown', 'unknown', 'unknown', 'https://x', ?, 'active', ?, ?, ?, ?)",
            (jid, sid, jid, now, jid, demo, now, now))
        con.execute("INSERT INTO saved_jobs (id, user_id, job_id, created_at) VALUES (?, 'u1', ?, ?)",
                    ("sv" + jid, jid, now))
    con.commit()
    con.close()

    alembic("upgrade", "head")
    con = sqlite3.connect(db_path)
    assert [r[0] for r in con.execute("SELECT id FROM job_listings")] == ["j2"]
    assert [r[0] for r in con.execute("SELECT id FROM job_sources")] == ["s2"]
    assert [r[0] for r in con.execute("SELECT job_id FROM saved_jobs")] == ["j2"]
    cols = {r[1] for r in con.execute("PRAGMA table_info(job_listings)")}
    assert {"posting_url", "source_platform"} <= cols
    con.close()


def test_source_entries_accept_display_names():
    from app.integrations.jobs.registry import parse_entries

    assert parse_entries(["coins:Coins.ph", "ninjavan: Ninja Van ", "tala", "bad id:x", ""]) == [
        ("coins", "Coins.ph"), ("ninjavan", "Ninja Van"), ("tala", "Tala"),
    ]


def test_lever_company_uses_configured_display_name(monkeypatch, production_providers):
    from app.integrations.jobs import registry

    monkeypatch.setattr(production_providers, "lever_sites_raw", "coins:Coins.ph")
    [lever] = [p for p in registry.build_providers(production_providers) if p.provider == "lever"]
    assert lever.identifier == "coins" and lever.display_name == "Coins.ph"
    assert registry.configured_sources(production_providers)["lever"] == ["coins"]


def test_transient_failures_are_retried_once():
    from app.integrations.jobs.greenhouse import GreenhouseProvider

    calls = {"n": 0}

    def flaky(request):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ReadTimeout("slow", request=request)
        return httpx.Response(200, json={"jobs": []})

    assert GreenhouseProvider("acme", transport=httpx.MockTransport(flaky)).fetch().listings == []
    assert calls["n"] == 2

    calls["n"] = 0

    def down(request):
        calls["n"] += 1
        return httpx.Response(503)

    with pytest.raises(ProviderError, match="HTTP 503"):
        GreenhouseProvider("acme", transport=httpx.MockTransport(down)).fetch()
    assert calls["n"] == 2  # one retry, then give up

    calls["n"] = 0

    def limited(request):
        calls["n"] += 1
        return httpx.Response(429)

    with pytest.raises(ProviderError):
        GreenhouseProvider("acme", transport=httpx.MockTransport(limited)).fetch()
    assert calls["n"] == 1  # rate limits are never retried
