# External integrations

## Job providers

All providers implement `JobProvider.fetch()` (`backend/app/integrations/jobs/base.py`) and return `ProviderListing` objects. Normalisation, skill tagging, deduplication, expiry and freshness tracking are shared (`services/job_service.py`).

### Greenhouse Job Board API: implemented

- **Docs:** https://developers.greenhouse.io/job-board.html (verified 2026-10-14)
- **Endpoint:** `GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`
- **Access:** public data; GET endpoints need no authentication. The API is **per company board**, so it can't search all of Greenhouse.
- **Fields used:** `id`, `title`, `absolute_url`, `content` (HTML-escaped), `location.name`, `departments[].name`, and `company_name`, `first_published`, `application_deadline` when present. `updated_at` is **not** treated as a posting date.
- **Rate limits:** none documented for GET. CareerMatch adds a per-source cooldown (`REFRESH_COOLDOWN_MINUTES`) and handles `429` with `Retry-After`.
- **Configure:** `GREENHOUSE_BOARDS=companyA,companyB`. The token is the last part of `https://boards.greenhouse.io/<token>`.

### Lever Postings API: implemented

- **Docs:** https://github.com/lever/postings-api (verified 2026-10-14)
- **Endpoint:** `GET https://api.lever.co/v0/postings/{site}?mode=json&skip=N&limit=100` (EU: `https://api.eu.lever.co`). Paginated, up to 2,000 postings per site.
- **Access:** published postings are public. Per company site, with no full-text search.
- **Fields used:** `id`, `text`, `hostedUrl`, `categories.{location, commitment, team, department}`, `country`, `workplaceType`, `description`/`descriptionPlain`, `lists[]` (kept as sections), `additional`, `salaryRange`, `salaryDescriptionPlain`, and `createdAt` when present.
- **Rate limits:** documented only for application POSTs. The same cooldown and `429` handling apply.
- **Configure:** `LEVER_SITES=companyA,companyB` and `LEVER_REGION=global|eu`. The site is the last part of `https://jobs.lever.co/<site>`.

### Demo provider: implemented, clearly labelled

20 fictional listings at fictional companies (suffixed "Demo – fictional"), linking to `example.com`. They're flagged `is_demo` everywhere and shown with a "Demo data, not a real job" badge. Turned on with `ENABLE_DEMO_PROVIDER=true` and **always disabled when `APP_ENV=production`**. They exist so the workflow can be demonstrated and tested offline.

### Error handling

| Situation | Behaviour |
|---|---|
| Provider unreachable or timeout | Source marked `error` with a message. **Existing listings are kept** (not expired) and show their last-checked age |
| HTTP 429 | Source marked `rate_limited`. Retry after the cooldown |
| HTTP 404 | "Source not found at the provider" (wrong board token or site name) |
| Unexpected JSON shape | `ProviderSchemaError`, source marked `error` |
| Individual invalid items (missing fields, non-HTTPS URL) | Skipped and counted (`skipped_invalid`) |
| Posting disappeared from a provider | Marked `expired` on the next successful refresh |
| Deadline passed | Marked `expired` |
| Same posting on two sources | The later one gets `duplicate_of_id` and is hidden |
| No provider configured | `/jobs/sources` reports `configured: false`. Listing endpoints return an empty list, **never invented jobs** |

### Not integrated, and why

LinkedIn, JobStreet, Indeed, Kalibrr and similar boards are **not** integrated. They don't offer an authorised public API for this use, and scraping them would breach their terms and anti-bot protections. The app says so in the job-sources panel. If you obtain authorised API access to another source, add a provider class and register it in `integrations/jobs/registry.py`.

### Adding a provider

1. Create `integrations/jobs/<name>.py` with a class extending `HttpJobProvider` (or `JobProvider`) that implements `fetch()` and maps responses to `ProviderListing`. Validate items with Pydantic and count invalid ones.
2. Add configuration to `core/config.py` and `.env.example`, and register the provider in `registry.build_providers` and `KNOWN_PROVIDERS`.
3. Add tests with recorded-format responses via `httpx.MockTransport` (see `tests/test_job_providers.py`).
4. Document the provider's endpoint, access terms and rate limits here.

### Manual URL import

Not implemented. Arbitrary career pages vary too much to parse reliably, and many prohibit automated access. A future version could accept URLs only from supported ATS domains (Greenhouse, Lever) and route them through the official APIs.

## Optional LLM (career assistant)

- **Provider:** Anthropic Messages API (`POST https://api.anthropic.com/v1/messages`, `anthropic-version: 2023-06-01`), via `integrations/llm/client.py`.
- **Configure:** `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY=…`, `LLM_MODEL=<model id you have access to>`, and optionally `LLM_TIMEOUT_SECONDS`. No model name is assumed.
- **Used only when** it's configured **and** the user has turned on "Allow the career assistant to use an external AI model". Otherwise the grounded template assistant answers, and nothing is sent.
- **Failures** (network, 429, 5xx, empty output) fall back to templates in `auto` mode, or return `502 llm_unavailable` in explicit `llm` mode.
- **Costs** are billed by the provider per token. The assistant is rate-limited (`RATE_LIMIT_ASSISTANT`).

## Semantic model

- `sentence-transformers` (optional, `pip install -r backend/requirements-semantic.txt`) downloads `EMBEDDING_MODEL` (default `sentence-transformers/all-MiniLM-L6-v2`) from Hugging Face on first use. To run offline, pre-download the model into the Hugging Face cache.
- Without it, the local LSA backend is used. `EMBEDDING_BACKEND=lsa` forces LSA.
