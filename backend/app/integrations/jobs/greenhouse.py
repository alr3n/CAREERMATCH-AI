"""Greenhouse Job Board API provider.

Documentation: https://developers.greenhouse.io/job-board.html

* ``GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true``
* Public data; GET endpoints need no authentication.
* One request returns every published job on that company's board — the API
  is per company, it cannot search all of Greenhouse.
* ``content`` is HTML-escaped HTML. ``updated_at`` is *not* the posting date,
  so it is never used as one; ``first_published`` / ``application_deadline``
  are used only when present.
"""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from app.integrations.jobs.base import (
    FetchResult,
    HttpJobProvider,
    ProviderListing,
    ProviderSchemaError,
    parse_iso,
)

BASE_URL = "https://boards-api.greenhouse.io/v1/boards"


class _Named(BaseModel):
    name: str | None = None


class _GreenhouseJob(BaseModel):
    id: int | str
    title: str
    absolute_url: str
    content: str | None = None
    location: _Named | None = None
    departments: list[_Named] = []
    company_name: str | None = None
    first_published: str | None = None
    application_deadline: str | None = None


class GreenhouseProvider(HttpJobProvider):
    provider = "greenhouse"

    def fetch(self) -> FetchResult:
        payload = self._get_json(f"{BASE_URL}/{self.identifier}/jobs", params={"content": "true"})
        if not isinstance(payload, dict) or not isinstance(payload.get("jobs"), list):
            raise ProviderSchemaError("Unexpected Greenhouse response shape (missing 'jobs' list)")
        listings: list[ProviderListing] = []
        skipped = 0
        for raw in payload["jobs"]:
            try:
                job = _GreenhouseJob.model_validate(raw)
            except ValidationError:
                skipped += 1
                continue
            if not job.absolute_url.startswith("https://"):
                skipped += 1
                continue
            listings.append(
                ProviderListing(
                    external_id=str(job.id),
                    title=job.title.strip(),
                    company=(job.company_name or self.display_name).strip(),
                    apply_url=job.absolute_url,
                    content_html=job.content or "",
                    location=job.location.name if job.location else None,
                    department=next((d.name for d in job.departments if d.name), None),
                    posted_at=parse_iso(job.first_published),
                    deadline=parse_iso(job.application_deadline),
                )
            )
        return FetchResult(listings=listings, skipped_invalid=skipped)
