"""Remotive public remote-jobs API provider.

Documentation and terms: https://github.com/remotive-com/remote-jobs-api

* ``GET https://remotive.com/api/remote-jobs`` (optional ``category``).
* Public, no key. Remotive asks API users to fetch at most about four times a
  day (requests above two per minute may be blocked), to link back to the
  Remotive listing URL and to credit Remotive as the source. CareerMatch keeps
  the Remotive URL as both the posting and apply link and shows "Remotive" as
  the source on every listing.
* The public feed is delayed by 24 hours and covers remote roles worldwide.
  Only listings whose ``candidate_required_location`` admits applicants in the
  Philippines (worldwide, Asia/APAC, or the Philippines itself) are kept.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ValidationError

from app.integrations.jobs.base import FetchResult, HttpJobProvider, ProviderListing, ProviderSchemaError, https_url, parse_iso

URL = "https://remotive.com/api/remote-jobs"

_OPEN_TO_PH = re.compile(r"\b(worldwide|anywhere|global|philippines|asia|apac|south[- ]?east asia|sea)\b", re.IGNORECASE)

_JOB_TYPES = {
    "full_time": "Full-time",
    "part_time": "Part-time",
    "contract": "Contract",
    "freelance": "Contract",
    "internship": "Internship",
}


class _RemotiveJob(BaseModel):
    id: int | str
    url: str
    title: str
    company_name: str
    category: str | None = None
    job_type: str | None = None
    publication_date: str | None = None
    candidate_required_location: str | None = None
    salary: str | None = None
    description: str | None = None


def open_to_philippines(required_location: str | None) -> bool:
    return bool(required_location and _OPEN_TO_PH.search(required_location))


class RemotiveProvider(HttpJobProvider):
    provider = "remotive"
    platform = "Remotive"
    min_interval_minutes = 360  # at most ~4 fetches a day, per Remotive's guidance

    def __init__(self, *args, category: str | None = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.category = category or None

    def fetch(self) -> FetchResult:
        params = {"category": self.category} if self.category else None
        payload = self._get_json(URL, params=params)
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
            raise ProviderSchemaError("Unexpected Remotive response shape (missing 'jobs' list)")
        listings: list[ProviderListing] = []
        skipped = 0
        for raw in payload["jobs"]:
            try:
                job = _RemotiveJob.model_validate(raw)
            except ValidationError:
                skipped += 1
                continue
            url = https_url(job.url)
            if not url:
                skipped += 1
                continue
            if not open_to_philippines(job.candidate_required_location):
                continue  # not open to applicants in the Philippines
            listings.append(
                ProviderListing(
                    external_id=str(job.id),
                    title=job.title.strip(),
                    company=job.company_name.strip(),
                    apply_url=url,
                    posting_url=url,
                    source_platform=self.platform,
                    content_html=job.description or None,
                    content_text=None if job.description else "",
                    location=f"Remote ({job.candidate_required_location})",
                    workplace_type="remote",
                    commitment=_JOB_TYPES.get((job.job_type or "").lower()),
                    department=job.category,
                    salary_text=(job.salary or "").strip() or None,
                    posted_at=parse_iso(job.publication_date),
                )
            )
        return FetchResult(listings=listings, skipped_invalid=skipped)
