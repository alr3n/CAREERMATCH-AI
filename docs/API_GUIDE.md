# API guide

Base path: `/api/v1`. Interactive OpenAPI docs: `http://localhost:8000/api/v1/docs` (schema at `/api/v1/openapi.json`).

## Conventions

- **Auth:** `Authorization: Bearer <access_token>` on every endpoint except `/auth/*` and `/health*`. Tokens are HS256 JWTs that expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default 60).
- **Errors** always look like this:

  ```json
  {"error": {"code": "not_found", "message": "Job not found", "details": null}}
  ```

  Validation errors use `code: "validation_error"` with `details: [{loc, message, type}]`. Internal errors never include exception details.
- **Pagination:** list endpoints take `page` (≥1) and `page_size` (1–100) and return `{items, total, page, page_size}`.
- **Isolation:** another user's resources return `404`, never `403`, so their existence isn't revealed.
- **Rate limits** (per user, or per IP for auth endpoints) return `429` with a `Retry-After` header. Defaults: auth 10/min, uploads 10/h, refresh 6/h, matching 30/h, assistant 30/h (configurable via `RATE_LIMIT_*`).

## Endpoints

### Health
| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness |
| GET | `/health/ready` | Readiness: database connectivity (`503` if unreachable) |

### Auth and profile
| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | `{email, password}` → `201 {access_token, token_type, expires_in, user}`. Password 8–72 chars, mixing letters with numbers or symbols. `409 email_taken` |
| POST | `/auth/login` | `{email, password}` → token. `401 invalid_credentials` (same message whether or not the account exists) |
| GET | `/profile` | `{user, profile, completeness, completeness_items, has_resume, llm_available}` |
| PATCH | `/profile` | Partial update of preferences and consent (`career_stage`, `goal`, `preferred_titles`, `preferred_industries`, `preferred_locations`, `work_arrangements`, `employment_types`, `min_salary`, `salary_currency`, `skills_to_develop`, `consent_llm_processing`, `consent_store_resume_text`) |
| DELETE | `/profile` | `204`. Permanently deletes the account and all its data |

### Resumes
| Method | Path | Description |
|---|---|---|
| POST | `/resumes/upload` | multipart `file` (PDF/DOCX ≤ `MAX_UPLOAD_MB`) → `201` extracted resume. Errors: `413 file_too_large`, `415 unsupported_type`/`type_mismatch`, `422 empty_file`/`malformed`/`encrypted`/`no_text` |
| GET | `/resumes` | Your resumes (newest first) |
| GET | `/resumes/{id}` | Extracted profile: skills with evidence, education, experience, projects, certifications, warnings, detected preferences |
| PATCH | `/resumes/{id}/profile` | Corrections. Provided fields replace stored ones (`skills`, `education`, `experience`, `projects`, `certifications`, `achievements`, `summary`, `total_experience_months`) |
| DELETE | `/resumes/{id}` | `204`. Deletes the file, extracted data and matches based on it |

### Jobs
| Method | Path | Description |
|---|---|---|
| GET | `/jobs/sources` | Configured sources with status, known providers (`configured: true/false`), demo flag, unsupported-provider note |
| POST | `/jobs/refresh` | Fetch from every configured provider (per-source cooldown) → per-source report: `ok`, `error`, `rate_limited` or `skipped_cooldown`, with counts |
| GET | `/jobs/facets` | Counts for filters (categories, locations, skills, live vs. demo) |
| GET | `/jobs` | Filtered list. Query: `q`, `employment_types`, `work_arrangements`, `experience_levels`, `categories`, `location`, `skills`, `checked_within_days`, `include_demo`, `saved_only`, `sort` (recently_checked, posted, title), `page`, `page_size` |
| POST | `/jobs/search` | Same filters in a JSON body (also `salary_min`, `salary_currency`), and records the search in history |
| GET | `/jobs/{id}` | Full listing with qualifications, tagged skills, freshness and `source_attribution` |

### Matches
| Method | Path | Description |
|---|---|---|
| POST | `/matches` | `{preset: balanced, skills_first or preferences_first, weights?: {component: 0–10}, filters?: {...}, limit: 1–100}` → `201` run with ranked results. `400 resume_required` |
| GET | `/matches` | Results of the latest run (or `?run_id=`), paginated |
| GET | `/matches/{id}` | Full explanation: components, weights, labels, evidence, job detail, feedback |
| POST | `/matches/{id}/feedback` | `{rating: relevant or not_relevant, comment?}` → `204` |

Example match summary:

```json
{
  "rank": 1, "score": 84.1, "evidence_coverage": 1.0,
  "components": {"semantic_similarity": 0.9, "required_skill_coverage": 0.83, "...": "..."},
  "matched_skills": ["SQL", "Python"], "missing_required": ["Power BI"],
  "top_reason": "4 of 6 required skills found in your resume, plus 2 related",
  "job": {"title": "Data Analyst Intern", "is_demo": true, "...": "..."}
}
```

### Saved jobs, skills, history, evaluation, assistant
| Method | Path | Description |
|---|---|---|
| GET | `/saved-jobs` | Paginated saved jobs |
| POST | `/saved-jobs` | `{job_id, note?}` → `201` (idempotent) |
| DELETE | `/saved-jobs/{job_id}` | `204`, or `404` if not saved |
| GET | `/skills/gaps` | `?top_k=` (default 20) jobs from the latest run → gaps (required/preferred counts, posting excerpts), identified skills, frequency across listings. `400 matches_required` |
| GET | `/skills/recommendations` | Project ideas, ways to demonstrate each skill, curated free resources |
| GET | `/history` | Searches and matching runs (filters only) |
| DELETE | `/history` | Clear history |
| GET | `/evaluation/summary` | Latest evaluation report, or `{"status": "not_evaluated", "message": "Not yet evaluated."}` |
| GET | `/assistant/status` | Whether an LLM is configured, your consent, and exactly what would be shared |
| POST | `/assistant` | `{task, job_id, input_text?, mode: auto, template or llm}`. Tasks: `explain_requirements`, `resume_suggestions`, `rewrite_bullet` (needs `input_text`), `portfolio_projects`, `interview_questions`, `cover_letter`. Returns a draft with `review_required: true` |

## CLI

```bash
cd backend
python -m app.cli refresh-jobs [--force]       # suitable for cron
python -m app.cli sources
python -m app.cli import-evaluation ../ml/artifacts/evaluation_report.json
```
