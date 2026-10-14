"""Job ingestion (refresh, normalise, deduplicate, expire) and querying."""

from __future__ import annotations

import logging
import threading
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.errors import AppError, not_found
from app.db.base import utcnow
from app.integrations.jobs.base import JobProvider, ProviderError, ProviderListing, ProviderRateLimited
from app.integrations.jobs.registry import KNOWN_PROVIDERS, build_providers
from app.ml.job_parser import (
    classify_category,
    classify_employment_type,
    classify_experience_level,
    classify_work_arrangement,
    fingerprint,
    html_to_lines,
    parse_description,
    text_to_lines,
)
from app.models import JobListing, JobSkill, JobSource, SearchHistory, User
from app.repositories import job_repository as repo
from app.schemas.job import (
    FacetCount,
    FacetsOut,
    JobDetailOut,
    JobFilters,
    JobSkillOut,
    JobSourceOut,
    JobSummaryOut,
    ProviderStatus,
    RefreshItem,
    SourcesResponse,
)

logger = logging.getLogger(__name__)
_refresh_lock = threading.Lock()

UNSUPPORTED_NOTE = (
    "LinkedIn, JobStreet, Indeed and similar sites are not integrated: they do not offer an authorised public "
    "API for this use, and scraping them would violate their terms. Only the providers listed here are used."
)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------


def sync_sources(db: Session, providers: list[JobProvider]) -> dict[tuple[str, str], JobSource]:
    existing = {(s.provider, s.identifier): s for s in db.scalars(select(JobSource))}
    configured: dict[tuple[str, str], JobSource] = {}
    for provider in providers:
        key = (provider.provider, provider.identifier)
        source = existing.get(key)
        if source is None:
            source = JobSource(
                provider=provider.provider,
                identifier=provider.identifier,
                display_name=provider.display_name,
                is_demo=provider.is_demo,
            )
            db.add(source)
        source.enabled = True
        source.display_name = provider.display_name
        configured[key] = source
    for key, source in existing.items():
        if key not in configured:
            source.enabled = False  # no longer configured: hide its listings
    db.flush()
    return configured


def list_sources(db: Session, settings: Settings | None = None) -> SourcesResponse:
    settings = settings or get_settings()
    sync_sources(db, build_providers(settings))
    db.commit()
    counts = dict(
        db.execute(
            select(JobListing.source_id, func.count(JobListing.id))
            .where(JobListing.status == "active", JobListing.duplicate_of_id.is_(None))
            .group_by(JobListing.source_id)
        ).all()
    )
    sources = []
    for source in db.scalars(select(JobSource).where(JobSource.enabled.is_(True)).order_by(JobSource.provider)):
        out = JobSourceOut.model_validate(source)
        out.active_listings = counts.get(source.id, 0)
        sources.append(out)
    providers = []
    for key, info in KNOWN_PROVIDERS.items():
        configured = settings.greenhouse_boards if key == "greenhouse" else settings.lever_sites
        providers.append(
            ProviderStatus(
                provider=key,
                name=info["name"],
                configured=bool(configured),
                sources=configured,
                docs=info["docs"],
                notes=info["notes"],
                config_variable=info["config"],
            )
        )
    return SourcesResponse(
        sources=sources, providers=providers, demo_enabled=settings.enable_demo_provider, unsupported_note=UNSUPPORTED_NOTE
    )


# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------


def normalise(listing: ProviderListing) -> dict:
    if listing.content_html:
        lines = html_to_lines(listing.content_html)
    else:
        lines = text_to_lines(listing.content_text or "")
    parsed = parse_description(lines, listing.sections)
    full_text = parsed.description
    level, min_years = classify_experience_level(listing.title, full_text)
    employment = classify_employment_type(listing.commitment, listing.title, full_text)
    if employment == "unknown" and level == "internship":
        employment = "internship"
    if level == "unknown" and employment == "internship":
        level = "internship"
    return {
        "title": listing.title[:300],
        "company": listing.company[:200],
        "description": full_text,
        "required_qualifications": parsed.required_qualifications,
        "preferred_qualifications": parsed.preferred_qualifications,
        "location": (listing.location or None) and listing.location[:300],
        "country": (listing.country or None) and listing.country[:2].upper(),
        "work_arrangement": classify_work_arrangement(listing.workplace_type, listing.location, full_text),
        "employment_type": employment,
        "experience_level": level,
        "min_years_experience": min_years,
        "category": classify_category(listing.title, listing.department),
        "department": (listing.department or None) and listing.department[:200],
        "salary_min": listing.salary_min,
        "salary_max": listing.salary_max,
        "salary_currency": (listing.salary_currency or None) and listing.salary_currency[:3].upper(),
        "salary_interval": listing.salary_interval,
        "salary_text": (listing.salary_text or None) and listing.salary_text[:300],
        "posted_at": _aware(listing.posted_at),
        "deadline": _aware(listing.deadline),
        "apply_url": listing.apply_url[:1000],
        "content_fingerprint": fingerprint(listing.company, listing.title, listing.location, full_text),
        "_skills": parsed.skills,
    }


# --------------------------------------------------------------------------
# Refresh
# --------------------------------------------------------------------------


def _ingest(db: Session, source: JobSource, listings: list[ProviderListing], now: datetime) -> RefreshItem:
    item = RefreshItem(provider=source.provider, identifier=source.identifier, status="ok", fetched=len(listings))
    current = {j.external_id: j for j in db.scalars(select(JobListing).where(JobListing.source_id == source.id))}
    seen: set[str] = set()
    for listing in listings:
        if listing.external_id in seen:
            continue
        seen.add(listing.external_id)
        data = normalise(listing)
        skills = data.pop("_skills")
        job = current.get(listing.external_id)
        if job is None:
            job = JobListing(
                source_id=source.id,
                provider=source.provider,
                external_id=listing.external_id,
                is_demo=source.is_demo,
                last_checked_at=now,
                **data,
            )
            db.add(job)
            item.created += 1
        else:
            for key, value in data.items():
                setattr(job, key, value)
            job.status = "active"
            job.last_checked_at = now
            item.updated += 1
        job.skills = [
            JobSkill(skill=s.skill, category=s.category, requirement=s.requirement, evidence=s.evidence) for s in skills
        ]
        deadline = _aware(job.deadline)
        if deadline and deadline < now:
            job.status = "expired"
            item.expired += 1
    # Listings that disappeared from the provider are no longer open.
    for external_id, job in current.items():
        if external_id not in seen and job.status != "expired":
            job.status = "expired"
            job.last_checked_at = now
            item.expired += 1
    db.flush()
    return item


def _mark_duplicates(db: Session) -> int:
    rows = db.scalars(
        select(JobListing).where(JobListing.status == "active").order_by(JobListing.created_at, JobListing.id)
    ).all()
    canonical: dict[str, JobListing] = {}
    duplicates = 0
    for job in rows:
        first = canonical.get(job.content_fingerprint)
        if first is None:
            canonical[job.content_fingerprint] = job
            job.duplicate_of_id = None
        else:
            job.duplicate_of_id = first.id
            duplicates += 1
    db.flush()
    return duplicates


def refresh_jobs(
    db: Session,
    settings: Settings | None = None,
    *,
    force: bool = False,
    transport: httpx.BaseTransport | None = None,
) -> list[RefreshItem]:
    settings = settings or get_settings()
    if not _refresh_lock.acquire(blocking=False):
        raise AppError(409, "refresh_in_progress", "A refresh is already running. Please try again shortly.")
    try:
        providers = build_providers(settings, transport=transport)
        sources = sync_sources(db, providers)
        now = utcnow()
        results: list[RefreshItem] = []
        for provider in providers:
            source = sources[(provider.provider, provider.identifier)]
            last = _aware(source.last_fetched_at)
            if not force and last and now - last < timedelta(minutes=settings.refresh_cooldown_minutes):
                results.append(
                    RefreshItem(
                        provider=source.provider,
                        identifier=source.identifier,
                        status="skipped_cooldown",
                        message=f"Checked less than {settings.refresh_cooldown_minutes} minutes ago",
                    )
                )
                continue
            try:
                fetched = provider.fetch()
            except ProviderRateLimited as exc:
                source.last_status, source.last_error = "rate_limited", exc.message[:500]
                results.append(RefreshItem(provider=source.provider, identifier=source.identifier,
                                           status="rate_limited", message=exc.message))
                continue
            except ProviderError as exc:
                logger.warning("Provider %s/%s failed: %s", source.provider, source.identifier, exc.message)
                source.last_status, source.last_error = "error", exc.message[:500]
                results.append(RefreshItem(provider=source.provider, identifier=source.identifier,
                                           status="error", message=exc.message))
                continue
            item = _ingest(db, source, fetched.listings, now)
            item.skipped_invalid = fetched.skipped_invalid
            source.last_fetched_at = now
            source.last_status = "ok"
            source.last_error = None
            source.last_fetch_count = len(fetched.listings)
            results.append(item)
        duplicates = _mark_duplicates(db)
        if results:
            results[-1].duplicates = duplicates
        db.commit()
        return results
    finally:
        _refresh_lock.release()


def ensure_jobs_loaded(db: Session) -> None:
    """Load listings on first use so a fresh install is not empty."""
    if db.scalar(select(func.count(JobSource.id)).where(JobSource.last_fetched_at.is_not(None))) == 0:
        try:
            refresh_jobs(db)
        except AppError:
            pass


# --------------------------------------------------------------------------
# Presentation
# --------------------------------------------------------------------------


def freshness(last_checked: datetime, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    age = utcnow() - _aware(last_checked)
    if age <= timedelta(days=1):
        return "fresh"
    if age <= timedelta(days=settings.listing_stale_days):
        return "recent"
    return "stale"


def to_summary(job: JobListing, saved: set[uuid.UUID]) -> JobSummaryOut:
    return JobSummaryOut(
        id=job.id,
        title=job.title,
        company=job.company,
        location=job.location,
        work_arrangement=job.work_arrangement,
        employment_type=job.employment_type,
        experience_level=job.experience_level,
        category=job.category,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
        salary_interval=job.salary_interval,
        salary_text=job.salary_text,
        posted_at=job.posted_at,
        deadline=job.deadline,
        apply_url=job.apply_url,
        last_checked_at=job.last_checked_at,
        freshness=freshness(job.last_checked_at),
        status=job.status,
        provider=job.provider,
        source_name=job.source.display_name if job.source else job.provider,
        is_demo=job.is_demo,
        is_saved=job.id in saved,
        required_skills=[s.skill for s in job.skills if s.requirement == "required"][:10],
    )


def to_detail(job: JobListing, saved: set[uuid.UUID]) -> JobDetailOut:
    summary = to_summary(job, saved)
    provider_name = KNOWN_PROVIDERS.get(job.provider, {}).get("name", "Demo provider")
    attribution = (
        "DEMO DATA — fictional listing generated for demonstration; not a real vacancy."
        if job.is_demo
        else f"Retrieved from the {provider_name} for '{job.source.display_name}'. Content is provided by the employer."
    )
    return JobDetailOut(
        **summary.model_dump(),
        description=job.description,
        required_qualifications=job.required_qualifications,
        preferred_qualifications=job.preferred_qualifications,
        skills=[JobSkillOut.model_validate(s) for s in job.skills],
        min_years_experience=job.min_years_experience,
        department=job.department,
        country=job.country,
        source_attribution=attribution,
    )


def search(db: Session, user: User, filters: JobFilters, record_history: bool = False):
    settings = get_settings()
    stmt = repo.apply_filters(repo.visible_listings(), filters, user.id, settings.enable_demo_provider)
    rows, total = repo.paginate(db, repo.order(stmt, filters.sort), filters.page, filters.page_size)
    saved = repo.saved_ids(db, user.id, [j.id for j in rows])
    if record_history:
        query = filters.model_dump(mode="json", exclude={"page", "page_size"}, exclude_defaults=True)
        db.add(SearchHistory(user_id=user.id, kind="search", query=query, result_count=total))
        db.commit()
    return [to_summary(j, saved) for j in rows], total


def get_job(db: Session, user: User, job_id: uuid.UUID) -> JobDetailOut:
    job = db.scalar(
        select(JobListing)
        .options(selectinload(JobListing.skills), selectinload(JobListing.source))
        .where(JobListing.id == job_id)
    )
    if job is None or (job.is_demo and not get_settings().enable_demo_provider):
        raise not_found("Job")
    return to_detail(job, repo.saved_ids(db, user.id, [job.id]))


def facets(db: Session) -> FacetsOut:
    settings = get_settings()
    base = repo.visible_listings()
    if not settings.enable_demo_provider:
        base = base.where(JobListing.is_demo.is_(False))
    jobs = db.scalars(base.options(selectinload(JobListing.skills))).all()
    categories = Counter(j.category or "Other" for j in jobs)
    locations = Counter((j.location or "Unspecified").split(",")[0].strip() for j in jobs)
    skills = Counter(s.skill for j in jobs for s in j.skills if s.requirement in {"required", "preferred"})
    last = max((_aware(j.last_checked_at) for j in jobs), default=None)
    return FacetsOut(
        total_active=len(jobs),
        live_active=sum(1 for j in jobs if not j.is_demo),
        demo_active=sum(1 for j in jobs if j.is_demo),
        categories=[FacetCount(value=k, count=v) for k, v in categories.most_common()],
        locations=[FacetCount(value=k, count=v) for k, v in locations.most_common(25)],
        skills=[FacetCount(value=k, count=v) for k, v in skills.most_common(40)],
        last_checked_at=last,
    )
