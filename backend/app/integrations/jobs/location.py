"""Location filtering for providers that return postings from every country.

Greenhouse boards and Lever sites list every office a company hires in. For a
Philippines-focused deployment (``JOB_LOCATION_FILTER=ph``) a posting is kept
when the provider says it is in the Philippines, its location names a
Philippine place, or it is remote and open to Asia/APAC/worldwide applicants.
Postings the filter removes are not stored, so they never show up as listings.
"""

from __future__ import annotations

import re

from app.integrations.jobs.base import ProviderListing

_PH_PLACES = re.compile(
    r"\b(philippines|pilipinas|metro manila|manila|makati|taguig|bgc|bonifacio global city|pasig|ortigas|"
    r"quezon city|mandaluyong|pasay|paranaque|parañaque|muntinlupa|alabang|las pinas|las piñas|marikina|"
    r"caloocan|valenzuela|cebu|mandaue|lapu-lapu|davao|iloilo|bacolod|cagayan de oro|baguio|"
    r"clark freeport|pampanga|laguna|cavite|dasmarinas|dasmariñas|batangas|bulacan|"
    r"calabarzon|visayas|mindanao|luzon)\b",
    re.IGNORECASE,
)
_REMOTE = re.compile(r"\b(remote|anywhere|work from home|wfh)\b", re.IGNORECASE)
_OPEN_REGION = re.compile(r"\b(apac|asia|asia[- ]pacific|south[- ]?east asia|sea|worldwide|global|anywhere)\b", re.IGNORECASE)


def in_philippines(listing: ProviderListing) -> bool:
    if (listing.country or "").upper() == "PH":
        return True
    location = listing.location or ""
    if _PH_PLACES.search(location):
        return True
    remote = (listing.workplace_type or "").lower() == "remote" or bool(_REMOTE.search(location))
    return remote and bool(_OPEN_REGION.search(location))


def passes_filter(listing: ProviderListing, mode: str) -> bool:
    if mode == "none":
        return True
    if mode == "ph":
        return in_philippines(listing)
    return True
