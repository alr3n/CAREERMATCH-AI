# External integrations

## Job providers

All listings come from real, external sources. There is no demo or sample-data provider in the application: when no source is configured or every source is unavailable, the API returns no listings and the UI says *"No live job listings are currently available. Please try again later."* Fictional listings exist only as an offline fixture for the automated tests (`backend/tests/fixture_jobs.py`).

All providers implement `JobProvider.fetch()` (`backend/app/integrations/jobs/base.py`) and return `ProviderListing` objects. Normalisation, skill tagging, the location filter, deduplication, expiry and freshness tracking are shared (`services/job_service.py`). Fields a provider does not supply stay empty and are shown as "Not specified"; nothing is estimated.

### Can LinkedIn, JobStreet, Indeed, Glassdoor or Kalibrr be integrated directly?

No. Checked in October 2026:

| Site | Read/search API for third parties | Why it is not contacted directly |
|---|---|---|
| LinkedIn | None. Talent Solutions APIs are for approved ATS partners to *post* jobs and receive applications | Terms prohibit scraping; logged-in and anti-bot protections |
| JobStreet (SEEK) | None. The SEEK API (covers JobStreet PH) is for hirers and recruitment-software partners to post jobs | Same |
| Indeed | Publisher job-search API closed to new sign-ups in 2020 and retired in 2024 | Same |
| Glassdoor | Public API discontinued | Same |
| Kalibrr | No public API. Kalibrr syndicates its listings to Google for Jobs | Same |

The authorised route to these boards' postings is **JSearch**, a commercial Google for Jobs aggregator (below). Each JSearch listing is labelled with the platform it was published on, e.g. "LinkedIn via JSearch".

### Sources and verification status

"Live-verified" means the real backend code fetched real postings from the real API in the read-only *Live job sources* workflow (`.github/workflows/live-sources.yml`, script `scripts/live_source_check.py`) on 2026-10-16.

| Provider | Access | Default sources (PH openings at verification) | Status |
|---|---|---|---|
| Greenhouse Job Board API | Public, no key | Xendit (4) | Live-verified |
| Lever Postings API | Public, no key | Coins.ph (55), Lalamove (20), Ninja Van (13), Tala (2) | Live-verified |
| SmartRecruiters Posting API | Public, no key | Sutherland (85), Delivery Hero/foodpanda (40), Grab (17), Bosch (7), Canva (5), Home Credit (3) | Live-verified |
| Remotive Remote Jobs API | Public, no key; attribution and link-back required | Remote roles open to PH / APAC / worldwide (10) | Live-verified |
| JSearch (OpenWeb Ninja) | Paid API key (free plan: 200 requests/month) | Your own queries, e.g. `software developer in Philippines` | Implemented and unit-tested against the documented response shape; **not live-tested** (needs your key) |

Counts change daily. The default employers are a starting set; replace them with the companies you want to follow.

### Greenhouse Job Board API

- **Docs:** https://developers.greenhouse.io/job-board.html
- **Endpoint:** `GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true` — one request per company board, no key.
- **Fields used:** `id`, `title`, `absolute_url` (posting and apply link), `content`, `location.name`, `departments[].name`, `company_name`, `first_published`, `application_deadline`. `updated_at` is not treated as a posting date. Greenhouse has no employment-type or salary field, so these show "Not specified" unless stated in the text.
- **Location:** boards list every office worldwide, so the Philippines filter applies (multi-office strings such as "Jakarta, Indonesia; Manila, Philippines" are kept).
- **Configure:** `GREENHOUSE_BOARDS=xendit:Xendit,…` — the token is the last part of `https://boards.greenhouse.io/<token>`.

### Lever Postings API

- **Docs:** https://github.com/lever/postings-api
- **Endpoint:** `GET https://api.lever.co/v0/postings/{site}?mode=json&skip=N&limit=100` (EU: `api.eu.lever.co`).
- **Fields used:** `id`, `text`, `hostedUrl` (posting), `applyUrl`, `categories.{location, commitment, team, department}`, `country`, `workplaceType`, `description`, `lists[]`, `additional`, `salaryRange`, `salaryDescriptionPlain`, `createdAt`.
- **Company name:** Lever returns none, so give one per site: `LEVER_SITES=coins:Coins.ph,ninjavan:Ninja Van`.
- **Location:** Philippines filter applies.

### SmartRecruiters Posting API

- **Docs:** https://developers.smartrecruiters.com/docs/posting-api
- **Endpoints:** `GET https://api.smartrecruiters.com/v1/companies/{company}/postings?country=ph&offset=N&limit=100`, then `GET …/postings/{id}` for each posting's job ad, `postingUrl` and `applyUrl`.
- **Load:** one detail request per posting, capped by `SMARTRECRUITERS_MAX_DETAILS` (default 100 per company). Postings beyond the cap are stored without a description and link to the public job page.
- **Location:** filtered by SmartRecruiters itself through `SMARTRECRUITERS_COUNTRY` (default `ph`).
- **Configure:** `SMARTRECRUITERS_COMPANIES=Grab,DeliveryHero:Delivery Hero (foodpanda),…` — the identifier is the part after `jobs.smartrecruiters.com/`.
- **Note:** some employers keep long-running "evergreen" postings; their `releasedDate` can be years old (e.g. Home Credit, 2016). The date is shown as provided.

### Remotive Remote Jobs API

- **Docs and terms:** https://github.com/remotive-com/remote-jobs-api
- **Endpoint:** `GET https://remotive.com/api/remote-jobs` (optional `REMOTIVE_CATEGORY`).
- **Terms honoured:** at most about four fetches a day (the provider's 360-minute minimum interval is enforced even for forced refreshes); every listing names Remotive as its source and links to the Remotive URL. Remotive's public feed is delayed 24 hours.
- **Location:** only roles whose `candidate_required_location` admits the Philippines (worldwide, Asia/APAC, Philippines) are kept.
- **Configure:** `REMOTIVE_ENABLED=true|false`.

### JSearch (Google for Jobs aggregator) — needs a key

- **Product:** https://www.openwebninja.com/api/jsearch (also on RapidAPI: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
- **Endpoint:** `GET https://jsearch.p.rapidapi.com/search?query=…&page=1&num_pages=N&country=ph&date_posted=month` with headers `X-RapidAPI-Key` and `X-RapidAPI-Host`.
- **Fields used:** `job_id`, `job_title`, `employer_name`, `job_publisher` (shown as the source platform), `job_apply_link`, `job_description`, `job_highlights` (Qualifications, Responsibilities), `job_employment_type`, `job_is_remote`, `job_location`/`job_city`/`job_country`, `job_min_salary`/`job_max_salary`/`job_salary_currency`/`job_salary_period` (only when present), `job_posted_at_datetime_utc`, `job_offer_expiration_datetime_utc`.
- **Quota:** every query × page is one request. Defaults: 1 page per query, refresh at most every 720 minutes (`JSEARCH_MIN_INTERVAL_MINUTES`). With 3 queries that is about 180 requests a month, inside the free plan.
- **Duplicates:** when a JSearch result is the same posting as one from an employer board (same URL, or same company + title + location), the employer's own listing is kept and the JSearch copy is hidden.
- **Configure:** `JSEARCH_API_KEY=…` and `JSEARCH_QUERIES=software developer in Philippines;data analyst in Philippines` (semicolon-separated). The key stays on the server: it is read from the environment, sent only in the request header, never logged, and never returned by the API (`/jobs/sources` lists the queries, not the key).
- **Verification:** unit tests cover mapping, header-only key use, missing salary, auth errors without key leakage, and dedupe against employer boards. Run the *Live job sources* workflow with a `JSEARCH_API_KEY` repository secret to verify it live.

### Location filter

`JOB_LOCATION_FILTER=ph` (default) keeps postings from Greenhouse and Lever that are in the Philippines (country code, or a Philippine city or region in the location), or remote and open to Asia/APAC/worldwide applicants. `none` keeps everything. Filtered postings are not stored; refresh results report how many were filtered out.

### Refresh schedule and limits

| Mechanism | Default |
|---|---|
| Background refresh in the API process (`AUTO_REFRESH_MINUTES`; 0 = off, use cron with `python -m app.cli refresh-jobs`) | every 360 min |
| General per-source cooldown (`REFRESH_COOLDOWN_MINUTES`; bypassed by `--force`) | 10 min |
| Provider minimum interval (never bypassed) | Remotive 360 min, JSearch 720 min |
| Request timeout (`PROVIDER_TIMEOUT_SECONDS`) | 15 s, one retry on transient failure |

### Error handling

| Situation | Behaviour |
|---|---|
| Provider unreachable, timeout, HTTP 502/503/504 | Retried once after a short pause (never for 429 or other 4xx). If it still fails: source marked `error`. **Existing listings are kept** with their last-checked time; the UI shows "1 source is temporarily unavailable" with the reason |
| HTTP 401/403 | "The provider refused the request … check the API key or access" (the key is never echoed) |
| HTTP 429 | Source marked `rate_limited`; retried after the cooldown |
| HTTP 404 | "Source '…' was not found at the provider" (wrong board token, site or company) |
| Unexpected JSON shape | `ProviderSchemaError`, source marked `error` |
| Invalid items (missing fields, non-HTTPS URL) | Skipped and counted (`skipped_invalid`) |
| A real source with zero Philippine postings | Fetched, all filtered out, no listings created |
| Posting removed by the employer | Marked `expired` on the next successful refresh |
| Deadline passed | Marked `expired` |
| Same posting from two sources | One canonical listing; the other gets `duplicate_of_id` and is hidden |
| No source configured, or every source down | Empty list and an honest message. **Never fake listings** |

### Adding a provider

1. Create `integrations/jobs/<name>.py` with a class extending `HttpJobProvider` that implements `fetch()`, validates items with Pydantic, and maps them to `ProviderListing` (set `posting_url` and `source_platform`). Set `needs_location_filter`, `min_interval_minutes` and `is_aggregator` as appropriate.
2. Add configuration to `core/config.py` and `.env.example`, and register it in `registry.build_providers`, `configured_sources` and `KNOWN_PROVIDERS`.
3. Add tests with recorded-format responses via `httpx.MockTransport` (see `tests/test_live_providers.py`).
4. Verify it live with the *Live job sources* workflow and document it here.

### Manual URL import

Not implemented. Arbitrary career pages vary too much to parse reliably, and many prohibit automated access.

## Optional LLM (career assistant)

- **Provider:** Anthropic Messages API (`POST https://api.anthropic.com/v1/messages`, `anthropic-version: 2023-06-01`), via `integrations/llm/client.py`.
- **Configure:** `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY=…`, `LLM_MODEL=<model id you have access to>`, and optionally `LLM_TIMEOUT_SECONDS`. No model name is assumed.
- **Used only when** it's configured **and** the user has turned on "Allow the career assistant to use an external AI model". Otherwise the grounded template assistant answers, and nothing is sent.
- **Failures** (network, 429, 5xx, empty output) fall back to templates in `auto` mode, or return `502 llm_unavailable` in explicit `llm` mode.
- **Costs** are billed by the provider per token. The assistant is rate-limited (`RATE_LIMIT_ASSISTANT`).

## Semantic model

- `sentence-transformers` (optional, `pip install -r backend/requirements-semantic.txt`) downloads `EMBEDDING_MODEL` (default `sentence-transformers/all-MiniLM-L6-v2`) from Hugging Face on first use. To run offline, pre-download the model into the Hugging Face cache.
- Without it, the local LSA backend is used. `EMBEDDING_BACKEND=lsa` forces LSA.
