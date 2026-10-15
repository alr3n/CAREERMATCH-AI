# Privacy and security

Resumes contain personal information. This document describes the controls that are **implemented**, the ones an operator must add for production, and the obligations to review before a public launch. Implementing these controls doesn't by itself make a deployment legally compliant.

## Data handled

| Data | Stored? | Notes |
|---|---|---|
| E-mail and password hash | Yes | bcrypt (cost 12). E-mail is the login identifier |
| Uploaded resume file | **No by default** | Parsed in memory, then discarded. With `RETAIN_RESUME_FILES=true`, stored under a random name in a per-user directory and deleted with the resume or account |
| Full resume text | **Only with consent** | Contact details are redacted first. Withdrawing consent deletes stored text |
| Extracted profile (skills, education, experience, projects, certifications, summary) | Yes | Needed for matching. Editable and deletable by the user |
| Contact details (name, e-mail and phone from the resume, address) | **Not extracted** | Not needed for matching |
| Preferences, saved jobs, matches, feedback | Yes | Deleted with the account |
| Search history | Yes, filters only | Never contains resume content. Clearable |
| Audit events | Yes | Event type and IDs only; user ID nulled on account deletion |

## Implemented controls

**Uploads**
- Extension allow-list (PDF, DOCX) **and** magic-byte check. The size limit (`MAX_UPLOAD_MB`, default 5) is enforced while streaming.
- Encrypted, malformed, empty and image-only PDFs are rejected with user-facing messages. DOCX archives are checked for structure and uncompressed size (zip-bomb guard).
- File names are sanitised for display only. Storage uses UUID names, and paths are checked to stay inside `STORAGE_DIR` (path-traversal guard).

**Authentication and authorisation**
- JWT (HS256) with expiry. `SECRET_KEY` must be at least 32 random characters in production; the app refuses to start otherwise.
- Every user-owned resource is filtered by `user_id`. Other users' resources return `404`, and tests cover cross-user access to resumes and matches.
- Login failures use one generic message, with timing equalised for unknown accounts.

**Abuse protection**
- Per-user or per-IP sliding-window rate limits on login and registration, upload, refresh, matching and the assistant (`429` with `Retry-After`).
- A per-source refresh cooldown and a single concurrent refresh.

**Logging and errors**
- A log filter redacts e-mail addresses, phone numbers, bearer tokens and JWTs. Resume text is never logged, and unhandled errors log only the exception type.
- Clients receive a consistent error envelope with no stack traces or internal messages.

**Untrusted content and prompt injection**
- Resume and job text is parsed with regular expressions and an HTML parser, never executed or evaluated.
- The optional LLM receives the posting, profile and user text inside `<job_posting>`, `<candidate_profile>` and `<user_text>` tags marked as untrusted data, with angle brackets stripped, under a system prompt that forbids following embedded instructions or inventing facts. LLM output is shown as a draft requiring review and is never executed or used to change data.
- The frontend renders all text as text (React escaping) and never uses `dangerouslySetInnerHTML`.

**HTTP**
- Security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`. CORS is restricted to `CORS_ORIGINS`.

**Fairness**
- No protected or sensitive characteristics are extracted or used for ranking: no age, gender, religion, ethnicity, marital status, photo or address.

**User control**
- Consent toggles for resume-text storage and LLM processing (both off by default).
- Deleting a resume or the whole account, with cascading deletes and file removal.
- The data-processing explanation in Settings and on the landing page.
- No automatic applications, and resumes are never sent to employers.

## External processors

| Processor | Receives | When |
|---|---|---|
| Greenhouse / Lever public APIs | Nothing about users. The server only *reads* public postings | On refresh |
| Anthropic (optional) | Structured profile (skills, experience and project descriptions, education fields, certifications), the selected posting, and any bullet the user submits. No name, e-mail, phone number or address | Only if the operator configures `LLM_PROVIDER=anthropic` **and** the user has turned on LLM consent |

## Operator checklist before public deployment

- [ ] Serve only over **TLS** (terminate at a reverse proxy or load balancer) and set `CORS_ORIGINS` to the real frontend origin.
- [ ] Set a strong `SECRET_KEY` and a strong database password. Keep `.env` out of version control (it's git-ignored).
- [ ] Decide on resume-file retention. Leave it off unless there's a documented need.
- [ ] Run more than one API worker? Replace the in-memory rate limiter with a shared store (e.g. Redis) and move refreshes to a single scheduled job.
- [ ] Consider HttpOnly, SameSite cookies instead of a bearer token in `sessionStorage` if you add any third-party scripts. The current SPA loads no third-party scripts, and fonts are self-hosted.
- [ ] Encrypted database backups with access controls (see the README's backup section) and a retention schedule for inactive accounts.
- [ ] Publish a privacy notice naming the controller, purposes, legal basis, retention, processors and user rights.
- [ ] Review obligations under the **Philippine Data Privacy Act of 2012 (RA 10173)** and NPC issuances (e.g. registration thresholds, breach notification, DPO appointment), and under the GDPR if serving EU residents. Get legal advice; this document isn't legal advice.
- [ ] If enabling the LLM, review the provider's data-processing terms and retention settings, and update the privacy notice.
- [ ] Run a dependency vulnerability scan (`pip-audit`, `npm audit`) as part of release.

## Reporting a vulnerability

Please report security issues privately to the repository owner rather than opening a public issue.
