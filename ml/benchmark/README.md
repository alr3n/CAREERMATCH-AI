# CareerMatch synthetic benchmark (v1)

A small, hand-built test set for evaluating CareerMatch AI's extraction and ranking. **Everything here is synthetic.** The candidates, employers and postings were written for this project, and the contact details use `example.com` and placeholder numbers. No real person or company is represented.

| File | Contents |
|---|---|
| `candidates.json` | 12 candidate personas: resume text, stated preferences, career stage and **gold annotations** (skills explicitly named in the resume, field of study, experience titles) |
| `jobs.json` | 30 job postings (HTML or plain text) across 11 fields and four seniority levels, with **gold skill annotations** tagged required / preferred / mentioned |
| `relevance_labels.csv` | Graded relevance for every candidate × job pair (360 rows) |

## Relevance rubric

Seniority ladder: internship < entry < mid < senior. A student is at the internship level, and a fresh graduate, career changer or entry-level professional is at entry level. A candidate with about 3 years of experience is at mid level.

| Label | Meaning |
|---|---|
| **2**, highly relevant | Same target field, seniority within one step of the candidate's level, **and** the candidate has most of the core required skills. |
| **1**, partially relevant | Same or adjacent field with a notable gap (seniority one step off, a type the candidate didn't ask for, or about half the core skills), **or** a different field where the candidate's skills transfer strongly. |
| **0**, not relevant | Unrelated field, or seniority two or more steps above the candidate. |

Label counts: 17 highly relevant, 25 partially relevant, 318 not relevant.

## Annotation guideline for gold skills

- Annotate a skill only if the text **explicitly names it** or its activity (e.g. "unit tests with pytest" → Unit Testing, "wireframes and prototype" → UI/UX Design).
- Implied skills are not annotated: a CNN on images is not automatically "Computer Vision".
- Use canonical taxonomy names where one exists. Skills outside the taxonomy are still annotated (e.g. *Vercel*) so that extraction recall honestly reflects missed skills.
- For postings, the level is the section the skill appears in: required, preferred, or mentioned when the posting has no structured requirements.

## How it was built, and what it can and can't show

- Labels and annotations were written by the project author following the rubric above. **There was no second annotator**, so inter-annotator agreement is unknown. The same author designed the scorer and the skill taxonomy, which risks shared assumptions.
- Candidates and postings were written to cover distinct fields, which makes field discrimination easier than real data. Real postings are longer and noisier.
- Nothing is trained on this benchmark. The scoring weights were fixed beforehand (the project brief's proposed values), and **the extractor must not be tuned on these errors**. If you change the extractor or taxonomy in response to benchmark results, the benchmark becomes a development set and you need a new held-out test set.
- What it can show: whether the ranking agrees with a careful human judgement on clear-cut cases, and where extraction fails.
- What it can't show: performance on real resumes and postings, fairness across groups, or any effect on employment outcomes.

## Extending it

Add candidates or jobs to the JSON files, add a label for **every** new pair to `relevance_labels.csv`, bump the version in `scripts/evaluate_matching.py` (`DATASET_VERSION`), and re-run `python scripts/evaluate_matching.py`. Ideally, have a second person label a sample independently and report the agreement (e.g. Cohen's κ).
