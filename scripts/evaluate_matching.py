#!/usr/bin/env python
"""Reproducible evaluation of extraction and ranking on the CareerMatch benchmark.

The benchmark (ml/benchmark/) is small, synthetic and hand-labelled — see its
README for the rubric and limitations. Nothing is trained, so the whole
benchmark is used as a test set; the scorer's weights were fixed beforehand
(the project brief's proposed values) and were not tuned on these labels.

    python scripts/evaluate_matching.py                       # writes ml/artifacts/evaluation_report.json
    python scripts/evaluate_matching.py --semantic sentence-transformers   # if installed
    python scripts/evaluate_matching.py --out /tmp/report.json --bootstrap 2000

Metrics: Precision@5 and MRR (relevant = label 2), Recall@10 (label 2),
nDCG@10 (graded 0/1/2), Precision@5 at label ≥ 1; micro precision/recall/F1
for skill extraction. 95% bootstrap confidence intervals resample candidates.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import statistics
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from _common import ARTIFACTS, BENCHMARK, write_json

from app.integrations.jobs.base import ProviderListing
from app.ml import metrics as M
from app.ml.baselines import keyword_overlap_scores, tfidf_cosine_scores
from app.ml.embeddings import LSABackend, get_backend
from app.ml.features import CandidateProfile, ExperienceEntry, JobRecord, JobSkillRef, ProjectEntry
from app.ml.job_parser import fingerprint
from app.ml.profile_extractor import extract_profile
from app.ml.scoring import MODEL_VERSION, rank
from app.services.job_service import normalise

SEED = 42
DATASET_VERSION = "v1"
TODAY = datetime(2026, 10, 1).date()  # fixed reference date so durations are reproducible


# --------------------------------------------------------------------------- loading


def load_benchmark(root: Path):
    candidates = json.loads((root / "candidates.json").read_text(encoding="utf-8"))
    jobs = json.loads((root / "jobs.json").read_text(encoding="utf-8"))
    labels: dict[str, dict[str, int]] = defaultdict(dict)
    with (root / "relevance_labels.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            labels[row["candidate_id"]][row["job_id"]] = int(row["label"])
    return candidates, jobs, labels


def job_records(jobs: list[dict]) -> tuple[list[JobRecord], dict[str, dict]]:
    records, parsed = [], {}
    for j in jobs:
        listing = ProviderListing(
            external_id=j["id"], title=j["title"], company=j["company"], apply_url="https://example.com/benchmark",
            content_html=j.get("content"), content_text=j.get("text"), location=j["location"],
            workplace_type=j["workplace"], commitment=j["commitment"],
        )
        data = normalise(listing)
        skills = data.pop("_skills")
        parsed[j["id"]] = {"data": data, "skills": skills}

        def refs(level: str, skills=skills) -> list[JobSkillRef]:
            return [JobSkillRef(s.skill, s.evidence) for s in skills if s.requirement == level]

        records.append(JobRecord(
            id=j["id"], title=data["title"], company=data["company"], description=data["description"],
            category=data["category"], location=data["location"], work_arrangement=data["work_arrangement"],
            employment_type=data["employment_type"], experience_level=data["experience_level"],
            min_years_experience=data["min_years_experience"], required_skills=refs("required"),
            preferred_skills=refs("preferred"), mentioned_skills=refs("mentioned"), department=data["department"],
        ))
    return records, parsed


def profile_from(candidate: dict, *, gold_skills: bool = False, with_preferences: bool = True) -> tuple[CandidateProfile, object]:
    extracted = extract_profile(candidate["resume"], today=TODAY)
    prefs = candidate["preferences"] if with_preferences else {}
    skills = set(candidate["gold"]["skills"]) if gold_skills else {s.name for s in extracted.skills}
    profile = CandidateProfile(
        skills=skills,
        experiences=[ExperienceEntry(e.title, e.organization, e.description, e.is_internship) for e in extracted.experience],
        projects=[ProjectEntry(p.name, p.description, p.skills) for p in extracted.projects],
        education_fields=[e.field_of_study or e.degree for e in extracted.education if (e.field_of_study or e.degree)],
        certifications=extracted.certifications,
        summary=extracted.summary,
        total_experience_months=extracted.total_experience_months,
        career_stage=prefs.get("career_stage"),
        preferred_titles=prefs.get("preferred_titles", []),
        preferred_locations=prefs.get("preferred_locations", []),
        work_arrangements=prefs.get("work_arrangements", []),
        employment_types=prefs.get("employment_types", []),
    )
    return profile, extracted


# --------------------------------------------------------------------------- extraction


def evaluate_extraction(candidates: list[dict], jobs: list[dict], parsed_jobs: dict) -> dict:
    resume_pairs, field_hits, title_hits, title_total = [], 0, 0, 0
    errors: dict[str, dict] = {}
    for c in candidates:
        extracted = extract_profile(c["resume"], today=TODAY)
        predicted_skills, gold_skills = {s.name for s in extracted.skills}, set(c["gold"]["skills"])
        resume_pairs.append((predicted_skills, gold_skills))
        if predicted_skills != gold_skills:
            errors[c["id"]] = {"false_positives": sorted(predicted_skills - gold_skills),
                               "false_negatives": sorted(gold_skills - predicted_skills)}
        fields = " ".join((e.field_of_study or "") + " " + (e.degree or "") for e in extracted.education).lower()
        field_hits += int(c["gold"]["education_field"].lower() in fields)
        predicted_titles = {(e.title or "").lower() for e in extracted.experience}
        for title in c["gold"]["experience_titles"]:
            title_total += 1
            title_hits += int(title.lower() in predicted_titles)

    job_pairs, level_correct, level_total = [], 0, 0
    for j in jobs:
        gold = j["gold"]
        gold_level = {s: lvl for lvl in ("required", "preferred", "mentioned") for s in gold.get(lvl, [])}
        predicted = {s.skill: s.requirement for s in parsed_jobs[j["id"]]["skills"]}
        job_pairs.append((set(predicted), set(gold_level)))
        if set(predicted) != set(gold_level):
            errors[j["id"]] = {"false_positives": sorted(set(predicted) - set(gold_level)),
                               "false_negatives": sorted(set(gold_level) - set(predicted))}
        for skill, lvl in gold_level.items():
            if skill in predicted:
                level_total += 1
                level_correct += int(predicted[skill] == lvl)

    resume_skills = M.micro_prf(resume_pairs)
    job_skills = M.micro_prf(job_pairs)
    return {
        "resume_skills": {**_rounded(resume_skills), "examples": len(candidates)},
        "job_skills": {**_rounded(job_skills), "examples": len(jobs)},
        "education_field_accuracy": {"precision": None, "recall": round(field_hits / len(candidates), 4), "f1": None,
                                     "examples": len(candidates), "note": "share of resumes whose gold field of study was extracted"},
        "experience_title_recall": {"precision": None, "recall": round(title_hits / title_total, 4) if title_total else None,
                                    "f1": None, "examples": title_total},
        "job_requirement_level_accuracy": {"precision": None, "recall": round(level_correct / level_total, 4) if level_total else None,
                                           "f1": None, "examples": level_total,
                                           "note": "required/preferred/mentioned tag correct, among correctly detected skills"},
        "skill_errors": errors,
    }


def _rounded(d: dict) -> dict:
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}


# --------------------------------------------------------------------------- ranking


def ranking_metrics(ranked_ids: list[str], labels: dict[str, int]) -> dict:
    graded = [labels.get(j, 0) for j in ranked_ids]
    return {
        "precision@5": M.precision_at_k(graded, 5, threshold=2),
        "precision@5_label>=1": M.precision_at_k(graded, 5, threshold=1),
        "recall@10": M.recall_at_k(graded, 10, threshold=2),
        "ndcg@10": M.ndcg_at_k(graded, 10),
        "mrr": M.reciprocal_rank(graded, threshold=2),
    }


def paired_diff_ci(a: list[float], b: list[float], n: int, seed: int = SEED) -> dict | None:
    """Bootstrap CI of mean(a - b) over candidates (paired)."""
    diffs = [x - y for x, y in zip(a, b, strict=True) if x is not None and y is not None]
    if len(diffs) < 2 or n <= 0:
        return None
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(diffs, k=len(diffs))) for _ in range(n))
    return {"mean_difference": round(statistics.fmean(diffs), 4),
            "95ci": [round(means[int(0.025 * n)], 4), round(means[int(0.975 * n) - 1], 4)]}


def bootstrap_ci(values: list[float], n: int, seed: int = SEED) -> list[float] | None:
    values = [v for v in values if v is not None]
    if len(values) < 2 or n <= 0:
        return None
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(values, k=len(values))) for _ in range(n))
    return [round(means[int(0.025 * n)], 4), round(means[int(0.975 * n) - 1], 4)]


def run_models(candidates, records, labels, semantic_backend, n_boot: int):
    def by_score(scores: list[float]) -> list[str]:
        order = sorted(range(len(records)), key=lambda i: (-scores[i], records[i].id))
        return [records[i].id for i in order]

    docs = [r.document() for r in records]
    models = {
        "keyword-overlap": ("baseline", "Share of the job's detected skills found in the profile (exact matches only)."),
        "tfidf-cosine": ("baseline", "TF-IDF cosine similarity between profile text and job text."),
        "semantic-only": ("baseline", f"Cosine similarity from the semantic backend alone ({semantic_backend.name})."),
        f"{MODEL_VERSION}": ("candidate", "Transparent multi-signal score with default weights, extracted skills and stated preferences."),
        f"{MODEL_VERSION} (no preferences)": ("ablation", "Same scorer without the candidate's stated preferences."),
        f"{MODEL_VERSION} (gold skills)": ("ablation", "Same scorer using hand-annotated skills instead of extracted ones (oracle extraction)."),
    }
    per_model: dict[str, list[dict]] = {m: [] for m in models}
    timings = {"extraction_ms": [], "matching_ms": []}
    for c in candidates:
        t0 = time.perf_counter()
        profile, _ = profile_from(c)
        timings["extraction_ms"].append((time.perf_counter() - t0) * 1000)
        lab = labels[c["id"]]

        per_model["keyword-overlap"].append(ranking_metrics(by_score(keyword_overlap_scores(profile, records)), lab))
        per_model["tfidf-cosine"].append(ranking_metrics(by_score(tfidf_cosine_scores(profile, records)), lab))
        t1 = time.perf_counter()
        sem = list(semantic_backend.similarities(profile.document(), docs))
        ranked = rank(profile, records, sem)
        timings["matching_ms"].append((time.perf_counter() - t1) * 1000)
        per_model["semantic-only"].append(ranking_metrics(by_score(sem), lab))
        per_model[MODEL_VERSION].append(ranking_metrics([j.id for j, _ in ranked], lab))

        no_pref, _ = profile_from(c, with_preferences=False)
        sem_np = list(semantic_backend.similarities(no_pref.document(), docs))
        per_model[f"{MODEL_VERSION} (no preferences)"].append(ranking_metrics([j.id for j, _ in rank(no_pref, records, sem_np)], lab))
        gold, _ = profile_from(c, gold_skills=True)
        sem_g = list(semantic_backend.similarities(gold.document(), docs))
        per_model[f"{MODEL_VERSION} (gold skills)"].append(ranking_metrics([j.id for j, _ in rank(gold, records, sem_g)], lab))

    stages = [c["stage"] for c in candidates]
    runs = []
    for name, (kind, note) in models.items():
        rows = per_model[name]
        keys = rows[0].keys()
        metrics = {k: (round(M.mean([r[k] for r in rows]), 4) if M.mean([r[k] for r in rows]) is not None else None) for k in keys}
        by_stage: dict[str, dict] = {}
        for stage in sorted(set(stages)):
            sel = [r for r, s in zip(rows, stages, strict=True) if s == stage]
            by_stage[stage] = {"candidates": len(sel), "ndcg@10": round(M.mean([r["ndcg@10"] for r in sel]) or 0, 4)}
        runs.append({
            "model": name, "kind": kind, "split": "test", "metrics": metrics,
            "ndcg@10_95ci": bootstrap_ci([r["ndcg@10"] for r in rows], n_boot),
            "by_career_stage": by_stage, "notes": note,
        })
    # Paired comparison of the candidate against the strongest baseline by nDCG@10.
    baselines = [r for r in runs if r["kind"] == "baseline"]
    best = max(baselines, key=lambda r: r["metrics"]["ndcg@10"])
    comparison = {
        "candidate": MODEL_VERSION,
        "baseline": best["model"],
        "metric": "ndcg@10",
        **(paired_diff_ci([r["ndcg@10"] for r in per_model[MODEL_VERSION]],
                          [r["ndcg@10"] for r in per_model[best["model"]]], n_boot) or {}),
    }
    ideal_p5 = statistics.fmean(min(5, sum(1 for v in labels[c["id"]].values() if v == 2)) / 5 for c in candidates)
    return runs, timings, comparison, round(ideal_p5, 4)


# --------------------------------------------------------------------------- data quality


def data_quality(parsed_jobs: dict) -> dict:
    listings = [p["data"] for p in parsed_jobs.values()]
    def summary(items: list[dict]) -> dict:
        n = len(items)
        fps = [fingerprint(i["company"], i["title"], i["location"], i["description"]) for i in items]
        return {
            "listings": n,
            "duplicate_rate": round(1 - len(set(fps)) / n, 4) if n else None,
            "https_apply_links": round(sum(i["apply_url"].startswith("https://") for i in items) / n, 4) if n else None,
            "unknown_work_arrangement": round(sum(i["work_arrangement"] == "unknown" for i in items) / n, 4),
            "unknown_employment_type": round(sum(i["employment_type"] == "unknown" for i in items) / n, 4),
            "unknown_experience_level": round(sum(i["experience_level"] == "unknown" for i in items) / n, 4),
            "missing_location": round(sum(not i["location"] for i in items) / n, 4),
        }

    return {
        "benchmark_jobs": summary(listings),
        "not_measured": [
            "Working source links (needs network access to the providers; checked per refresh in production via HTTP status).",
            "Share of expired listings still displayed: expired listings are excluded by query; verify on a live database.",
        ],
    }


# --------------------------------------------------------------------------- main


LIMITATIONS = [
    "Tiny benchmark: 12 synthetic candidates × 30 synthetic postings (360 pairs). Results are indicative only and "
    "confidence intervals are wide.",
    "Labels were assigned by the project author with a written rubric; there was no second annotator, so "
    "inter-annotator agreement is unknown, and the author also designed the scorer (risk of shared assumptions).",
    "Candidates and postings were written to cover distinct fields, which makes field discrimination easier than "
    "in real data. Real postings are noisier and longer.",
    "The skill taxonomy was written by the same author; extraction recall on skills outside the taxonomy is zero "
    "by construction (a few such skills are included in the gold annotations to keep this visible).",
    "Default scoring weights come from the project brief and were not tuned; no supervised ranker was trained "
    "because no genuine labelled training data exists.",
    "This evaluates ranking agreement with relevance labels, not employment outcomes. No claim is made that "
    "CareerMatch AI improves hiring results.",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--benchmark", type=Path, default=BENCHMARK)
    parser.add_argument("--out", type=Path, default=ARTIFACTS / "evaluation_report.json")
    parser.add_argument("--semantic", choices=["lsa", "sentence-transformers"], default="lsa")
    parser.add_argument("--bootstrap", type=int, default=1000)
    args = parser.parse_args()
    random.seed(SEED)

    candidates, jobs, labels = load_benchmark(args.benchmark)
    records, parsed = job_records(jobs)
    backend = LSABackend() if args.semantic == "lsa" else get_backend("sentence-transformers")
    if args.semantic == "sentence-transformers" and isinstance(backend, LSABackend):
        raise SystemExit("sentence-transformers is not available; install backend/requirements-semantic.txt")

    extraction = evaluate_extraction(candidates, jobs, parsed)
    runs, timings, comparison, ideal_p5 = run_models(candidates, records, labels, backend, args.bootstrap)
    counts = defaultdict(int)
    for lab in labels.values():
        for v in lab.values():
            counts[v] += 1

    report = {
        "report_version": 1,
        "evaluated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "model_version": MODEL_VERSION,
        "semantic_backend": backend.name,
        "seed": SEED,
        "dataset": {
            "name": "CareerMatch synthetic benchmark",
            "version": DATASET_VERSION,
            "description": "Synthetic early-career candidate resumes (Philippine context) and synthetic job postings "
                           "written for this project, with graded relevance labels (0 not relevant, 1 partially "
                           "relevant, 2 highly relevant) and gold skill annotations. No real personal data.",
            "candidates": len(candidates),
            "jobs": len(jobs),
            "pairs": sum(len(v) for v in labels.values()),
            "label_counts": {str(k): v for k, v in sorted(counts.items())},
            "labels": "Assigned by the project author following the rubric in ml/benchmark/README.md; not independently reviewed.",
            "split": "test (100%)",
            "split_note": "No model is trained, so there is no training or validation split. The scorer's weights were "
                          "fixed before evaluation and not tuned on these labels.",
        },
        "metric_definitions": {
            "precision@5": "share of the top 5 with label 2",
            "precision@5_label>=1": "share of the top 5 with label ≥ 1",
            "recall@10": "share of label-2 jobs found in the top 10",
            "ndcg@10": "graded nDCG (gain 2^label − 1)",
            "mrr": "reciprocal rank of the first label-2 job",
        },
        "runs": runs,
        "max_achievable": {"precision@5": ideal_p5,
                           "note": "Few label-2 jobs exist per candidate, so Precision@5 cannot reach 1.0."},
        "comparison": comparison,
        "extraction": extraction,
        "data_quality": data_quality(parsed),
        "performance": {
            "environment": f"{platform.system()} {platform.machine()}, Python {platform.python_version()}",
            "resume_extraction_ms_median": round(statistics.median(timings["extraction_ms"]), 1),
            "matching_ms_median_per_candidate": round(statistics.median(timings["matching_ms"]), 1),
            "jobs_per_match": len(records),
            "note": "In-process timings of the ML code only (no HTTP or database), measured during this run.",
        },
        "limitations": LIMITATIONS,
    }
    write_json(args.out, report)

    print(f"Benchmark: {len(candidates)} candidates × {len(jobs)} jobs; semantic backend: {backend.name}\n")
    header = f"{'model':38} {'P@5':>6} {'P@5≥1':>6} {'R@10':>6} {'nDCG@10':>8} {'MRR':>6}  nDCG 95% CI"
    print(header)
    print("-" * len(header))
    for r in runs:
        m = r["metrics"]
        print(f"{r['model']:38} {m['precision@5']:6.3f} {m['precision@5_label>=1']:6.3f} {m['recall@10']:6.3f} "
              f"{m['ndcg@10']:8.3f} {m['mrr']:6.3f}  {r['ndcg@10_95ci']}")
    print(f"\nMax achievable P@5: {ideal_p5}")
    print(f"Paired nDCG@10 difference vs {comparison['baseline']}: {comparison.get('mean_difference')} "
          f"95% CI {comparison.get('95ci')}")
    print("\nExtraction:")
    for task, vals in extraction.items():
        print(f"  {task:32} " + " ".join(f"{k}={v}" for k, v in vals.items() if k in {"precision", "recall", "f1", "examples"}))
    print(f"\nReport written to {args.out}")


if __name__ == "__main__":
    main()
