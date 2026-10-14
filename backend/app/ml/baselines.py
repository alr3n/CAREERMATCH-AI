"""Simple baselines the transparent scorer is compared against."""

from __future__ import annotations

import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.ml.features import CandidateProfile, JobRecord

_TOKEN = re.compile(r"[a-z0-9+#.]+")
_STOP = {
    "the", "and", "a", "an", "of", "to", "in", "for", "with", "on", "or", "is", "are", "be", "as", "at", "by",
    "we", "you", "our", "your", "will", "this", "that", "from", "it", "have", "has", "who", "can",
}


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 1}


def keyword_overlap_scores(profile: CandidateProfile, jobs: list[JobRecord]) -> list[float]:
    """Baseline 1: share of the job's skill keywords present in the profile.

    Uses every skill the job mentions (required, preferred or elsewhere),
    exact canonical matches only — no related-skill credit, no weighting.
    Falls back to word overlap when a job lists no recognised skills.
    """
    user = {s.lower() for s in profile.skills}
    profile_tokens = _tokens(profile.document())
    scores = []
    for job in jobs:
        skills = {s.skill.lower() for s in job.required_skills + job.preferred_skills + job.mentioned_skills}
        if skills:
            scores.append(len(skills & user) / len(skills))
        else:
            job_tokens = _tokens(job.document())
            scores.append(len(job_tokens & profile_tokens) / len(job_tokens) if job_tokens else 0.0)
    return scores


def tfidf_cosine_scores(profile: CandidateProfile, jobs: list[JobRecord]) -> list[float]:
    """Baseline 2: TF-IDF cosine similarity between profile text and job text."""
    if not jobs:
        return []
    corpus = [profile.document(), *[j.document() for j in jobs]]
    try:
        matrix = TfidfVectorizer(stop_words="english", sublinear_tf=True).fit_transform(corpus)
    except ValueError:
        return [0.0] * len(jobs)
    return list(np.asarray(cosine_similarity(matrix[:1], matrix[1:])[0], dtype=float))
