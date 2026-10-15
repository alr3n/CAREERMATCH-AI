# Architecture

## System overview

```
┌──────────────────────────────┐        HTTPS / JSON (Bearer JWT)        ┌──────────────────────────────────────────┐
│  Frontend (React + Vite)     │ ─────────────────────────────────────►  │  Backend (FastAPI)                        │
│  pages / features /          │                                         │  api/routes  →  services  →  repositories │
│  components / services/api   │ ◄─────────────────────────────────────  │        │            │                    │
└──────────────────────────────┘                                         │        ▼            ▼                    │
                                                                         │      ml/        integrations/            │
                                                                         │  (extraction,   (jobs: greenhouse,       │
                                                                         │   scoring,       lever, demo;            │
                                                                         │   explanations)  llm: anthropic)         │
                                                                         └──────┬───────────────────┬───────────────┘
                                                                                │ SQLAlchemy        │ httpx (outbound, public APIs)
                                                                                ▼                   ▼
                                                                        PostgreSQL 16       Greenhouse / Lever / optional LLM
```

## Repository layout

```
backend/
  app/
    api/            FastAPI routers (thin: validation, auth, status codes) and shared dependencies
    core/           settings, error envelope, PII-safe logging, rate limiter
    db/             declarative base, engine and session
    models/         SQLAlchemy models (users, resumes, jobs, activity)
    schemas/        Pydantic request/response models
    services/       business logic (profile, resume, jobs, matching, skill gaps, assistant, audit)
    repositories/   reusable query builders (job filtering and pagination)
    integrations/
      jobs/         provider abstraction + Greenhouse, Lever, demo providers
      llm/          optional Anthropic Messages API client
    ml/             taxonomy, extraction, job parsing, embeddings, scoring, baselines, metrics, explanations
    security/       password hashing, JWT, safe file handling
    cli.py          refresh-jobs / sources / import-evaluation
  alembic/          migrations
  tests/            pytest suite (SQLite by default, PostgreSQL in CI)
frontend/
  src/
    components/     reusable UI (ResumeUploader, JobCard, MatchScore, …)
    features/       larger composite pieces (ResumeEditor, AssistantPanel, SourcesPanel)
    pages/          routed screens
    hooks/          auth context, async loader, save toggle
    services/api.ts typed API client
    types/api.ts    response types mirroring the backend schemas
  e2e/              Playwright end-to-end test
ml/
  benchmark/        synthetic, hand-labelled evaluation set
  artifacts/        evaluation_report.json (other artifacts ignored)
scripts/            dataset inspect/validate/preprocess + evaluation
data/               local-only raw/processed datasets (git-ignored)
docs/               this documentation
```

## Request flow: generating matches

1. `POST /api/v1/matches` → `routes/matches.py` authenticates the user and applies the per-user rate limit.
2. `match_service.run_matching` loads the active resume and preferences and builds a `CandidateProfile` (`ml/features.py`).
3. Visible listings (active, not duplicated, from enabled sources, optionally filtered) are loaded and converted to `JobRecord`s.
4. The semantic backend computes similarities in one batch. `ml/scoring.rank` scores every listing deterministically.
5. `ml/explain.build_evidence` turns each score breakdown into evidence. Results and evidence are stored in `match_results` / `match_evidence` under one `run_id`, and the request (filters only) goes into `search_history`.
6. The response contains the ranked summaries. `GET /matches/{id}` returns the full explanation.

## Separation of concerns

- **Routers** never contain business logic, and **services** never build HTTP responses.
- **ML code** (`app/ml`) works on plain dataclasses (`CandidateProfile`, `JobRecord`) and has no database dependency, so the evaluation scripts run the exact same scoring code as the API.
- **Providers** only fetch and map provider JSON to `ProviderListing`. Normalisation, skill tagging, deduplication and expiry are shared, so a new source means one new class.
- **The frontend** talks to the API only through `services/api.ts`, whose types are kept in step with the Pydantic schemas.

## Key design decisions

| Decision | Reason |
|---|---|
| Rule-based extraction plus a curated taxonomy | Runs offline, explainable evidence for every item, no labelled training data available |
| Transparent weighted score, not a learned ranker | No genuine labelled training set yet. Transparency is a product requirement (see ML_METHODOLOGY.md) |
| LSA fallback for semantic similarity | Core workflow must work without paid APIs or model downloads |
| PostgreSQL in production, SQLite for tests | Same SQLAlchemy models. JSON columns use JSONB on PostgreSQL |
| In-process rate limiter | Correct for one API process. Swap for Redis when scaling horizontally |
| Original resume files discarded by default | Data minimisation. Retention is opt-in for operators |
| pgvector not used yet | Embeddings are computed per request on the current corpus (hundreds to low thousands of listings). pgvector becomes worthwhile when listings reach tens of thousands with a fixed embedding model |
| Session-storage token on the frontend | Simple SPA auth. Mitigated by strict input handling and no third-party scripts. See PRIVACY_AND_SECURITY.md for the trade-off versus HttpOnly cookies |

## Scaling notes

- Job refresh runs from the CLI (`python -m app.cli refresh-jobs`) on a schedule, or via the rate-limited endpoint.
- Matching is O(listings) per request. Above roughly 10k listings, pre-compute job embeddings with Sentence Transformers, store them (pgvector), and pre-filter by vector similarity before transparent scoring.
- Multiple API workers need a shared rate-limit store and a database-level lock (or a job queue) for refreshes.
