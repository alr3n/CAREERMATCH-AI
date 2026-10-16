# Database schema

PostgreSQL 16 in production. Migrations live in `backend/alembic/versions/` (initial: `0001_initial_schema.py`). Every primary key is a UUID. JSON columns are `JSONB` on PostgreSQL. Timestamps are timezone-aware (UTC).

```bash
cd backend && alembic upgrade head      # apply
alembic downgrade -1                    # roll back one revision
alembic revision --autogenerate -m "…"  # after changing models
```

## Entity relationships

```
users 1──1 user_profiles
users 1──* resumes 1──* extracted_skills
                   1──* education_records
                   1──* experience_records
                   1──* projects
users 1──* match_results *──1 job_listings
             match_results 1──* match_evidence
             match_results *──1 resumes
users 1──* saved_jobs *──1 job_listings
users 1──* search_history
users 1──* user_feedback *──1 job_listings
users 1──* audit_events (user_id SET NULL on delete)
job_sources 1──* job_listings 1──* job_skills
job_listings 0..1──* job_listings (duplicate_of_id)
model_versions 1──* evaluation_runs
```

## Tables

| Table | Purpose | Key columns / constraints |
|---|---|---|
| `users` | Accounts | `email` unique, `password_hash` (bcrypt), `is_active` |
| `user_profiles` | Preferences and consent; every field optional | `user_id` unique FK (CASCADE); lists stored as JSON; `min_salary` + `salary_currency`; `consent_llm_processing`, `consent_store_resume_text`, `consent_updated_at` |
| `resumes` | One uploaded resume and its extracted profile summary | FK `user_id` (CASCADE); sanitised `original_filename`; `sha256`; `storage_path` (only if retention is enabled); `raw_text` (only with consent, redacted); `status` processed/reviewed; `extraction_warnings`; `detected_preferences`; `is_active` |
| `extracted_skills` | Skills on a resume | FK `resume_id` (CASCADE); `source` extracted/user; `evidence` line; `confidence` |
| `education_records` / `experience_records` / `projects` | Structured resume sections | FK `resume_id` (CASCADE); `position` for ordering; `source` extracted/user; experience has `duration_months` (only when clearly supported) and `is_internship` |
| `job_sources` | One configured provider endpoint | unique (`provider`, `identifier`); `is_demo` (legacy, always false); `enabled`; `last_fetched_at`, `last_status`, `last_error`, `last_fetch_count` |
| `job_listings` | Normalised postings | unique (`source_id`, `external_id`); `apply_url`; `posting_url` (original posting); `source_platform` (e.g. Lever, LinkedIn); `last_checked_at` (indexed); `status` active/expired; `content_fingerprint` (indexed); `duplicate_of_id`; `is_demo` (legacy, always false; rows with true are excluded from every query and were purged by migration 0002); classified `work_arrangement`, `employment_type`, `experience_level`, `category`; salary fields only from the provider; indexes on (status, is_demo) and (arrangement, type, level) |
| `job_skills` | Skills in a posting | FK `job_id` (CASCADE); `requirement` required/preferred/mentioned; `evidence`; index on `skill` |
| `match_results` | One ranked job in a matching run | FKs to user, resume, job (CASCADE); `run_id` (indexed); `rank`; `score` 0–100; `evidence_coverage`; `components`, `weights` (JSON); `semantic_backend`; `model_version` |
| `match_evidence` | Explanation items | FK `match_id` (CASCADE); `kind`, `label`, `detail`, `requirement`, `position` |
| `saved_jobs` | Saved opportunities | unique (`user_id`, `job_id`) |
| `search_history` | Searches and matching runs | `kind` search/match; `query` JSON with filters only (**never resume content**); `result_count`; `run_id` |
| `user_feedback` | Relevance feedback (future training labels) | unique (`user_id`, `job_id`); `rating` relevant/not_relevant |
| `model_versions` | Registered model configurations | unique (`name`, `version`) |
| `evaluation_runs` | Recorded evaluation results | dataset name/version, split, `metrics` JSON, `config`, `notes` |
| `audit_events` | Security-relevant events | `event_type`; `detail` JSON without PII; `user_id` SET NULL on delete |

## Deletion

- **Delete resume** (`DELETE /resumes/{id}`): removes the stored file if one exists, then the resume row. Cascades remove its skills, education, experience, projects, match results and evidence.
- **Delete account** (`DELETE /profile`): removes the user's storage directory, then the user row. Cascades remove the profile, resumes (and their dependants), matches, saved jobs, history and feedback. Audit events keep only the event type, with `user_id` set to NULL.
- **Withdraw text consent:** clears `raw_text` on all of the user's resumes.

SQLite needs `PRAGMA foreign_keys=ON` for cascades. The engine sets it on every connection.

## Data minimisation

- Contact details are never extracted or stored as fields.
- Raw resume text is stored only with consent, after redaction.
- Original files are discarded unless `RETAIN_RESUME_FILES=true`. Retained files are stored under random names in a per-user directory.
- Search history stores filters and keywords only.
