"""SmartRecruiters Posting API provider.

Documentation: https://developers.smartrecruiters.com/docs/posting-api

* ``GET https://api.smartrecruiters.com/v1/companies/{company}/postings?country=ph&offset=N&limit=100``
  lists a company's public postings (no description).
* ``GET https://api.smartrecruiters.com/v1/companies/{company}/postings/{id}``
  returns one posting with its job ad sections, ``postingUrl`` and ``applyUrl``.
* Public data published by the employer for job distribution; no key needed.
* Per company. The ``country`` filter is applied by SmartRecruiters itself, so
  only postings in the configured country are returned.

Response shape verified against live postings (Grab, Sutherland, Delivery Hero)
on 2026-10-16.
"""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from app.integrations.jobs.base import (
    FetchResult,
    HttpJobProvider,
    ProviderError,
    ProviderListing,
    ProviderRateLimited,
    ProviderSchemaError,
    https_url,
    parse_iso,
)

BASE_URL = "https://api.smartrecruiters.com/v1/companies"
PAGE_SIZE = 100
MAX_PAGES = 10

# Display names for the ISO codes SmartRecruiters returns in lowercase.
_COUNTRY_NAMES = {"ph": "Philippines", "sg": "Singapore", "my": "Malaysia", "id": "Indonesia", "th": "Thailand", "vn": "Vietnam"}


class _Label(BaseModel):
    id: str | None = None
    label: str | None = None


class _Company(BaseModel):
    identifier: str | None = None
    name: str | None = None


class _Location(BaseModel):
    city: str | None = None
    region: str | None = None
    country: str | None = None
    remote: bool | None = None
    hybrid: bool | None = None
    fullLocation: str | None = None


class _Posting(BaseModel):
    id: str
    name: str
    company: _Company = _Company()
    releasedDate: str | None = None
    location: _Location = _Location()
    department: _Label | None = None
    function: _Label | None = None
    typeOfEmployment: _Label | None = None
    experienceLevel: _Label | None = None


class _Section(BaseModel):
    title: str | None = None
    text: str | None = None


class _JobAd(BaseModel):
    sections: dict[str, _Section] = {}


class _PostingDetail(_Posting):
    postingUrl: str | None = None
    applyUrl: str | None = None
    jobAd: _JobAd = _JobAd()


# Order of the job-ad sections in the stored description. The employer's
# general "company description" goes last so requirements are parsed first.
_SECTION_ORDER = ("jobDescription", "qualifications", "additionalInformation", "companyDescription")


def _location_text(loc: _Location) -> str | None:
    country = _COUNTRY_NAMES.get((loc.country or "").lower(), (loc.country or "").upper() or None)
    parts = [p.strip() for p in (loc.city, loc.region, country) if p and p.strip()]
    # Keep order, drop repeats ("Taguig, Taguig, Philippines").
    seen: list[str] = []
    for part in parts:
        if part.lower() not in (s.lower() for s in seen):
            seen.append(part)
    text = ", ".join(seen) or None
    if loc.remote and text:
        return f"Remote, {text}"
    return text


class SmartRecruitersProvider(HttpJobProvider):
    provider = "smartrecruiters"
    platform = "SmartRecruiters"

    def __init__(self, *args, country: str | None = "ph", max_details: int = 100, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.country = (country or "").lower() or None
        self.max_details = max_details

    def _detail(self, posting_id: str) -> _PostingDetail | None:
        try:
            raw = self._get_json(f"{BASE_URL}/{self.identifier}/postings/{posting_id}")
        except ProviderRateLimited:
            raise
        except ProviderError:
            return None  # listing is still real; it just has no description
        try:
            return _PostingDetail.model_validate(raw)
        except ValidationError:
            return None

    def fetch(self) -> FetchResult:
        postings: list[_Posting] = []
        skipped = 0
        params: dict = {"limit": PAGE_SIZE}
        if self.country:
            params["country"] = self.country
        for page in range(MAX_PAGES):
            payload = self._get_json(f"{BASE_URL}/{self.identifier}/postings", params={**params, "offset": page * PAGE_SIZE})
            if not isinstance(payload, dict) or not isinstance(payload.get("content"), list):
                raise ProviderSchemaError("Unexpected SmartRecruiters response shape (missing 'content' list)")
            for raw in payload["content"]:
                try:
                    postings.append(_Posting.model_validate(raw))
                except ValidationError:
                    skipped += 1
            total = payload.get("totalFound")
            if len(payload["content"]) < PAGE_SIZE or (isinstance(total, int) and len(postings) + skipped >= total):
                break

        listings: list[ProviderListing] = []
        for index, posting in enumerate(postings):
            detail = self._detail(posting.id) if index < self.max_details else None
            # Without the detail call there is no verified public URL, so the
            # documented public job page pattern is used.
            company_id = posting.company.identifier or self.identifier
            fallback_url = f"https://jobs.smartrecruiters.com/{company_id}/{posting.id}"
            posting_url = (detail and https_url(detail.postingUrl)) or fallback_url
            apply_url = (detail and https_url(detail.applyUrl)) or posting_url
            html = ""
            if detail:
                for key in _SECTION_ORDER:
                    section = detail.jobAd.sections.get(key)
                    if section and section.text:
                        html += f"<h3>{section.title or ''}</h3>{section.text}"
            loc = posting.location
            listings.append(
                ProviderListing(
                    external_id=posting.id,
                    title=posting.name.strip(),
                    company=(posting.company.name or self.display_name).strip(),
                    apply_url=apply_url,
                    posting_url=posting_url,
                    source_platform=self.platform,
                    content_html=html or None,
                    content_text=None if html else "",
                    location=_location_text(loc),
                    country=(loc.country or None) and loc.country.upper(),
                    workplace_type="remote" if loc.remote else "hybrid" if loc.hybrid else None,
                    commitment=posting.typeOfEmployment.label if posting.typeOfEmployment else None,
                    department=(posting.department and posting.department.label)
                    or (posting.function and posting.function.label)
                    or None,
                    posted_at=parse_iso(posting.releasedDate),
                )
            )
        return FetchResult(listings=listings, skipped_invalid=skipped)
