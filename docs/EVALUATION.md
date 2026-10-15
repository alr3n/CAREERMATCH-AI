# Evaluation

Reproduce with:

```bash
cd backend && pip install -r requirements.txt && cd ..
python scripts/evaluate_matching.py            # writes ml/artifacts/evaluation_report.json
```

The report is also shown in the app under **Model evaluation**. If no report exists, the page says "Not yet evaluated".

## Setup

| Item | Value |
|---|---|
| Dataset | CareerMatch synthetic benchmark v1 (`ml/benchmark/`): 12 candidates × 30 postings = 360 labelled pairs (17 highly relevant, 25 partially relevant, 318 not relevant) |
| Labels | Graded 0/1/2, assigned by the project author with the rubric in `ml/benchmark/README.md`. One annotator, not independently reviewed |
| Split | 100% test. Nothing is trained; the scorer's weights were fixed before evaluation |
| Model under test | `transparent-v1`, default weights, extracted skills and the candidate's stated preferences |
| Semantic backend | LSA (`lsa-tfidf-svd (local)`). Sentence Transformers couldn't be downloaded in the build environment, so it **has not been evaluated** |
| Seed | 42. Bootstrap: 1,000 resamples over candidates |
| Evaluated | 2026-10-14 (see `evaluated_at` in the report) |

Metric definitions: **P@5** = share of the top 5 with label 2; **P@5 (≥1)** = share with label ≥ 1; **R@10** = share of label-2 jobs ranked in the top 10; **nDCG@10** = graded, gain 2^label − 1; **MRR** = reciprocal rank of the first label-2 job.

## Ranking results (measured)

| Model | Role | P@5 | P@5 (≥1) | R@10 | nDCG@10 | nDCG@10 95% CI | MRR |
|---|---|---|---|---|---|---|---|
| keyword-overlap | baseline | 0.267 | 0.550 | 1.000 | 0.922 | [0.854, 0.974] | 0.883 |
| tfidf-cosine | baseline | 0.283 | 0.567 | 1.000 | 0.926 | [0.887, 0.960] | 0.944 |
| semantic-only (LSA) | baseline | 0.283 | 0.517 | 1.000 | 0.908 | [0.861, 0.948] | 0.933 |
| **transparent-v1** | candidate | 0.283 | **0.600** | 1.000 | **0.952** | [0.901, 0.984] | 0.933 |
| transparent-v1, no preferences | ablation | 0.267 | 0.550 | 1.000 | 0.933 | [0.875, 0.973] | 0.931 |
| transparent-v1, gold skills | ablation | 0.283 | 0.583 | 1.000 | 0.948 | [0.899, 0.978] | 0.933 |

- **Maximum achievable P@5 is 0.283.** Most candidates have only one or two highly relevant jobs, so P@5 can't reach 1.0. Every model except keyword overlap hits this ceiling.
- **Paired difference, transparent-v1 vs. tfidf-cosine (nDCG@10): +0.026, 95% CI [−0.001, 0.051].** The interval includes zero, so **this benchmark doesn't show a reliable improvement over the TF-IDF baseline.** The transparent scorer is at least as good on these cases while also providing explanations, preference handling and evidence coverage.
- Removing preferences lowers nDCG@10 (0.952 → 0.933), and P@5 (≥1) drops too, so stated preferences help on this benchmark.
- Using gold skills instead of extracted ones doesn't improve ranking (0.948 vs. 0.952), which suggests extraction errors aren't the bottleneck here.
- R@10 is 1.000 for every method: the benchmark is easy at depth 10 because its fields are well separated. That's a limitation of the benchmark, not evidence of real-world performance.
- The report also breaks nDCG@10 down by career stage (student, fresh graduate, entry level, experienced, career transition). With only 1–4 candidates per stage, those numbers aren't interpretable on their own.

## Extraction results (measured)

| Task | Precision | Recall | F1 | Examples |
|---|---|---|---|---|
| Resume skills (micro) | 0.923 | 0.973 | 0.947 | 12 resumes |
| Job-posting skills (micro) | 0.979 | 0.946 | 0.962 | 30 postings |
| Education field of study extracted | n/a | 1.000 | n/a | 12 resumes |
| Experience titles extracted | n/a | 1.000 | n/a | 10 entries |
| Required/preferred/mentioned tag correct (among detected skills) | n/a | 0.964 | n/a | 139 skills |

**Errors observed** (all listed in `extraction.skill_errors` in the report):

- *False positives:* "Sales" from a project called "Sales Forecast Notebook"; "Auditing" from "Test Audit Firm"; "Social Media Marketing" from "social media kits"/"social media graphics"; "Call Center Operations" from "Test BPO Company"; "Leadership" from "Present to leadership"; "Data Visualization" from "dashboards".
- *False negatives:* short names in prose ("Python **or R**", "**Go**", "**Dart**") because ambiguous short names only count in list contexts; "Content Writing" from "content writer"; "Accounting" from "BS Accountancy"; "English Proficiency" from "Good written English"; "Graphic Design" from "a portfolio of design work"; "UI/UX Design" from "wireframes"; *Vercel* and *dbt* (not in the taxonomy, or the strict-matching rule).

These errors were **not** fixed by tuning the extractor against the benchmark. Doing so would turn the test set into a development set. They're recorded as future work, to be addressed and then re-measured on a **new** held-out set.

**Why extraction scores are high.** The same author wrote the taxonomy, the resumes and the gold annotations, so vocabulary overlap is much higher than with real resumes. Expect substantially lower recall on real documents.

## Job data quality (measured on benchmark postings and demo listings)

From `data_quality` in the report: duplicate rate 0% for both sets; 100% of apply links use HTTPS; the share of `unknown` work arrangement, employment type and experience level is reported per set; locations are present for every listing.

**Not measured:** working source links (needs network access to the providers) and the share of expired listings still displayed (they're excluded by query; verify on a live database).

## System performance (measured, indicative)

The report records the median in-process time for resume extraction and for scoring 30 jobs against one candidate (ML code only, no HTTP or database), plus the machine description. Both were well under a second on the build machine. Treat these as order-of-magnitude figures, not benchmarks.

## Limitations of this evaluation

1. **Tiny, synthetic, single-annotator benchmark.** The confidence intervals are wide, and agreement between annotators is unknown.
2. **The author designed the scorer, the taxonomy and the labels**, which risks shared assumptions inflating agreement.
3. **Well-separated fields** make the task easier than real job search.
4. **No real-world validation:** nothing here measures performance on real resumes and postings, fairness across demographic groups, or employment outcomes. **No claim is made that CareerMatch AI improves hiring results.**
5. Sentence Transformers and the external datasets haven't been evaluated (no network access during the build).

## Next steps

- Have a second annotator label the benchmark, and report Cohen's κ.
- Annotate a sample of real (consented or public, licence-checked) resumes and postings as a new held-out set.
- Evaluate the Sentence Transformers backend: `python scripts/evaluate_matching.py --semantic sentence-transformers`.
- Collect `user_feedback` and, once enough labelled pairs exist, train and compare a learned ranker (see `ML_METHODOLOGY.md`, section 8).
