# CareerMatch AI

**Your Skills. Your Next Opportunity.**

CareerMatch AI reads a resume once, builds a structured skill profile that the user reviews and corrects, ranks job and internship listings from real, permitted job-board APIs, and explains every recommendation: which skills matched, which requirements were not found in the resume, how the level and preferences fit, and where the listing came from.

It is built as a portfolio-quality AI/ML product with an honest scope. A compatibility score is **not** a probability of being hired, and a skill "not found in your resume" is not proof that the user lacks it.

---

## Contents

1. [Problem](#problem) · 2. [Target users](#target-users) · 3. [Features](#features) · 4. [Architecture](#architecture) · 5. [Tech stack](#tech-stack) · 6. [Getting started](#getting-started) · 7. [Configuration](#configuration) · 8. [Database](#database) · 9. [Development and testing](#development-and-testing) · 10. [ML methodology](#ml-methodology) · 11. [Datasets](#datasets) · 12. [Evaluation results](#evaluation-results) · 13. [Job providers](#job-providers) · 14. [API](#api) · 15. [Privacy and security](#privacy-and-security) · 16. [Limitations](#limitations) · 17. [Deployment](#deployment) · 18. [Roadmap](#roadmap)

---

## Problem

Students and job seekers, especially in the Philippines, often find that keyword search on job sites returns many listings that don't fit what they can actually do, so they end up comparing their CV with dozens of postings by hand. CareerMatch AI does that comparison for them. It extracts skills and experience from the resume, compares them with each posting's stated requirements and with the user's own preferences, and shows the evidence behind every ranking.

## Target users

- College students looking for internships or OJT
- Fresh graduates looking for a first job
- Entry-level professionals and career changers
- Anyone who wants to see their skill gaps before applying

The primary market is the Philippines (it recognises local degree abbreviations, OJT, Metro Manila cities, and PHP salaries), with remote and international listings where providers publish them.

## Features

| Area | Implemented |
|---|---|
| **Resume upload** | PDF (PyMuPDF) and DOCX (python-docx). Extension and magic-byte checks, a size limit, zip-bomb guard, and clear errors for empty, encrypted, malformed or scanned files. Original files are discarded after parsing by default |
| **Profile extraction** | Rule-based extraction of skills (curated taxonomy of about 170 skills, each with its evidence line), education, experience with durations only when clearly supported, projects, certifications and achievements. Names, e-mail addresses and phone numbers are not extracted |
| **Review and correction** | Users edit every extracted field before matching and can update preferences without re-uploading |
| **Preferences** | Career stage, goal, target titles, industries, PH locations, remote/hybrid/on-site, employment type, optional minimum salary, skills to develop. All optional |
| **Job discovery** | Provider abstraction with **Greenhouse Job Board API** and **Lever Postings API** integrations, normalisation into one schema, deduplication by content fingerprint, freshness tracking, expiry, and source attribution |
| **Filtering** | Internship, entry level, full-time or part-time, remote, hybrid, on-site, location, category, skills, salary (only listings that disclose salary), recently checked, saved |
| **Matching** | Transparent multi-signal score: semantic similarity, required and preferred skill coverage, experience-level fit, preference fit, title relevance. Users can choose a preset or set their own weights |
| **Explanations** | Matched and related skills with the posting line, requirements not found, relevant resume projects or experience, level and preference checks, the top reasons, source, last-checked time and application link |
| **Skill-gap analysis** | Gaps across the top matches or selected jobs, split into required and preferred, with the posting lines that ask for them, project ideas, ways to demonstrate each skill, and curated free resources. Also shows how often each skill appears across listings |
| **Career assistant** | Explains requirements, suggests resume improvements, rewrites bullets without inventing facts, suggests portfolio projects, writes interview questions, and drafts cover letters. It is template-based and grounded by default. An optional LLM is used only with explicit user consent, and every output is a draft for the user to review |
| **Dashboard** | Overview, recommendations, job detail, my resume, skill gaps (charts), saved jobs, search history, model evaluation, settings and privacy |
| **Privacy controls** | Consent toggles, deleting a resume, deleting the whole account and all its data, clearing history, and an explanation of how data is processed |
| **Evaluation** | Reproducible script, a hand-labelled synthetic benchmark, baselines and ablations, bootstrap confidence intervals, and extraction precision, recall and F1 |

**Planned, not implemented:** supervised learning-to-rank (no genuine labelled training data yet), OCR for scanned PDFs, manual URL import, and pgvector-backed pre-computed embeddings. See [Roadmap](#roadmap).

## Architecture

```
React + Vite SPA  ──HTTPS/JSON (Bearer JWT)──►  FastAPI
 pages / features / components                    api/routes → services → repositories → PostgreSQL
 services/api.ts (typed client)                   ml/ (extraction, parsing, embeddings, scoring, explain, metrics)
                                                  integrations/jobs (Greenhouse, Lever, Demo) · integrations/llm (optional)
```

The ML code works on plain dataclasses and has no database dependency, so the evaluation script runs the **same** scoring code as the API. Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```
backend/    FastAPI app (api, core, db, models, schemas, services, repositories, integrations, ml, security), Alembic, pytest
frontend/   React + TypeScript + Tailwind, Vitest/RTL unit tests, Playwright E2E
ml/         benchmark/ (synthetic, hand-labelled), artifacts/evaluation_report.json
scripts/    inspect / validate / preprocess datasets, evaluate_matching.py
data/       local-only raw and processed datasets (git-ignored)
docs/       architecture, schema, API, ML, evaluation, privacy, integrations, dataset card
```

## Tech stack

- **Frontend:** React 18, TypeScript 5.7, Vite 5, Tailwind CSS 3, React Router 6, React Hook Form + Zod, Radix Dialog, Recharts
- **Backend:** Python 3.11+ (CI uses 3.12), FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PyJWT, bcrypt, httpx
- **Database:** PostgreSQL 16 (SQLite for tests and quick local runs)
- **ML/NLP:** scikit-learn (TF-IDF, truncated SVD/LSA), NumPy, pandas; optional Sentence Transformers (`all-MiniLM-L6-v2`, pretrained, not fine-tuned)
- **Documents:** PyMuPDF, python-docx
- **Quality:** pytest, Ruff, Vitest + Testing Library, Playwright, GitHub Actions; Docker and Docker Compose

Exact versions are pinned in `backend/requirements*.txt` and `frontend/package-lock.json`.

## Getting started

### Option A: Docker Compose

```bash
cp .env.example .env          # set SECRET_KEY; optionally GREENHOUSE_BOARDS / LEVER_SITES
docker compose up --build
```

- Web app: http://localhost:5173
- API docs: http://localhost:8000/api/v1/docs

The backend container applies migrations on start.

### Option B: Local development

Requirements: Python 3.11+, Node 22, PostgreSQL 16 (or SQLite).

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg://careermatch:careermatch@localhost:5432/careermatch
#   or: export DATABASE_URL=sqlite:///./careermatch.db
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm ci
npm run dev                    # http://localhost:5173
```

Load real listings with `python -m app.cli refresh-jobs` (after configuring providers), or use **Refresh** in the app. With `ENABLE_DEMO_PROVIDER=true`, 20 clearly labelled fictional listings are available so the workflow can be tried offline. They show a "Demo data" badge everywhere, link only to `example.com`, and are disabled automatically in production.

## Configuration

All settings come from environment variables. `.env.example` lists them with comments. The important ones:

| Variable | Purpose |
|---|---|
| `APP_ENV` | `development`, `test` or `production`. In production the demo provider is off and a strong `SECRET_KEY` is required |
| `SECRET_KEY` | JWT signing key, at least 32 random characters in production |
| `DATABASE_URL` | SQLAlchemy URL (PostgreSQL recommended) |
| `CORS_ORIGINS` | Allowed browser origins |
| `MAX_UPLOAD_MB`, `STORAGE_DIR`, `RETAIN_RESUME_FILES` | Upload limits and optional retention of original files |
| `GREENHOUSE_BOARDS`, `LEVER_SITES`, `LEVER_REGION` | Job sources (comma-separated board tokens or site names) |
| `REFRESH_COOLDOWN_MINUTES`, `LISTING_STALE_DAYS` | Refresh throttling and the "stale listing" threshold |
| `EMBEDDING_BACKEND`, `EMBEDDING_MODEL` | `auto`, `sentence-transformers` or `lsa` |
| `LLM_PROVIDER`, `ANTHROPIC_API_KEY`, `LLM_MODEL` | Optional assistant LLM (`none` by default) |
| `VITE_API_BASE_URL` | API base URL baked into the frontend build |

The app is fully usable without any paid API. Matching uses local TF-IDF/LSA by default.

## Database

There are 18 tables: users, user profiles, resumes and their extracted skills, education, experience and projects, job sources, listings and skills, match results and evidence, saved jobs, search history, model versions, evaluation runs, user feedback, and audit events. They use UUID keys and timestamps, have unique constraints on `(source, external_id)`, carry indexes for the common filters, and cascade deletes from the user. See [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md).

```bash
cd backend
alembic upgrade head        # apply
alembic downgrade base      # roll back everything
alembic check               # verify models and migrations agree
```

## Development and testing

```bash
# Backend: lint and tests (SQLite by default; set TEST_DATABASE_URL to run against PostgreSQL)
cd backend
ruff check app tests && (cd ../scripts && ruff check .)
pytest
TEST_DATABASE_URL=postgresql+psycopg://careermatch:careermatch@localhost:5432/careermatch_test pytest

# Frontend
cd frontend
npm run typecheck && npm test && npm run build

# End-to-end (starts a throwaway backend + built frontend)
cd frontend
npx playwright install chromium     # first time only
npx playwright test
```

**Results from the latest verification run (2026-10-15):**

| Check | Result |
|---|---|
| Ruff (backend and scripts) | passed |
| Alembic upgrade, downgrade and upgrade on PostgreSQL 16, plus `alembic check` | passed, no drift |
| pytest on PostgreSQL 16 | 114 passed |
| pytest on SQLite | 114 passed |
| TypeScript typecheck and production build | passed |
| Vitest + Testing Library | 22 passed |
| Playwright E2E (upload → review skills → search → match → open → save → delete resume and account) | 1 passed |

The GitHub Actions workflow (backend on PostgreSQL and SQLite, frontend, and E2E) also passed on its first run for commit `1c120eb`. The Docker images have not been built yet because the development environment has no Docker daemon. The Compose file was validated with `docker compose config`.

Test coverage includes valid, empty, oversized, malformed, encrypted and mislabelled uploads; unsafe file names; extraction corrections; exact, related and missing skills; empty jobs and profiles; conflicting preferences; score normalisation; deterministic ranking; provider success, empty, rate-limited, error, invalid-schema, duplicate, expired and unconfigured cases (including a payload captured from the live Greenhouse API); unauthorised and cross-user access; invalid tokens; rate limits; and deletion.

## ML methodology

1. **Extraction** is rule-based: section detection, a curated skill taxonomy with aliases, and patterns for degrees and date ranges. Every extracted skill keeps its evidence line, and the user corrects anything that is wrong.
2. **Job parsing** splits postings into requirement, preferred and other sections and tags each skill as *required*, *preferred* or *mentioned*.
3. **Semantic similarity** uses LSA (TF-IDF 1–2-grams plus truncated SVD), fitted per request on the current corpus. A pretrained Sentence Transformers model is used instead when installed.
4. **Transparent scoring (`transparent-v1`)**:

   ```
   score = 100 × Σ wᵢ·cᵢ / Σ wᵢ    over the components that could be computed
   semantic 0.35 · required skills 0.30 · preferred skills 0.10 · experience 0.10 · preferences 0.10 · title relevance 0.05
   ```

   The weights are the brief's proposed starting values. **They were not tuned.** Missing information is excluded rather than counted as zero, and the share of weight that could be evaluated is shown as *evidence coverage*. Related skills earn half credit and are always labelled "related".
5. **Baselines:** keyword overlap, TF-IDF cosine, and semantic similarity alone.
6. **No supervised ranker is trained**, because no genuine labelled training data exists. The schema already stores per-component features, user feedback and model versions for a future learning-to-rank model.

Full details: [docs/ML_METHODOLOGY.md](docs/ML_METHODOLOGY.md).

## Datasets

The five candidate public datasets from the brief were inspected for licence, provenance, language and labels. See [docs/DATASET_CARD.md](docs/DATASET_CARD.md). In short, several have unverified licences, one is Korean, and the matching datasets have labels generated by an LLM or by rules, not by humans. **None is used as ground truth.** `scripts/inspect_datasets.py`, `validate_datasets.py` and `preprocess_datasets.py` handle them locally once downloaded into `data/raw/`; see [data/README.md](data/README.md). No dataset is committed, and historical postings are never shown as current vacancies.

## Evaluation results

The benchmark is `ml/benchmark/`: 12 synthetic candidates × 30 synthetic postings = 360 pairs, labelled 0/1/2 by the project author with a written rubric. There was a single annotator and no training split, because nothing is trained. Reproduce it with `python scripts/evaluate_matching.py`.

| Model | P@5 | P@5 (≥1) | R@10 | nDCG@10 (95% CI) | MRR |
|---|---|---|---|---|---|
| keyword-overlap | 0.267 | 0.550 | 1.000 | 0.922 [0.854, 0.974] | 0.883 |
| tfidf-cosine | 0.283 | 0.567 | 1.000 | 0.926 [0.887, 0.960] | 0.944 |
| semantic-only (LSA) | 0.283 | 0.517 | 1.000 | 0.908 [0.861, 0.948] | 0.933 |
| **transparent-v1** | 0.283 | **0.600** | 1.000 | **0.952** [0.901, 0.984] | 0.933 |

- The highest achievable P@5 is 0.283, because most candidates have only one or two highly relevant jobs.
- The paired nDCG@10 difference between transparent-v1 and tfidf-cosine is **+0.026, 95% CI [−0.001, 0.051]**. The interval includes zero, so **this benchmark does not show a reliable improvement over the TF-IDF baseline.** The transparent scorer is at least as good while also providing explanations and preference handling.
- Skill extraction (micro): resumes P 0.923 / R 0.973 / F1 0.947; postings P 0.979 / R 0.946 / F1 0.962.

These are small, synthetic and indicative results. They say nothing about real-world hiring outcomes. Full report and limitations: [docs/EVALUATION.md](docs/EVALUATION.md). The app's **Model evaluation** page shows the same report, or "Not yet evaluated" if none exists.

## Job providers

| Provider | Status |
|---|---|
| Greenhouse Job Board API | Implemented (public GET, one company board per token) |
| Lever Postings API | Implemented (public GET, one company site per name; global or EU) |
| Demo | Implemented for offline demos and tests. Clearly labelled fictional data |
| LinkedIn, JobStreet, Indeed, Kalibrr | **Not integrated.** There is no authorised API for this use, and the app does not scrape them |

Endpoints and field mappings were checked against the official documentation and live responses in October 2026. The automated tests use recorded-format responses through `httpx.MockTransport`. Run a first live refresh in your own environment after setting `GREENHOUSE_BOARDS` or `LEVER_SITES`. If no provider is configured, the app says so and shows no invented listings. Details: [docs/EXTERNAL_INTEGRATIONS.md](docs/EXTERNAL_INTEGRATIONS.md).

## API

The REST API lives under `/api/v1`, with OpenAPI docs at `/api/v1/docs`. Groups: auth, profile, resumes, jobs (sources, refresh, facets, list and search, detail), matches (generate, list, detail, feedback), saved jobs, skills (gaps and recommendations), history, evaluation summary, and assistant. Errors use one envelope, `{"error": {"code", "message", "details"}}`. Listing endpoints are paginated, other users' resources return 404, and expensive operations are rate-limited. Health checks are at `/health` and `/health/ready`. Reference: [docs/API_GUIDE.md](docs/API_GUIDE.md).

## Privacy and security

Resume files are parsed and then discarded unless the operator opts in to keeping them. Full text is stored only with user consent. Contact details are never extracted. Logs pass through a filter that redacts PII, and resume text is never logged. Uploads are validated and stored safely. Authentication uses JWTs, and per-user isolation is covered by tests. Rate limits apply to expensive endpoints. Resume and posting content is treated as untrusted, including against prompt injection in the optional LLM path. Protected characteristics are not extracted or used for ranking, and users can delete their data at any time. **These controls do not by themselves make a deployment legally compliant.** Review the Philippine Data Privacy Act of 2012 obligations and the checklist in [docs/PRIVACY_AND_SECURITY.md](docs/PRIVACY_AND_SECURITY.md) before a public launch.

## Limitations

- Rule-based extraction misses skills outside the taxonomy and some ambiguous short names written in prose. OCR is not enabled for scanned PDFs.
- Greenhouse and Lever are searched per company board or site. There is no cross-company search, so coverage depends on which companies you configure.
- LSA similarity is lexical and depends on the corpus. Sentence Transformers handles paraphrase better but needs a model download, and it was not exercised in the evaluation above.
- The evaluation benchmark is tiny, synthetic and labelled by one annotator.
- The in-process rate limiter and refresh lock assume a single API process.
- Tokens are stored in session storage; see the HttpOnly-cookie trade-off in the privacy doc.

## Deployment

1. Build the images with `docker compose build`, or use the Dockerfiles individually: `backend/Dockerfile`, and `frontend/Dockerfile`, which is an nginx static build that takes the `VITE_API_BASE_URL` build arg.
2. Set `APP_ENV=production`, a strong `SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, and your providers.
3. Put a TLS-terminating reverse proxy in front of both services. The backend runs `alembic upgrade head` on start, and the container health check uses `/health/ready`.
4. Schedule `python -m app.cli refresh-jobs` (for example hourly with cron), within each provider's terms.
5. **Backups:** take daily encrypted `pg_dump` backups with access controls, test restores regularly, and set a retention period. Resume files are not stored by default; if retention is enabled, back up `STORAGE_DIR` the same way.
6. **Costs:** the core workflow needs only compute and PostgreSQL. Greenhouse and Lever public GET endpoints are free. The optional LLM is billed per token by its provider and is rate-limited. Sentence Transformers runs locally on CPU.

## Roadmap

- Collect consented feedback and double-annotated relevance labels, then train and evaluate a learning-to-rank model (LightGBM LambdaRank) with SHAP explanations against `transparent-v1`
- Pre-compute embeddings with pgvector for larger corpora
- Optional OCR for scanned resumes
- URL import limited to supported ATS domains, routed through their official APIs
- A shared rate-limit store (Redis) for multi-worker deployments
