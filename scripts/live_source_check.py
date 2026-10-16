"""Live end-to-end check of every configured job source.

Runs the real backend code against the real provider APIs (network required)
and writes a report. Nothing here is mocked. Used by
``.github/workflows/live-sources.yml``; can also be run locally:

    cd backend
    DATABASE_URL=sqlite:///./live.db alembic upgrade head
    DATABASE_URL=sqlite:///./live.db python ../scripts/live_source_check.py --out ../live-report

Checks:
1. Refresh every configured source; record fetched / kept / filtered / errors.
2. Per source: active listings, field completeness, sample listings.
3. Data integrity: https links only, no demo or example.com rows, no visible duplicates.
4. Original-posting links answer (sampled, a few per source, polite).
5. A second refresh respects cooldowns and keeps listings active.
6. Failure paths: unknown board (404), timeout, a board with zero PH results.
7. API: list, search, company / source / salary filters, facets, sources.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ.setdefault("AUTO_REFRESH_MINUTES", "0")

import httpx  # noqa: E402
from sqlalchemy import func, select  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.integrations.jobs.base import ProviderError  # noqa: E402
from app.integrations.jobs.greenhouse import GreenhouseProvider  # noqa: E402
from app.integrations.jobs.lever import LeverProvider  # noqa: E402
from app.models import JobListing, JobSource  # noqa: E402
from app.repositories import job_repository as repo  # noqa: E402
from app.services import job_service  # noqa: E402

LINKS_PER_SOURCE = 2


def _iso(dt):
    return dt.isoformat() if dt else None


def refresh(settings, force: bool) -> list[dict]:
    with SessionLocal() as db:
        return [r.model_dump() for r in job_service.refresh_jobs(db, settings, force=force)]


def per_source_summary() -> dict:
    out: dict = {}
    with SessionLocal() as db:
        visible = db.scalars(repo.visible_listings()).all()
        by_source = defaultdict(list)
        for job in visible:
            by_source[job.source_id].append(job)
        for source in db.scalars(select(JobSource).where(JobSource.enabled.is_(True)).order_by(JobSource.provider)):
            jobs = by_source.get(source.id, [])
            n = len(jobs) or 1
            out[f"{source.provider}/{source.identifier}"] = {
                "status": source.last_status,
                "error": source.last_error,
                "last_fetched_at": _iso(source.last_fetched_at),
                "active_visible": len(jobs),
                "completeness": {
                    "location": round(sum(bool(j.location) for j in jobs) / n, 3),
                    "salary": round(sum(j.salary_min is not None or j.salary_max is not None or bool(j.salary_text) for j in jobs) / n, 3),
                    "posted_at": round(sum(j.posted_at is not None for j in jobs) / n, 3),
                    "description": round(sum(len(j.description or "") > 200 for j in jobs) / n, 3),
                    "employment_type_known": round(sum(j.employment_type != "unknown" for j in jobs) / n, 3),
                    "required_skills": round(sum(any(s.requirement == "required" for s in j.skills) for j in jobs) / n, 3),
                },
                "platforms": dict(Counter(j.source_platform for j in jobs)),
                "samples": [
                    {
                        "title": j.title,
                        "company": j.company,
                        "location": j.location,
                        "employment_type": j.employment_type,
                        "work_arrangement": j.work_arrangement,
                        "salary": [str(j.salary_min) if j.salary_min is not None else None,
                                   str(j.salary_max) if j.salary_max is not None else None, j.salary_currency, j.salary_text],
                        "posted_at": _iso(j.posted_at),
                        "source_platform": j.source_platform,
                        "posting_url": j.posting_url,
                        "apply_url": j.apply_url,
                        "required_skills": [s.skill for s in j.skills if s.requirement == "required"][:6],
                    }
                    for j in sorted(jobs, key=lambda x: x.posted_at or x.last_checked_at, reverse=True)[:3]
                ],
            }
    return out


def integrity() -> dict:
    with SessionLocal() as db:
        all_rows = db.scalars(select(JobListing)).all()
        visible = db.scalars(repo.visible_listings()).all()
        fingerprints = Counter(j.content_fingerprint for j in visible)
        return {
            "stored_rows": len(all_rows),
            "visible_active": len(visible),
            "hidden_duplicates": db.scalar(select(func.count(JobListing.id)).where(JobListing.duplicate_of_id.is_not(None))),
            "expired": sum(j.status == "expired" for j in all_rows),
            "demo_rows": sum(j.is_demo for j in all_rows),
            "example_com_links": sum("example.com" in (j.apply_url + (j.posting_url or "")) for j in all_rows),
            "non_https_links": sum(not j.apply_url.startswith("https://") for j in all_rows),
            "visible_duplicate_fingerprints": sum(c - 1 for c in fingerprints.values() if c > 1),
        }


def link_check() -> list[dict]:
    results = []
    with SessionLocal() as db:
        visible = db.scalars(repo.visible_listings()).all()
    picked: dict = defaultdict(list)
    for job in visible:
        if len(picked[job.source_id]) < LINKS_PER_SOURCE:
            picked[job.source_id].append(job)
    headers = {"User-Agent": "CareerMatchAI/0.1 (link check; respects provider terms)"}
    with httpx.Client(timeout=20, follow_redirects=True, headers=headers) as client:
        for jobs in picked.values():
            for job in jobs:
                try:
                    r = client.get(job.posting_url or job.apply_url)
                    status = r.status_code
                except httpx.HTTPError as exc:
                    status = f"error: {type(exc).__name__}"
                results.append({"provider": job.provider, "url": job.posting_url, "status": status})
                time.sleep(1)  # be polite
    return results


def failure_paths() -> dict:
    out = {}
    try:
        GreenhouseProvider("this-board-does-not-exist-cm", timeout=15).fetch()
        out["unknown_board"] = "no error (unexpected)"
    except ProviderError as exc:
        out["unknown_board"] = exc.message
    try:
        LeverProvider("coins", timeout=0.001).fetch()
        out["timeout"] = "no error (unexpected)"
    except ProviderError as exc:
        out["timeout"] = exc.message
    # A real board with no Philippine postings: fetched but nothing kept.
    try:
        listings = GreenhouseProvider("dropbox", timeout=15).fetch().listings
        from app.integrations.jobs.location import passes_filter

        out["zero_ph_results_board"] = {"fetched": len(listings), "kept": sum(passes_filter(x, "ph") for x in listings)}
    except ProviderError as exc:
        out["zero_ph_results_board"] = exc.message
    return out


def refresh_with_broken_source(settings) -> list[dict]:
    """Add an unknown board: it must fail alone while every other source keeps its listings.

    Not forced, so the working sources are skipped by their cooldown (no extra
    load on the providers) and only the new, broken source is contacted.
    """
    original = settings.greenhouse_boards_raw
    settings.greenhouse_boards_raw = f"{original},this-board-does-not-exist-cm"
    try:
        results = refresh(settings, force=False)
    finally:
        settings.greenhouse_boards_raw = original
        with SessionLocal() as db:  # sync back to the normal configuration
            from app.integrations.jobs import registry

            job_service.sync_sources(db, registry.build_providers(settings))
            db.commit()
    return results


def api_checks() -> dict:
    from fastapi.testclient import TestClient

    from app.main import create_app

    out = {}
    with TestClient(create_app()) as c:
        token = c.post("/api/v1/auth/register", json={"email": f"live-check-{int(time.time())}@example.org",
                                                      "password": "live-check-pass-1!"}).json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        facets = c.get("/api/v1/jobs/facets", headers=h).json()
        out["facets"] = {k: facets[k] for k in ("total_active", "with_salary", "last_checked_at")}
        out["facets"]["platforms"] = facets["platforms"]
        out["facets"]["top_locations"] = facets["locations"][:8]
        listing = c.get("/api/v1/jobs", headers=h, params={"page_size": 5}).json()
        out["list_total"] = listing["total"]
        out["list_first"] = [{k: i[k] for k in ("title", "company", "source_platform", "posting_url")} for i in listing["items"][:3]]
        out["search_engineer"] = c.post("/api/v1/jobs/search", headers=h, json={"q": "engineer"}).json()["total"]
        out["filter_company_grab"] = c.get("/api/v1/jobs", headers=h, params={"company": "grab"}).json()["total"]
        out["filter_platform_lever"] = c.get("/api/v1/jobs", headers=h, params={"platforms": "Lever"}).json()["total"]
        out["filter_platform_smartrecruiters"] = c.get("/api/v1/jobs", headers=h, params={"platforms": "SmartRecruiters"}).json()["total"]
        out["filter_has_salary"] = c.get("/api/v1/jobs", headers=h, params={"has_salary": "true"}).json()["total"]
        out["filter_remote"] = c.get("/api/v1/jobs", headers=h, params={"work_arrangements": "remote"}).json()["total"]
        out["filter_location_taguig"] = c.get("/api/v1/jobs", headers=h, params={"location": "taguig"}).json()["total"]
        first = listing["items"][0] if listing["items"] else None
        if first:
            detail = c.get(f"/api/v1/jobs/{first['id']}", headers=h).json()
            out["detail_sample"] = {k: detail[k] for k in ("title", "source_attribution", "posting_url", "apply_url")}
            out["detail_sample"]["skills"] = len(detail["skills"])
        sources = c.get("/api/v1/jobs/sources", headers=h).json()
        out["sources"] = [{k: s[k] for k in ("provider", "identifier", "last_status", "active_listings", "last_error")}
                          for s in sources["sources"]]
        out["providers_configured"] = {p["provider"]: p["configured"] for p in sources["providers"]}
    return out


def emit_annotations(report: dict, chunk: int = 3500) -> None:
    """Print the report as GitHub Actions notice annotations.

    Annotations are readable through the public checks API, so a read-only
    workflow can share its results without artifacts or write access.
    """
    # GitHub keeps at most 10 notices per step, so the report is gzipped and
    # base64-encoded first (≈4x smaller).
    compact = json.dumps(report, separators=(",", ":"), default=str)
    packed = base64.b64encode(gzip.compress(compact.encode("utf-8"), 9)).decode("ascii")
    parts = [packed[i:i + chunk] for i in range(0, len(packed), chunk)]
    if len(parts) > 10:
        print(f"::warning::Report too large for annotations ({len(parts)} parts); see the artifact")
    for n, part in enumerate(parts[:10], start=1):
        print(f"::notice title=live-report-gz {n}/{len(parts)}::{part}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--annotations", action="store_true", help="Also print the report as GitHub Actions notices")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    started = datetime.now(UTC)
    report: dict = {"started_at": started.isoformat(), "location_filter": settings.job_location_filter,
                    "jsearch_configured": settings.jsearch_configured}
    report["first_refresh"] = refresh(settings, force=True)
    report["sources"] = per_source_summary()
    report["integrity"] = integrity()
    report["second_refresh"] = refresh(settings, force=False)
    report["integrity_after_second_refresh"] = integrity()
    report["broken_source_refresh"] = refresh_with_broken_source(settings)
    report["integrity_after_broken_source"] = integrity()
    report["failure_paths"] = failure_paths()
    report["link_check"] = link_check()
    report["api"] = api_checks()
    report["finished_at"] = datetime.now(UTC).isoformat()
    (args.out / "report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    if args.annotations:
        emit_annotations(report)
    ok = [r for r in report["first_refresh"] if r["status"] == "ok"]
    print(f"{len(ok)}/{len(report['first_refresh'])} sources ok; "
          f"{report['integrity']['visible_active']} visible listings; demo rows: {report['integrity']['demo_rows']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
