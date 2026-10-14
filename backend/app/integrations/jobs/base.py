"""Provider abstraction for job sources.

A provider fetches postings from one configured endpoint (a Greenhouse board,
a Lever site, …) and returns ``ProviderListing`` objects. Normalisation,
skill extraction, deduplication and persistence are provider-independent, so
adding a source means implementing ``fetch`` only.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

import httpx

USER_AGENT = "CareerMatchAI/0.1 (job matching; respects provider terms)"


class ProviderError(Exception):
    """The provider could not be reached or returned an error."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ProviderRateLimited(ProviderError):
    def __init__(self, retry_after: int | None) -> None:
        super().__init__("The provider rate-limited the request" + (f"; retry after {retry_after}s" if retry_after else ""))
        self.retry_after = retry_after


class ProviderSchemaError(ProviderError):
    """The response did not have the documented shape."""


@dataclass
class ProviderListing:
    external_id: str
    title: str
    company: str
    apply_url: str
    content_html: str | None = None
    content_text: str | None = None
    sections: list[tuple[str, list[str]]] = field(default_factory=list)
    location: str | None = None
    country: str | None = None
    workplace_type: str | None = None
    commitment: str | None = None
    department: str | None = None
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    salary_currency: str | None = None
    salary_interval: str | None = None
    salary_text: str | None = None
    posted_at: datetime | None = None
    deadline: datetime | None = None


@dataclass
class FetchResult:
    listings: list[ProviderListing]
    skipped_invalid: int = 0


class JobProvider(ABC):
    provider: str = "base"
    is_demo: bool = False

    def __init__(self, identifier: str, display_name: str | None = None) -> None:
        self.identifier = identifier
        self.display_name = display_name or identifier

    @abstractmethod
    def fetch(self) -> FetchResult: ...


class HttpJobProvider(JobProvider):
    def __init__(
        self,
        identifier: str,
        display_name: str | None = None,
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        super().__init__(identifier, display_name)
        self.timeout = timeout
        self.transport = transport

    def _get_json(self, url: str, params: dict | None = None):
        try:
            with httpx.Client(
                timeout=self.timeout, transport=self.transport, headers={"User-Agent": USER_AGENT}
            ) as client:
                response = client.get(url, params=params)
        except httpx.TimeoutException:
            raise ProviderError("The provider did not respond in time") from None
        except httpx.HTTPError:
            raise ProviderError("The provider could not be reached") from None
        if response.status_code == 429:
            retry = response.headers.get("Retry-After")
            raise ProviderRateLimited(int(retry) if retry and retry.isdigit() else None)
        if response.status_code == 404:
            raise ProviderError(f"Source '{self.identifier}' was not found at the provider")
        if response.status_code >= 400:
            raise ProviderError(f"The provider returned HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError:
            raise ProviderSchemaError("The provider returned invalid JSON") from None


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
