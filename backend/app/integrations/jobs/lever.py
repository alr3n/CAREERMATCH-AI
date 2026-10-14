"""Lever Postings API provider.

Documentation: https://github.com/lever/postings-api

* ``GET https://api.lever.co/v0/postings/{site}?mode=json&skip=N&limit=M``
  (EU accounts: ``https://api.eu.lever.co``)
* Public, published postings only; no key is needed to read them.
* Per company site — it cannot search all Lever customers, and it does not
  support full-text search.
* ``workplaceType``, ``categories.commitment`` and ``salaryRange`` are used
  when present; nothing is filled in when they are absent.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from pydantic import BaseModel, ValidationError

from app.integrations.jobs.base import FetchResult, HttpJobProvider, ProviderListing, ProviderSchemaError
from app.ml.job_parser import html_to_lines

BASE_URLS = {"global": "https://api.lever.co/v0/postings", "eu": "https://api.eu.lever.co/v0/postings"}
PAGE_SIZE = 100
MAX_PAGES = 20


class _Categories(BaseModel):
    location: str | None = None
    commitment: str | None = None
    team: str | None = None
    department: str | None = None


class _ListBlock(BaseModel):
    text: str = ""
    content: str = ""


class _Salary(BaseModel):
    currency: str | None = None
    interval: str | None = None
    min: float | int | None = None
    max: float | int | None = None


class _LeverPosting(BaseModel):
    id: str
    text: str
    hostedUrl: str
    applyUrl: str | None = None
    categories: _Categories = _Categories()
    country: str | None = None
    workplaceType: str | None = None
    description: str | None = None
    descriptionPlain: str | None = None
    lists: list[_ListBlock] = []
    additional: str | None = None
    salaryRange: _Salary | None = None
    salaryDescriptionPlain: str | None = None
    createdAt: int | None = None


def _decimal(value: float | int | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


class LeverProvider(HttpJobProvider):
    provider = "lever"

    def __init__(self, *args, region: str = "global", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.base_url = BASE_URLS.get(region, BASE_URLS["global"])

    def fetch(self) -> FetchResult:
        listings: list[ProviderListing] = []
        skipped = 0
        for page in range(MAX_PAGES):
            payload = self._get_json(
                f"{self.base_url}/{self.identifier}",
                params={"mode": "json", "skip": page * PAGE_SIZE, "limit": PAGE_SIZE},
            )
            if not isinstance(payload, list):
                raise ProviderSchemaError("Unexpected Lever response shape (expected a list of postings)")
            for raw in payload:
                try:
                    posting = _LeverPosting.model_validate(raw)
                except ValidationError:
                    skipped += 1
                    continue
                if not posting.hostedUrl.startswith("https://"):
                    skipped += 1
                    continue
                listings.append(self._to_listing(posting))
            if len(payload) < PAGE_SIZE:
                break
        return FetchResult(listings=listings, skipped_invalid=skipped)

    def _to_listing(self, p: _LeverPosting) -> ProviderListing:
        sections: list[tuple[str, list[str]]] = []
        for block in p.lists:
            items = [line.lstrip("• ").strip() for line, _ in html_to_lines(block.content)]
            if block.text and items:
                sections.append((block.text, items))
        content_html = (p.description or "") + (p.additional or "")
        salary = p.salaryRange
        return ProviderListing(
            external_id=p.id,
            title=p.text.strip(),
            company=self.display_name,
            apply_url=p.hostedUrl,
            content_html=content_html or None,
            content_text=None if content_html else (p.descriptionPlain or ""),
            sections=sections,
            location=p.categories.location,
            country=(p.country or None),
            workplace_type=p.workplaceType if p.workplaceType and p.workplaceType != "unspecified" else None,
            commitment=p.categories.commitment,
            department=p.categories.department or p.categories.team,
            salary_min=_decimal(salary.min) if salary else None,
            salary_max=_decimal(salary.max) if salary else None,
            salary_currency=(salary.currency or None) if salary else None,
            salary_interval=(salary.interval or None) if salary else None,
            salary_text=p.salaryDescriptionPlain or None,
            posted_at=datetime.fromtimestamp(p.createdAt / 1000, tz=UTC) if p.createdAt else None,
        )
