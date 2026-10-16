"""Job ingestion (refresh, normalise, deduplicate, expire) and querying."""

from __future__ import annotations

import logging
import re
import threading
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.core.errors import AppError, not_found
from app.db.base import utcnow
from app.integrations.jobs import registry
from app.integrations.jobs.base import JobProvider, ProviderError, ProviderListing, ProviderRateLimited
from app.integrations.jobs.location import passes_filter
from app.integrations.jobs.registry import KNOWN_PROVIDERS
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
# Provider keys whose listings are re-published copies (lose ties when deduplicating).
_AGGREGATORS = frozenset({"jsearch"})
_refresh_lock = threading.Lock()
_sources_lock = threading.Lock()

UNSUPPORTED_NOTE = (
    "LinkedIn, JobStreet, Indeed, Glassdoor and Kalibrr are not contacted directly: none offers an authorised public "
    "API for reading listings, and their terms forbid scraping. Their postings can be included through the JSearch "
    "aggregator when a JSEARCH_API_KEY is configured. Every listing links to its original posting."
)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------


def sync_sources(db: Session, providers: list[JobProvider]) -> dict[tuple[str, str], JobSource]:
    """Create/enable rows for configured providers and disable the rest.

    Safe under concurrent requests: a process-local lock serialises callers in
    one API process, and a savepoint absorbs the unique-constraint race when
    several processes create the same source at once.
    """
    with _sources_lock:
        return _sync_sources(db, providers)


def _sync_sources(db: Session, providers: list[JobProvider]) -> dict[tuple[str, str], JobSource]:
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
                is_demo=False,
            )
            try:
                with db.begin_nested():
                    db.add(source)
                    db.flush()
            except IntegrityError:
                source = db.scalar(
                    select(JobSource).where(JobSource.provider == provider.provider, JobSource.identifier == provider.identifier)
                )
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
    sync_sources(db, registry.build_providers(settings))
    db.commit()
    counts = dict(
        db.execute(
            select(JobListing.source_id, func.count(JobListing.id))
            .where(JobListing.status == "active", JobListing.duplicate_of_id.is_(None), JobListing.is_demo.is_(False))
            .group_by(JobListing.source_id)
        ).all()
    )
    sources = []
    for source in db.scalars(select(JobSource).where(JobSource.enabled.is_(True)).order_by(JobSource.provider)):
        out = JobSourceOut.model_validate(source)
        out.active_listings = counts.get(source.id, 0)
        sources.append(out)
    configured = registry.configured_sources(settings)
    providers = [
        ProviderStatus(
            provider=key,
            name=info["name"],
            configured=bool(configured[key]),
            sources=configured[key],
            docs=info["docs"],
            notes=info["notes"],
            access=info["access"],
            config_variable=info["config"],
        )
        for key, info in KNOWN_PROVIDERS.items()
    ]
    last_ok = max((_aware(s.last_fetched_at) for s in sources if s.last_fetched_at), default=None)
    return SourcesResponse(
        sources=sources,
        providers=providers,
        last_successful_refresh_at=last_ok,
        location_filter=settings.job_location_filter,
        unsupported_note=UNSUPPORTED_NOTE,
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
        "posting_url": (listing.posting_url or listing.apply_url)[:1000],
        "source_platform": (listing.source_platform or None) and listing.source_platform[:120],
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
                is_demo=False,
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


def _norm_key(*parts: str | None) -> str:
    return "|".join(re.sub(r"[^a-z0-9]+", " ", (p or "").lower()).strip() for p in parts)


def _norm_url(url: str | None) -> str:
    if not url:
        return ""
    parsed = urlsplit(url.strip())
    return f"{parsed.netloc.lower().removeprefix('www.')}{parsed.path.rstrip('/')}"


def _mark_duplicates(db: Session) -> int:
    """Hide repeated postings, keeping one canonical listing.

    Three keys identify the same posting: identical content fingerprint, the
    same original posting URL, or — across *different* sources — the same
    company, title and location (an aggregator re-publishing an employer's own
    posting). Employer boards win over aggregators; otherwise the oldest row wins.
    """
    rows = db.scalars(
        select(JobListing).where(JobListing.status == "active", JobListing.is_demo.is_(False))
    ).all()
    rows = sorted(rows, key=lambda j: (j.provider in _AGGREGATORS, _aware(j.created_at) or utcnow(), str(j.id)))
    by_fingerprint: dict[str, JobListing] = {}
    by_url: dict[str, JobListing] = {}
    by_title: dict[str, JobListing] = {}
    duplicates = 0
    for job in rows:
        url_key = _norm_url(job.posting_url or job.apply_url)
        title_key = _norm_key(job.company, job.title, job.location)
        first = by_fingerprint.get(job.content_fingerprint) or (url_key and by_url.get(url_key))
        if first is None:
            candidate = by_title.get(title_key)
            if candidate is not None and candidate.source_id != job.source_id:
                first = candidate
        if first is None:
            job.duplicate_of_id = None
            by_fingerprint[job.content_fingerprint] = job
            if url_key:
                by_url[url_key] = job
            by_title.setdefault(title_key, job)
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
        providers = registry.build_providers(settings, transport=transport)
        sources = sync_sources(db, providers)
        now = utcnow()
        results: list[RefreshItem] = []
        for provider in providers:
            source = sources[(provider.provider, provider.identifier)]
            last = _aware(source.last_fetched_at)
            # The provider's own minimum interval (its usage terms) always applies;
            # the general cooldown can be bypassed with force.
            cooldown = max(provider.min_interval_minutes, 0 if force else settings.refresh_cooldown_minutes)
            if cooldown and last and now - last < timedelta(minutes=cooldown):
                results.append(
                    RefreshItem(
                        provider=source.provider,
                        identifier=source.identifier,
                        status="skipped_cooldown",
                        message=f"Checked less than {cooldown} minutes ago",
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
            listings = fetched.listings
            filtered_out = 0
            if provider.needs_location_filter:
                listings = [x for x in fetched.listings if passes_filter(x, settings.job_location_filter)]
                filtered_out = len(fetched.listings) - len(listings)
            item = _ingest(db, source, listings, now)
            item.skipped_invalid = fetched.skipped_invalid
            item.filtered_out = filtered_out
            logger.info(
                "Provider %s/%s ok: fetched=%d kept=%d new=%d closed=%d",
                source.provider, source.identifier, len(fetched.listings), len(listings), item.created, item.expired,
            )
            source.last_fetched_at = now
            source.last_status = "ok"
            source.last_error = None
            source.last_fetch_count = len(listings)
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
    provider_platform = KNOWN_PROVIDERS.get(job.provider, {}).get("name", job.provider)
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
        posting_url=job.posting_url or job.apply_url,
        last_checked_at=job.last_checked_at,
        freshness=freshness(job.last_checked_at),
        status=job.status,
        provider=job.provider,
        provider_name=provider_platform,
        source_name=job.source.display_name if job.source else job.provider,
        source_platform=job.source_platform or provider_platform,
        is_saved=job.id in saved,
        required_skills=[s.skill for s in job.skills if s.requirement == "required"][:10],
    )


def to_detail(job: JobListing, saved: set[uuid.UUID]) -> JobDetailOut:
    summary = to_summary(job, saved)
    provider_name = summary.provider_name
    if job.provider in _AGGREGATORS and job.source_platform:
        attribution = (
            f"Published on {job.source_platform}; retrieved through the {provider_name}. "
            "Content is provided by the employer — check the original posting before applying."
        )
    else:
        source = job.source.display_name if job.source else job.provider
        attribution = f"Retrieved from the {provider_name} for '{source}'. Content is provided by the employer."
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
    stmt = repo.apply_filters(repo.visible_listings(), filters, user.id)
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
    if job is None or job.is_demo:
        raise not_found("Job")
    return to_detail(job, repo.saved_ids(db, user.id, [job.id]))


def facets(db: Session) -> FacetsOut:
    jobs = db.scalars(repo.visible_listings().options(selectinload(JobListing.skills), selectinload(JobListing.source))).all()
    categories = Counter(j.category or "Other" for j in jobs)
    locations = Counter((j.location or "Unspecified").split(",")[0].strip() for j in jobs)
    skills = Counter(s.skill for j in jobs for s in j.skills if s.requirement in {"required", "preferred"})
    platforms = Counter(j.source_platform or KNOWN_PROVIDERS.get(j.provider, {}).get("name", j.provider) for j in jobs)
    companies = Counter(j.company for j in jobs)
    last = max((_aware(j.last_checked_at) for j in jobs), default=None)
    return FacetsOut(
        total_active=len(jobs),
        with_salary=sum(1 for j in jobs if j.salary_min is not None or j.salary_max is not None or j.salary_text),
        categories=[FacetCount(value=k, count=v) for k, v in categories.most_common()],
        locations=[FacetCount(value=k, count=v) for k, v in locations.most_common(25)],
        skills=[FacetCount(value=k, count=v) for k, v in skills.most_common(40)],
        platforms=[FacetCount(value=k, count=v) for k, v in platforms.most_common()],
        companies=[FacetCount(value=k, count=v) for k, v in companies.most_common(40)],
        last_checked_at=last,
    )
