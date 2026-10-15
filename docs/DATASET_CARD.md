# Dataset card

This card covers every dataset considered for CareerMatch AI: what it is, what role it could play, and what it can and can't prove. Facts about the Hugging Face datasets come from their dataset cards as read on **2026-10-14**. The Kaggle pages couldn't be read without an account, so their schema and licence are listed as *unverified* until `scripts/inspect_datasets.py` is run on the downloaded files.

> **Network note.** The environment that built this project couldn't reach Kaggle or Hugging Face, so **none of the five external datasets has been downloaded or used to produce any reported metric.** The reported evaluation uses only the synthetic benchmark in `ml/benchmark/`.

## Summary

| Dataset | Role it could play | Size | Language | Licence | Labels | Used for reported results? |
|---|---|---|---|---|---|---|
| [Kaggle Resume Dataset](https://www.kaggle.com/datasets/snehaanbhawal/resume-dataset) | Resume parsing robustness | not verified | en (expected) | **unverified** | job category | No |
| [Kaggle Job Description Dataset](https://www.kaggle.com/datasets/ravindrasinghrana/job-description-dataset) | Job-description processing | not verified | en (expected) | **unverified** | none (skills column) | No |
| [batuhanmtl/job-skill-set](https://huggingface.co/datasets/batuhanmtl/job-skill-set) | Job skill extraction (weak reference) | 1,167 rows, 1 split | en | not stated; inherits the source LinkedIn dataset's terms | **machine-generated** skill lists | No |
| [Divyanandh/resume-matching-dataset-v2](https://huggingface.co/datasets/Divyanandh/resume-matching-dataset-v2) | Matching pairs (not applicable) | 74,147 rows (train 69k / val 100 / test 5k) | **Korean** | not stated | **GPT-4o-mini-generated** grades and scores | No |
| [michaelozon/candidate-matching-synthetic](https://huggingface.co/datasets/michaelozon/candidate-matching-synthetic) | Synthetic resumes (limited) | card claims 10k resumes, 2.5k jobs, 2.5k matches; only the resume table was verified | en | MIT (per card) | **rule-derived** match labels (≥60% skill overlap) | No |
| CareerMatch synthetic benchmark (`ml/benchmark/`) | Primary evaluation of extraction and ranking | 12 candidates × 30 jobs = 360 pairs | en | part of this repository | **hand-assigned** graded relevance and gold skills | **Yes** |

## Per-dataset notes

### Kaggle Resume Dataset (snehaanbhawal)
- **Described as** "a collection of resumes in PDF as well as string format for data extraction".
- **Expected columns** (to verify): `ID`, `Resume_str`, `Resume_html`, `Category`.
- **Can show:** whether the PDF/text extraction and section detection hold up on varied real-world formatting, and the distribution of job categories.
- **Can't show:** skill-extraction accuracy (no skill annotations) or matching quality (no job pairs). A sample would need manual skill annotation first.
- **Cautions:** likely contains real people's resumes. Keep it local, never commit it, and redact before display (the scripts redact e-mails and phone numbers).

### Kaggle Job Description Dataset (ravindrasinghrana)
- **Expected columns** (to verify): `Job Id`, `Job Title`, `Role`, `Job Description`, `skills`, `Responsibilities`, plus company/location/salary fields.
- **Can show:** throughput and robustness of the job-description parser.
- **Can't show:** current vacancies (it's a static dataset and must **never** be shown to users as live jobs). If the postings turn out to be generated rather than collected, it can't show real-world matching quality either.

### batuhanmtl/job-skill-set
- 1,167 English postings in 5 categories, derived from a Kaggle LinkedIn job postings dataset. `job_skill_set` was produced automatically with an external API (RecAI) and was **not** manually checked.
- **Can show:** rough agreement between our extracted skills and another automatic extractor.
- **Can't show:** true extraction precision or recall, because the reference itself is unvalidated. Many descriptions are upper-case or contain merged words.

### Divyanandh/resume-matching-dataset-v2
- Fully synthetic **Korean** job posts, resumes, self-introductions and evaluations, all generated with GPT-4o-mini, including `total_score` (0–100) and grades.
- **Not suitable** for CareerMatch AI's primary evaluation: the language differs, the taxonomy is English, and LLM-generated scores aren't ground truth. The card also has inconsistencies (score ranges, citation). It's kept in the specs only so the decision is documented.

### michaelozon/candidate-matching-synthetic
- Synthetic English resumes (role, seniority, years, industry, education, 5–8 skills, short summary, three bullets) generated with Qwen2.5-0.5B-Instruct. Match labels follow a fixed rule (≥60% must-have skill overlap).
- **Can show:** that the pipeline runs on a large volume of structured resumes.
- **Can't show:** ranking quality. The labels are defined by skill overlap, so a skill-overlap ranker would look perfect by construction. The sample rows also repeat the same template text.

## Selection

Following the "smallest suitable combination" principle:

1. **Primary (used):** the CareerMatch synthetic benchmark, which is the only dataset with human-assigned relevance labels and gold skill annotations in the target context (Philippine early-career, English).
2. **Recommended next (not yet used):** `batuhanmtl/job-skill-set` as a *weak* reference for job skill extraction, and a manually annotated sample of 50–100 resumes from the Kaggle Resume Dataset for resume extraction, once their licences have been confirmed.
3. **Not selected:** the Korean resume-matching dataset (language, LLM labels) and the candidate-matching-synthetic labels (circular with skill overlap).

## Live data is separate

Historical datasets are never mixed with live listings. Live jobs come only from the Greenhouse and Lever providers (see `EXTERNAL_INTEGRATIONS.md`), are stored with their source URL, provider ID, last-checked time and status, and are never generated or imputed.
