"""Transparent, multi-signal compatibility scoring (model ``transparent-v1``).

    score = 100 × Σ wᵢ·cᵢ / Σ wᵢ      (sum over components that are applicable)

Components (each normalised to [0, 1]):

=========================  ======  ==============================================
component                  weight  meaning
=========================  ======  ==============================================
semantic_similarity        0.35    cosine similarity of profile vs. job text
required_skill_coverage    0.30    share of required skills found (related = ½)
preferred_skill_coverage   0.10    share of preferred skills found (related = ½)
experience_compatibility   0.10    career stage / years vs. job level
preference_compatibility   0.10    arrangement, location, employment type, salary
profile_relevance          0.05    preferred titles / categories vs. job
=========================  ======  ==============================================

The default weights are the starting values proposed in the project brief.
They are **assumptions, not validated optimal weights** — see
docs/ML_METHODOLOGY.md and the evaluation report.

Missing information is handled explicitly: a component that cannot be
computed (e.g. the posting lists no skills, or the user gave no preferences)
is ``None`` and is excluded from both numerator and denominator. The share of
total weight that *could* be evaluated is reported as ``evidence_coverage`` so
a high score built on little evidence is visible as such.

The score is a compatibility indicator. It is **not** a probability of being
hired and must never be presented as one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

from app.ml.features import CandidateProfile, JobRecord, JobSkillRef
from app.ml.taxonomy import related_skills

MODEL_VERSION = "transparent-v1"

DEFAULT_WEIGHTS: dict[str, float] = {
    "semantic_similarity": 0.35,
    "required_skill_coverage": 0.30,
    "preferred_skill_coverage": 0.10,
    "experience_compatibility": 0.10,
    "preference_compatibility": 0.10,
    "profile_relevance": 0.05,
}

WEIGHT_PRESETS: dict[str, dict[str, float]] = {
    "balanced": DEFAULT_WEIGHTS,
    "skills_first": {
        "semantic_similarity": 0.25,
        "required_skill_coverage": 0.40,
        "preferred_skill_coverage": 0.15,
        "experience_compatibility": 0.10,
        "preference_compatibility": 0.05,
        "profile_relevance": 0.05,
    },
    "preferences_first": {
        "semantic_similarity": 0.25,
        "required_skill_coverage": 0.20,
        "preferred_skill_coverage": 0.05,
        "experience_compatibility": 0.10,
        "preference_compatibility": 0.25,
        "profile_relevance": 0.15,
    },
}

RELATED_CREDIT = 0.5

# stage -> job level -> compatibility
_STAGE_LEVEL: dict[str, dict[str, float]] = {
    "student": {"internship": 1.0, "entry": 0.6, "mid": 0.15, "senior": 0.0},
    "fresh_graduate": {"internship": 0.9, "entry": 1.0, "mid": 0.35, "senior": 0.05},
    "entry_level": {"internship": 0.6, "entry": 1.0, "mid": 0.6, "senior": 0.2},
    "experienced": {"internship": 0.3, "entry": 0.7, "mid": 1.0, "senior": 0.9},
    "career_transition": {"internship": 0.8, "entry": 1.0, "mid": 0.5, "senior": 0.2},
}

_NCR = (
    "metro manila", "manila", "makati", "taguig", "bgc", "pasig", "quezon city", "mandaluyong", "pasay",
    "parañaque", "paranaque", "muntinlupa", "alabang", "ortigas", "caloocan", "marikina", "san juan", "valenzuela",
    "las piñas", "las pinas", "malabon", "navotas", "pateros", "ncr",
)
_TITLE_STOP = {"intern", "internship", "junior", "jr", "senior", "sr", "lead", "the", "a", "an", "and", "of", "for", "i", "ii", "iii"}


@dataclass
class SkillCoverage:
    score: float | None
    matched: list[JobSkillRef] = field(default_factory=list)
    related: list[tuple[JobSkillRef, str]] = field(default_factory=list)  # (job skill, user's related skill)
    missing: list[JobSkillRef] = field(default_factory=list)
    used_mentioned_proxy: bool = False


@dataclass
class PreferenceCheck:
    name: str
    satisfied: bool
    detail: str


@dataclass
class ScoreBreakdown:
    score: float  # 0..100
    evidence_coverage: float  # 0..1
    components: dict[str, float | None]
    weights: dict[str, float]
    required: SkillCoverage
    preferred: SkillCoverage
    preference_checks: list[PreferenceCheck]
    experience_note: str | None
    relevance_note: str | None


def normalise_weights(weights: dict[str, float] | None) -> dict[str, float]:
    merged = dict(DEFAULT_WEIGHTS)
    if weights:
        for key, value in weights.items():
            if key in merged:
                merged[key] = max(0.0, float(value))
    total = sum(merged.values())
    if total <= 0:
        return dict(DEFAULT_WEIGHTS)
    return {k: v / total for k, v in merged.items()}


def skill_coverage(job_skills: list[JobSkillRef], user_skills: set[str]) -> SkillCoverage:
    if not job_skills:
        return SkillCoverage(score=None)
    user_lower = {s.lower(): s for s in user_skills}
    cov = SkillCoverage(score=0.0)
    total = 0.0
    for ref in job_skills:
        if ref.skill.lower() in user_lower:
            cov.matched.append(ref)
            total += 1.0
            continue
        related = sorted(r for r in related_skills(ref.skill) if r.lower() in user_lower)
        if related:
            cov.related.append((ref, related[0]))
            total += RELATED_CREDIT
        else:
            cov.missing.append(ref)
    cov.score = total / len(job_skills)
    return cov


def experience_compatibility(profile: CandidateProfile, job: JobRecord) -> tuple[float | None, str | None]:
    values: list[float] = []
    notes: list[str] = []
    stage = profile.career_stage
    level = job.experience_level
    if stage in _STAGE_LEVEL and level in _STAGE_LEVEL[stage]:
        values.append(_STAGE_LEVEL[stage][level])
        notes.append(f"{level.replace('_', ' ')} posting vs. your stage: {stage.replace('_', ' ')}")
    if job.min_years_experience is not None and profile.total_experience_months is not None:
        if job.min_years_experience == 0:
            values.append(1.0)
        else:
            years = profile.total_experience_months / 12
            values.append(min(1.0, years / job.min_years_experience))
        notes.append(
            f"posting asks for {job.min_years_experience}+ years; your resume shows about "
            f"{profile.total_experience_months / 12:.1f} years with exact dates"
        )
    if not values:
        return None, None
    return sum(values) / len(values), "; ".join(notes)


def _monthly(amount: Decimal, interval: str | None) -> Decimal | None:
    interval = (interval or "").lower()
    if "year" in interval or "annual" in interval:
        return amount / 12
    if "month" in interval or not interval:
        return amount
    return None  # hourly/daily/weekly: not comparable without assumptions


def _location_match(preferred: list[str], job_location: str) -> bool:
    loc = job_location.lower()
    for pref in preferred:
        p = pref.lower().strip()
        if not p:
            continue
        if p in loc:
            return True
        if p in {"metro manila", "ncr", "manila"} and any(city in loc for city in _NCR):
            return True
    return False


def preference_compatibility(profile: CandidateProfile, job: JobRecord) -> tuple[float | None, list[PreferenceCheck]]:
    checks: list[PreferenceCheck] = []
    label = {"remote": "Remote", "hybrid": "Hybrid", "onsite": "On-site"}
    if profile.work_arrangements and job.work_arrangement != "unknown":
        ok = job.work_arrangement in profile.work_arrangements
        checks.append(PreferenceCheck(
            "work_arrangement", ok,
            f"{label.get(job.work_arrangement, job.work_arrangement)} "
            + ("matches your preference" if ok else
               f"is not in your preferences ({', '.join(label.get(a, a) for a in profile.work_arrangements)})"),
        ))
    if profile.preferred_locations and job.location:
        if job.work_arrangement == "remote":
            checks.append(PreferenceCheck("location", True, f"Remote role ({job.location})"))
        else:
            ok = _location_match(profile.preferred_locations, job.location)
            checks.append(PreferenceCheck(
                "location", ok,
                f"{job.location} " + ("is in your preferred locations" if ok else "is outside your preferred locations"),
            ))
    if profile.employment_types and job.employment_type != "unknown":
        ok = job.employment_type in profile.employment_types
        checks.append(PreferenceCheck(
            "employment_type", ok,
            f"{job.employment_type.replace('_', '-')} " + ("matches your preference" if ok else "is not a type you selected"),
        ))
    if (
        profile.min_salary is not None
        and job.salary_max is not None
        and profile.salary_currency
        and job.salary_currency == profile.salary_currency
    ):
        monthly = _monthly(Decimal(job.salary_max), job.salary_interval)
        if monthly is not None:
            ok = monthly >= profile.min_salary
            checks.append(PreferenceCheck(
                "salary", ok,
                f"Listed maximum ≈ {job.salary_currency} {monthly:,.0f}/month "
                + ("meets" if ok else "is below") + f" your minimum of {profile.salary_currency} {profile.min_salary:,.0f}",
            ))
    if not checks:
        return None, checks
    return sum(1.0 for c in checks if c.satisfied) / len(checks), checks


def _title_tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9+#]+", text.lower()) if t not in _TITLE_STOP}


def profile_relevance(profile: CandidateProfile, job: JobRecord) -> tuple[float | None, str | None]:
    scores: list[tuple[float, str]] = []
    if profile.preferred_titles:
        job_tokens = _title_tokens(job.title)
        best, best_title = 0.0, ""
        for title in profile.preferred_titles:
            tokens = _title_tokens(title)
            if tokens:
                overlap = len(tokens & job_tokens) / len(tokens)
                if overlap > best:
                    best, best_title = overlap, title
        scores.append((best, f"title overlaps with '{best_title}'" if best > 0 else "title differs from your target roles"))
    if profile.preferred_categories:
        cats = {c.lower() for c in profile.preferred_categories}
        hit = (job.category or "").lower() in cats or any(
            c in (job.department or "").lower() for c in cats if c
        )
        scores.append((1.0 if hit else 0.0, f"category '{job.category}' " + ("is" if hit else "is not") + " one you selected"))
    if not scores:
        return None, None
    best = max(scores, key=lambda s: s[0])
    return best[0], best[1]


def score_job(
    profile: CandidateProfile, job: JobRecord, semantic: float | None, weights: dict[str, float] | None = None
) -> ScoreBreakdown:
    w = normalise_weights(weights)
    required_refs = job.required_skills
    used_proxy = False
    if not required_refs and job.mentioned_skills:
        required_refs = job.mentioned_skills
        used_proxy = True
    required = skill_coverage(required_refs, profile.skills)
    required.used_mentioned_proxy = used_proxy
    preferred = skill_coverage(job.preferred_skills, profile.skills)
    exp_score, exp_note = experience_compatibility(profile, job)
    pref_score, checks = preference_compatibility(profile, job)
    rel_score, rel_note = profile_relevance(profile, job)

    components: dict[str, float | None] = {
        "semantic_similarity": None if semantic is None else float(max(0.0, min(1.0, semantic))),
        "required_skill_coverage": required.score,
        "preferred_skill_coverage": preferred.score,
        "experience_compatibility": exp_score,
        "preference_compatibility": pref_score,
        "profile_relevance": rel_score,
    }
    available = {k: v for k, v in components.items() if v is not None}
    weight_sum = sum(w[k] for k in available)
    score = 100.0 * sum(w[k] * v for k, v in available.items()) / weight_sum if weight_sum > 0 else 0.0
    return ScoreBreakdown(
        score=round(score, 2),
        evidence_coverage=round(weight_sum, 4),
        components={k: (round(v, 4) if v is not None else None) for k, v in components.items()},
        weights={k: round(v, 4) for k, v in w.items()},
        required=required,
        preferred=preferred,
        preference_checks=checks,
        experience_note=exp_note,
        relevance_note=rel_note,
    )


def rank(
    profile: CandidateProfile,
    jobs: list[JobRecord],
    semantic_scores: list[float] | None,
    weights: dict[str, float] | None = None,
) -> list[tuple[JobRecord, ScoreBreakdown]]:
    """Deterministic ranking: score desc, then evidence coverage, then job id."""
    results = []
    for idx, job in enumerate(jobs):
        sem = semantic_scores[idx] if semantic_scores is not None else None
        results.append((job, score_job(profile, job, sem, weights)))
    results.sort(key=lambda item: (-item[1].score, -item[1].evidence_coverage, item[0].id))
    return results
