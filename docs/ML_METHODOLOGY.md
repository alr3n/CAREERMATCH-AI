# ML methodology

CareerMatch AI ranks job listings for a user and explains each ranking. This document describes what is actually implemented, what was deliberately **not** done, and why.

## 1. Pipeline overview

```
resume file ──► text extraction ──► section detection ──► structured profile ──► (user review & correction)
                                                                │
job providers ──► normalisation ──► job skill tagging ─────────┤
                                                                ▼
                         semantic similarity + skill coverage + experience + preferences + relevance
                                                                ▼
                                   transparent weighted score + evidence ──► ranked, explained results
```

## 2. Resume extraction (rule-based)

Module: `backend/app/ml/profile_extractor.py`, `skill_extractor.py`, `taxonomy.py`.

- **Sections** are found by matching headings against a curated list of aliases ("Work Experience", "OJT", "Licenses & Certifications", …), including Philippine conventions such as OJT and "Seminars attended".
- **Skills** are matched against a curated taxonomy of about 170 skills with aliases. Matching is whole-word. Product names that are also common words are case-sensitive ("React", "Excel"). Very short or ambiguous names (R, Go, C, Swift, Dart, SAS) count only in lines that look like a skills list or sit inside a skills section. Each skill keeps the line it was found on as evidence.
- **Education:** degree patterns (including PH abbreviations such as BSIT → Information Technology), institution keywords and years.
- **Experience:** entries are split into blocks. Titles, organisations and date ranges are parsed. **Duration is only computed when both ends have a month**, so it's "clearly supported", and overlapping intervals are merged for the total.
- **Preferences** (internship, remote, locations, target titles) are detected only in the summary or objective and are offered to the user as suggestions. They're never applied automatically.
- **Not extracted:** names, e-mail addresses, phone numbers and addresses. Nothing is inferred from missing information.

Why rules and not an LLM or a trained NER model? The core workflow has to run locally without paid APIs, every extracted item has to be explainable (evidence line), and no labelled training data for this context exists. An optional LLM could improve extraction later (behind explicit consent). It isn't used for extraction today.

## 3. Job processing

Module: `backend/app/ml/job_parser.py`. Postings are converted to lines with headings and split into sections. Skills under requirement headings are tagged *required*, those under "nice to have" or on lines saying "a plus" are *preferred*, and the rest are *mentioned*. Level, minimum years, employment type, arrangement and category come from provider fields first, then the title or explicit phrases, and otherwise `unknown`.

## 4. Semantic similarity

Module: `backend/app/ml/embeddings.py`.

| Backend | When used | Notes |
|---|---|---|
| Sentence Transformers (`all-MiniLM-L6-v2` by default) | `sentence-transformers` installed and the model loadable | **Pretrained** model, not fine-tuned by this project |
| LSA (TF-IDF 1–2-grams + truncated SVD) | default fallback; always available | Fitted per request on the current job corpus plus the profile. `k = min(128, n_docs // 2)`, a heuristic chosen on the offline test-fixture listings (not the benchmark) to stop LSA collapsing into plain TF-IDF on small corpora |

The profile document is built from the **structured, user-corrected** profile (target roles, summary, skills, experience, projects, education, certifications), not the raw resume text. Cosine similarity is clipped to [0, 1]. Every match result records which backend produced it. Absolute similarity values differ between backends, so scores from different backends aren't directly comparable.

## 5. Transparent scoring (`transparent-v1`)

Module: `backend/app/ml/scoring.py`.

```
score = 100 × Σ wᵢ·cᵢ / Σ wᵢ        (sum over components that could be computed)
```

| Component cᵢ | Default wᵢ | Definition |
|---|---|---|
| Semantic similarity | 0.35 | clipped cosine (section 4) |
| Required-skill coverage | 0.30 | (exact matches + ½ × related matches) / required skills. If the posting has no structured requirements, skills *mentioned* anywhere are used instead, and this is flagged in the explanation |
| Preferred-skill coverage | 0.10 | same, for preferred skills |
| Experience compatibility | 0.10 | lookup of career stage × job level, averaged with min(1, years / required years) when both are known |
| Preference compatibility | 0.10 | share of applicable checks met: arrangement, location (remote counts as a match; "Metro Manila" covers NCR cities), employment type, salary (same currency only; yearly converted to monthly) |
| Profile relevance | 0.05 | best token overlap between the job title and the user's target titles, or a category match |

**Assumptions, stated plainly**

- The default weights are the brief's *proposed starting values*. They were **not tuned or validated**. Presets (`skills_first`, `preferences_first`) and custom weights let users express their own priorities.
- Missing information is excluded, not treated as zero. The share of weight that could be evaluated is reported as **evidence coverage** and shown in the UI, so a high score built on little evidence is visible.
- Related skills (e.g. MySQL for a PostgreSQL requirement) earn half credit and are always labelled as related, never as a match.
- A skill not found in a resume is described as "not found in your resume", never as a deficiency.
- Listing freshness isn't part of the score. Expired and duplicate listings are excluded, and stale listings carry a caveat.
- Ranking is deterministic: score descending, then evidence coverage, then job ID.
- No sensitive or protected characteristics (age, gender, religion, ethnicity, marital status, photos, address) are extracted or used.

**The score is a compatibility indicator. It is not a probability of being hired.**

## 6. Explanations

Module: `backend/app/ml/explain.py`. Explanations are assembled only from structured evidence: the three largest weighted contributions, matched and related skills with the posting line, skills not found, the user's own experience and projects that mention matched skills, preference checks, and caveats (stale listing, unstructured requirements, low evidence coverage). The optional LLM assistant may *rephrase* help for the user but never generates the match explanation.

## 7. Baselines and comparison

`backend/app/ml/baselines.py` provides:

1. **Keyword overlap:** share of the job's detected skills present in the profile (exact matches, no weighting).
2. **TF-IDF cosine:** profile text vs. job text.
3. **Semantic only:** the backend similarity alone.

`scripts/evaluate_matching.py` compares these with `transparent-v1` and two ablations (no preferences; gold-annotated skills instead of extracted ones). Results are in `EVALUATION.md`.

## 8. Supervised ranking: not implemented, by design

A learned ranker (logistic regression, LightGBM LambdaRank, XGBoost rank:ndcg) is only meaningful with a genuine labelled training set. None exists yet: the 360-pair benchmark is a test set, and the candidate public datasets have machine-generated or rule-derived labels (see `DATASET_CARD.md`). Following the brief, the transparent baseline stays in place and the learned ranker is a **future extension**. The data model is ready for it: `match_results` stores per-component features, `user_feedback` collects explicit relevance judgements, and `model_versions` / `evaluation_runs` record versions and metrics.

The process for building that dataset:

1. Collect representative resume–job pairs (consenting users' feedback plus sampled pairs).
2. Have at least two qualified reviewers label them with the rubric in `ml/benchmark/README.md`, and measure agreement.
3. Split by **candidate** (and de-duplicate near-identical postings by fingerprint) into train, validation and test sets, so that no candidate or near-duplicate posting appears in more than one split.
4. Train the ranker on the component features, tune on validation, and report test metrics against `transparent-v1` with confidence intervals.
5. Use SHAP (tree models) or coefficients to explain the learned ranker, and keep the transparent evidence panel either way.

## 9. Known limitations

- Rule-based extraction misses skills outside the taxonomy and ambiguous short names written in prose (e.g. "Python or R").
- LSA similarity depends on the current corpus. Sentence Transformers is better at paraphrase but needs a model download.
- The evaluation benchmark is small, synthetic and single-annotator (see `EVALUATION.md`).
- No evidence about employment outcomes exists or is claimed.
