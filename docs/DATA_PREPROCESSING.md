# Data preprocessing

Covers the reusable dataset pipeline in `scripts/` and the preprocessing that the application applies to resumes and job postings at runtime.

## Offline dataset pipeline

```
data/raw/<dataset_key>/*.csv|json|jsonl|parquet
        │  inspect_datasets.py   schema, size, nulls, text lengths, label distribution, language, redacted sample
        │  validate_datasets.py  required columns, empty/malformed text, duplicates; exit 1 if columns are missing
        ▼  preprocess_datasets.py
data/processed/{resumes|jobs|pairs}__<dataset_key>.csv + manifest.json
```

Dataset keys and their expected schemas live in `scripts/dataset_specs.py`. Downloads are manual (commands are printed by `inspect_datasets.py`) and land in `data/raw/`, which is git-ignored.

### Steps in `preprocess_datasets.py`

| Step | Detail |
|---|---|
| Load | CSV, JSON, JSON Lines, Parquet (Parquet needs `pyarrow` from `backend/requirements-ml.txt`) |
| Validate | Stop with an error if a required column is missing. Nothing is guessed. |
| Normalise field names | Per role: resumes → `source, source_id, category, text`; jobs → `source, source_id, title, category, description, reference_skills`; pairs → `source, source_id, job_text, resume_text, reference_label, label_origin` |
| Source identifiers | The dataset key and original ID are kept on every row |
| Malformed text | Removed if empty, under 30 characters, under 90% printable characters, or HTML tags only. **Counted in the manifest.** |
| Duplicates | Exact duplicates of the text (and title) are removed. **Counted in the manifest.** |
| Text cleaning | Unicode NFKC, control characters stripped, whitespace collapsed, truncated to 20,000 characters |
| PII | E-mail addresses and phone-number-like sequences are replaced with `[REDACTED_…]` before writing |
| Reference skills | Lists given as JSON, Python literals or delimited strings are normalised to `skill; skill` |
| Our extraction | For English text, `extracted_skills` holds CareerMatch's own taxonomy matches, for comparison |
| Sampling | Optional `--sample N` with seed 42. Unsampled rows are counted as removed with the reason `not_sampled`. |
| Manifest | `manifest.json` records the creation time, seed, configuration, input file SHA-256 hashes, rows loaded, rows removed per reason and rows retained |

Rows are never dropped silently. Every removal has a reason and a count.

### Reproducibility

The same inputs and arguments produce identical outputs: the seed is fixed, there are no time-dependent transformations, and input hashes are recorded. `backend/tests/test_dataset_scripts.py` exercises validation, preprocessing (counts, redaction, manifest) and evaluation determinism on synthetic fixtures.

## Runtime preprocessing

### Resumes (`backend/app/ml/document_text.py`, `profile_extractor.py`)

1. File type checked against magic bytes (`%PDF-`, ZIP/DOCX structure). Encrypted, empty, malformed and image-only PDFs are rejected with explanations. DOCX archives are checked for zip bombs.
2. Text extracted with PyMuPDF (PDF) or python-docx (DOCX, including tables), then normalised as above.
3. Sections are detected from headings (summary, skills, education, experience, internships, projects, certifications, achievements).
4. Skills are matched against the taxonomy, with the source line kept as evidence. Ambiguous short names (R, Go, C) only count in list-like or skills-section lines.
5. Contact details are **not extracted**. If the user consents to storing resume text, it's redacted first.
6. The original file is discarded unless `RETAIN_RESUME_FILES=true`.

### Job postings (`backend/app/ml/job_parser.py`, `services/job_service.py`)

1. Greenhouse's escaped HTML is unescaped and converted to lines that keep headings and list items. Lever's structured `lists` are kept as sections.
2. Headings are classified as required, preferred or other. Lines mentioning "preferred", "a plus" and similar are treated as preferred.
3. Skills are tagged required, preferred or mentioned, with the posting line as evidence.
4. Experience level, minimum years, employment type, work arrangement and category are classified from structured provider fields first, then from the title or explicit phrases. Otherwise they're `unknown`, never guessed.
5. A content fingerprint (normalised company, title, location and description) identifies duplicates across sources.
