"""JSearch (OpenWeb Ninja) job-search API provider — requires an API key.

Product page: https://www.openwebninja.com/api/jsearch
Marketplace:  https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch

JSearch is a commercial aggregator of Google for Jobs. Its results include
postings published on LinkedIn, Indeed, Glassdoor, JobStreet and employer
sites, each tagged with its ``job_publisher``. This is the authorised way for
CareerMatch to show those boards' listings: LinkedIn, JobStreet (SEEK) and
Glassdoor offer no public read API, Indeed retired its Publisher API, and
their terms forbid scraping.

* ``GET https://jsearch.p.rapidapi.com/search?query=…&page=1&num_pages=1&country=ph&date_posted=month``
* Headers ``X-RapidAPI-Key`` (from ``JSEARCH_API_KEY``) and ``X-RapidAPI-Host``.
* Each request counts against the plan quota (the free plan is 200 requests a
  month), so queries are few, pages are capped and the provider refreshes at
  most every ``JSEARCH_MIN_INTERVAL_MINUTES``.
* Salary fields are often ``null``; they are stored only when present.

The key never leaves the backend: it is read from the environment, sent only
in the request header and never logged or returned by the API.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ValidationError

from app.integrations.jobs.base import (
    FetchResult,
    HttpJobProvider,
    ProviderListing,
    ProviderSchemaError,
    https_url,
    parse_iso,
)

RAPIDAPI_HOST = "jsearch.p.rapidapi.com"
URL = f"https://{RAPIDAPI_HOST}/search"

_EMPLOYMENT = {
    "FULLTIME": "Full-time",
    "PARTTIME": "Part-time",
    "CONTRACTOR": "Contract",
    "INTERN": "Internship",
    "TEMPORARY": "Temporary",
}
_PERIOD = {
    "HOUR": "per-hour-wage",
    "DAY": "per-day-wage",
    "WEEK": "per-week-salary",
    "MONTH": "per-month-salary",
    "YEAR": "per-year-salary",
}


class _Highlights(BaseModel):
    Qualifications: list[str] = []
    Responsibilities: list[str] = []
    Benefits: list[str] = []


class _JSearchJob(BaseModel):
    job_id: str
    job_title: str
    employer_name: str
    job_apply_link: str
    job_publisher: str | None = None
    job_google_link: str | None = None
    job_description: str | None = None
    job_employment_type: str | None = None
    job_is_remote: bool | None = None
    job_posted_at_datetime_utc: str | None = None
    job_location: str | None = None
    job_city: str | None = None
    job_state: str | None = None
    job_country: str | None = None
    job_min_salary: float | int | None = None
    job_max_salary: float | int | None = None
    job_salary_currency: str | None = None
    job_salary_period: str | None = None
    job_offer_expiration_datetime_utc: str | None = None
    job_highlights: _Highlights | None = None


def _decimal(value: float | int | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


class JSearchProvider(HttpJobProvider):
    provider = "jsearch"
    platform = "JSearch"
    is_aggregator = True

    def __init__(
        self,
        *args,
        api_key: str,
        queries: list[str],
        country: str = "ph",
        date_posted: str = "month",
        pages: int = 1,
        min_interval_minutes: int = 720,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._api_key = api_key
        self.queries = queries
        self.country = country
        self.date_posted = date_posted
        self.pages = pages
        self.min_interval_minutes = min_interval_minutes

    def __repr__(self) -> str:  # never include the key
        return f"JSearchProvider(queries={len(self.queries)}, country={self.country!r})"

    def fetch(self) -> FetchResult:
        headers = {"X-RapidAPI-Key": self._api_key, "X-RapidAPI-Host": RAPIDAPI_HOST}
        listings: list[ProviderListing] = []
        skipped = 0
        for query in self.queries:
            payload = self._get_json(
                URL,
                params={
                    "query": query,
                    "page": 1,
                    "num_pages": self.pages,
                    "country": self.country,
                    "date_posted": self.date_posted,
                },
                headers=headers,
            )
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise ProviderSchemaError("Unexpected JSearch response shape (missing 'data' list)")
            for raw in payload["data"]:
                try:
                    job = _JSearchJob.model_validate(raw)
                except ValidationError:
                    skipped += 1
                    continue
                apply_url = https_url(job.job_apply_link)
                if not apply_url:
                    skipped += 1
                    continue
                listings.append(self._to_listing(job, apply_url))
        return FetchResult(listings=listings, skipped_invalid=skipped)

    def _to_listing(self, j: _JSearchJob, apply_url: str) -> ProviderListing:
        sections: list[tuple[str, list[str]]] = []
        if j.job_highlights:
            if j.job_highlights.Qualifications:
                sections.append(("Qualifications", j.job_highlights.Qualifications))
            if j.job_highlights.Responsibilities:
                sections.append(("Responsibilities", j.job_highlights.Responsibilities))
        location = j.job_location or ", ".join(p for p in (j.job_city, j.job_state, j.job_country) if p) or None
        has_salary = j.job_min_salary is not None or j.job_max_salary is not None
        return ProviderListing(
            external_id=j.job_id[:120],
            title=j.job_title.strip(),
            company=j.employer_name.strip(),
            apply_url=apply_url,
            posting_url=apply_url,
            source_platform=(j.job_publisher or "").strip() or None,
            content_text=j.job_description or "",
            sections=sections,
            location=location,
            country=j.job_country,
            workplace_type="remote" if j.job_is_remote else None,
            commitment=_EMPLOYMENT.get((j.job_employment_type or "").upper().replace("-", "").replace(" ", "")),
            salary_min=_decimal(j.job_min_salary),
            salary_max=_decimal(j.job_max_salary),
            salary_currency=j.job_salary_currency if has_salary else None,
            salary_interval=_PERIOD.get((j.job_salary_period or "").upper()) if has_salary else None,
            posted_at=parse_iso(j.job_posted_at_datetime_utc),
            deadline=parse_iso(j.job_offer_expiration_datetime_utc),
        )
